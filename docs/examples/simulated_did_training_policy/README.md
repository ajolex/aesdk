# Example: A Simulated Difference-in-Differences Study

This example is written for an RA or instructor who wants to see how AESDK changes an AI-assisted analysis workflow.

Imagine the research question is:

> Did a state-level job-training subsidy reduce county employment rates?

The data here are simulated, so we know the true effect. The point is not the substantive result. The point is to show how AESDK forces the AI agent to check the design before it writes or runs code.

## What The Example Shows

The example walks through five steps:

1. Generate panel data.
2. Use a pre-analysis plan.
3. Compare a bad proposal with a good proposal.
4. Let AESDK block the bad proposal.
5. Run the good proposal and leave a reproducibility record.

## Files

- `generate_data.py`: creates the simulated panel data.
- `training_policy_panel.csv`: simulated state-year panel data.
- `pap.yaml`: the pre-analysis plan.
- `proposal_blocked.json`: a bad proposal that uses the wrong inference choice.
- `proposal_pass.json`: a proposal that clusters at the treatment assignment level.
- `exec_code.py`: the analysis code that AESDK runs only after preflight passes.

## Step 1: Generate The Data

```bash
python docs/examples/simulated_did_training_policy/generate_data.py
```

The simulated true treatment effect is `-2.25`.

## Step 2: Ask AESDK What A DiD Design Requires

```bash
aesdk agent context --method did
```

This prints the assumptions, diagnostics, and source-backed guardrails that an AI agent should read before writing code.

## Step 3: Run Preflight On The Good Proposal

```bash
aesdk agent preflight --method did --pap docs/examples/simulated_did_training_policy/pap.yaml --proposal docs/examples/simulated_did_training_policy/proposal_pass.json --conformance strict
```

Expected result:

```text
status=pass blocked=False
```

## Step 4: See AESDK Block A Bad Proposal

```bash
aesdk agent preflight --method did --pap docs/examples/simulated_did_training_policy/pap.yaml --proposal docs/examples/simulated_did_training_policy/proposal_blocked.json --conformance strict
```

Expected result:

```text
status=block blocked=True
```

The blocked proposal uses a non-clustered standard error choice in a panel DiD setting. AESDK stops the agent before analysis code runs.

## Step 5: Run The Approved Analysis

```bash
aesdk agent run --method did --pap docs/examples/simulated_did_training_policy/pap.yaml --proposal docs/examples/simulated_did_training_policy/proposal_pass.json --code-file docs/examples/simulated_did_training_policy/exec_code.py --conformance strict
```

The analysis should estimate a negative treatment effect close to the simulated true effect.

## Step 6: Check The Reproducibility Record

```bash
aesdk reproduce --blob docs/examples/simulated_did_training_policy/.aesdk.json --replay
```

This verifies the recorded run and replays the execution event.

## Optional: Use The Analysis Helper Directly

AESDK also has a small Python analysis helper:

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

Expected estimate:

```text
-2.2298
```

That is close to the simulated true effect of `-2.25`.
