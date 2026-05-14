import json

import pandas as pd
import pytest
import yaml

import aesdk as ae
from aesdk.trace.blob import ReplicationBlob


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


def test_run_analysis_uses_proposal_directory_for_human_evidence(valid_pap_file, tmp_path) -> None:
    pap_dir = tmp_path / "pap"
    proposal_dir = tmp_path / "proposal"
    pap_dir.mkdir()
    proposal_dir.mkdir()
    pap_path = pap_dir / "pap.yaml"
    pap_path.write_text(valid_pap_file.read_text(encoding="utf-8"), encoding="utf-8")
    (proposal_dir / "followup_transcript.md").write_text("Human asked a clarification question.", encoding="utf-8")
    (proposal_dir / "prompt.md").write_text("Write Python analysis code.", encoding="utf-8")
    (proposal_dir / "output.md").write_text("Generated Python analysis code.", encoding="utf-8")
    proposal_path = proposal_dir / "proposal.json"
    proposal_path.write_text(
        json.dumps(
            {
                "estimator": "DiD",
                "standard_errors": "cluster",
                "clustering": "state",
                "ai_use": {
                    "used": True,
                    "role": "code_generation",
                    "languages": ["python"],
                    "model": "gpt-example",
                    "model_metadata_source": "api_response",
                    "prompts_archived": True,
                    "raw_outputs_archived": True,
                    "human_in_loop": True,
                    "human_interaction_files": ["followup_transcript.md"],
                    "human_reviewed": False,
                    "reproducible_without_ai": True,
                    "live_model_required": False,
                    "prompt_files": ["prompt.md"],
                    "output_files": ["output.md"],
                    "code_files": ["analysis.py"],
                },
            }
        ),
        encoding="utf-8",
    )
    code_path = proposal_dir / "analysis.py"
    code_path.write_text("print('ran')", encoding="utf-8")

    result = ae.run_analysis(
        method="did",
        pap_path=pap_path,
        proposal=proposal_path,
        code_path=code_path,
        blob_path=tmp_path / ".aesdk.json",
    )

    assert result.status == "pass"
    assert result.sandbox is not None
    assert result.sandbox.stdout.strip() == "ran"


def test_run_analysis_records_timeout_and_workflow_report(valid_pap_file, tmp_path) -> None:
    (tmp_path / "prompts").mkdir()
    (tmp_path / "ai_outputs").mkdir()
    (tmp_path / "prompts" / "analysis_prompt.md").write_text("Write Python analysis code.", encoding="utf-8")
    (tmp_path / "ai_outputs" / "code_response.md").write_text("Generated Python analysis code.", encoding="utf-8")
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
                    "languages": ["python"],
                    "provider": "Anthropic",
                    "model": "claude-sonnet-4.6",
                    "model_metadata_source": "agent_reported",
                    "prompts_archived": True,
                    "raw_outputs_archived": True,
                    "human_reviewed": False,
                    "reproducible_without_ai": True,
                    "live_model_required": False,
                    "prompt_files": ["prompts/analysis_prompt.md"],
                    "output_files": ["ai_outputs/code_response.md"],
                    "code_files": ["analysis.py"],
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
    assert "Review Summary" in report_text
    assert "Econometric Gatekeeping" in report_text
    assert "AI Use" in report_text
    assert "AI Evidence Archive" in report_text
    assert "Workflow Timeline" in report_text
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


