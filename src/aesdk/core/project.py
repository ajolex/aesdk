"""Project orchestration and policy gating."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aesdk.config import config
from aesdk.core.attestation import AttestationProvider, EndpointAttestationProvider, NoopAttestationProvider
from aesdk.core.errors import GovernanceBlockError, MissingPAPError
from aesdk.core.state_machine import ProjectStateMachine
from aesdk.governance.pap import validate_pap_file
from aesdk.governance.policy import compute_rulepack_hash, resolve_profile
from aesdk.protocol.validator import RuleRegistry, ValidationResult, Validator
from aesdk.sandbox.runner import SandboxResult, SandboxRunner, normalize_language
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
    governance_passport: dict[str, Any]

    _last_proposal: dict[str, Any] | None = None
    _last_validation: ValidationResult | None = None

    @classmethod
    def create(
        cls,
        *,
        pap_path: str | Path,
        proposal_path: str | Path | None = None,
        blob_path: str | Path | None = None,
        registry: RuleRegistry | None = None,
        blob: ReplicationBlob | None = None,
        sandbox_runner: SandboxRunner | None = None,
        context: str = "research",
        conformance: str | None = None,
        policy_version: str = "1.0.0",
        attestor: AttestationProvider | None = None,
        attestation_endpoint: str | None = None,
        attestation_token: str | None = None,
    ) -> "Project":
        pap_target = Path(pap_path)
        proposal_target = Path(proposal_path) if proposal_path else None
        if not pap_target.exists():
            raise MissingPAPError(f"PAP is required and was not found: {pap_target}")
        pap = validate_pap_file(pap_target)
        project_id = pap.get("project", {}).get("id", pap_target.stem)

        active_registry = registry or RuleRegistry()
        profile = resolve_profile(context=context, conformance=conformance)
        rulepack_hash = compute_rulepack_hash(active_registry.rules_dir)

        passport = {
            "policy_version": policy_version,
            "policy_profile": profile.name,
            "execution_context": profile.context.value,
            "conformance_level": profile.conformance.value,
            "rulepack_hash": rulepack_hash,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        active_attestor: AttestationProvider
        if attestor is not None:
            active_attestor = attestor
        elif attestation_endpoint:
            active_attestor = EndpointAttestationProvider(attestation_endpoint, token=attestation_token)
        else:
            active_attestor = NoopAttestationProvider()

        evidence = active_attestor.attest(passport)
        passport["attestation"] = {
            "provider": evidence.provider,
            "statement": evidence.statement,
            "timestamp": evidence.timestamp,
            "details": evidence.details,
        }

        blob_target = Path(blob_path or pap_target.parent / ".aesdk.json")
        active_blob = blob or ReplicationBlob(
            project_id=project_id,
            pap_path=pap_target,
            environment={"python": platform.python_version(), "platform": platform.platform()},
            metadata={"governance_passport": passport},
        )

        state_machine = ProjectStateMachine()
        state_machine.on_init()
        active_blob.record(
            "init",
            trace_events.init_payload(
                pap_path=str(pap_target),
                pap_hash=active_blob.pap_hash,
                governance_passport=passport,
            ),
        )
        active_blob.save(blob_target)
        artifact_base_dirs = [Path.cwd(), pap_target.resolve().parent]
        artifact_base_dirs_by_source = {"pap": pap_target.resolve().parent}
        if proposal_target:
            artifact_base_dirs.append(proposal_target.resolve().parent)
            artifact_base_dirs_by_source["proposal"] = proposal_target.resolve().parent

        return cls(
            pap_path=pap_target,
            pap=pap,
            blob_path=blob_target,
            blob=active_blob,
            validator=Validator(
                registry=active_registry,
                artifact_base_dirs=artifact_base_dirs,
                artifact_base_dirs_by_source=artifact_base_dirs_by_source,
            ),
            sandbox_runner=sandbox_runner
            or SandboxRunner(
                mem_limit_mb=config.sandbox_mem_limit_mb,
                cpu_limit_sec=config.sandbox_cpu_limit_sec,
                artifact_dir=blob_target.parent,
            ),
            state_machine=state_machine,
            governance_passport=passport,
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

        result = self.validator.validate(
            self.pap,
            active_proposal,
            conformance=resolve_profile(
                context=self.governance_passport["execution_context"],
                conformance=self.governance_passport["conformance_level"],
            ).conformance,
        )
        self._last_validation = result
        self.state_machine.on_validate(result.status)
        self.blob.record("validate", trace_events.validation_payload(result))
        self._flush()
        return result

    def execute(
        self,
        code: str,
        proposal: dict[str, Any] | None = None,
        *,
        language: str = "python",
        timeout_seconds: int | None = None,
    ) -> SandboxResult:
        if proposal is not None:
            self.propose_model(proposal)
        if self._last_validation is None:
            self.validate(self._last_proposal or {})
        assert self._last_validation is not None
        if self._last_validation.blocked:
            raise GovernanceBlockError("Execution blocked by governance rules.")

        self.state_machine.on_execute()
        active_language = normalize_language(language)
        sandbox_result = self.sandbox_runner.run(code, language=active_language, timeout_seconds=timeout_seconds)
        self.blob.record(
            "execute",
            trace_events.execute_payload(
                code=code,
                status=sandbox_result.status,
                diagnostics=[item.to_dict() for item in sandbox_result.diagnostics],
                language=active_language,
                timeout_seconds=timeout_seconds,
                artifacts=sandbox_result.artifacts,
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
