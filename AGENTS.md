# AGENTS.md

## AESDK Rule For AI Research Agents

This repository contains AESDK, a guardrail system for AI-assisted econometric analysis. If you are an AI agent working in this repo, assume the user is doing empirical economics research and may not be a software developer.

Your job is to help the research workflow stay disciplined.

## Before Writing Analysis Code

Before writing econometric code, do this:

1. Identify the method. Supported method ids include `ols_cef`, `iv_2sls`, `panel_fe`, `did`, `rdd`, `matching`, `synthetic_control`, `nonlinear_did`, `gmm`, `limited_dependent`, and `time_series`. Use `aesdk methods list` if unsure.
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
6. Only write or run analysis code after AESDK passes, or after the researcher explicitly documents an override or warning acknowledgement.

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
- ## Context Reset & Memory Protocol
To prevent token bloat, `AI_MEMORY.md` holds long-term context.
- **Trigger:** When user says "Save memory and close" or `/memorize`.
- **Action 1 (Append):** Summarize the fix/feature using the exact format below. Append to the bottom of `AI_MEMORY.md`.
  ### [Date] - [Feature | Bug] - [Short Title]
  - **Issue:** [1-sentence description]
  - **Resolution:** [How it was built or fixed]
  - **Implications:** [Files changed / logic altered]
  - **Difficulty:** [Easy/Medium/Hard] - [Why]
  - **Lessons:** [Explicit guardrail for future agents]
- **Action 2 (Auto-Prune):** If `AI_MEMORY.md` exceeds ~150 lines after appending, you MUST prune it:
  1. Read entries older than 2 weeks.
  2. Extract their "Lessons" and merge them into a permanent `## Core Architecture Directives` bulleted list at the very top of the file.
  3. Delete the granular log entries for those older items.
  4. Keep the 5 most recent granular logs intact.
- **Commit:** Save and commit the memory update.
