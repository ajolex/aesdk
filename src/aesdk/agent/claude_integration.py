"""Install AESDK into Claude Code: project-level setup and the plugin bundle.

Two delivery routes share the same files:

- ``install_claude_project`` writes hooks, skills, the methods-reviewer
  subagent, and slash commands into a project's ``.claude/`` folder (what
  ``aesdk setup --claude`` does). No marketplace needed.
- ``build_plugin`` generates the ``plugins/aesdk`` folder published through the
  repository's ``.claude-plugin/marketplace.json``
  (``/plugin marketplace add ajolex/aesdk`` then ``/plugin install aesdk@aesdk``).

The subagent and command Markdown live in ``aesdk/agent/templates/claude``;
skills are generated from the method packs, so the plugin never drifts from
the package.
"""

from __future__ import annotations

import json
import shutil
from importlib.resources import files
from pathlib import Path
from typing import Any

from aesdk.agent.hooks import claude_hook_settings, install_claude_hooks
from aesdk.agent.skills import write_skills

_MISSING_AESDK_NOTE = (
    "AESDK econometrics guardrails are configured for this project but the aesdk package is not "
    "installed. Offer the researcher to install it with: python -m pip install \"aesdk[mcp]\""
)


def _copy_templates(kind: str, destination: Path) -> list[Path]:
    source = files("aesdk.agent.templates").joinpath("claude").joinpath(kind)
    destination.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for item in sorted(source.iterdir(), key=lambda p: p.name):
        if item.name.endswith(".md"):
            target = destination / item.name
            target.write_text(item.read_text(encoding="utf-8"), encoding="utf-8")
            written.append(target)
    return written


def install_claude_project(project_dir: str | Path = ".", command: str = "aesdk") -> dict[str, Any]:
    """Install hooks, skills, subagent, and commands into ``<project>/.claude``."""

    root = Path(project_dir)
    claude_dir = root / ".claude"
    return {
        "settings": str(install_claude_hooks(root, command=command)),
        "skills": [str(p) for p in write_skills(claude_dir / "skills")],
        "agents": [str(p) for p in _copy_templates("agents", claude_dir / "agents")],
        "commands": [str(p) for p in _copy_templates("commands", claude_dir / "commands")],
    }


def plugin_hooks() -> dict[str, Any]:
    hooks = claude_hook_settings("aesdk")
    start = hooks["SessionStart"][0]["hooks"][0]
    start["command"] = f"{start['command']} || echo '{_MISSING_AESDK_NOTE}'"
    return {"description": "AESDK econometrics guardrails", "hooks": hooks}


def build_plugin(plugin_dir: str | Path, version: str) -> list[Path]:
    """(Re)generate the Claude Code plugin folder. Returns the files written."""

    root = Path(plugin_dir)
    for generated in ("skills", "agents", "commands"):
        shutil.rmtree(root / generated, ignore_errors=True)
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (root / "hooks").mkdir(parents=True, exist_ok=True)

    manifest = {
        "name": "aesdk",
        "version": version,
        "description": (
            "Econometrics guardrails for AI-assisted research: method skills, a methods-reviewer subagent, "
            "hooks that block analysis code which skips the AESDK methods check, the AESDK MCP tools, and "
            "automatic AI-provenance archiving. Requires `pip install \"aesdk[mcp]\"`."
        ),
        "author": {"name": "AESDK Contributors", "url": "https://github.com/ajolex/aesdk"},
        "homepage": "https://github.com/ajolex/aesdk",
        "repository": "https://github.com/ajolex/aesdk",
        "license": "Apache-2.0",
        "keywords": ["econometrics", "causal-inference", "pre-analysis-plan", "reproducibility", "research"],
    }
    written = [
        _write_json(root / ".claude-plugin" / "plugin.json", manifest),
        _write_json(root / "hooks" / "hooks.json", plugin_hooks()),
        _write_json(root / ".mcp.json", {"mcpServers": {"aesdk": {"command": "aesdk", "args": ["mcp"]}}}),
    ]
    written.extend(write_skills(root / "skills"))
    written.extend(_copy_templates("agents", root / "agents"))
    written.extend(_copy_templates("commands", root / "commands"))
    return written


def _write_json(path: Path, data: dict[str, Any]) -> Path:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path
