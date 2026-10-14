---
name: aesdk-bayesian
description: "AESDK guardrails for Bayesian Econometrics (bayesian): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Bayesian Econometrics code (estimators: BayesianRegression, MCMC, GibbsSampler, BayesianVAR, HierarchicalBayes). Typical setting: Prior information should be combined with the likelihood, or a full posterior is wanted. Hierarchical structure or regularization is naturally expressed through priors."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method bayesian`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method bayesian --depth full`).

# Bayesian Econometrics (bayesian)

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Bayesian Econometrics

Purpose: Estimate a posterior distribution over parameters by combining a likelihood with declared priors, typically via MCMC.

## Required Assumptions
- Priors are declared and justified, and the likelihood is stated.
- Posterior sampling (MCMC) convergence is checked.
- Prior sensitivity is assessed.
- Reported quantities (posterior means, credible intervals) are interpreted as Bayesian, not frequentist.

## Required PAP Fields
- `bayesian_block.priors`
- `bayesian_block.likelihood`
- `bayesian_block.sampler`
- `bayesian_block.convergence_plan`
- `bayesian_block.prior_sensitivity_plan`

## Diagnostics
- Report convergence diagnostics (for example R-hat, effective sample size, trace plots).
- Report prior specification and a prior-sensitivity analysis.
- Report credible intervals and posterior predictive checks.

## Blocks Or Warnings
- Block Bayesian estimates without declared priors.
- Warn when MCMC convergence is not demonstrated.
- Warn when credible intervals are reported as frequentist confidence intervals.

## Source Locators
- `koop_poirier_tobias_2007`
  - choice of prior pages=[103, 104]
  - Bayesian interval (credible) estimation pages=[75]
  - the normal linear regression model pages=[131]
  - Bayesian computation, Gibbs sampling, Metropolis-Hastings, and convergence pages=[142, 153, 158, 167]
