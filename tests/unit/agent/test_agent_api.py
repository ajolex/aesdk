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


def test_preflight_blocks_method_pap_mismatch(valid_pap_file) -> None:
    result = ae.preflight(
        method="rdd",
        pap_path=valid_pap_file,
        proposal={"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"},
        conformance="strict",
    )

    assert result.blocked
    assert result.status == "block"
    assert "AGENT-METHOD-001" in {item.rule_id for item in result.violations}
    assert "PAP identification strategy is 'DiD'" in result.explain()


def test_preflight_blocks_method_proposal_mismatch(valid_pap_file) -> None:
    result = ae.preflight(
        method="did",
        pap_path=valid_pap_file,
        proposal={"estimator": "OLS", "standard_errors": "cluster", "clustering": "state"},
        conformance="strict",
    )

    assert result.blocked
    assert result.status == "block"
    assert "AGENT-METHOD-001" in {item.rule_id for item in result.violations}
    assert "proposal estimator is 'OLS'" in result.explain()


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


def test_draft_pap_records_design_origin() -> None:
    pap = ae.draft_pap(
        goal="Estimate randomized rollout effect",
        method="did",
        outcome="earnings",
        treatment="offer",
        unit="village",
        time="month",
        design_origin="experimental_rct",
    )

    assert pap["identification"]["design_origin"] == "experimental_rct"


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


def test_run_analysis_records_timeout_and_workflow_report(valid_pap_file, tmp_path) -> None:
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps(
            {
                "estimator": "DiD",
                "standard_errors": "cluster",
                "clustering": "state",
                "ai_use": {
                    "used": True,
                    "role": "code_generation",
                    "provider": "Anthropic",
                    "model": "claude-sonnet-4.6",
                    "prompts_archived": True,
                    "raw_outputs_archived": True,
                    "human_reviewed": True,
                    "reproducible_without_ai": True,
                    "live_model_required": False,
                    "prompt_files": ["prompts/analysis_prompt.md"],
                    "output_files": ["ai_outputs/code_response.md"],
                },
            }
        ),
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
        timeout_seconds=77,
    )
    report_path = ae.write_workflow_report(blob_path=blob_path)
    blob = json.loads(blob_path.read_text(encoding="utf-8"))
    execute_payload = next(event["payload"] for event in blob["events"] if event["event_type"] == "execute")

    assert result.status == "pass"
    assert execute_payload["timeout_seconds"] == 77
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "AESDK Workflow Report" in report_text
    assert "AI Use" in report_text
    assert "claude-sonnet-4.6" in report_text


def test_run_analysis_requires_acknowledgement_for_warnings(valid_pap_dict, tmp_path) -> None:
    valid_pap_dict["did_block"]["parallel_trends_test"] = False
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(valid_pap_dict, sort_keys=False), encoding="utf-8")
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"}),
        encoding="utf-8",
    )
    code_path = tmp_path / "analysis.py"
    code_path.write_text("print('ran')", encoding="utf-8")

    result = ae.run_analysis(
        method="did",
        pap_path=pap_path,
        proposal=proposal_path,
        code_path=code_path,
        conformance="basic",
    )

    assert result.status == "warn"
    assert result.blocked
    assert result.warning_acknowledgement_required
    assert result.sandbox is None

    acknowledged = ae.run_analysis(
        method="did",
        pap_path=pap_path,
        proposal=proposal_path,
        code_path=code_path,
        conformance="basic",
        acknowledge_warnings=True,
    )
    assert acknowledged.status == "pass"
    assert acknowledged.sandbox is not None
    assert acknowledged.sandbox.stdout.strip() == "ran"


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
    assert result.blocked
    assert result.sandbox is not None
    assert result.sandbox.diagnostics[0].code == "MISSING_RUNTIME"


def test_run_analysis_infers_r_from_r_file(valid_pap_file, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AESDK_R", "definitely-not-rscript")
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"}),
        encoding="utf-8",
    )
    code_path = tmp_path / "analysis.R"
    code_path.write_text("print(1)", encoding="utf-8")

    result = ae.run_analysis(method="did", pap_path=valid_pap_file, proposal=proposal_path, code_path=code_path)

    assert result.status == "block"
    assert result.blocked
    assert result.sandbox is not None
    assert result.sandbox.diagnostics[0].code == "MISSING_RUNTIME"


def test_drafted_pap_can_be_serialized_and_validated(tmp_path) -> None:
    pap = ae.draft_pap(goal="Estimate OLS association", method="ols_cef", outcome="y", treatment="x")
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")
    result = ae.preflight(method="ols_cef", pap_path=pap_path, proposal={"estimator": "OLS", "standard_errors": "HC3"})
    assert result.status in {"pass", "warn"}


def test_intake_task_writes_reviewable_pap_and_proposal(tmp_path) -> None:
    task_path = tmp_path / "Stata_Task.txt"
    task_path.write_text(
        "Estimate a randomized rollout using two-way fixed effects and an event study.",
        encoding="utf-8",
    )

    result = ae.intake_task(
        task_path=task_path,
        outcome="employment",
        treatment="assigned_training",
        unit="county",
        time="year",
        design_origin="experimental_rct",
    )
    pap = yaml.safe_load(result.pap_path.read_text(encoding="utf-8"))
    proposal = json.loads(result.proposal_path.read_text(encoding="utf-8"))

    assert result.method == "did"
    assert result.task_text_path is not None and result.task_text_path.exists()
    assert pap["data"]["structure"] == "panel"
    assert pap["identification"]["design_origin"] == "experimental_rct"
    assert "design_note" in pap["identification"]
    assert proposal["design_origin"] == "experimental_rct"


