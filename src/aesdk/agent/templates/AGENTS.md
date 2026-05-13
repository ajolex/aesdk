# AESDK Agent Instructions

For econometric analysis, always use AESDK before writing or running code.

1. Identify the method. Supported method ids include `ols_cef`, `iv_2sls`, `panel_fe`, `did`, `rdd`, `matching`, `synthetic_control`, `nonlinear_did`, `gmm`, `limited_dependent`, and `time_series`. Use `aesdk methods list` if unsure.
2. Load context:
   `aesdk agent context --method <method>`
3. Run preflight:
   `aesdk agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict`
4. If AESDK returns `block`, stop and explain the issue in plain research language.
5. If AESDK returns `warn`, explain what needs researcher review.
6. Do not run analysis code on `warn` unless the researcher explicitly acknowledges the warning; pass `--acknowledge-warnings` only after that acknowledgement is documented.
7. Do not invent econometric assumptions, diagnostics, citations, or estimator requirements.
8. Use governed execution when running analysis code:
   `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json --code-file analysis.py`
