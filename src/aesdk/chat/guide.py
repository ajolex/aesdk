"""Ready-to-paste presets and connector config for using AESDK inside chat."""

from __future__ import annotations

from importlib.resources import files

_TARGETS = {
    "chatgpt": "chatgpt.md",
    "claude": "claude.md",
    "mcp": "mcp_config.md",
}


def available_targets() -> list[str]:
    return sorted(_TARGETS)


def chat_guide(target: str) -> str:
    """Return the bundled chat preset/config for a target: chatgpt|claude|mcp."""
    key = (target or "").strip().lower()
    if key not in _TARGETS:
        raise ValueError(f"target must be one of: {', '.join(available_targets())}")
    resource = files("aesdk.chat.presets").joinpath(_TARGETS[key])
    return resource.read_text(encoding="utf-8")
