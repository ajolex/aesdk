"""Agent-friendly gated analysis execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aesdk.agent.preflight import PreflightResult, preflight
from aesdk.core.project import Project
from aesdk.sandbox.runner import SandboxResult, infer_language_from_path, normalize_language


@dataclass(frozen=True)
class AnalysisRunResult:
    preflight: PreflightResult
    sandbox: SandboxResult | None
    blob_path: str | None

    @property
    def blocked(self) -> bool:
        return self.preflight.blocked

    @property
    def status(self) -> str:
        if self.blocked:
            return "block"
        return self.sandbox.status if self.sandbox else self.preflight.status


def run_analysis(
    *,
    method: str,
    pap_path: str | Path,
    proposal: dict[str, Any] | str | Path,
    code: str | None = None,
    code_path: str | Path | None = None,
    language: str | None = None,
    blob_path: str | Path | None = None,
    context: str = "production",
    conformance: str = "strict",
    policy_version: str = "1.0.0",
) -> AnalysisRunResult:
    """Run preflight, then execute analysis code only if governance passes."""

    gate = preflight(method=method, pap_path=pap_path, proposal=proposal, conformance=conformance)
    if gate.blocked:
        return AnalysisRunResult(preflight=gate, sandbox=None, blob_path=str(blob_path) if blob_path else None)
    active_code = code
    if active_code is None and code_path is not None:
        active_code = Path(code_path).read_text(encoding="utf-8-sig")
    if active_code is None:
        return AnalysisRunResult(preflight=gate, sandbox=None, blob_path=str(blob_path) if blob_path else None)
    active_language = normalize_language(language) if language else infer_language_from_path(code_path)

    project = Project.create(
        pap_path=pap_path,
        blob_path=blob_path,
        context=context,
        conformance=conformance,
        policy_version=policy_version,
    )
    project.propose_model(gate.proposal or {})
    validation = project.validate()
    if validation.blocked:
        return AnalysisRunResult(
            preflight=PreflightResult(
                method_id=gate.method_id,
                context=gate.context,
                validation=validation,
                pap_path=str(pap_path),
                proposal=gate.proposal,
            ),
            sandbox=None,
            blob_path=str(project.blob_path),
        )
    sandbox = project.execute(active_code, language=active_language)
    return AnalysisRunResult(preflight=gate, sandbox=sandbox, blob_path=str(project.blob_path))
