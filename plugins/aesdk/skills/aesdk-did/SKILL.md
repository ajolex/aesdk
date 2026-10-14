---
name: aesdk-did
description: "AESDK guardrails for Differences-in-Differences (did): identifying assumptions, required pre-analysis-plan fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. Use before writing or reviewing Differences-in-Differences code (estimators: DiD, TWFE, EventStudy). Typical setting: A treatment, policy, or exposure changes for one group but not for a credible comparison group. Outcome data are observed before and after treatment. The research question targets a treatment effect under a parallel-trends style design."
license: Apache-2.0
---

Follow the `aesdk-workflow` steps with `--method did`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method did --depth full`).

# Differences-in-Differences (did)

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