def test_run_analysis_embeds_ai_lock_and_runtime_metadata(valid_pap_dict, tmp_path) -> None:
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    runtime = tmp_path / "codex_runtime.json"
    code_path = tmp_path / "analysis.py"
    pap_path = tmp_path / "pap.yaml"
    proposal_path = tmp_path / "proposal.json"
    blob_path = tmp_path / ".aesdk.json"

    prompt.write_text("Write analysis code.", encoding="utf-8")
    output.write_text("Generated Python analysis code.", encoding="utf-8")
    runtime.write_text(
        json.dumps(
            {
                "schema": "aesdk.codex_runtime.v1",
                "session": {"model": "gpt-test", "reasoning_effort": "high"},
            }
        ),
        encoding="utf-8",
    )
    code_path.write_text("print('ran')", encoding="utf-8")
    valid_pap_dict["ai_use"] = {
        "used": True,
        "role": "code_generation",
        "languages": ["python"],
        "provider": "OpenAI",
        "model": "gpt-test",
        "model_metadata_source": "agent_reported",
        "prompts_archived": True,
        "raw_outputs_archived": True,
        "human_reviewed": False,
        "reproducible_without_ai": True,
        "live_model_required": False,
        "prompt_files": [prompt.name],
        "output_files": [output.name],
        "runtime_metadata_files": [runtime.name],
        "code_files": [code_path.name],
    }
    pap_path.write_text(yaml.safe_dump(valid_pap_dict, sort_keys=False), encoding="utf-8")
    proposal_path.write_text(
        json.dumps({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"}),
        encoding="utf-8",
    )

    result = ae.run_analysis(
        method="did",
        pap_path=pap_path,
        proposal=proposal_path,
        code_path=code_path,
        blob_path=blob_path,
    )

    assert result.status == "pass"
    blob = json.loads(blob_path.read_text(encoding="utf-8"))
    ai_lock = blob["metadata"]["ai_lock"]
    assert ai_lock["status"] == "pass"
    assert ai_lock["runtime_metadata"][0]["metadata"]["session"]["reasoning_effort"] == "high"
    assert ai_lock["executed_code"]["matches_archived_code"] is True
    event_types = [event["event_type"] for event in blob["events"]]
    assert event_types == ["init", "propose_model", "validate", "ai_lock", "execute"]
    ai_lock_event = next(event for event in blob["events"] if event["event_type"] == "ai_lock")
    assert ai_lock_event["payload"]["ai_lock"] == ai_lock
    assert ReplicationBlob.load(blob_path).verify_integrity()[0] is True


def test_run_analysis_blocks_when_ai_lock_code_file_does_not_match(valid_pap_dict, tmp_path) -> None:
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    archived_code = tmp_path / "reviewed.py"
    executed_code = tmp_path / "scratch.py"
    pap_path = tmp_path / "pap.yaml"
    proposal_path = tmp_path / "proposal.json"
    blob_path = tmp_path / ".aesdk.json"

    prompt.write_text("Write analysis code.", encoding="utf-8")
    output.write_text("Generated Python analysis code.", encoding="utf-8")
    archived_code.write_text("print('reviewed')", encoding="utf-8")
    executed_code.write_text("print('scratch')", encoding="utf-8")
    valid_pap_dict["ai_use"] = {
        "used": True,
        "role": "code_generation",
        "languages": ["python"],
        "provider": "OpenAI",
        "model": "gpt-test",
        "model_metadata_source": "agent_reported",
        "prompts_archived": True,
        "raw_outputs_archived": True,
        "human_reviewed": False,
        "reproducible_without_ai": True,
        "live_model_required": False,
        "prompt_files": [prompt.name],
        "output_files": [output.name],
        "code_files": [archived_code.name],
    }
    pap_path.write_text(yaml.safe_dump(valid_pap_dict, sort_keys=False), encoding="utf-8")
    proposal_path.write_text(
        json.dumps({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"}),
        encoding="utf-8",
    )

    result = ae.run_analysis(
        method="did",
        pap_path=pap_path,
        proposal=proposal_path,
        code_path=executed_code,
        blob_path=blob_path,
    )

    assert result.status == "block"
    assert result.sandbox is None
    blob = json.loads(blob_path.read_text(encoding="utf-8"))
    assert [event["event_type"] for event in blob["events"]] == ["init", "propose_model", "validate", "ai_lock"]
    assert blob["metadata"]["ai_lock"]["executed_code"]["matches_archived_code"] is False
    codes = {item["code"] for item in blob["metadata"]["ai_lock"]["findings"]}
    assert "EXECUTED_CODE_NOT_ARCHIVED" in codes


def test_ai_passport_blocks_malformed_agent_unavailable_runtime_metadata(valid_pap_dict, tmp_path) -> None:
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    code = tmp_path / "analysis.py"
    runtime = tmp_path / "codex_runtime.json"
    pap_path = tmp_path / "pap.yaml"

    prompt.write_text("Write analysis code.", encoding="utf-8")
    output.write_text("Generated Python analysis code.", encoding="utf-8")
    code.write_text("print('ran')", encoding="utf-8")
    runtime.write_text("{not json", encoding="utf-8")
    valid_pap_dict["ai_use"] = {
        "used": True,
        "role": "code_generation",
        "languages": ["python"],
        "provider": "OpenAI",
        "agent_tool": "Codex",
        "model_metadata_source": "agent_unavailable",
        "model_metadata_unavailable_reason": "The coding-agent surface did not expose the exact model id.",
        "prompts_archived": True,
        "raw_outputs_archived": True,
        "human_reviewed": False,
        "reproducible_without_ai": True,
        "live_model_required": False,
        "prompt_files": [prompt.name],
        "output_files": [output.name],
        "runtime_metadata_files": [runtime.name],
        "code_files": [code.name],
    }
    pap_path.write_text(yaml.safe_dump(valid_pap_dict, sort_keys=False), encoding="utf-8")

    result = ae.write_ai_passport(pap_path=pap_path)

    assert result.status == "block"
    codes = {item["code"] for item in result.passport["findings"]}
    assert "RUNTIME_METADATA_INVALID" in codes


def test_run_analysis_does_not_embed_blocking_ai_lock_for_non_ai_run(valid_pap_file, tmp_path) -> None:
    proposal_path = tmp_path / "proposal.json"
    code_path = tmp_path / "analysis.py"
    blob_path = tmp_path / ".aesdk.json"
    proposal_path.write_text(
        json.dumps({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"}),
        encoding="utf-8",
    )
    code_path.write_text("print('ran')", encoding="utf-8")

    result = ae.run_analysis(
        method="did",
        pap_path=valid_pap_file,
        proposal=proposal_path,
        code_path=code_path,
        blob_path=blob_path,
    )

    assert result.status == "pass"
    blob = json.loads(blob_path.read_text(encoding="utf-8"))
    assert "ai_lock" not in blob["metadata"]
    assert "ai_lock" not in {event["event_type"] for event in blob["events"]}


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


def test_prepare_api_writes_replication_blob(tmp_path) -> None:
    intake = ae.intake_prompt(
        prompt="Estimate an OLS association between x and y.",
        method="ols_cef",
        outcome="y",
        treatment="x",
        output_dir=tmp_path,
    )
    blob_path = tmp_path / ".aesdk.json"

    prepared = ae.prepare(
        pap_path=intake.pap_path,
        proposal=intake.proposal_path,
        blob_path=blob_path,
        conformance="basic",
    )

    assert prepared.status == "pass"
    assert prepared.blob_path == blob_path
    assert blob_path.exists()


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
            "model_metadata_source": "api_response",
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_reviewed": False,
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


def test_write_ai_passport_hashes_stata_and_r_code_files(valid_pap_dict, tmp_path) -> None:
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    stata_code = tmp_path / "analysis.do"
    r_code = tmp_path / "analysis.R"
    prompt.write_text("Write equivalent Stata and R analysis code.", encoding="utf-8")
    output.write_text("Generated Stata and R scripts.", encoding="utf-8")
    stata_code.write_text("set seed 20260514\ndisplay 1\n", encoding="utf-8")
    r_code.write_text("set.seed(20260514)\nprint(1)\n", encoding="utf-8")
    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": "code_generation",
            "languages": ["stata", "r"],
            "provider": "OpenAI",
            "model": "gpt-example",
            "model_metadata_source": "api_response",
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_reviewed": False,
            "reproducible_without_ai": True,
            "live_model_required": False,
            "prompt_files": [prompt.name],
            "output_files": [output.name],
            "code_files": [stata_code.name, r_code.name],
        },
    }
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")

    result = ae.write_ai_passport(pap_path=pap_path)
    code_records = result.passport["artifact_hashes"]["code_files"]

    assert result.status == "pass"
    assert result.passport["ai_use"]["languages"] == ["stata", "r"]
    assert [record["original_path"] for record in code_records] == ["analysis.do", "analysis.R"]
    assert all(len(record["sha256"]) == 64 for record in code_records)


def test_write_ai_passport_blocks_language_code_file_mismatch(valid_pap_dict, tmp_path) -> None:
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    r_code = tmp_path / "analysis.R"
    prompt.write_text("Write Stata code.", encoding="utf-8")
    output.write_text("Generated code.", encoding="utf-8")
    r_code.write_text("set.seed(20260514)\nprint(1)\n", encoding="utf-8")
    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": "code_generation",
            "languages": ["stata"],
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_reviewed": False,
            "reproducible_without_ai": True,
            "live_model_required": False,
            "prompt_files": [prompt.name],
            "output_files": [output.name],
            "code_files": [r_code.name],
        },
    }
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")

    result = ae.write_ai_passport(pap_path=pap_path)

    codes = {item["code"] for item in result.passport["findings"]}
    assert result.status == "block"
    assert "AI_CODE_LANGUAGE_MISMATCH" in codes


def test_write_ai_passport_hashes_human_review_evidence(valid_pap_dict, tmp_path) -> None:
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    code = tmp_path / "analysis.do"
    review = tmp_path / "review.md"
    prompt.write_text("Write Stata code.", encoding="utf-8")
    output.write_text("Generated code.", encoding="utf-8")
    code.write_text("set seed 20260514\ndisplay 1\n", encoding="utf-8")
    review.write_text("Reviewed estimator, clustering, and code outputs.", encoding="utf-8")
    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": "code_generation",
            "languages": ["stata"],
            "model": "gpt-example",
            "model_metadata_source": "api_response",
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_reviewed": True,
            "review_status": "self_reviewed",
            "reviewer_role": "researcher",
            "review_files": [review.name],
            "review_checklist": ["estimator", "standard_errors", "outputs"],
            "reproducible_without_ai": True,
            "live_model_required": False,
            "prompt_files": [prompt.name],
            "output_files": [output.name],
            "code_files": [code.name],
        },
    }
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")

    result = ae.write_ai_passport(pap_path=pap_path)

    assert result.status == "pass"
    assert result.passport["ai_use"]["review_status"] == "self_reviewed"
    assert len(result.passport["artifact_hashes"]["review_files"][0]["sha256"]) == 64


