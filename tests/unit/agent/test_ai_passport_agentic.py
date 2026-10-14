"""AI passport evidence for agentic sessions: transcripts, autonomy, MCP, memory."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

import aesdk as ae
from aesdk.agent.runtime_metadata import write_claude_runtime_metadata
from aesdk.governance.policy import ConformanceLevel
from aesdk.protocol.validator import Validator


def _session(path: Path, model: str = "claude-opus-5-5", tools: list[str] | None = None, mode: str = "default") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {"type": "user", "sessionId": path.stem, "version": "2.1.0", "permissionMode": mode,
         "message": {"role": "user", "content": "Estimate the DiD"}},
        {"type": "assistant", "message": {"model": model, "content": [
            {"type": "tool_use", "name": name, "input": {}} for name in (tools or [])
        ]}},
    ]
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return path


def _write(tmp_path: Path, pap: dict) -> dict:
    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")
    result = ae.write_ai_passport(pap_path=pap_path, output_path=tmp_path / "ai.lock.json")
    return json.loads(result.path.read_text(encoding="utf-8"))


def _codes(passport: dict) -> set[str]:
    return {item["code"] for item in passport["findings"]}


def _ai_use(**overrides) -> dict:
    base = {
        "used": True,
        "role": "literature_summarization",
        "provider": "Anthropic",
        "agent_tool": "Claude Code",
        "model": "claude-opus-5-5",
        "model_metadata_source": "transcript",
        "prompts_archived": True,
        "raw_outputs_archived": True,
        "human_reviewed": False,
        "reproducible_without_ai": True,
        "output_files": ["out.md"],
    }
    base.update(overrides)
    return base


def test_hook_archives_are_auto_discovered(valid_pap_dict, tmp_path: Path) -> None:
    (tmp_path / "out.md").write_text("summary", encoding="utf-8")
    _session(tmp_path / ".aesdk" / "sessions" / "s1.jsonl")
    (tmp_path / ".aesdk" / "prompts.jsonl").write_text('{"prompt": "x"}\n', encoding="utf-8")

    passport = _write(tmp_path, {**valid_pap_dict, "ai_use": _ai_use()})

    assert passport["auto_discovered"]["session_files"] == [".aesdk/sessions/s1.jsonl"]
    assert passport["auto_discovered"]["prompt_files"] == [".aesdk/prompts.jsonl"]
    assert passport["field_provenance"]["session_files"] == "auto_discovered"
    assert len(passport["artifact_hashes"]["session_files"][0]["sha256"]) == 64
    assert passport["agent_sessions"]["models_used"] == ["claude-opus-5-5"]
    assert passport["status"] == "pass", passport["findings"]


def test_session_evidence_contradicting_declarations_warns(valid_pap_dict, tmp_path: Path) -> None:
    (tmp_path / "out.md").write_text("summary", encoding="utf-8")
    _session(
        tmp_path / ".aesdk" / "sessions" / "s1.jsonl",
        model="claude-sonnet-5-5",
        tools=["mcp__stata__run", "Agent", "WebFetch"],
        mode="bypassPermissions",
    )
    (tmp_path / ".aesdk" / "prompts.jsonl").write_text('{"prompt": "x"}\n', encoding="utf-8")

    passport = _write(tmp_path, {**valid_pap_dict, "ai_use": _ai_use()})
    codes = _codes(passport)

    assert {"SESSION_MODEL_MISMATCH", "MCP_SERVERS_UNDECLARED", "AGENT_FEATURE_UNDECLARED", "AGENT_AUTONOMY_UNDECLARED"} <= codes
    assert passport["status"] == "warn"


def test_missing_model_is_recoverable_from_transcript(valid_pap_dict, tmp_path: Path) -> None:
    (tmp_path / "out.md").write_text("summary", encoding="utf-8")
    _session(tmp_path / ".aesdk" / "sessions" / "s1.jsonl")
    (tmp_path / ".aesdk" / "prompts.jsonl").write_text('{"prompt": "x"}\n', encoding="utf-8")
    ai_use = _ai_use()
    del ai_use["model"]

    codes = _codes(_write(tmp_path, {**valid_pap_dict, "ai_use": ai_use}))

    assert "MODEL_ONLY_IN_TRANSCRIPT" in codes
    assert "MODEL_METADATA_MISSING" not in codes


def test_autonomous_work_without_review_warns_in_passport_and_rules(valid_pap_dict, tmp_path: Path) -> None:
    (tmp_path / "out.md").write_text("summary", encoding="utf-8")
    (tmp_path / "p.md").write_text("prompt", encoding="utf-8")
    ai_use = _ai_use(agent_autonomy="cloud_autonomous", prompt_files=["p.md"])
    pap = {**valid_pap_dict, "ai_use": ai_use}

    assert "AUTONOMOUS_WORK_UNREVIEWED" in _codes(_write(tmp_path, pap))
    result = Validator(artifact_base_dirs=[tmp_path]).validate(pap, {}, conformance=ConformanceLevel.STRICT)
    assert "AI-REP-030" in {v.rule_id for v in result.violations}


def test_declared_memory_and_session_files_must_exist(valid_pap_dict, tmp_path: Path) -> None:
    (tmp_path / "out.md").write_text("summary", encoding="utf-8")
    (tmp_path / "p.md").write_text("prompt", encoding="utf-8")
    pap = {**valid_pap_dict, "ai_use": _ai_use(prompt_files=["p.md"], memory_files=["CLAUDE.md"], session_files=["gone.jsonl"])}

    passport = _write(tmp_path, pap)
    assert passport["status"] == "block"
    result = Validator(artifact_base_dirs=[tmp_path]).validate(pap, {}, conformance=ConformanceLevel.STRICT)
    assert "AI-REP-031" in {v.rule_id for v in result.violations}

    (tmp_path / "CLAUDE.md").write_text("Use AESDK.", encoding="utf-8")
    _session(tmp_path / "gone.jsonl")
    passport = _write(tmp_path, pap)
    assert len(passport["artifact_hashes"]["memory_files"][0]["sha256"]) == 64
    assert passport["status"] == "pass", passport["findings"]


def test_claude_runtime_prefers_transcript_model(tmp_path: Path) -> None:
    transcript = _session(tmp_path / "t.jsonl", model="claude-fable-5-1", mode="acceptEdits")
    result = write_claude_runtime_metadata(output_path=tmp_path / "rt.json", workspace_path=tmp_path, transcript_path=transcript)
    session = result.metadata["session"]
    assert session["model"] == "claude-fable-5-1"
    assert session["metadata_sources"]["session_model"] == "transcript"
    assert session["approval_policy"] == "acceptEdits"
    assert result.metadata["transcript"]["models_used"] == ["claude-fable-5-1"]
    assert result.metadata["timezone"]
