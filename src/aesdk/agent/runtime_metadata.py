"""Runtime metadata snapshots for coding agents."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class RuntimeMetadataResult:
    path: Path
    metadata: dict[str, Any]


def write_codex_runtime_metadata(
    *,
    output_path: str | Path = "codex_runtime.json",
    workspace_path: str | Path = ".",
    surface: str = "Codex Desktop / IDE extension",
    session_model: str | None = None,
    reasoning_effort: str | None = None,
    reasoning_summary: str | None = None,
    verbosity: str | None = None,
    approval_policy: str | None = None,
    sandbox_mode: str | None = None,
    timezone: str = "Asia/Manila",
    now: datetime | None = None,
) -> RuntimeMetadataResult:
    """Write a local Codex runtime metadata snapshot for AI-passport archiving."""

    workspace = Path(workspace_path).resolve()
    user_config = Path.home() / ".codex" / "config.toml"
    project_config = workspace / ".codex" / "config.toml"
    config_values = _merged_config_values([user_config, project_config])
    repo_root = _git_output(["rev-parse", "--show-toplevel"], workspace)
    commit_sha = _git_output(["rev-parse", "HEAD"], workspace)
    repo_path = Path(repo_root) if repo_root else workspace
    active_time = now or datetime.now(ZoneInfo(timezone))

    effective_model = session_model or config_values.get("model")
    effective_reasoning_effort = reasoning_effort or config_values.get("model_reasoning_effort") or config_values.get("reasoning_effort")
    effective_reasoning_summary = reasoning_summary or config_values.get("model_reasoning_summary") or config_values.get("reasoning_summary")
    effective_verbosity = verbosity or config_values.get("model_verbosity") or config_values.get("verbosity")
    effective_approval_policy = approval_policy or config_values.get("approval_policy")
    effective_sandbox_mode = sandbox_mode or config_values.get("sandbox_mode") or config_values.get("sandbox") or config_values.get("windows.sandbox")

    metadata = {
        "schema": "aesdk.codex_runtime.v1",
        "codex_client": _codex_version(),
        "surface": surface,
        "workspace": {
            "path": str(workspace),
            "repo_name": repo_path.name,
            "repo_root": str(repo_path),
            "commit_sha": commit_sha,
        },
        "session": {
            "model": effective_model,
            "reasoning_effort": effective_reasoning_effort,
            "reasoning_summary": effective_reasoning_summary,
            "verbosity": effective_verbosity,
            "approval_policy": effective_approval_policy,
            "sandbox_mode": effective_sandbox_mode,
            "metadata_sources": _metadata_sources(
                session_model=session_model,
                reasoning_effort=reasoning_effort,
                reasoning_summary=reasoning_summary,
                verbosity=verbosity,
                approval_policy=approval_policy,
                sandbox_mode=sandbox_mode,
                config_values=config_values,
            ),
        },
        "config_sources_checked": [_config_source_record(user_config), _config_source_record(project_config)],
        "date_time": active_time.isoformat(),
        "timezone": timezone,
        "metadata_block": _metadata_block(
            codex_client=_codex_version(),
            surface=surface,
            repo_name=repo_path.name,
            commit_sha=commit_sha,
            session_model=effective_model,
            reasoning_effort=effective_reasoning_effort,
            reasoning_summary=effective_reasoning_summary,
            verbosity=effective_verbosity,
            approval_policy=effective_approval_policy,
            sandbox_mode=effective_sandbox_mode,
            date_time=active_time.strftime("%Y-%m-%d %H:%M:%S"),
            timezone=timezone,
        ),
        "limitations": [
            "Values are collected from local Codex CLI/config and explicit CLI overrides.",
            "If the active session model differs from config, archive a /status or /model transcript or pass the value explicitly.",
        ],
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return RuntimeMetadataResult(path=output, metadata=metadata)


def write_claude_runtime_metadata(
    *,
    output_path: str | Path = "claude_runtime.json",
    workspace_path: str | Path = ".",
    surface: str = "Claude Code",
    session_model: str | None = None,
    reasoning_effort: str | None = None,
    reasoning_summary: str | None = None,
    verbosity: str | None = None,
    approval_policy: str | None = None,
    sandbox_mode: str | None = None,
    timezone: str = "Asia/Manila",
    now: datetime | None = None,
) -> RuntimeMetadataResult:
    """Write a local Claude Code runtime metadata snapshot for AI-passport archiving."""

    workspace = Path(workspace_path).resolve()
    user_config = Path.home() / ".claude" / "settings.json"
    project_config = workspace / ".claude" / "settings.json"
    config_values = _merged_json_values([user_config, project_config])
    repo_root = _git_output(["rev-parse", "--show-toplevel"], workspace)
    commit_sha = _git_output(["rev-parse", "HEAD"], workspace)
    repo_path = Path(repo_root) if repo_root else workspace
    active_time = now or datetime.now(ZoneInfo(timezone))
    effective_model = session_model or _first_config(config_values, ["model", "defaultModel", "session.model"])
    effective_reasoning_effort = reasoning_effort or _first_config(config_values, ["reasoningEffort", "reasoning_effort", "session.reasoningEffort"])
    effective_reasoning_summary = reasoning_summary or _first_config(config_values, ["reasoningSummary", "reasoning_summary"])
    effective_verbosity = verbosity or _first_config(config_values, ["verbosity", "outputVerbosity"])
    effective_approval_policy = approval_policy or _first_config(config_values, ["permissionMode", "approvalPolicy", "permissions.defaultMode"])
    effective_sandbox_mode = sandbox_mode or _first_config(config_values, ["sandboxMode", "sandbox.mode"])

    metadata = _runtime_metadata(
        schema="aesdk.claude_runtime.v1",
        client_key="claude_code_client",
        client_value=_command_version("claude", ["--version"]),
        surface=surface,
        workspace=workspace,
        repo_path=repo_path,
        commit_sha=commit_sha,
        session_model=effective_model,
        reasoning_effort=effective_reasoning_effort,
        reasoning_summary=effective_reasoning_summary,
        verbosity=effective_verbosity,
        approval_policy=effective_approval_policy,
        sandbox_mode=effective_sandbox_mode,
        config_sources=[user_config, project_config],
        metadata_sources=_metadata_sources(
            session_model=session_model,
            reasoning_effort=reasoning_effort,
            reasoning_summary=reasoning_summary,
            verbosity=verbosity,
            approval_policy=approval_policy,
            sandbox_mode=sandbox_mode,
            config_values=config_values,
            config_key_map={
                "session_model": ("model", "defaultModel", "session.model"),
                "reasoning_effort": ("reasoningEffort", "reasoning_effort", "session.reasoningEffort"),
                "reasoning_summary": ("reasoningSummary", "reasoning_summary"),
                "verbosity": ("verbosity", "outputVerbosity"),
                "approval_policy": ("permissionMode", "approvalPolicy", "permissions.defaultMode"),
                "sandbox_mode": ("sandboxMode", "sandbox.mode"),
            },
            config_source_label="settings.json",
        ),
        active_time=active_time,
        timezone=timezone,
        metadata_title="Claude Code client",
        config_sources_label="user ~/.claude/settings.json and project .claude/settings.json",
        limitations=[
            "Values are collected from local Claude Code CLI/settings and explicit CLI overrides.",
            "If Claude Code does not expose the active model in settings, archive a status transcript or pass the value explicitly.",
        ],
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return RuntimeMetadataResult(path=output, metadata=metadata)


def write_copilot_runtime_metadata(
    *,
    output_path: str | Path = "copilot_runtime.json",
    workspace_path: str | Path = ".",
    surface: str = "VS Code / GitHub Copilot",
    session_model: str | None = None,
    reasoning_effort: str | None = None,
    reasoning_summary: str | None = None,
    verbosity: str | None = None,
    approval_policy: str | None = None,
    sandbox_mode: str | None = None,
    timezone: str = "Asia/Manila",
    now: datetime | None = None,
) -> RuntimeMetadataResult:
    """Write a local VS Code Copilot runtime metadata snapshot for AI-passport archiving."""

    workspace = Path(workspace_path).resolve()
    user_config = _vscode_user_settings_path()
    project_config = workspace / ".vscode" / "settings.json"
    config_values = _merged_json_values([user_config, project_config])
    repo_root = _git_output(["rev-parse", "--show-toplevel"], workspace)
    commit_sha = _git_output(["rev-parse", "HEAD"], workspace)
    repo_path = Path(repo_root) if repo_root else workspace
    active_time = now or datetime.now(ZoneInfo(timezone))
    effective_model = session_model or _first_config(
        config_values,
        ["github.copilot.chat.model", "github.copilot.chat.defaultModel", "copilot.model"],
    )
    effective_reasoning_effort = reasoning_effort or _first_config(config_values, ["github.copilot.chat.reasoningEffort", "copilot.reasoningEffort"])
    effective_reasoning_summary = reasoning_summary or _first_config(config_values, ["github.copilot.chat.reasoningSummary"])
    effective_verbosity = verbosity or _first_config(config_values, ["github.copilot.chat.verbosity"])
    effective_approval_policy = approval_policy or _first_config(config_values, ["github.copilot.chat.approvalPolicy"])
    effective_sandbox_mode = sandbox_mode or _first_config(config_values, ["github.copilot.chat.sandboxMode"])

    metadata = _runtime_metadata(
        schema="aesdk.copilot_runtime.v1",
        client_key="vscode_client",
        client_value=_vscode_version(),
        surface=surface,
        workspace=workspace,
        repo_path=repo_path,
        commit_sha=commit_sha,
        session_model=effective_model,
        reasoning_effort=effective_reasoning_effort,
        reasoning_summary=effective_reasoning_summary,
        verbosity=effective_verbosity,
        approval_policy=effective_approval_policy,
        sandbox_mode=effective_sandbox_mode,
        config_sources=[user_config, project_config],
        metadata_sources=_metadata_sources(
            session_model=session_model,
            reasoning_effort=reasoning_effort,
            reasoning_summary=reasoning_summary,
            verbosity=verbosity,
            approval_policy=approval_policy,
            sandbox_mode=sandbox_mode,
            config_values=config_values,
            config_key_map={
                "session_model": ("github.copilot.chat.model", "github.copilot.chat.defaultModel", "copilot.model"),
                "reasoning_effort": ("github.copilot.chat.reasoningEffort", "copilot.reasoningEffort"),
                "reasoning_summary": ("github.copilot.chat.reasoningSummary",),
                "verbosity": ("github.copilot.chat.verbosity",),
                "approval_policy": ("github.copilot.chat.approvalPolicy",),
                "sandbox_mode": ("github.copilot.chat.sandboxMode",),
            },
            config_source_label="VS Code settings.json",
        ),
        active_time=active_time,
        timezone=timezone,
        metadata_title="VS Code client",
        config_sources_label="user VS Code settings.json and workspace .vscode/settings.json",
        limitations=[
            "Values are collected from local VS Code/Copilot extension metadata, settings, and explicit CLI overrides.",
            "Copilot may not expose the active chat model in settings; archive a status/model transcript or pass the value explicitly when needed.",
        ],
    )
    metadata["copilot_extensions"] = _copilot_extensions()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return RuntimeMetadataResult(path=output, metadata=metadata)


def _codex_version() -> str | None:
    return _command_version("codex", ["--version"])


def _command_version(command: str, args: list[str]) -> str | None:
    executable = shutil.which(command)
    if not executable:
        return None
    try:
        result = subprocess.run([executable, *args], check=False, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    text = (result.stdout or result.stderr).strip()
    return text or None


def _git_output(args: list[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(["git", *args], cwd=str(cwd), check=False, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _merged_config_values(paths: list[Path]) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in paths:
        if path.exists() and path.is_file():
            values.update(_parse_simple_toml(path.read_text(encoding="utf-8-sig")))
    return values


def _merged_json_values(paths: list[Path]) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in paths:
        if path.exists() and path.is_file():
            try:
                loaded = _loads_jsonc(path.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError:
                continue
            if isinstance(loaded, dict):
                values.update(_flatten_json(loaded))
    return values


def _loads_jsonc(text: str) -> Any:
    return json.loads(_strip_trailing_commas(_strip_json_comments(text)))


def _strip_json_comments(text: str) -> str:
    output: list[str] = []
    in_string = False
    quote = ""
    escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                in_string = False
            index += 1
            continue
        if char in {'"', "'"}:
            in_string = True
            quote = char
            output.append(char)
            index += 1
            continue
        if char == "/" and next_char == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue
        if char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(text) and not (text[index] == "*" and text[index + 1] == "/"):
                index += 1
            index += 2
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _strip_trailing_commas(text: str) -> str:
    return re.sub(r",\s*([}\]])", r"\1", text)


def _flatten_json(data: dict[str, Any], prefix: str = "") -> dict[str, str]:
    values: dict[str, str] = {}
    for key, value in data.items():
        active = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            values.update(_flatten_json(value, active))
        elif isinstance(value, (str, int, float, bool)):
            values[active] = str(value)
    return values


def _first_config(values: dict[str, str], keys: list[str]) -> str | None:
    for key in keys:
        if key in values:
            return values[key]
    return None


def _parse_simple_toml(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    section: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = [part.strip().strip('"').strip("'") for part in line.strip("[]").split(".") if part.strip()]
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*=\s*(.+)$", line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip().strip('"').strip("'")
        values[key] = value
        if section:
            values[".".join([*section, key])] = value
    return values


def _config_source_record(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if path.exists() and path.is_file():
        record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return record


def _metadata_sources(**kwargs: Any) -> dict[str, str]:
    config_values = kwargs.pop("config_values")
    config_key_map = kwargs.pop("config_key_map", None)
    config_source_label = kwargs.pop("config_source_label", "config.toml")
    sources: dict[str, str] = {}
    mapping = config_key_map or {
        "session_model": ("model",),
        "reasoning_effort": ("model_reasoning_effort", "reasoning_effort"),
        "reasoning_summary": ("model_reasoning_summary", "reasoning_summary"),
        "verbosity": ("model_verbosity", "verbosity"),
        "approval_policy": ("approval_policy",),
        "sandbox_mode": ("sandbox_mode", "sandbox", "windows.sandbox"),
    }
    for field, config_keys in mapping.items():
        if kwargs.get(field) is not None:
            sources[field] = "explicit_argument"
        elif any(key in config_values for key in config_keys):
            sources[field] = config_source_label
        else:
            sources[field] = "unavailable"
    return sources


def _runtime_metadata(
    *,
    schema: str,
    client_key: str,
    client_value: str | None,
    surface: str,
    workspace: Path,
    repo_path: Path,
    commit_sha: str | None,
    session_model: str | None,
    reasoning_effort: str | None,
    reasoning_summary: str | None,
    verbosity: str | None,
    approval_policy: str | None,
    sandbox_mode: str | None,
    config_sources: list[Path],
    metadata_sources: dict[str, str],
    active_time: datetime,
    timezone: str,
    metadata_title: str,
    config_sources_label: str,
    limitations: list[str],
) -> dict[str, Any]:
    return {
        "schema": schema,
        client_key: client_value,
        "surface": surface,
        "workspace": {
            "path": str(workspace),
            "repo_name": repo_path.name,
            "repo_root": str(repo_path),
            "commit_sha": commit_sha,
        },
        "session": {
            "model": session_model,
            "reasoning_effort": reasoning_effort,
            "reasoning_summary": reasoning_summary,
            "verbosity": verbosity,
            "approval_policy": approval_policy,
            "sandbox_mode": sandbox_mode,
            "metadata_sources": metadata_sources,
        },
        "config_sources_checked": [_config_source_record(path) for path in config_sources],
        "date_time": active_time.isoformat(),
        "timezone": timezone,
        "metadata_block": _metadata_block(
            client_label=metadata_title,
            client_value=client_value,
            surface=surface,
            repo_name=repo_path.name,
            commit_sha=commit_sha,
            session_model=session_model,
            reasoning_effort=reasoning_effort,
            reasoning_summary=reasoning_summary,
            verbosity=verbosity,
            approval_policy=approval_policy,
            sandbox_mode=sandbox_mode,
            config_sources_label=config_sources_label,
            date_time=active_time.strftime("%Y-%m-%d %H:%M:%S"),
            timezone=timezone,
        ),
        "limitations": limitations,
    }


def _vscode_version() -> str | None:
    return _command_version("code", ["--version"])


def _copilot_extensions() -> list[str]:
    executable = shutil.which("code")
    if not executable:
        return []
    try:
        result = subprocess.run([executable, "--list-extensions", "--show-versions"], check=False, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if "copilot" in line.lower()]


def _vscode_user_settings_path() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "Code" / "User" / "settings.json"
    return Path.home() / ".config" / "Code" / "User" / "settings.json"


def _metadata_block(
    *,
    surface: str,
    repo_name: str,
    commit_sha: str | None,
    session_model: str | None,
    reasoning_effort: str | None,
    reasoning_summary: str | None,
    verbosity: str | None,
    approval_policy: str | None,
    sandbox_mode: str | None,
    date_time: str,
    timezone: str,
    client_label: str = "Codex client",
    client_value: str | None = None,
    codex_client: str | None = None,
    config_sources_label: str = "user ~/.codex/config.toml and project .codex/config.toml",
) -> str:
    active_client = client_value if client_value is not None else codex_client
    return "\n".join(
        [
            f"{client_label}: {active_client or 'unavailable'}",
            f"Surface: {surface}",
            f"Workspace/repo: {repo_name} {commit_sha or 'unavailable'}",
            f"Session model: {session_model or 'unavailable'}",
            f"Reasoning effort: {reasoning_effort or 'unavailable'}",
            f"Reasoning summary: {reasoning_summary or 'unavailable'}",
            f"Verbosity: {verbosity or 'unavailable'}",
            f"Approval policy: {approval_policy or 'unavailable'}",
            f"Sandbox mode: {sandbox_mode or 'unavailable'}",
            f"Config sources checked: {config_sources_label}",
            f"Date/time: {date_time}, {timezone}",
        ]
    )
