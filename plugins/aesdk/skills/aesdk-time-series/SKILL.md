---
name: aesdk-time-series
description: "AESDK guardrails for Time-Series Econometrics (time_series): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Time-Series Econometrics code (estimators: ARIMA, ARMAX, VAR, VECM, ARDL, HACRegression). Typical setting: Temporal ordering, serial dependence, dynamics, forecasting, or nonstationarity are central to the analysis. The data have a meaningful time index and frequency."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method time_series`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method time_series --depth full`).

# Time-Series Econometrics (time_series)

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Time-Series Econometrics

Purpose: Model serial dependence, dynamics, forecasting, or time-series causal/regression designs with explicit attention to stationarity and temporal ordering.

## Required Assumptions
- The time index and frequency are declared.
- Stationarity, trends, seasonality, and breaks are addressed before estimation.
- Lag order and forecast horizon are registered.
- Inference accounts for serial correlation when regression is used.

## Required PAP Fields
- `time_series_block.time_index`
- `time_series_block.frequency`
- `time_series_block.stationarity_plan`
- `time_series_block.lag_order_plan`
- `time_series_block.forecast_or_causal_target`

## Diagnostics
- Inspect time plots, autocorrelation, and partial autocorrelation.
- Run unit-root or stationarity checks where relevant.
- Report lag-selection criteria and residual diagnostics.
- Guard against look-ahead bias in forecasting.

## Blocks Or Warnings
- Block time-series regression with no time index.
- Warn on likely spurious regression with trending nonstationary series.
- Warn when forecast evaluation uses future information.

## Source Locators
- `stock_watson_intro_econometrics`
  - time-series regression and forecasting pages=[17, 18, 19, 23, 24, 32, 38]
- `greene_econometric_analysis`
  - time-series econometrics pages=[3, 9, 10, 14, 15, 23, 24, 30]
