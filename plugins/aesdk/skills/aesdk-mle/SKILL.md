---
name: aesdk-mle
description: "AESDK guardrails for Maximum Likelihood Estimation (mle): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Maximum Likelihood Estimation code (estimators: MLE, QMLE). Typical setting: A fully parametric model implies a likelihood for the observed data. The estimand is a parameter of that distribution or a function of it."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method mle`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method mle --depth full`).

# Maximum Likelihood Estimation (mle)

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Maximum Likelihood Estimation

Purpose: Estimate parameters by maximizing a likelihood implied by a declared distributional model, with inference from the information matrix.

## Required Assumptions
- The parametric density/likelihood is explicitly specified.
- The likelihood is correctly specified, or quasi-MLE with robust inference is used and stated.
- Optimization convergence and identification are checked.
- Standard errors come from the information matrix, or a robust sandwich under possible misspecification.

## Required PAP Fields
- `mle_block.distribution`
- `mle_block.likelihood`
- `mle_block.parameters`
- `mle_block.optimizer`
- `mle_block.standard_error_type`

## Diagnostics
- Report convergence status and starting-value sensitivity.
- Check identification and the information-matrix conditioning.
- Use likelihood-ratio, Wald, or LM tests appropriately.
- Prefer robust (sandwich) standard errors when the density may be misspecified.

## Blocks Or Warnings
- Block MLE without a declared distribution/likelihood.
- Warn when convergence is not confirmed.
- Warn when non-robust standard errors are used under a quasi-likelihood interpretation.

## Source Locators
- `greene_econometric_analysis`
  - maximum likelihood estimation, log-likelihood, and the information matrix pages=[509, 520, 524]
  - likelihood-ratio, Wald, and Lagrange-multiplier tests pages=[509, 514]
  - pseudo-/quasi-maximum likelihood and robust covariance pages=[545, 546]
