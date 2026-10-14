# AESDK Agent Context: gmm

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Generalized Method of Moments

Purpose: Estimate parameters from moment restrictions when the model is defined by orthogonality or equilibrium conditions.

## Required Assumptions
- Moment conditions are explicitly derived and registered.
- Identification rank and parameter count are checked.
- The weighting matrix and covariance estimator are documented.
- Overidentification tests are interpreted as diagnostics, not proof of validity.

## Required PAP Fields
- `gmm_block.moment_conditions`
- `gmm_block.parameters`
- `gmm_block.instruments`
- `gmm_block.weighting_matrix`
- `gmm_block.identification_rank`

## Diagnostics
- Check moment-condition dimensions and identification.
- Report overidentification diagnostics when overidentified.
- Report sensitivity to weighting matrix and instrument set.

## Blocks Or Warnings
- Block GMM without explicit moment conditions.
- Block if there are fewer valid moments than parameters.
- Warn when many instruments may weaken finite-sample performance.

## Source Locators
- `greene_econometric_analysis`
  - GMM and advanced econometric estimation pages=[3, 9, 10, 11, 12, 14, 22, 31]
- `hansen_1982`
  - large sample properties of GMM estimators

## Knowledge Pack Maturity
- status: pending_human_review
- source_review: ai_source_audited_pending_human_review
- code_recipes: starter

## Estimator Decision Tree
- The problem is linear IV with heteroskedasticity concerns. -> Use IV-GMM only after registering instruments and weighting/covariance choices.
- The model is overidentified. -> Report overidentification diagnostics as stress tests.
- There are many instruments relative to sample size. -> Reduce instruments or document finite-sample risks.

## Failure Modes
- Moment conditions are not written down.: Block estimation.
- Underidentified parameter vector.: Block until moments, instruments, or parameters are revised.
- Many weak instruments.: Warn or block depending on severity and conformance.

## Code Recipes
- gmm-python-linearmodels-ivgmm: python / linearmodels
- gmm-r-gmm: r / gmm
- gmm-stata-gmm: stata / Stata

## Reporting Checklist
- Write moment conditions and parameters before code.
- Report instrument set, weighting matrix, and covariance estimator.
- Report identification/rank audit.
- Report overidentification diagnostics only as diagnostics.
