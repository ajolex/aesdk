import sys
from pathlib import Path

import pytest

import aesdk.sandbox.runner as runner_module
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


def test_python_seed_is_injected_and_recorded() -> None:
    result = SandboxRunner(python_seed=20260514).run("import random\nprint(random.random())", language="python")
    repeated = SandboxRunner(python_seed=20260514).run("import random\nprint(random.random())", language="python")

    assert result.status == "pass"
    assert result.artifacts["python_seed"] == "20260514"
    assert result.artifacts["python_seed_injected"] == "true"
    assert result.stdout == repeated.stdout


def test_python_existing_seed_is_preserved() -> None:
    result = SandboxRunner(python_seed=20260514).run("import random\nrandom.seed(123)\nprint(random.random())")

    assert result.status == "pass"
    assert result.artifacts["python_seed"] == "123"
    assert result.artifacts["python_seed_injected"] == "false"


def test_python_unrelated_seed_method_does_not_disable_injection() -> None:
    result = SandboxRunner(python_seed=20260514).run(
        "class Model:\n    def seed(self, value):\n        pass\nmodel = Model()\nmodel.seed(123)\nprint('ok')"
    )

    assert result.status == "pass"
    assert result.artifacts["python_seed"] == "20260514"
    assert result.artifacts["python_seed_injected"] == "true"


def test_preexec_resource_limits_use_per_call_timeout(monkeypatch) -> None:
    calls = []

    class FakeResource:
        RLIMIT_AS = "as"
        RLIMIT_CPU = "cpu"

        @staticmethod
        def setrlimit(name, limits):  # noqa: ANN001
            calls.append((name, limits))

    monkeypatch.setattr(runner_module.os, "name", "posix")
    monkeypatch.setattr(runner_module, "resource", FakeResource)

    preexec = SandboxRunner(cpu_limit_sec=30)._preexec_resource_limits(cpu_limit_sec=123)
    assert preexec is not None
    preexec()

    assert ("cpu", (123, 123)) in calls


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


def test_stata_log_is_captured_as_execution_artifact(tmp_path, monkeypatch) -> None:
    artifact_dir = tmp_path / "artifacts"
    scripts = []

    def fake_run(command, **kwargs):  # noqa: ANN001
        scripts.append(Path(command[-1]).read_text(encoding="utf-8"))
        Path.cwd().joinpath("sandbox_entry.log").write_text("stata output", encoding="utf-8")
        return _CompletedProcess(returncode=0, stdout="")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("subprocess.run", fake_run)

    result = SandboxRunner(stata_executable=sys.executable, artifact_dir=artifact_dir).run("display 1", language="stata")

    assert result.status == "pass"
    captured = Path(result.artifacts["stata_log_path"])
    assert captured.parent == artifact_dir
    assert captured.name.startswith("stata_sandbox_")
    assert result.artifacts["stata_log_path"] == str(captured)
    assert result.artifacts["stata_seed_injected"] == "true"
    assert result.artifacts["stata_seed"].isdigit()
    assert len(result.artifacts["stata_seed"]) == 8
    assert scripts[0].startswith(f"set seed {result.artifacts['stata_seed']}\n")
    assert captured.read_text(encoding="utf-8") == "stata output"
    assert not (tmp_path / "sandbox_entry.log").exists()


def test_stata_stale_cwd_log_is_not_captured(tmp_path, monkeypatch) -> None:
    stale = tmp_path / "sandbox_entry.log"
    stale.write_text("old output", encoding="utf-8")

    def fake_run(command, **kwargs):  # noqa: ANN001
        return _CompletedProcess(returncode=0, stdout="ok")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("subprocess.run", fake_run)

    result = SandboxRunner(stata_executable=sys.executable).run("display 1", language="stata")

    assert result.status == "pass"
    assert "stata_log_path" not in result.artifacts
    assert stale.read_text(encoding="utf-8") == "old output"


def test_stata_log_artifact_names_are_unique_by_script(tmp_path, monkeypatch) -> None:
    artifact_dir = tmp_path / "artifacts"

    def fake_run(command, **kwargs):  # noqa: ANN001
        Path.cwd().joinpath("sandbox_entry.log").write_text(Path(command[-1]).read_text(), encoding="utf-8")
        return _CompletedProcess(returncode=0, stdout="")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("subprocess.run", fake_run)

    first = SandboxRunner(stata_executable=sys.executable, artifact_dir=artifact_dir).run("display 1", language="stata")
    second = SandboxRunner(stata_executable=sys.executable, artifact_dir=artifact_dir).run("display 2", language="stata")

    assert first.artifacts["stata_log_path"] != second.artifacts["stata_log_path"]
    assert Path(first.artifacts["stata_log_path"]).exists()
    assert Path(second.artifacts["stata_log_path"]).exists()


def test_stata_existing_seed_is_preserved(tmp_path, monkeypatch) -> None:
    scripts = []

    def fake_run(command, **kwargs):  # noqa: ANN001
        scripts.append(Path(command[-1]).read_text(encoding="utf-8"))
        return _CompletedProcess(returncode=0, stdout="ok")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("subprocess.run", fake_run)

    result = SandboxRunner(stata_executable=sys.executable, stata_seed=20260514).run(
        "set seed 12345\ndisplay 1",
        language="stata",
    )

    assert result.status == "pass"
    assert result.artifacts["stata_seed"] == "12345"
    assert result.artifacts["stata_seed_injected"] == "false"
    assert scripts[0].count("set seed") == 1
    assert scripts[0].startswith("set seed 12345\n")


def test_r_seed_is_injected_and_recorded(tmp_path, monkeypatch) -> None:
    scripts = []

    def fake_run(command, **kwargs):  # noqa: ANN001
        scripts.append(Path(command[-1]).read_text(encoding="utf-8"))
        return _CompletedProcess(returncode=0, stdout="ok")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("subprocess.run", fake_run)

    result = SandboxRunner(r_executable=sys.executable, r_seed=20260514).run("print(1)", language="r")

    assert result.status == "pass"
    assert result.artifacts["r_seed"] == "20260514"
    assert result.artifacts["r_seed_injected"] == "true"
    assert scripts[0].startswith("set.seed(20260514)\n")


def test_r_existing_seed_is_preserved(tmp_path, monkeypatch) -> None:
    scripts = []

    def fake_run(command, **kwargs):  # noqa: ANN001
        scripts.append(Path(command[-1]).read_text(encoding="utf-8"))
        return _CompletedProcess(returncode=0, stdout="ok")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("subprocess.run", fake_run)

    result = SandboxRunner(r_executable=sys.executable, r_seed=20260514).run("set.seed(123)\nprint(1)", language="r")

    assert result.status == "pass"
    assert result.artifacts["r_seed"] == "123"
    assert result.artifacts["r_seed_injected"] == "false"
    assert scripts[0].count("set.seed") == 1


def test_unsupported_language_blocks() -> None:
    runner = SandboxRunner()
    result = runner.run("print('x')", language="julia")

    assert result.status == "block"
    assert result.diagnostics[0].code == "UNSUPPORTED_LANGUAGE"