def test_write_ai_passport_hashes_runtime_metadata(valid_pap_dict, tmp_path) -> None:
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    code = tmp_path / "analysis.do"
    runtime = tmp_path / "codex_runtime.json"
    prompt.write_text("Write Stata code.", encoding="utf-8")
    output.write_text("Generated code.", encoding="utf-8")
    code.write_text("set seed 20260514\ndisplay 1\n", encoding="utf-8")
    runtime.write_text(
        json.dumps(
            {
                "schema": "aesdk.codex_runtime.v1",
                "codex_client": "codex-cli test",
                "session": {"model": None, "reasoning_effort": None},
            }
        ),
        encoding="utf-8",
    )
    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": "code_generation",
            "languages": ["stata"],
            "provider": "OpenAI",
            "agent_tool": "Codex",
            "model_metadata_source": "agent_unavailable",
            "model_metadata_unavailable_reason": "The coding agent transcript exposed the tool name but not the underlying model id.",
            "runtime_metadata_files": [runtime.name],
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_reviewed": False,
            "reproducible_without_ai": True,
            "live_model_required": False,
            "prompt_files": [prompt.name],
            "output_files": [output.name],
            "code_files": [code.name],
        },
    }
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")

    result = ae.write_ai_passport(pap_path=pap_path)

    assert result.status == "pass"
    assert len(result.passport["artifact_hashes"]["runtime_metadata_files"][0]["sha256"]) == 64


