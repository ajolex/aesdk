from copy import deepcopy

from aesdk.governance.policy import ConformanceLevel
from aesdk.protocol.validator import RuleRegistry, Validator


def _rct_pap(
    valid_pap_dict: dict,
    *,
    rct_block: dict | None = None,
    standard_errors: str = "HC1",
    clustering: str | list[str] | None = None,
) -> dict:
    pap = deepcopy(valid_pap_dict)
    pap["data"] = {**pap["data"], "structure": "cross-section"}
    pap["identification"] = {
        **pap["identification"],
        "strategy": "RCT",
        "standard_errors": standard_errors,
    }
    if clustering is not None:
        pap["identification"]["clustering"] = clustering
    else:
        pap["identification"].pop("clustering", None)
    pap.pop("did_block", None)
    base_rct = {
        "randomization_unit": "individual",
        "assignment_variable": "assigned",
        "treatment_arms": ["treatment"],
        "control_group": "control",
        "assignment_probability": 0.5,
        "random_seed": 42,
        "estimand": "ITT",
        "baseline_balance_check": True,
        "attrition_check": True,
        "spillover_plan": "Measure within-household and neighborhood exposure.",
        "sutva_rationale": "Treatment is delivered at the individual level with no expected cross-unit exposure.",
        "power_calculation": True,
        "trial_registration": True,
        "pap_registered": True,
    }
    if rct_block:
        base_rct.update(rct_block)
    pap["rct_block"] = base_rct
    return pap


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


def test_rule_engine_blocks_unreachable_online_citations(valid_pap_dict: dict) -> None:
    proposal = {
        "estimator": "DiD",
        "standard_errors": "cluster",
        "citation_report": {"hallucinated_count": 0, "uncertain_count": 0, "unreachable_count": 1},
    }
    result = Validator().validate(valid_pap_dict, proposal)
    ids = {violation.rule_id for violation in result.violations}
    assert "CI-003" in ids
    assert result.status == "block"


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


def test_rule_engine_blocks_clustered_inference_without_level(valid_pap_dict: dict) -> None:
    pap = dict(valid_pap_dict)
    pap["identification"] = {
        **valid_pap_dict["identification"],
        "standard_errors": "cluster",
    }
    pap["identification"].pop("clustering")
    proposal = {"estimator": "DiD", "standard_errors": "cluster"}

    result = Validator().validate(pap, proposal)

    ids = {violation.rule_id for violation in result.violations}
    assert "W-PANEL-003" in ids
    assert result.status == "block"


def test_rule_engine_blocks_one_dimension_for_two_way_cluster(valid_pap_dict: dict) -> None:
    proposal = {"estimator": "DiD", "standard_errors": "two-way-cluster", "clustering": "state"}

    result = Validator().validate(valid_pap_dict, proposal)

    ids = {violation.rule_id for violation in result.violations}
    assert "W-PANEL-004" in ids
    assert result.status == "block"


def test_rule_engine_accepts_two_way_cluster_dimensions(valid_pap_dict: dict) -> None:
    proposal = {
        "estimator": "DiD",
        "standard_errors": "two-way-cluster",
        "clustering": ["state", "year"],
        "treatment_level": "state",
    }

    result = Validator().validate(valid_pap_dict, proposal)

    ids = {violation.rule_id for violation in result.violations}
    assert "W-PANEL-002" not in ids
    assert "W-PANEL-003" not in ids
    assert "W-PANEL-004" not in ids
    assert result.status == "pass"


def test_rule_engine_warns_when_iv_first_stage_missing(valid_pap_dict: dict) -> None:
    pap = dict(valid_pap_dict)
    pap["identification"] = {
        **valid_pap_dict["identification"],
        "strategy": "IV",
    }
    pap.pop("did_block")
    pap["iv_block"] = {
        "instruments": ["quarter_of_birth"],
        "first_stage_f_threshold": 10,
        "exclusion_restriction_documented": True,
    }
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
    pap["iv_block"] = {
        "instruments": ["quarter_of_birth"],
        "first_stage_f_threshold": 10,
        "exclusion_restriction_documented": True,
    }
    proposal = {"estimator": "IV", "standard_errors": "HC3", "first_stage_f_stat": 4.2}
    result = Validator().validate(pap, proposal)
    ids = {violation.rule_id for violation in result.violations}
    assert "W-IV-002" in ids
    assert result.status == "block"


