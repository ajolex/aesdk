import json
import os
import subprocess
import sys

from typer.testing import CliRunner

from aesdk.cli.main import app


def test_agent_codex_runtime_writes_metadata(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    (home / ".codex" / "config.toml").write_text('model = "gpt-test"\nmodel_reasoning_effort = "high"\n', encoding="utf-8")
    workspace = tmp_path / "repo"
    workspace.mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    monkeypatch.setattr("aesdk.agent.runtime_metadata._codex_version", lambda: "codex-cli test")
    monkeypatch.setattr("aesdk.agent.runtime_metadata._git_output", lambda args, cwd: "abc123")

    output = tmp_path / "codex_runtime.json"
    result = CliRunner().invoke(
        app,
        ["agent", "codex-runtime", "--workspace", str(workspace), "--output", str(output)],
    )

    assert result.exit_code == 0
    assert "runtime_metadata_written=" in result.output
    assert "Codex client: codex-cli test" in result.output
    assert output.exists()


def test_agent_claude_runtime_writes_metadata(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "settings.json").write_text('{"model":"claude-test"}', encoding="utf-8")
    workspace = tmp_path / "repo"
    workspace.mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    monkeypatch.setattr("aesdk.agent.runtime_metadata._command_version", lambda command, args: "claude test")
    monkeypatch.setattr("aesdk.agent.runtime_metadata._git_output", lambda args, cwd: "abc123")

    output = tmp_path / "claude_runtime.json"
    result = CliRunner().invoke(
        app,
        ["agent", "claude-runtime", "--workspace", str(workspace), "--output", str(output)],
    )

    assert result.exit_code == 0
    assert "runtime_metadata_written=" in result.output
    assert "Claude Code client: claude test" in result.output
    assert output.exists()


def test_agent_copilot_runtime_writes_metadata(tmp_path, monkeypatch) -> None:
    appdata = tmp_path / "AppData"
    (appdata / "Code" / "User").mkdir(parents=True)
    (appdata / "Code" / "User" / "settings.json").write_text('{"github.copilot.chat.model":"gpt-test"}', encoding="utf-8")
    workspace = tmp_path / "repo"
    workspace.mkdir()
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setattr("aesdk.agent.runtime_metadata._vscode_version", lambda: "code test")
    monkeypatch.setattr("aesdk.agent.runtime_metadata._copilot_extensions", lambda: ["GitHub.copilot@1.2.3"])
    monkeypatch.setattr("aesdk.agent.runtime_metadata._git_output", lambda args, cwd: "abc123")

    output = tmp_path / "copilot_runtime.json"
    result = CliRunner().invoke(
        app,
        ["agent", "copilot-runtime", "--workspace", str(workspace), "--output", str(output)],
    )

    assert result.exit_code == 0
    assert "runtime_metadata_written=" in result.output
    assert "VS Code client: code test" in result.output
    assert output.exists()


def test_agent_review_diff_writes_patch(tmp_path) -> None:
    ai_code = tmp_path / "analysis_ai.py"
    final_code = tmp_path / "analysis.py"
    output = tmp_path / "review" / "human_code_diff.patch"
    ai_code.write_text("print(1)\n", encoding="utf-8")
    final_code.write_text("import random\nrandom.seed(20260514)\nprint(1)\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["agent", "review-diff", "--ai-code", str(ai_code), "--final-code", str(final_code), "--output", str(output)],
    )

    assert result.exit_code == 0
    assert "review_diff_written=" in result.output
    assert "changed=true" in result.output
    assert "+import random" in output.read_text(encoding="utf-8")


def test_agent_review_diff_handles_cp1252_code(tmp_path) -> None:
    ai_code = tmp_path / "analysis_ai.do"
    final_code = tmp_path / "analysis.do"
    output = tmp_path / "human_code_diff.patch"
    ai_code.write_bytes("* cafe\n display 1\n".replace("cafe", "caf\xe9").encode("cp1252"))
    final_code.write_bytes("* cafe\n set seed 20260514\n display 1\n".replace("cafe", "caf\xe9").encode("cp1252"))

    result = CliRunner().invoke(
        app,
        ["agent", "review-diff", "--ai-code", str(ai_code), "--final-code", str(final_code), "--output", str(output)],
    )

    assert result.exit_code == 0
    assert "changed=true" in result.output
    assert "+ set seed 20260514" in output.read_text(encoding="utf-8")


def test_agent_review_diff_writes_r_patch(tmp_path) -> None:
    ai_code = tmp_path / "analysis_ai.R"
    final_code = tmp_path / "analysis.R"
    output = tmp_path / "review" / "human_code_diff.patch"
    ai_code.write_text("print(1)\n", encoding="utf-8")
    final_code.write_text("set.seed(20260514)\nprint(1)\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["agent", "review-diff", "--ai-code", str(ai_code), "--final-code", str(final_code), "--output", str(output)],
    )

    assert result.exit_code == 0
    assert "changed=true" in result.output
    assert "+set.seed(20260514)" in output.read_text(encoding="utf-8")


def test_agent_interaction_log_appends_entries(tmp_path) -> None:
    output = tmp_path / "review" / "followup_transcript.md"

    first = CliRunner().invoke(
        app,
        ["agent", "interaction-log", "--output", str(output), "--speaker", "human", "--message", "Why cluster by state?", "--source", "chat"],
    )
    second = CliRunner().invoke(
        app,
        ["agent", "interaction-log", "--output", str(output), "--speaker", "agent", "--message", "AESDK requires the treatment-level cluster check."],
    )

    text = output.read_text(encoding="utf-8")
    assert first.exit_code == 0
    assert second.exit_code == 0
    assert "entries=1" in first.output
    assert "entries=2" in second.output
    assert "Why cluster by state?" in text
    assert "AESDK requires the treatment-level cluster check." in text


def test_python_module_entrypoint_lists_methods() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str((__import__("pathlib").Path(__file__).resolve().parents[3] / "src"))

    result = subprocess.run(
        [sys.executable, "-m", "aesdk", "methods", "list"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )

    assert result.returncode == 0
    assert "did" in result.stdout


def test_agent_doctor_runs() -> None:
    result = CliRunner().invoke(app, ["agent", "doctor"])

    assert result.exit_code == 0
    assert "aesdk_version=" in result.output
    assert "python_m_aesdk=" in result.output


def test_agent_doctor_respects_configured_stata_and_r_paths(tmp_path, monkeypatch) -> None:
    stata = tmp_path / "StataMP-64.exe"
    rscript = tmp_path / "Rscript.exe"
    stata.write_text("", encoding="utf-8")
    rscript.write_text("", encoding="utf-8")
    monkeypatch.setenv("AESDK_STATA", str(stata))
    monkeypatch.setenv("AESDK_R", str(rscript))

    result = CliRunner().invoke(app, ["agent", "doctor", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["stata_executable"] == str(stata)
    assert payload["rscript_executable"] == str(rscript)


def test_validate_uses_pap_and_proposal_directories_for_ai_evidence(valid_pap_dict, tmp_path) -> None:
    import yaml

    pap_dir = tmp_path / "pap"
    proposal_dir = tmp_path / "proposal"
    pap_dir.mkdir()
    proposal_dir.mkdir()
    pap_path = pap_dir / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(valid_pap_dict, sort_keys=False), encoding="utf-8")
    (proposal_dir / "followup_transcript.md").write_text("Human asked a clarification question.", encoding="utf-8")
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

    result = CliRunner().invoke(app, ["validate", "--pap", str(pap_path), "--proposal", str(proposal_path)])

    assert result.exit_code == 0
    assert "status=pass" in result.output
    assert "AI-REP-022" not in result.output


def test_validate_exits_nonzero_when_blocked(valid_pap_dict, tmp_path) -> None:
    import yaml

    pap_path = tmp_path / "pap.yaml"
    proposal_path = tmp_path / "proposal.json"
    pap_path.write_text(yaml.safe_dump(valid_pap_dict, sort_keys=False), encoding="utf-8")
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
                    "human_interaction_files": ["missing_transcript.md"],
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

    result = CliRunner().invoke(app, ["validate", "--pap", str(pap_path), "--proposal", str(proposal_path)])

    assert result.exit_code == 1
    assert "status=block" in result.output
    assert "AI-REP-022" in result.output


def test_init_accepts_pap_without_proposal(valid_pap_file, tmp_path) -> None:
    blob_path = tmp_path / ".aesdk.json"

    result = CliRunner().invoke(app, ["init", "--pap", str(valid_pap_file), "--blob", str(blob_path)])

    assert result.exit_code == 0
    assert "initialized project=" in result.output
    assert blob_path.exists()


def test_agent_run_prints_sandbox_diagnostics_for_missing_r_runtime(valid_pap_file, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AESDK_R", "definitely-not-rscript")
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"}),
        encoding="utf-8",
    )
    code_path = tmp_path / "analysis.R"
    code_path.write_text("print(1)", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "agent",
            "run",
            "--method",
            "did",
            "--pap",
            str(valid_pap_file),
            "--proposal",
            str(proposal_path),
            "--code-file",
            str(code_path),
        ],
    )

    assert result.exit_code == 1
    assert "status=block blocked=True" in result.output
    assert "MISSING_RUNTIME" in result.output
    assert "Rscript executable was not found" in result.output


def test_agent_run_prints_sandbox_diagnostics_for_missing_stata_runtime(valid_pap_file, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AESDK_STATA", "definitely-not-stata")
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"}),
        encoding="utf-8",
    )
    code_path = tmp_path / "analysis.do"
    code_path.write_text("display 1", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "agent",
            "run",
            "--method",
            "did",
            "--pap",
            str(valid_pap_file),
            "--proposal",
            str(proposal_path),
            "--code-file",
            str(code_path),
        ],
    )

    assert result.exit_code == 1
    assert "status=block blocked=True" in result.output
    assert "MISSING_RUNTIME" in result.output
    assert "Stata executable was not found" in result.output


def test_agent_run_accepts_timeout_and_agent_report(valid_pap_file, tmp_path) -> None:
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"}),
        encoding="utf-8",
    )
    code_path = tmp_path / "analysis.py"
    code_path.write_text("print('ok')", encoding="utf-8")
    blob_path = tmp_path / ".aesdk.json"
    report_path = tmp_path / "workflow.html"
    runner = CliRunner()

    run_result = runner.invoke(
        app,
        [
            "agent",
            "run",
            "--method",
            "did",
            "--pap",
            str(valid_pap_file),
            "--proposal",
            str(proposal_path),
            "--code-file",
            str(code_path),
            "--blob",
            str(blob_path),
            "--timeout-seconds",
            "5",
        ],
    )
    report_result = runner.invoke(
        app,
        ["agent", "report", "--blob", str(blob_path), "--output", str(report_path)],
    )

    assert run_result.exit_code == 0
    assert "status=pass blocked=False" in run_result.output
    assert report_result.exit_code == 0
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "Review Summary" in report_text
    assert "Workflow Timeline" in report_text


