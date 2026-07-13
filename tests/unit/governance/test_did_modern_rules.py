"""Tests for the modern DiD guardrails grounded in Roth, Sant'Anna, Bilinski & Poe (2023)."""

from __future__ import annotations

import aesdk as ae


def _did_pap(**did_overrides) -> dict:
    did_block = {
        "parallel_trends_test": True,
        "event_study_leads_lags": [-2, -1, 0, 1, 2],
        "staggered_adoption": False,
        "control_group": "never_treated",
        "control_group_justification": "Never-treated units share the pre-period trend.",
    }
    did_block.update(did_overrides)
    return {
        "project": {
            "id": "did_modern",
            "title": "Modern DiD guardrails fixture",
            "author": "AESDK Test",
            "date_registered": "2026-07-13",
            "version": "1.0.0",
        },
        "data": {"source": "no_such_file.csv", "unit": "state", "time": "year", "structure": "panel"},
        "identification": {
            "strategy": "DiD",
            "treatment_variable": "treated",
            "outcome_variable": "y",
            "covariates": {"mandatory": [], "optional": []},
            "standard_errors": "cluster",
            "clustering": "state",
            "expected_sign": "positive",
        },
        "did_block": did_block,
        "robustness": {"specification_curve": False},
    }


def _preflight(pap: dict):
    import tempfile
    from pathlib import Path

    import yaml

    d = Path(tempfile.mkdtemp())
    p = d / "pap.yaml"
    p.write_text(yaml.safe_dump(pap), encoding="utf-8")
    return ae.preflight(
        method="did",
        pap_path=p,
        proposal={"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"},
        conformance="basic",
        scan_data_file=False,
    )


def test_missing_best_practices_surface_as_info_guidance() -> None:
    result = _preflight(_did_pap())
    by_id = {v.rule_id: v for v in result.violations}
    assert {"AP-DID-007", "AP-DID-008", "AP-DID-009"}.issubset(by_id)
    # Advisory: they surface guidance without changing the gate for a well-formed PAP.
    assert all(by_id[r].severity.value == "info" for r in ["AP-DID-007", "AP-DID-008", "AP-DID-009"])
    assert result.status == "pass"


def test_declaring_best_practices_clears_warnings() -> None:
    result = _preflight(
        _did_pap(
            sensitivity_analysis=True,
            no_anticipation=True,
            parallel_trends_transformation="levels",
        )
    )
    ids = {v.rule_id for v in result.violations}
    assert "AP-DID-007" not in ids
    assert "AP-DID-008" not in ids
    assert "AP-DID-009" not in ids


def test_twfe_with_covariates_flagged() -> None:
    result = _preflight(
        _did_pap(
            sensitivity_analysis=True,
            no_anticipation=True,
            parallel_trends_transformation="levels",
            covariate_adjustment="twfe_covariates",
        )
    )
    ids = {v.rule_id for v in result.violations}
    assert "AP-DID-010" in ids


def test_doubly_robust_adjustment_not_flagged() -> None:
    result = _preflight(
        _did_pap(
            sensitivity_analysis=True,
            no_anticipation=True,
            parallel_trends_transformation="levels",
            covariate_adjustment="doubly_robust",
        )
    )
    ids = {v.rule_id for v in result.violations}
    assert "AP-DID-010" not in ids
