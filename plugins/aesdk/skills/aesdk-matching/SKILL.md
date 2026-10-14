---
name: aesdk-matching
description: "AESDK guardrails for Matching / Propensity Score Preprocessing (matching): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Matching / Propensity Score Preprocessing code (estimators: Matching, PropensityScore, Mahalanobis, EntropyBalance). Typical setting: The design compares treated and untreated units after improving balance on pre-treatment covariates. The research team can defend selection on observed covariates or uses matching as transparent preprocessing."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method matching`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method matching --depth full`).

# Matching / Propensity Score Preprocessing (matching)

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
