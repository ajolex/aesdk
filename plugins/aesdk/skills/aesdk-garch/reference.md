# AESDK Agent Context: garch

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Volatility Models (ARCH / GARCH)

Purpose: Model the conditional variance of a time series (volatility clustering) alongside its conditional mean.

## Required Assumptions
- The conditional-mean model is specified before the conditional-variance model.
- The residuals show ARCH effects that justify a volatility model.
- Stationarity and positivity constraints on the variance parameters hold (for example non-negative coefficients and persistence below one).
- The innovation distribution (normal, Student-t) is stated.

## Required PAP Fields
- `garch_block.mean_model`
- `garch_block.variance_model`
- `garch_block.innovation_distribution`
- `garch_block.arch_test_plan`

## Diagnostics
- Test for ARCH effects (Engle LM test) before fitting.
- Check parameter constraints and persistence (for example alpha plus beta below one for GARCH(1,1)).
- Check standardized-residual diagnostics (Ljung-Box and the assumed distribution).

## Blocks Or Warnings
- Warn when a volatility model is fit without evidence of ARCH effects.
- Warn when variance-parameter constraints are violated (non-stationary variance).

## Source Locators
- `tsay_financial_time_series_2010`
  - conditional heteroscedastic models and testing for ARCH effects pages=[122, 127, 131]
  - ARCH and GARCH model building and estimation pages=[135, 139]
  - EGARCH and leverage effects pages=[149, 153]

## Knowledge Pack Maturity
- status: reviewed_guardrail
- source_review: primary_source_page_audited
- code_recipes: starter

## Estimator Decision Tree
- Residuals show volatility clustering and symmetric responses. -> Use a GARCH(1,1) with a stated innovation distribution.
- Volatility responds asymmetrically to positive vs negative shocks (leverage). -> Use EGARCH or GJR-GARCH.
- Standardized residuals are heavy-tailed. -> Use a Student-t (or skewed-t) innovation distribution.

## Failure Modes
- Fitting a volatility model with no evidence of ARCH effects.: Warn and require an ARCH-LM test first.
- Estimated variance process is non-stationary or has negative coefficients.: Warn and require constraint checks before interpreting or forecasting.

## Code Recipes
- garch-python-arch: python / arch
- garch-r-rugarch: r / rugarch

## Reporting Checklist
- State the conditional-mean model, the variance model, and the innovation distribution.
- Report an ARCH-effects test justifying the volatility model.
- Report persistence and confirm stationarity/positivity constraints.
- Report standardized-residual diagnostics.
