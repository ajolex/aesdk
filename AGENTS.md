# AGENTS.md

## Purpose

AESDK is an Agentic Econometrics SDK. Treat it like a software SDK for applied econometrics: agents should use packaged protocols, rulepacks, examples, and source metadata before proposing or executing an analysis.

## Core Principle

Do not invent econometric methods, assumptions, citations, diagnostics, or estimator requirements. Use the method protocols and governance rules in this repository, then cite the registered source metadata. When the SDK does not yet cover a method, say that coverage is missing and create a narrow extension instead of improvising.

## Required Workflow For Econometric Tasks

1. Read the relevant PAP, proposal, and method protocol.
2. Identify the data structure, identification strategy, estimator, inference method, clustering level, and robustness plan.
3. Load agent context with `aesdk agent context --method <method>` before writing analysis code.
4. Validate the PAP/proposal with `aesdk agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict` before execution.
5. Prefer `import aesdk as ae` and the top-level functions `ae.agent_context`, `ae.preflight`, `ae.draft_pap`, and `ae.run_analysis` in automated workflows.
6. Validate the PAP with `aesdk validate` before execution when using the lower-level CLI.
7. Treat `block` as a hard stop. Treat `warn` as requiring researcher acknowledgement or a documented override.
8. Record execution in the replication blob when running code.
9. Verify citations for any agent-generated research text.

## Textbook Sources

The first source set is local to this repo:

- `tools/Wooldridge.pdf`
- `tools/MostlyHarmlessEconometrics.pdf`

Permanent, compact SDK context lives in:

- `src/aesdk/knowledge/sources.yaml`
- `src/aesdk/knowledge/method_protocols.yaml`
- `src/aesdk/governance/rules/*.rules.yaml`

Use these files instead of copying large textbook passages into prompts or outputs. Protocols must be paraphrased and source-linked, not long verbatim extracts.

## Development Guidance

- Keep rules small, testable, and tied to source metadata.
- Prefer adding fields to the PAP schema over hiding assumptions in prose.
- Add tests when a rule can block, warn, or change conformance behavior.
- Do not weaken an existing blocking rule without adding a clear migration note.
- If a rule uses a condition, make sure the validator context exposes every referenced field.
- Keep examples realistic enough that an applied researcher can recognize the workflow.

## Useful Commands

```bash
python -m pytest
aesdk agent context --method did
aesdk agent preflight --method did --pap pap.yaml --proposal proposal.json --conformance strict
aesdk methods list
aesdk methods show did
aesdk methods sources did --format yaml
aesdk methods validate
aesdk validate --pap docs/examples/did_min_wage/pap.yaml --proposal docs/examples/did_min_wage/proposal_blocked.json --conformance strict
```
