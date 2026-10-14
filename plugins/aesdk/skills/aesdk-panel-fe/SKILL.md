---
name: aesdk-panel-fe
description: "AESDK guardrails for Panel Fixed Effects / Unobserved Effects (panel_fe): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Panel Fixed Effects / Unobserved Effects code (estimators: FE, TWFE, POLS, RE). Typical setting: Repeated observations are available for the same units. The design needs to control for time-invariant unobserved heterogeneity. Identification comes from within-unit change, time shocks, or both."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method panel_fe`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method panel_fe --depth full`).

# Panel Fixed Effects / Unobserved Effects (panel_fe)

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
