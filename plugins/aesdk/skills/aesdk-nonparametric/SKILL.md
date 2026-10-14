---
name: aesdk-nonparametric
description: "AESDK guardrails for Nonparametric / Semiparametric Estimation (nonparametric): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Nonparametric / Semiparametric Estimation code (estimators: KernelRegression, LocalPolynomial, SeriesEstimator, LOESS). Typical setting: The shape of a conditional mean or density should be estimated flexibly rather than assumed. There are few continuous conditioning variables."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method nonparametric`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method nonparametric --depth full`).

# Nonparametric / Semiparametric Estimation (nonparametric)

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Nonparametric / Semiparametric Estimation

Purpose: Estimate conditional means or densities with flexible functional forms that do not impose a global parametric shape.

## Required Assumptions
- The estimand (for example the conditional mean function) and the smoothing target are stated.
- Bandwidth or series-length selection is data-driven and disclosed.
- The dimension of continuous conditioning variables is small enough to avoid the curse of dimensionality.
- Boundary bias and inference (bias-corrected or undersmoothed) are addressed.

## Required PAP Fields
- `nonparametric_block.estimator`
- `nonparametric_block.bandwidth_rule`
- `nonparametric_block.continuous_regressors`
- `nonparametric_block.inference_plan`

## Diagnostics
- Report the bandwidth/series-selection rule and sensitivity to it.
- Report the number of continuous conditioning variables (curse of dimensionality).
- Address boundary bias and the inference method for confidence bands.

## Blocks Or Warnings
- Warn when bandwidth selection is undisclosed or arbitrary.
- Warn when many continuous regressors make nonparametric estimation infeasible.

## Source Locators
- `li_racine_nonparametric_2007`
  - kernel density and kernel regression estimation pages=[52, 104, 110]
  - local constant and local polynomial (local linear) estimation pages=[124, 127, 132]
  - bandwidth selection by cross-validation pages=[59, 63, 117, 205]
  - kernel estimation with mixed continuous and discrete data pages=[178, 194]
