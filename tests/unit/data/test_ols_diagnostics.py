"""Tests for the Wooldridge OLS assumption checker and non-absorbing DiD probe."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from aesdk.data import ols_assumption_report, scan_data

CHECKLIST_KEYS = {
    "functional_form",
    "random_sampling",
    "no_perfect_collinearity",
    "zero_conditional_mean",
    "homoskedasticity",
    "no_serial_correlation",
    "normality",
    "influential_obs",
    "inference_choice",
}


def _rng():
    return np.random.default_rng(20260713)


def _well_behaved(n: int = 300) -> pd.DataFrame:
    rng = _rng()
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    y = 2.0 + 3.0 * x1 - 1.0 * x2 + rng.normal(0, 1, n)
    return pd.DataFrame({"y": y, "treated": x1, "income": x2})


def test_report_has_full_checklist() -> None:
    df = _well_behaved()
    report = ols_assumption_report(
        df, outcome="y", regressors=["treated", "income"], structure="cross-section",
        standard_errors="HC1",
    )
    assert report.fitted is True
    keys = {c.key for c in report.checks}
    assert CHECKLIST_KEYS.issubset(keys)
    # Ten items total (df item only appears when n<=k).
    assert len(report.checks) == len(CHECKLIST_KEYS)


def test_well_behaved_model_passes_core_assumptions() -> None:
    df = _well_behaved()
    report = ols_assumption_report(
        df, outcome="y", regressors=["treated", "income"], structure="cross-section",
        standard_errors="HC1",
    )
    status = {c.key: c.status for c in report.checks}
    assert status["homoskedasticity"] == "pass"
    assert status["functional_form"] == "pass"
    assert status["no_perfect_collinearity"] == "pass"
    assert status["inference_choice"] == "pass"
    # Untestable assumptions are declaration items, not false passes.
    assert status["zero_conditional_mean"] == "declaration"
    assert status["random_sampling"] == "declaration"


def test_detects_heteroskedasticity() -> None:
    rng = _rng()
    n = 400
    x1 = rng.uniform(1, 5, n)
    y = 1.0 + 2.0 * x1 + rng.normal(0, 1, n) * x1  # variance grows with x1
    df = pd.DataFrame({"y": y, "treated": x1})
    report = ols_assumption_report(
        df, outcome="y", regressors=["treated"], structure="cross-section",
        standard_errors="conventional",
    )
    het = next(c for c in report.checks if c.key == "homoskedasticity")
    assert het.status == "warn"
    # Robust SEs suppress the warning.
    report_robust = ols_assumption_report(
        df, outcome="y", regressors=["treated"], structure="cross-section", standard_errors="HC1",
    )
    het_robust = next(c for c in report_robust.checks if c.key == "homoskedasticity")
    assert het_robust.status == "pass"


def test_detects_perfect_collinearity() -> None:
    rng = _rng()
    n = 100
    x1 = rng.normal(0, 1, n)
    df = pd.DataFrame({"y": rng.normal(0, 1, n), "treated": x1, "dup": 2.0 * x1})
    report = ols_assumption_report(
        df, outcome="y", regressors=["treated", "dup"], structure="cross-section",
    )
    collin = next(c for c in report.checks if c.key == "no_perfect_collinearity")
    assert collin.status == "fail"


def test_detects_functional_form_misspecification() -> None:
    rng = _rng()
    n = 400
    x1 = rng.uniform(-3, 3, n)
    y = 1.0 + 2.0 * x1 ** 2 + rng.normal(0, 1, n)  # true model is quadratic
    df = pd.DataFrame({"y": y, "treated": x1})
    report = ols_assumption_report(
        df, outcome="y", regressors=["treated"], structure="cross-section", standard_errors="HC1",
    )
    form = next(c for c in report.checks if c.key == "functional_form")
    assert form.status == "warn"


def _ols_pap(source: str) -> dict:
    return {
        "project": {
            "id": "ols_probe",
            "title": "OLS assumption probe fixture",
            "author": "AESDK Test",
            "date_registered": "2026-07-13",
            "version": "1.0.0",
        },
        "data": {"source": source, "unit": "id", "structure": "cross-section"},
        "identification": {
            "strategy": "OLS",
            "treatment_variable": "treated",
            "outcome_variable": "y",
            "covariates": {"mandatory": ["income"], "optional": []},
            "standard_errors": "conventional",
            "expected_sign": "positive",
        },
        "robustness": {"specification_curve": False},
    }


def test_scan_data_emits_ols_findings(tmp_path: Path) -> None:
    rng = _rng()
    n = 400
    x1 = rng.uniform(1, 5, n)
    df = pd.DataFrame(
        {"y": 1.0 + 2.0 * x1 + rng.normal(0, 1, n) * x1, "treated": x1, "income": rng.normal(0, 1, n)}
    )
    data = tmp_path / "cs.csv"
    df.to_csv(data, index=False)
    result = scan_data(method="ols_cef", pap=_ols_pap("cs.csv"), base_dirs=[tmp_path])
    assert result.profile.ols_assumptions is not None
    assert result.profile.ols_assumptions.fitted is True
    ids = {f.rule_id for f in result.findings}
    assert "DATA-OLS-homoskedasticity" in ids


def test_non_absorbing_treatment_detected(tmp_path: Path) -> None:
    # Unit B turns treatment off (1 -> 0): non-absorbing.
    df = pd.DataFrame(
        {
            "state": ["A", "A", "A", "B", "B", "B"],
            "year": [1, 2, 3, 1, 2, 3],
            "treated": [0, 1, 1, 1, 1, 0],
            "employment": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "income": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        }
    )
    data = tmp_path / "panel.csv"
    df.to_csv(data, index=False)
    pap = {
        "project": {"id": "did_na", "title": "Non-absorbing DiD", "author": "T", "date_registered": "2026-07-13", "version": "1.0.0"},
        "data": {"source": "panel.csv", "unit": "state", "time": "year", "structure": "panel"},
        "identification": {
            "strategy": "DiD",
            "treatment_variable": "treated",
            "outcome_variable": "employment",
            "covariates": {"mandatory": [], "optional": []},
            "standard_errors": "cluster",
            "clustering": "state",
            "expected_sign": "positive",
        },
        "did_block": {"parallel_trends_test": True, "staggered_adoption": True},
        "robustness": {"specification_curve": False},
    }
    result = scan_data(method="did", pap=pap, base_dirs=[tmp_path])
    ids = {f.rule_id for f in result.findings}
    assert "DATA-DID-003" in ids
    assert result.profile.treatment_non_absorbing is True
