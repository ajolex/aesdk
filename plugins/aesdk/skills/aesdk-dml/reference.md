# AESDK Agent Context: dml

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

## Knowledge Pack Maturity
- status: pending_human_review
- source_review: ai_source_audited_pending_human_review
- code_recipes: starter

## Estimator Decision Tree
- Treatment is unconfounded given high-dimensional controls and the effect is a scalar. -> Use a partially linear regression (PLR) or interactive regression model (IRM) DML estimator with cross-fitting.
- Identification uses an instrument. -> Use a partially linear IV (PLIV) DML estimator; the instrument must still satisfy relevance and exclusion.
- The goal is heterogeneous treatment effects (CATE). -> Use a causal forest or a DML-based CATE learner and report honest confidence intervals.

## Failure Modes
- Calling an association causal without an identification assumption.: Block causal interpretation until unconfoundedness or an instrument is stated.
- No cross-fitting, so regularization/overfitting bias contaminates the estimate.: Warn and require cross-fitting.
- Using a non-orthogonal plug-in of machine-learning predictions.: Warn and require a Neyman-orthogonal score.

## Code Recipes
- dml-python-doubleml: python / doubleml
- dml-r-grf-causalforest: r / grf

## Reporting Checklist
- State the target parameter and the identification assumption.
- Report the orthogonal score (PLR/PLIV/IRM) and the nuisance learners.
- Report cross-fitting folds/repetitions and sensitivity to learners.
- For heterogeneous effects, report honest confidence intervals.