def test_intake_task_infers_randomized_did_design_origin(tmp_path) -> None:
    task_path = tmp_path / "Stata_Task.txt"
    task_path.write_text(
        "Use an event study for a randomized rollout of the training offer.",
        encoding="utf-8",
    )

    result = ae.intake_task(
        task_path=task_path,
        outcome="employment",
        treatment="offer",
        unit="county",
        time="year",
    )
    pap = yaml.safe_load(result.pap_path.read_text(encoding="utf-8"))
    proposal = json.loads(result.proposal_path.read_text(encoding="utf-8"))

    assert result.method == "did"
    assert pap["identification"]["design_origin"] == "experimental_rct"
    assert proposal["design_origin"] == "experimental_rct"


def test_write_ai_passport_hashes_archived_files(valid_pap_dict, tmp_path) -> None:
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.jsonl"
    prompt.write_text("Classify each comment.", encoding="utf-8")
    output.write_text('{"id": 1, "label": "eligible"}\n', encoding="utf-8")
    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": "text_classification",
            "provider": "OpenAI",
            "model": "gpt-example",
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_reviewed": True,
            "reproducible_without_ai": True,
            "prompt_files": [prompt.name],
            "output_files": [output.name],
        },
    }
    pap_path = tmp_path / "pap.yaml"
    passport_path = tmp_path / "ai.lock.json"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")

    result = ae.write_ai_passport(pap_path=pap_path, output_path=passport_path)
    passport = json.loads(result.path.read_text(encoding="utf-8"))

    assert result.status == "pass"
    assert passport["schema"] == "aesdk.ai_passport.v1"
    assert len(passport["source_documents"]["pap_sha256"]) == 64
    assert passport["ai_use"]["model"] == "gpt-example"
    assert passport["artifact_hashes"]["prompt_files"][0]["exists"] is True
    assert len(passport["artifact_hashes"]["output_files"][0]["sha256"]) == 64


def test_write_ai_passport_blocks_missing_artifact_files(valid_pap_dict, tmp_path) -> None:
    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": "code_generation",
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_reviewed": True,
            "reproducible_without_ai": True,
            "live_model_required": False,
            "prompt_files": ["missing_prompt.md"],
            "output_files": ["missing_output.md"],
        },
    }
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")

    result = ae.write_ai_passport(pap_path=pap_path)

    assert result.status == "block"
    codes = {item["code"] for item in result.passport["findings"]}
    assert "ARTIFACT_NOT_HASHED" in codes


def test_workflow_report_reads_pap_level_ai_use_and_passport(valid_pap_file, valid_pap_dict, tmp_path) -> None:
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    prompt.write_text("Write code.", encoding="utf-8")
    output.write_text("Generated code.", encoding="utf-8")
    valid_pap_dict["ai_use"] = {
        "used": True,
        "role": "code_generation",
        "provider": "Anthropic",
        "model": "claude-sonnet-4.6",
        "prompts_archived": True,
        "raw_outputs_archived": True,
        "human_reviewed": True,
        "reproducible_without_ai": True,
        "live_model_required": False,
        "prompt_files": [prompt.name],
        "output_files": [output.name],
    }
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(valid_pap_dict, sort_keys=False), encoding="utf-8")
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"}),
        encoding="utf-8",
    )
    code_path = tmp_path / "analysis.py"
    code_path.write_text("print('ran')", encoding="utf-8")
    blob_path = tmp_path / ".aesdk.json"

    run = ae.run_analysis(method="did", pap_path=pap_path, proposal=proposal_path, code_path=code_path, blob_path=blob_path)
    passport = ae.write_ai_passport(pap_path=pap_path, proposal_path=proposal_path, output_path=tmp_path / "ai.lock.json")
    report = ae.write_workflow_report(blob_path=run.blob_path)
    text = report.read_text(encoding="utf-8")

    assert passport.status == "pass"
    assert "claude-sonnet-4.6" in text
    assert "passport_status" in text
    assert "sha256=" in text


def test_drafted_rct_pap_can_be_serialized_and_validated(tmp_path) -> None:
    pap = ae.draft_pap(
        goal="Estimate tutoring offer effect",
        method="experimental_rct",
        outcome="test_score",
        treatment="assigned_tutoring",
        unit="student",
    )
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")

    result = ae.preflight(
        method="experimental_rct",
        pap_path=pap_path,
        proposal={"estimator": "RCT", "standard_errors": "HC3"},
        conformance="basic",
    )

    assert pap["identification"]["strategy"] == "RCT"
    assert pap["rct_block"]["randomization_unit"] == "student"
    assert result.status in {"pass", "warn"}
    assert not result.blocked


def test_template_cli_resource_available() -> None:
    from importlib.resources import files

    agents_template = files("aesdk.agent.templates").joinpath("AGENTS.md")
    claude_template = files("aesdk.agent.templates").joinpath("CLAUDE.md")
    assert agents_template.is_file()
    assert claude_template.is_file()
    agents_text = agents_template.read_text(encoding="utf-8")
    claude_text = claude_template.read_text(encoding="utf-8")
    assert "always use AESDK" in agents_text
    assert "experimental_rct" in agents_text
    assert "analysis.do" in agents_text
    assert "experimental_rct" in claude_text
    assert "Stata" in claude_text
