---
name: aesdk-gmm
description: "AESDK guardrails for Generalized Method of Moments (gmm): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Generalized Method of Moments code (estimators: GMM, IVGMM, DynamicPanelGMM). Typical setting: The model is defined by moment restrictions, orthogonality conditions, or instrumented equations. A full likelihood is unavailable, undesirable, or less central than valid moments."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method gmm`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method gmm --depth full`).

# Generalized Method of Moments (gmm)

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Generalized Method of Moments

Purpose: Estimate parameters from moment restrictions when the model is defined by orthogonality or equilibrium conditions.

## Required Assumptions
- Moment conditions are explicitly derived and registered.
- Identification rank and parameter count are checked.
- The weighting matrix and covariance estimator are documented.
- Overidentification tests are interpreted as diagnostics, not proof of validity.

## Required PAP Fields
- `gmm_block.moment_conditions`
- `gmm_block.parameters`
- `gmm_block.instruments`
- `gmm_block.weighting_matrix`
- `gmm_block.identification_rank`

## Diagnostics
- Check moment-condition dimensions and identification.
- Report overidentification diagnostics when overidentified.
- Report sensitivity to weighting matrix and instrument set.

## Blocks Or Warnings
- Block GMM without explicit moment conditions.
- Block if there are fewer valid moments than parameters.
- Warn when many instruments may weaken finite-sample performance.

## Source Locators
- `greene_econometric_analysis`
  - GMM and advanced econometric estimation pages=[3, 9, 10, 11, 12, 14, 22, 31]
- `hansen_1982`
  - large sample properties of GMM estimators
