# Phase 1 — Protocol Layer (`aesdk.protocol`)

**Goal:** Build the enforcement core. The SDK cannot run any analysis without a valid
Pre-Analysis Plan. Phase 1 defines the PAP schema, the state machine, and the
textbook-grounded validator.

**Target MVP:** Researcher can initialize a project, write a PAP, and have the SDK
accept or block agent model proposals.

---

## 1.1 Pre-Analysis Plan (PAP) Schema

The canonical PAP is a `.yaml` file with mandatory and optional fields.
The SDK will refuse to initialize without all mandatory fields.

```yaml
# my_project.pap.yaml — Canonical Schema

project:
  id: "proj_001"
  title: "Effect of Minimum Wage on Employment (State Panel)"
  author: "A. Researcher"
  date_registered: "2026-01-15"
  version: "1.0.0"

data:
  source: "BLS_CPS_StatePanel_2000_2020.csv"
  unit: "state"
  time: "year"
  structure: "panel"  # cross-section | panel | time-series | pooled

identification:
  strategy: "DiD"  # OLS | IV | DiD | RDD | Matching | SynthControl | EventStudy
  treatment_variable: "min_wage_increase"
  outcome_variable: "log_employment_rate"
  covariates:
    mandatory: ["state_fe", "year_fe", "log_gdp_per_capita"]
    optional: ["unemployment_rate_lag1", "log_population"]
  fixed_effects: ["state", "year"]
  clustering: "state"
  expected_sign: "negative"  # null | positive | negative

iv_block:  # Only required if strategy == "IV"
  instruments: []
  first_stage_f_threshold: 10  # Staiger-Stock rule (MHE Ch. 4)

did_block:  # Only required if strategy == "DiD"
  parallel_trends_test: true
  event_study_leads_lags: [-3, -2, -1, 0, 1, 2, 3]
  staggered_adoption: false

robustness:
  specification_curve: true
  vary_controls: true
  vary_clustering: ["state", "state-year"]
  vary_functional_form: ["linear", "log-linear"]
```

---

## 1.2 State Machine — Agent Workflow

```
[INIT] → PAP Loaded & Validated
   ↓
[PROPOSE] → Agent proposes model/code
   ↓
[VALIDATE] → SDK checks against PAP + Textbook Rules
   ↓         ↙             ↘
[PASS]     [OVERRIDE?]    [BLOCK]
   ↓          ↓               ↓
[EXECUTE]  [Log Override]   [Error + Guidance]
   ↓
[TRACE] → Replication Blob Updated
   ↓
[NEXT ACTION]
```

Override requires a structured log entry: the agent cannot self-approve overrides—they must
be surfaced to the researcher for acknowledgment.

---

## 1.3 Key Modules

### `aesdk.Project`
```python
# Conceptual API
import aesdk

research = aesdk.Project(pap_path="./my_project.pap.yaml")
# Loads PAP, validates schema, initializes rule registry, opens trace log

suggestion = agent.propose_model("Run a DiD with state and year FE")

result = research.validate(suggestion)
# Returns: ValidationResult(status='pass'|'block'|'warn', rules_triggered=[], guidance="")

if result.status == "pass":
    research.execute(suggestion)
elif result.status == "warn":
    research.execute(suggestion, acknowledge_warnings=True)
else:
    print(result.guidance)
    # "Error [W-PANEL-001]: Panel DiD requires cluster SE at state level. 
    #  Reference: Wooldridge (2010), Ch. 7.8."
```

### `aesdk.protocol.Validator`
- Loads governance rules from `aesdk/governance/rules/*.rules.yaml`
- Evaluates each rule against the proposed model + PAP context
- Generates `ValidationResult` with severity-ranked findings

### `aesdk.protocol.OverrideLog`
- Timestamped JSON entry per override
- Fields: `rule_id`, `justification`, `researcher_acknowledged`, `agent_reasoning`, `timestamp`
- Appended to Replication Blob (Phase 2)

---

## 1.4 Task Checklist

- [ ] Define and publish canonical PAP YAML schema with JSON Schema validation
- [ ] Implement `aesdk.Project` class (init, validate, execute, override)
- [ ] Implement `aesdk.protocol.Validator` with rule loading
- [ ] Author initial rule files: `wooldridge_ols.rules.yaml`, `wooldridge_panel.rules.yaml`,
      `angrist_pischke_iv.rules.yaml`, `angrist_pischke_did.rules.yaml`
- [ ] Implement state machine with explicit state transitions
- [ ] CLI: `aesdk init --pap my_project.pap.yaml`
- [ ] Unit tests: valid PAP pass, invalid PAP block, rule trigger scenarios
- [ ] PAP template generator: `aesdk new-pap --strategy DiD`

---

## 1.5 Review Criteria
- Does the SDK block execution without a valid PAP?
- Are errors attributed to specific textbook rules with chapter references?
- Is the override mechanism researcher-gated (not auto-approved by agent)?
- Can rule files be added without modifying core SDK code?