---
name: aesdk-limited-dependent
description: "AESDK guardrails for Limited Dependent Variable Models (limited_dependent): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Limited Dependent Variable Models code (estimators: Logit, ConditionalLogit, MixedLogit, Probit, Tobit, Poisson, NegativeBinomial, OrderedLogit, MultinomialLogit). Typical setting: The outcome is binary, censored, truncated, ordered, multinomial, conditional choice, mixed choice, fractional, or a count. The analysis needs effects that respect the outcome support."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method limited_dependent`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method limited_dependent --depth full`).

# Limited Dependent Variable Models (limited_dependent)

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