def test_rule_engine_blocks_iv_without_exclusion_argument(valid_pap_dict: dict) -> None:
    pap = dict(valid_pap_dict)
    pap["identification"] = {
        **valid_pap_dict["identification"],
        "strategy": "IV",
    }
    pap.pop("did_block")
    pap["iv_block"] = {"instruments": ["quarter_of_birth"], "first_stage_f_threshold": 10}
    proposal = {"estimator": "IV", "standard_errors": "HC3", "first_stage_f_stat": 20}

    result = Validator().validate(pap, proposal)

    ids = {violation.rule_id for violation in result.violations}
    assert "W-IV-004" in ids
    assert result.status == "block"


def test_rule_engine_blocks_eval_failures_instead_of_silent_pass(valid_pap_dict: dict, tmp_path) -> None:
    rule_file = tmp_path / "bad.rules.yaml"
    rule_file.write_text(
        """
source:
  id: BAD_RULE
rules:
  - id: BAD-001
    name: Bad Rule
    severity: error
    estimators: []
    data_structures: []
    condition: "len(null) == 0"
    requirement: "This malformed rule must not silently pass."
""",
        encoding="utf-8",
    )

    result = Validator(registry=RuleRegistry(rules_dir=tmp_path)).validate(valid_pap_dict, {})

    ids = {violation.rule_id for violation in result.violations}
    assert "BAD-001-EVAL" in ids
    assert result.status == "block"


def test_did_rules_fire_for_twfe_strategy_alias(valid_pap_dict: dict) -> None:
    pap = dict(valid_pap_dict)
    pap["identification"] = {
        **valid_pap_dict["identification"],
        "strategy": "TWFE",
    }
    proposal = {"estimator": "TWFE", "standard_errors": "cluster", "clustering": "state"}

    result = Validator().validate(pap, proposal)

    ids = {violation.rule_id for violation in result.violations}
    assert "AP-DID-003" in ids
    assert result.status == "block"


def test_ols_rules_block_causal_claim_without_identification(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "data": {**valid_pap_dict["data"], "structure": "cross-section"},
        "identification": {
            **valid_pap_dict["identification"],
            "strategy": "OLS",
            "standard_errors": "robust",
        },
    }
    pap.pop("did_block")
    proposal = {"estimator": "OLS", "causal_claim": True, "identification_assumption_documented": False}

    result = Validator().validate(pap, proposal)

    ids = {violation.rule_id for violation in result.violations}
    assert "OLS-002" in ids
    assert result.status == "block"


def test_rdd_rules_block_missing_running_variable(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "data": {**valid_pap_dict["data"], "structure": "cross-section"},
        "identification": {**valid_pap_dict["identification"], "strategy": "RDD"},
    }
    pap.pop("did_block")
    pap["rdd_block"] = {"cutoff": 50, "bandwidth_rule": "mserd", "sharp_or_fuzzy": "sharp"}

    result = Validator().validate(pap, {"estimator": "RDD"})

    ids = {violation.rule_id for violation in result.violations}
    assert "RDD-001" in ids
    assert result.status == "block"


def test_matching_rules_block_post_treatment_covariates(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "data": {**valid_pap_dict["data"], "structure": "cross-section"},
        "identification": {**valid_pap_dict["identification"], "strategy": "Matching"},
    }
    pap.pop("did_block")
    pap["matching_block"] = {
        "pre_treatment_covariates": ["age"],
        "post_treatment_covariates": ["earnings_after"],
        "estimand": "ATT",
        "balance_diagnostics": True,
    }

    result = Validator().validate(pap, {"estimator": "Matching"})

    ids = {violation.rule_id for violation in result.violations}
    assert "MATCH-002" in ids
    assert result.status == "block"


def test_synthetic_control_rules_block_missing_donor_pool(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "identification": {**valid_pap_dict["identification"], "strategy": "SyntheticControl"},
    }
    pap.pop("did_block")
    pap["synthetic_control_block"] = {
        "treated_unit": "California",
        "intervention_time": 2010,
        "predictors": ["pre_outcome"],
    }

    result = Validator().validate(pap, {"estimator": "SyntheticControl"})

    ids = {violation.rule_id for violation in result.violations}
    assert "SYNTH-002" in ids
    assert result.status == "block"


