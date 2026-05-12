# AESDK Agent Instructions

For econometric analysis, always use AESDK before writing or running code.

1. Identify the method: `ols_cef`, `iv_2sls`, `panel_fe`, `did`, or `rdd`.
2. Load context:
   `aesdk agent context --method <method>`
3. Run preflight:
   `aesdk agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict`
4. If AESDK returns `block`, stop and explain the issue in plain research language.
5. If AESDK returns `warn`, explain what needs researcher review.
6. Do not invent econometric assumptions, diagnostics, citations, or estimator requirements.
7. Use governed execution when running analysis code:
   `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json --code-file analysis.py`
