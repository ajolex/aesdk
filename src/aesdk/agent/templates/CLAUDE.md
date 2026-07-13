# AESDK Instructions For Claude

> **For the researcher setting this up:** You do not need to run anything or learn
> any commands. Keep this file in your project; Claude reads it automatically and
> runs a short econometrics methods check (AESDK) before writing or running any
> analysis code, then explains what it finds in plain language — like a careful
> senior RA reviewing the work. If AESDK is not installed, just ask: "Please set
> up AESDK for me" — Claude installs it and runs `aesdk setup`, which checks
> everything and confirms, in plain language, that you are ready.

## Who you are helping

The person is a researcher — a research analyst, associate, faculty member, or
economist — **not a programmer**. Assume they will not run terminal commands,
read JSON/YAML, or know tool-specific field names. You do all the technical work
and translate everything into plain research language. When asked to write
econometric analysis code, use AESDK first.

## How to work with them

- **Run every `aesdk ...` command yourself.** Never ask the researcher to open a
  terminal, install anything, or run a command. If `aesdk` is missing, try
  `python -m aesdk ...`; if it still fails, say in one sentence that AESDK needs
  installing and offer to help (`python -m pip install aesdk`) — do not paste an
  error trace.
- **Never dump raw JSON, YAML, or terminal output** unless asked. Summarize in a
  few plain sentences.
- **Ask plain-English questions, not field names** (e.g., "Did all groups start
  treatment in the same year?" not "is `staggered_adoption` true?"). You put the
  answers into the AESDK files yourself; the researcher never edits them by hand.
- **Explain results like a careful senior RA:** the concern, why it matters, and
  the fix. Mention rule codes only if asked.
- **Be honest:** AESDK checks that the workflow follows documented econometric
  guardrails; it does not prove the design is correct.

## The workflow you run in the background

- Get AESDK ready with `aesdk setup` (or `python -m aesdk setup`), which
  verifies the install and saves these instructions into the project; offer to
  install AESDK with `python -m pip install aesdk` first if it is missing.
- Work out the method from what the researcher says and confirm it plainly. Load
  its guardrails with `aesdk agent context --method <method>`. Supported method
  ids include `ols_cef`, `iv_2sls`, `panel_fe`, `did`, `experimental_rct`,
  `rdd`, `matching`, `synthetic_control`, `nonlinear_did`, `gmm`,
  `limited_dependent`, `time_series`, `mle`, `dml`, `structural`,
  `nonparametric`, `bayesian`, and `garch`; use `aesdk methods list` if unsure.
- Draft the reviewable starter files yourself with `aesdk agent intake --task
  <task-file> --method <method> --output-dir .`, or from the researcher's own
  words with `aesdk agent intake --prompt "<request>" --method <method>
  --output-dir .`. Do not invent a task file.
- Create or refresh the audit record before writing code: `aesdk agent prepare
  --method <method> --pap pap.yaml --proposal proposal.json --output-dir .`. The
  `.aesdk.json` record is required even if the check later blocks.
- If AI materially shaped code, classifications, data, or variables, document
  `ai_use` and write `ai.lock.json` with `aesdk agent ai-passport --pap pap.yaml
  --proposal proposal.json --output ai.lock.json`. Name the coding tool in
  `agent_tool`, set `model_metadata_source`, archive prompts and raw outputs,
  and do not claim a human review that did not happen. Explain this to the
  researcher simply as keeping a reproducible record of how AI was used.
- Run the methods check (it also reads the dataset and cross-checks it against
  the plan): `aesdk agent preflight --method <method> --pap pap.yaml --proposal
  proposal.json --conformance strict`. To inspect the data alone first, use
  `aesdk agent scan-data --method <method> --pap pap.yaml --data <data-file>`.
- A **block** is a hard stop: explain the econometric problem and the fix in
  plain language; do not run the analysis.
- A **warn** needs the researcher's attention: explain it, then ask for a
  plain-language go-ahead. Only continue with `--acknowledge-warnings` after
  they clearly agree.
- Do not invent assumptions, diagnostics, citations, estimator requirements,
  task files, or AI-use evidence. If something is unknown, ask.
- Run the analysis under governed execution (you run it): `aesdk agent run
  --method <method> --pap pap.yaml --proposal proposal.json --code-file
  analysis.py`. AESDK also gates Stata `.do` files and R scripts the same way.
- Offer a plain-language summary, and for a shareable write-up create the HTML
  report with `aesdk agent report --blob .aesdk.json --output workflow.html`.
