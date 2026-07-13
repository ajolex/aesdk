"""Tests for the chat tool layer, presets, and MCP command."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml
from typer.testing import CliRunner

from aesdk.chat import available_targets, chat_guide
from aesdk.chat import tools
from aesdk.cli.main import app

runner = CliRunner()


def _did_pap(source: str) -> str:
    pap = {
        "project": {
            "id": "chat_did",
            "title": "Chat DiD fixture",
            "author": "T",
            "date_registered": "2026-07-13",
            "version": "1.0.0",
        },
        "data": {"source": source, "unit": "state", "time": "year", "structure": "panel"},
        "identification": {
            "strategy": "DiD",
            "treatment_variable": "treated",
            "outcome_variable": "employment",
            "covariates": {"mandatory": [], "optional": []},
            "standard_errors": "cluster",
            "clustering": "state",
            "expected_sign": "positive",
        },
        "did_block": {"parallel_trends_test": True, "staggered_adoption": False},
        "robustness": {"specification_curve": False},
    }
    return yaml.safe_dump(pap)


def test_list_methods_covers_full_toolkit() -> None:
    methods = {m["method_id"] for m in tools.list_methods()}
    assert {"ols_cef", "did", "iv_2sls", "dml", "bayesian", "garch"}.issubset(methods)


def test_method_context_returns_markdown() -> None:
    text = tools.method_context("did")
    assert "Differences-in-Differences" in text


def test_preflight_text_blocks_bad_did() -> None:
    result = tools.preflight(
        method="did",
        pap_yaml=_did_pap("nope.csv"),
        proposal='{"estimator": "TWFE", "standard_errors": "HC3", "clustering": "state"}',
        conformance="strict",
    )
    assert result["blocked"] is True
    assert any(v["rule_id"] == "W-PANEL-001" for v in result["violations"])


def test_preflight_text_with_local_data_runs_scan(tmp_path: Path) -> None:
    data = tmp_path / "panel.csv"
    rows = []
    for s in range(60):
        adopt = 3 + (s % 3) if s % 2 == 0 else None  # staggered
        for y in range(1, 7):
            t = 1 if (adopt is not None and y >= adopt) else 0
            rows.append({"state": f"S{s}", "year": y, "treated": t, "employment": 100.0 + s + y + t})
    pd.DataFrame(rows).to_csv(data, index=False)
    result = tools.preflight(
        method="did",
        pap_yaml=_did_pap(str(data)),
        proposal='{"estimator": "TWFE", "standard_errors": "cluster", "clustering": "state"}',
        conformance="strict",
        data_path=str(data),
    )
    assert result.get("data_scan", {}).get("scanned") is True
    assert any(v["rule_id"] == "DATA-DID-001" for v in result["violations"])


def test_chat_guide_targets_render() -> None:
    assert set(available_targets()) == {"chatgpt", "claude", "mcp"}
    assert "AESDK" in chat_guide("chatgpt")
    assert "MCP" in chat_guide("claude")
    assert "mcpServers" in chat_guide("mcp")


def test_chat_guide_cli() -> None:
    result = runner.invoke(app, ["chat-guide", "--target", "chatgpt"])
    assert result.exit_code == 0
    assert "code interpreter" in result.output.lower()


def test_mcp_cli_degrades_without_extra() -> None:
    # The mcp package is an optional extra; without it the command should exit
    # with a clear, actionable message rather than a traceback.
    try:
        import mcp  # noqa: F401

        installed = True
    except Exception:
        installed = False
    if installed:
        return  # cannot easily test the missing-extra path when it is installed
    result = runner.invoke(app, ["mcp"])
    assert result.exit_code == 1
    assert "pip install aesdk[mcp]" in result.output
