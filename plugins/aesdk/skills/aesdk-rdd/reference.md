# AESDK Agent Context: rdd

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Regression Discontinuity Design

Purpose: Estimate causal effects near a treatment assignment cutoff under continuity of potential outcomes around the threshold.

## Required Assumptions
- A running variable and cutoff define treatment assignment.
- Potential outcomes are smooth through the cutoff absent treatment.
- Units cannot precisely manipulate assignment around the cutoff, or manipulation is diagnosed and addressed.
- The bandwidth, polynomial/order choices, and inference method are registered before estimation.

## Required PAP Fields
- `rdd_block.running_variable`
- `rdd_block.cutoff`
- `rdd_block.bandwidth_rule`
- `rdd_block.manipulation_check`
- `identification.outcome_variable`
- `identification.treatment_variable`

## Diagnostics
- Check density or manipulation around the cutoff.
- Assess covariate continuity near the cutoff.
- Report sensitivity to bandwidth and functional-form choices.
- Separate sharp and fuzzy RD designs explicitly.

## Blocks Or Warnings
- Block RDD without a registered running variable and cutoff.
- Warn when no manipulation or density check is registered.
- Warn when bandwidth sensitivity is missing.

## Source Locators
- `angrist_pischke_mhe`
  - regression discontinuity designs pages=[205, 206]

## Knowledge Pack Maturity
- status: planned_guardrail
- source_review: limited
- code_recipes: starter

## Estimator Decision Tree
- Treatment is deterministically assigned by crossing the cutoff. -> Use sharp RDD.
- Crossing the cutoff changes treatment probability but not treatment deterministically. -> Use fuzzy RDD with the cutoff as an instrument for treatment.
- Running variable or cutoff is missing. -> Block RDD execution.

## Failure Modes
- No running variable or cutoff.: Block RDD execution.
- No manipulation check.: Warn and require researcher acknowledgement.
- High-order global polynomial used as default.: Warn and prefer local methods with bandwidth sensitivity.

## Code Recipes
- rdd-python-rdrobust: python / rdrobust
- rdd-r-rdrobust: r / rdrobust
- rdd-stata-rdrobust: stata / rdrobust

## Reporting Checklist
- State running variable, cutoff, and whether the design is sharp or fuzzy.
- Report bandwidth rule and sensitivity checks.
- Report manipulation/density and covariate-continuity diagnostics.
- Interpret the estimate as local to the cutoff.
