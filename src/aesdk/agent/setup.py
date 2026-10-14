"""Plain-language onboarding for non-technical researchers.

`aesdk setup` is the one entry point a research analyst, associate, or faculty
member should ever need to think about. It verifies that AESDK is installed and
working, optionally drops the ready-made assistant instructions
(``AGENTS.md`` / ``CLAUDE.md``) into the project, and prints an encouraging,
jargon-free readiness summary with plain next steps.

It never installs packages or changes system settings on its own; it checks and
reports. Missing optional runtimes (Stata, R) are reported gently, not as
errors, because most workflows are Python and do not need them.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import Any

from aesdk.knowledge.catalog import list_method_ids
from aesdk.sandbox.runner import (
    _R_EXECUTABLE_CANDIDATES,
    _R_EXECUTABLE_ENV,
    _STATA_EXECUTABLE_CANDIDATES,
    _STATA_EXECUTABLE_ENV,
)

_VALID_TEMPLATES = {"AGENTS.md", "CLAUDE.md"}


@dataclass
class SetupResult:
    ready: bool = False
    aesdk_version: str | None = None
    python_version: str | None = None
    python_executable: str | None = None
    working_directory: str | None = None
    working_directory_writable: bool = False
    method_registry_ok: bool = False
    method_count: int = 0
    stata_available: bool = False
    r_available: bool = False
    templates_written: list[str] = field(default_factory=list)
    templates_present: list[str] = field(default_factory=list)
    hooks_installed: str | None = None
    skills_written: list[str] = field(default_factory=list)
    claude_extras: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "aesdk_version": self.aesdk_version,
            "python_version": self.python_version,
            "python_executable": self.python_executable,
            "working_directory": self.working_directory,
            "working_directory_writable": self.working_directory_writable,
            "method_registry_ok": self.method_registry_ok,
            "method_count": self.method_count,
            "stata_available": self.stata_available,
            "r_available": self.r_available,
            "templates_written": self.templates_written,
            "templates_present": self.templates_present,
            "hooks_installed": self.hooks_installed,
            "skills_written": self.skills_written,
            "claude_extras": self.claude_extras,
            "notes": self.notes,
            "next_steps": self.next_steps,
        }

    def friendly_report(self) -> str:
        lines: list[str] = []
        if self.ready:
            lines.append("AESDK is set up and ready.")
            lines.append("")
            lines.append(
                f"You have AESDK {self.aesdk_version or 'installed'} and it can guide "
                f"{self.method_count} econometric methods (OLS, IV, DiD, RCTs, panel, "
                "and more)."
            )
        else:
            lines.append("AESDK is installed but a couple of things still need attention.")
        if self.templates_written:
            lines.append("")
            lines.append(
                "Saved assistant instructions to your project: "
                + ", ".join(self.templates_written)
                + ". You do not need to open or edit these files."
            )
        if self.templates_present:
            lines.append("")
            lines.append(
                "Kept your existing instruction file(s): " + ", ".join(self.templates_present) + "."
            )
        if self.hooks_installed:
            lines.append("")
            lines.append(
                "Turned on automatic enforcement for Claude Code: analysis code that skips the "
                "methods check is stopped, and prompts and session records are saved under .aesdk/."
            )
        if self.skills_written:
            lines.append("")
            lines.append(
                f"Saved {len(self.skills_written)} AESDK skills so assistants load method guidance "
                "only when it is relevant."
            )
        if self.claude_extras:
            lines.append("")
            lines.append(
                "Added an independent methods-reviewer assistant and the /aesdk-check and "
                "/aesdk-report shortcuts for Claude Code."
            )
        if self.notes:
            lines.append("")
            lines.append("Good to know:")
            for note in self.notes:
                lines.append(f"  - {note}")
        lines.append("")
        lines.append("What happens next:")
        for step in self.next_steps:
            lines.append(f"  - {step}")
        return "\n".join(lines)


def _resolve_executable(configured: str | None, candidates: tuple[str, ...]) -> str | None:
    if configured:
        located = shutil.which(configured) or (configured if Path(configured).exists() else None)
        if located:
            return located
    for candidate in candidates:
        located = shutil.which(candidate)
        if located:
            return located
    return None


def _package_version() -> str | None:
    try:
        from aesdk._version import __version__

        return __version__
    except Exception:  # pragma: no cover - version module always present
        return None


def run_setup(
    *,
    output_dir: str | Path = ".",
    write_templates: str = "both",
    force: bool = False,
    install_hooks: bool = False,
    write_skills: bool = False,
    claude: bool = False,
) -> SetupResult:
    """Verify the environment, optionally write assistant templates, and report.

    ``write_templates`` is one of ``both``, ``AGENTS.md``, ``CLAUDE.md``, or
    ``none``. Existing files are never overwritten unless ``force`` is true.
    ``install_hooks`` merges AESDK's Claude Code hooks into
    ``.claude/settings.json``; ``write_skills`` writes AESDK Agent Skills into
    ``.claude/skills`` and ``.agents/skills``. ``claude`` installs the full
    Claude Code integration (hooks, skills, methods-reviewer subagent, and
    slash commands) into ``.claude/``.
    """

    result = SetupResult()
    result.aesdk_version = _package_version()
    result.python_version = platform.python_version()
    result.python_executable = sys.executable

    out = Path(output_dir)
    result.working_directory = str(out.resolve())
    try:
        out.mkdir(parents=True, exist_ok=True)
        probe = out / ".aesdk_setup_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        result.working_directory_writable = True
    except OSError:
        result.working_directory_writable = False

    try:
        methods = list(list_method_ids())
        result.method_registry_ok = bool(methods)
        result.method_count = len(methods)
    except Exception:
        result.method_registry_ok = False

    result.stata_available = bool(
        _resolve_executable(os.getenv(_STATA_EXECUTABLE_ENV), _STATA_EXECUTABLE_CANDIDATES)
    )
    result.r_available = bool(
        _resolve_executable(os.getenv(_R_EXECUTABLE_ENV), _R_EXECUTABLE_CANDIDATES)
    )

    # Optionally write the ready-made assistant instructions.
    targets: list[str] = []
    choice = (write_templates or "both").strip().lower()
    if choice == "both":
        targets = ["AGENTS.md", "CLAUDE.md"]
    elif choice == "none":
        targets = []
    else:
        for name in _VALID_TEMPLATES:
            if name.lower() == choice:
                targets = [name]
                break
    for name in targets:
        destination = out / name
        if destination.exists() and not force:
            result.templates_present.append(name)
            continue
        try:
            source = files("aesdk.agent.templates").joinpath(name)
            destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            result.templates_written.append(name)
        except Exception:
            result.notes.append(f"Could not write {name}; you can generate it with 'aesdk agent template'.")

    if claude:
        try:
            from aesdk.agent.claude_integration import install_claude_project

            installed = install_claude_project(out)
            result.hooks_installed = installed["settings"]
            result.skills_written.extend(installed["skills"])
            result.claude_extras = installed["agents"] + installed["commands"]
        except Exception as exc:
            result.notes.append(f"Could not install the Claude Code integration: {exc}")
    if install_hooks and not result.hooks_installed:
        try:
            from aesdk.agent.hooks import install_claude_hooks

            result.hooks_installed = str(install_claude_hooks(out))
        except Exception as exc:
            result.notes.append(f"Could not install Claude Code hooks: {exc}")
    if write_skills:
        try:
            from aesdk.agent.skills import write_skills as _write_skills

            roots = [out / ".agents" / "skills"]
            if not claude:
                roots.insert(0, out / ".claude" / "skills")
            for root in roots:
                result.skills_written.extend(str(p) for p in _write_skills(root))
        except Exception as exc:
            result.notes.append(f"Could not write AESDK skills: {exc}")

    result.ready = bool(
        result.aesdk_version
        and result.method_registry_ok
        and result.working_directory_writable
    )

    # Gentle, plain-language notes for optional runtimes.
    if not result.stata_available:
        result.notes.append(
            "Stata was not detected. That is fine unless you plan to run Stata (.do) files; "
            "point AESDK to it later by setting AESDK_STATA if needed."
        )
    if not result.r_available:
        result.notes.append(
            "R was not detected. That is fine unless you plan to run R scripts; "
            "point AESDK to it later by setting AESDK_R if needed."
        )
    if not result.working_directory_writable:
        result.notes.append(
            "This folder is not writable, so the audit record cannot be saved here. "
            "Try running from your project folder."
        )

    # Plain-language next steps.
    if result.ready:
        result.next_steps = [
            "Just describe your analysis to your AI assistant in plain language "
            "(what you want to estimate, and what your data looks like).",
            "The assistant runs AESDK's methods check for you before writing any code "
            "and explains anything it finds; you do not run any commands.",
            "If the assistant flags a concern, it will tell you what it means and what to do; "
            "the analysis proceeds once you say to.",
        ]
    else:
        if not result.aesdk_version:
            result.next_steps.append(
                "Ask your assistant to install AESDK (pip install aesdk), then run setup again."
            )
        if not result.method_registry_ok:
            result.next_steps.append(
                "AESDK's method library did not load; ask your assistant to reinstall AESDK."
            )
        if not result.working_directory_writable:
            result.next_steps.append("Run setup again from a folder you can write to.")
        if not result.next_steps:
            result.next_steps.append("Ask your assistant to help finish the AESDK setup.")

    return result
