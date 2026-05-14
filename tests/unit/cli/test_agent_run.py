import json

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
    assert "Workflow Events" in report_path.read_text(encoding="utf-8")


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