def test_agent_intake_writes_scaffold_files(tmp_path) -> None:
    task_path = tmp_path / "task.txt"
    task_path.write_text("Run an event study for a randomized training rollout.", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "agent",
            "intake",
            "--task",
            str(task_path),
            "--outcome",
            "wage",
            "--treatment",
            "offer",
            "--unit",
            "worker",
            "--time",
            "quarter",
            "--design-origin",
            "experimental_rct",
        ],
    )

    assert result.exit_code == 0
    assert "method=did" in result.output
    assert (tmp_path / "pap.yaml").exists()
    assert (tmp_path / "proposal.json").exists()
    assert (tmp_path / ".aesdk.json").exists()


def test_agent_intake_accepts_prompt_without_task_file(tmp_path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "agent",
            "intake",
            "--prompt",
            "Run an event study for a randomized staggered rollout across GVHs with not-yet-treated controls.",
            "--outcome",
            "uptake",
            "--treatment",
            "treated",
            "--unit",
            "gvh",
            "--time",
            "month",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "method=did" in result.output
    assert "blob_written=" in result.output
    assert (tmp_path / "prompt_extracted.txt").exists()
    assert (tmp_path / ".aesdk.json").exists()
    pap = __import__("yaml").safe_load((tmp_path / "pap.yaml").read_text(encoding="utf-8"))
    proposal = json.loads((tmp_path / "proposal.json").read_text(encoding="utf-8"))
    assert pap["identification"]["strategy"] == "EventStudy"
    assert pap["identification"]["design_origin"] == "experimental_rct"
    assert pap["did_block"]["staggered_adoption"] is True
    assert pap["rct_block"]["randomization_unit"] == "gvh"
    assert proposal["estimator"] == "EventStudy"


def test_agent_intake_task_prescribed_twfe_warns_and_writes_blob(tmp_path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "agent",
            "intake",
            "--prompt",
            "You must use TWFE for this randomized staggered rollout across GVHs with not-yet-treated controls.",
            "--outcome",
            "uptake",
            "--treatment",
            "treated",
            "--unit",
            "gvh",
            "--time",
            "month",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "status=warn blocked=False" in result.output
    assert "AP-DID-006" in result.output
    assert (tmp_path / ".aesdk.json").exists()
    proposal = json.loads((tmp_path / "proposal.json").read_text(encoding="utf-8"))
    assert proposal["estimator"] == "TWFE"
    assert proposal["task_required_estimator"] == "TWFE"


def test_agent_intake_requires_blob_without_opt_out(tmp_path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "agent",
            "intake",
            "--prompt",
            "Run OLS.",
            "--output-dir",
            str(tmp_path),
            "--no-write-blob",
        ],
    )

    assert result.exit_code != 0
    assert not (tmp_path / "pap.yaml").exists()


def test_agent_intake_blocks_unreadable_pdf_without_prompt(tmp_path, monkeypatch) -> None:
    task = tmp_path / "task.pdf"
    task.write_text("not really a pdf", encoding="utf-8")
    monkeypatch.setattr("aesdk.agent.intake.shutil.which", lambda command: None)

    result = CliRunner().invoke(app, ["agent", "intake", "--task", str(task), "--output-dir", str(tmp_path)])

    assert result.exit_code != 0
    assert not (tmp_path / ".aesdk.json").exists()


def test_agent_prepare_from_prompt_writes_required_blob(tmp_path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "agent",
            "prepare",
            "--prompt",
            "Run an event study for a randomized staggered rollout across GVHs with not-yet-treated controls.",
            "--outcome",
            "uptake",
            "--treatment",
            "treated",
            "--unit",
            "gvh",
            "--time",
            "month",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "blob_written=" in result.output
    assert (tmp_path / ".aesdk.json").exists()


def test_agent_template_requires_prepare_blob() -> None:
    result = CliRunner().invoke(app, ["agent", "template", "--target", "AGENTS.md"])

    assert result.exit_code == 0
    assert "agent prepare" in result.output
    assert ".aesdk.json is required" in result.output


def test_agent_ai_passport_writes_lockfile(valid_pap_dict, tmp_path) -> None:
    import yaml

    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    code = tmp_path / "analysis.do"
    prompt.write_text("Write code.", encoding="utf-8")
    output.write_text("Generated code.", encoding="utf-8")
    code.write_text("set seed 20260514\ndisplay 1\n", encoding="utf-8")
    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": "code_generation",
            "languages": ["stata"],
            "provider": "Anthropic",
            "model": "claude-sonnet-4.6",
            "model_metadata_source": "agent_reported",
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_reviewed": False,
            "reproducible_without_ai": True,
            "prompt_files": [prompt.name],
            "output_files": [output.name],
            "code_files": [code.name],
        },
    }
    pap_path = tmp_path / "pap.yaml"
    output_path = tmp_path / "ai.lock.json"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["agent", "ai-passport", "--pap", str(pap_path), "--output", str(output_path)],
    )

    assert result.exit_code == 0
    assert "ai_passport_written=" in result.output
    assert "status=pass" in result.output
    assert output_path.exists()


