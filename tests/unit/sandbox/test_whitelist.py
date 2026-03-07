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
