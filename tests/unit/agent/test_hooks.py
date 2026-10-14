"""Tests for the coding-agent hooks that enforce AESDK guardrails."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from aesdk.agent.hooks import (
    claude_hook_settings,
    contains_estimation_code,
    find_analysis_invocation,
    install_claude_hooks,
    latest_validation_status,
    pre_tool_use,
    run_hook,
    session_end,
    user_prompt,
)


@pytest.fixture(autouse=True)
def _default_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AESDK_HOOK_MODE", raising=False)
    monkeypatch.delenv("AESDK_BLOB", raising=False)
    monkeypatch.delenv("AESDK_ARCHIVE_DIR", raising=False)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "analysis.py").write_text("import statsmodels.formula.api as smf\nsmf.ols('y ~ x', d).fit()\n")
    (tmp_path / "util.py").write_text("print('hello')\n")
    (tmp_path / "model.R").write_text("library(fixest)\nfeols(y ~ x | id, data = d)\n")
    (tmp_path / "main.do").write_text("use data, clear\nquietly reghdfe y x, absorb(id) vce(cluster id)\n")
    return tmp_path


def _bash(command: str, cwd: Path) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}


def _record(project: Path, status: str) -> None:
    (project / ".aesdk.json").write_text(
        json.dumps({"events": [{"event_type": "validate", "payload": {"status": status}}]})
    )


@pytest.mark.parametrize(
    ("code", "language", "expected"),
    [
        ("import statsmodels.api as sm", "python", True),
        ("from linearmodels.iv import IV2SLS", "python", True),
        ("import pandas as pd\nprint(pd.__version__)", "python", False),
        ("library(fixest)", "r", True),
        ("fit <- lm(y ~ x, data = d)", "r", True),
        ("x <- read.csv('a.csv')", "r", False),
        ("regress y x, robust", "stata", True),
        ("cap: xtreg y x, fe", "stata", True),
        ("use data, clear\nsummarize", "stata", False),
    ],
)
def test_contains_estimation_code(code: str, language: str, expected: bool) -> None:
    assert contains_estimation_code(code, language) is expected


@pytest.mark.parametrize(
    "command",
    [
        "python analysis.py",
        "python3 -u analysis.py --flag",
        "cd . && python analysis.py | tee log.txt",
        "FOO=1 python analysis.py",
        "uv run python analysis.py",
        "python -c 'import statsmodels.api as sm'",
        "Rscript model.R",
        "Rscript -e 'library(fixest)'",
        "stata-mp -b do main.do",
    ],
)
def test_direct_analysis_execution_is_denied(project: Path, command: str) -> None:
    decision = pre_tool_use(_bash(command, project))
    assert decision.denied
    assert "aesdk agent run" in decision.reason


@pytest.mark.parametrize(
    "command",
    [
        "python util.py",
        "python -m pytest -q",
        "aesdk agent run --method did --pap pap.yaml --proposal proposal.json --code-file analysis.py",
        "python -m aesdk agent run --method did --pap p.yaml --proposal q.json --code-file model.R",
        "ls -la && git status",
        "python missing.py",
    ],
)
def test_other_commands_are_allowed(project: Path, command: str) -> None:
    assert pre_tool_use(_bash(command, project)).action == "allow"


def test_find_analysis_invocation_reports_language(project: Path) -> None:
    invocation = find_analysis_invocation("Rscript model.R", project)
    assert invocation is not None and invocation.language == "r" and invocation.target == "model.R"


def test_writing_estimation_code_requires_a_recorded_check(project: Path) -> None:
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(project / "new.py"), "content": "import pyfixest as pf\n"},
        "cwd": str(project),
    }
    denied = pre_tool_use(payload)
    assert denied.denied and "no AESDK methods check" in denied.reason

    _record(project, "block")
    blocked = pre_tool_use(payload)
    assert blocked.denied and "BLOCKED" in blocked.reason

    _record(project, "warn")
    assert pre_tool_use(payload).action == "allow"


def test_non_estimation_writes_are_allowed(project: Path) -> None:
    for payload in (
        {"tool_name": "Write", "tool_input": {"file_path": "clean.py", "content": "import pandas"}, "cwd": str(project)},
        {"tool_name": "Write", "tool_input": {"file_path": "notes.md", "content": "import statsmodels"}, "cwd": str(project)},
        {"tool_name": "Edit", "tool_input": {"file_path": "a.do", "new_string": "summarize y"}, "cwd": str(project)},
    ):
        assert pre_tool_use(payload).action == "allow"


def test_edit_and_multiedit_inspect_new_code(project: Path) -> None:
    edit = {"tool_name": "Edit", "tool_input": {"file_path": "a.do", "new_string": "reg y x"}, "cwd": str(project)}
    multi = {
        "tool_name": "MultiEdit",
        "tool_input": {"file_path": "a.R", "edits": [{"old_string": "a", "new_string": "glm(y ~ x)"}]},
        "cwd": str(project),
    }
    assert pre_tool_use(edit).denied
    assert pre_tool_use(multi).denied


def test_modes(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AESDK_HOOK_MODE", "warn")
    assert pre_tool_use(_bash("python analysis.py", project)).action == "warn"
    monkeypatch.setenv("AESDK_HOOK_MODE", "off")
    assert pre_tool_use(_bash("python analysis.py", project)).action == "allow"


def test_latest_validation_status_uses_last_validate_event(project: Path) -> None:
    assert latest_validation_status(project) is None
    (project / ".aesdk.json").write_text(
        json.dumps(
            {
                "events": [
                    {"event_type": "validate", "payload": {"status": "block"}},
                    {"event_type": "execute", "payload": {"status": "pass"}},
                    {"event_type": "validate", "payload": {"status": "pass"}},
                ]
            }
        )
    )
    assert latest_validation_status(project) == "pass"


def test_run_hook_wire_format(project: Path) -> None:
    code, out, _ = run_hook("pre-tool-use", json.dumps(_bash("python analysis.py", project)))
    assert code == 0
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["hookEventName"] == "PreToolUse"
    assert decision["permissionDecision"] == "deny"
    assert run_hook("pre-tool-use", json.dumps(_bash("ls", project))) == (0, "", "")
    assert run_hook("pre-tool-use", "not json")[0] == 0
    assert run_hook("nope", "{}")[0] == 1

    code, out, _ = run_hook("session-start", json.dumps({"cwd": str(project)}))
    context = json.loads(out)["hookSpecificOutput"]
    assert context["hookEventName"] == "SessionStart"
    assert "No AESDK methods check" in context["additionalContext"]


def test_user_prompt_archive(project: Path) -> None:
    user_prompt({"prompt": "Estimate the DiD effect", "session_id": "s1", "cwd": str(project)})
    lines = (project / ".aesdk" / "prompts.jsonl").read_text().splitlines()
    record = json.loads(lines[0])
    assert record["prompt"] == "Estimate the DiD effect" and record["session_id"] == "s1"
    assert len(record["sha256"]) == 64


def test_user_prompt_archive_can_be_disabled(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AESDK_ARCHIVE_PROMPTS", "0")
    user_prompt({"prompt": "x", "cwd": str(project)})
    assert not (project / ".aesdk").exists()


def test_session_end_archives_transcript(project: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    transcript = tmp_path_factory.mktemp("t") / "abc.jsonl"
    transcript.write_text(
        "\n".join(
            json.dumps(r)
            for r in [
                {"type": "user", "sessionId": "abc", "version": "2.1.0", "message": {"role": "user", "content": "hi"}},
                {"type": "assistant", "message": {"model": "claude-opus-5-5", "content": [{"type": "text", "text": "ok"}]}},
            ]
        )
    )
    session_end({"transcript_path": str(transcript), "session_id": "abc", "cwd": str(project), "reason": "other"})
    sessions = project / ".aesdk" / "sessions"
    assert (sessions / "abc.jsonl").read_text() == transcript.read_text()
    summary = json.loads((sessions / "abc.summary.json").read_text())
    assert summary["models_used"] == ["claude-opus-5-5"]
    assert summary["end_reason"] == "other"


def test_install_claude_hooks_is_idempotent_and_merges(tmp_path: Path) -> None:
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(
        json.dumps({"model": "opus", "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "other"}]}]}})
    )
    install_claude_hooks(tmp_path)
    install_claude_hooks(tmp_path)
    data = json.loads(settings.read_text())
    assert data["model"] == "opus"
    commands = [h["command"] for g in data["hooks"]["PreToolUse"] for h in g["hooks"]]
    assert commands == ["other", "aesdk hook pre-tool-use"]
    assert set(data["hooks"]) == set(claude_hook_settings())


def test_console_script_fast_path(project: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "aesdk", "hook", "pre-tool-use"],
        input=json.dumps(_bash("python analysis.py", project)),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
