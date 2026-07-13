"""Data-aware preflight probes.

AESDK's rule engine validates *declared* PAP/proposal metadata. It does not, on
its own, look at the dataset. That leaves a gap: an agent can declare
``staggered_adoption: false`` on genuinely staggered data, name an outcome
column that does not exist, or cluster standard errors on a variable with a
handful of clusters, and the declaration-only rules will pass it.

This module reads the declared dataset and derives a small set of
*structural facts*, then cross-checks them against the PAP/proposal
declarations. Each cross-check maps to a documented econometric failure mode.

Design principles:

* **Graceful degradation.** If the dataset cannot be located or read, no
  findings are produced and preflight behaves exactly as before. The probes
  never manufacture a block from a missing or unreadable file.
* **Conservative identification.** A declared variable name is only checked
  for existence when it looks like a plain column identifier, not a
  constructed expression (``i.year``, ``log(x)``, ``a*b``). This avoids false
  positives on regressors that are built inside the analysis code.
* **Advisory by default.** Only two contradictions gate a workflow: a missing
  core variable (the code would crash or silently mis-run) and a
  staggered-adoption mismatch (a known bias trap). The remaining checks are
  empirical-practice warnings that never escalate a passing workflow into a
  block.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aesdk.data.ols_diagnostics import OLSDiagnosticsReport, ols_assumption_report
from aesdk.governance.policy import ConformanceLevel
from aesdk.protocol.validator import (
    RuleViolation,
    Severity,
    _apply_conformance_to_severity,
    _normalized_standard_errors,
)

# Angrist & Pischke, *Mostly Harmless Econometrics* (2009), and Cameron & Miller
# (2015), "A Practitioner's Guide to Cluster-Robust Inference", both flag that
# cluster-robust asymptotics are unreliable with few clusters; ~42 is the widely
# cited rule-of-thumb boundary below which wild-cluster-bootstrap inference is
# recommended.
FEW_CLUSTERS_THRESHOLD = 42

# Fraction of missing values on a core variable above which listwise deletion
# (and, for experiments, differential attrition) becomes a first-order concern.
HIGH_MISSINGNESS_FRACTION = 0.20

# Guardrail on file size so a probe never tries to load an unreasonably large
# file into memory during a preflight. Larger files are skipped gracefully.
MAX_DATA_BYTES = 1_500_000_000

_PLAIN_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_BINARY_METHODS = {"did", "matching", "experimental_rct", "nonlinear_did"}


@dataclass
class DataProfile:
    """Structural facts derived from the dataset."""

    resolved: bool = False
    path: str | None = None
    reason_unresolved: str | None = None
    n_rows: int | None = None
    n_columns: int | None = None
    columns_present: dict[str, bool] = field(default_factory=dict)
    structure_inferred: str | None = None
    n_units: int | None = None
    n_periods: int | None = None
    balanced_panel: bool | None = None
    n_clusters: int | None = None
    n_singleton_clusters: int | None = None
    adoption_cohorts: int | None = None
    treatment_is_binary: bool | None = None
    treatment_non_absorbing: bool | None = None
    ols_assumptions: OLSDiagnosticsReport | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolved": self.resolved,
            "path": self.path,
            "reason_unresolved": self.reason_unresolved,
            "n_rows": self.n_rows,
            "n_columns": self.n_columns,
            "columns_present": self.columns_present,
            "structure_inferred": self.structure_inferred,
            "n_units": self.n_units,
            "n_periods": self.n_periods,
            "balanced_panel": self.balanced_panel,
            "n_clusters": self.n_clusters,
            "n_singleton_clusters": self.n_singleton_clusters,
            "adoption_cohorts": self.adoption_cohorts,
            "treatment_is_binary": self.treatment_is_binary,
            "treatment_non_absorbing": self.treatment_non_absorbing,
            "ols_assumptions": self.ols_assumptions.to_dict() if self.ols_assumptions else None,
        }


@dataclass
class DataScanResult:
    """Result of a data-aware preflight scan."""

    profile: DataProfile
    findings: list[RuleViolation] = field(default_factory=list)

    @property
    def scanned(self) -> bool:
        return self.profile.resolved

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanned": self.scanned,
            "profile": self.profile.to_dict(),
            "findings": [
                {
                    "rule_id": item.rule_id,
                    "rule_name": item.rule_name,
                    "severity": item.severity.value,
                    "message": item.message,
                    "guidance": item.guidance,
                    "citation": item.citation,
                    "source_file": item.source_file,
                }
                for item in self.findings
            ],
        }


def _is_plain_identifier(name: Any) -> bool:
    return isinstance(name, str) and bool(_PLAIN_IDENTIFIER.match(name.strip()))


def _first_str(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def resolve_data_path(
    pap: dict[str, Any],
    *,
    data_path: str | Path | None = None,
    base_dirs: list[Path] | None = None,
) -> Path | None:
    """Resolve the dataset location from an explicit path or ``data.source``.

    Returns ``None`` if nothing resolvable is declared or the file is absent.
    """

    base_dirs = base_dirs or [Path.cwd()]
    declared = data_path if data_path is not None else (pap.get("data", {}) or {}).get("source")
    if not declared:
        return None
    candidate = Path(str(declared))
    if candidate.is_absolute():
        return candidate if candidate.is_file() else None
    for base in base_dirs:
        resolved = base / candidate
        if resolved.is_file():
            return resolved
    return None


def _read_frame(path: Path):
    try:
        import pandas as pd
    except Exception:  # pragma: no cover - pandas is a hard dependency
        return None, "pandas is not available"
    try:
        if path.stat().st_size > MAX_DATA_BYTES:
            return None, "dataset exceeds the data-scan size limit"
    except OSError:
        return None, "dataset could not be stat'd"
    suffix = path.suffix.lower()
    try:
        if suffix in {".csv"}:
            return pd.read_csv(path), None
        if suffix in {".tsv", ".tab"}:
            return pd.read_csv(path, sep="\t"), None
        if suffix in {".dta"}:
            return pd.read_stata(path), None
        if suffix in {".parquet", ".pq"}:
            return pd.read_parquet(path), None
        if suffix in {".feather"}:
            return pd.read_feather(path), None
        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(path), None
        # Unknown extension: try CSV as a best effort.
        return pd.read_csv(path), None
    except Exception as exc:  # noqa: BLE001 - any read failure degrades gracefully
        return None, f"dataset could not be read ({type(exc).__name__})"


def _column_is_binary(series) -> bool:
    values = series.dropna().unique()
    if len(values) == 0 or len(values) > 2:
        return False
    allowed = {0, 1, 0.0, 1.0, True, False}
    try:
        return all(value in allowed for value in values)
    except TypeError:
        return False


def _finding(
    rule_id: str,
    rule_name: str,
    severity: Severity,
    message: str,
    guidance: str,
    citation: str,
    *,
    conformance: ConformanceLevel,
    escalates: bool,
) -> RuleViolation:
    effective = _apply_conformance_to_severity(
        severity,
        conformance,
        {"strict_escalates": escalates} if severity == Severity.WARNING else None,
    )
    return RuleViolation(
        rule_id=rule_id,
        rule_name=rule_name,
        severity=effective,
        message=message,
        guidance=guidance,
        citation=citation,
        source_file="aesdk.data.probe",
    )


def _extract_fields(pap: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    identification = pap.get("identification", {}) or {}
    data = pap.get("data", {}) or {}
    did = pap.get("did_block", {}) or {}
    iv = pap.get("iv_block", {}) or {}
    rdd = {**(pap.get("rdd_block", {}) or {}), **(proposal.get("rdd_block", {}) or {})}
    rct = {**(pap.get("rct_block", {}) or {}), **(proposal.get("rct_block", {}) or {})}
    covariates = identification.get("covariates", {}) or {}
    return {
        "outcome": _first_str(proposal.get("outcome_variable"), identification.get("outcome_variable")),
        "treatment": _first_str(proposal.get("treatment_variable"), identification.get("treatment_variable")),
        "unit": _first_str(data.get("unit")),
        "time": _first_str(data.get("time"), data.get("time_index"), proposal.get("time")),
        "clustering": _first_str(proposal.get("clustering"), identification.get("clustering")),
        "standard_errors": _normalized_standard_errors(
            proposal.get("standard_errors", identification.get("standard_errors"))
        ),
        "declared_structure": _first_str(data.get("structure")),
        "mandatory_covariates": [c for c in (covariates.get("mandatory") or []) if isinstance(c, str)],
        "instruments": [c for c in (iv.get("instruments") or []) if isinstance(c, str)],
        "running_variable": _first_str(rdd.get("running_variable")),
        "assignment_variable": _first_str(rct.get("assignment_variable")),
        "staggered_declared": did.get("staggered_adoption"),
    }


def scan_data(
    *,
    method: str,
    pap: dict[str, Any],
    proposal: dict[str, Any] | None = None,
    data_path: str | Path | None = None,
    base_dirs: list[str | Path] | None = None,
    conformance: str | ConformanceLevel = ConformanceLevel.STRICT,
) -> DataScanResult:
    """Read the declared dataset and cross-check it against the PAP/proposal.

    All failures to locate or read the dataset degrade to an empty, non-blocking
    result. Findings are returned as :class:`RuleViolation` objects so they can
    be merged directly into a preflight :class:`ValidationResult`.
    """

    proposal = proposal or {}
    conformance_enum = (
        conformance
        if isinstance(conformance, ConformanceLevel)
        else ConformanceLevel(str(conformance).lower())
    )
    resolved_bases = [Path(b) for b in (base_dirs or [Path.cwd()])]
    profile = DataProfile()

    path = resolve_data_path(pap, data_path=data_path, base_dirs=resolved_bases)
    if path is None:
        profile.reason_unresolved = "no readable dataset was declared or found"
        return DataScanResult(profile=profile)

    profile.path = str(path)
    frame, reason = _read_frame(path)
    if frame is None:
        profile.reason_unresolved = reason
        return DataScanResult(profile=profile)

    profile.resolved = True
    profile.n_rows = int(frame.shape[0])
    profile.n_columns = int(frame.shape[1])
    columns = set(map(str, frame.columns))
    fields = _extract_fields(pap, proposal)
    findings: list[RuleViolation] = []

    def present(name: str | None) -> bool | None:
        if not _is_plain_identifier(name):
            return None
        return name in columns

    # -- 1. Core-variable existence -----------------------------------------
    core_specs = [
        ("outcome_variable", fields["outcome"], Severity.ERROR, True),
        ("treatment_variable", fields["treatment"], Severity.ERROR, True),
        ("unit", fields["unit"], Severity.WARNING, True),
        ("time", fields["time"], Severity.WARNING, True),
        ("running_variable", fields["running_variable"], Severity.WARNING, True),
        ("assignment_variable", fields["assignment_variable"], Severity.WARNING, True),
    ]
    for label, name, severity, escalates in core_specs:
        found = present(name)
        if name and _is_plain_identifier(name):
            profile.columns_present[name] = bool(found)
        if found is False:
            findings.append(
                _finding(
                    "DATA-VARS-001",
                    "Declared Variable Must Exist In The Dataset",
                    severity,
                    f"The declared {label} '{name}' is not a column in the dataset "
                    f"({path.name}). Available columns include: "
                    f"{', '.join(sorted(columns)[:12])}"
                    + ("..." if len(columns) > 12 else "")
                    + ".",
                    "Fix the variable name in the PAP/proposal or confirm the correct dataset "
                    "before writing analysis code. A misnamed core variable causes a crash or a "
                    "silently wrong estimate.",
                    "AESDK data-aware preflight",
                    conformance=conformance_enum,
                    escalates=escalates,
                )
            )

    for name in fields["instruments"]:
        if present(name) is False:
            findings.append(
                _finding(
                    "DATA-VARS-002",
                    "Declared Instrument Must Exist In The Dataset",
                    Severity.WARNING,
                    f"The declared instrument '{name}' is not a column in the dataset ({path.name}).",
                    "Confirm the instrument name or dataset before estimating the first stage.",
                    "AESDK data-aware preflight",
                    conformance=conformance_enum,
                    escalates=True,
                )
            )

    for name in fields["mandatory_covariates"]:
        if present(name) is False:
            findings.append(
                _finding(
                    "DATA-VARS-003",
                    "Declared Mandatory Covariate Not Found As A Column",
                    Severity.WARNING,
                    f"The mandatory covariate '{name}' is not a raw column in the dataset "
                    f"({path.name}). If it is constructed in code, document that; otherwise "
                    "the name may be wrong.",
                    "Confirm whether the covariate is a raw column or built during analysis.",
                    "AESDK data-aware preflight",
                    conformance=conformance_enum,
                    escalates=False,
                )
            )

    unit = fields["unit"] if present(fields["unit"]) else None
    time = fields["time"] if present(fields["time"]) else None
    treatment = fields["treatment"] if present(fields["treatment"]) else None
    outcome = fields["outcome"] if present(fields["outcome"]) else None
    cluster = fields["clustering"] if present(fields["clustering"]) else None

    # -- 2. Panel structure --------------------------------------------------
    if unit is not None:
        profile.n_units = int(frame[unit].nunique(dropna=True))
    if time is not None:
        profile.n_periods = int(frame[time].nunique(dropna=True))
    if unit is not None and time is not None:
        if profile.n_units and profile.n_periods:
            profile.structure_inferred = "panel" if profile.n_periods > 1 else "cross-section"
            per_unit_periods = frame.groupby(unit)[time].nunique(dropna=True)
            profile.balanced_panel = bool(per_unit_periods.nunique() == 1)

    # -- 3. Treatment cardinality -------------------------------------------
    if treatment is not None:
        profile.treatment_is_binary = _column_is_binary(frame[treatment])
        if profile.treatment_is_binary is False and method in _BINARY_METHODS:
            n_distinct = int(frame[treatment].dropna().nunique())
            findings.append(
                _finding(
                    "DATA-TREAT-001",
                    "Treatment Is Not Binary For A Binary-Treatment Method",
                    Severity.INFO,
                    f"The treatment '{treatment}' takes {n_distinct} distinct values, which is not "
                    f"a simple 0/1 indicator, but method '{method}' typically targets a binary "
                    "treatment estimand.",
                    "Confirm whether this is a multi-arm, dose, or intensity treatment and that the "
                    "estimand and estimator match. A non-binary treatment changes what the estimate means.",
                    "AESDK data-aware preflight",
                    conformance=conformance_enum,
                    escalates=False,
                )
            )

    # -- 4. Staggered adoption (DiD) ----------------------------------------
    if (
        method == "did"
        and unit is not None
        and time is not None
        and treatment is not None
        and profile.treatment_is_binary
    ):
        treated_rows = frame[frame[treatment] == 1]
        if not treated_rows.empty:
            first_treated = treated_rows.groupby(unit)[time].min()
            cohorts = int(first_treated.nunique())
            profile.adoption_cohorts = cohorts
            declared = fields["staggered_declared"]
            if cohorts > 1 and declared is not True:
                findings.append(
                    _finding(
                        "DATA-DID-001",
                        "Data Show Staggered Adoption Not Declared In The PAP",
                        Severity.WARNING,
                        f"The data show {cohorts} distinct treatment-adoption cohorts (staggered "
                        f"adoption), but did_block.staggered_adoption is "
                        f"{'false' if declared is False else 'not set'}. Plain two-way fixed "
                        "effects can be biased here through negative weighting of already-treated "
                        "comparisons.",
                        "Set staggered_adoption: true and use a heterogeneity-robust estimator "
                        "(Callaway-Sant'Anna, Sun-Abraham, or stacked DiD), or register a "
                        "documented decomposition before interpreting TWFE causally.",
                        "Goodman-Bacon (2021); Callaway & Sant'Anna (2021)",
                        conformance=conformance_enum,
                        escalates=True,
                    )
                )
            elif cohorts == 1 and declared is True:
                findings.append(
                    _finding(
                        "DATA-DID-002",
                        "PAP Declares Staggered Adoption But Data Show One Cohort",
                        Severity.INFO,
                        "did_block.staggered_adoption is true, but the data show a single "
                        "treatment-adoption cohort. A common-timing DiD/event-study estimator is "
                        "sufficient here.",
                        "Confirm the timing design; a single adoption cohort does not require "
                        "staggered-adoption estimators.",
                        "Callaway & Sant'Anna (2021)",
                        conformance=conformance_enum,
                        escalates=False,
                    )
                )

    # -- 4b. Non-absorbing treatment (turns on and off) ---------------------
    if (
        method in {"did", "nonlinear_did"}
        and unit is not None
        and time is not None
        and treatment is not None
        and profile.treatment_is_binary
    ):
        ordered = frame[[unit, time, treatment]].dropna().sort_values([unit, time])
        deltas = ordered.groupby(unit)[treatment].diff()
        turns_off = bool((deltas < 0).any())
        profile.treatment_non_absorbing = turns_off
        if turns_off:
            findings.append(
                _finding(
                    "DATA-DID-003",
                    "Treatment Turns Off (Non-Absorbing Treatment)",
                    Severity.WARNING,
                    "The treatment switches from 1 back to 0 for at least one unit, so this is a "
                    "non-absorbing (switching) treatment, not a staggered absorbing rollout. Most "
                    "staggered-DiD estimators assume treatment, once adopted, stays on.",
                    "Use an estimator built for treatments that turn on and off "
                    "(de Chaisemartin & D'Haultfoeuille 2020/2024), and state any no-carryover "
                    "assumption, rather than a standard absorbing-treatment DiD estimator.",
                    "de Chaisemartin & D'Haultfoeuille (2020); Roth, Sant'Anna, Bilinski & Poe (2023)",
                    conformance=conformance_enum,
                    escalates=False,
                )
            )

    # -- 5. Cluster structure ------------------------------------------------
    se_text = str(fields["standard_errors"] or "").lower()
    cluster_declared = bool(fields["clustering"]) or "cluster" in se_text
    # Wild-cluster-bootstrap is the recommended few-clusters remedy; do not warn
    # when it is already the declared inference method.
    few_clusters_remedy_used = "wild" in se_text and "cluster" in se_text
    if cluster is not None:
        sizes = frame.groupby(cluster).size()
        profile.n_clusters = int(len(sizes))
        n_singletons = int((sizes == 1).sum())
        profile.n_singleton_clusters = n_singletons
        if cluster_declared and not few_clusters_remedy_used and profile.n_clusters < FEW_CLUSTERS_THRESHOLD:
            findings.append(
                _finding(
                    "DATA-CLUST-001",
                    "Few Clusters For Cluster-Robust Inference",
                    Severity.WARNING,
                    f"Clustering on '{cluster}' yields {profile.n_clusters} clusters, below the "
                    f"~{FEW_CLUSTERS_THRESHOLD}-cluster rule of thumb. Cluster-robust standard "
                    "errors can be too small (over-rejection) with few clusters.",
                    "Use wild-cluster-bootstrap inference (or another few-clusters remedy) and "
                    "report the number of clusters.",
                    "Cameron & Miller (2015); Angrist & Pischke (2009)",
                    conformance=conformance_enum,
                    escalates=False,
                )
            )
        if n_singletons > 0:
            findings.append(
                _finding(
                    "DATA-CLUST-002",
                    "Singleton Clusters Present",
                    Severity.WARNING,
                    f"{n_singletons} of {profile.n_clusters} clusters on '{cluster}' contain a "
                    "single observation. Singleton clusters do not contribute to cluster-robust "
                    "variance and can distort inference and fixed-effects degrees of freedom.",
                    "Report how singleton clusters are handled (dropped or retained) and confirm "
                    "the clustering level is appropriate.",
                    "Correia (2015); Cameron & Miller (2015)",
                    conformance=conformance_enum,
                    escalates=False,
                )
            )

    # -- 6. Missingness on core variables -----------------------------------
    for label, name in [("outcome", outcome), ("treatment", treatment)]:
        if name is None:
            continue
        frac = float(frame[name].isna().mean())
        if frac > HIGH_MISSINGNESS_FRACTION:
            findings.append(
                _finding(
                    "DATA-MISS-001",
                    "High Missingness On A Core Variable",
                    Severity.WARNING,
                    f"The {label} '{name}' is missing for {frac:.0%} of rows. Listwise deletion "
                    "may drop a large, possibly non-random, share of the sample.",
                    "Report the missingness, check whether it is differential across treatment, and "
                    "state the sample-construction rule. For experiments, assess attrition.",
                    "Angrist & Pischke (2009), attrition and missing data",
                    conformance=conformance_enum,
                    escalates=False,
                )
            )

    # -- 7. Zero-variance declared regressors -------------------------------
    variance_targets = [("outcome", outcome), ("treatment", treatment)]
    variance_targets += [("covariate", c) for c in fields["mandatory_covariates"] if present(c)]
    for label, name in variance_targets:
        if name is None:
            continue
        if int(frame[name].dropna().nunique()) <= 1:
            findings.append(
                _finding(
                    "DATA-COLLIN-001",
                    "Declared Variable Has No Variation",
                    Severity.WARNING,
                    f"The {label} '{name}' takes a single value (no variation) in the dataset. "
                    "A constant regressor is collinear with the intercept and a constant outcome "
                    "or treatment is not estimable.",
                    "Confirm the variable and the estimation sample; a no-variation column signals "
                    "a data or filtering error.",
                    "AESDK data-aware preflight",
                    conformance=conformance_enum,
                    escalates=False,
                )
            )

    # -- 8. OLS assumption battery (Wooldridge MLR.1-6 + Ch. 8/9/12) --------
    if method == "ols_cef" and outcome is not None:
        regressors = [r for r in [treatment, *fields["mandatory_covariates"]] if r]
        report = ols_assumption_report(
            frame,
            outcome=outcome,
            regressors=regressors,
            structure=fields["declared_structure"],
            standard_errors=fields["standard_errors"],
        )
        profile.ols_assumptions = report
        findings.extend(
            _ols_findings(report, path.name, conformance_enum)
        )

    return DataScanResult(profile=profile, findings=findings)


def _ols_findings(
    report: OLSDiagnosticsReport,
    data_name: str,
    conformance: ConformanceLevel,
) -> list[RuleViolation]:
    findings: list[RuleViolation] = []
    if not report.fitted:
        return findings
    for check in report.checks:
        if check.status == "fail":
            severity = Severity.ERROR
        elif check.status == "warn":
            severity = Severity.WARNING
        else:
            continue
        findings.append(
            _finding(
                f"DATA-OLS-{check.key}",
                f"OLS Assumption ({check.wooldridge}): {check.name}",
                severity,
                f"{check.detail} [Wooldridge {check.wooldridge}; dataset {data_name}]",
                "Review this OLS assumption before interpreting the coefficients or their standard errors.",
                f"Wooldridge, Introductory Econometrics ({check.wooldridge})",
                conformance=conformance,
                escalates=False,
            )
        )
    return findings
