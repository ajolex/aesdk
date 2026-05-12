from pathlib import Path

import numpy as np
import pandas as pd


SEED = 20260513
TRUE_EFFECT = -2.25
OUT = Path(__file__).with_name("training_policy_panel.csv")


def main() -> None:
    rng = np.random.default_rng(SEED)
    states = [f"S{str(i).zfill(2)}" for i in range(1, 13)]
    treated_states = set(states[:6])
    years = list(range(2016, 2024))
    state_fe = {state: rng.normal(0, 1.2) for state in states}
    rows = []

    for state in states:
        treated_group = int(state in treated_states)
        base_income = rng.normal(52_000, 4_500)
        base_unemp = rng.normal(5.8, 0.6)
        for year in years:
            post = int(year >= 2020)
            policy_active = treated_group * post
            year_trend = 0.35 * (year - 2016)
            median_income = base_income + 850 * (year - 2016) + rng.normal(0, 900)
            unemployment_rate = base_unemp - 0.08 * (year - 2016) + rng.normal(0, 0.35)
            employment_rate = (
                61.0
                + state_fe[state]
                + year_trend
                + 0.000035 * (median_income - 52_000)
                - 0.75 * unemployment_rate
                + TRUE_EFFECT * policy_active
                + rng.normal(0, 0.55)
            )
            rows.append(
                {
                    "state": state,
                    "year": year,
                    "treated_group": treated_group,
                    "post": post,
                    "policy_active": policy_active,
                    "median_income": round(float(median_income), 2),
                    "unemployment_rate": round(float(unemployment_rate), 3),
                    "employment_rate": round(float(employment_rate), 3),
                }
            )

    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"wrote={OUT}")
    print(f"seed={SEED} true_effect={TRUE_EFFECT}")


if __name__ == "__main__":
    main()
