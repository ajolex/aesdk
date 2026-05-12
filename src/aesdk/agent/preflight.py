"""Preflight validation for AI agents before code generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aesdk.agent.context import AgentContext, agent_context
from aesdk.governance.pap import validate_pap_file
from aesdk.governance.policy import ConformanceLevel
from aesdk.protocol.validator import RuleViolation, ValidationResult, Validator


@dataclass(frozen=True)
class PreflightResult:
    method_id: str
    context: AgentContext
    validation: ValidationResult | None = None
    pap_path: str | None = None
    proposal: dict[str, Any] | None = None

    @property
    def status(self) -> str:
        return self.validation.status if self.validation else "context-only"

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
        }


def _load_proposal(proposal: dict[str, Any] | str | Path | None) -> dict[str, Any]:
    if proposal is None:
        return {}
    if isinstance(proposal, dict):
        return proposal
    with Path(proposal).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def preflight(
    *,
    method: str,
    pap_path: str | Path | None = None,
    proposal: dict[str, Any] | str | Path | None = None,
    conformance: str = "strict",
) -> PreflightResult:
    """Load method context and optionally validate a PAP/proposal pair."""

    ctx = agent_context(method)
    loaded_proposal = _load_proposal(proposal)
    if pap_path is None:
        return PreflightResult(method_id=method, context=ctx, proposal=loaded_proposal)
    pap = validate_pap_file(pap_path)
    validation = Validator().validate(
        pap=pap,
        proposal=loaded_proposal,
        conformance=ConformanceLevel(conformance.lower()),
    )
    return PreflightResult(
        method_id=method,
        context=ctx,
        validation=validation,
        pap_path=str(pap_path),
        proposal=loaded_proposal,
    )
