"""Coding-agent hooks that turn AESDK instructions into enforced guardrails.

`AGENTS.md`/`CLAUDE.md` instructions only work if the agent obeys them. Agent
hooks run *outside* the model, so a blocked analysis actually stays blocked:

- ``session-start``: tells the agent AESDK is active and what the latest
  methods-check status is.
- ``pre-tool-use``: denies shell commands that run estimation code directly
  (``python analysis.py``, ``Rscript model.R``, ``stata -b do main.do``) instead of
  through ``aesdk agent run``, and denies writing estimation code before a
  non-blocking AESDK methods check has been recorded in ``.aesdk.json``.
- ``user-prompt``: appends each researcher prompt to ``.aesdk/prompts.jsonl`` so
  ``prompts_archived`` in the AI passport is backed by a real archive.
- ``session-end``: copies the agent session transcript into ``.aesdk/sessions/``
  with a summary (models actually used, tools, MCP servers, subagents,
  compaction) for the AI passport.

The handlers are pure functions over the hook payload (a dict) so they are easy
to test; ``run_hook`` adapts them to the Claude Code stdin/stdout protocol.

``AESDK_HOOK_MODE`` controls enforcement: ``enforce`` (default) denies,
``warn`` allows but tells the agent why it should not have, ``off`` disables
the guard. Prompt/session archiving can be disabled with
``AESDK_ARCHIVE_PROMPTS=0`` / ``AESDK_ARCHIVE_SESSIONS=0``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ARCHIVE_DIR = ".aesdk"

_PY_ESTIMATION_MODULES = {
    "statsmodels",
    "linearmodels",
    "pyfixest",
    "rdrobust",
    "rddensity",
    "scpi",
    "doubleml",
    "econml",
    "pyblp",
    "arch",
    "pymc",
    "bambi",
    "differences",
    "csdid",
    "causalml",
    "dowhy",
}
_PY_ESTIMATION_CALLS = re.compile(r"\b(?:smf?\.(?:ols|wls|gls|logit|probit|poisson|glm|mixedlm|quantreg)|LinearRegression|feols|IV2SLS|PanelOLS)\s*\(")

_R_ESTIMATION_PACKAGES = {
    "fixest", "did", "rdrobust", "MatchIt", "Synth", "gmm", "DRDID", "NonlinearDiD",
    "scpi", "np", "grf", "DoubleML", "brms", "rugarch", "AER", "plm", "estimatr",
    "lfe", "ivreg", "sandwich", "lme4", "survival", "fwildclusterboot", "did2s",
    "didimputation", "HonestDiD", "rdd", "synthdid", "modelsummary",
}
_R_ESTIMATION_CALLS = re.compile(
    r"(?<![\w.])(?:lm|glm|feols|feglm|fepois|ivreg|plm|felm|lm_robust|iv_robust|att_gt|rdrobust|"
    r"matchit|synth|gmm|brm|ugarchfit|arima|coeftest)\s*\("
)

_STATA_ESTIMATION_COMMANDS = re.compile(
    r"^\s*(?:(?:quietly|qui|noisily|capture|cap|bootstrap[^:]*|by[^:]*|xi)\s*:?\s*)*"
    r"(?:reg|regr|regre|regres|regress|areg|reghdfe|ivreg|ivregress|ivreg2|ivreghdfe|xtreg|xtivreg|"
    r"xtabond|xtdpdsys|logit|logistic|probit|ologit|oprobit|mlogit|tobit|poisson|nbreg|ppmlhdfe|"
    r"csdid|did_imputation|did_multiplegt|eventstudyinteract|jwdid|xthdidregress|didregress|"
    r"rdrobust|rdplot|teffects|psmatch2|synth|synth_runner|gmm|arima|arch|var|newey|ml\s+model|"
    r"boottest|bayes|bayesmh|dsregress|poregress|xporegress)\b",
    re.IGNORECASE | re.MULTILINE,
)

_PYTHON_EXECUTABLES = re.compile(r"^(?:.*[/\\])?(?:python(?:\d+(?:\.\d+)?)?|py|ipython|uv|pipenv|poetry)(?:\.exe)?$", re.IGNORECASE)
_R_EXECUTABLES = re.compile(r"^(?:.*[/\\])?(?:Rscript|R)(?:\.exe)?$", re.IGNORECASE)
_STATA_EXECUTABLES = re.compile(r"^(?:.*[/\\])?(?:stata|stata-se|stata-mp|statase|statamp|xstata\S*|Stata\S*)(?:\.exe)?$", re.IGNORECASE)

_CODE_EXTENSIONS = {".py": "python", ".r": "r", ".do": "stata", ".ipynb": "python"}
_WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
_SHELL_TOOLS = {"Bash", "PowerShell", "shell", "run_shell_command"}


@dataclass(frozen=True)
class HookDecision:
    """Outcome of a hook handler, independent of any agent's wire format."""

    action: str = "allow"  # allow | deny | warn | context
    reason: str = ""

    @property
    def denied(self) -> bool:
        return self.action == "deny"


