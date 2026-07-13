"""One-command Claude Desktop MCP connection for non-technical researchers.

Editing ``claude_desktop_config.json`` by hand is the main friction in connecting
AESDK to Claude. `connect_claude_desktop` finds that file on the user's operating
system and adds (or updates) the ``aesdk`` MCP server entry, merging into any
existing configuration instead of overwriting it, and backing up the previous
file first. The command never installs packages; it only edits the local config.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ConnectResult:
    config_path: str | None = None
    claude_desktop_detected: bool = False
    created: bool = False
    updated: bool = False
    already_current: bool = False
    backup_path: str | None = None
    server_command: list[str] = field(default_factory=list)
    mcp_extra_installed: bool = False
    dry_run: bool = False
    error: str | None = None
    notes: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "config_path": self.config_path,
            "claude_desktop_detected": self.claude_desktop_detected,
            "created": self.created,
            "updated": self.updated,
            "already_current": self.already_current,
            "backup_path": self.backup_path,
            "server_command": self.server_command,
            "mcp_extra_installed": self.mcp_extra_installed,
            "dry_run": self.dry_run,
            "error": self.error,
            "notes": self.notes,
            "next_steps": self.next_steps,
        }

    def friendly_report(self) -> str:
        lines: list[str] = []
        if self.error:
            lines.append("Could not connect AESDK to Claude Desktop automatically.")
            lines.append(f"  Reason: {self.error}")
            if self.next_steps:
                lines.append("What to do:")
                for step in self.next_steps:
                    lines.append(f"  - {step}")
            return "\n".join(lines)
        if self.dry_run:
            lines.append("Dry run - no changes were written.")
        elif self.already_current:
            lines.append("AESDK is already connected to Claude Desktop; nothing to change.")
        elif self.created:
            lines.append("Connected AESDK to Claude Desktop (created a new config file).")
        else:
            lines.append("Connected AESDK to Claude Desktop (added AESDK to your existing config).")
        lines.append(f"  Config file: {self.config_path}")
        if not self.claude_desktop_detected:
            lines.append("")
            lines.append(
                "  WARNING: Claude Desktop was not detected here. If you are not on the computer "
                "where the Claude Desktop app is installed -- for example, inside a web chat's "
                "code sandbox -- this file will be ignored and nothing is actually connected. "
                "Run this in a terminal on your own computer instead."
            )
        if self.backup_path:
            lines.append(f"  Saved a backup of your previous config: {self.backup_path}")
        if self.notes:
            lines.append("")
            for note in self.notes:
                lines.append(f"  - {note}")
        lines.append("")
        lines.append("What happens next:")
        for step in self.next_steps:
            lines.append(f"  - {step}")
        return "\n".join(lines)


def default_config_path() -> Path:
    """Return the Claude Desktop config path for the current operating system."""
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "Claude" / "claude_desktop_config.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def _mcp_extra_installed() -> bool:
    try:
        import mcp  # noqa: F401

        return True
    except Exception:
        return False


def connect_claude_desktop(
    *,
    config_path: str | Path | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> ConnectResult:
    """Add or update the AESDK MCP server entry in Claude Desktop's config.

    Merges into any existing ``mcpServers`` without disturbing other entries.
    Backs up the previous config before writing. Never installs packages.
    """
    result = ConnectResult(dry_run=dry_run)
    path = Path(config_path) if config_path else default_config_path()
    result.config_path = str(path)
    result.mcp_extra_installed = _mcp_extra_installed()
    # Claude Desktop keeps its config in a "Claude" app-data folder. If that
    # folder (or the config file) is absent, the app is very likely not
    # installed on this machine -- e.g., we are in a web chat's code sandbox --
    # so a written config would be a throwaway that never connects anything.
    result.claude_desktop_detected = path.exists() or path.parent.exists()

    # Use the current interpreter so it works regardless of PATH.
    command = [sys.executable, "-m", "aesdk", "mcp"]
    result.server_command = command
    desired_entry = {"command": command[0], "args": command[1:]}

    existing: dict[str, Any] = {}
    if path.exists():
        try:
            text = path.read_text(encoding="utf-8-sig").strip()
            existing = json.loads(text) if text else {}
            if not isinstance(existing, dict):
                raise ValueError("config root is not an object")
        except (ValueError, OSError) as exc:
            if not force:
                result.error = (
                    f"Existing config could not be read as JSON ({type(exc).__name__}). "
                    "Re-run with --force to replace it, or fix the file."
                )
                result.next_steps = [
                    "Open the config file and check it is valid JSON, or re-run with --force.",
                    f"Config file: {path}",
                ]
                return result
            existing = {}
    else:
        result.created = True

    servers = existing.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
    if servers.get("aesdk") == desired_entry:
        result.already_current = True
    else:
        result.updated = not result.created

    if not result.claude_desktop_detected:
        result.notes.append(
            "Claude Desktop was not detected on this machine, so this config will not connect "
            "anything here. Run 'aesdk connect-claude' in a terminal on the computer where the "
            "Claude Desktop app is installed (not inside a web chat's code sandbox)."
        )
    if not result.mcp_extra_installed:
        result.notes.append(
            "The MCP tools are not installed yet. Before using AESDK in Claude, run: "
            'pip install "aesdk[mcp]"'
        )

    if dry_run:
        result.next_steps = [
            "Re-run without --dry-run to write these changes.",
            "Then fully quit and reopen Claude Desktop.",
        ]
        return result

    if result.already_current:
        result.next_steps = [
            "Fully quit and reopen Claude Desktop if you have not since installing.",
            'In a chat, say: "Use AESDK to check my study design before we write code."',
        ]
        return result

    # Write, backing up any existing file first.
    servers["aesdk"] = desired_entry
    existing["mcpServers"] = servers
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            backup = path.with_suffix(path.suffix + ".aesdk-backup")
            backup.write_text(path.read_text(encoding="utf-8-sig"), encoding="utf-8")
            result.backup_path = str(backup)
        path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        result.error = f"Could not write the config file ({type(exc).__name__}): {path}"
        result.next_steps = ["Check that Claude Desktop is installed and the folder is writable."]
        return result

    result.next_steps = [
        "Fully quit and reopen Claude Desktop so it loads the AESDK connector.",
        'In a chat, say: "Use AESDK to check my study design before we write code."',
    ]
    if not result.mcp_extra_installed:
        result.next_steps.insert(0, 'Install the MCP tools first: pip install "aesdk[mcp]"')
    return result
