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

- method guidance for common econometric workflows, including OLS/CEF, IV/2SLS, panel fixed effects, DiD, randomized controlled trials/experimental methods, RDD, matching, synthetic control, nonlinear DiD, GMM, limited dependent variable models, time series, maximum likelihood estimation, double/debiased machine learning, structural/BLP estimation, nonparametric/semiparametric estimation, Bayesian econometrics, and ARCH/GARCH volatility models
- pre-analysis plan checks
- proposal validation with `pass`, `warn`, or `block`
- data-aware preflight that reads the declared dataset and cross-checks the PAP against it (missing variables, undeclared staggered adoption, few clusters, singleton clusters, missingness, no-variation regressors)
- AI-agent context packets that explain the relevant assumptions and diagnostics
- governed execution that refuses to run blocked analysis code
- governed execution for Python scripts, Stata `.do` files, and R scripts
- reproducibility records through an `.aesdk.json` audit file
- task/prompt intake helpers that draft a reviewable `pap.yaml` and `proposal.json` and create the required `.aesdk.json` audit file
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

Install AESDK before adding AESDK commands to `AGENTS.md`, `CLAUDE.md`, or another agent instruction file. If the package is not installed, the agent will usually report `aesdk` as missing when it tries to run preflight.

For local development from this repository:

```bash
pip install -e .
```

From PyPI:

```bash
pip install aesdk
```

Then get set up in one step. This verifies the install, saves the ready-made
assistant instructions into your project, and prints a plain-language "you're
ready" summary — no other commands to learn:

```bash
aesdk setup
```

If you are not a programmer, that is the only command you (or your assistant)
need. Check that the command is available:

```bash
aesdk methods list
```

If your shell cannot find `aesdk` after installation, use the Python module entry point or install with the same Python interpreter your agent uses:

```bash
python -m pip install aesdk
python -m aesdk methods list
```

## Use AESDK From Python

AI agents can use the top-level Python API:

```python
import aesdk as ae

intake = ae.intake_prompt(
    prompt="Estimate whether a randomized rollout affected county employment with an event-study design.",
    method="did",
    output_dir=".",
    outcome="employment",
    treatment="treated",
    unit="county",
    time="year",
)

prepared = ae.prepare(
    pap_path=intake.pap_path,
    proposal=intake.proposal_path,
    blob_path=".aesdk.json",
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
aesdk agent doctor
aesdk agent context --method did
aesdk agent context --method did --depth full
aesdk agent preflight --method did --pap pap.yaml --proposal proposal.json --conformance strict
aesdk agent draft-pap --method did --goal "Estimate policy effects" --data panel.csv --outcome y --treatment treated --unit state --time year --output pap.yaml
aesdk agent intake --task <task-file.pdf> --method did --output-dir .
aesdk agent intake --prompt "Estimate the policy effect with a DiD event-study design." --method did --output-dir .
aesdk agent prepare --prompt "Estimate the policy effect with a DiD event-study design." --method did --output-dir .
aesdk agent prepare --method did --pap pap.yaml --proposal proposal.json --output-dir .
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

You do not need to hand-write these instructions. Generate the ready-made file
and save it in your project:

```bash
aesdk agent template --target AGENTS.md   # for most AI coding agents
aesdk agent template --target CLAUDE.md   # for Claude / Claude Code
```

Both bundled templates are written for a **non-technical audience** — research
analysts, associates, faculty, and economists who do not run terminal commands.
They instruct the AI assistant to do all the technical work itself (run the
AESDK commands, draft and update the record files, run the analysis) and to
translate everything into plain research language: ask plain-English questions
instead of field names, never dump JSON or terminal output, and explain any
issue like a careful senior RA — what the concern is, why it matters, and what
to do next.

If you are not a programmer, the only thing you need to do is keep this file in
your project and, if AESDK is not installed yet, ask your assistant: "Please set
up AESDK for me." The assistant handles the rest and keeps the methods check
running quietly in the background before any analysis code is written or run.

## Use AESDK From Chat (ChatGPT or Claude)

Most researchers start in a chat window (ChatGPT or Claude) rather than a coding
agent. AESDK works there too, at three levels:

```bash
aesdk chat-guide --target chatgpt   # paste-in preset for a ChatGPT Custom GPT / chat
aesdk chat-guide --target claude    # paste-in preset for a Claude Project / chat
aesdk chat-guide --target mcp       # connect AESDK to Claude as an MCP connector
```

- **Advisory (zero setup):** paste the `chatgpt` or `claude` preset into a Custom
  GPT, a Claude Project, or your first message. The assistant then follows AESDK's
  workflow and guardrails and explains issues in plain language. Because nothing
  executes, treat its verdicts as a knowledgeable review, not enforcement.
- **Enforced via code interpreter:** in ChatGPT Advanced Data Analysis or Claude's
  code tool, upload your data (and, for ChatGPT's offline sandbox, the AESDK wheel),
  and the assistant runs `aesdk` for real pass/warn/block results.
- **Enforced via MCP (recommended for Claude):** run AESDK as a local Model Context
  Protocol server so Claude can call the real checks from a chat window, with your
  data staying on your machine. Full steps are below.

### Connect AESDK to Claude via MCP (two commands)

Run these in a terminal **on your own computer** — not inside a web chat's code
tool. The claude.ai web sandbox is a temporary container with no Claude Desktop,
so wiring it up there connects nothing (and `aesdk connect-claude` will warn you
if it can't find Claude Desktop). This runs entirely on your machine; no data is
sent anywhere. There is no JSON to edit — the second command finds and updates
Claude Desktop's config for you (merging with anything already there, and backing
up the old file first):

```bash
pip install "aesdk[mcp]"   # install the MCP tools
aesdk connect-claude       # wire AESDK into Claude Desktop
```

Then fully quit and reopen Claude Desktop, and in a chat say: *"Use AESDK to check
my study design before we write any code."* Claude can now call `list_methods`,
`method_context`, `preflight`, `scan_data`, and `check_ols`, and explains the
pass/warn/block result in plain language. Use `aesdk connect-claude --dry-run` to
preview the change first.

<details>
<summary>Prefer to edit the config yourself?</summary>

Open Claude Desktop's **Settings → Developer → Edit Config**
(`claude_desktop_config.json`) and add an `aesdk` entry, then restart:

```json
{
  "mcpServers": {
    "aesdk": {
      "command": "python",
      "args": ["-m", "aesdk", "mcp"]
    }
  }
}
```

`aesdk chat-guide --target mcp` prints this and the auto-connect steps at any time.
</details>

On **claude.ai** (web), add a custom connector only if your organization hosts a
trusted internal AESDK endpoint; because econometrics data is often confidential,
prefer the local Claude Desktop setup above. Code execution is intentionally
**not** exposed over MCP — chat gets the guardrails and diagnostics, while
governed execution stays in the CLI.

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

Human-in-the-loop and human-intervention evidence works the same for Stata and R. For a Stata workflow, list the AI draft `.do`, final `.do`, and `review/human_code_diff.patch`; for an R workflow, list the AI draft `.R`, final `.R`, and the same patch or manual-change note. AESDK hashes these evidence files in the AI passport and blocks a claimed human code modification if the diff records no actual textual code change.

## AI Replicability Passport

AESDK treats AI use as acceptable only when the work can be reproduced from archived artifacts without needing the same live AI model later. Add an `ai_use` block to the PAP or proposal when AI materially shapes the work:

```yaml
ai_use:
  used: true
  role: code_generation
  languages: ["stata"]
  provider: OpenAI
  agent_tool: Codex
  model_metadata_source: agent_unavailable
  model_metadata_unavailable_reason: The coding agent transcript did not expose the underlying model id.
  runtime_metadata_files: ["codex_runtime.json"]
  temperature: 0
  prompts_archived: true
  raw_outputs_archived: true
  human_in_loop: true
  human_interaction_files: ["review/followup_transcript.md"]
  human_modified_code: true
  ai_code_draft_files: ["ai_outputs/analysis_ai.do"]
  human_intervention_files: ["review/human_code_diff.patch"]
  human_reviewed: false
  review_status: not_reviewed
  reproducible_without_ai: true
  live_model_required: false
  ai_output_used_as_data: false
  prompt_files: ["prompts/analysis_prompt.md"]
  output_files: ["ai_outputs/code_response.md"]
  code_files: ["analysis.do"]