def test_write_ai_passport_hashes_human_in_loop_and_intervention_evidence(valid_pap_dict, tmp_path) -> None:
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    ai_draft = tmp_path / "analysis_ai.do"
    final_code = tmp_path / "analysis.do"
    interaction = tmp_path / "followup_transcript.md"
    intervention = tmp_path / "human_code_diff.patch"
    prompt.write_text("Write Stata code.", encoding="utf-8")
    output.write_text("Generated code.", encoding="utf-8")
    ai_draft.write_text("display 1\n", encoding="utf-8")
    final_code.write_text("set seed 20260514\ndisplay 1\n", encoding="utf-8")
    interaction.write_text("Human asked the agent to add a reproducibility seed.", encoding="utf-8")
    diff = ae.write_review_diff(ai_code_path=ai_draft, final_code_path=final_code, output_path=intervention)
    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": "code_generation",
            "languages": ["stata"],
            "model": "gpt-example",
            "model_metadata_source": "api_response",
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_in_loop": True,
            "human_interaction_files": [interaction.name],
            "human_modified_code": True,
            "ai_code_draft_files": [ai_draft.name],
            "human_intervention_files": [intervention.name],
            "human_reviewed": False,
            "reproducible_without_ai": True,
            "live_model_required": False,
            "prompt_files": [prompt.name],
            "output_files": [output.name],
            "code_files": [final_code.name],
        },
    }
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")

    result = ae.write_ai_passport(pap_path=pap_path)

    assert diff.changed is True
    assert result.status == "pass"
    assert len(result.passport["artifact_hashes"]["human_interaction_files"][0]["sha256"]) == 64
    assert len(result.passport["artifact_hashes"]["human_intervention_files"][0]["sha256"]) == 64
    assert len(result.passport["artifact_hashes"]["ai_code_draft_files"][0]["sha256"]) == 64
    assert result.passport["ai_use"]["human_reviewed"] is False


