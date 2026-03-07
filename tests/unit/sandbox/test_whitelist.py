import pytest

from aesdk.core.errors import ImportWhitelistError
from aesdk.sandbox.runner import SandboxRunner


def test_import_whitelist_blocks_forbidden_imports() -> None:
    runner = SandboxRunner()
    with pytest.raises(ImportWhitelistError):
        runner.run_python("import os\nprint('no')")
