import pytest

from aesdk.core.errors import PAPValidationError
from aesdk.governance.pap import validate_pap_dict


def test_pap_schema_validation_passes(valid_pap_dict: dict) -> None:
    validate_pap_dict(valid_pap_dict)


def test_pap_schema_validation_fails_missing_required(valid_pap_dict: dict) -> None:
    bad = dict(valid_pap_dict)
    bad.pop("identification")
    with pytest.raises(PAPValidationError):
        validate_pap_dict(bad)