def test_rct_rules_block_missing_randomization_unit(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "data": {**valid_pap_dict["data"], "structure": "cross-section"},
        "identification": {**valid_pap_dict["identification"], "strategy": "RCT", "standard_errors": "HC1"},
    }
    pap.pop("did_block")
    pap["rct_block"] = {
        "assignment_variable": "assigned",
        "treatment_arms": ["cash_transfer"],
        "control_group": "business_as_usual",
        "estimand": "ITT",
    }

    result = Validator().validate(pap, {"estimator": "RCT", "standard_errors": "HC1"})

    ids = {violation.rule_id for violation in result.violations}
    assert "RCT-001" in ids
    assert result.status == "block"


def test_rct_late_rules_require_compliance_assumptions(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "data": {**valid_pap_dict["data"], "structure": "cross-section"},
        "identification": {**valid_pap_dict["identification"], "strategy": "LATE", "standard_errors": "HC1"},
    }
    pap.pop("did_block")
    pap["rct_block"] = {
        "randomization_unit": "individual",
        "assignment_variable": "assigned",
        "treatment_arms": ["voucher_offer"],
        "control_group": "no_offer",
        "estimand": "LATE",
        "takeup_variable": "used_voucher",
    }

    result = Validator().validate(pap, {"estimator": "LATE", "standard_errors": "HC1"})

    ids = {violation.rule_id for violation in result.violations}
    assert "RCT-009" in ids
    assert result.status == "block"


def test_cluster_rct_requires_clustered_inference(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "data": {**valid_pap_dict["data"], "structure": "cross-section"},
        "identification": {**valid_pap_dict["identification"], "strategy": "RCT", "standard_errors": "HC1"},
    }
    pap.pop("did_block")
    pap["rct_block"] = {
        "randomization_unit": "school",
        "assignment_variable": "assigned",
        "treatment_arms": ["tutoring"],
        "control_group": "status_quo",
        "estimand": "ITT",
        "cluster_randomized": True,
    }

    result = Validator().validate(pap, {"estimator": "RCT", "standard_errors": "HC1"})

    ids = {violation.rule_id for violation in result.violations}
    assert "RCT-007" in ids
    assert result.status == "block"


def test_rct_late_rules_fire_when_pap_strategy_is_rct(valid_pap_dict: dict) -> None:
    pap = _rct_pap(
        valid_pap_dict,
        rct_block={
            "estimand": "LATE",
            "exclusion_for_late_documented": False,
            "monotonicity_documented": False,
        },
    )

    result = Validator().validate(pap, {"estimator": "RCT", "standard_errors": "HC1"})

    ids = {violation.rule_id for violation in result.violations}
    assert {"RCT-008", "RCT-009"}.issubset(ids)
    assert result.status == "block"


def test_rct_tot_estimator_triggers_compliance_reporting(valid_pap_dict: dict) -> None:
    pap = _rct_pap(valid_pap_dict, rct_block={"estimand": "ToT"})

    result = Validator().validate(pap, {"estimator": "ToT", "standard_errors": "HC1"})

    ids = {violation.rule_id for violation in result.violations}
    assert "RCT-010" in ids
    assert result.status == "warn"


def test_rct_blocks_ate_when_compliance_is_imperfect(valid_pap_dict: dict) -> None:
    pap = _rct_pap(
        valid_pap_dict,
        rct_block={
            "estimand": "ATE",
            "compliance_type": "encouragement",
            "compliance_rate": 0.62,
        },
    )

    result = Validator().validate(pap, {"estimator": "ATE", "standard_errors": "HC1"})

    ids = {violation.rule_id for violation in result.violations}
    assert "RCT-018" in ids
    assert result.status == "block"


def test_cluster_rct_requires_declared_cluster_level(valid_pap_dict: dict) -> None:
    pap = _rct_pap(
        valid_pap_dict,
        rct_block={"randomization_unit": "school", "cluster_randomized": True},
        standard_errors="cluster",
    )

    result = Validator().validate(pap, {"estimator": "RCT", "standard_errors": "cluster"})

    ids = {violation.rule_id for violation in result.violations}
    assert "RCT-016" in ids
    assert result.status == "block"


def test_cluster_rct_blocks_clustering_below_randomization_unit(valid_pap_dict: dict) -> None:
    pap = _rct_pap(
        valid_pap_dict,
        rct_block={"randomization_unit": "school", "cluster_randomized": True},
        standard_errors="cluster",
        clustering="individual",
    )

    result = Validator().validate(
        pap,
        {"estimator": "RCT", "standard_errors": "cluster", "clustering": "individual"},
    )

    ids = {violation.rule_id for violation in result.violations}
    assert "RCT-017" in ids
    assert result.status == "block"


