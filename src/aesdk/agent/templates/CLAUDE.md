# AESDK Instructions For Claude

When asked to write econometric analysis code, use AESDK first.

- Load method guidance with `aesdk agent context --method <method>`.
- Supported method ids include `ols_cef`, `iv_2sls`, `panel_fe`, `did`, `experimental_rct`, `rdd`, `matching`, `synthetic_control`, `nonlinear_did`, `gmm`, `limited_dependent`, and `time_series`; use `aesdk methods list` if unsure.
- If a task file exists but `pap.yaml` and `proposal.json` do not, draft reviewable starter files with `aesdk agent intake --task <task-file> --method <method> --output-dir .`.
- If AI materially shaped code, classifications, extracted data, or variables, document `ai_use` and write `ai.lock.json` with `aesdk agent ai-passport --pap pap.yaml --proposal proposal.json --output ai.lock.json`.
- For AI-written analysis code, declare `ai_use.languages` and list the final reviewed `.py`, `.R`, or `.do` scripts in `ai_use.code_files`; the declared languages must match the archived code extensions.
- Record coding agents/editors such as Codex, Claude Code, VS Code, GitHub Copilot, or OpenCode in `ai_use.agent_tool`, not `ai_use.model`. Always set `model_metadata_source` to show where the model id came from. If the underlying model id is unavailable, set `model_metadata_source: agent_unavailable`, name the tool in `agent_tool`, explain why, run the matching runtime snapshot command (`aesdk agent codex-runtime`, `aesdk agent claude-runtime`, or `aesdk agent copilot-runtime`), and list it in `runtime_metadata_files`.
- If the researcher asks follow-up questions or corrects the agent, record `human_in_loop: true` and archive the transcript in `human_interaction_files`; use `aesdk agent interaction-log` when creating that transcript.
- If a human edits AI-generated code, record `human_modified_code: true`, archive the AI draft in `ai_code_draft_files`, and use `aesdk agent review-diff --ai-code <draft> --final-code <final> --output review/human_code_diff.patch` or another change note in `human_intervention_files`.
- Do not set `human_reviewed: true` unless a researcher review is documented with `review_status` and existing `review_files`.
- Run preflight with `aesdk agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict`.
- A `block` result is a hard stop.
- A `warn` result requires researcher review.
- Do not run analysis code on `warn` unless the researcher explicitly acknowledges the warning; use `--acknowledge-warnings` only after that acknowledgement is documented.
- Do not invent assumptions, diagnostics, citations, or estimator requirements.
- Do not make replication depend on a live AI model; archive prompts, raw AI outputs, and AI-derived data used downstream.
- Explain AESDK results in plain language for economics RAs and faculty.
- Use governed execution for Python, Stata `.do`, and R scripts with `aesdk agent run`.
- Use `aesdk agent report --blob .aesdk.json --output workflow.html` when the researcher needs a visual run summary.