def test_agent_ai_passport_writes_r_lockfile(valid_pap_dict, tmp_path) -> None:
    import yaml

    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    code = tmp_path / "analysis.R"
    prompt.write_text("Write R code.", encoding="utf-8")
    output.write_text("Generated R code.", encoding="utf-8")
    code.write_text("set.seed(20260514)\nprint(1)\n", encoding="utf-8")
    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": "code_generation",
            "languages": "r",
            "provider": "Anthropic",
            "model": "claude-sonnet-4.6",
            "model_metadata_source": "agent_reported",
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
    output_path = tmp_path / "ai.lock.json"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["agent", "ai-passport", "--pap", str(pap_path), "--output", str(output_path)],
    )

    assert result.exit_code == 0
    assert "status=pass" in result.output
    assert output_path.exists()


def test_agent_ai_passport_blocks_incomplete_evidence(valid_pap_dict, tmp_path) -> None:
    import yaml

    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": "code_generation",
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_reviewed": False,
            "reproducible_without_ai": True,
            "prompt_files": ["missing_prompt.md"],
            "output_files": ["missing_output.md"],
        },
    }
    pap_path = tmp_path / "pap.yaml"
    output_path = tmp_path / "ai.lock.json"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["agent", "ai-passport", "--pap", str(pap_path), "--output", str(output_path)],
    )

    assert result.exit_code == 1
    assert "status=block" in result.output
    assert "ARTIFACT_NOT_HASHED" in result.output
    assert output_path.exists()
