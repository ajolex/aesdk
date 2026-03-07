# Phase 4 — Automated Specification Curve Analysis (`aesdk.curve`)

**Goal:** Turn the LLM from a writing tool into a rigor tool. Automatically generate
every plausible model variation and visualize how fragile or robust the core finding is.

---

## 4.1 Theoretical Grounding

Specification Curve Analysis (SCA) is based on:
- **Simonsohn, Simmons & Nelson (2020)** — *Specification Curve Analysis*, Nature Human Behaviour
- **Leamer (1983)** — *Let's Take the Con Out of Econometrics* (Extreme Bounds Analysis)
- **Young (2022)** — *Consistency without Inference* (robustness of Stata results)

The core question: **Is the sign and significance of β stable across all defensible
model specifications?**

---

## 4.2 Specification Dimensions (PAP-Configured)

The researcher defines in the PAP what dimensions are "in play" for the SCA.
The SDK generates the full Cartesian product of valid combinations.

```yaml
# In PAP: robustness section
robustness:
  specification_curve: true
  vary_controls:
    baseline: ["state_fe", "year_fe"]
    optional_sets:
      - ["log_gdp_per_capita"]
      - ["unemployment_rate_lag1"]
      - ["log_population"]
      - ["log_gdp_per_capita", "unemployment_rate_lag1"]
  vary_clustering:
    - "state"
    - "state-year"
    - "none (robust)"
  vary_functional_form:
    - "linear"
    - "log-linear"
    - "log-log"
  vary_sample:
    - "full"
    - "drop_outliers_p99"
    - "balanced_panel_only"
  vary_estimator:
    - "FE-TWFE"
    - "stacked-DiD"         # Cengiz et al. approach
    - "Callaway-SantAnna"   # CS DiD for staggered adoption
```

---

## 4.3 SCA Output

The SDK produces:
1. **Specification Table** — One row per specification, with β, SE, p-value, N, R², controls used
2. **Specification Curve Plot** — Sorted by β, colored by significance (p<0.05)
3. **Robustness Summary** — % of specs significant, % with correct sign, p-value distribution

```
Specification Curve: Effect of Minimum Wage on log(Employment)

β estimates (sorted):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 -0.32 ███████████████████ *** (spec 14: log-log, CS-DiD, state cluster)
 -0.28 ████████████████ ***   (spec 03: linear, TWFE, state cluster)
 -0.19 ██████████ **          (spec 07: linear, stacked, robust SE)
 -0.11 ██████ *               (spec 01: log-lin, TWFE, no cluster)
 +0.04 ██ (ns)                (spec 22: linear, TWFE, no FE, robust)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Summary:
  Total specifications: 48
  Significant (p<0.05): 38 (79.2%)
  Correct sign (negative): 45 (93.8%)
  Median β: -0.21 [95% CI: -0.31, -0.12]
  Robustness verdict: ROBUST ✓
```

---

## 4.4 Key Modules

### `aesdk.curve.SpecificationEngine`
- Generates specification grid from PAP robustness block
- Validates each spec against governance rules before running
- Executes specs in parallel (async or multiprocessing)

### `aesdk.curve.SCAPlotter`
- Sorted β plot with CI bars
- Lower panel: indicator matrix (which controls/options active per spec)
- Export: PNG, SVG, interactive Plotly HTML

### `aesdk.curve.RobustnessSummary`
- Computes: % significant, % correct sign, p-value histogram
- Flags: specs that flip sign (potential non-robustness)
- Compares to researcher's "preferred" spec from PAP

---

## 4.5 Task Checklist

- [ ] Build `SpecificationEngine`: grid generation, PAP integration, rule validation per spec
- [ ] Async/parallel execution of spec grid via `aesdk.sandbox`
- [ ] Build `SCAPlotter` (matplotlib primary, Plotly optional)
- [ ] Build `RobustnessSummary` with formal SCA statistics
- [ ] Integrate into `aesdk.Project` as `research.run_sca()`
- [ ] CLI: `aesdk sca --pap my_project.pap.yaml --output ./sca_results/`
- [ ] Export specification table as CSV/LaTeX
- [ ] Edge case handling: non-convergent specs, singular matrices, small-N subsamples

---

## 4.6 Review Criteria
- Is the spec grid fully derived from PAP (no ad-hoc additions by agent)?
- Is each spec validated against governance rules before execution?
- Does the plot clearly show robustness vs. fragility?
- Is the summary interpretable by a non-technical reader?