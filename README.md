# Agentic Econometrics SDK (AESDK)

AESDK is an SDK for econometric analysis in the same sense that a software SDK is a packaged development environment: it gives agents and analysts reusable tools, validated protocols, documentation, examples, and policy checks so they do not have to reinvent standard methods from scratch.

The motivation is practical. Econometric analysis is not a blank creative exercise; most applied work uses established identification strategies, estimators, diagnostics, and inference procedures described in textbooks and the causal inference literature. In an AI-assisted research workflow, LLMs and agents need durable econometric guardrails because they were not trained specifically to perform applied econometrics with the discipline expected by peer review, replication, or regulation.

AESDK turns textbook econometrics into machine-checkable scaffolding:

- method protocols that state assumptions, required inputs, diagnostics, estimator choices, and failure modes
- governance rules that pass, warn, or block proposed analysis steps
- pre-analysis plan validation before execution
- auditable replication records and replay
- citation and source integrity checks so agents cannot invent authority

## Key capabilities

- Textbook-backed method registry for OLS/CEF regression, IV/2SLS, panel fixed effects, and DiD workflows.
- PAP required before execution.
- Rules engine with pass/warn/block outcomes.
- Conformance levels: `basic`, `strict`, `regulated`.
- Context profiles: `research`, `production`, `regulated`.
- Governance passport metadata embedded in blob.
- Full replay execution for recorded execute events.
- Signed audit artifacts:
  - HMAC signing/verification
  - KMS-HTTP signing/verification hooks
- Remote attestation hooks:
  - no-op local provider
  - HTTP endpoint provider

## Quickstart

```bash
pip install -e .
aesdk init --pap docs/examples/did_min_wage/pap.yaml --context production --conformance strict --policy-version 1.2.0
aesdk validate --pap docs/examples/did_min_wage/pap.yaml --proposal docs/examples/did_min_wage/proposal_blocked.json --conformance strict
aesdk reproduce --blob docs/examples/did_min_wage/.aesdk.json --replay
```

## Method protocols

AESDK ships durable method context extracted and paraphrased from local textbook sources, starting with:

- `tools/Wooldridge.pdf`
- `tools/MostlyHarmlessEconometrics.pdf`

The source PDFs remain local references. The package stores compact, non-verbatim method protocols under `src/aesdk/knowledge/` so agents can use the guidance permanently without copying whole books into prompts.

```bash
aesdk methods list
aesdk methods show did
aesdk methods show iv_2sls --format yaml
aesdk methods sources did --format yaml
aesdk methods validate
aesdk sources list
```

## Agent workflows

AESDK is designed to be called by AI coding agents before they write or run econometric analysis code.

```python
import aesdk as ae

gate = ae.preflight(
    method="did",
    pap_path="docs/examples/simulated_did_training_policy/pap.yaml",
    proposal="docs/examples/simulated_did_training_policy/proposal_pass.json",
    conformance="strict",
)

if gate.blocked:
    raise RuntimeError(gate.explain())

print(gate.agent_context_markdown())
```

Agent-facing CLI helpers mirror the Python API:

```bash
aesdk agent context --method did
aesdk agent preflight --method did --pap pap.yaml --proposal proposal.json --conformance strict
aesdk agent draft-pap --method did --goal "Estimate policy effects" --data panel.csv --outcome y --treatment treated --unit state --time year --output pap.yaml
aesdk agent run --method did --pap pap.yaml --proposal proposal.json --code-file analysis.py
aesdk agent template --target AGENTS.md
aesdk agent template --target CLAUDE.md
```

The intended `AGENTS.md`/`CLAUDE.md` rule is simple: load AESDK context before coding, run AESDK preflight before execution, and stop on `block`.

## Analysis layer

The `aesdk.curve` package provides real estimation helpers for common SDK-backed workflows:

- DiD via OLS with registered covariates, fixed effects, and robust or clustered inference
- panel fixed effects via entity/time dummies and clustered inference
- plugin estimator hooks for custom methods

```python
from aesdk.curve.runner import CurveRunner

runner = CurveRunner("docs/examples/simulated_did_training_policy/training_policy_panel.csv")
result = runner.execute_spec(
    "did",
    {
        "outcome": "employment_rate",
        "treatment": "policy_active",
        "time": "year",
        "covariates": ["median_income", "unemployment_rate"],
        "fixed_effects": ["state", "year"],
        "cluster": "state",
    },
)
print(result.coefficients["policy_active"])
```

## Signed audits

```bash
aesdk audit sign --blob docs/examples/regulated_profile/.aesdk.json --mode hmac --secret your-secret --key-id local
aesdk audit verify-signature --blob docs/examples/regulated_profile/.aesdk.json --signature docs/examples/regulated_profile/.aesdk.json.sig.json --secret your-secret
```

## KMS-HTTP signing integration

```bash
aesdk audit sign --blob docs/examples/regulated_profile/.aesdk.json --mode kms-http --kms-endpoint https://kms.example --key-id key-1 --kms-token TOKEN
aesdk audit verify-signature --blob docs/examples/regulated_profile/.aesdk.json --signature docs/examples/regulated_profile/.aesdk.json.sig.json --kms-endpoint https://kms.example --kms-token TOKEN
```

## Docs

- Functionality: `docs/PROJECT_FUNCTIONALITY.md`
- Security: `SECURITY.md`
- Release checklist: `docs/RELEASE_CHECKLIST.md`

## Current implementation status

Implemented:

- PAP schema validation and conformance-aware rule evaluation
- rulepacks for panel inference, DiD, and citation integrity
- replication blob creation, integrity verification, replay, and audit signing
- sandbox execution allowlist
- specification curve scaffolding
- LLM adapter scaffolding
- permanent method protocol registry in `src/aesdk/knowledge/`

Next:

- expand textbook-derived rulepacks beyond the initial OLS/IV/panel/DiD protocols
- add source-page anchors and extraction QA for each rule
- expose protocol recommendations during `aesdk validate`
- add richer PAP blocks for RDD, matching, synthetic control, quantile regression, and DML
- harden sandbox execution and signed replay reports for regulated use
