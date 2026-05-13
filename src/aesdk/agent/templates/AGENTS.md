# AESDK Agent Instructions

For econometric analysis, always use AESDK before writing or running code.

1. Identify the method. Supported method ids include `ols_cef`, `iv_2sls`, `panel_fe`, `did`, `experimental_rct`, `rdd`, `matching`, `synthetic_control`, `nonlinear_did`, `gmm`, `limited_dependent`, and `time_series`. Use `aesdk methods list` if unsure.
2. Load context:
   `aesdk agent context --method <method>`
3. If the task starts from a folder or assignment document and `pap.yaml` / `proposal.json` do not exist, create reviewable starter files:
   `aesdk agent intake --task <task-file> --method <method> --output-dir .`
4. Run preflight:
   `aesdk agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict`
5. If AESDK returns `block`, stop and explain the issue in plain research language.
6. If AESDK returns `warn`, explain what needs researcher review.
7. Do not run analysis code on `warn` unless the researcher explicitly acknowledges the warning; pass `--acknowledge-warnings` only after that acknowledgement is documented.
8. Do not invent econometric assumptions, diagnostics, citations, or estimator requirements.
9. Use governed execution when running analysis code:
   `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json --code-file analysis.py`
   AESDK also gates Stata `.do` files and R scripts:
   `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json --code-file analysis.do --language stata`
   `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json --code-file analysis.R --language r`
10. When a run should be reviewed visually, write an HTML workflow report:
   `aesdk agent report --blob .aesdk.json --output workflow.html`
