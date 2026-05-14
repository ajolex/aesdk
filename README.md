# AESDK: Econometrics Guardrails For AI-Assisted Research

AESDK helps economics research assistants, applied researchers, and faculty use AI coding tools more safely when writing econometric analysis code.

The basic problem is simple: AI agents can write Python, R, or Stata-like analysis code quickly, but they can also choose the wrong estimator, skip required diagnostics, use the wrong standard errors, or cite methods loosely. AESDK gives the agent a checklist grounded in econometrics before it writes or runs code.

Think of AESDK as a research-methods preflight:

- What design is this? OLS, IV, DiD, panel fixed effects, RDD?
- What assumptions must be stated?
- What diagnostics should be planned?
- What standard errors or clustering choices are required?
- Should the proposed analysis be allowed to run?
- Can we leave behind a reproducible audit trail?

AESDK is not a replacement for judgment, supervision, or peer review. It is a guardrail that makes AI-assisted analysis less ad hoc.

## Who This Is For

AESDK is designed for:

- economics RAs using AI agents to draft analysis code
- professors supervising empirical projects
- applied researchers who want pre-analysis discipline in AI-assisted workflows
- teams that need reproducible, auditable research pipelines

You do not need to be a software engineer to benefit from it. The intended workflow is: install AESDK once, add a short instruction to `AGENTS.md` or `CLAUDE.md`, and make the AI agent call AESDK before it writes analysis code.

## What AESDK Does

AESDK currently provides:

- method guidance for common econometric workflows, including OLS/CEF, IV/2SLS, panel fixed effects, DiD, randomized controlled trials/experimental methods, RDD, matching, synthetic control, nonlinear DiD, GMM, limited dependent variable models, and time series
- pre-analysis plan checks
- proposal validation with `pass`, `warn`, or `block`
- AI-agent context packets that explain the relevant assumptions and diagnostics
- governed execution that refuses to run blocked analysis code
- governed execution for Python scripts, Stata `.do` files, and R scripts
- reproducibility records through an `.aesdk.json` audit file
- task-folder intake helpers that draft a reviewable `pap.yaml` and `proposal.json`
- HTML workflow reports that supervisors can inspect without reading raw JSON
- AI Replicability Passports for archived prompts, raw outputs, model metadata, AI-generated code, and AI-derived variables
- replay checks for recorded execution
- enforced online citation/source integrity checks for agent-generated research text

The method guidance is compact and paraphrased. It is meant to guide agents, not to redistribute textbooks.

## A Typical RA Workflow

Suppose an RA asks an AI agent:

> Estimate whether a state-level job-training subsidy affected county employment using panel data.

Without AESDK, the agent may immediately write a regression. With AESDK, the agent first runs a preflight check.

```bash
aesdk agent context --method did
aesdk agent preflight --method did --pap pap.yaml --proposal proposal.json --conformance strict
```

If the proposed analysis uses panel DiD with non-clustered standard errors, AESDK blocks it before code runs. If the proposal is acceptable, the agent can proceed.

## Install

For local development from this repository:

```bash
pip install -e .
```

After a public release:

```bash
pip install aesdk
```

## Use AESDK From Python

AI agents can use the top-level Python API:

```python
import aesdk as ae

intake = ae.intake_task(
    task_path="Stata_Task.pdf",
    method="did",
    output_dir=".",
    outcome="employment",
    treatment="treated",
    unit="county",
    time="year",
)

gate = ae.preflight(
    method="did",
    pap_path=intake.pap_path,
    proposal=intake.proposal_path,
    conformance="strict",
)

if gate.blocked:
    raise RuntimeError(gate.explain())

run = ae.run_analysis(
    method="did",
    pap_path=intake.pap_path,
    proposal=intake.proposal_path,
    code_path="analysis.do",
    blob_path=".aesdk.json",
    timeout_seconds=300,
)

report_path = ae.write_workflow_report(blob_path=run.blob_path, output_path="workflow.html")
```

The important rule is: if `gate.blocked` is true, the agent should stop and explain why. Drafted intake files still need researcher review before they are treated as binding.

## Use AESDK From The Command Line

These commands are useful in an AI-agent workflow:

```bash
aesdk agent context --method did
aesdk agent context --method did --depth full
aesdk agent preflight --method did --pap pap.yaml --proposal proposal.json --conformance strict
aesdk agent draft-pap --method did --goal "Estimate policy effects" --data panel.csv --outcome y --treatment treated --unit state --time year --output pap.yaml
aesdk agent intake --task Stata_Task.pdf --method did --output-dir .
aesdk agent ai-passport --pap pap.yaml --proposal proposal.json --output ai.lock.json
aesdk agent run --method did --pap pap.yaml --proposal proposal.json --code-file analysis.py
aesdk agent run --method did --pap pap.yaml --proposal proposal.json --code-file analysis.do --language stata
aesdk agent run --method did --pap pap.yaml --proposal proposal.json --code-file analysis.R --language r
aesdk agent report --blob .aesdk.json --output workflow.html
```

