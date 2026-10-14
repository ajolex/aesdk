import pandas as pd
import statsmodels.formula.api as smf

df = pd.read_csv("training_policy_panel.csv")
fit = smf.ols("employment_rate ~ policy_active + C(state) + C(year)", data=df).fit()
print(fit.params["policy_active"])
