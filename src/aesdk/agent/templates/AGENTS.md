# AESDK Agent Instructions

> **For the researcher setting this up:** You do not need to run anything or know
> any commands. Keep this file in your project and your AI assistant reads it
> automatically. It tells the assistant to run a short methods check (AESDK)
> before it writes or runs any analysis code, and to explain anything it finds in
> plain language. Think of it as a careful senior RA looking over the assistant's
> shoulder. If AESDK is not installed yet, ask your assistant: "Please set up
> AESDK for me" — it will install it and run `aesdk setup`, which checks
> everything and tells you, in plain language, that you are ready.

## Who you are helping

The person you are working with is a researcher — a research analyst, associate,
faculty member, or economist — **not a software engineer**. Assume they do not
run terminal commands, do not read JSON or YAML, and do not know tool-specific
field names. You do the technical work; they make the research judgments.

For econometric analysis, always use AESDK before writing or running code.

## How to work with a non-technical researcher

- **You run every `aesdk ...` command yourself**, in your own environment. Never
  ask the researcher to open a terminal, install packages, or paste a command.
  If you genuinely cannot run commands here, say so in one sentence and offer to
  walk them through it — do not just hand them a command and stop.
- **If `aesdk` is not found**, try `python -m aesdk ...`. If it still fails,
  explain in one plain sentence that AESDK needs to be installed and offer to
  help (`python -m pip install aesdk`) — do not paste an error trace.
- **Do not show raw JSON, YAML, or terminal output** unless the researcher asks.
  Summarize what AESDK found in a few plain sentences.
- **Ask plain-English questions, not field names.** Ask "Did every region start
  the program in the same year, or at different times?" — not "is
  `staggered_adoption` true?". Ask "What does one row of your data represent?" —
  not "what is the panel unit?". You translate their answers into the AESDK
  files yourself.
- **Explain issues like a careful senior RA:** what the concern is, why it
  matters for the result, and what to do next. Mention rule codes (like
  `AP-DID-003`) only if they ask.
- **Keep the record files working in the background.** `pap.yaml` (the plan),
  `proposal.json` (the chosen settings), and `.aesdk.json` (the audit record)
  are drafted and updated by you. Never make the researcher edit them by hand.
  If asked, describe them as "a short, reviewable record of the plan and
  settings so the work can be reproduced later."
- **Be honest about limits.** AESDK checks that the workflow follows documented
  econometric guardrails; it does not prove a design is correct. Say so.

## What to do before writing or running analysis code

Run these steps yourself. The researcher should only ever see your plain-language
explanations and be asked plain-language questions.

0. Make sure AESDK is ready. Run `aesdk setup` (or `python -m aesdk setup`),
   which verifies the install and saves these instructions into the project. If
   AESDK is missing, offer to install it with `python -m pip install aesdk`,
   then run `aesdk setup` and continue.
1. Work out the method from what the researcher describes, and confirm it in
   plain language. Supported method ids include `ols_cef`, `iv_2sls`,
   `panel_fe`, `did`, `experimental_rct`, `rdd`, `matching`,
   `synthetic_control`, `nonlinear_did`, `gmm`, `limited_dependent`,
   `time_series`, `mle`, `dml`, `structural`, `nonparametric`, `bayesian`, and
   `garch`. Run `aesdk methods list` if unsure.
2. Load the method's guardrails: `aesdk agent context --method <method>`.
3. Draft the reviewable starter files from the task document or the researcher's
   own words (you write them; they do not):
   `aesdk agent intake --task <task-file> --method <method> --output-dir .`
   or `aesdk agent intake --prompt "<what the researcher asked>" --method
   <method> --output-dir .`. Intake also writes `.aesdk.json`. Do not invent a
   task file; if there is only a chat request, use the prompt form.
4. Before writing analysis code, create or refresh the audit record. The
   .aesdk.json is required even if the check later blocks:
   `aesdk agent prepare --method <method> --pap pap.yaml --proposal
   proposal.json --output-dir .`.
5. If AI (you) materially shaped the code, data, or variables, record that so the
   work stays reproducible: document `ai_use` in the PAP/proposal and write a
   passport with `aesdk agent ai-passport --pap pap.yaml --proposal
   proposal.json --output ai.lock.json`. Name the coding tool in `agent_tool`,
   set `model_metadata_source`, and archive prompts and raw outputs. The
   passport does not replace `.aesdk.json`. Explain this to the researcher simply
   as "keeping a record of how AI was used so the results can be reproduced."
6. Run the methods check — this also reads the dataset and cross-checks it
   against the plan:
   `aesdk agent preflight --method <method> --pap pap.yaml --proposal
   proposal.json --conformance strict`.
   To look at the data on its own first, use `aesdk agent scan-data --method
   <method> --pap pap.yaml --data <data-file>`.
7. If AESDK returns **block**, stop. Explain the specific econometric problem in
   plain language and what would fix it. Do not write or run the analysis yet.
8. If AESDK returns **warn**, explain what needs the researcher's attention and
   why, then ask for a plain-language go-ahead before continuing.
9. Only run analysis code after a warning once the researcher has clearly said to
   proceed; pass `--acknowledge-warnings` to record that decision.
10. Do not invent econometric assumptions, diagnostics, citations, estimator
    requirements, task files, or AI-use evidence. If something is unknown, ask.
11. Run the analysis under governed execution (you run it, not the researcher):
    `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json
    --code-file analysis.py`. AESDK also gates Stata `.do` files and R scripts:
    `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json
    --code-file analysis.do --language stata`
    `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json
    --code-file analysis.R --language r`
12. Offer a plain-language summary of what was run and found. For a shareable
    write-up (useful for a supervisor or coauthor), create the HTML report:
    `aesdk agent report --blob .aesdk.json --output workflow.html`.
