"""Tests for the econometric spec engine."""

from __future__ import annotations

import pandas as pd

from aesdk.curve.runner import CurveRunner
from aesdk.curve.spec_engine import SpecEngine, SpecResult
from aesdk.curve.summarize import summarize_result
from aesdk.plugins import plugins


def test_spec_engine_did_estimates_real_model() -> None:
    df = pd.DataFrame(
        {
            "state": ["a", "a", "b", "b", "c", "c", "d", "d"],
            "year": [0, 1, 0, 1, 0, 1, 0, 1],
            "policy": [0, 1, 0, 1, 0, 0, 0, 0],
            "cov1": [1, 2, 1, 2, 1, 2, 1, 2],
            "outcome": [10, 14, 11, 15, 10, 11, 11, 12],
        }
    )
    engine = SpecEngine(df)
    result = engine.run_did(
        outcome="outcome",
        treatment="policy",
        time="year",
        covariates=["cov1"],
        fixed_effects=["state", "year"],
        cluster="state",
    )

    assert isinstance(result, SpecResult)
    assert result.estimator_name == "Difference-in-Differences (OLS)"
    assert "policy" in result.coefficients
    assert result.n_observations == 8
    assert "C(state)" in result.diagnostics["formula"]


def test_spec_engine_panel_fixed_effects_estimates_real_model() -> None:
    df = pd.DataFrame(
        {
            "outcome": [1, 2, 3, 4, 2, 3, 4, 5],
            "cov1": [0, 1, 2, 3, 0, 1, 2, 3],
            "entity": [1, 1, 1, 1, 2, 2, 2, 2],
            "time": [1, 2, 3, 4, 1, 2, 3, 4],
        }
    )
    engine = SpecEngine(df)
    result = engine.run_panel_fixed_effects(outcome="outcome", covariates=["cov1"], entity_id="entity", time_id="time")

    assert isinstance(result, SpecResult)
    assert result.estimator_name == "Panel Fixed Effects"
    assert "cov1" in result.coefficients
    assert result.diagnostics["entity_effects"] is True


def test_curve_runner_uses_registered_custom_estimator(tmp_path) -> None:
    df = pd.DataFrame({"outcome": [1, 2], "treatment": [0, 1], "time": [0, 1]})
    csv_path = tmp_path / "data.csv"
    df.to_csv(csv_path, index=False)

    def custom_estimator(data, **params):  # noqa: ANN001, ANN003
        return SpecResult("Custom", {"x": 1.0}, {"x": 0.1}, {"x": 0.01}, 0.5, len(data), {"params": params})

    plugins.register_estimator("custom", custom_estimator)
    runner = CurveRunner(csv_path)
    result = runner.execute_spec("custom", {"flag": True})
    assert result.estimator_name == "Custom"
    assert result.n_observations == 2


def test_curve_runner_builtin_did(tmp_path) -> None:
    df = pd.DataFrame({"outcome": [1, 2, 2, 4], "treatment": [0, 1, 0, 1], "time": [0, 1, 0, 1]})
    csv_path = tmp_path / "data.csv"
    df.to_csv(csv_path, index=False)

    runner = CurveRunner(csv_path)
    result = runner.execute_spec("did", {"outcome": "outcome", "treatment": "treatment", "time": "time"})
    assert result.n_observations == 4


def test_summarize_result() -> None:
    result = SpecResult(
        estimator_name="Test Est",
        coefficients={"var1": 0.5},
        std_errors={"var1": 0.1},
        p_values={"var1": 0.01},
        r_squared=0.5,
        n_observations=100,
        diagnostics={},
    )
    summary = summarize_result(result)
    assert "Estimator: Test Est" in summary
    assert "var1: 0.5000" in summary