def test_write_ai_passport_hashes_r_human_intervention_evidence(valid_pap_dict, tmp_path) -> None:
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    ai_draft = tmp_path / "analysis_ai.R"
    final_code = tmp_path / "analysis.R"
    interaction = tmp_path / "followup_transcript.md"
    intervention = tmp_path / "human_code_diff.patch"
    prompt.write_text("Write R code.", encoding="utf-8")
    output.write_text("Generated R code.", encoding="utf-8")
    ai_draft.write_text("print(1)\n", encoding="utf-8")
    final_code.write_text("set.seed(20260514)\nprint(1)\n", encoding="utf-8")
    interaction_result = ae.append_interaction_log(
        output_path=interaction,
        speaker="human",
        message="Please add the reproducibility seed before the R analysis runs.",
        source="chat",
    )
    diff = ae.write_review_diff(ai_code_path=ai_draft, final_code_path=final_code, output_path=intervention)
    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": "code_generation",
            "languages": ["r"],
            "model": "gpt-example",
            "model_metadata_source": "api_response",
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_in_loop": True,
            "human_interaction_files": [interaction.name],
            "human_modified_code": True,
            "ai_code_draft_files": [ai_draft.name],
            "human_intervention_files": [intervention.name],
            "human_reviewed": False,
            "reproducible_without_ai": True,
            "live_model_required": False,
            "prompt_files": [prompt.name],
            "output_files": [output.name],
            "code_files": [final_code.name],
        },
    }
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")

    result = ae.write_ai_passport(pap_path=pap_path)

    assert interaction_result.entry_count == 1
    assert diff.changed is True
    assert result.status == "pass"
    assert result.passport["ai_use"]["languages"] == ["r"]
    assert result.passport["artifact_hashes"]["code_files"][0]["original_path"] == "analysis.R"
    assert len(result.passport["artifact_hashes"]["human_interaction_files"][0]["sha256"]) == 64
    assert len(result.passport["artifact_hashes"]["human_intervention_files"][0]["sha256"]) == 64
    assert len(result.passport["artifact_hashes"]["ai_code_draft_files"][0]["sha256"]) == 64


