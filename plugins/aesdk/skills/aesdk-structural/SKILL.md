---
name: aesdk-structural
description: "AESDK guardrails for Structural Estimation (IO / BLP) (structural): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Structural Estimation (IO / BLP) code (estimators: BLP, StructuralGMM, StructuralMLE, DiscreteChoiceDemand). Typical setting: Counterfactuals require deep parameters (preferences, costs, technology) that only a model can recover. Equilibrium or optimality conditions link observed data to structural parameters."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method structural`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method structural --depth full`).

# Structural Estimation (IO / BLP) (structural)

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Structural Estimation (IO / BLP)

Purpose: Estimate structural (deep) parameters from an economic model and equilibrium/optimality restrictions, enabling model-driven counterfactuals.

## Required Assumptions
- The economic model, deep parameters, and equilibrium/optimality conditions are stated.
- Endogenous variables (for example prices) are instrumented with a defensible instrument set.
- Identification of the structural parameters from the moments/likelihood is argued.
- Counterfactuals are tied to the estimated model, with stated out-of-sample caveats.

## Required PAP Fields
- `structural_block.model`
- `structural_block.parameters`
- `structural_block.moment_or_likelihood`
- `structural_block.instruments`
- `structural_block.identification_argument`

## Diagnostics
- Report the estimation moments/likelihood and the instruments used for endogenous variables.
- Report identification and fit diagnostics.
- Report sensitivity of counterfactuals to key parameters and assumptions.

## Blocks Or Warnings
- Block structural counterfactuals without a stated model and identification argument.
- Warn when endogenous prices/choices are not instrumented.
- Warn when counterfactuals extrapolate far beyond the estimation support.

## Source Locators
- `berry_levinsohn_pakes_1995`
- `hayashi_econometrics_2000`
  - single-equation GMM and orthogonality conditions pages=[203, 208, 211]
  - GMM identification and the rank condition pages=[219, 281]
  - efficient GMM and the optimal weighting matrix pages=[230, 233]
- `train_discrete_choice_2009`
  - logit choice probabilities and identification of choice models pages=[39, 76]
  - nested logit and mixed logit (random coefficients) pages=[101, 163, 172]
  - simulation-based estimation (MSL/MSM) pages=[287, 296]
