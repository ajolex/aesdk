# AESDK Agent Context: experimental_rct

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Randomized Controlled Trials / Experimental Methods

Purpose: Estimate causal effects from randomized assignment while keeping the target estimand, assignment process, compliance, attrition, and spillovers explicit.

## Required Assumptions
- Treatment assignment is randomized according to a documented and reproducible assignment rule.
- The estimand is declared before analysis, such as ITT, ATE, ATT/ToT, or LATE.
- Interference, attrition, noncompliance, and implementation deviations are checked before causal claims.
- Inference matches the randomization unit and any clustering or stratification.

## Required PAP Fields
- `rct_block.randomization_unit`
- `rct_block.assignment_variable`
- `rct_block.treatment_arms`
- `rct_block.estimand`
- `identification.outcome_variable`
- `identification.treatment_variable`
- `identification.standard_errors`

## Diagnostics
- Report baseline balance and assignment reproducibility.
- Report compliance/take-up when estimating ATT/ToT or LATE.
- Report attrition, spillover checks, and a SUTVA rationale.
- Cluster at the randomization unit when assignment is clustered, or document a valid randomization-inference plan.

## Blocks Or Warnings
- Block RCT analysis without randomization unit, assignment variable, treatment arms, or estimand.
- Block LATE when compliance/take-up and exclusion/monotonicity arguments are missing.
- Block unqualified ATE claims when assignment is an encouragement or compliance is imperfect.
- Block cluster-randomized designs that omit the cluster level or cluster below the randomization unit.
- Warn when attrition, spillovers, power, trial registration, SUTVA rationale, or PAP registration are missing.

## Source Locators
- `jpal_randomization`
  - randomization, ATE intuition, assignment unit, strata, and replicable assignment
- `jpal_data_analysis`
  - ATE, LATE, treatment-on-treated, attrition, spillovers, and randomization inference
- `bedecarrats_guerin_roubaud_2015`
  - RCT scope and political-economy cautions pages=[1, 2, 3]

## Knowledge Pack Maturity
- status: pending_human_review
- source_review: ai_source_audited_pending_human_review
- code_recipes: starter

## Estimator Decision Tree
- Assignment and treatment receipt coincide with perfect compliance. -> Estimate ATE/ITT as the treatment-control mean difference or regression on assignment.
- Assignment is randomized but take-up is imperfect. -> Report ITT and, if justified, use assignment as an instrument for treatment receipt to estimate LATE.
- Randomization is clustered or stratified. -> Respect the randomization unit in inference and include the registered cluster level and strata/covariates.
- Attrition or spillovers differ by assignment. -> Do not report unqualified ATE; use bounds, sensitivity checks, or redesign the estimand.

## Failure Modes
- ATE claimed when assignment is only an encouragement and compliance is imperfect.: Block ATE; report ITT or justify LATE with compliance assumptions.
- Cluster-randomized design analyzed with individual iid standard errors.: Block or require clustered/randomization-unit inference with the cluster level declared.
- Differential attrition is ignored.: Warn or block under strict conformance; require bounds or sensitivity analysis.
- Spillovers contaminate the control group.: Require spillover-aware estimand, design adjustment, or sensitivity analysis.

## Code Recipes
- rct-python-statsmodels-itt: python / statsmodels
- rct-r-lm-itt: r / stats
- rct-stata-regress-itt: stata / Stata

## Reporting Checklist
- State randomization unit, assignment variable, treatment arms, and assignment probability.
- Archive a random seed, assignment file, public lottery record, or assignment script.
- State whether the reported estimand is ITT, ATE, ATT/ToT, or LATE.
- Report baseline balance, compliance/take-up, attrition, spillover diagnostics, and SUTVA rationale.
- Use clustering or randomization inference that matches the assignment design.
- Discuss external-validity and implementation-scope limits.
