"""Tests for generated Agent Skills, transcripts, and the Claude Code plugin."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from typer.testing import CliRunner

from aesdk._version import __version__
from aesdk.agent.claude_integration import build_plugin, install_claude_project
from aesdk.agent.skills import WORKFLOW_SKILL, skill_name, write_skills
from aesdk.agent.transcripts import summarize_sessions, summarize_transcript
from aesdk.cli.main import app
from aesdk.knowledge.catalog import list_method_ids

REPO = Path(__file__).resolve().parents[3]
runner = CliRunner()


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    return yaml.safe_load(text.split("---\n")[1])


def test_skills_follow_agent_skills_format(tmp_path: Path) -> None:
    written = write_skills(tmp_path)
    assert len(written) == len(list_method_ids()) + 1
    for path in written:
        meta = _frontmatter(path)
        assert meta["name"] == path.parent.name
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", meta["name"]) and len(meta["name"]) <= 64
        assert 0 < len(meta["description"]) <= 1024
    assert (tmp_path / skill_name("did") / "reference.md").exists()
    assert "aesdk agent preflight" in (tmp_path / WORKFLOW_SKILL / "SKILL.md").read_text()


def test_skill_name() -> None:
    assert skill_name("iv_2sls") == "aesdk-iv-2sls"
    assert skill_name("experimental_rct") == "aesdk-experimental-rct"


def test_committed_plugin_matches_generator(tmp_path: Path) -> None:
    """plugins/aesdk must be regenerated (scripts/build_plugin.py) when sources change."""

    build_plugin(tmp_path, version=__version__)
    committed = REPO / "plugins" / "aesdk"
    generated = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    actual = sorted(p.relative_to(committed) for p in committed.rglob("*") if p.is_file())
    assert generated == actual
    for rel in generated:
        assert (committed / rel).read_text(encoding="utf-8") == (tmp_path / rel).read_text(encoding="utf-8"), rel


def test_marketplace_points_at_plugin() -> None:
    marketplace = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    entry = marketplace["plugins"][0]
    assert entry["name"] == "aesdk"
    assert (REPO / entry["source"] / ".claude-plugin" / "plugin.json").exists()


def test_install_claude_project(tmp_path: Path) -> None:
    installed = install_claude_project(tmp_path)
    assert Path(installed["settings"]).exists()
    assert (tmp_path / ".claude" / "agents" / "aesdk-methods-reviewer.md").exists()
    assert (tmp_path / ".claude" / "commands" / "aesdk-check.md").exists()
    meta = _frontmatter(tmp_path / ".claude" / "agents" / "aesdk-methods-reviewer.md")
    assert meta["name"] == "aesdk-methods-reviewer" and meta["description"]


def test_setup_claude_flag(tmp_path: Path) -> None:
    result = runner.invoke(app, ["setup", "--output-dir", str(tmp_path), "--claude", "--format", "json"])
    data = json.loads(result.output)
    assert data["hooks_installed"]
    assert data["skills_written"] and data["claude_extras"]


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\nnot-json\n", encoding="utf-8")
    return path


def test_summarize_claude_transcript(tmp_path: Path) -> None:
    transcript = _write_jsonl(
        tmp_path / "s.jsonl",
        [
            {"type": "user", "sessionId": "s", "version": "2.1.0", "permissionMode": "default",
             "timestamp": "2026-01-01T00:00:00Z", "message": {"role": "user", "content": "Run the DiD"}},
            {"type": "assistant", "timestamp": "2026-01-01T00:01:00Z", "message": {"model": "claude-opus-5-5", "content": [
                {"type": "tool_use", "name": "mcp__aesdk__preflight", "input": {}},
                {"type": "tool_use", "name": "Agent", "input": {}},
                {"type": "tool_use", "name": "WebSearch", "input": {}},
            ]}},
            {"type": "assistant", "isSidechain": True, "message": {"model": "claude-haiku-5-5", "content": []}},
            {"type": "user", "isCompactSummary": True, "message": {"role": "user", "content": "summary"}},
            {"type": "assistant", "message": {"model": "<synthetic>", "content": []}},
        ],
    )
    summary = summarize_transcript(transcript)
    assert summary["agent_tool"] == "Claude Code"
    assert summary["models_used"] == ["claude-haiku-5-5", "claude-opus-5-5"]
    assert summary["mcp_servers"] == ["aesdk"]
    assert summary["used_subagents"] and summary["compacted"] and summary["used_web_tools"]
    assert summary["permission_modes"] == ["default"]
    assert summary["started_at"] == "2026-01-01T00:00:00Z"
    assert len(summary["transcript_sha256"]) == 64


def test_summarize_codex_rollout(tmp_path: Path) -> None:
    rollout = _write_jsonl(
        tmp_path / "rollout.jsonl",
        [
            {"type": "session_meta", "payload": {"id": "r1", "cli_version": "0.50.0"}},
            {"type": "turn_context", "payload": {"model": "gpt-5-codex", "effort": "high", "approval_policy": "on-request"}},
            {"type": "response_item", "payload": {"type": "function_call", "name": "shell"}},
            {"type": "response_item", "payload": {"type": "message", "role": "user"}},
        ],
    )
    summary = summarize_transcript(rollout)
    assert summary["agent_tool"] == "Codex"
    assert summary["models_used"] == ["gpt-5-codex"]
    assert summary["reasoning_efforts"] == ["high"]
    assert summary["permission_modes"] == ["on-request"]


def test_summarize_sessions_aggregates(tmp_path: Path) -> None:
    _write_jsonl(tmp_path / "a.jsonl", [{"type": "assistant", "message": {"model": "m1", "content": []}}])
    _write_jsonl(tmp_path / "b.jsonl", [{"type": "assistant", "message": {"model": "m2", "content": []}}])
    aggregate = summarize_sessions(tmp_path)
    assert aggregate["session_count"] == 2 and aggregate["models_used"] == ["m1", "m2"]
    assert summarize_sessions(tmp_path / "missing")["session_count"] == 0