def test_randomization_inference_plan_satisfies_cluster_rct_inference(valid_pap_dict: dict) -> None:
    pap = _rct_pap(
        valid_pap_dict,
        rct_block={
            "randomization_unit": "school",
            "cluster_randomized": True,
            "randomization_inference_plan": True,
        },
        standard_errors="HC1",
    )

    result = Validator().validate(pap, {"estimator": "RCT", "standard_errors": "HC1"})

    ids = {violation.rule_id for violation in result.violations}
    assert "RCT-007" not in ids
    assert "RCT-016" not in ids
    assert "RCT-017" not in ids
    assert result.status == "pass"


def test_stratified_randomization_requires_strata(valid_pap_dict: dict) -> None:
    pap = _rct_pap(valid_pap_dict, rct_block={"stratification_used": True, "strata": []})

    result = Validator().validate(pap, {"estimator": "RCT", "standard_errors": "HC1"})

    ids = {violation.rule_id for violation in result.violations}
    assert "RCT-022" in ids
    assert result.status == "block"


def test_differential_attrition_requires_sensitivity_plan(valid_pap_dict: dict) -> None:
    pap = _rct_pap(
        valid_pap_dict,
        rct_block={"attrition_differential": True, "attrition_sensitivity_plan": ""},
    )

    result = Validator().validate(pap, {"estimator": "RCT", "standard_errors": "HC1"})

    ids = {violation.rule_id for violation in result.violations}
    assert "RCT-019" in ids
    assert result.status == "warn"


def test_spillover_risk_requires_plan_and_sutva_rationale(valid_pap_dict: dict) -> None:
    pap = _rct_pap(
        valid_pap_dict,
        rct_block={
            "spillover_risk": True,
            "spillover_measurement_plan": "",
            "sutva_rationale": "",
        },
    )

    result = Validator().validate(pap, {"estimator": "RCT", "standard_errors": "HC1"})

    ids = {violation.rule_id for violation in result.violations}
    assert "RCT-020" in ids
    assert "RCT-021" in ids
    assert result.status == "warn"


def test_rct_placeholder_text_does_not_satisfy_spillover_or_sutva_rules(valid_pap_dict: dict) -> None:
    pap = _rct_pap(
        valid_pap_dict,
        rct_block={
            "spillover_plan": "TBD",
            "sutva_rationale": "to be determined",
        },
    )

    result = Validator().validate(pap, {"estimator": "RCT", "standard_errors": "HC1"})

    ids = {violation.rule_id for violation in result.violations}
    assert "RCT-013" in ids
    assert "RCT-021" in ids
    assert result.status == "warn"


def test_rct_blocks_ate_with_plain_language_imperfect_compliance(valid_pap_dict: dict) -> None:
    pap = _rct_pap(
        valid_pap_dict,
        rct_block={
            "estimand": "ATE",
            "compliance_type": "imperfect compliance",
        },
    )

    result = Validator().validate(pap, {"estimator": "ATE", "standard_errors": "HC1"})

    ids = {violation.rule_id for violation in result.violations}
    assert "RCT-018" in ids
    assert result.status == "block"


def test_cluster_rct_blocks_common_units_below_village_assignment(valid_pap_dict: dict) -> None:
    pap = _rct_pap(
        valid_pap_dict,
        rct_block={"randomization_unit": "village", "cluster_randomized": True},
        standard_errors="cluster",
        clustering="individual",
    )

    result = Validator().validate(
        pap,
        {"estimator": "RCT", "standard_errors": "cluster", "clustering": "individual"},
    )

    ids = {violation.rule_id for violation in result.violations}
    assert "RCT-017" in ids
    assert result.status == "block"


def test_synthetic_control_rules_fire_for_synthcontrol_alias(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "identification": {**valid_pap_dict["identification"], "strategy": "SynthControl"},
    }
    pap.pop("did_block")
    pap["synthetic_control_block"] = {
        "treated_unit": "California",
        "intervention_time": 2010,
        "predictors": ["pre_outcome"],
    }

    result = Validator().validate(pap, {"estimator": "SynthControl"})

    ids = {violation.rule_id for violation in result.violations}
    assert "SYNTH-002" in ids
    assert result.status == "block"


