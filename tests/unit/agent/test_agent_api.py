import json

import pandas as pd
import pytest
import yaml

import aesdk as ae


def test_agent_context_markdown_contains_binding_instructions() -> None:
    ctx = ae.agent_context("did")
    text = ctx.to_markdown()
    assert "Binding Instructions" in text
    assert "Differences-in-Differences" in text
    assert "Source Locators" in text


def test_agent_context_full_depth_includes_knowledge_pack() -> None:
    ctx = ae.agent_context("did", depth="full")
    text = ctx.to_markdown()

    assert ctx.knowledge_pack is not None
    assert ctx.to_dict()["knowledge_pack"]["method_id"] == "did"
    assert "Estimator Decision Tree" in text


def test_preflight_blocks_invalid_proposal(valid_pap_file) -> None:
    result = ae.preflight(
        method="did",
        pap_path=valid_pap_file,
        proposal={"estimator": "TWFE", "standard_errors": "HC3", "clustering": "state"},
        conformance="strict",
    )
    assert result.blocked
    assert result.status == "block"
    assert "W-PANEL-001" in {item.rule_id for item in result.violations}
    assert "hard stop" not in result.explain().lower()


def test_draft_pap_infers_panel_shape(tmp_path) -> None:
    data_path = tmp_path / "panel.csv"
    pd.DataFrame(
        {
            "state": ["a", "a", "b", "b"],
            "year": [2020, 2021, 2020, 2021],
            "y": [1, 2, 1, 3],
            "d": [0, 1, 0, 0],
        }
    ).to_csv(data_path, index=False)
    pap = ae.draft_pap(
        goal="Estimate policy effect",
        method="did",
        data_path=data_path,
        outcome="y",
        treatment="d",
        unit="state",
        time="year",
    )
    assert pap["data"]["structure"] == "panel"
    assert pap["data"]["T"] == 2
    assert pap["data"]["G"] == 2
    assert pap["identification"]["strategy"] == "DiD"
    assert "did_block" in pap


def test_run_analysis_returns_block_without_execution(valid_pap_file, tmp_path) -> None:
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps({"estimator": "DiD", "standard_errors": "HC3"}), encoding="utf-8")
    code_path = tmp_path / "analysis.py"
    code_path.write_text("print('should not run')", encoding="utf-8")

    result = ae.run_analysis(method="did", pap_path=valid_pap_file, proposal=proposal_path, code_path=code_path)
    assert result.blocked
    assert result.sandbox is None


def test_run_analysis_executes_when_preflight_passes(valid_pap_file, tmp_path) -> None:
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"}),
        encoding="utf-8",
    )
    code_path = tmp_path / "analysis.py"
    code_path.write_text("print('ran')", encoding="utf-8")
    blob_path = tmp_path / ".aesdk.json"

    result = ae.run_analysis(
        method="did",
        pap_path=valid_pap_file,
        proposal=proposal_path,
        code_path=code_path,
        blob_path=blob_path,
    )
    assert result.status == "pass"
    assert result.sandbox is not None
    assert result.sandbox.stdout.strip() == "ran"
    assert blob_path.exists()


def test_run_analysis_infers_stata_from_do_file(valid_pap_file, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AESDK_STATA", "definitely-not-stata")
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"}),
        encoding="utf-8",
    )
    code_path = tmp_path / "analysis.do"
    code_path.write_text("display 1", encoding="utf-8")

    result = ae.run_analysis(method="did", pap_path=valid_pap_file, proposal=proposal_path, code_path=code_path)

    assert result.status == "block"
    assert result.sandbox is not None
    assert result.sandbox.diagnostics[0].code == "MISSING_RUNTIME"


def test_drafted_pap_can_be_serialized_and_validated(tmp_path) -> None:
    pap = ae.draft_pap(goal="Estimate OLS association", method="ols_cef", outcome="y", treatment="x")
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")
    result = ae.preflight(method="ols_cef", pap_path=pap_path, proposal={"estimator": "OLS", "standard_errors": "HC3"})
    assert result.status in {"pass", "warn"}


def test_template_cli_resource_available() -> None:
    from importlib.resources import files

    template = files("aesdk.agent.templates").joinpath("AGENTS.md")
    assert template.is_file()
    assert "always use AESDK" in template.read_text(encoding="utf-8")
