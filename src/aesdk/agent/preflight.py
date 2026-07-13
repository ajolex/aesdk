"""Preflight validation for AI agents before code generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aesdk.agent.context import AgentContext, agent_context
from aesdk.data.probe import DataProfile, DataScanResult, scan_data
from aesdk.governance.pap import validate_pap_file
from aesdk.governance.policy import ConformanceLevel
from aesdk.protocol.validator import RuleViolation, Severity, ValidationResult, Validator


_METHOD_STRATEGY_ALIASES = {
    "ols_cef": {"OLS"},
    "iv_2sls": {"IV", "2SLS"},
    "panel_fe": {"FE", "TWFE", "POLS", "RE"},
    "did": {"DiD", "TWFE", "EventStudy"},
    "rdd": {"RDD"},
    "matching": {"Matching", "PropensityScore", "Mahalanobis", "EntropyBalance"},
    "experimental_rct": {"RCT", "RandomizedExperiment", "RandomizedControlledTrial", "ITT", "ATE", "ATT", "ToT", "LATE"},
    "synthetic_control": {"SynthControl", "SyntheticControl", "AugmentedSyntheticControl", "SyntheticDiD"},
    "nonlinear_did": {"NonlinearDiD", "PoissonDiD", "LogitDiD", "DRDID"},
    "gmm": {"GMM", "IVGMM", "DynamicPanelGMM"},
    "limited_dependent": {
        "Logit",
        "ConditionalLogit",
        "MixedLogit",
        "Probit",
        "Tobit",
        "Poisson",
        "NegativeBinomial",
        "OrderedLogit",
        "MultinomialLogit",
    },
    "time_series": {"ARIMA", "ARMAX", "VAR", "VECM", "ARDL", "HACRegression"},
    "mle": {"MLE", "QMLE"},
    "dml": {"DML", "DoubleML", "PLR", "PLIV", "IRM", "CausalForest"},
    "structural": {"BLP", "StructuralGMM", "StructuralMLE", "DiscreteChoiceDemand"},
    "nonparametric": {"KernelRegression", "LocalPolynomial", "SeriesEstimator", "LOESS"},
    "bayesian": {"BayesianRegression", "MCMC", "GibbsSampler", "BayesianVAR", "HierarchicalBayes"},
    "garch": {"ARCH", "GARCH", "EGARCH", "GJR-GARCH"},
}


@dataclass(frozen=True)
class PreflightResult:
    method_id: str
    context: AgentContext
    validation: ValidationResult | None = None
    pap_path: str | None = None
    proposal: dict[str, Any] | None = None
    data_scan: DataScanResult | None = None

    @property
    def status(self) -> str:
        return self.validation.status if self.validation else "context-only"

    @property
    def data_profile(self) -> DataProfile | None:
        return self.data_scan.profile if self.data_scan else None

    @property
    def data_scanned(self) -> bool:
        return bool(self.data_scan and self.data_scan.scanned)

    @property
    def blocked(self) -> bool:
        return bool(self.validation and self.validation.blocked)

    @property
    def warnings(self) -> list[RuleViolation]:
        if not self.validation:
            return []
        return [item for item in self.validation.violations if item.severity.value == "warning"]

    @property
    def violations(self) -> list[RuleViolation]:
        return self.validation.violations if self.validation else []

    def explain(self) -> str:
        if not self.validation:
            return "AESDK context loaded; no PAP/proposal validation was requested."
        if not self.validation.violations:
            return f"AESDK preflight status={self.validation.status}; no rule violations."
        lines = [f"AESDK preflight status={self.validation.status}."]
        if self.data_scanned:
            lines.append(f"Data scan: read {self.data_scan.profile.path}.")
        for violation in self.validation.violations:
            lines.append(f"- {violation.rule_id} severity={violation.severity.value}: {violation.message}")
            if violation.guidance:
                lines.append(f"  guidance: {violation.guidance}")
        return "\n".join(lines)

    def agent_context_markdown(self) -> str:
        return self.context.to_markdown()

    def to_dict(self) -> dict[str, Any]:
        return {
            "method_id": self.method_id,
            "status": self.status,
            "blocked": self.blocked,
            "pap_path": self.pap_path,
            "proposal": self.proposal,
            "violations": [
                {
                    "rule_id": item.rule_id,
                    "rule_name": item.rule_name,
                    "severity": item.severity.value,
                    "message": item.message,
                    "guidance": item.guidance,
                    "citation": item.citation,
                    "source_file": item.source_file,
                }
                for item in self.violations
            ],
            "context": self.context.to_dict(),
            "data_scan": self.data_scan.to_dict() if self.data_scan else None,
        }


def _load_proposal(proposal: dict[str, Any] | str | Path | None) -> dict[str, Any]:
    if proposal is None:
        return {}
    if isinstance(proposal, dict):
        return proposal
    with Path(proposal).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _method_strategy_violation(method: str, pap: dict[str, Any], proposal: dict[str, Any]) -> RuleViolation | None:
    strategy = pap.get("identification", {}).get("strategy")
    allowed = _METHOD_STRATEGY_ALIASES.get(method)
    if not allowed:
        return None
    if strategy and strategy not in allowed:
        return RuleViolation(
            rule_id="AGENT-METHOD-001",
            rule_name="Requested Method Must Match PAP Strategy",
            severity=Severity.ERROR,
            message=(
                f"Agent requested method '{method}', but the PAP identification strategy is '{strategy}'. "
                "Load the matching method context or update the PAP with a documented researcher-approved change."
            ),
            guidance="Do not proceed with analysis code until the requested method and registered PAP strategy agree.",
            citation="AESDK agent preflight protocol",
            source_file="aesdk.agent.preflight",
        )
    estimator = proposal.get("estimator")
    if not estimator or estimator in allowed:
        return None
    did = pap.get("did_block", {})
    if method == "panel_fe" and estimator in _METHOD_STRATEGY_ALIASES["did"] and did:
        return RuleViolation(
            rule_id="AGENT-METHOD-001",
            rule_name="Requested Method Must Match Proposed Estimator",
            severity=Severity.ERROR,
            message=(
                f"Agent requested method '{method}', but the proposal estimator is '{estimator}' and the PAP "
                "contains a DiD block. This looks like a treatment-timing/event-study design, not a generic "
                "panel fixed-effects exercise."
            ),
            guidance="Use --method did for DiD, event-study, or staggered rollout tasks unless a researcher documents a non-causal panel FE objective.",
            citation="AESDK agent preflight protocol",
            source_file="aesdk.agent.preflight",
        )
    return RuleViolation(
        rule_id="AGENT-METHOD-001",
        rule_name="Requested Method Must Match Proposed Estimator",
        severity=Severity.ERROR,
        message=(
            f"Agent requested method '{method}', but the proposal estimator is '{estimator}'. "
            "Load the matching method context or update the PAP with a documented researcher-approved change."
        ),
        guidance="Do not proceed with analysis code until the requested method and proposed estimator agree.",
        citation="AESDK agent preflight protocol",
        source_file="aesdk.agent.preflight",
    )


def _status_from_violations(violations: list[RuleViolation]) -> str:
    if any(v.severity == Severity.ERROR for v in violations):
        return "block"
    if any(v.severity == Severity.WARNING for v in violations):
        return "warn"
    return "pass"


def preflight(
    *,
    method: str,
    pap_path: str | Path | None = None,
    proposal: dict[str, Any] | str | Path | None = None,
    conformance: str = "strict",
    scan_data_file: bool = True,
    data_path: str | Path | None = None,
) -> PreflightResult:
    """Load method context and optionally validate a PAP/proposal pair.

    When ``scan_data_file`` is true and the PAP declares a readable dataset (or
    ``data_path`` is provided), AESDK also reads the data and cross-checks the
    declared structure against it. A missing or unreadable dataset degrades
    gracefully: no data findings are produced and the declaration-only result
    is returned unchanged.
    """

    ctx = agent_context(method)
    loaded_proposal = _load_proposal(proposal)
    if pap_path is None:
        return PreflightResult(method_id=method, context=ctx, proposal=loaded_proposal)
    pap = validate_pap_file(pap_path)
    pap_parent = Path(pap_path).resolve().parent
    artifact_base_dirs = [Path.cwd(), pap_parent]
    artifact_base_dirs_by_source = {"pap": pap_parent}
    if isinstance(proposal, (str, Path)):
        proposal_parent = Path(proposal).resolve().parent
        artifact_base_dirs.append(proposal_parent)
        artifact_base_dirs_by_source["proposal"] = proposal_parent
    validation = Validator(
        artifact_base_dirs=artifact_base_dirs,
        artifact_base_dirs_by_source=artifact_base_dirs_by_source,
    ).validate(
        pap=pap,
        proposal=loaded_proposal,
        conformance=ConformanceLevel(conformance.lower()),
    )

    data_scan: DataScanResult | None = None
    if scan_data_file:
        data_scan = scan_data(
            method=method,
            pap=pap,
            proposal=loaded_proposal,
            data_path=data_path,
            base_dirs=artifact_base_dirs,
            conformance=conformance,
        )
        if data_scan.findings:
            merged = [*validation.violations, *data_scan.findings]
            validation = ValidationResult(status=_status_from_violations(merged), violations=merged)

    method_violation = _method_strategy_violation(method, pap, loaded_proposal)
    if method_violation:
        validation = ValidationResult(status="block", violations=[method_violation, *validation.violations])
    return PreflightResult(
        method_id=method,
        context=ctx,
        validation=validation,
        pap_path=str(pap_path),
        proposal=loaded_proposal,
        data_scan=data_scan,
    )
