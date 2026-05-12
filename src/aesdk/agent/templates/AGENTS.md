# AESDK Agent Instructions

For econometric analysis, always use AESDK before writing or running code.

1. Identify the method: `ols_cef`, `iv_2sls`, `panel_fe`, `did`, or `rdd`.
2. Load context before coding:
   `python -m aesdk.cli.main agent context --method <method>`
3. Run preflight before execution:
   `python -m aesdk.cli.main agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict`
4. If AESDK returns `status=block`, stop. Explain the violated assumptions and do not write execution code.
5. If AESDK returns `status=warn`, document the warning and require researcher acknowledgement.
6. Never invent econometric assumptions, diagnostics, citations, or estimator requirements.
