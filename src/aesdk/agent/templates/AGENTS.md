# AESDK Agent Instructions

For econometric analysis, always use AESDK before writing or running code.

1. Identify the method. Supported method ids include `ols_cef`, `iv_2sls`, `panel_fe`, `did`, `experimental_rct`, `rdd`, `matching`, `synthetic_control`, `nonlinear_did`, `gmm`, `limited_dependent`, and `time_series`. Use `aesdk methods list` if unsure.
2. Load context:
   `aesdk agent context --method <method>`
3. If the task starts from a folder or assignment document and `pap.yaml` / `proposal.json` do not exist, create reviewable starter files:
   `aesdk agent intake --task <task-file> --method <method> --output-dir .`
4. If AI materially shaped code, classifications, extracted data, or variables, document `ai_use` in the PAP/proposal and write a passport:
   `aesdk agent ai-passport --pap pap.yaml --proposal proposal.json --output ai.lock.json`
   For AI-written analysis code, `ai_use` must declare `languages` and list the final reviewed `.py`, `.R`, or `.do` scripts in `code_files`; the declared languages must match the archived code extensions.
   Record coding agents/editors such as Codex, Claude Code, VS Code, GitHub Copilot, or OpenCode in `agent_tool`, not `model`. Always set `model_metadata_source` to show where the model id came from. If the underlying model id is unavailable, set `model_metadata_source: agent_unavailable`, name the tool in `agent_tool`, explain why, run `aesdk agent codex-runtime`, `aesdk agent claude-runtime`, or `aesdk agent copilot-runtime` as appropriate, and list the file in `runtime_metadata_files`. Do not set `human_reviewed: true` unless a researcher review is documented with `review_status` and existing `review_files`.
5. Run preflight:
   `aesdk agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict`
6. If AESDK returns `block`, stop and explain the issue in plain research language.
7. If AESDK returns `warn`, explain what needs researcher review.
8. Do not run analysis code on `warn` unless the researcher explicitly acknowledges the warning; pass `--acknowledge-warnings` only after that acknowledgement is documented.
9. Do not invent econometric assumptions, diagnostics, citations, estimator requirements, or AI-use evidence.
10. Use governed execution when running analysis code:
   `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json --code-file analysis.py`
   AESDK also gates Stata `.do` files and R scripts:
   `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json --code-file analysis.do --language stata`
   `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json --code-file analysis.R --language r`
11. When a run should be reviewed visually, write an HTML workflow report:
   `aesdk agent report --blob .aesdk.json --output workflow.html`
