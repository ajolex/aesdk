"""Typed event payload helpers for replication blob."""

from __future__ import annotations

import hashlib
from typing import Any

from aesdk.protocol.validator import ValidationResult


def init_payload(*, pap_path: str, pap_hash: str, governance_passport: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"pap_path": pap_path, "pap_hash": pap_hash}
    if governance_passport is not None:
        payload["governance_passport"] = governance_passport
    return payload


def proposal_payload(*, proposal: dict[str, Any], seed: int, temperature: float, model: str) -> dict[str, Any]:
    return {
        "proposal": proposal,
        "seed": seed,
        "temperature": temperature,
        "model": model,
    }


def validation_payload(result: ValidationResult) -> dict[str, Any]:
    return {
        "status": result.status,
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
            for item in result.violations
        ],
    }


def execute_payload(
    *,
    code: str,
    status: str,
    diagnostics: list[dict[str, Any]],
    language: str = "python",
    timeout_seconds: int | None = None,
    artifacts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    payload: dict[str, Any] = {
        "status": status,
        "diagnostics": diagnostics,
        "language": language,
        "code": code,
        "code_sha256": code_hash,
    }
    if timeout_seconds is not None:
        payload["timeout_seconds"] = timeout_seconds
    if artifacts:
        payload["artifacts"] = artifacts
    return payload


def override_payload(*, rule_ids: list[str], justification: str) -> dict[str, Any]:
    return {"rule_ids": rule_ids, "justification": justification}


def code_change_payload(*, path: str, summary: str) -> dict[str, Any]:
    return {"path": path, "summary": summary}
