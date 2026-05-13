import pytest

from aesdk.core.errors import ForbiddenCodePatternError
from aesdk.sandbox.runner import SandboxRunner, infer_language_from_path, normalize_language


def test_language_helpers_normalize_and_infer() -> None:
    assert normalize_language("py") == "python"
    assert normalize_language("do-file") == "stata"
    assert infer_language_from_path("analysis.py") == "python"
    assert infer_language_from_path("analysis.do") == "stata"


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


def test_unsupported_language_blocks() -> None:
    runner = SandboxRunner()
    result = runner.run("print('x')", language="r")

    assert result.status == "block"
    assert result.diagnostics[0].code == "UNSUPPORTED_LANGUAGE"
