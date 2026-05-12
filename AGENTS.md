# AGENTS.md

## AESDK Rule For AI Research Agents

This repository contains AESDK, a guardrail system for AI-assisted econometric analysis. If you are an AI agent working in this repo, assume the user is doing empirical economics research and may not be a software developer.

Your job is to help the research workflow stay disciplined.

## Before Writing Analysis Code

Before writing econometric code, do this:

1. Identify the method: `ols_cef`, `iv_2sls`, `panel_fe`, `did`, or `rdd`.
2. Load AESDK context:

```bash
aesdk agent context --method <method>
```

3. If a PAP and proposal exist, run preflight:

```bash
aesdk agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict
```

4. If AESDK returns `block`, stop. Explain the issue in plain research language.
5. If AESDK returns `warn`, explain what needs researcher acknowledgement.
6. Only write or run analysis code after AESDK passes or the researcher explicitly documents an override.

## Python API

Prefer the top-level API in automated workflows:

```python
import aesdk as ae

gate = ae.preflight(method="did", pap_path="pap.yaml", proposal="proposal.json")
if gate.blocked:
    raise RuntimeError(gate.explain())
```

Use `ae.run_analysis(...)` when executing code so AESDK records the run.

## Research Principles

- Do not invent econometric assumptions.
- Do not invent citations.
- Do not silently change the estimator, standard errors, clustering level, sample, or covariates.
- Treat the PAP as binding unless the researcher documents a change.
- Explain violations in ordinary language that an RA or professor can review.
- Use method protocols and source locators from `src/aesdk/knowledge/`.

## Textbook Sources

Local textbook files may exist under `tools/`, but public package artifacts should only contain compact paraphrased protocols, source metadata, and rules. Do not copy long textbook passages into outputs.

## Useful Checks

```bash
python -m pytest
aesdk methods validate
aesdk agent context --method did
aesdk agent preflight --method did --pap docs/examples/simulated_did_training_policy/pap.yaml --proposal docs/examples/simulated_did_training_policy/proposal_pass.json
```
