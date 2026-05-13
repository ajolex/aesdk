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


def test_pap_schema_accepts_rct_tot_strategy(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "data": {**valid_pap_dict["data"], "structure": "cross-section"},
        "identification": {
            **valid_pap_dict["identification"],
            "strategy": "ToT",
            "standard_errors": "HC3",
        },
        "rct_block": {
            "randomization_unit": "individual",
            "assignment_variable": "assigned",
            "treatment_arms": ["training_offer"],
            "control_group": "no_offer",
            "estimand": "ToT",
        },
    }
    pap.pop("did_block")

    validate_pap_dict(pap)