@dataclass(frozen=True)
class AnalysisInvocation:
    language: str
    target: str  # script path, or "<inline>"
    reason: str


# --------------------------------------------------------------------------
# Detection helpers
# --------------------------------------------------------------------------


def contains_estimation_code(code: str, language: str) -> bool:
    """Heuristically decide whether ``code`` fits an econometric model."""

    if not code:
        return False
    language = language.lower()
    if language == "python":
        imports = set(re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][\w]*)", code, flags=re.MULTILINE))
        if imports & _PY_ESTIMATION_MODULES:
            return True
        return bool(_PY_ESTIMATION_CALLS.search(code))
    if language == "r":
        packages = set(re.findall(r"\b(?:library|require|requireNamespace)\s*\(\s*['\"]?([A-Za-z][\w.]*)", code))
        packages |= set(re.findall(r"\b([A-Za-z][\w.]*)::", code))
        if packages & _R_ESTIMATION_PACKAGES:
            return True
        return bool(_R_ESTIMATION_CALLS.search(code))
    if language == "stata":
        return bool(_STATA_ESTIMATION_COMMANDS.search(code))
    return False


def _notebook_code(text: str) -> str:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text or ""
    cells = data.get("cells", []) if isinstance(data, dict) else []
    chunks: list[str] = []
    for cell in cells:
        if isinstance(cell, dict) and cell.get("cell_type") == "code":
            source = cell.get("source", "")
            chunks.append("".join(source) if isinstance(source, list) else str(source))
    return "\n".join(chunks)


def _read_script(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return _notebook_code(text) if path.suffix.lower() == ".ipynb" else text


def _split_segments(command: str) -> list[list[str]]:
    """Split a shell command line into simple-command token lists."""

    segments: list[list[str]] = []
    for part in re.split(r"\s*(?:&&|\|\||;|\||\n)\s*", command):
        part = part.strip()
        if not part:
            continue
        try:
            tokens = shlex.split(part, posix=True)
        except ValueError:
            tokens = part.split()
        # Drop leading env assignments (FOO=1 python x.py) and wrappers.
        while tokens and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]) or tokens[0] in {"env", "time", "nohup", "sudo", "exec"}):
            tokens = tokens[1:]
        if tokens:
            segments.append(tokens)
    return segments


def _is_aesdk_governed(tokens: list[str]) -> bool:
    joined = " ".join(tokens)
    return bool(re.search(r"(?:^|[\s/\\])aesdk(?:\.exe)?\s+(?:agent\s+run|execute)\b", joined)) or bool(
        re.search(r"-m\s+aesdk\s+(?:agent\s+run|execute)\b", joined)
    )


