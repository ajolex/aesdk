# What AESDK Does

AESDK is a guardrail system for AI-assisted econometric work. It is meant to help an RA, professor, or applied research team catch common workflow problems before an AI agent writes or runs analysis code.

It does three main things:

1. Gives the AI agent method guidance.
2. Checks the proposed analysis against a pre-analysis plan and econometric rules.
3. Leaves behind a reproducible record of what was run.

## Main Features

### Method Guidance

AESDK stores two layers of method guidance.

The first layer is compact method protocols for common empirical workflows:

- OLS / CEF regression
- IV / 2SLS
- panel fixed effects
- differences-in-differences
- randomized controlled trials and experimental methods
- regression discontinuity
- matching and propensity-score preprocessing
- synthetic control
- nonlinear DiD
- generalized method of moments
- limited dependent variable models
- time-series econometrics

The protocols summarize assumptions, diagnostics, standard-error expectations, and source references. They are designed for AI agents to read before writing code.

The protocols are also mapped into a curriculum structure that looks like a standard econometrics sequence:

- Foundations: regression mechanics, Gauss-Markov, omitted variable bias, inference, and functional forms
- Identification Pivot: endogeneity, robust inference, IV/2SLS, simultaneity, and limited dependent variables
- Theoretical and Micro-foundations: matrix OLS, asymptotics, MLE, GMM, panel data, and time-series dynamics
- Advanced Empirical Research: potential outcomes, randomized controlled trials and field experiments, DiD, RDD, matching, synthetic control, nonlinear DiD, structural models, and double machine learning

This makes AESDK easier for RAs and professors to audit: a method is not just a code recipe, it has a place in the econometrics curriculum and a set of assumptions attached to that place.

Rule files and knowledge packs are method/topic organized rather than author organized. For example, DiD rules live under a DiD rule file, while Angrist-Pischke, Callaway-Sant'Anna, Wooldridge, or other sources appear as supporting references inside the rules and source metadata. That separation reduces the chance that an AI agent treats a source name as a method or invents source-specific rules.

Executable rule coverage now exists for every bundled method pack. AESDK ships 116 runnable governance rules across OLS/CEF, IV/2SLS, panel inference, DiD, randomized controlled trials/experimental methods, RDD, matching, synthetic control, nonlinear DiD, GMM, limited dependent variable models, time series, citation integrity, and AI replicability. The expanded methods still carry maturity labels where human econometrician review is pending, but they are no longer guidance-only.

The second layer is the Real Knowledge Pack system. A knowledge pack is a self-contained, source-anchored method guide with:

- when to use or avoid the method
- estimand language
- estimator decision tree
- assumptions in plain and formal language
- required inputs
- diagnostics
- failure modes
- Python, R, or Stata starter recipes from official package documentation
- reporting checklist
- maturity labels that tell the agent how much confidence to place in the pack

Current packs are available with:

```bash
aesdk agent context --method did --depth full
aesdk methods packs
aesdk methods pack did --format yaml
aesdk rules list --format text
```

AESDK also includes metadata-only source inventory and topic locator reports for all local textbook/source PDFs. These reports point to source files and pages but do not package long textbook text.

Maintainers can refresh the page-by-page knowledge audit whenever new books or papers are added:

```bash
python scripts/deep_knowledge_audit.py --tools-dir tools --write-report docs/deep_knowledge_audit_report.yaml
```

The audit checks every local PDF page for method-topic signals, compares those signals with existing packs, and reports source hits, missing packs, duplicate IDs, and long-text risks. Use it to guide human review and pack expansion.

The newest expanded packs are `pending_human_review` and `ai_source_audited_pending_human_review`. Their core guardrails are executable, and they are ready for a human econometrician's final review, but they are not labeled as reviewed or final audited doctrine.

### Preflight Checks

The most important public workflow is:

```bash
aesdk agent preflight --method did --pap pap.yaml --proposal proposal.json --conformance strict
```

AESDK returns:

- `pass`: the proposal can proceed
- `warn`: the researcher should review something
- `block`: the agent should stop

For example, AESDK blocks a panel DiD proposal that uses non-clustered standard errors.

### Pre-analysis Plan Support

AESDK validates a PAP before execution. The PAP records the research question, data structure, treatment variable, outcome variable, covariates, fixed effects, standard errors, and method-specific design information.

Agents can also draft a starter PAP:

```bash
aesdk agent draft-pap --method did --goal "Estimate policy effects" --data panel.csv --outcome y --treatment treated --unit state --time year --output pap.yaml
```

The draft still needs researcher review.

When a researcher starts from a task folder or assignment document, agents can use intake to create the starter files in the same folder:

```bash
aesdk agent intake --task Stata_Task.pdf --method did --output-dir .
```

The intake command extracts task text when possible, infers or accepts a method, and writes a reviewable `pap.yaml` and `proposal.json`. It is intentionally a first draft, not a substitute for the researcher checking the design.

### AI Replicability Passport

AESDK can also govern how AI itself was used in the research workflow. The PAP or proposal may include an `ai_use` block documenting the AI role, provider, model, prompt/output archives, human review, and whether the final analysis can be reproduced without calling a live AI model.

