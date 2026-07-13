"""Tests for one-command Claude Desktop MCP connection."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from aesdk.chat import connect_claude_desktop, default_config_path
from aesdk.cli.main import app

runner = CliRunner()


def test_default_config_path_is_os_appropriate() -> None:
    p = str(default_config_path())
    assert p.endswith("claude_desktop_config.json")
    assert "Claude" in p


def test_creates_config_when_absent(tmp_path: Path) -> None:
    cfg = tmp_path / "claude_desktop_config.json"
    result = connect_claude_desktop(config_path=cfg)
    assert result.ok and result.created
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert "aesdk" in data["mcpServers"]
    assert data["mcpServers"]["aesdk"]["args"][-2:] == ["aesdk", "mcp"]


def test_merges_without_clobbering_other_servers(tmp_path: Path) -> None:
    cfg = tmp_path / "claude_desktop_config.json"
    cfg.write_text(
        json.dumps({"mcpServers": {"other": {"command": "x"}}, "theme": "dark"}),
        encoding="utf-8",
    )
    result = connect_claude_desktop(config_path=cfg)
    assert result.ok and result.updated
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["mcpServers"]["other"] == {"command": "x"}  # preserved
    assert "aesdk" in data["mcpServers"]
    assert data["theme"] == "dark"  # other keys preserved
    assert result.backup_path and Path(result.backup_path).exists()


def test_idempotent_second_run(tmp_path: Path) -> None:
    cfg = tmp_path / "claude_desktop_config.json"
    connect_claude_desktop(config_path=cfg)
    second = connect_claude_desktop(config_path=cfg)
    assert second.already_current is True
    assert second.updated is False


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    cfg = tmp_path / "claude_desktop_config.json"
    result = connect_claude_desktop(config_path=cfg, dry_run=True)
    assert result.ok
    assert not cfg.exists()


def test_invalid_config_refused_without_force(tmp_path: Path) -> None:
    cfg = tmp_path / "claude_desktop_config.json"
    cfg.write_text("{not valid json", encoding="utf-8")
    result = connect_claude_desktop(config_path=cfg)
    assert result.ok is False
    assert "force" in (result.error or "").lower()
    # File left untouched.
    assert cfg.read_text(encoding="utf-8") == "{not valid json"


def test_invalid_config_replaced_with_force(tmp_path: Path) -> None:
    cfg = tmp_path / "claude_desktop_config.json"
    cfg.write_text("{not valid json", encoding="utf-8")
    result = connect_claude_desktop(config_path=cfg, force=True)
    assert result.ok
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert "aesdk" in data["mcpServers"]


def test_connect_cli(tmp_path: Path) -> None:
    cfg = tmp_path / "claude_desktop_config.json"
    result = runner.invoke(app, ["connect-claude", "--config-path", str(cfg)])
    assert result.exit_code == 0
    assert "Connected AESDK" in result.output
    assert cfg.exists()