def test_write_ai_passport_blocks_no_change_human_intervention(valid_pap_dict, tmp_path) -> None:
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    ai_draft = tmp_path / "analysis_ai.do"
    final_code = tmp_path / "analysis.do"
    intervention = tmp_path / "human_code_diff.patch"
    prompt.write_text("Write Stata code.", encoding="utf-8")
    output.write_text("Generated code.", encoding="utf-8")
    ai_draft.write_text("set seed 20260514\ndisplay 1\n", encoding="utf-8")
    final_code.write_text("set seed 20260514\ndisplay 1\n", encoding="utf-8")
    ae.write_review_diff(ai_code_path=ai_draft, final_code_path=final_code, output_path=intervention)
    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": "code_generation",
            "languages": ["stata"],
            "model": "gpt-example",
            "model_metadata_source": "api_response",
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_modified_code": True,
            "ai_code_draft_files": [ai_draft.name],
            "human_intervention_files": [intervention.name],
            "human_reviewed": False,
            "reproducible_without_ai": True,
            "live_model_required": False,
            "prompt_files": [prompt.name],
            "output_files": [output.name],
            "code_files": [final_code.name],
        },
    }
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")

    result = ae.write_ai_passport(pap_path=pap_path)

    assert result.status == "block"
    codes = {item["code"] for item in result.passport["findings"]}
    assert "HUMAN_INTERVENTION_NO_CODE_CHANGE" in codes


def test_write_ai_passport_blocks_blank_human_review_evidence(valid_pap_dict, tmp_path) -> None:
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    code = tmp_path / "analysis.do"
    review = tmp_path / "review.md"
    prompt.write_text("Write Stata code.", encoding="utf-8")
    output.write_text("Generated code.", encoding="utf-8")
    code.write_text("set seed 20260514\ndisplay 1\n", encoding="utf-8")
    review.write_text("   \n", encoding="utf-8")
    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": "code_generation",
            "languages": ["stata"],
            "model": "gpt-example",
            "model_metadata_source": "api_response",
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_reviewed": True,
            "review_status": "self_reviewed",
            "review_files": [review.name],
            "reproducible_without_ai": True,
            "live_model_required": False,
            "prompt_files": [prompt.name],
            "output_files": [output.name],
            "code_files": [code.name],
        },
    }
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")

    result = ae.write_ai_passport(pap_path=pap_path)

    assert result.status == "block"
    codes = {item["code"] for item in result.passport["findings"]}
    assert "HUMAN_REVIEW_FILE_BLANK" in codes


def test_append_interaction_log_writes_hashable_transcript(tmp_path) -> None:
    log = tmp_path / "review" / "followup_transcript.md"

    first = ae.append_interaction_log(output_path=log, speaker="human", message="Please justify the clustering level.", source="chat")
    second = ae.append_interaction_log(output_path=log, speaker="agent", message="I checked AESDK and updated the proposal.", source="chat")

    text = log.read_text(encoding="utf-8")
    assert first.entry_count == 1
    assert second.entry_count == 2
    assert "Please justify the clustering level." in text
    assert len(second.sha256) == 64


def test_preflight_uses_proposal_directory_for_proposal_ai_evidence(valid_pap_file, tmp_path) -> None:
    pap_dir = tmp_path / "pap"
    proposal_dir = tmp_path / "proposal"
    pap_dir.mkdir()
    proposal_dir.mkdir()
    pap_path = pap_dir / "pap.yaml"
    pap_path.write_text(valid_pap_file.read_text(encoding="utf-8"), encoding="utf-8")
    (pap_dir / "followup_transcript.md").write_text("This file is in the wrong directory.", encoding="utf-8")
    (proposal_dir / "prompt.md").write_text("Write Stata code.", encoding="utf-8")
    (proposal_dir / "output.md").write_text("Generated code.", encoding="utf-8")
    (proposal_dir / "analysis.do").write_text("set seed 20260514\ndisplay 1\n", encoding="utf-8")
    proposal_path = proposal_dir / "proposal.json"
    proposal_path.write_text(
        json.dumps(
            {
                "estimator": "DiD",
                "standard_errors": "cluster",
                "clustering": "state",
                "ai_use": {
                    "used": True,
                    "role": "code_generation",
                    "languages": ["stata"],
                    "model": "gpt-example",
                    "model_metadata_source": "api_response",
                    "prompts_archived": True,
                    "raw_outputs_archived": True,
                    "human_in_loop": True,
                    "human_interaction_files": ["followup_transcript.md"],
                    "human_reviewed": False,
                    "reproducible_without_ai": True,
                    "live_model_required": False,
                    "prompt_files": ["prompt.md"],
                    "output_files": ["output.md"],
                    "code_files": ["analysis.do"],
                },
            }
        ),
        encoding="utf-8",
    )

    result = ae.preflight(method="did", pap_path=pap_path, proposal=proposal_path)

    ids = {violation.rule_id for violation in result.violations}
    assert "AI-REP-022" in ids
    assert result.blocked


