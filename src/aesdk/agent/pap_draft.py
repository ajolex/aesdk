"""PAP drafting helpers for agent workflows."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


_METHOD_TO_STRATEGY = {
    "did": "DiD",
    "experimental_rct": "RCT",
    "gmm": "GMM",
    "iv_2sls": "IV",
    "limited_dependent": "Logit",
    "matching": "Matching",
    "nonlinear_did": "NonlinearDiD",
    "ols_cef": "OLS",
    "panel_fe": "TWFE",
    "rdd": "RDD",
    "synthetic_control": "SyntheticControl",
    "time_series": "ARIMA",
}


def _project_id(goal: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "_", goal.lower()).strip("_")
    return (slug[:48] or "aesdk_project").strip("_")


def _infer_data(data_path: str | Path | None, unit: str | None, time: str | None) -> dict[str, Any]:
    if data_path is None:
        structure = "panel" if unit and time else "cross-section"
        data = {"source": "TBD", "unit": unit or "unit", "structure": structure}
        if time:
            data["time_index"] = time
        return data
    path = Path(data_path)
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
    else:
        return {"source": str(path), "unit": unit or "unit", "structure": "cross-section"}

    structure = "panel" if unit and time and unit in df.columns and time in df.columns else "cross-section"
    data: dict[str, Any] = {"source": str(path), "unit": unit or "unit", "structure": structure, "N": int(len(df))}
    if structure == "panel":
        data["T"] = int(df[time].nunique())
        data["G"] = int(df[unit].nunique())
    return data


def draft_pap(
    *,
    goal: str,
    method: str,
    data_path: str | Path | None = None,
    outcome: str = "outcome",
    treatment: str = "treatment",
    covariates: list[str] | None = None,
    unit: str | None = None,
    time: str | None = None,
    author: str = "AESDK Agent",
    expected_sign: str = "ambiguous",
    design_origin: str | None = None,
) -> dict[str, Any]:
    """Draft a minimal PAP dictionary from agent-known analysis metadata."""

    strategy = _METHOD_TO_STRATEGY.get(method, "other")
    pap: dict[str, Any] = {
        "project": {
            "id": _project_id(goal),
            "title": goal,
            "author": author,
            "date_registered": date.today().isoformat(),
            "version": "1.0.0",
        },
        "data": _infer_data(data_path, unit, time),
        "identification": {
            "strategy": strategy,
            "treatment_variable": treatment,
            "outcome_variable": outcome,
            "covariates": {"mandatory": covariates or [], "optional": []},
            "standard_errors": "cluster" if method in {"did", "panel_fe"} else "HC3",
            "expected_sign": expected_sign,
        },
        "robustness": {"specification_curve": False},
    }

    if unit and method in {"did", "panel_fe"}:
        pap["identification"]["clustering"] = unit
    if design_origin:
        pap["identification"]["design_origin"] = design_origin
    if method in {"did", "panel_fe"}:
        fixed_effects = [item for item in [unit, time] if item]
        if fixed_effects:
            pap["identification"]["fixed_effects"] = fixed_effects
    if method == "did":
        pap["did_block"] = {
            "parallel_trends_test": True,
            "event_study_leads_lags": [-3, -2, -1, 0, 1, 2, 3],
            "staggered_adoption": False,
            "treatment_pre_announced": False,
            "anticipation_periods": 0,
            "control_group": "never_treated",
            "control_group_justification": "Drafted by AESDK; researcher must verify comparison-group credibility.",
            "goodman_bacon_decomposition": False,
            "hausman_test_documented": False,
            "placebo_test": True,
        }
    if method == "iv_2sls":
        pap["iv_block"] = {"instruments": ["TBD"], "first_stage_f_threshold": 10}
    if method == "experimental_rct":
        pap["rct_block"] = {
            "randomization_unit": unit or "unit",
            "assignment_variable": treatment,
            "treatment_arms": [treatment],
            "control_group": "control",
            "assignment_probability": 0.5,
            "randomization_method": "TBD",
            "estimand": "ITT",
            "baseline_balance_check": True,
            "attrition_check": False,
            "spillover_plan": "TBD",
            "spillover_risk": False,
            "sutva_rationale": "TBD",
            "power_calculation": False,
            "trial_registration": False,
            "pap_registered": True,
        }
    return pap
