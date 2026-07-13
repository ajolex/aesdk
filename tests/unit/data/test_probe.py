"""Tests for data-aware preflight probes."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import aesdk as ae
from aesdk.data import scan_data


def _pap(source: str, **overrides) -> dict:
    pap = {
        "project": {
            "id": "did_probe",
            "title": "DiD data probe fixture",
            "author": "AESDK Test",
            "date_registered": "2026-07-13",
            "version": "1.0.0",
        },
        "data": {"source": source, "unit": "state", "time": "year", "structure": "panel"},
        "identification": {
            "strategy": "DiD",
            "treatment_variable": "treated",
            "outcome_variable": "employment",
            "covariates": {"mandatory": ["income"], "optional": []},
            "standard_errors": "cluster",
            "clustering": "state",
            "expected_sign": "negative",
        },
        "did_block": {"parallel_trends_test": True, "staggered_adoption": False},
        "robustness": {"specification_curve": False},
    }
    for key, value in overrides.items():
        pap[key] = value
    return pap


def _write_panel(
    path: Path,
    *,
    n_states: int = 60,
    n_years: int = 6,
    staggered: bool = False,
    outcome_missing_frac: float = 0.0,
) -> None:
    rows = []
    for s in range(n_states):
        # Half the states are treated; adoption year varies iff staggered.
        adopt = None
        if s % 2 == 0:
            adopt = 3 + (s % 3) if staggered else 3
        for y in range(1, n_years + 1):
            treated = 1 if (adopt is not None and y >= adopt) else 0
            emp = 100.0 + s + y + (5 if treated else 0)
            rows.append({"state": f"S{s}", "year": y, "treated": treated, "employment": emp, "income": 10.0 + y})
    df = pd.DataFrame(rows)
    if outcome_missing_frac > 0:
        n_missing = int(len(df) * outcome_missing_frac)
        df.loc[df.index[:n_missing], "employment"] = None
    df.to_csv(path, index=False)


def test_scan_missing_file_degrades_gracefully(tmp_path: Path) -> None:
    result = scan_data(method="did", pap=_pap("does_not_exist.csv"), base_dirs=[tmp_path])
    assert result.scanned is False
    assert result.findings == []
    assert result.profile.reason_unresolved


def test_scan_detects_unstaggered_panel(tmp_path: Path) -> None:
    data = tmp_path / "panel.csv"
    _write_panel(data, staggered=False)
    result = scan_data(method="did", pap=_pap("panel.csv"), base_dirs=[tmp_path])
    assert result.scanned is True
    assert result.profile.n_units == 60
    assert result.profile.adoption_cohorts == 1
    ids = {f.rule_id for f in result.findings}
    assert "DATA-DID-001" not in ids


def test_scan_flags_undeclared_staggered_adoption(tmp_path: Path) -> None:
    data = tmp_path / "panel.csv"
    _write_panel(data, staggered=True)
    result = scan_data(method="did", pap=_pap("panel.csv"), base_dirs=[tmp_path], conformance="strict")
    ids = {f.rule_id for f in result.findings}
    assert "DATA-DID-001" in ids
    finding = next(f for f in result.findings if f.rule_id == "DATA-DID-001")
    # Warning escalates under strict conformance.
    assert finding.severity.value == "error"
    assert result.profile.adoption_cohorts and result.profile.adoption_cohorts > 1


def test_scan_flags_missing_core_variable(tmp_path: Path) -> None:
    data = tmp_path / "panel.csv"
    _write_panel(data, staggered=False)
    pap = _pap("panel.csv")
    pap["identification"]["outcome_variable"] = "wages_not_a_column"
    result = scan_data(method="did", pap=pap, base_dirs=[tmp_path])
    ids = {f.rule_id for f in result.findings}
    assert "DATA-VARS-001" in ids
    finding = next(f for f in result.findings if f.rule_id == "DATA-VARS-001")
    assert finding.severity.value == "error"


def test_scan_flags_few_clusters(tmp_path: Path) -> None:
    data = tmp_path / "panel.csv"
    _write_panel(data, n_states=10, staggered=False)
    result = scan_data(method="did", pap=_pap("panel.csv"), base_dirs=[tmp_path])
    ids = {f.rule_id for f in result.findings}
    assert "DATA-CLUST-001" in ids
    assert result.profile.n_clusters == 10


def test_scan_suppresses_few_clusters_when_wild_bootstrap(tmp_path: Path) -> None:
    data = tmp_path / "panel.csv"
    _write_panel(data, n_states=10, staggered=False)
    pap = _pap("panel.csv")
    pap["identification"]["standard_errors"] = "wild-cluster-bootstrap"
    result = scan_data(method="did", pap=pap, base_dirs=[tmp_path])
    # The recommended few-clusters remedy is already declared, so no nag.
    assert "DATA-CLUST-001" not in {f.rule_id for f in result.findings}
    assert result.profile.n_clusters == 10


def test_scan_flags_singleton_clusters(tmp_path: Path) -> None:
    data = tmp_path / "panel.csv"
    df = pd.DataFrame(
        {
            "state": ["A", "A", "B", "B", "C"],  # C is a singleton cluster
            "year": [1, 2, 1, 2, 1],
            "treated": [0, 1, 0, 0, 0],
            "employment": [1.0, 2.0, 3.0, 4.0, 5.0],
            "income": [5.0, 6.0, 7.0, 8.0, 9.0],
        }
    )
    df.to_csv(data, index=False)
    result = scan_data(method="did", pap=_pap("panel.csv"), base_dirs=[tmp_path])
    ids = {f.rule_id for f in result.findings}
    assert "DATA-CLUST-002" in ids
    assert result.profile.n_singleton_clusters == 1


def test_scan_flags_high_missingness(tmp_path: Path) -> None:
    data = tmp_path / "panel.csv"
    _write_panel(data, staggered=False, outcome_missing_frac=0.4)
    result = scan_data(method="did", pap=_pap("panel.csv"), base_dirs=[tmp_path])
    ids = {f.rule_id for f in result.findings}
    assert "DATA-MISS-001" in ids


def test_scan_flags_zero_variance_covariate(tmp_path: Path) -> None:
    data = tmp_path / "panel.csv"
    df = pd.DataFrame(
        {
            "state": ["A", "A", "B", "B"],
            "year": [1, 2, 1, 2],
            "treated": [0, 1, 0, 0],
            "employment": [1.0, 2.0, 3.0, 4.0],
            "income": [5.0, 5.0, 5.0, 5.0],  # constant
        }
    )
    df.to_csv(data, index=False)
    result = scan_data(method="did", pap=_pap("panel.csv"), base_dirs=[tmp_path])
    ids = {f.rule_id for f in result.findings}
    assert "DATA-COLLIN-001" in ids


def test_scan_skips_expression_covariates(tmp_path: Path) -> None:
    data = tmp_path / "panel.csv"
    _write_panel(data, staggered=False)
    pap = _pap("panel.csv")
    pap["identification"]["covariates"]["mandatory"] = ["log(income)", "i.year"]
    result = scan_data(method="did", pap=pap, base_dirs=[tmp_path])
    # Constructed expressions must not be flagged as missing columns.
    assert "DATA-VARS-003" not in {f.rule_id for f in result.findings}


def test_preflight_integrates_data_scan(tmp_path: Path) -> None:
    data = tmp_path / "panel.csv"
    _write_panel(data, staggered=True)
    pap_path = tmp_path / "pap.yaml"
    import yaml

    pap_path.write_text(yaml.safe_dump(_pap("panel.csv"), sort_keys=False), encoding="utf-8")
    result = ae.preflight(
        method="did",
        pap_path=pap_path,
        proposal={"estimator": "TWFE", "standard_errors": "cluster", "clustering": "state"},
        conformance="strict",
    )
    assert result.data_scanned is True
    assert "DATA-DID-001" in {v.rule_id for v in result.violations}
    payload = json.loads(json.dumps(result.to_dict()))
    assert payload["data_scan"]["scanned"] is True


def test_preflight_no_scan_flag_disables_probe(tmp_path: Path) -> None:
    data = tmp_path / "panel.csv"
    _write_panel(data, staggered=True)
    pap_path = tmp_path / "pap.yaml"
    import yaml

    pap_path.write_text(yaml.safe_dump(_pap("panel.csv"), sort_keys=False), encoding="utf-8")
    result = ae.preflight(
        method="did",
        pap_path=pap_path,
        proposal={"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"},
        conformance="strict",
        scan_data_file=False,
    )
    assert result.data_scan is None
    assert "DATA-DID-001" not in {v.rule_id for v in result.violations}
