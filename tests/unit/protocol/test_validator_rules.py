from aesdk.governance.policy import ConformanceLevel
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


def test_rule_engine_triggers_ci_001_for_hallucinated_citations(valid_pap_dict: dict) -> None:
    proposal = {
        "estimator": "DiD",
        "standard_errors": "cluster",
        "citation_report": {"hallucinated_count": 1, "uncertain_count": 0},
    }
    result = Validator().validate(valid_pap_dict, proposal)
    ids = {violation.rule_id for violation in result.violations}
    assert "CI-001" in ids
    assert result.status == "block"


def test_strict_conformance_escalates_warnings_to_block(valid_pap_dict: dict) -> None:
    proposal = {
        "estimator": "DiD",
        "standard_errors": "cluster",
        "citation_report": {"hallucinated_count": 0, "uncertain_count": 2},
        "citation_uncertainty_acknowledged": False,
    }
    basic = Validator().validate(valid_pap_dict, proposal, conformance=ConformanceLevel.BASIC)
    strict = Validator().validate(valid_pap_dict, proposal, conformance=ConformanceLevel.STRICT)
    assert basic.status == "warn"
    assert strict.status == "block"


def test_rule_engine_blocks_clustering_below_assignment_level(valid_pap_dict: dict) -> None:
    proposal = {
        "estimator": "DiD",
        "standard_errors": "cluster",
        "clustering": "county",
        "treatment_level": "state",
    }
    result = Validator().validate(valid_pap_dict, proposal)
    ids = {violation.rule_id for violation in result.violations}
    assert "W-PANEL-002" in ids
    assert result.status == "block"


def test_rule_engine_warns_when_iv_first_stage_missing(valid_pap_dict: dict) -> None:
    pap = dict(valid_pap_dict)
    pap["identification"] = {
        **valid_pap_dict["identification"],
        "strategy": "IV",
    }
    pap.pop("did_block")
    pap["iv_block"] = {"instruments": ["quarter_of_birth"], "first_stage_f_threshold": 10}
    proposal = {"estimator": "IV", "standard_errors": "HC3"}
    result = Validator().validate(pap, proposal)
    ids = {violation.rule_id for violation in result.violations}
    assert "W-IV-003" in ids
    assert result.status == "warn"


def test_rule_engine_blocks_weak_iv_first_stage(valid_pap_dict: dict) -> None:
    pap = dict(valid_pap_dict)
    pap["identification"] = {
        **valid_pap_dict["identification"],
        "strategy": "IV",
    }
    pap.pop("did_block")
    pap["iv_block"] = {"instruments": ["quarter_of_birth"], "first_stage_f_threshold": 10}
    proposal = {"estimator": "IV", "standard_errors": "HC3", "first_stage_f_stat": 4.2}
    result = Validator().validate(pap, proposal)
    ids = {violation.rule_id for violation in result.violations}
    assert "W-IV-002" in ids
    assert result.status == "block"
