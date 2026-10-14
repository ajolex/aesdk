---
name: aesdk-nonlinear-did
description: "AESDK guardrails for Nonlinear Difference-in-Differences (nonlinear_did): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Nonlinear Difference-in-Differences code (estimators: NonlinearDiD, PoissonDiD, LogitDiD, DRDID). Typical setting: A DiD design has binary, count, fractional, or otherwise nonlinear outcomes. The target effect is on a scale that a linear TWFE coefficient does not directly represent."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method nonlinear_did`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method nonlinear_did --depth full`).

# Nonlinear Difference-in-Differences (nonlinear_did)

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
