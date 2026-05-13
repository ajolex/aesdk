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
- regression discontinuity
- matching and propensity-score preprocessing
- synthetic control
- nonlinear DiD
- generalized method of moments
- limited dependent variable models
- time-series econometrics

The protocols summarize assumptions, diagnostics, standard-error expectations, and source references. They are designed for AI agents to read before writing code.

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
```

AESDK also includes metadata-only source inventory and topic locator reports for all local textbook/source PDFs. These reports point to source files and pages but do not package long textbook text.

Maintainers can refresh the page-by-page knowledge audit whenever new books or papers are added:

```bash
python scripts/deep_knowledge_audit.py --tools-dir tools --write-report docs/deep_knowledge_audit_report.yaml
```

The audit checks every local PDF page for method-topic signals, compares those signals with existing packs, and reports source hits, missing packs, duplicate IDs, and long-text risks. Use it to guide human review and pack expansion.

The newest expanded packs are `pending_human_review` and `ai_source_audited_pending_human_review`. They are ready for a human econometrician's final review, but they are not labeled as reviewed or final audited doctrine.

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

### Governed Execution

AESDK can run Python or Stata code only after the analysis passes preflight:

```bash
aesdk agent run --method did --pap pap.yaml --proposal proposal.json --code-file analysis.py
aesdk agent run --method did --pap pap.yaml --proposal proposal.json --code-file analysis.do --language stata
```

If the proposal is blocked, the code does not run.
Stata runs require a licensed local Stata executable on `PATH` or in `AESDK_STATA`.

### Reproducibility Record

When AESDK executes analysis code, it writes an `.aesdk.json` file. This records the sequence of events: initialization, proposal, validation, and execution.

Replay check:

```bash
aesdk reproduce --blob .aesdk.json --replay
```

This is useful for supervisors, coauthors, future RAs, and audit trails.

### Citation and Source Checks

AESDK includes utilities to verify citation metadata in agent-generated text. This matters because AI agents can invent plausible-looking references.

```bash
aesdk cite verify --text reasoning_log.txt
```

## More Advanced Features

AESDK also includes:

- conformance levels: `basic`, `strict`, and `regulated`
- context profiles: `research`, `production`, and `regulated`
- hash-chained replication blobs
- replay checks
- HMAC and KMS signing options
- sandboxed execution controls
- Python and Stata execution dispatch, with R planned next
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
- an R execution bridge with the same preflight and replay semantics as Python and Stata
- conversion from PDF-page locators to cleaner printed-page/chapter anchors where possible
- container isolation for high-stakes regulated execution
- signed replay reports for external auditors
- live examples for AWS/GCP/Azure KMS setups
