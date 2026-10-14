# AESDK Agent Context: synthetic_control

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Synthetic Control

Purpose: Estimate effects for one or a few treated aggregate units using weighted donor units that match pre-treatment outcomes or predictors.

## Required Assumptions
- A credible donor pool is defined before estimation.
- The treated unit has enough pre-treatment history to assess fit.
- Donor units are not affected by the treatment or spillovers.
- The outcome path is comparable after weighting.

## Required PAP Fields
- `synthetic_control_block.treated_unit`
- `synthetic_control_block.donor_pool`
- `synthetic_control_block.intervention_time`
- `synthetic_control_block.predictors`
- `synthetic_control_block.placebo_tests`
- `identification.outcome_variable`

## Diagnostics
- Report pre-treatment fit and predictor balance.
- Report donor weights.
- Run placebo or permutation checks where feasible.
- Test sensitivity to donor-pool exclusions.

## Blocks Or Warnings
- Block when treated unit, intervention time, or donor pool is missing.
- Warn when pre-treatment fit is poor.
- Warn when the donor pool includes potentially treated or contaminated units.

## Source Locators
- `world_bank_impact_eval`
  - synthetic control in impact evaluation pages=[167, 168, 169, 174, 178]
- `abadie_diamond_hainmueller_2010`
  - synthetic control methods for comparative case studies

## Knowledge Pack Maturity
- status: pending_human_review
- source_review: ai_source_audited_pending_human_review
- code_recipes: starter

## Estimator Decision Tree
- There is one treated aggregate unit and many untreated donor units. -> Use classical synthetic control and report weights and pre-treatment fit.
- Pre-treatment fit is poor. -> Do not report a causal effect without redesigning the donor pool or method.
- There are multiple treated units or staggered timing. -> Consider generalized, augmented, or synthetic DiD variants with explicit aggregation.

## Failure Modes
- Poor pre-treatment fit.: Block strong causal claims or redesign the donor pool.
- Contaminated donor pool.: Exclude affected donors and rerun diagnostics.
- No placebo or sensitivity analysis.: Warn and require researcher acknowledgement.

## Code Recipes
- synth-python-scpi: python / scpi
- synth-r-synth: r / Synth
- synth-stata-scpi: stata / scpi

## Reporting Checklist
- State treated unit, treatment date, donor-pool eligibility, and predictors.
- Report pre-treatment fit before discussing post-treatment gaps.
- Report donor weights and influential-donor sensitivity.
- Report placebo/permutation evidence when feasible.
