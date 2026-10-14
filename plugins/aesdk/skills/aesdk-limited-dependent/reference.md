# AESDK Agent Context: limited_dependent

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Limited Dependent Variable Models

Purpose: Model binary, censored, truncated, ordered, multinomial, or count outcomes with estimators and interpretations suited to the outcome support.

## Required Assumptions
- The outcome type and support are declared before choosing the estimator.
- Coefficients are not reported as marginal effects unless transformed.
- Functional form, link function, and distributional assumptions are documented.
- Convergence and sparse-cell risks are checked.

## Required PAP Fields
- `limited_dependent_block.outcome_type`
- `limited_dependent_block.link_or_family`
- `limited_dependent_block.target_effect`
- `limited_dependent_block.marginal_effect_plan`
- `identification.covariates`

## Diagnostics
- Report marginal effects or predicted probabilities when appropriate.
- Check convergence and separation for binary models.
- Check overdispersion for count models.

## Blocks Or Warnings
- Block interpreting logit/probit coefficients as probability effects.
- Warn on convergence failure or separation.
- Warn when a count model ignores overdispersion.

## Source Locators
- `greene_econometric_analysis`
  - limited dependent variable and nonlinear models pages=[179, 211, 212, 214, 450]
- `wooldridge_cross_section_panel`
  - binary response and nonlinear panel/cross-section models pages=[534, 535, 536, 537, 538, 539]

## Knowledge Pack Maturity
- status: pending_human_review
- source_review: ai_source_audited_pending_human_review
- code_recipes: starter

## Estimator Decision Tree
- Outcome is binary. -> Use logit/probit, conditional logit, mixed logit, or a linear probability model with interpretation and inference explicitly justified.
- Outcome is censored or corner-solution. -> Consider Tobit or two-part models and state censoring assumptions.
- Outcome is a count. -> Use Poisson or negative binomial logic and check overdispersion.

## Failure Modes
- Logit/probit coefficient interpreted as probability effect.: Block or require marginal effects.
- Complete separation.: Warn or block and revise model/data.
- Count model ignores overdispersion.: Warn and require robust or alternative count specification.

## Code Recipes
- limited-python-statsmodels-logit: python / statsmodels
- limited-python-statsmodels-poisson: python / statsmodels
- limited-r-stats-glm-logit: r / stats
- limited-r-stats-glm-poisson: r / stats
- limited-stata-logit: stata / Stata
- limited-stata-poisson: stata / Stata

## Reporting Checklist
- State outcome type, link/family, and target effect scale.
- Report marginal effects or predicted contrasts when needed.
- Report convergence, separation, and overdispersion checks; for repeated choice panels, cluster or otherwise account for respondent-level dependence.
- Avoid causal language unless identification is separately justified.
