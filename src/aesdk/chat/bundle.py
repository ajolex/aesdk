"""Build an MCP Bundle (``aesdk.mcpb``) for one-click install in Claude Desktop.

An MCP Bundle is a zip with a ``manifest.json``. AESDK uses the ``uv`` server
type: the bundle declares ``aesdk[mcp]`` in ``pyproject.toml`` and the host app
installs it with uv, so the researcher double-clicks the file instead of
installing Python packages or editing ``claude_desktop_config.json``.

Spec: https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from aesdk._version import __version__

_TOOLS = [
    ("list_methods", "List the econometric methods AESDK can guide."),
    ("method_context", "Guardrails for a method: assumptions, required plan fields, diagnostics, inference."),
    ("draft_plan", "Draft a reviewable pre-analysis plan and proposal from a plain description."),
    ("preflight", "Methods check: pass/warn/block for a plan and proposal, with data-aware checks."),
    ("scan_data", "Cross-check a local dataset against the declared plan."),
    ("check_ols", "Wooldridge ten-item OLS assumption checklist on local data."),
    ("prepare_record", "Save the plan, proposal, and .aesdk.json audit record in a project folder."),
    ("workflow_report", "Write a supervisor-readable workflow.html report."),
    ("ai_passport", "Write the AI Replicability Passport (ai.lock.json)."),
]

_SERVER_PY = '''"""AESDK MCP server entry point for the MCP Bundle (installed by the host with uv)."""

from aesdk.chat.server import run

if __name__ == "__main__":
    run()
'''


def manifest(version: str = __version__) -> dict[str, Any]:
    return {
        "manifest_version": "0.4",
        "name": "aesdk",
        "display_name": "AESDK econometrics guardrails",
        "version": version,
        "description": "Checks econometric analysis plans (OLS, IV, DiD, RCTs, RDD, panel, and more) before code is written.",
        "long_description": (
            "AESDK gives Claude real pass/warn/block methods checks for applied econometrics: identifying "
            "assumptions, required pre-analysis-plan fields, diagnostics, and clustering choices, plus "
            "data-aware checks on a local dataset. Everything runs on your computer; your data is not uploaded. "
            "It does not execute analysis code."
        ),
        "author": {"name": "AESDK Contributors", "url": "https://github.com/ajolex/aesdk"},
        "repository": {"type": "git", "url": "https://github.com/ajolex/aesdk"},
        "homepage": "https://github.com/ajolex/aesdk",
        "documentation": "https://github.com/ajolex/aesdk#readme",
        "license": "Apache-2.0",
        "keywords": ["econometrics", "causal-inference", "research", "pre-analysis-plan", "reproducibility"],
        "server": {
            "type": "uv",
            "entry_point": "src/server.py",
            "mcp_config": {"command": "uv", "args": ["run", "--directory", "${__dirname}", "src/server.py"]},
        },
        "tools": [{"name": name, "description": description} for name, description in _TOOLS],
        "prompts_generated": True,
        "compatibility": {"platforms": ["darwin", "win32", "linux"], "runtimes": {"python": ">=3.10"}},
    }


def pyproject(version: str = __version__) -> str:
    return (
        "[project]\n"
        'name = "aesdk-mcpb"\n'
        f'version = "{version}"\n'
        'requires-python = ">=3.10"\n'
        f'dependencies = ["aesdk[mcp]=={version}"]\n'
    )


def write_bundle_dir(directory: str | Path, version: str = __version__) -> list[Path]:
    """Write the unpacked bundle (manifest, pyproject, entry point) to ``directory``."""

    root = Path(directory)
    (root / "src").mkdir(parents=True, exist_ok=True)
    files = {
        root / "manifest.json": json.dumps(manifest(version), indent=2) + "\n",
        root / "pyproject.toml": pyproject(version),
        root / ".mcpbignore": ".venv/\nserver/lib/\n__pycache__/\n",
        root / "src" / "server.py": _SERVER_PY,
    }
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")
    return list(files)


def build_mcpb(output: str | Path = "aesdk.mcpb", version: str = __version__) -> Path:
    """Write a ready-to-install ``.mcpb`` (zip) file."""

    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest(version), indent=2) + "\n")
        archive.writestr("pyproject.toml", pyproject(version))
        archive.writestr(".mcpbignore", ".venv/\nserver/lib/\n__pycache__/\n")
        archive.writestr("src/server.py", _SERVER_PY)
    return target