def test_ai_passport_validation_summary_uses_field_provenance(valid_pap_file, tmp_path) -> None:
    pap_dir = tmp_path / "pap"
    proposal_dir = tmp_path / "proposal"
    pap_dir.mkdir()
    proposal_dir.mkdir()
    pap_path = pap_dir / "pap.yaml"
    pap_path.write_text(valid_pap_file.read_text(encoding="utf-8"), encoding="utf-8")
    (pap_dir / "followup_transcript.md").write_text("Wrong-folder transcript.", encoding="utf-8")
    proposal_path = proposal_dir / "proposal.json"
    proposal_path.write_text(
        json.dumps(
            {
                "estimator": "DiD",
                "standard_errors": "cluster",
                "clustering": "state",
                "ai_use": {
                    "used": True,
                    "role": "code_generation",
                    "languages": ["stata"],
                    "model": "gpt-example",
                    "model_metadata_source": "api_response",
                    "prompts_archived": True,
                    "raw_outputs_archived": True,
                    "human_in_loop": True,
                    "human_interaction_files": ["followup_transcript.md"],
                    "human_reviewed": False,
                    "reproducible_without_ai": True,
                    "live_model_required": False,
                    "prompt_files": ["prompt.md"],
                    "output_files": ["output.md"],
                    "code_files": ["analysis.do"],
                },
            }
        ),
        encoding="utf-8",
    )

    result = ae.write_ai_passport(pap_path=pap_path, proposal_path=proposal_path)

    assert result.status == "block"
    assert result.passport["validation"]["status"] == "block"
    ids = {item["rule_id"] for item in result.passport["validation"]["violations"]}
    assert "AI-REP-022" in ids


def test_write_ai_passport_blocks_missing_artifact_files(valid_pap_dict, tmp_path) -> None:
    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": "code_generation",
            "languages": ["stata"],
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_reviewed": False,
            "reproducible_without_ai": True,
            "live_model_required": False,
            "prompt_files": ["missing_prompt.md"],
            "output_files": ["missing_output.md"],
            "code_files": ["missing_analysis.do"],
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
    code = tmp_path / "analysis.py"
    interaction = tmp_path / "followup_transcript.md"
    prompt.write_text("Write code.", encoding="utf-8")
    output.write_text("Generated code.", encoding="utf-8")
    code.write_text("print('ran')", encoding="utf-8")
    interaction.write_text("Human asked a follow-up question.", encoding="utf-8")
    valid_pap_dict["ai_use"] = {
        "used": True,
        "role": "code_generation",
        "languages": ["python"],
        "provider": "Anthropic",
        "model": "claude-sonnet-4.6",
        "model_metadata_source": "agent_reported",
        "prompts_archived": True,
        "raw_outputs_archived": True,
        "human_in_loop": True,
        "human_interaction_files": [interaction.name],
        "human_reviewed": False,
        "reproducible_without_ai": True,
        "live_model_required": False,
        "prompt_files": [prompt.name],
        "output_files": [output.name],
        "code_files": [code.name],
    }
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(valid_pap_dict, sort_keys=False), encoding="utf-8")
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"}),
        encoding="utf-8",
    )
    code_path = code
    blob_path = tmp_path / ".aesdk.json"

    run = ae.run_analysis(method="did", pap_path=pap_path, proposal=proposal_path, code_path=code_path, blob_path=blob_path)
    report = ae.write_workflow_report(blob_path=run.blob_path)
    text = report.read_text(encoding="utf-8")
    blob = json.loads(blob_path.read_text(encoding="utf-8"))

    assert blob["metadata"]["ai_lock"]["status"] == "pass"
    assert "claude-sonnet-4.6" in text
    assert "passport_status" in text
    assert "sha256=" in text
    assert "Replication statement" in text
    assert 'href="followup_transcript.md"' in text
    assert 'href="analysis.py"' in text


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