def test_nonlinear_did_rules_block_missing_target_scale(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "identification": {**valid_pap_dict["identification"], "strategy": "DiD"},
        "nonlinear_did_block": {
            "outcome_family": "binary",
            "effect_transformation": "marginal_effect",
        },
    }

    result = Validator().validate(pap, {"estimator": "LogitDiD"})

    ids = {violation.rule_id for violation in result.violations}
    assert "NLDID-002" in ids
    assert result.status == "block"


def test_gmm_rules_block_underidentified_moments(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "data": {**valid_pap_dict["data"], "structure": "cross-section"},
        "identification": {**valid_pap_dict["identification"], "strategy": "GMM"},
    }
    pap.pop("did_block")
    pap["gmm_block"] = {
        "moment_conditions": ["E[z*u]=0"],
        "parameters": ["beta_0", "beta_1"],
        "weighting_matrix": "robust",
    }

    result = Validator().validate(pap, {"estimator": "GMM"})

    ids = {violation.rule_id for violation in result.violations}
    assert "GMM-003" in ids
    assert result.status == "block"


def test_gmm_null_moments_trigger_missing_moments_rule(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "data": {**valid_pap_dict["data"], "structure": "cross-section"},
        "identification": {**valid_pap_dict["identification"], "strategy": "GMM"},
    }
    pap.pop("did_block")
    pap["gmm_block"] = {
        "moment_conditions": None,
        "parameters": ["beta_0"],
        "weighting_matrix": "robust",
        "identification_rank": 1,
    }

    result = Validator().validate(pap, {"estimator": "GMM"})

    ids = {violation.rule_id for violation in result.violations}
    assert "GMM-001" in ids
    assert not any(rule_id.endswith("-EVAL") for rule_id in ids)
    assert result.status == "block"


def test_gmm_rules_block_missing_identification_rank(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "data": {**valid_pap_dict["data"], "structure": "cross-section"},
        "identification": {**valid_pap_dict["identification"], "strategy": "GMM"},
    }
    pap.pop("did_block")
    pap["gmm_block"] = {
        "moment_conditions": ["E[z*u]=0"],
        "parameters": ["beta_0"],
        "weighting_matrix": "robust",
    }

    result = Validator().validate(pap, {"estimator": "GMM"})

    ids = {violation.rule_id for violation in result.violations}
    assert "GMM-007" in ids
    assert result.status == "block"


def test_panel_fe_rules_block_time_invariant_regressor_interpretation(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "data": {**valid_pap_dict["data"], "structure": "panel", "unit": "firm", "time": "year"},
        "identification": {
            **valid_pap_dict["identification"],
            "strategy": "FE",
            "standard_errors": "cluster",
            "clustering": "firm",
            "fixed_effects": ["unit"],
            "within_variation_documented": True,
        },
    }
    pap.pop("did_block")
    proposal = {
        "estimator": "FE",
        "standard_errors": "cluster",
        "clustering": "firm",
        "time_invariant_regressors": ["female"],
        "time_invariant_interpreted": True,
    }

    result = Validator().validate(pap, proposal)

    ids = {violation.rule_id for violation in result.violations}
    assert "PANEL-FE-008" in ids
    assert result.status == "block"


def test_limited_dependent_rules_block_raw_coefficients(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "data": {**valid_pap_dict["data"], "structure": "cross-section"},
        "identification": {**valid_pap_dict["identification"], "strategy": "Logit"},
    }
    pap.pop("did_block")
    pap["limited_dependent_block"] = {
        "outcome_type": "binary",
        "link_or_family": "logit",
        "target_effect": "probability",
        "reporting_raw_coefficient": True,
    }

    result = Validator().validate(pap, {"estimator": "Logit"})

    ids = {violation.rule_id for violation in result.violations}
    assert "LDV-003" in ids
    assert result.status == "block"


def test_time_series_rules_block_lookahead_bias(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "data": {**valid_pap_dict["data"], "structure": "time-series", "time_index": "date", "frequency": "monthly"},
        "identification": {**valid_pap_dict["identification"], "strategy": "ARIMA"},
    }
    pap.pop("did_block")
    pap["time_series_block"] = {
        "stationarity_plan": "difference once if unit root is detected",
        "lag_order_plan": "AIC on training sample",
        "forecast_or_causal_target": "forecast",
        "lookahead_bias": True,
    }

    result = Validator().validate(pap, {"estimator": "ARIMA"})

    ids = {violation.rule_id for violation in result.violations}
    assert "TS-005" in ids
    assert result.status == "block"
