"""Project orchestration and policy gating."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aesdk.core.errors import GovernanceBlockError, MissingPAPError
from aesdk.core.state_machine import ProjectStateMachine
from aesdk.governance.pap import validate_pap_file
from aesdk.protocol.validator import RuleRegistry, ValidationResult, Validator
from aesdk.sandbox.runner import SandboxResult, SandboxRunner
from aesdk.trace import events as trace_events
from aesdk.trace.blob import ReasoningLog, ReplicationBlob


@dataclass
class Project:
    pap_path: Path
    pap: dict[str, Any]
    blob_path: Path
    blob: ReplicationBlob
    validator: Validator
    sandbox_runner: SandboxRunner
    state_machine: ProjectStateMachine

    _last_proposal: dict[str, Any] | None = None
    _last_validation: ValidationResult | None = None

    @classmethod
    def create(
        cls,
        *,
        pap_path: str | Path,
        blob_path: str | Path | None = None,
        registry: RuleRegistry | None = None,
        blob: ReplicationBlob | None = None,
        sandbox_runner: SandboxRunner | None = None,
    ) -> "Project":
        pap_target = Path(pap_path)
        if not pap_target.exists():
            raise MissingPAPError(f"PAP is required and was not found: {pap_target}")
        pap = validate_pap_file(pap_target)
        project_id = pap.get("project", {}).get("id", pap_target.stem)
        blob_target = Path(blob_path or pap_target.parent / ".aesdk.json")
        active_blob = blob or ReplicationBlob(
            project_id=project_id,
            pap_path=pap_target,
            environment={"python": platform.python_version(), "platform": platform.platform()},
        )

        state_machine = ProjectStateMachine()
        state_machine.on_init()
        active_blob.record(
            "init",
            trace_events.init_payload(pap_path=str(pap_target), pap_hash=active_blob.pap_hash),
        )
        active_blob.save(blob_target)

        return cls(
            pap_path=pap_target,
            pap=pap,
            blob_path=blob_target,
            blob=active_blob,
            validator=Validator(registry=registry),
            sandbox_runner=sandbox_runner or SandboxRunner(),
            state_machine=state_machine,
        )

    def propose_model(
        self,
        proposal: dict[str, Any],
        *,
        seed: int = 0,
        temperature: float = 0.0,
        model: str = "unspecified",
    ) -> None:
        self.state_machine.on_propose()
        self._last_proposal = proposal
        self.blob.record(
            "propose_model",
            trace_events.proposal_payload(
                proposal=proposal,
                seed=seed,
                temperature=temperature,
                model=model,
            ),
        )
        self._flush()

    def validate(self, proposal: dict[str, Any] | None = None) -> ValidationResult:
        active_proposal = proposal or self._last_proposal
        if active_proposal is None:
            active_proposal = {}
            self.propose_model(active_proposal)

        result = self.validator.validate(self.pap, active_proposal)
        self._last_validation = result
        self.state_machine.on_validate(result.status)
        self.blob.record("validate", trace_events.validation_payload(result))
        self._flush()
        return result

    def execute(self, code: str, proposal: dict[str, Any] | None = None) -> SandboxResult:
        if proposal is not None:
            self.propose_model(proposal)
        if self._last_validation is None:
            self.validate(self._last_proposal or {})
        assert self._last_validation is not None
        if self._last_validation.blocked:
            raise GovernanceBlockError("Execution blocked by governance rules.")

        self.state_machine.on_execute()
        sandbox_result = self.sandbox_runner.run_python(code)
        self.blob.record(
            "execute",
            trace_events.execute_payload(
                status=sandbox_result.status,
                diagnostics=[item.to_dict() for item in sandbox_result.diagnostics],
            ),
        )
        self._flush()
        return sandbox_result

    def override(self, rule_ids: list[str], justification: str) -> None:
        self.state_machine.on_override()
        self.blob.record("override", trace_events.override_payload(rule_ids=rule_ids, justification=justification))
        self._flush()

    def code_change(self, *, path: str | Path, summary: str, reasoning_log: ReasoningLog) -> None:
        self.blob.record(
            "code_change",
            trace_events.code_change_payload(path=str(path), summary=summary),
            reasoning_log=reasoning_log,
        )
        self._flush()

    def _flush(self) -> None:
        self.blob.save(self.blob_path)
