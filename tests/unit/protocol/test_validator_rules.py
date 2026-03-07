from aesdk.protocol.validator import Validator


def test_rule_engine_triggers_w_panel_001(valid_pap_dict: dict) -> None:
    proposal = {"estimator": "TWFE", "standard_errors": "HC3", "clustering": "state"}
    result = Validator().validate(valid_pap_dict, proposal)
    ids = {violation.rule_id for violation in result.violations}
    assert "W-PANEL-001" in ids
    assert result.status == "block"


def test_rule_engine_triggers_ap_did_003(valid_pap_dict: dict) -> None:
    proposal = {"estimator": "TWFE", "standard_errors": "cluster", "clustering": "state"}
    result = Validator().validate(valid_pap_dict, proposal)
    ids = {violation.rule_id for violation in result.violations}
    assert "AP-DID-003" in ids
    assert result.status == "block"
