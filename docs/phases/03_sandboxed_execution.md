# Phase 3 — Sandboxed Execution Engine (`aesdk.sandbox`)

**Goal:** Ensure all agent-generated code is validated statistically and syntactically
before the researcher sees any output. The sandbox is the last line of defense.

---

## 3.1 Architecture

```
Agent Code Output
       ↓
[Syntax Check] — AST parse, library whitelist check
       ↓
[Docker/venv Execution] — Isolated, reproducible environment
       ↓
[Statistical Soundness Check] — Econometric assumption tests
       ↓
      / \
  PASS   FAIL
   ↓       ↓
Proceed  [Self-Correction Loop]
           ↓
       Feed stack trace + econometric guidance back to agent
           ↓
       Agent revises (max N iterations)
           ↓
       Re-enter sandbox
```

---

## 3.2 Library Whitelist

The sandbox enforces a curated whitelist of econometric libraries.
Attempts to import unlisted libraries trigger a warning and require PAP-level approval.

```yaml
# aesdk/sandbox/whitelist.yaml
approved_libraries:
  econometrics:
    - statsmodels       # OLS, GLS, ARIMA, VAR
    - linearmodels      # Panel FE/RE, IV, Between
    - pyfixest         # High-dimensional FE (Correia-style)
    - rdrobust          # RDD (Calonico et al.)
    - doubleml          # Double/Debiased ML (Chernozhukov et al.)
    - causalml          # Causal ML methods
  data:
    - pandas
    - numpy
    - polars
  visualization:
    - matplotlib
    - seaborn
    - plotly
  utilities:
    - scipy
    - scikit-learn      # With warning: not for primary causal inference
```

---

## 3.3 Statistical Soundness Checks

Beyond syntax, the sandbox runs econometric diagnostics automatically:

| Check | Method | Triggered When |
|---|---|---|
| Multicollinearity | VIF > 10 flag | OLS, FE with many controls |
| Heteroskedasticity | Breusch-Pagan test | OLS without robust SE |
| Serial Correlation | Wooldridge test for panel | Panel FE/RE |
| Weak Instruments | Kleibergen-Paap F < 10 | IV/2SLS |
| Overlap / Common Support | Propensity score overlap plot | Matching |
| Pre-trend Test | Event study F-test for pre-periods | DiD |
| Bandwidth Sensitivity | RD estimate at ±10%, ±20% bandwidth | RDD |
| Singleton Clusters | Count singletons | Clustered SE |
| Separation | Perfect prediction check | Probit/Logit |

Each failed check generates a structured `SandboxDiagnostic` fed to the self-correction loop.

---

## 3.4 Self-Correction Loop

```python
# Conceptual flow
MAX_ITERATIONS = 3

for attempt in range(MAX_ITERATIONS):
    result = sandbox.run(agent_code)
    if result.status == "pass":
        break
    
    correction_prompt = sdk.build_correction_prompt(
        stack_trace=result.error,
        diagnostics=result.diagnostics,
        pap=research.pap,
        rules=research.active_rules
    )
    # Correction prompt references specific textbook fixes:
    # "Weak instrument detected (F=6.2 < 10). Per Angrist & Pischke (MHE, Ch.4),
    #  consider stronger instruments or LIML. Do not simply remove the IV."
    
    agent_code = agent.revise(correction_prompt)
else:
    raise AESDKError("Max sandbox iterations reached. Human review required.")
```

---

## 3.5 Task Checklist

- [ ] Build Docker image: `aesdk-sandbox:latest` with approved library set
- [ ] Implement `aesdk.sandbox.Runner` (venv fallback + Docker primary)
- [ ] Implement library whitelist enforcement (AST import inspection)
- [ ] Implement statistical soundness check suite (all checks in §3.3)
- [ ] Build `SandboxDiagnostic` structured output format
- [ ] Build self-correction prompt templates (textbook-grounded, per estimator)
- [ ] Implement iteration counter with hard cap and escalation to researcher
- [ ] Log all sandbox iterations to Replication Blob (Phase 2)
- [ ] Support for R execution kernel (Phase 3b / future)

---

## 3.6 Review Criteria
- Does the sandbox catch hallucinated libraries before execution?
- Are econometric diagnostics run automatically, not on request?
- Is the self-correction loop grounded in textbook guidance (not just "fix the bug")?
- Are all sandbox iterations logged in the Replication Blob?