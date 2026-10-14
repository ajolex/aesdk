# AESDK Agent Context: did

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Differences-in-Differences

Purpose: Estimate treatment effects by comparing outcome changes between treated and comparison groups under a parallel-trends design.

## Required Assumptions
- A credible comparison group is defined before estimation.
- Parallel trends or a design-specific substitute is argued and diagnosed.
- Treatment timing, anticipation, and dynamic effects are documented.
- Inference accounts for clustering and serial correlation in grouped or panel treatment designs.

## Required PAP Fields
- `did_block.parallel_trends_test`
- `did_block.event_study_leads_lags`
- `did_block.staggered_adoption`
- `did_block.control_group`
- `did_block.control_group_justification`
- `identification.standard_errors`
- `identification.clustering`

## Diagnostics
- Report pre-treatment event-study leads or another registered pre-trend diagnostic.
- Document the comparison group for staggered adoption.
- Avoid plain TWFE as the default estimator when treatment timing is staggered.
- Use placebo or falsification checks when registered.

## Blocks Or Warnings
- Block staggered-adoption TWFE unless a modern estimator or decomposition strategy is registered.
- Block DiD without clustered or stronger inference for panel/grouped designs.
- Block missing comparison-group justification.
- Warn when pre-trend diagnostics are missing.

## Source Locators
- `angrist_pischke_mhe`
  - fixed effects, differences-in-differences, and panel data pages=[181]
  - differences-in-differences examples and diagnostics pages=[185, 187, 189, 191, 193]
  - clustering and serial correlation in panels pages=[238, 247, 249, 251]
- `callaway_santanna_2021`
  - multiple-period DiD with staggered treatment timing

## Knowledge Pack Maturity
- status: reviewed_guardrail
- source_review: partial_multi_source
- code_recipes: starter

## Estimator Decision Tree
- There are exactly two periods and a single treated cohort. -> Use a simple DiD contrast or an equivalent regression with treatment, post, and interaction terms.
- There are many periods but all treated units adopt at the same time. -> Use TWFE or event-study regression, with clustered inference and registered pre-trend checks.
- Treatment adoption is staggered across cohorts. -> Prefer group-time ATT, interaction-weighted event study, stacked DiD, or a documented decomposition strategy; block unqualified plain TWFE.
- The outcome is nonlinear or binary and the target is not a linear mean effect. -> Escalate to nonlinear DiD guidance; do not silently use linear TWFE as the estimand.
- Treatment turns on and off, or a unit is treated more than once (non-absorbing). -> Use estimators built for switching treatments (de Chaisemartin & D'Haultfoeuille 2020/2024); state any no-carryover assumption. Do not use standard absorbing-treatment DiD estimators.
- Treatment is continuous or multi-valued (a dose or intensity). -> Use continuous/multi-valued DiD estimators (Callaway, Goodman-Bacon & Sant'Anna; de Chaisemartin & D'Haultfoeuille) and define the dose-specific estimand; a single binary indicator misstates it.

## Failure Modes
- No comparison-group justification.: Block causal execution until the comparison group is declared and defended.
- Plain TWFE under staggered adoption.: Block unless the PAP registers a modern estimator, decomposition, or justified homogeneous-effects design.
- Conventional standard errors in panel/grouped treatment.: Block and require clustered or stronger inference.
- Treating a non-significant, underpowered pre-trend test as proof of parallel trends.: Warn; require a sensitivity analysis (Rambachan & Roth) rather than a pre-test verdict.
- Adding covariates linearly to a TWFE regression to satisfy conditional parallel trends.: Warn; require regression adjustment, IPW, or a doubly-robust estimator instead.

## Code Recipes
- did-python-pyfixest-event-study: python / pyfixest
- did-r-did-att-gt: r / did
- did-stata-xtdidregress: stata / Stata

## Reporting Checklist
- State the treated group, comparison group, treatment timing, and estimand.
- State the parallel-trends and no-anticipation assumptions, and the outcome scale (levels/logs) they are assumed in.
- Report the estimator and why it matches the timing design (and, if staggered, that it is heterogeneity-robust).
- Show pre-trend or registered substitute diagnostics, and a sensitivity analysis to parallel-trends violations.
- Report clustering level, number of clusters, and small-cluster adjustments if used; for event studies, report uniform sup-t bands.
- If covariates are needed for identification, report a doubly-robust/IPW/regression-adjustment estimator, not TWFE-with-covariates.
- Separate design evidence from statistical significance.
