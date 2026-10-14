---
name: aesdk-experimental-rct
description: "AESDK guardrails for Randomized Controlled Trials / Experimental Methods (experimental_rct): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Randomized Controlled Trials / Experimental Methods code (estimators: RCT, RandomizedExperiment, RandomizedControlledTrial, ITT, ATE, ATT, ToT, LATE). Typical setting: Treatment or encouragement is assigned by a randomized rule. The research team can document the assignment unit, treatment arms, and assignment probabilities. The target estimand is ITT, ATE, ATT/ToT, LATE, or a registered experimental contrast."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method experimental_rct`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method experimental_rct --depth full`).

# Randomized Controlled Trials / Experimental Methods (experimental_rct)

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
