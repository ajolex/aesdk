# AESDK Instructions For Claude

When asked to write econometric analysis code, use AESDK first.

- Load method guidance with `aesdk agent context --method <method>`.
- Supported method ids include `ols_cef`, `iv_2sls`, `panel_fe`, `did`, `experimental_rct`, `rdd`, `matching`, `synthetic_control`, `nonlinear_did`, `gmm`, `limited_dependent`, and `time_series`; use `aesdk methods list` if unsure.
- If a task file exists but `pap.yaml` and `proposal.json` do not, draft reviewable starter files with `aesdk agent intake --task <task-file> --method <method> --output-dir .`.
- If AI materially shaped code, classifications, extracted data, or variables, document `ai_use` and write `ai.lock.json` with `aesdk agent ai-passport --pap pap.yaml --proposal proposal.json --output ai.lock.json`.
- Run preflight with `aesdk agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict`.
- A `block` result is a hard stop.
- A `warn` result requires researcher review.
- Do not run analysis code on `warn` unless the researcher explicitly acknowledges the warning; use `--acknowledge-warnings` only after that acknowledgement is documented.
- Do not invent assumptions, diagnostics, citations, or estimator requirements.
- Do not make replication depend on a live AI model; archive prompts, raw AI outputs, and AI-derived data used downstream.
- Explain AESDK results in plain language for economics RAs and faculty.
- Use governed execution for Python, Stata `.do`, and R scripts with `aesdk agent run`.
- Use `aesdk agent report --blob .aesdk.json --output workflow.html` when the researcher needs a visual run summary.
