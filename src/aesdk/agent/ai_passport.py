"""AI-use reproducibility passport helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from aesdk.governance.policy import compute_rulepack_hash
from aesdk.protocol.validator import DEFAULT_RULES_DIR, Validator


@dataclass(frozen=True)
class AIPassportResult:
    path: Path
    passport: dict[str, Any]
    summary_path: Path | None = None

    @property
    def status(self) -> str:
        return str(self.passport.get("status", "unknown"))

    @property
    def blocked(self) -> bool:
        return self.status == "block"


def write_ai_passport(
    *,
    pap_path: str | Path,
    proposal_path: str | Path | None = None,
    output_path: str | Path | None = None,
    summary_output_path: str | Path | None = None,
) -> AIPassportResult:
    """Write an ai.lock.json-style passport from PAP/proposal AI-use metadata."""

    pap_target = Path(pap_path)
    proposal_target = Path(proposal_path) if proposal_path else None
    pap = _load_structured(pap_target)
    proposal = _load_structured(proposal_target) if proposal_target else {}

    output = Path(output_path) if output_path else pap_target.parent / "ai.lock.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    passport = build_ai_passport(
        pap=pap,
        pap_path=pap_target,
        proposal=proposal,
        proposal_path=proposal_target,
    )
    output.write_text(json.dumps(passport, indent=2), encoding="utf-8")
    summary_output = Path(summary_output_path) if summary_output_path else None
    if summary_output is not None:
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(json.dumps(build_ai_passport_summary(passport), indent=2), encoding="utf-8")
    return AIPassportResult(path=output, passport=passport, summary_path=summary_output)


def build_ai_passport(
    *,
    pap: dict[str, Any] | None = None,
    pap_path: str | Path | None = None,
    proposal: dict[str, Any] | None = None,
    proposal_path: str | Path | None = None,
    ai_use: dict[str, Any] | None = None,
    base_dir: str | Path = ".",
) -> dict[str, Any]:
    """Build a reproducibility passport for AI-assisted research artifacts."""

    active_pap = pap or {}
    active_proposal = proposal or {}
    if ai_use is not None:
        merged = dict(ai_use)
        provenance = {key: "direct" for key in merged}
        base_dirs = {"direct": Path(base_dir)}
    else:
        merged, provenance, base_dirs = _merged_ai_use_with_provenance(
            active_pap,
            active_proposal,
            pap_path=Path(pap_path) if pap_path else None,
            proposal_path=Path(proposal_path) if proposal_path else None,
        )

    prompt_files = _file_records(_base_for("prompt_files", provenance, base_dirs), merged.get("prompt_files", []))
    output_files = _file_records(_base_for("output_files", provenance, base_dirs), merged.get("output_files", []))
    input_files = _file_records(_base_for("input_files", provenance, base_dirs), merged.get("input_files", []))
    ai_code_draft_files = _file_records(_base_for("ai_code_draft_files", provenance, base_dirs), merged.get("ai_code_draft_files", []))
    code_files = _file_records(_base_for("code_files", provenance, base_dirs), merged.get("code_files", []))
    human_interaction_files = _file_records(
        _base_for("human_interaction_files", provenance, base_dirs),
        merged.get("human_interaction_files", []),
    )
    human_intervention_files = _file_records(
        _base_for("human_intervention_files", provenance, base_dirs),
        merged.get("human_intervention_files", []),
    )
    review_files = _file_records(_base_for("review_files", provenance, base_dirs), merged.get("review_files", []))
    runtime_metadata_files = _file_records(
        _base_for("runtime_metadata_files", provenance, base_dirs),
        merged.get("runtime_metadata_files", []),
    )
    runtime_metadata = _runtime_metadata_records(runtime_metadata_files)
    artifact_hashes = {
        "prompt_files": prompt_files,
        "output_files": output_files,
        "input_files": input_files,
        "ai_code_draft_files": ai_code_draft_files,
        "code_files": code_files,
        "human_interaction_files": human_interaction_files,
        "human_intervention_files": human_intervention_files,
        "review_files": review_files,
        "runtime_metadata_files": runtime_metadata_files,
    }
    findings = _passport_findings(
        merged,
        prompt_files,
        output_files,
        input_files,
        ai_code_draft_files,
        code_files,
        human_interaction_files,
        human_intervention_files,
        review_files,
        runtime_metadata_files,
        runtime_metadata,
    )
    validation_base_dirs = [Path.cwd(), *base_dirs.values()]
    validation = _validation_summary(active_pap, active_proposal, validation_base_dirs, base_dirs) if active_pap else None
    if validation and validation["status"] == "block":
        findings.append(
            {
                "severity": "error",
                "code": "VALIDATION_BLOCK",
                "message": "PAP/proposal validation is blocked; inspect validation.violations.",
            }
        )

    status = _status_from_findings(findings)
    evidence_summary = _passport_evidence_summary(
        merged,
        artifact_hashes,
        runtime_metadata,
        findings,
        validation,
        status,
    )
    improvement_opportunities = _passport_improvement_opportunities(
        merged,
        evidence_summary,
        findings,
        validation,
    )
    pap_target = Path(pap_path) if pap_path else None
    proposal_target = Path(proposal_path) if proposal_path else None
    return {
        "schema": "aesdk.ai_passport.v1",
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_documents": {
            "pap_path": str(pap_target) if pap_target else None,
            "pap_sha256": _sha256_file(pap_target),
            "proposal_path": str(proposal_target) if proposal_target else None,
            "proposal_sha256": _sha256_file(proposal_target),
            "rulepack_hash": compute_rulepack_hash(DEFAULT_RULES_DIR),
        },
        "field_provenance": provenance,
        "field_provenance_note": "Field provenance records which source document supplied each metadata field; it is not independent verification of the field value.",
        "ai_use": _public_ai_use(merged),
        "artifact_hashes": artifact_hashes,
        "runtime_metadata": runtime_metadata,
        "validation": validation,
        "findings": findings,
        "evidence_summary": evidence_summary,
        "improvement_opportunities": improvement_opportunities,
        "replication_statement": _replication_statement(merged, status),
    }


def build_ai_passport_summary(passport: dict[str, Any]) -> dict[str, Any]:
    """Return a compact reviewer-oriented JSON summary for an AI passport."""

    return {
        "schema": "aesdk.ai_passport_summary.v1",
        "passport_schema": passport.get("schema"),
        "status": passport.get("status"),
        "generated_at": passport.get("generated_at"),
        "source_documents": passport.get("source_documents", {}),
        "evidence_summary": passport.get("evidence_summary", {}),
        "improvement_opportunities": passport.get("improvement_opportunities", []),
        "findings": passport.get("findings", []),
        "validation": passport.get("validation"),
        "replication_statement": passport.get("replication_statement"),
    }


def _passport_evidence_summary(
    ai_use: dict[str, Any],
    artifact_hashes: dict[str, list[dict[str, Any]]],
    runtime_metadata: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    validation: dict[str, Any] | None,
    status: str,
) -> dict[str, Any]:
    runtime_summary = _runtime_metadata_summary(runtime_metadata)
    return {
        "artifact_type": "ai_passport",
        "status": status,
        "declared_ai_use": ai_use.get("used") is True,
        "roles": _as_list(ai_use.get("role", [])),
        "languages": _as_list(ai_use.get("languages", [])),
        "finding_counts": _severity_counts(findings),
        "validation_status": validation.get("status") if isinstance(validation, dict) else None,
        "validation_violation_count": len(validation.get("violations", [])) if isinstance(validation, dict) else None,
        "model_metadata": {
            "model": None if _text_missing(ai_use.get("model")) else ai_use.get("model"),
            "agent_tool": ai_use.get("agent_tool"),
            "source": ai_use.get("model_metadata_source"),
            "unavailable_reason_present": not _text_missing(ai_use.get("model_metadata_unavailable_reason")),
            "runtime_models": runtime_summary["models"],
            "runtime_unavailable_fields": runtime_summary["unavailable_session_fields"],
        },
        "human_review": {
            "human_in_loop": ai_use.get("human_in_loop") is True,
            "human_reviewed": ai_use.get("human_reviewed") is True,
            "review_status": ai_use.get("review_status"),
            "human_modified_code": ai_use.get("human_modified_code") is True,
        },
        "artifact_counts": {
            key: _artifact_record_summary(records)
            for key, records in artifact_hashes.items()
        },
        "runtime_metadata": runtime_summary,
        "replication_blob_note": "The AI passport is not the .aesdk.json replication blob; keep it alongside the blob produced by agent prepare or agent run.",
    }


def _passport_improvement_opportunities(
    ai_use: dict[str, Any],
    evidence_summary: dict[str, Any],
    findings: list[dict[str, Any]],
    validation: dict[str, Any] | None,
) -> list[dict[str, str]]:
    if ai_use.get("used") is not True:
        return []

    opportunities: list[dict[str, str]] = []
    if ai_use.get("human_reviewed") is not True:
        opportunities.append(
            {
                "severity": "info",
                "code": "HUMAN_REVIEW_NOT_DOCUMENTED",
                "message": "Passport evidence can pass without documented researcher review; add review_status and review_files once a human review is complete.",
            }
        )

    model_summary = evidence_summary.get("model_metadata", {})
    if ai_use.get("model_metadata_source") == "agent_unavailable":
        if model_summary.get("runtime_models") and _text_missing(ai_use.get("model")):
            opportunities.append(
                {
                    "severity": "info",
                    "code": "RUNTIME_MODEL_NEEDS_VERIFICATION",
                    "message": "Runtime metadata contains a session model, but the passport model field is still unavailable; copy it only if the researcher can verify the runtime snapshot is authoritative.",
                }
            )
        opportunities.append(
            {
                "severity": "info",
                "code": "AGENT_METADATA_LIMITED",
                "message": "Agent-unavailable model metadata is acceptable with a runtime snapshot, but it is weaker than provider API metadata or a reviewed session transcript.",
            }
        )

    unavailable_fields = model_summary.get("runtime_unavailable_fields") or []
    if unavailable_fields:
        opportunities.append(
            {
                "severity": "info",
                "code": "RUNTIME_METADATA_FIELDS_UNAVAILABLE",
                "message": "Some runtime fields were unavailable in the archived snapshot: " + ", ".join(str(item) for item in unavailable_fields) + ".",
            }
        )

    roles = set(_as_list(ai_use.get("role", [])))
    artifact_counts = evidence_summary.get("artifact_counts", {})
    if "code_generation" in roles and not artifact_counts.get("ai_code_draft_files", {}).get("declared", 0):
        opportunities.append(
            {
                "severity": "info",
                "code": "AI_CODE_DRAFT_NOT_ARCHIVED",
                "message": "For generated analysis code, archive the first AI draft separately when feasible so later human edits can be compared directly.",
            }
        )

    if "other" in roles and _text_missing(ai_use.get("notes")):
        opportunities.append(
            {
                "severity": "info",
                "code": "OTHER_AI_ROLE_NEEDS_NOTE",
                "message": "The role list includes other; describe the additional AI role in notes.",
            }
        )

    if isinstance(validation, dict) and validation.get("status") == "warn":
        opportunities.append(
            {
                "severity": "info",
                "code": "VALIDATION_WARNINGS_NEED_ACKNOWLEDGEMENT",
                "message": "PAP/proposal validation returned warnings; record researcher acknowledgement before treating the workflow as final.",
            }
        )

    if any(item.get("severity") == "warning" for item in findings):
        opportunities.append(
            {
                "severity": "info",
                "code": "PASSPORT_WARNINGS_PRESENT",
                "message": "The passport has warning findings; resolve or explicitly acknowledge them before archival.",
            }
        )

    return opportunities


def _artifact_record_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    missing = [str(record.get("original_path")) for record in records if not record.get("exists")]
    hashed = [record for record in records if record.get("exists") and record.get("sha256")]
    return {
        "declared": len(records),
        "existing": sum(1 for record in records if record.get("exists")),
        "hashed": len(hashed),
        "missing": len(missing),
        "missing_paths": missing,
    }


def _runtime_metadata_summary(runtime_metadata: list[dict[str, Any]]) -> dict[str, Any]:
    models: list[str] = []
    unavailable_fields: set[str] = set()
    parse_error_count = 0
    embedded_count = 0
    for item in runtime_metadata:
        if item.get("parse_error"):
            parse_error_count += 1
        if item.get("embedded") is True:
            embedded_count += 1
        metadata = item.get("metadata")
        if not isinstance(metadata, dict):
            continue
        session = metadata.get("session")
        if not isinstance(session, dict):
            continue
        model = session.get("model")
        if not _text_missing(model):
            models.append(str(model))
        for key, value in session.items():
            if key == "metadata_sources":
                continue
            if _text_missing(value):
                unavailable_fields.add(str(key))
        metadata_sources = session.get("metadata_sources")
        if isinstance(metadata_sources, dict):
            for key, value in metadata_sources.items():
                if _text_missing(value):
                    unavailable_fields.add(str(key))
    return {
        "declared": len(runtime_metadata),
        "embedded": embedded_count,
        "parse_error_count": parse_error_count,
        "models": sorted(set(models)),
        "unavailable_session_fields": sorted(unavailable_fields),
    }


def _severity_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for item in items:
        severity = str(item.get("severity", "info"))
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def _load_structured(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        loaded = json.loads(text)
    else:
        loaded = yaml.safe_load(text) or {}
    if not isinstance(loaded, dict):
        return {}
    return loaded


def _merged_ai_use_with_provenance(
    pap: dict[str, Any],
    proposal: dict[str, Any],
    *,
    pap_path: Path | None,
    proposal_path: Path | None,
) -> tuple[dict[str, Any], dict[str, str], dict[str, Path]]:
    merged: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    pap_ai = pap.get("ai_use", {})
    proposal_ai = proposal.get("ai_use", {})
    if isinstance(pap_ai, dict):
        for key, value in pap_ai.items():
            merged[key] = value
            provenance[key] = "pap"
    if isinstance(proposal_ai, dict):
        for key, value in proposal_ai.items():
            if value is not None:
                merged[key] = value
                provenance[key] = "proposal"
    base_dirs = {
        "pap": pap_path.parent if pap_path else Path("."),
        "proposal": proposal_path.parent if proposal_path else (pap_path.parent if pap_path else Path(".")),
        "direct": Path("."),
    }
    return merged, provenance, base_dirs


def _public_ai_use(ai_use: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "used",
        "role",
        "languages",
        "provider",
        "model",
        "model_version",
        "agent_tool",
        "agent_tool_version",
        "model_metadata_source",
        "model_metadata_unavailable_reason",
        "temperature",
        "top_p",
        "seed",
        "prompts_archived",
        "raw_outputs_archived",
        "human_in_loop",
        "human_interaction_files",
        "human_modified_code",
        "ai_code_draft_files",
        "human_intervention_files",
        "human_reviewed",
        "review_status",
        "reviewer_role",
        "review_date",
        "review_files",
        "runtime_metadata_files",
        "review_checklist",
        "reproducible_without_ai",
        "live_model_required",
        "ai_output_used_as_data",
        "ai_derived_variables",
        "code_files",
        "qa_sample_plan",
        "sensitivity_plan",
        "notes",
    ]
    return {key: ai_use.get(key) for key in fields if key in ai_use}


def _base_for(field: str, provenance: dict[str, str], base_dirs: dict[str, Path]) -> Path:
    return base_dirs.get(provenance.get(field, "direct"), Path("."))


def _file_records(base_dir: Path, values: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for value in _as_list(values):
        original = str(value)
        path = Path(original)
        if not path.is_absolute():
            path = base_dir / path
        record: dict[str, Any] = {
            "original_path": original,
            "resolved_path": str(path),
            "exists": path.exists(),
        }
        if path.exists() and path.is_file():
            record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            record["size_bytes"] = path.stat().st_size
        records.append(record)
    return records


_RUNTIME_METADATA_EMBED_LIMIT_BYTES = 128_000
_SENSITIVE_KEY_PARTS = ("token", "secret", "password", "credential", "api_key", "private_key")


def _runtime_metadata_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    embedded: list[dict[str, Any]] = []
    for record in records:
        item: dict[str, Any] = {
            "original_path": record.get("original_path"),
            "resolved_path": record.get("resolved_path"),
            "exists": record.get("exists", False),
            "sha256": record.get("sha256"),
        }
        path = Path(str(record.get("resolved_path", "")))
        if record.get("exists") and path.is_file():
            size_bytes = path.stat().st_size
            if size_bytes > _RUNTIME_METADATA_EMBED_LIMIT_BYTES:
                item["parse_error"] = f"runtime metadata file exceeds embed limit ({size_bytes} bytes)"
                item["embedded"] = False
                embedded.append(item)
                continue
            try:
                loaded = json.loads(path.read_text(encoding="utf-8-sig"))
            except Exception as exc:
                item["parse_error"] = str(exc)
            else:
                if not isinstance(loaded, dict):
                    item["parse_error"] = "runtime metadata JSON must be an object"
                else:
                    item["metadata"] = _curated_runtime_metadata(loaded)
                    item["embedded"] = True
        embedded.append(item)
    return embedded


def _curated_runtime_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Embed reviewer-useful runtime fields without copying arbitrary settings wholesale."""

    curated: dict[str, Any] = {}
    for key in [
        "schema",
        "codex_client",
        "claude_client",
        "vscode_version",
        "copilot_extensions",
        "surface",
        "date_time",
        "timezone",
        "metadata_block",
        "limitations",
    ]:
        if key in metadata:
            curated[key] = _redact_runtime_value(metadata[key])
    workspace = metadata.get("workspace")
    if isinstance(workspace, dict):
        curated["workspace"] = {
            key: _redact_runtime_value(workspace.get(key))
            for key in ["repo_name", "commit_sha"]
            if workspace.get(key) is not None
        }
    session = metadata.get("session")
    if isinstance(session, dict):
        curated["session"] = {
            key: _redact_runtime_value(session.get(key))
            for key in [
                "model",
                "reasoning_effort",
                "reasoning_summary",
                "verbosity",
                "approval_policy",
                "sandbox_mode",
                "metadata_sources",
            ]
            if key in session
        }
    return curated


