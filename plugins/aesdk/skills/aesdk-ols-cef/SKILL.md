---
name: aesdk-ols-cef
description: "AESDK guardrails for OLS / CEF Regression (ols_cef): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing OLS / CEF Regression code (estimators: OLS). Typical setting: The estimand is a conditional mean relationship or a causal parameter justified by design. The analysis can state treatment, outcome, covariates, and inference plan before estimation."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method ols_cef`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method ols_cef --depth full`).

# OLS / CEF Regression (ols_cef)

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
