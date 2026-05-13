import sys

import pytest

from aesdk.core.errors import ForbiddenCodePatternError
from aesdk.core.errors import ImportWhitelistError
from aesdk.sandbox.runner import SandboxRunner, infer_language_from_path, normalize_language


class _CompletedProcess:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_language_helpers_normalize_and_infer() -> None:
    assert normalize_language("py") == "python"
    assert normalize_language("do-file") == "stata"
    assert normalize_language("Rscript") == "r"
    assert infer_language_from_path("analysis.py") == "python"
    assert infer_language_from_path("analysis.do") == "stata"
    assert infer_language_from_path("analysis.R") == "r"


def test_stata_runtime_missing_blocks_with_plain_diagnostic(monkeypatch) -> None:
    monkeypatch.delenv("AESDK_STATA", raising=False)
    runner = SandboxRunner(stata_executable="definitely-not-stata")

    result = runner.run("display 1", language="stata")

    assert result.status == "block"
    assert result.diagnostics[0].code == "MISSING_RUNTIME"


def test_stata_shell_escape_is_blocked() -> None:
    runner = SandboxRunner()

    with pytest.raises(ForbiddenCodePatternError):
        runner.run("! dir", language="stata")

    with pytest.raises(ForbiddenCodePatternError):
        runner.run("capture shell dir", language="stata")

    with pytest.raises(ForbiddenCodePatternError):
        runner.run("quietly ssc install reghdfe", language="stata")


def test_r_runtime_missing_blocks_with_plain_diagnostic(monkeypatch) -> None:
    monkeypatch.delenv("AESDK_R", raising=False)
    runner = SandboxRunner(r_executable="definitely-not-rscript")

    result = runner.run("print(1)", language="r")

    assert result.status == "block"
    assert result.diagnostics[0].code == "MISSING_RUNTIME"


def test_r_shell_and_package_install_are_blocked() -> None:
    runner = SandboxRunner()

    with pytest.raises(ForbiddenCodePatternError):
        runner.run("system('dir')", language="r")

    with pytest.raises(ForbiddenCodePatternError):
        runner.run("writeLines('x', 'out.txt')", language="r")

    with pytest.raises(ForbiddenCodePatternError):
        runner.run("install.packages('fixest')", language="r")

    with pytest.raises(ForbiddenCodePatternError):
        runner.run('source("https://example.com/script.R")', language="r")


def test_r_package_whitelist_blocks_unapproved_packages() -> None:
    runner = SandboxRunner()

    with pytest.raises(ImportWhitelistError):
        runner.run("library(notApprovedForAESDK)", language="r")


def test_non_python_execution_uses_caller_cwd(monkeypatch) -> None:
    calls = []

    def fake_run(command, **kwargs):  # noqa: ANN001
        calls.append((command, kwargs))
        return _CompletedProcess(returncode=0, stdout="ok")

    monkeypatch.setattr("subprocess.run", fake_run)

    SandboxRunner(stata_executable=sys.executable).run("display 1", language="stata")
    SandboxRunner(r_executable=sys.executable).run("print(1)", language="r")

    assert "cwd" not in calls[0][1]
    assert "cwd" not in calls[1][1]


def test_unsupported_language_blocks() -> None:
    runner = SandboxRunner()
    result = runner.run("print('x')", language="julia")

    assert result.status == "block"
    assert result.diagnostics[0].code == "UNSUPPORTED_LANGUAGE"