def _resolve(cwd: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else cwd / path


def find_analysis_invocation(command: str, cwd: str | Path = ".") -> AnalysisInvocation | None:
    """Return the first segment of ``command`` that runs estimation code ungoverned."""

    base = Path(cwd)
    for tokens in _split_segments(command or ""):
        if _is_aesdk_governed(tokens):
            continue
        exe = tokens[0]
        args = tokens[1:]
        if _PYTHON_EXECUTABLES.match(exe):
            if exe.lower().startswith(("uv", "pipenv", "poetry")):
                # uv run python x.py / poetry run python x.py
                if args[:1] != ["run"]:
                    continue
                args = args[1:]
                if args and _PYTHON_EXECUTABLES.match(args[0]):
                    args = args[1:]
            if "-c" in args:
                code = args[args.index("-c") + 1] if args.index("-c") + 1 < len(args) else ""
                if contains_estimation_code(code, "python"):
                    return AnalysisInvocation("python", "<inline>", "inline Python fits an econometric model")
                continue
            if "-m" in args:
                continue  # modules (pytest, pip, aesdk itself) are not analysis scripts
            script = next((a for a in args if a.lower().endswith((".py", ".ipynb"))), None)
            if script and contains_estimation_code(_read_script(_resolve(base, script)), "python"):
                return AnalysisInvocation("python", script, f"{script} fits an econometric model")
        elif exe.lower() in {"jupyter", "papermill", "quarto"} or exe.lower().endswith(("jupyter", "papermill")):
            notebook = next((a for a in args if a.lower().endswith(".ipynb")), None)
            if notebook and contains_estimation_code(_read_script(_resolve(base, notebook)), "python"):
                return AnalysisInvocation("python", notebook, f"{notebook} fits an econometric model")
        elif _R_EXECUTABLES.match(exe):
            if "-e" in args:
                code = " ".join(args[args.index("-e") + 1 : args.index("-e") + 2])
                if contains_estimation_code(code, "r"):
                    return AnalysisInvocation("r", "<inline>", "inline R fits an econometric model")
                continue
            script = next((a for a in args if a.lower().endswith(".r")), None)
            if script is None and "-f" in args and args.index("-f") + 1 < len(args):
                script = args[args.index("-f") + 1]
            if script and contains_estimation_code(_read_script(_resolve(base, script)), "r"):
                return AnalysisInvocation("r", script, f"{script} fits an econometric model")
        elif _STATA_EXECUTABLES.match(exe):
            script = next((a for a in args if a.lower().endswith(".do")), None)
            if script and contains_estimation_code(_read_script(_resolve(base, script)), "stata"):
                return AnalysisInvocation("stata", script, f"{script} fits an econometric model")
    return None


# --------------------------------------------------------------------------
# Preparation-record lookup
# --------------------------------------------------------------------------


def latest_validation_status(cwd: str | Path = ".", blob_path: str | Path | None = None) -> str | None:
    """Return the status of the most recent AESDK validation in ``.aesdk.json``."""

    candidate = Path(blob_path or os.getenv("AESDK_BLOB") or Path(cwd) / ".aesdk.json")
    if not candidate.is_absolute():
        candidate = Path(cwd) / candidate
    try:
        data = json.loads(candidate.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    for event in reversed(data.get("events", []) or []):
        if isinstance(event, dict) and event.get("event_type") == "validate":
            status = (event.get("payload") or {}).get("status")
            return str(status) if status else None
    return None


# --------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------


def hook_mode() -> str:
    mode = (os.getenv("AESDK_HOOK_MODE") or "enforce").strip().lower()
    return mode if mode in {"enforce", "warn", "off"} else "enforce"


def _apply_mode(reason: str) -> HookDecision:
    mode = hook_mode()
    if mode == "off":
        return HookDecision()
    return HookDecision(action="deny" if mode == "enforce" else "warn", reason=reason)


def _run_suggestion(language: str, target: str) -> str:
    code = target if target != "<inline>" else "analysis" + {"python": ".py", "r": ".R", "stata": ".do"}[language]
    return (
        f"aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json --code-file {code}"
    )


def pre_tool_use(payload: dict[str, Any]) -> HookDecision:
    """Guard shell execution and code writes before the agent's tool runs."""

    if hook_mode() == "off":
        return HookDecision()
    tool = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input") or {}
    cwd = Path(payload.get("cwd") or ".")

    if tool in _SHELL_TOOLS:
        command = str(tool_input.get("command") or "")
        written = _shell_written_code_language(command)
        if written:
            write_decision = _guard_code_write(_shell_payload_text(command), written, cwd)
            if write_decision.action != "allow":
                return write_decision
        invocation = find_analysis_invocation(command, cwd)
        if invocation is None:
            return HookDecision()
        return _apply_mode(
            f"AESDK: {invocation.reason}, but it is being run directly instead of under governed "
            f"execution. Run the methods check, then execute it with `{_run_suggestion(invocation.language, invocation.target)}` "
            "so the analysis is gated by preflight and recorded in .aesdk.json. "
            "If this is not econometric analysis, explain that to the researcher; they can set AESDK_HOOK_MODE=warn."
        )

    if tool in _WRITE_TOOLS:
        file_path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        language = _CODE_EXTENSIONS.get(Path(file_path).suffix.lower())
        if not language:
            return HookDecision()
        new_code = "\n".join(
            str(tool_input.get(key) or "") for key in ("content", "new_string", "new_source")
        )
        for edit in tool_input.get("edits") or []:
            if isinstance(edit, dict):
                new_code += "\n" + str(edit.get("new_string") or "")
        if file_path.lower().endswith(".ipynb") and tool_input.get("content"):
            new_code = _notebook_code(str(tool_input.get("content")))
        return _guard_code_write(new_code, language, cwd)

    return HookDecision()


_SHELL_WRITE = re.compile(r"(?:>>?|\btee\s+(?:-a\s+)?)\s*['\"]?([^\s'\";|&<>]+\.(?:py|r|do))\b", re.IGNORECASE)


def _shell_written_code_language(command: str) -> str | None:
    """Language of a code file the shell command writes (heredoc, redirect, tee)."""

    match = _SHELL_WRITE.search(command)
    if not match:
        return None
    return _CODE_EXTENSIONS.get(Path(match.group(1)).suffix.lower())


def _shell_payload_text(command: str) -> str:
    """Command text plus each quoted argument on its own line (echo/printf bodies)."""

    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        tokens = []
    return "\n".join([command, *(token.replace("\\n", "\n") for token in tokens)])


def _guard_code_write(new_code: str, language: str, cwd: Path) -> HookDecision:
    """Deny writing estimation code until a non-blocking methods check exists."""

    if not contains_estimation_code(new_code, language):
        return HookDecision()
    status = latest_validation_status(cwd)
    if status in {"pass", "warn"}:
        return HookDecision()
    if status == "block":
        return _apply_mode(
            "AESDK: the latest methods check for this project BLOCKED the analysis, so estimation code "
            "should not be written yet. Explain the blocking issue to the researcher, fix the plan, and "
            "re-run `aesdk agent prepare --method <method> --pap pap.yaml --proposal proposal.json` until it passes."
        )
    return _apply_mode(
        "AESDK: this file fits an econometric model, but no AESDK methods check has been recorded for this "
        "project yet. First run `aesdk agent intake --prompt \"<request>\" --method <method> --output-dir .` "
        "(or `aesdk agent prepare --method <method> --pap pap.yaml --proposal proposal.json --output-dir .`), "
        "explain the result to the researcher, and only then write the analysis code."
    )


def _archive_root(payload: dict[str, Any]) -> Path:
    root = os.getenv("AESDK_ARCHIVE_DIR")
    if root:
        return Path(root)
    return Path(payload.get("cwd") or ".") / ARCHIVE_DIR


def _enabled(env_name: str) -> bool:
    return (os.getenv(env_name) or "1").strip().lower() not in {"0", "false", "no", "off"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def user_prompt(payload: dict[str, Any]) -> HookDecision:
    """Archive the researcher's prompt so prompt archiving is verifiable."""

    if not _enabled("AESDK_ARCHIVE_PROMPTS"):
        return HookDecision()
    prompt = str(payload.get("prompt") or "")
    if not prompt:
        return HookDecision()
    root = _archive_root(payload)
    root.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": _now(),
        "session_id": payload.get("session_id"),
        "sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt": prompt,
    }
    with (root / "prompts.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return HookDecision()


def session_end(payload: dict[str, Any], sessions_dir: str | Path | None = None) -> HookDecision:
    """Copy the session transcript and write a provenance summary next to it."""

    if not _enabled("AESDK_ARCHIVE_SESSIONS"):
        return HookDecision()
    transcript = payload.get("transcript_path")
    if not transcript:
        return HookDecision()
    source = Path(str(transcript)).expanduser()
    if not source.is_file():
        return HookDecision()
    from aesdk.agent.transcripts import summarize_transcript

    session_id = str(payload.get("session_id") or source.stem)
    safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id)
    sessions = Path(sessions_dir) if sessions_dir else _archive_root(payload) / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    destination = sessions / f"{safe_id}.jsonl"
    shutil.copyfile(source, destination)
    summary = summarize_transcript(destination)
    summary["archived_at"] = _now()
    summary["end_reason"] = payload.get("reason")
    summary["permission_mode"] = payload.get("permission_mode") or summary.get("permission_mode")
    (sessions / f"{safe_id}.summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return HookDecision()


def session_start_context(payload: dict[str, Any]) -> str:
    """Context injected at session start so the agent knows AESDK is active."""

    cwd = Path(payload.get("cwd") or ".")
    status = latest_validation_status(cwd)
    if status is None:
        state = "No AESDK methods check has been recorded for this project yet."
    else:
        state = f"The latest AESDK methods check for this project returned: {status}."
    mode = hook_mode()
    enforcement = {
        "enforce": "Estimation code that skips the methods check will be denied by AESDK hooks.",
        "warn": "AESDK hooks will warn (not deny) when estimation code skips the methods check.",
        "off": "AESDK enforcement hooks are turned off (AESDK_HOOK_MODE=off).",
    }[mode]
    return (
        "AESDK econometrics guardrails are active in this project. Before writing or running regression or "
        "causal-inference code, follow the aesdk-workflow skill (intake -> prepare -> preflight -> "
        f"`aesdk agent run`). {state} {enforcement}"
    )


def session_start(payload: dict[str, Any]) -> HookDecision:
    return HookDecision(action="context", reason=session_start_context(payload))


HANDLERS = {
    "session-start": session_start,
    "pre-tool-use": pre_tool_use,
    "user-prompt": user_prompt,
    "session-end": session_end,
}


def run_hook(event: str, raw_stdin: str) -> tuple[int, str, str]:
    """Run a hook handler on Claude Code's stdin JSON.

    Returns ``(exit_code, stdout, stderr)``. Archiving failures never block
    the agent; only the pre-tool-use guard can deny.
    """

    handler = HANDLERS.get(event)
    if handler is None:
        return 1, "", f"Unknown AESDK hook event: {event}. Use one of: {', '.join(sorted(HANDLERS))}"
    try:
        payload = json.loads(raw_stdin) if raw_stdin.strip() else {}
    except json.JSONDecodeError:
        return 0, "", "AESDK hook: could not parse hook input; allowing."
    try:
        decision = handler(payload)
    except Exception as exc:  # never break the agent session over archiving
        return 0, "", f"AESDK hook {event} failed: {exc}"
    if decision.action == "context":
        output = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": decision.reason}}
        return 0, json.dumps(output), ""
    if event != "pre-tool-use" or decision.action == "allow":
        return 0, "", ""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny" if decision.denied else "allow",
            "permissionDecisionReason": decision.reason,
        }
    }
    if decision.action == "warn":
        output["hookSpecificOutput"].pop("permissionDecision")
        output["hookSpecificOutput"].pop("permissionDecisionReason")
        output["hookSpecificOutput"]["additionalContext"] = decision.reason
        output["systemMessage"] = decision.reason
    return 0, json.dumps(output), ""


def claude_hook_settings(command: str = "aesdk") -> dict[str, Any]:
    """Return the ``hooks`` block for a Claude Code settings.json."""

    def entry(event: str, timeout: int | None = None) -> dict[str, Any]:
        hook: dict[str, Any] = {"type": "command", "command": f"{command} hook {event}"}
        if timeout:
            hook["timeout"] = timeout
        return hook

    return {
        "SessionStart": [{"hooks": [entry("session-start")]}],
        "PreToolUse": [
            {"matcher": "Bash|PowerShell|Write|Edit|MultiEdit|NotebookEdit", "hooks": [entry("pre-tool-use")]}
        ],
        "UserPromptSubmit": [{"hooks": [entry("user-prompt")]}],
        "Stop": [{"hooks": [entry("session-end", 30)]}],
        "SessionEnd": [{"hooks": [entry("session-end", 30)]}],
    }


def install_claude_hooks(project_dir: str | Path = ".", command: str = "aesdk") -> Path:
    """Merge AESDK hooks into ``<project>/.claude/settings.json`` (idempotent)."""

    settings_path = Path(project_dir) / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings: dict[str, Any] = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8-sig") or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"{settings_path} is not valid JSON; fix it before installing AESDK hooks") from exc
    hooks = settings.setdefault("hooks", {})
    for event, groups in claude_hook_settings(command).items():
        existing = [
            group
            for group in hooks.get(event, [])
            if not any(" hook " in str(h.get("command", "")) and "aesdk" in str(h.get("command", "")) for h in group.get("hooks", []))
        ]
        hooks[event] = existing + groups
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return settings_path
