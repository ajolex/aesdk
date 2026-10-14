# AESDK Agent Context: matching

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Matching / Propensity Score Preprocessing

Purpose: Improve treated-control comparability on pre-treatment covariates before estimating treatment effects.

## Required Assumptions
- The covariates used for matching are measured before treatment.
- Selection into treatment is ignorable after the registered covariates, or the analysis is described as design support rather than causal proof.
- Treated and comparison units have common support.
- Post-matching outcome analysis respects the matched design and uncertainty.

## Required PAP Fields
- `matching_block.method`
- `matching_block.pre_treatment_covariates`
- `matching_block.estimand`
- `matching_block.balance_diagnostics`
- `identification.outcome_variable`
- `identification.treatment_variable`

## Diagnostics
- Report balance before and after matching.
- Inspect common support and discarded units.
- Report effective sample size and whether matching changed the target population.

## Blocks Or Warnings
- Block matching on post-treatment variables.
- Warn when balance remains poor after matching.
- Warn when discarded units make the estimand unclear.

## Source Locators
- `world_bank_impact_eval`
  - matching and propensity-score design pages=[173, 174, 175]
- `angrist_pischke_mhe`
  - selection, matching logic, and regression design comparisons pages=[30, 32, 34, 38, 58]

## Knowledge Pack Maturity
- status: pending_human_review
- source_review: ai_source_audited_pending_human_review
- code_recipes: starter

## Estimator Decision Tree
- Treatment is binary and covariates are rich pre-treatment controls. -> Use propensity-score, Mahalanobis, exact/coarsened exact, or hybrid matching; report balance.
- Common support is weak. -> Trim or redefine the estimand before estimating effects.
- Balance remains poor after matching. -> Block causal interpretation or revise the matching specification.

## Failure Modes
- Matching uses post-treatment variables.: Block; rebuild the covariate set with pre-treatment variables only.
- Poor balance remains after matching.: Warn or block under strict conformance.
- Discarded units change the estimand silently.: Require reporting of the retained population and estimand.

## Code Recipes
- matching-r-matchit: r / MatchIt
- matching-python-statsmodels-pscore: python / statsmodels
- matching-stata-teffects-psmatch: stata / Stata

## Reporting Checklist
- State ATT, ATC, or ATE and the retained analysis population.
- List all pre-treatment matching covariates.
- Report balance and support before and after matching.
- State whether matching is preprocessing or the main identifying design.
