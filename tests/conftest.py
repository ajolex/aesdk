import json
import shutil
import sys
import uuid
from pathlib import Path

import pytest
import yaml

SRC_DIR = Path(__file__).resolve().parents[1] / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture()
def valid_pap_dict() -> dict:
    return {
        "project": {
            "id": "did_min_wage",
            "title": "Minimum wage effects with panel DiD",
            "author": "AESDK Test",
            "date_registered": "2026-03-07",
            "version": "1.0.0",
        },
        "data": {
            "source": "min_wage_panel.csv",
            "unit": "state",
            "structure": "panel",
            "N": 500,
            "T": 10,
            "G": 50,
            "time_invariant_vars": [],
        },
        "identification": {
            "strategy": "DiD",
            "treatment_variable": "treated",
            "outcome_variable": "employment",
            "covariates": {"mandatory": ["income"], "optional": ["unemployment"]},
            "standard_errors": "cluster",
            "clustering": "state",
            "expected_sign": "negative",
        },
        "did_block": {
            "parallel_trends_test": True,
            "event_study_leads_lags": [-3, -2, -1, 0, 1, 2, 3],
            "staggered_adoption": True,
            "control_group": "never_treated",
            "control_group_justification": "States never adopting treatment",
            "treatment_pre_announced": False,
            "anticipation_periods": 0,
            "goodman_bacon_decomposition": True,
            "hausman_test_documented": False,
            "placebo_test": True,
        },
        "robustness": {"specification_curve": False},
    }


@pytest.fixture()
def runtime_dir() -> Path:
    target = Path("tests/.runtime") / str(uuid.uuid4())
    target.mkdir(parents=True, exist_ok=True)
    yield target
    shutil.rmtree(target, ignore_errors=True)


@pytest.fixture()
def valid_pap_file(runtime_dir: Path, valid_pap_dict: dict) -> Path:
    target = runtime_dir / "pap.yaml"
    target.write_text(yaml.safe_dump(valid_pap_dict, sort_keys=False), encoding="utf-8")
    return target


@pytest.fixture()
def blocked_did_proposal_file(runtime_dir: Path) -> Path:
    proposal = {
        "estimator": "TWFE",
        "standard_errors": "HC3",
        "clustering": "state",
        "treatment_level": "state",
    }
    target = runtime_dir / "proposal.json"
    target.write_text(json.dumps(proposal), encoding="utf-8")
    return target
