# AESDK Agent Context: structural

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Structural Estimation (IO / BLP)

Purpose: Estimate structural (deep) parameters from an economic model and equilibrium/optimality restrictions, enabling model-driven counterfactuals.

## Required Assumptions
- The economic model, deep parameters, and equilibrium/optimality conditions are stated.
- Endogenous variables (for example prices) are instrumented with a defensible instrument set.
- Identification of the structural parameters from the moments/likelihood is argued.
- Counterfactuals are tied to the estimated model, with stated out-of-sample caveats.

## Required PAP Fields
- `structural_block.model`
- `structural_block.parameters`
- `structural_block.moment_or_likelihood`
- `structural_block.instruments`
- `structural_block.identification_argument`

## Diagnostics
- Report the estimation moments/likelihood and the instruments used for endogenous variables.
- Report identification and fit diagnostics.
- Report sensitivity of counterfactuals to key parameters and assumptions.

## Blocks Or Warnings
- Block structural counterfactuals without a stated model and identification argument.
- Warn when endogenous prices/choices are not instrumented.
- Warn when counterfactuals extrapolate far beyond the estimation support.

## Source Locators
- `berry_levinsohn_pakes_1995`
- `hayashi_econometrics_2000`
  - single-equation GMM and orthogonality conditions pages=[203, 208, 211]
  - GMM identification and the rank condition pages=[219, 281]
  - efficient GMM and the optimal weighting matrix pages=[230, 233]
- `train_discrete_choice_2009`
  - logit choice probabilities and identification of choice models pages=[39, 76]
  - nested logit and mixed logit (random coefficients) pages=[101, 163, 172]
  - simulation-based estimation (MSL/MSM) pages=[287, 296]

## Knowledge Pack Maturity
- status: reviewed_guardrail
- source_review: primary_source_page_audited
- code_recipes: starter

## Estimator Decision Tree
- The target is differentiated-product demand with endogenous prices. -> Use a BLP-style random-coefficients logit with demand instruments (e.g., cost shifters, BLP instruments).
- Individual-level discrete choices are observed. -> Use simulation-based discrete-choice estimation (mixed/nested logit) with a stated choice set.
- The model is defined by moment/equilibrium conditions. -> Use structural GMM; document the moments and the identifying instruments.

## Failure Modes
- Presenting counterfactuals without a stated model or identification.: Block until the model and identification argument are documented.
- Treating endogenous prices/choices as exogenous.: Warn and require instruments for the endogenous variables.
- Extrapolating counterfactuals far outside the estimation support.: Warn and require an out-of-support caveat.

## Code Recipes
- structural-python-pyblp: python / pyblp
- structural-python-choice: python / statsmodels

## Reporting Checklist
- State the economic model, the deep parameters, and the equilibrium/optimality conditions.
- Report the estimation moments or likelihood and the instruments for endogenous variables.
- Report identification and fit diagnostics.
- Report counterfactuals with sensitivity and out-of-support caveats.
