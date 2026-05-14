from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import aesdk as ae


def test_write_codex_runtime_metadata_reads_config_and_git(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    config_dir = home / ".codex"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text(
        'model = "gpt-test"\nmodel_reasoning_effort = "high"\n[windows]\nsandbox = "unelevated"\n',
        encoding="utf-8",
    )
    workspace = tmp_path / "repo"
    workspace.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setattr("aesdk.agent.runtime_metadata._codex_version", lambda: "codex-cli test")
    monkeypatch.setattr(
        "aesdk.agent.runtime_metadata._git_output",
        lambda args, cwd: str(workspace) if args == ["rev-parse", "--show-toplevel"] else "abc123",
    )

    result = ae.write_codex_runtime_metadata(
        output_path=tmp_path / "codex_runtime.json",
        workspace_path=workspace,
        now=datetime(2026, 5, 14, 9, 30),
    )
    data = json.loads(result.path.read_text(encoding="utf-8"))

    assert data["codex_client"] == "codex-cli test"
    assert data["workspace"]["repo_name"] == "repo"
    assert data["workspace"]["commit_sha"] == "abc123"
    assert data["session"]["model"] == "gpt-test"
    assert data["session"]["reasoning_effort"] == "high"
    assert data["session"]["sandbox_mode"] == "unelevated"
    assert "Codex client: codex-cli test" in data["metadata_block"]


def test_write_codex_runtime_metadata_allows_explicit_session_override(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    (home / ".codex" / "config.toml").write_text('model = "config-model"\n', encoding="utf-8")
    workspace = tmp_path / "repo"
    workspace.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setattr("aesdk.agent.runtime_metadata._codex_version", lambda: "codex-cli test")
    monkeypatch.setattr("aesdk.agent.runtime_metadata._git_output", lambda args, cwd: None)

    result = ae.write_codex_runtime_metadata(
        output_path=tmp_path / "codex_runtime.json",
        workspace_path=workspace,
        session_model="status-model",
    )

    assert result.metadata["session"]["model"] == "status-model"
    assert result.metadata["session"]["metadata_sources"]["session_model"] == "explicit_argument"


def test_write_claude_runtime_metadata_reads_settings(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    config_dir = home / ".claude"
    config_dir.mkdir(parents=True)
    (config_dir / "settings.json").write_text(
        '{"model":"claude-test","reasoningEffort":"extended","permissionMode":"acceptEdits"}',
        encoding="utf-8",
    )
    workspace = tmp_path / "repo"
    workspace.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setattr(
        "aesdk.agent.runtime_metadata._command_version",
        lambda command, args: "claude-code test" if command == "claude" else None,
    )
    monkeypatch.setattr(
        "aesdk.agent.runtime_metadata._git_output",
        lambda args, cwd: str(workspace) if args == ["rev-parse", "--show-toplevel"] else "def456",
    )

    result = ae.write_claude_runtime_metadata(output_path=tmp_path / "claude_runtime.json", workspace_path=workspace)

    assert result.metadata["schema"] == "aesdk.claude_runtime.v1"
    assert result.metadata["claude_code_client"] == "claude-code test"
    assert result.metadata["session"]["model"] == "claude-test"
    assert result.metadata["session"]["reasoning_effort"] == "extended"
    assert result.metadata["session"]["approval_policy"] == "acceptEdits"
    assert result.metadata["session"]["metadata_sources"]["session_model"] == "settings.json"
    assert "Claude Code client: claude-code test" in result.metadata["metadata_block"]


def test_write_copilot_runtime_metadata_reads_vscode_settings(tmp_path, monkeypatch) -> None:
    appdata = tmp_path / "AppData"
    settings_dir = appdata / "Code" / "User"
    settings_dir.mkdir(parents=True)
    (settings_dir / "settings.json").write_text(
        """
        {
          // VS Code settings commonly allow comments.
          "github.copilot.chat.model": "gpt-copilot-test",
          "github.copilot.chat.reasoningEffort": "high",
        }
        """,
        encoding="utf-8",
    )
    workspace = tmp_path / "repo"
    workspace.mkdir()
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setattr("aesdk.agent.runtime_metadata._vscode_version", lambda: "code test")
    monkeypatch.setattr("aesdk.agent.runtime_metadata._copilot_extensions", lambda: ["GitHub.copilot@1.2.3"])
    monkeypatch.setattr(
        "aesdk.agent.runtime_metadata._git_output",
        lambda args, cwd: str(workspace) if args == ["rev-parse", "--show-toplevel"] else "fed789",
    )

    result = ae.write_copilot_runtime_metadata(output_path=tmp_path / "copilot_runtime.json", workspace_path=workspace)

    assert result.metadata["schema"] == "aesdk.copilot_runtime.v1"
    assert result.metadata["vscode_client"] == "code test"
    assert result.metadata["copilot_extensions"] == ["GitHub.copilot@1.2.3"]
    assert result.metadata["session"]["model"] == "gpt-copilot-test"
    assert result.metadata["session"]["reasoning_effort"] == "high"
    assert result.metadata["session"]["metadata_sources"]["session_model"] == "VS Code settings.json"
    assert "VS Code client: code test" in result.metadata["metadata_block"]
