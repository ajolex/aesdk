# CLAUDE.md

## AESDK Requirement

For econometric analysis code, Claude must use AESDK before writing or running code.

1. Identify the method: `ols_cef`, `iv_2sls`, `panel_fe`, `did`, or `rdd`.
2. Load context with `aesdk agent context --method <method>` or `import aesdk as ae; ae.agent_context("<method>")`.
3. Run preflight with `aesdk agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict`.
4. If AESDK returns `block`, stop and explain the violated assumptions.
5. Use `ae.run_analysis(...)` or `aesdk agent run ...` for governed execution.
6. Do not invent econometric assumptions, diagnostics, citations, or estimator requirements.
