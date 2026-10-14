# AESDK Agent Context: time_series

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

## Knowledge Pack Maturity
- status: pending_human_review
- source_review: ai_source_audited_pending_human_review
- code_recipes: starter

## Estimator Decision Tree
- The goal is forecasting a single series. -> Use ARIMA/SARIMAX or another forecasting model with train/test temporal split.
- Multiple series interact dynamically. -> Consider VAR/VECM after stationarity and cointegration checks.
- Regression uses time-series errors. -> Use HAC/Newey-West or an explicit serial-correlation model.

## Failure Modes
- No time index.: Block time-series workflow.
- Spurious regression with trending nonstationary series.: Warn or block until stationarity/cointegration plan is stated.
- Look-ahead bias.: Block forecast evaluation until data splitting is corrected.

## Code Recipes
- ts-python-statsmodels-sarimax: python / statsmodels
- ts-stata-arima: stata / Stata
- ts-r-stats-arima: r / stats

## Reporting Checklist
- State time index, frequency, sample period, and forecast/causal target.
- Report stationarity, trend, seasonality, and lag-order choices.
- Report residual autocorrelation diagnostics.
- For forecasting, use temporal out-of-sample evaluation.
