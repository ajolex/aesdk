"""Use AESDK from chat interfaces (ChatGPT, Claude) via presets or MCP."""

from .connect import ConnectResult, connect_claude_desktop, default_config_path
from .guide import available_targets, chat_guide

__all__ = [
    "ConnectResult",
    "available_targets",
    "chat_guide",
    "connect_claude_desktop",
    "default_config_path",
]
