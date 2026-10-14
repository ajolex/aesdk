# AESDK Agent Context: nonlinear_did

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Nonlinear Difference-in-Differences

Purpose: Handle DiD designs where the outcome, link function, or target effect is nonlinear and a linear TWFE coefficient is not the desired estimand.

## Required Assumptions
- The target scale and estimand are stated before estimation.
- Parallel trends or a design-specific substitute is stated on the relevant scale.
- Treatment timing and comparison groups are registered.
- Functional-form sensitivity is acknowledged and diagnosed.

## Required PAP Fields
- `nonlinear_did_block.outcome_family`
- `nonlinear_did_block.target_scale`
- `did_block.control_group`
- `did_block.staggered_adoption`
- `identification.clustering`

## Diagnostics
- Report the estimand scale and marginal effect or ATT transformation.
- Check functional-form sensitivity where feasible.
- Use DiD diagnostics for timing, comparison groups, and clustering.

## Blocks Or Warnings
- Block silent interpretation of nonlinear coefficients as level effects.
- Block missing comparison-group justification.
- Warn when the target scale is unclear.

## Source Locators
- `wooldridge_nonlinear_did_2023`
  - nonlinear DiD with panel data pages=[1, 2, 3, 12, 14, 17, 21, 22]
- `callaway_santanna_2021`
  - staggered DiD estimands and group-time effects

## Knowledge Pack Maturity
- status: pending_human_review
- source_review: ai_source_audited_pending_human_review
- code_recipes: starter

## Estimator Decision Tree
- Outcome is binary and the target is a probability-scale effect. -> Prefer estimators or post-estimation transformations that report ATT or marginal effects on the probability scale.
- Outcome is count-like and exposure varies. -> Consider Poisson-style mean models with careful interpretation and robust inference.
- Treatment timing is staggered. -> Use group-time or doubly robust DiD logic and avoid unqualified nonlinear TWFE.

## Failure Modes
- Raw nonlinear coefficient reported as ATT.: Block until post-estimation effect transformation is specified.
- Target scale is undefined.: Block under strict conformance.
- Staggered timing handled with unqualified nonlinear TWFE.: Warn or block and require modern/group-time logic.

## Code Recipes
- nonlinear-did-r-drdid: r / DRDID
- nonlinear-did-r-nonlinear-did: r / NonlinearDiD

## Reporting Checklist
- State outcome family and target effect scale.
- Report comparison group, timing design, and clustering.
- Report transformed ATT or marginal effects, not only model coefficients.
- Discuss functional-form sensitivity.