You can also print ready-to-use agent instructions:

```bash
aesdk agent template --target AGENTS.md
aesdk agent template --target CLAUDE.md
```

## Add This To AGENTS.md Or CLAUDE.md

For most users, the most useful setup is to tell the AI agent:

```text
Before writing econometric analysis code, use AESDK.
Load method context with `aesdk agent context --method <method>`.
Run intake when starting from a task document: `aesdk agent intake --task <task.pdf> --output-dir .`.
If AI materially shaped the analysis, document `ai_use` and write `ai.lock.json` with `aesdk agent ai-passport --pap pap.yaml --proposal proposal.json`.
Run preflight with `aesdk agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict`.
If AESDK returns block, stop and explain the violated assumptions.
Do not invent econometric assumptions, diagnostics, citations, or estimator requirements.
```

This keeps AESDK in the background as part of the automated workflow.

## Worked Example

The repository includes a simulated DiD example:

```bash
python docs/examples/simulated_did_training_policy/generate_data.py
aesdk agent preflight --method did --pap docs/examples/simulated_did_training_policy/pap.yaml --proposal docs/examples/simulated_did_training_policy/proposal_pass.json --conformance strict
aesdk agent run --method did --pap docs/examples/simulated_did_training_policy/pap.yaml --proposal docs/examples/simulated_did_training_policy/proposal_pass.json --code-file docs/examples/simulated_did_training_policy/exec_code.py --blob docs/examples/simulated_did_training_policy/.aesdk.json
aesdk agent report --blob docs/examples/simulated_did_training_policy/.aesdk.json --output docs/examples/simulated_did_training_policy/workflow.html
```

The same example intentionally includes a bad proposal:

```bash
aesdk agent preflight --method did --pap docs/examples/simulated_did_training_policy/pap.yaml --proposal docs/examples/simulated_did_training_policy/proposal_blocked.json --conformance strict
```

AESDK blocks it because the proposal uses an invalid inference choice for panel DiD.

## Stata And R Support

AESDK can gate and run Stata `.do` files and R scripts after preflight passes:

```bash
aesdk agent run --method did --pap pap.yaml --proposal proposal.json --code-file analysis.do
aesdk agent run --method did --pap pap.yaml --proposal proposal.json --code-file analysis.R
```

The language is inferred from `.do`, `.R`, or `.r`, or can be set with `--language stata` or `--language r`. Longer jobs can use `--timeout-seconds`. AESDK runs Stata in batch mode through a local licensed Stata installation and runs R through `Rscript`. If the runtimes are not on `PATH`, set:

```bash
AESDK_STATA="C:\Program Files\Stata18\StataMP-64.exe"
AESDK_R="C:\Program Files\R\R-4.5.0\bin\Rscript.exe"
```

Python, Stata, and R execution record `language=...` in the `.aesdk.json` audit file. When code does not already declare a seed, AESDK uses a date seed (`yyyymmdd`) and records it in the execution artifacts: Python seeds `random` and NumPy when available, Stata prepends `set seed yyyymmdd`, and R prepends `set.seed(yyyymmdd)`. If the researcher already declared a seed, AESDK preserves it and records that it was not injected. Stata logs are captured as execution artifacts when available, so the HTML workflow report can point reviewers to the actual run log. The Stata guard blocks shell escapes and destructive commands such as `shell`, `!`, `erase`, `rm`, and package/network installs. The R guard blocks shell calls, file deletion helpers, package installs, network `source`/`url` helpers, and `library()`/`require()` calls outside the AESDK R package allowlist. Python and R recipe packages are checked against the sandbox allowlists, so bundled recipes and governed execution stay aligned.

## AI Replicability Passport

AESDK treats AI use as acceptable only when the work can be reproduced from archived artifacts without needing the same live AI model later. Add an `ai_use` block to the PAP or proposal when AI materially shapes the work:

```yaml
ai_use:
  used: true
  role: code_generation
  languages: ["stata"]
  provider: Anthropic
  model: claude-sonnet-4.6
  temperature: 0
  prompts_archived: true
  raw_outputs_archived: true
  human_reviewed: true
  reproducible_without_ai: true
  live_model_required: false
  ai_output_used_as_data: false
  prompt_files: ["prompts/analysis_prompt.md"]
  output_files: ["ai_outputs/code_response.md"]
  code_files: ["analysis.do"]
```

Then write the passport:

```bash
aesdk agent ai-passport --pap pap.yaml --proposal proposal.json --output ai.lock.json
```