```

Then write the passport:

```bash
# Run the one that matches the AI tool used for this analysis.
aesdk agent codex-runtime --output codex_runtime.json
# or: aesdk agent claude-runtime --output claude_runtime.json
# or: aesdk agent copilot-runtime --output copilot_runtime.json
aesdk agent ai-passport --pap pap.yaml --proposal proposal.json --output ai.lock.json
```

The passport records model/tool metadata and hashes archived prompt/output/input/code files. `model` is for the underlying model id, while `agent_tool` is for the coding agent or editor, such as Codex, Claude Code, VS Code, or OpenCode. Every AI-use record must state `model_metadata_source`. If the coding agent does not expose the underlying model id, say so with `model_metadata_source: agent_unavailable`, name the tool in `agent_tool`, explain the limitation in `model_metadata_unavailable_reason`, and archive an existing runtime metadata file; do not put the tool name in `model`. AESDK can write runtime snapshots for Codex, Claude Code, and Copilot in VS Code. These commands record the local client or extension version when available, surface, repository name and commit SHA, session model and reasoning settings from explicit overrides or local config/settings, approval or permission policy, sandbox mode, config sources checked, and timestamp.

If AI generated analysis code, declare the language and list the final reviewed code files in `code_files`; this applies equally to Python `.py`, R `.R`, and Stata `.do` workflows. AESDK checks that declared languages match the archived code extensions, so a passport cannot claim Stata while only hashing an R script. If a human asked follow-up questions or corrected the agent, set `human_in_loop: true` and archive a non-empty transcript or comment trail in `human_interaction_files`. If a human manually changed AI-generated code, set `human_modified_code: true`, archive the AI draft in `ai_code_draft_files`, and archive a non-empty patch or change note in `human_intervention_files`.

AESDK can create the code-intervention patch:

```bash
aesdk agent interaction-log --output review/followup_transcript.md --speaker human --message "Please justify the clustering level." --source chat
aesdk agent review-diff --ai-code ai_outputs/analysis_ai.do --final-code analysis.do --output review/human_code_diff.patch
```

These fields do not automatically count as final human review. `human_reviewed: true` still requires review status and non-empty review evidence files; agent-only runs should leave it false until a researcher actually reviews the work. AESDK blocks workflows that require a live AI model for replication, and it blocks AI-derived data when raw AI outputs are not archived.

## Data-Aware Preflight

The rule engine validates what the researcher or agent *declares* in the PAP and proposal. That leaves a gap: an agent can declare `staggered_adoption: false` on genuinely staggered data, name an outcome column that does not exist, or cluster standard errors on a variable with only a handful of clusters, and the declaration-only rules will pass it.

Data-aware preflight closes that gap. When the PAP declares a readable dataset (via `data.source`) or you pass `--data`, AESDK reads the data and cross-checks the declared structure against it. Each check maps to a documented econometric failure mode:

- **DATA-VARS-001/002/003** — the declared outcome, treatment, unit, time, running, assignment, instrument, and mandatory-covariate names must exist as columns. A missing outcome or treatment variable is a hard block; constructed expressions such as `log(income)` or `i.year` are recognized and skipped so real regressors are not misflagged.
- **DATA-DID-001/002** — detects the number of treatment-adoption cohorts. If the data are staggered but `did_block.staggered_adoption` is not set, AESDK flags the two-way fixed-effects negative-weighting trap (Goodman-Bacon 2021; Callaway & Sant'Anna 2021).
- **DATA-CLUST-001** — warns when clustering yields fewer than ~42 clusters and recommends wild-cluster-bootstrap inference (Cameron & Miller 2015).
- **DATA-CLUST-002** — flags singleton clusters that distort cluster-robust variance and fixed-effects degrees of freedom (Correia 2015).
- **DATA-MISS-001** — warns on high missingness (>20%) of a core variable.
- **DATA-COLLIN-001** — flags declared variables with no variation (collinear with the intercept, or a constant outcome/treatment).
- **DATA-TREAT-001** — notes when the treatment is non-binary for a method that targets a binary-treatment estimand.

Run it standalone or as part of preflight:

```bash
aesdk agent scan-data --method did --pap pap.yaml
aesdk agent scan-data --method did --pap pap.yaml --data panel.csv --format json
aesdk agent preflight --method did --pap pap.yaml --proposal proposal.json --conformance strict
aesdk agent preflight --method did --pap pap.yaml --proposal proposal.json --no-scan-data
```

From Python:

```python
import aesdk as ae

scan = ae.scan_data(method="did", pap=pap_dict, proposal=proposal_dict, data_path="panel.csv")
print(scan.profile.adoption_cohorts, scan.profile.n_clusters)
for finding in scan.findings:
    print(finding.rule_id, finding.severity.value, finding.message)
