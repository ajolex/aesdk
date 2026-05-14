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
    return AIPassportResult(path=output, passport=passport)


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
    findings = _passport_findings(merged, prompt_files, output_files, input_files)
    validation = _validation_summary(active_pap, active_proposal) if active_pap else None
    if validation and validation["status"] == "block":
        findings.append(
            {
                "severity": "error",
                "code": "VALIDATION_BLOCK",
                "message": "PAP/proposal validation is blocked; inspect validation.violations.",
            }
        )

    status = _status_from_findings(findings)
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
        "ai_use": _public_ai_use(merged),
        "artifact_hashes": {
            "prompt_files": prompt_files,
            "output_files": output_files,
            "input_files": input_files,
        },
        "validation": validation,
        "findings": findings,
        "replication_statement": _replication_statement(merged, status),
    }


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
        "provider",
        "model",
        "model_version",
        "temperature",
        "top_p",
        "seed",
        "prompts_archived",
        "raw_outputs_archived",
        "human_reviewed",
        "reproducible_without_ai",
        "live_model_required",
        "ai_output_used_as_data",
        "ai_derived_variables",
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


def _passport_findings(
    ai_use: dict[str, Any],
    prompt_files: list[dict[str, Any]],
    output_files: list[dict[str, Any]],
    input_files: list[dict[str, Any]],
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
    for record in [*prompt_files, *output_files, *input_files]:
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


def _validation_summary(pap: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    result = Validator().validate(pap, proposal)
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


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _replication_statement(ai_use: dict[str, Any], status: str) -> str:
    if not ai_use:
        return "No AI-use metadata was found; this passport is incomplete."
    if not ai_use.get("used", False):
        return "No AI use was declared for this analysis."
    if status == "pass":
        return "The analysis can be replicated from archived AI artifacts without calling a live AI model."
    return "The AI-use evidence is incomplete; replication without a live AI model is not fully established."