The passport records model metadata and hashes archived prompt/output/input/code files. If AI generated analysis code, declare the language and list the final reviewed code files in `code_files`; this applies equally to Python `.py`, R `.R`, and Stata `.do` workflows. AESDK checks that declared languages match the archived code extensions, so a passport cannot claim Stata while only hashing an R script. AESDK blocks workflows that require a live AI model for replication, and it blocks AI-derived data when raw AI outputs are not archived.

## Method Protocols

To see what AESDK tells an agent about a method:

```bash
aesdk methods list
aesdk methods show did
aesdk methods packs
aesdk methods pack did --format yaml
aesdk methods curriculum --format yaml
aesdk methods sources did --format yaml
aesdk rules list --format text
aesdk sources inventory --format yaml
aesdk sources software --format yaml
```

AESDK now has two knowledge layers:

- **method protocols**, which are compact guardrails used by preflight checks
- **Real Knowledge Packs**, which add estimator decision trees, assumptions, required inputs, diagnostics, failure modes, code recipes, reporting checklists, source anchors, and maturity labels

The governance layer is organized around a standard econometrics curriculum:

- **Foundations (The Mechanics)**: probability/statistics review, simple and multiple regression, Gauss-Markov assumptions, omitted variable bias, inference, and functional forms
- **The Identification Pivot**: dummy variables, heteroskedasticity-robust inference, IV/2SLS, simultaneity, and limited dependent variable models
- **Theoretical and Micro-foundations**: matrix OLS, asymptotics, MLE, GMM, panel fixed effects/random effects, and time-series dynamics
- **Advanced Empirical Research**: potential outcomes, randomized controlled trials and field experiments, DiD, RDD, matching, synthetic control, nonlinear DiD, structural/BLP-style modeling, and double machine learning

Each method protocol now declares its curriculum stage and topic tags, so an AI agent can see where a method sits in the larger econometrics sequence before it writes code.

Governance files and knowledge packs are organized by econometric topic or method, not by textbook author. Textbooks and papers remain registered as sources inside the rule or pack, but the file identity is the research decision being governed: `did`, `iv_2sls`, `panel_inference`, `citation_integrity`, and the method pack ids. This is deliberate: it helps AI agents treat sources as evidence rather than inventing author-specific doctrine.

Every bundled method pack now has an executable governance rule file. AESDK currently ships 109 executable rules across OLS/CEF, IV/2SLS, panel inference, DiD, randomized controlled trials/experimental methods, RDD, matching, synthetic control, nonlinear DiD, GMM, limited dependent variable models, time series, citation integrity, and AI replicability. The newer method areas still carry human-review maturity labels, but their core required inputs, assumptions, diagnostics, and failure modes are now promoted into runnable `pass`/`warn`/`block` checks.

The source metadata covers the local textbook/source library under `tools/`, including Wooldridge, Angrist & Pischke, Greene, Stock & Watson, Gujarati, Verbeek, Heiss, World Bank impact evaluation material, J-PAL randomized-evaluation resources, critical RCT scope sources, recent Wooldridge DiD sources, and package documentation. Public source registry entries must include an online locator such as a DOI, publisher page, journal page, author page, or official package page. The package stores metadata, source locators, and compact paraphrased guidance. It does not package the PDFs or long extracted textbook text.

For maintainers adding new books or papers, run the deep audit:

```bash
python scripts/deep_knowledge_audit.py --tools-dir tools --write-report docs/deep_knowledge_audit_report.yaml
```

The report scans local PDFs page-by-page and records candidate page locators, duplicate pack IDs, long-text warnings, and coverage gaps. It is a maintenance aid, not a substitute for human source review.

The newest packs for matching, synthetic control, nonlinear DiD, GMM, limited dependent variable models, and time series are marked `pending_human_review` with `ai_source_audited_pending_human_review`. They now have executable guardrails, but a human econometrician should still sign off before treating their full guidance as final audited doctrine.

## Reproducibility

When AESDK runs analysis code, it writes a replication record:

```bash
aesdk reproduce --blob .aesdk.json --replay
aesdk agent report --blob .aesdk.json --output workflow.html
```

This lets a supervisor, coauthor, or future RA inspect what was proposed, validated, and executed. The HTML report summarizes the workflow events, execution diagnostics, recorded artifacts, and nearby output files in the task folder.

## What AESDK Does Not Do

AESDK does not:

- guarantee that an empirical design is correct
- replace an advisor, coauthor, referee, or domain expert
- prove that an identification assumption is true
- redistribute copyrighted textbook content
- accept AI-generated citations that cannot be found online

It helps ensure that the agent follows a documented research workflow and stops when obvious econometric guardrails are violated.

## License

AESDK is released under the Apache-2.0 license.

## Documentation

- Distribution and public release: `docs/DISTRIBUTION.md`
- Functionality overview: `docs/PROJECT_FUNCTIONALITY.md`
- Security notes: `SECURITY.md`
- Release checklist: `docs/RELEASE_CHECKLIST.md`