```

The scan is **safe by design**: if the dataset cannot be located or read, no findings are produced and preflight behaves exactly as before. Advisory data checks (few clusters, singletons, missingness, no variation) never turn a passing workflow into a block; only a missing core variable and a staggered-adoption mismatch gate. AESDK reads local data files (`.csv`, `.tsv`, `.dta`, `.parquet`, `.feather`, `.xlsx`) and derives structural facts only; it does not modify the data or send it anywhere.

### OLS Assumption Checker (Wooldridge)

For `ols_cef`, AESDK fits the declared linear model on the data and runs a ten-item assumption checklist grounded in Wooldridge, *Introductory Econometrics: A Modern Approach*. It is honest about what data can and cannot show: the diagnostics that can be tested are tested, and the two assumptions that cannot be tested from data alone are reported as declaration items rather than given a false "pass".

| # | Assumption | Wooldridge | How AESDK checks it |
|---|---|---|---|
| 1 | Linear in parameters (functional form) | MLR.1 | Ramsey RESET test |
| 2 | Random sampling / independent observations | MLR.2 | declaration-only (notes duplicates) |
| 3 | No perfect collinearity | MLR.3 | matrix rank + VIF |
| 4 | Zero conditional mean (exogeneity) | MLR.4 | declaration-only (untestable) |
| 5 | Homoskedasticity | MLR.5 | Breusch-Pagan + White |
| 6 | No serial correlation (time-ordered data) | TS.5 | Breusch-Godfrey + Durbin-Watson |
| 7 | Normality of errors | MLR.6 | Jarque-Bera (CLT-softened when n is large) |
| 8 | No unduly influential observations | Ch. 9 | Cook's distance + leverage |
| 9 | Sufficient observations for the parameters | — | n vs k / rank |
| 10 | Inference matches the error structure | Ch. 8/12 | robust/clustered SE vs detected heteroskedasticity or dependence |

```bash
aesdk agent check-ols --pap pap.yaml --data cross_section.csv
```

```python
import aesdk as ae

report = ae.ols_assumption_report(df, outcome="y", regressors=["treated", "income"],
                                  structure="cross-section", standard_errors="conventional")
for check in report.checks:
    print(check.wooldridge, check.name, check.status)
```

When run inside preflight, detected violations (e.g. heteroskedasticity with non-robust standard errors, functional-form misspecification, perfect collinearity) become `DATA-OLS-*` findings.

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

Every bundled method pack now has an executable governance rule file. AESDK currently ships 146 executable rules across OLS/CEF, IV/2SLS, panel inference, DiD, randomized controlled trials/experimental methods, RDD, matching, synthetic control, nonlinear DiD, GMM, limited dependent variable models, time series, maximum likelihood estimation, double/debiased machine learning, structural/BLP estimation, nonparametric estimation, Bayesian econometrics, ARCH/GARCH volatility models, citation integrity, and AI replicability. The newer method areas still carry human-review maturity labels, but their core required inputs, assumptions, diagnostics, and failure modes are now promoted into runnable `pass`/`warn`/`block` checks.

The source metadata covers the local textbook/source library under `tools/`, including Wooldridge, Angrist & Pischke, Greene, Stock & Watson, Gujarati, Verbeek, Heiss, World Bank impact evaluation material, J-PAL randomized-evaluation resources, critical RCT scope sources, recent Wooldridge DiD sources, and package documentation. Public source registry entries must include an online locator such as a DOI, publisher page, journal page, author page, or official package page. The package stores metadata, source locators, and compact paraphrased guidance. It does not package the PDFs or long extracted textbook text.

For maintainers adding new books or papers, run the deep audit:

```bash
python scripts/deep_knowledge_audit.py --tools-dir tools --write-report docs/deep_knowledge_audit_report.yaml
```

The report scans local PDFs page-by-page and records candidate page locators, duplicate pack IDs, long-text warnings, and coverage gaps. It is a maintenance aid, not a substitute for human source review.

The packs for matching, synthetic control, nonlinear DiD, GMM, limited dependent variable models, time series, and double/debiased machine learning are marked `pending_human_review` with `ai_source_audited_pending_human_review`. They now have executable guardrails, but a human econometrician should still sign off before treating their full guidance as final audited doctrine. (Double/debiased machine learning is anchored on journal articles rather than a local textbook, so its upgrade path is a human sign-off rather than page anchors.)

The nonparametric, Bayesian, ARCH/GARCH volatility, maximum likelihood, and structural/BLP packs have been upgraded to `reviewed_guardrail` with `primary_source_page_audited`: their guidance is anchored to verified page numbers in the local source PDFs (Li & Racine 2007; Koop, Poirier & Tobias 2007; Tsay 2010; Greene *Econometric Analysis*; Hayashi 2000; Train 2009), recorded in `source_map.yaml` and the pack `source_anchors`.

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
