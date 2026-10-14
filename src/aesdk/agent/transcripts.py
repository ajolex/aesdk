"""Summarize coding-agent session transcripts for the AI Replicability Passport.

Agent sessions are now long, multi-turn, tool-using runs: the model can change
mid-session (``/model`` switches, fallbacks), subagents run in side contexts,
context gets compacted, and MCP servers or web tools feed in outside content.
A config file only says what model was *configured*; the transcript says what
actually ran.

Transcript formats are internal to each tool and change between versions, so
this parser is deliberately defensive: it reads JSON Lines, tolerates unknown
keys, and records what it could not determine instead of guessing. It
understands Claude Code transcripts (``~/.claude/projects/...``) and Codex
rollouts (``~/.codex/sessions/...``), and degrades to a generic scan otherwise.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

_SUBAGENT_TOOLS = {"Task", "Agent"}
_WEB_TOOLS = {"WebSearch", "WebFetch", "web_search", "web_fetch", "web_search_call"}
_COMPUTER_TOOLS = {"computer", "Computer", "browser", "computer_use"}


def _iter_records(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield record


def _content_blocks(message: Any) -> list[dict[str, Any]]:
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if isinstance(content, list):
        return [block for block in content if isinstance(block, dict)]
    return []


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize_transcript(path: str | Path) -> dict[str, Any]:
    """Return a provenance summary of one agent session transcript."""

    transcript = Path(path)
    models: Counter[str] = Counter()
    tools: Counter[str] = Counter()
    mcp_servers: set[str] = set()
    versions: set[str] = set()
    session_ids: set[str] = set()
    permission_modes: set[str] = set()
    reasoning_efforts: set[str] = set()
    timestamps: list[str] = []
    user_turns = 0
    assistant_turns = 0
    sidechain_records = 0
    subagent_calls = 0
    compactions = 0
    agent_tool = None
    records = 0

    for record in _iter_records(transcript):
        records += 1
        rtype = record.get("type")
        if isinstance(record.get("timestamp"), str):
            timestamps.append(record["timestamp"])
        if record.get("sessionId"):
            session_ids.add(str(record["sessionId"]))
        if record.get("version"):
            versions.add(str(record["version"]))
            agent_tool = agent_tool or "Claude Code"
        if record.get("permissionMode"):
            permission_modes.add(str(record["permissionMode"]))
        if record.get("isSidechain"):
            sidechain_records += 1
        if record.get("isCompactSummary") or rtype == "summary" or record.get("subtype") == "compact_boundary":
            compactions += 1

        # Claude Code: {"type": "assistant"|"user", "message": {...}}
        message = record.get("message")
        if rtype == "assistant" and isinstance(message, dict):
            assistant_turns += 1
            model = message.get("model")
            if isinstance(model, str) and model and not model.startswith("<"):
                models[model] += 1
            for block in _content_blocks(message):
                if block.get("type") == "tool_use" and block.get("name"):
                    name = str(block["name"])
                    tools[name] += 1
                    if name in _SUBAGENT_TOOLS:
                        subagent_calls += 1
                    if name.startswith("mcp__"):
                        mcp_servers.add(name.split("__")[1])
        elif rtype == "user" and isinstance(message, dict) and not record.get("isMeta"):
            content = message.get("content")
            if isinstance(content, str) or any(b.get("type") == "text" for b in _content_blocks(message)):
                user_turns += 1

        # Codex rollouts: {"type": "session_meta"|"turn_context"|"response_item", "payload": {...}}
        payload = record.get("payload")
        if isinstance(payload, dict):
            if rtype == "session_meta":
                agent_tool = "Codex"
                if payload.get("cli_version"):
                    versions.add(str(payload["cli_version"]))
                if payload.get("id"):
                    session_ids.add(str(payload["id"]))
            elif rtype == "turn_context":
                if payload.get("model"):
                    models[str(payload["model"])] += 1
                if payload.get("effort"):
                    reasoning_efforts.add(str(payload["effort"]))
                if payload.get("approval_policy"):
                    permission_modes.add(str(payload["approval_policy"]))
            elif rtype == "response_item":
                ptype = payload.get("type")
                if ptype in {"function_call", "custom_tool_call", "local_shell_call", "web_search_call"}:
                    name = str(payload.get("name") or ptype)
                    tools[name] += 1
                    if "__" in name and name.startswith("mcp"):
                        mcp_servers.add(name.split("__")[1])
                elif ptype == "message" and payload.get("role") == "user":
                    user_turns += 1
                elif ptype == "message" and payload.get("role") == "assistant":
                    assistant_turns += 1
            elif rtype == "compacted":
                compactions += 1

    tool_names = set(tools)
    limitations = []
    if not models:
        limitations.append("No model id was found in the transcript; record the model another way.")
    limitations.append("Transcript formats are internal to the agent tool; this summary is best-effort.")
    return {
        "schema": "aesdk.agent_session.v1",
        "transcript_file": str(transcript),
        "transcript_sha256": sha256_file(transcript),
        "records": records,
        "agent_tool": agent_tool,
        "agent_tool_versions": sorted(versions),
        "session_ids": sorted(session_ids),
        "models_used": sorted(models),
        "model_turns": dict(models),
        "reasoning_efforts": sorted(reasoning_efforts),
        "permission_modes": sorted(permission_modes),
        "user_turns": user_turns,
        "assistant_turns": assistant_turns,
        "tool_calls": dict(tools),
        "mcp_servers": sorted(mcp_servers),
        "subagent_calls": subagent_calls,
        "sidechain_records": sidechain_records,
        "used_subagents": bool(subagent_calls or sidechain_records),
        "compactions": compactions,
        "compacted": compactions > 0,
        "used_web_tools": bool(tool_names & _WEB_TOOLS),
        "used_computer_use": bool(tool_names & _COMPUTER_TOOLS),
        "started_at": min(timestamps) if timestamps else None,
        "ended_at": max(timestamps) if timestamps else None,
        "limitations": limitations,
    }


def summarize_sessions(sessions_dir: str | Path) -> dict[str, Any]:
    """Aggregate every archived ``*.jsonl`` session under ``sessions_dir``."""

    root = Path(sessions_dir)
    summaries = [summarize_transcript(p) for p in sorted(root.glob("*.jsonl"))] if root.is_dir() else []
    models: set[str] = set()
    servers: set[str] = set()
    modes: set[str] = set()
    efforts: set[str] = set()
    tools_used: set[str] = set()
    for item in summaries:
        models.update(item["models_used"])
        servers.update(item["mcp_servers"])
        modes.update(item["permission_modes"])
        efforts.update(item["reasoning_efforts"])
        if item.get("agent_tool"):
            tools_used.add(item["agent_tool"])
    return {
        "session_count": len(summaries),
        "agent_tools": sorted(tools_used),
        "models_used": sorted(models),
        "reasoning_efforts": sorted(efforts),
        "permission_modes": sorted(modes),
        "mcp_servers": sorted(servers),
        "used_subagents": any(s["used_subagents"] for s in summaries),
        "compacted": any(s["compacted"] for s in summaries),
        "used_web_tools": any(s["used_web_tools"] for s in summaries),
        "used_computer_use": any(s["used_computer_use"] for s in summaries),
        "sessions": summaries,
    }


def find_claude_transcripts(workspace: str | Path = ".", claude_home: str | Path | None = None) -> list[Path]:
    """Locate Claude Code transcripts for a workspace, newest first."""

    import os
    import re

    root = Path(claude_home or os.getenv("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "projects"
    encoded = re.sub(r"[^A-Za-z0-9]", "-", str(Path(workspace).resolve()))
    candidates = [root / encoded] if (root / encoded).is_dir() else [p for p in root.glob(encoded[:200] + "*") if p.is_dir()]
    files = [f for d in candidates for f in d.glob("*.jsonl")]
    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)
