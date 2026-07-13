"""Functional tests for the newly added method guardrails.

Covers Maximum Likelihood, Double/Debiased ML, Structural/BLP, Nonparametric,
Bayesian, and GARCH volatility guardrails.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

import aesdk as ae


def _pap(strategy: str, structure: str = "cross-section", **blocks) -> Path:
    pap = {
        "project": {
            "id": "new_method",
            "title": "New method guardrail fixture",
            "author": "AESDK Test",
            "date_registered": "2026-07-13",
            "version": "1.0.0",
        },
        "data": {"source": "no_such_file.csv", "unit": "id", "structure": structure},
        "identification": {
            "strategy": strategy,
            "treatment_variable": "x",
            "outcome_variable": "y",
            "covariates": {"mandatory": [], "optional": []},
            "expected_sign": "positive",
        },
        "robustness": {"specification_curve": False},
    }
    pap.update(blocks)
    d = Path(tempfile.mkdtemp())
    p = d / "pap.yaml"
    p.write_text(yaml.safe_dump(pap), encoding="utf-8")
    return p


def _ids(method, pap, proposal, conformance="basic"):
    result = ae.preflight(
        method=method, pap_path=pap, proposal=proposal, conformance=conformance, scan_data_file=False
    )
    return {v.rule_id for v in result.violations}, result


def test_mle_requires_distribution() -> None:
    pap = _pap("MLE")
    ids, res = _ids("mle", pap, {"estimator": "MLE"})
    assert "MLE-001" in ids and res.blocked
    pap_ok = _pap("MLE", mle_block={"distribution": "logistic", "convergence_confirmed": True})
    ids_ok, res_ok = _ids("mle", pap_ok, {"estimator": "MLE"})
    assert "MLE-001" not in ids_ok


def test_qmle_requires_robust_se() -> None:
    pap = _pap("QMLE", mle_block={"distribution": "poisson", "convergence_confirmed": True})
    ids, _ = _ids("mle", pap, {"estimator": "QMLE"})
    assert "MLE-003" in ids
    pap_ok = _pap(
        "QMLE",
        mle_block={"distribution": "poisson", "convergence_confirmed": True, "standard_error_type": "robust"},
    )
    ids_ok, _ = _ids("mle", pap_ok, {"estimator": "QMLE"})
    assert "MLE-003" not in ids_ok


def test_dml_requires_identification_and_cross_fitting() -> None:
    pap = _pap("DML")
    ids, res = _ids(
        "dml", pap, {"estimator": "DML", "causal_claim": True, "identification_assumption_documented": False}
    )
    assert "DML-001" in ids and res.blocked
    assert "DML-002" in ids  # no cross-fitting declared
    assert "DML-003" in ids  # no orthogonal score declared


def test_dml_clean_when_declared() -> None:
    pap = _pap("DML", dml_block={"cross_fitting_folds": 5, "orthogonal_score": "PLR"})
    ids, _ = _ids("dml", pap, {"estimator": "DML", "causal_claim": True})
    assert "DML-002" not in ids
    assert "DML-003" not in ids


def test_structural_requires_model_and_identification() -> None:
    pap = _pap("BLP")
    ids, res = _ids("structural", pap, {"estimator": "BLP"})
    assert "STRUCT-001" in ids and res.blocked
    pap_ok = _pap(
        "BLP",
        structural_block={
            "model": "random-coefficients logit",
            "identification_argument": "cost-shifter instruments",
            "prices_endogenous": True,
            "instruments": ["cost_shifter"],
        },
    )
    ids_ok, _ = _ids("structural", pap_ok, {"estimator": "BLP"})
    assert "STRUCT-001" not in ids_ok
    assert "STRUCT-002" not in ids_ok


def test_structural_flags_uninstrumented_prices() -> None:
    pap = _pap(
        "BLP",
        structural_block={
            "model": "random-coefficients logit",
            "identification_argument": "instruments",
            "prices_endogenous": True,
            "instruments": [],
        },
    )
    ids, _ = _ids("structural", pap, {"estimator": "BLP"})
    assert "STRUCT-002" in ids


def test_nonparametric_requires_bandwidth_rule() -> None:
    pap = _pap("KernelRegression")
    ids, _ = _ids("nonparametric", pap, {"estimator": "KernelRegression"})
    assert "NONPARAM-001" in ids
    pap_ok = _pap("KernelRegression", nonparametric_block={"bandwidth_rule": "cross-validation"})
    ids_ok, _ = _ids("nonparametric", pap_ok, {"estimator": "KernelRegression"})
    assert "NONPARAM-001" not in ids_ok


def test_nonparametric_flags_curse_of_dimensionality() -> None:
    pap = _pap(
        "KernelRegression",
        nonparametric_block={
            "bandwidth_rule": "cross-validation",
            "continuous_regressor_count": 6,
        },
    )
    ids, _ = _ids("nonparametric", pap, {"estimator": "KernelRegression"})
    assert "NONPARAM-002" in ids


def test_bayesian_requires_priors_and_convergence() -> None:
    pap = _pap("MCMC")
    ids, res = _ids("bayesian", pap, {"estimator": "MCMC"})
    assert "BAYES-001" in ids and res.blocked
    assert "BAYES-002" in ids
    pap_ok = _pap(
        "MCMC",
        bayesian_block={
            "priors": "normal(0,1) on coefficients",
            "convergence_checked": True,
            "prior_sensitivity_checked": True,
        },
    )
    ids_ok, _ = _ids("bayesian", pap_ok, {"estimator": "MCMC"})
    assert "BAYES-001" not in ids_ok
    assert "BAYES-002" not in ids_ok
    assert "BAYES-003" not in ids_ok


def test_garch_requires_time_series_structure() -> None:
    pap = _pap("GARCH", structure="cross-section")
    ids, res = _ids("garch", pap, {"estimator": "GARCH"})
    assert "GARCH-001" in ids and res.blocked


def test_garch_requires_arch_test_on_time_series() -> None:
    pap = _pap("GARCH", structure="time-series")
    ids, _ = _ids("garch", pap, {"estimator": "GARCH"})
    assert "GARCH-001" not in ids
    assert "GARCH-002" in ids
    pap_ok = _pap(
        "GARCH",
        structure="time-series",
        garch_block={
            "arch_test_planned": True,
            "mean_model": "AR(1)",
            "innovation_distribution": "student-t",
        },
    )
    ids_ok, _ = _ids("garch", pap_ok, {"estimator": "GARCH"})
    assert "GARCH-002" not in ids_ok
    assert "GARCH-003" not in ids_ok
