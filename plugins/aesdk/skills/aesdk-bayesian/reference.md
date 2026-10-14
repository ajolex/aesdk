# AESDK Agent Context: bayesian

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

## Knowledge Pack Maturity
- status: reviewed_guardrail
- source_review: primary_source_page_audited
- code_recipes: starter

## Estimator Decision Tree
- A standard regression with prior information is wanted. -> Use a Bayesian regression with explicit priors and report the posterior.
- Data are grouped/multilevel. -> Use a hierarchical model with priors on the group-level variances.
- The posterior has no closed form. -> Use MCMC and demonstrate convergence before summarizing the posterior.

## Failure Modes
- Reporting a posterior without declared priors.: Block until priors are stated.
- Summarizing a non-converged MCMC run.: Warn and require convergence evidence before interpretation.
- Reporting credible intervals as frequentist confidence intervals.: Warn and require correct Bayesian interpretation.

## Code Recipes
- bayesian-python-pymc: python / pymc
- bayesian-r-brms: r / brms

## Reporting Checklist
- State the priors and the likelihood.
- Report MCMC convergence diagnostics (R-hat, effective sample size).
- Report a prior-sensitivity analysis.
- Report credible intervals and interpret them as Bayesian, not frequentist.
