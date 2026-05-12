import json

import pandas as pd
import statsmodels.formula.api as smf


DATA_PATH = "docs/examples/simulated_did_training_policy/training_policy_panel.csv"

df = pd.read_csv(DATA_PATH)

model = smf.ols(
    "employment_rate ~ policy_active + median_income + unemployment_rate + C(state) + C(year)",
    data=df,
).fit(cov_type="cluster", cov_kwds={"groups": df["state"]})

effect = float(model.params["policy_active"])
se = float(model.bse["policy_active"])
summary = {
    "estimand": "Average DiD effect of state job-training subsidy on employment_rate",
    "estimator": "OLS DiD with state and year fixed effects",
    "standard_errors": "clustered by state",
    "n_obs": int(model.nobs),
    "treatment_effect": round(effect, 4),
    "clustered_se": round(se, 4),
    "ci_95": [round(effect - 1.96 * se, 4), round(effect + 1.96 * se, 4)],
}

print(json.dumps(summary, indent=2, sort_keys=True))
