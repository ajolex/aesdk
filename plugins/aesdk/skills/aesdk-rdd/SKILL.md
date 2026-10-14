---
name: aesdk-rdd
description: "AESDK guardrails for Regression Discontinuity Design (rdd): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Regression Discontinuity Design code (estimators: RDD). Typical setting: Treatment assignment changes discontinuously at a known cutoff in a running variable. Units near the cutoff are plausibly comparable."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method rdd`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method rdd --depth full`).

# Regression Discontinuity Design (rdd)

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
