# AESDK Agent Context: nonparametric

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

## Knowledge Pack Maturity
- status: reviewed_guardrail
- source_review: primary_source_page_audited
- code_recipes: starter

## Estimator Decision Tree
- The conditional mean is smooth and there are one or two continuous regressors. -> Use kernel regression or local polynomial regression with data-driven bandwidth.
- A flexible but computationally simple global fit is acceptable. -> Use a series/sieve estimator and disclose the number of terms.
- There are several continuous regressors. -> Impose a semiparametric restriction (e.g., partially linear or single-index) to avoid the curse of dimensionality.

## Failure Modes
- Hand-picked bandwidth that drives the result.: Warn and require a data-driven, disclosed selection rule with sensitivity.
- Many continuous regressors making the estimator effectively uninformative.: Warn and require a semiparametric restriction or dimension reduction.

## Code Recipes
- nonparametric-python-kernelreg: python / statsmodels
- nonparametric-r-np: r / np

## Reporting Checklist
- State the estimand and the smoothing method.
- Report the bandwidth/series-selection rule and sensitivity to it.
- Report the number of continuous regressors and any semiparametric restriction.
- Describe boundary handling and the inference method for confidence bands.
