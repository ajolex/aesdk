---
name: aesdk-garch
description: "AESDK guardrails for Volatility Models (ARCH / GARCH) (garch): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Volatility Models (ARCH / GARCH) code (estimators: ARCH, GARCH, EGARCH, GJR-GARCH). Typical setting: A time series (often financial returns) shows volatility clustering to be modeled or forecast. The conditional variance, not only the conditional mean, is of interest."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method garch`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method garch --depth full`).

# Volatility Models (ARCH / GARCH) (garch)

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
