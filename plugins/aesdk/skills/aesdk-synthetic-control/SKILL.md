---
name: aesdk-synthetic-control
description: "AESDK guardrails for Synthetic Control (synthetic_control): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Synthetic Control code (estimators: SyntheticControl, AugmentedSyntheticControl, SyntheticDiD). Typical setting: One or a few aggregate units receive treatment at a known time. A donor pool can reproduce the treated unit's pre-treatment outcome path or predictors."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method synthetic_control`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method synthetic_control --depth full`).

# Synthetic Control (synthetic_control)

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
