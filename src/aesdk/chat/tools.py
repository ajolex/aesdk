"""Pure tool functions that expose AESDK checks to chat clients.

These wrap the existing agent API so they can be called from an MCP server (see
`aesdk.chat.server`) or directly. They take plain text inputs (a chat model
composes the PAP as YAML and the proposal as JSON) and return plain data, so
they are easy to unit-test without any chat/MCP runtime.

Privacy note: `list_methods`, `method_context`, and `preflight` operate only on
text the assistant composes -- no dataset leaves the machine. `scan_data` and
`check_ols` read a local data file and are only meaningful when the server runs
on the user's own machine (for example, a local MCP connector).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import yaml

from aesdk.agent.context import agent_context
from aesdk.agent.preflight import preflight as _run_preflight


def list_methods() -> list[dict[str, str | None]]:
    """Return the supported econometric methods and their display names."""
    from aesdk.knowledge.catalog import get_method_protocol, list_method_ids

    methods: list[dict[str, str | None]] = []
    for method_id in sorted(list_method_ids()):
        try:
            name = get_method_protocol(method_id).get("name")
        except Exception:
            name = None
        methods.append({"method_id": method_id, "name": name})
    return methods


def method_context(method: str, depth: str = "protocol") -> str:
    """Return the AESDK guardrail context for a method as markdown."""
    return agent_context(method, depth=depth).to_markdown()


def _load_proposal(proposal: str | dict | None) -> dict[str, Any]:
    if proposal is None or proposal == "":
        return {}
    if isinstance(proposal, dict):
        return proposal
    return json.loads(proposal)


def _trim_result(result) -> dict[str, Any]:
    payload = {
        "method_id": result.method_id,
        "status": result.status,
        "blocked": result.blocked,
        "violations": [
            {
                "rule_id": v.rule_id,
                "severity": v.severity.value,
                "message": v.message,
                "guidance": v.guidance,
            }
            for v in result.violations
        ],
        "explanation": result.explain(),
    }
    if result.data_scan is not None:
        payload["data_scan"] = result.data_scan.to_dict()
    return payload


def preflight(
    method: str,
    pap_yaml: str,
    proposal: str | dict | None = None,
    conformance: str = "strict",
    data_path: str | None = None,
) -> dict[str, Any]:
    """Validate a PAP (YAML text) and proposal (JSON text) and return the verdict.

    If ``data_path`` points to a readable local file, the data-aware checks run
    too. Otherwise only the declaration checks run (data scan is skipped).
    """
    pap = yaml.safe_load(pap_yaml) or {}
    proposal_dict = _load_proposal(proposal)
    with tempfile.TemporaryDirectory() as tmp:
        pap_path = Path(tmp) / "pap.yaml"
        pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")
        result = _run_preflight(
            method=method,
            pap_path=pap_path,
            proposal=proposal_dict,
            conformance=conformance,
            scan_data_file=bool(data_path),
            data_path=data_path,
        )
    return _trim_result(result)


def scan_data(method: str, pap_yaml: str, data_path: str, conformance: str = "strict") -> dict[str, Any]:
    """Run the data-aware scan against a local dataset and return findings."""
    from aesdk.data import scan_data as _scan_data

    pap = yaml.safe_load(pap_yaml) or {}
    result = _scan_data(
        method=method,
        pap=pap,
        proposal={},
        data_path=data_path,
        base_dirs=[Path.cwd()],
        conformance=conformance,
    )
    return result.to_dict()


def check_ols(pap_yaml: str, data_path: str) -> dict[str, Any]:
    """Fit the declared OLS model on a local dataset and return the checklist."""
    result = scan_data(method="ols_cef", pap_yaml=pap_yaml, data_path=data_path, conformance="basic")
    profile = result.get("profile", {})
    return {
        "fitted": bool((profile.get("ols_assumptions") or {}).get("fitted")),
        "ols_assumptions": profile.get("ols_assumptions"),
        "findings": result.get("findings", []),
    }
