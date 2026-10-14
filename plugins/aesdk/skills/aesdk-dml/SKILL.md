---
name: aesdk-dml
description: "AESDK guardrails for Double / Debiased Machine Learning (dml): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Double / Debiased Machine Learning code (estimators: DML, DoubleML, PLR, PLIV, IRM, CausalForest). Typical setting: A low-dimensional causal or structural parameter must be estimated with many controls or flexible nuisance functions. Identification rests on unconfoundedness given controls, or on a valid instrument."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method dml`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method dml --depth full`).

# Double / Debiased Machine Learning (dml)

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Double / Debiased Machine Learning

Purpose: Estimate a low-dimensional causal parameter in the presence of high-dimensional nuisance functions using Neyman-orthogonal scores and cross-fitting.

## Required Assumptions
- The target parameter and identification (unconfoundedness or a valid instrument) are stated before estimation.
- The moment/score used for the target parameter is Neyman-orthogonal.
- Nuisance functions are estimated by machine learning with cross-fitting (sample splitting).
- Regularization/overfitting bias is controlled through orthogonalization and cross-fitting.

## Required PAP Fields
- `dml_block.target_parameter`
- `dml_block.identification`
- `dml_block.nuisance_learners`
- `dml_block.cross_fitting_folds`
- `dml_block.orthogonal_score`

## Diagnostics
- Report the number of cross-fitting folds and repetitions.
- Report nuisance-learner choices and tuning.
- Report sensitivity to learners and folds.
- For heterogeneous effects, report honest inference (e.g., causal forests).

## Blocks Or Warnings
- Block causal DML without a stated identification assumption.
- Warn when cross-fitting is not used (regularization bias).
- Warn when the score is not orthogonal to the nuisance functions.

## Source Locators
- `chernozhukov_dml_2018`
- `wager_athey_2018`
