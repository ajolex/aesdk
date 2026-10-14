"""Regenerate plugins/aesdk from the installed AESDK package.

Run after changing method packs, hooks, or the Claude templates:

    python scripts/build_plugin.py

CI fails if the committed plugin differs from this output.
"""

from __future__ import annotations

from pathlib import Path

from aesdk._version import __version__
from aesdk.agent.claude_integration import build_plugin

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    files = build_plugin(ROOT / "plugins" / "aesdk", version=__version__)
    print(f"wrote {len(files)} plugin files to plugins/aesdk")
