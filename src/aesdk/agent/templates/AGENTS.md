# AESDK Agent Instructions

For econometric analysis, always use AESDK before writing or running code.

0. Make sure AESDK is callable. Run `aesdk agent doctor`; if `aesdk` is missing, use `python -m aesdk agent doctor` after installing with `python -m pip install aesdk`.
1. Identify the method. Supported method ids include `ols_cef`, `iv_2sls`, `panel_fe`, `did`, `experimental_rct`, `rdd`, `matching`, `synthetic_control`, `nonlinear_did`, `gmm`, `limited_dependent`, and `time_series`. Use `aesdk methods list` or `python -m aesdk methods list` if unsure.
2. Load context:
   `aesdk agent context --method <method>`
3. If the task starts from a folder or assignment document and `pap.yaml` / `proposal.json` do not exist, create reviewable starter files from the document. Intake also writes `.aesdk.json` by default:
   `aesdk agent intake --task <task-file> --method <method> --output-dir .`
   If there is no task file and the instructions are only in the chat/prompt, use:
   `aesdk agent intake --prompt "<research task>" --method <method> --output-dir .`
4. Before writing analysis code, create or refresh the AESDK replication blob. .aesdk.json is required, even when analysis later blocks:
   `aesdk agent prepare --prompt "<research task>" --method <method> --output-dir .`
   or, if `pap.yaml` and `proposal.json` already exist:
   `aesdk agent prepare --method <method> --pap pap.yaml --proposal proposal.json --output-dir .`
5. If AI materially shaped code, classifications, extracted data, or variables, document `ai_use` in the PAP/proposal and write a passport:
   `aesdk agent ai-passport --pap pap.yaml --proposal proposal.json --output ai.lock.json`
   The passport alone is not a replication blob; the workflow must also contain `.aesdk.json` from `aesdk agent prepare` or `aesdk agent run`.
   For AI-written analysis code, `ai_use` must declare `languages` and list the final reviewed `.py`, `.R`, or `.do` scripts in `code_files`; the declared languages must match the archived code extensions.
   Record coding agents/editors such as Codex, Claude Code, VS Code, GitHub Copilot, or OpenCode in `agent_tool`, not `model`. Always set `model_metadata_source` to show where the model id came from. If the underlying model id is unavailable, set `model_metadata_source: agent_unavailable`, name the tool in `agent_tool`, explain why, run `aesdk agent codex-runtime`, `aesdk agent claude-runtime`, or `aesdk agent copilot-runtime` as appropriate, and list the file in `runtime_metadata_files`. If the researcher asks follow-up questions or corrects the agent, record `human_in_loop: true` and archive the transcript in `human_interaction_files`; use `aesdk agent interaction-log` when creating that transcript. If a human edits AI-generated code, record `human_modified_code: true`, archive the AI draft in `ai_code_draft_files`, and use `aesdk agent review-diff --ai-code <draft> --final-code <final> --output review/human_code_diff.patch` or another change note in `human_intervention_files`. Do not set `human_reviewed: true` unless a researcher review is documented with `review_status` and existing `review_files`.
6. Run preflight:
   `aesdk agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict`
7. If AESDK returns `block`, stop and explain the issue in plain research language.
8. If AESDK returns `warn`, explain what needs researcher review.
9. Do not run analysis code on `warn` unless the researcher explicitly acknowledges the warning; pass `--acknowledge-warnings` only after that acknowledgement is documented.
10. Do not invent econometric assumptions, diagnostics, citations, estimator requirements, task files, or AI-use evidence.
11. Use governed execution when running analysis code:
   `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json --code-file analysis.py`
   AESDK also gates Stata `.do` files and R scripts:
   `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json --code-file analysis.do --language stata`
   `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json --code-file analysis.R --language r`
12. When a run should be reviewed visually, write an HTML workflow report:
   `aesdk agent report --blob .aesdk.json --output workflow.html`
