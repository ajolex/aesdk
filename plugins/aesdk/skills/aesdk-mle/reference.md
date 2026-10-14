# AESDK Agent Context: mle

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

## Knowledge Pack Maturity
- status: reviewed_guardrail
- source_review: primary_source_page_audited
- code_recipes: starter

## Estimator Decision Tree
- The parametric model is believed correctly specified. -> Use MLE with information-matrix standard errors; report LR/Wald/LM tests.
- The conditional mean is of interest but the full density may be misspecified. -> Use quasi-MLE (e.g., Poisson QMLE) with robust sandwich standard errors and say so.
- Optimization is unstable or the likelihood is flat. -> Report convergence, try multiple starting values, and check identification before interpreting estimates.

## Failure Modes
- Reporting estimates from a run that did not converge.: Block interpretation until convergence is confirmed.
- Classical standard errors under a misspecified density.: Warn and require robust (sandwich) inference or a correct-specification argument.

## Code Recipes
- mle-python-genericlikelihood: python / statsmodels
- mle-r-stats4: r / stats4

## Reporting Checklist
- State the distribution/likelihood and the parameters estimated.
- Report convergence and identification diagnostics.
- State the standard-error type (information matrix vs robust sandwich).
- Interpret marginal effects where the raw coefficients are not the quantity of interest.
