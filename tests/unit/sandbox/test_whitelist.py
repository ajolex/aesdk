import pytest

from aesdk.core.errors import ForbiddenCodePatternError, ImportWhitelistError
from aesdk.sandbox.runner import SandboxRunner


def test_import_whitelist_blocks_forbidden_imports() -> None:
    runner = SandboxRunner()
    with pytest.raises(ImportWhitelistError):
        runner.run_python("import os\nprint('no')")


def test_forbidden_calls_are_blocked() -> None:
    runner = SandboxRunner()
    with pytest.raises(ForbiddenCodePatternError):
        runner.run_python("print('x')\nopen('secret.txt', 'w')")


def test_sandbox_timeout_blocks_long_running_code() -> None:
    runner = SandboxRunner(cpu_limit_sec=1)
    result = runner.run_python("while True:\n    pass", timeout_seconds=1)
    assert result.status == "block"
    assert any(item.code in {"TIMEOUT", "RUNTIME"} for item in result.diagnostics)


def test_sandbox_resource_limits_hook_is_configurable() -> None:
    runner = SandboxRunner(mem_limit_mb=128, cpu_limit_sec=2)
    assert runner.mem_limit_mb == 128
    assert runner.cpu_limit_sec == 2
