# Simulated DiD Training Policy Example

This example shows AESDK as an econometrics SDK rather than a generic code runner.

Use case: an analyst wants to estimate whether a state-level job-training subsidy changed county employment rates. The data are simulated, but the workflow is realistic:

1. Generate or inspect panel data.
2. Register a pre-analysis plan.
3. Propose an analysis.
4. Let AESDK block invalid inference choices.
5. Run a compliant DiD analysis and write an auditable replication blob.

## Files

- `training_policy_panel.csv`: deterministic simulated panel data.
- `generate_data.py`: deterministic random-data generator.
- `pap.yaml`: pre-analysis plan for a non-staggered DiD design.
- `proposal_blocked.json`: intentionally invalid proposal using non-clustered standard errors.
- `proposal_pass.json`: compliant proposal using clustered inference at the treatment assignment level.
- `exec_code.py`: estimation script run through the AESDK sandbox.

## Commands

```bash
python docs/examples/simulated_did_training_policy/generate_data.py
aesdk methods show did --format yaml
aesdk methods sources did --format yaml
aesdk agent context --method did
aesdk agent preflight --method did --pap docs/examples/simulated_did_training_policy/pap.yaml --proposal docs/examples/simulated_did_training_policy/proposal_pass.json --conformance strict
aesdk validate --pap docs/examples/simulated_did_training_policy/pap.yaml --proposal docs/examples/simulated_did_training_policy/proposal_blocked.json --conformance strict
aesdk validate --pap docs/examples/simulated_did_training_policy/pap.yaml --proposal docs/examples/simulated_did_training_policy/proposal_pass.json --conformance strict
aesdk execute --pap docs/examples/simulated_did_training_policy/pap.yaml --proposal docs/examples/simulated_did_training_policy/proposal_pass.json --code-file docs/examples/simulated_did_training_policy/exec_code.py --context production --conformance strict --policy-version 1.2.0
aesdk reproduce --blob docs/examples/simulated_did_training_policy/.aesdk.json --replay
```

You can also run the same data through the SDK analysis layer:

```python
from aesdk.curve.runner import CurveRunner

runner = CurveRunner("docs/examples/simulated_did_training_policy/training_policy_panel.csv")
result = runner.execute_spec(
    "did",
    {
        "outcome": "employment_rate",
        "treatment": "policy_active",
        "time": "year",
        "covariates": ["median_income", "unemployment_rate"],
        "fixed_effects": ["state", "year"],
        "cluster": "state",
    },
)
print(round(result.coefficients["policy_active"], 4))
```

Expected behavior:

- `proposal_blocked.json` should return `status=block` because panel DiD requires clustered or stronger inference.
- `proposal_pass.json` should return `status=pass`.
- `exec_code.py` should estimate a negative treatment effect close to the simulated policy effect.
