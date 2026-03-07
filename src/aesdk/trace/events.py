"""Typed event payload helpers for replication blob."""

from __future__ import annotations

from typing import Any

from aesdk.protocol.validator import ValidationResult


def init_payload(*, pap_path: str, pap_hash: str) -> dict[str, Any]:
    return {"pap_path": pap_path, "pap_hash": pap_hash}


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


def execute_payload(*, status: str, diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    return {"status": status, "diagnostics": diagnostics}


def override_payload(*, rule_ids: list[str], justification: str) -> dict[str, Any]:
    return {"rule_ids": rule_ids, "justification": justification}


def code_change_payload(*, path: str, summary: str) -> dict[str, Any]:
    return {"path": path, "summary": summary}