def _redact_runtime_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: ("[redacted]" if any(part in str(key).lower() for part in _SENSITIVE_KEY_PARTS) else _redact_runtime_value(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_runtime_value(item) for item in value]
    return value


def _passport_findings(
    ai_use: dict[str, Any],
    prompt_files: list[dict[str, Any]],
    output_files: list[dict[str, Any]],
    input_files: list[dict[str, Any]],
    ai_code_draft_files: list[dict[str, Any]],
    code_files: list[dict[str, Any]],
    human_interaction_files: list[dict[str, Any]],
    human_intervention_files: list[dict[str, Any]],
    review_files: list[dict[str, Any]],
    runtime_metadata_files: list[dict[str, Any]],
    runtime_metadata: list[dict[str, Any]],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not ai_use:
        findings.append({"severity": "error", "code": "AI_USE_MISSING", "message": "No ai_use metadata found."})
        return findings
    if ai_use.get("used") is not True:
        return findings
    if ai_use.get("reproducible_without_ai") is not True or ai_use.get("live_model_required") is True:
        findings.append(
            {
                "severity": "error",
                "code": "LIVE_AI_DEPENDENCY",
                "message": "AI-assisted work must be reproducible without calling a live AI model.",
            }
        )
    if ai_use.get("prompts_archived") is not True:
        findings.append({"severity": "warning", "code": "PROMPTS_NOT_ARCHIVED", "message": "Prompts are not archived."})
    if ai_use.get("raw_outputs_archived") is not True:
        findings.append({"severity": "warning", "code": "OUTPUTS_NOT_ARCHIVED", "message": "Raw AI outputs are not archived."})
    if ai_use.get("prompts_archived") is True and not prompt_files:
        findings.append({"severity": "error", "code": "PROMPT_FILES_MISSING", "message": "prompt_files is empty."})
    if ai_use.get("raw_outputs_archived") is True and not output_files:
        findings.append({"severity": "error", "code": "OUTPUT_FILES_MISSING", "message": "output_files is empty."})
    if ai_use.get("human_in_loop") is True and not human_interaction_files:
        findings.append(
            {
                "severity": "error",
                "code": "HUMAN_INTERACTION_FILES_MISSING",
                "message": "human_in_loop is true but human_interaction_files is empty.",
            }
        )
    if ai_use.get("human_in_loop") is True and _has_blank_text_file(human_interaction_files):
        findings.append(
            {
                "severity": "error",
                "code": "HUMAN_INTERACTION_FILE_BLANK",
                "message": "human_in_loop is true but an interaction evidence file is blank.",
            }
        )
    if ai_use.get("human_modified_code") is True:
        if not human_intervention_files:
            findings.append(
                {
                    "severity": "error",
                    "code": "HUMAN_INTERVENTION_FILES_MISSING",
                    "message": "human_modified_code is true but human_intervention_files is empty.",
                }
            )
        if _has_blank_text_file(human_intervention_files):
            findings.append(
                {
                    "severity": "error",
                    "code": "HUMAN_INTERVENTION_FILE_BLANK",
                    "message": "human_modified_code is true but an intervention evidence file is blank.",
                }
            )
        if not ai_code_draft_files:
            findings.append(
                {
                    "severity": "error",
                    "code": "AI_CODE_DRAFT_FILES_MISSING",
                    "message": "human_modified_code is true but ai_code_draft_files is empty.",
                }
            )
        if _has_no_change_intervention_file(human_intervention_files):
            findings.append(
                {
                    "severity": "error",
                    "code": "HUMAN_INTERVENTION_NO_CODE_CHANGE",
                    "message": "human_modified_code is true but an intervention diff records no textual code changes.",
                }
            )
    if _looks_like_agent_tool_model(ai_use.get("model")):
        findings.append(
            {
                "severity": "error",
                "code": "MODEL_FIELD_IS_AGENT_TOOL",
                "message": "The model field names a coding agent/tool rather than the underlying model.",
            }
        )
    if _text_missing(ai_use.get("model")) and _text_missing(ai_use.get("model_metadata_unavailable_reason")):
        findings.append(
            {
                "severity": "error",
                "code": "MODEL_METADATA_MISSING",
                "message": "Record the underlying model or explain why model metadata is unavailable.",
            }
        )
    if _text_missing(ai_use.get("model_metadata_source")):
        findings.append(
            {
                "severity": "error",
                "code": "MODEL_METADATA_SOURCE_MISSING",
                "message": "Record where the model metadata came from.",
            }
        )
    if not _text_missing(ai_use.get("model_metadata_unavailable_reason")) and ai_use.get("model_metadata_source") != "agent_unavailable":
        findings.append(
            {
                "severity": "warning",
                "code": "MODEL_METADATA_SOURCE_MISMATCH",
                "message": "Unavailable model metadata should use model_metadata_source=agent_unavailable.",
            }
        )
    if ai_use.get("model_metadata_source") == "agent_unavailable" and _text_missing(ai_use.get("agent_tool")):
        findings.append(
            {
                "severity": "error",
                "code": "AGENT_TOOL_MISSING",
                "message": "model metadata is marked unavailable but agent_tool is empty.",
            }
        )
    if ai_use.get("model_metadata_source") == "agent_unavailable" and not runtime_metadata_files:
        findings.append(
            {
                "severity": "error",
                "code": "RUNTIME_METADATA_FILES_MISSING",
                "message": "model metadata is marked unavailable but runtime_metadata_files is empty.",
            }
        )
    if runtime_metadata and any(item.get("parse_error") for item in runtime_metadata):
        severity = "error" if ai_use.get("model_metadata_source") == "agent_unavailable" else "warning"
        findings.append(
            {
                "severity": severity,
                "code": "RUNTIME_METADATA_INVALID",
                "message": "A runtime metadata file could not be parsed or safely embedded.",
            }
        )
    if ai_use.get("model_metadata_source") == "agent_unavailable" and runtime_metadata:
        for item in runtime_metadata:
            metadata = item.get("metadata")
            if not isinstance(metadata, dict) or not metadata.get("schema") or not isinstance(metadata.get("session"), dict):
                findings.append(
                    {
                        "severity": "error",
                        "code": "RUNTIME_METADATA_INCOMPLETE",
                        "message": "Unavailable model metadata requires a parsed runtime metadata object with schema and session fields.",
                    }
                )
                break
    if ai_use.get("human_reviewed") is True:
        if ai_use.get("review_status") in {None, "not_reviewed"} or not review_files:
            findings.append(
                {
                    "severity": "error",
                    "code": "HUMAN_REVIEW_EVIDENCE_MISSING",
                    "message": "human_reviewed is true but review status or review_files evidence is missing.",
                }
            )
        if _has_blank_text_file(review_files):
            findings.append(
                {
                    "severity": "error",
                    "code": "HUMAN_REVIEW_FILE_BLANK",
                    "message": "human_reviewed is true but a review evidence file is blank.",
                }
            )
    roles = _as_list(ai_use.get("role", []))
    if "code_generation" in roles:
        languages = _normalized_languages(ai_use.get("languages", []))
        if not languages:
            findings.append({"severity": "error", "code": "AI_CODE_LANGUAGE_MISSING", "message": "languages is empty for AI-generated code."})
        if "none" in languages:
            findings.append({"severity": "error", "code": "AI_CODE_LANGUAGE_NONE", "message": "languages cannot include none for AI-generated code."})
        if not code_files:
            findings.append({"severity": "error", "code": "CODE_FILES_MISSING", "message": "code_files is empty for AI-generated code."})
        if _ai_code_language_mismatch(languages, code_files):
            findings.append(
                {
                    "severity": "error",
                    "code": "AI_CODE_LANGUAGE_MISMATCH",
                    "message": "Declared AI code languages do not match the archived code file extensions.",
                }
            )
    for record in [
        *prompt_files,
        *output_files,
        *input_files,
        *ai_code_draft_files,
        *code_files,
        *human_interaction_files,
        *human_intervention_files,
        *review_files,
        *runtime_metadata_files,
    ]:
        if not record.get("exists") or "sha256" not in record:
            findings.append(
                {
                    "severity": "error",
                    "code": "ARTIFACT_NOT_HASHED",
                    "message": f"AI artifact is missing or unhashable: {record.get('resolved_path')}",
                }
            )
    if ai_use.get("ai_output_used_as_data") is True:
        if not _as_list(ai_use.get("ai_derived_variables", [])):
            findings.append({"severity": "error", "code": "AI_VARIABLES_MISSING", "message": "AI-derived variables are not named."})
        if not input_files:
            findings.append({"severity": "error", "code": "INPUT_FILES_MISSING", "message": "input_files is empty for AI-derived data."})
        if not ai_use.get("qa_sample_plan"):
            findings.append({"severity": "warning", "code": "QA_PLAN_MISSING", "message": "QA sample plan is missing."})
        if not ai_use.get("sensitivity_plan"):
            findings.append({"severity": "warning", "code": "SENSITIVITY_PLAN_MISSING", "message": "Sensitivity plan is missing."})
    return findings


def _validation_summary(
    pap: dict[str, Any],
    proposal: dict[str, Any],
    artifact_base_dirs: list[Path],
    artifact_base_dirs_by_source: dict[str, Path],
) -> dict[str, Any]:
    result = Validator(
        artifact_base_dirs=artifact_base_dirs,
        artifact_base_dirs_by_source=artifact_base_dirs_by_source,
    ).validate(pap, proposal)
    return {
        "status": result.status,
        "violations": [
            {
                "rule_id": item.rule_id,
                "severity": item.severity.value,
                "message": item.message,
            }
            for item in result.violations
        ],
    }


def _status_from_findings(findings: list[dict[str, str]]) -> str:
    if any(item.get("severity") == "error" for item in findings):
        return "block"
    if any(item.get("severity") == "warning" for item in findings):
        return "warn"
    return "pass"


def _sha256_file(path: Path | None) -> str | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _has_no_change_intervention_file(records: list[dict[str, Any]]) -> bool:
    for record in records:
        if not record.get("exists"):
            continue
        path = Path(str(record.get("resolved_path", "")))
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = path.read_text(encoding="cp1252")
        if "AESDK-REVIEW-DIFF: no_textual_changes" in text:
            return True
    return False


def _has_blank_text_file(records: list[dict[str, Any]]) -> bool:
    for record in records:
        if not record.get("exists"):
            continue
        path = Path(str(record.get("resolved_path", "")))
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = path.read_text(encoding="cp1252")
        if not text.strip():
            return True
    return False


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _code_languages_from_records(records: list[dict[str, Any]]) -> list[str]:
    languages: list[str] = []
    for record in records:
        suffix = Path(str(record.get("original_path", ""))).suffix.lower()
        if suffix == ".py":
            languages.append("python")
        elif suffix == ".r":
            languages.append("r")
        elif suffix == ".do":
            languages.append("stata")
    return sorted(set(languages))


def _normalized_languages(values: Any) -> list[str]:
    return sorted({str(value).strip().lower() for value in _as_list(values) if str(value).strip()})


def _normalized_phrase(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    for separator in ["-", "/", "\\", ",", ";", ":"]:
        text = text.replace(separator, " ")
    return "_".join(part for part in text.split() if part)


def _text_missing(value: Any) -> bool:
    return _normalized_phrase(value) in {"", "tbd", "todo", "to_be_determined", "unknown", "na", "n_a", "none", "not_applicable", "undisclosed", "not_disclosed", "unavailable"}


def _looks_like_agent_tool_model(value: Any) -> bool:
    text = _normalized_phrase(value)
    if text in {
        "codex",
        "codex_cli",
        "openai_codex",
        "claude_code",
        "claude",
        "claude_cli",
        "vs_code",
        "vscode",
        "vs_code_copilot",
        "vscode_copilot",
        "github_copilot",
        "copilot",
        "open_code",
        "opencode",
        "cursor",
        "windsurf",
    }:
        return True
    return any(token in text.split("_") for token in {"codex", "copilot"})


def _ai_code_language_mismatch(declared_languages: Any, code_file_records: list[dict[str, Any]]) -> bool:
    declared = set(_normalized_languages(declared_languages))
    recognized = set(_code_languages_from_records(code_file_records))
    if not declared or "none" in declared:
        return False
    if "mixed" in declared:
        return False
    if not recognized:
        return False
    return declared != recognized


def _replication_statement(ai_use: dict[str, Any], status: str) -> str:
    if not ai_use:
        return "No AI-use metadata was found; this passport is incomplete."
    if not ai_use.get("used", False):
        return "No AI use was declared for this analysis."
    if status == "pass":
        return "The analysis can be replicated from archived AI artifacts without calling a live AI model."
    return "The AI-use evidence is incomplete; replication without a live AI model is not fully established."
