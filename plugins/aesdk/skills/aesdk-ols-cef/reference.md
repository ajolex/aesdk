# AESDK Agent Context: ols_cef

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: OLS / CEF Regression

Purpose: Estimate conditional mean relationships and, under stated identification assumptions, causal parameters.

## Required Assumptions
- The target estimand is stated before estimation.
- The identifying variation is conditionally exogenous given the registered covariates or design.
- The functional form and included covariates are part of the pre-analysis plan.
- Inference is robust to plausible heteroskedasticity or clustering in the design.

## Required PAP Fields
- `identification.strategy`
- `identification.treatment_variable`
- `identification.outcome_variable`
- `identification.covariates`
- `identification.standard_errors`
- `robustness.specification_curve`

## Diagnostics
- Inspect covariate balance or design support where causal language is used.
- Use heteroskedasticity-robust inference unless conventional inference is explicitly justified.
- For grouped, repeated, or assigned-at-group designs, cluster at the assignment or sampling level.

## Blocks Or Warnings
- Block causal claims if the exogeneity/design assumption is not documented.
- Warn when conventional standard errors are used without justification.
- Block post-hoc covariate selection that is not declared in the PAP.

## Source Locators
- `wooldridge_cross_section_panel`
  - heteroskedasticity-robust inference pages=[253]
  - econometrics, causal questions, and data structures pages=[1, 2, 3, 4, 5]
- `angrist_pischke_mhe`
  - Making Regression Make Sense pages=[37, 38, 40, 42]

## Knowledge Pack Maturity
- status: reviewed_guardrail
- source_review: partial_multi_source
- code_recipes: starter

## Estimator Decision Tree
- The goal is prediction or descriptive association. -> Use OLS/CEF language and avoid causal claims.
- The goal is causal and treatment is as-good-as-random conditional on controls. -> Use OLS with registered covariates and robust or clustered inference.
- Treatment varies at group level or observations are repeated. -> Use clustered inference at the assignment/repeated-observation level.

## Failure Modes
- Causal language without identification.: Block or rewrite as descriptive.
- Conventional standard errors with plausible heteroskedasticity or dependence.: Warn or block under strict conformance.
- Post-hoc covariate selection.: Require disclosure and move to robustness/specification-curve workflow.

## Code Recipes
- ols-python-statsmodels: python / statsmodels
- ols-r-fixest: r / fixest
- ols-stata-regress: stata / Stata

## Reporting Checklist
- State whether the estimate is descriptive or causal.
- List all registered covariates.
- Report covariance estimator and any clustering.
- Discuss support, omitted-variable risk, and robustness checks.