```bash
aesdk agent ai-passport --pap pap.yaml --proposal proposal.json --output ai.lock.json
```

The generated passport hashes archived prompt, raw-output, input, code, and human-review evidence files. If AI writes or materially revises analysis code, the `ai_use` block must declare the analysis language and list the final reviewed script in `code_files`, whether the code is Python, Stata, or R. AESDK also checks that declared languages match the archived code extensions, so an R script cannot be hidden behind a Stata declaration.

The passport separates the coding agent from the underlying model. Tools such as Codex, Claude Code, VS Code, GitHub Copilot, and OpenCode belong in `agent_tool`; `model` should only contain the underlying model id when it is actually exposed by the tool or API. AESDK now requires every AI-use record to state where model metadata came from. If model metadata is unavailable, AESDK requires the agent tool name, an explicit unavailable reason, and an existing runtime metadata artifact rather than a made-up model name. AESDK can write runtime snapshots with `aesdk agent codex-runtime`, `aesdk agent claude-runtime`, and `aesdk agent copilot-runtime`. These capture local client or extension version when available, surface, repository and commit, session/config model settings, approval or permission policy, sandbox mode, config sources checked, and timestamp. A true human-review claim also needs `review_status` and at least one existing `review_files` artifact; agent-only runs should record `human_reviewed: false`.

AESDK blocks workflows that require a live AI model for replication, blocks AI code generation without code-file records, and blocks AI-derived data when raw AI outputs are not archived. This is meant for cases where AI writes code, classifies text, extracts data, scores documents, or creates variables that later enter an econometric analysis.

### Governed Execution

AESDK can run Python, Stata, or R code only after the analysis passes preflight:

```bash
aesdk agent run --method did --pap pap.yaml --proposal proposal.json --code-file analysis.py
aesdk agent run --method did --pap pap.yaml --proposal proposal.json --code-file analysis.do --language stata --timeout-seconds 300
aesdk agent run --method did --pap pap.yaml --proposal proposal.json --code-file analysis.R --language r
```

If the proposal is blocked, the code does not run.
Stata runs require a licensed local Stata executable on `PATH` or in `AESDK_STATA`. R runs require `Rscript` on `PATH` or in `AESDK_R`.
Python and R package imports are checked against the sandbox allowlists before execution. The bundled method-pack recipes are tested against those allowlists so AESDK does not recommend a package that its own execution guard would reject.
When Python, Stata, or R code does not already declare a seed, AESDK uses a date seed (`yyyymmdd`) and records it in the execution artifacts. Python seeds `random` and NumPy when available, Stata prepends `set seed yyyymmdd`, and R prepends `set.seed(yyyymmdd)`. If the researcher already declared a seed, AESDK preserves it. Stata logs are captured as execution artifacts when available, which makes it easier to audit what happened during a `.do` file run.

### Reproducibility Record

When AESDK executes analysis code, it writes an `.aesdk.json` file. This records the sequence of events: initialization, proposal, validation, and execution.

Replay check:

```bash
aesdk reproduce --blob .aesdk.json --replay
aesdk agent report --blob .aesdk.json --output workflow.html
```

This is useful for supervisors, coauthors, future RAs, and audit trails. The HTML report gives a plain workflow view of validation, execution, diagnostics, AI-use metadata, recorded run artifacts, and nearby task-folder outputs.

### Citation and Source Checks

AESDK includes utilities to verify citation metadata in agent-generated text. This matters because AI agents can invent plausible-looking references.

```bash
aesdk cite verify --text reasoning_log.txt
```

Online verification is mandatory. DOI-like citations must resolve online, and public AESDK source metadata must include a DOI or public URL. A citation that cannot be found online is treated as a research-integrity problem, not a cosmetic warning.

## More Advanced Features

AESDK also includes:

- conformance levels: `basic`, `strict`, and `regulated`
- context profiles: `research`, `production`, and `regulated`
- hash-chained replication blobs
- replay checks
- HMAC and KMS signing options
- sandboxed execution controls
- Python, Stata, and R execution dispatch
- CSV and HTML trace export
- optional LLM adapters

Most research users will not need these details on day one. They are there for teams that need stronger auditability.

## What AESDK Does Not Claim

AESDK does not prove that an identification strategy is valid. It cannot know whether parallel trends is truly credible, whether an instrument is truly exogenous, or whether a research design is substantively convincing.

AESDK helps enforce a disciplined workflow:

- state the plan
- check the proposed method
- block obvious violations
- run only after preflight
- keep a reproducible record

## Example Projects

- `docs/examples/simulated_did_training_policy`: a realistic simulated DiD workflow
- `docs/examples/did_min_wage`: a blocked DiD governance example
- `docs/examples/regulated_profile`: a signed-audit example

## Remaining Hardening Opportunities

- deeper human-audited maturity upgrades from `starter_guardrail` to `reviewed_guardrail` and eventually `audited`
- human-audited expansion of specialized Stata/R/Python recipes as official package support matures
- conversion from PDF-page locators to cleaner printed-page/chapter anchors where possible
- container isolation for high-stakes regulated execution
- signed replay reports for external auditors
- live examples for AWS/GCP/Azure KMS setups
