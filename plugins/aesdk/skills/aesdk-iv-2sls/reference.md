# AESDK Agent Context: iv_2sls

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

## Knowledge Pack Maturity
- status: reviewed_guardrail
- source_review: partial_multi_source
- code_recipes: starter

## Estimator Decision Tree
- One endogenous regressor and one excluded instrument. -> Use just-identified 2SLS; focus on relevance and exclusion rather than overidentification.
- More excluded instruments than endogenous regressors. -> Use overidentified 2SLS; report overidentification diagnostics as stress tests, not proof of validity.
- First-stage evidence is weak. -> Block default 2SLS interpretation; require stronger instruments, weak-IV robust inference, or design revision.

## Failure Modes
- No excluded instrument.: Block IV execution.
- Weak first stage.: Block standard IV interpretation until weak-instrument handling is registered.
- Exclusion restriction is asserted but not argued.: Warn or block under strict conformance.

## Code Recipes
- iv-python-linearmodels: python / linearmodels
- iv-stata-ivregress: stata / Stata
- iv-r-fixest: r / fixest

## Reporting Checklist
- Name every endogenous variable and excluded instrument.
- Report the first stage and weak-instrument threshold.
- Explain the exclusion restriction in substantive terms.
- State whether the estimate is interpreted as LATE or another instrument-specific estimand.
