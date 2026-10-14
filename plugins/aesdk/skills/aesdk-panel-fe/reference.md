# AESDK Agent Context: panel_fe

## Binding Instructions
- Do not write econometric execution code until AESDK preflight passes.
- Treat `block` as a hard stop.
- Treat `warn` as requiring documented researcher acknowledgement.
- Do not invent assumptions, diagnostics, or citations.

## Method: Panel Fixed Effects / Unobserved Effects

Purpose: Use repeated observations to control for time-invariant unobserved heterogeneity or model panel dependence.

## Required Assumptions
- The panel unit and time index are declared.
- The source of identifying variation after fixed effects is described.
- Serial correlation, heteroskedasticity, and clustering are addressed in inference.
- Time-invariant regressors are not interpreted as identified by unit fixed effects.

## Required PAP Fields
- `data.unit`
- `data.structure`
- `data.N`
- `data.T`
- `identification.fixed_effects`
- `identification.standard_errors`
- `identification.clustering`

## Diagnostics
- Cluster at the repeated-observation unit or treatment assignment level.
- Consider serial correlation diagnostics for longer panels.
- Document whether fixed effects, random effects, or pooled models match the estimand.

## Blocks Or Warnings
- Block panel workflows using conventional or only HC standard errors when clustered inference is required.
- Block clustering below the treatment assignment level when that level is known.
- Warn when fixed-effects identification is claimed but the remaining within-unit variation is not described.

## Source Locators
- `wooldridge_cross_section_panel`
  - fixed effects and unobserved effects pages=[424, 438, 446, 447, 448]
  - panel data models pages=[460, 774, 809]
- `angrist_pischke_mhe`
  - Parallel Worlds: fixed effects, differences-in-differences, and panel data pages=[181]

## Knowledge Pack Maturity
- status: reviewed_guardrail
- source_review: partial_multi_source
- code_recipes: starter

## Estimator Decision Tree
- Unobserved unit traits may confound treatment and are plausibly time-invariant. -> Use unit fixed effects and explain the within-unit identifying variation.
- Common shocks vary by period. -> Add time fixed effects if they match the estimand.
- Treatment is assigned at a group level. -> Cluster at least at the assignment level.

## Failure Modes
- Conventional standard errors in panel data.: Block when clustered or stronger inference is required.
- Claiming identification for a time-invariant regressor under unit FE.: Block or rewrite the estimand.
- Fixed effects used as automatic causal proof.: Require a design argument for within-unit exogeneity.

## Code Recipes
- panel-python-linearmodels: python / linearmodels
- panel-r-fixest: r / fixest
- panel-stata-xtreg: stata / Stata

## Reporting Checklist
- Declare unit and time dimensions.
- List all fixed effects and explain what variation remains.
- Report cluster level and cluster count.
- Avoid causal language unless the within-unit identification argument is stated.
