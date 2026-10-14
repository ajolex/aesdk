"""Protocol-level tests for the AESDK MCP server (works with MCP SDK 1.x and 2.x)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

mcp = pytest.importorskip("mcp")

from mcp import ClientSession  # noqa: E402
from mcp.client.stdio import StdioServerParameters, stdio_client  # noqa: E402

EXAMPLE = Path(__file__).resolve().parents[3] / "docs" / "examples" / "simulated_did_training_policy"


def _dump(obj) -> dict:
    return obj.model_dump(by_alias=True, mode="json")


async def _elicit(*args):
    from mcp import types

    return types.ElicitResult(action="accept", content={"outcome": "employment", "treatment": "treated", "unit": "county", "time": "year"})


async def _session(callback):
    params = StdioServerParameters(command=sys.executable, args=["-m", "aesdk", "mcp"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, elicitation_callback=_elicit) as session:
            await session.initialize()
            return await callback(session)


def _run(callback):
    return asyncio.run(_session(callback))


def _structured(result) -> dict:
    data = _dump(result)
    assert not data.get("isError"), data
    return data["structuredContent"]


def test_tools_have_annotations_and_output_schemas() -> None:
    async def body(session):
        return _dump(await session.list_tools())["tools"]

    tools = {t["name"]: t for t in _run(body)}
    expected = {
        "list_methods", "method_context", "draft_plan", "preflight", "scan_data", "check_ols",
        "prepare_record", "workflow_report", "ai_passport",
    }
    assert expected <= set(tools)
    for name in ("list_methods", "preflight", "scan_data", "check_ols", "draft_plan", "method_context"):
        assert tools[name]["annotations"]["readOnlyHint"] is True, name
    for name in ("prepare_record", "workflow_report", "ai_passport"):
        assert tools[name]["annotations"]["readOnlyHint"] is False
        assert tools[name]["annotations"]["destructiveHint"] is False
    assert "status" in tools["preflight"]["outputSchema"]["properties"]
    assert "ctx" not in tools["draft_plan"]["inputSchema"]["properties"]


def test_resources_and_prompts() -> None:
    async def body(session):
        resources = _dump(await session.list_resources())["resources"]
        templates = _dump(await session.list_resource_templates())["resourceTemplates"]
        prompts = _dump(await session.list_prompts())["prompts"]
        did = await session.read_resource("aesdk://methods/did")
        prompt = await session.get_prompt("design_review", {"description": "County DiD"})
        return resources, templates, prompts, _dump(did), _dump(prompt)

    resources, templates, prompts, did, prompt = _run(body)
    assert {"aesdk://methods", "aesdk://workflow"} <= {r["uri"] for r in resources}
    assert "aesdk://methods/{method_id}" in {t["uriTemplate"] for t in templates}
    assert {"design_review", "explain_result"} <= {p["name"] for p in prompts}
    assert "Differences-in-Differences" in did["contents"][0]["text"]
    assert "County DiD" in json.dumps(prompt)


def test_draft_plan_elicits_missing_facts_then_preflight_blocks_bad_proposal() -> None:
    pap_yaml = (EXAMPLE / "pap.yaml").read_text(encoding="utf-8")
    blocked = (EXAMPLE / "proposal_blocked.json").read_text(encoding="utf-8")

    async def body(session):
        draft = await session.call_tool("draft_plan", {"method": "did", "goal": "Effect of a training subsidy on county employment"})
        verdict = await session.call_tool(
            "preflight", {"method": "did", "pap_yaml": pap_yaml, "proposal_json": blocked, "data_path": ""}
        )
        return _structured(draft), _structured(verdict)

    draft, verdict = _run(body)
    assert draft["missing"] == []  # filled in by the elicitation callback
    assert "employment" in draft["pap_yaml"]
    assert verdict["status"] == "block" and verdict["blocked"] is True
    assert verdict["violations"]


def test_prepare_record_and_report_write_project_files(tmp_path: Path) -> None:
    pap_yaml = (EXAMPLE / "pap.yaml").read_text(encoding="utf-8")
    proposal = (EXAMPLE / "proposal_pass.json").read_text(encoding="utf-8")

    async def body(session):
        record = await session.call_tool(
            "prepare_record",
            {"method": "did", "pap_yaml": pap_yaml, "proposal_json": proposal, "project_dir": str(tmp_path)},
        )
        report = await session.call_tool("workflow_report", {"project_dir": str(tmp_path)})
        return _structured(record), _structured(report)

    record, report = _run(body)
    assert Path(record["path"]).exists() and record["blocked"] is False
    assert Path(report["path"]).name == "workflow.html" and Path(report["path"]).exists()
