---
name: aesdk-iv-2sls
description: "AESDK guardrails for Instrumental Variables / 2SLS (iv_2sls): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Instrumental Variables / 2SLS code (estimators: IV, 2SLS). Typical setting: The treatment or exposure is endogenous because of omitted variables, simultaneity, measurement error, or selection. There is at least one excluded instrument with a substantive relevance and exclusion argument."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method iv_2sls`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method iv_2sls --depth full`).

# Instrumental Variables / 2SLS (iv_2sls)

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Instrumental Variables / 2SLS

Purpose: Estimate causal effects when treatment or exposure is endogenous and valid excluded instruments are available.

## Required Assumptions
- Excluded instruments are relevant for the endogenous variable.
- Excluded instruments affect the outcome only through the endogenous variable.
- Excluded instruments are independent of unobserved determinants of the outcome under the design.
- The estimand is interpreted carefully when effects are heterogeneous.

## Required PAP Fields
- `iv_block.instruments`
- `iv_block.first_stage_f_threshold`
- `identification.treatment_variable`
- `identification.outcome_variable`
- `identification.covariates`

## Diagnostics
- Report first-stage strength for excluded instruments.
- Use heteroskedasticity-robust or cluster-robust 2SLS inference as appropriate.
- When overidentified, report and interpret overidentification checks as diagnostics rather than proof of validity.
- Document the substantive exclusion restriction argument.

## Blocks Or Warnings
- Block IV execution when no excluded instrument is registered.
- Block or warn when the reported first-stage statistic is below the registered threshold.
- Warn when first-stage evidence is missing.

## Source Locators
- `wooldridge_cross_section_panel`
  - instrumental variables estimation pages=[466, 468, 470, 472, 474]
- `angrist_pischke_mhe`
  - IV and causality pages=[100, 101, 103, 105]
