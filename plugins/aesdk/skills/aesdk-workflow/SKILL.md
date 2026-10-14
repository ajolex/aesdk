---
name: aesdk-workflow
description: "Econometrics methods check (AESDK) to run BEFORE writing or running any regression, causal-inference, or econometric analysis code (OLS, IV/2SLS, panel fixed effects, difference-in-differences, event studies, RCTs, RDD, matching, synthetic control, GMM, logit/probit, time series, MLE, DML, structural, nonparametric, Bayesian, GARCH) in Python, R, or Stata. Use when a researcher asks to estimate an effect, run a regression, analyze an experiment or policy, or review an analysis plan."
license: Apache-2.0
---

# AESDK econometrics workflow

The person is usually a researcher, not a programmer. Run every command yourself,
never paste raw JSON/YAML or tracebacks, ask plain-English questions instead of
field names, and explain findings like a careful senior RA: the concern, why it
matters, and the fix. AESDK checks that the workflow follows documented
econometric guardrails; it does not prove the design is correct.

## Steps

1. **Method.** Work out the method from what the researcher says and confirm it in
   plain language. Load the matching `aesdk-<method>` skill if one is available, or
   run `aesdk agent context --method <method>` (`aesdk methods list` lists ids).
2. **Plan.** Draft the reviewable plan from the researcher's words:
   `aesdk agent intake --prompt "<request>" --method <method> --output-dir .`
   (or `--task <file>` for a task document; never invent a task file).
3. **Record.** `aesdk agent prepare --method <method> --pap pap.yaml --proposal proposal.json --output-dir .`
   creates `.aesdk.json`, which is required even when the check blocks.
4. **Check.** `aesdk agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict`
   also reads the declared dataset and cross-checks it against the plan.
   - **block** = hard stop. Explain the problem and the fix; do not write or run analysis code.
   - **warn** = explain it and get a clear plain-language go-ahead before continuing.
5. **Run under governance.** `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json --code-file analysis.py`
   (also `.do` for Stata and `.R` for R). Never run estimation scripts directly with
   `python`, `Rscript`, or `stata`; AESDK hooks may deny that.
6. **Report.** `aesdk agent report --blob .aesdk.json --output workflow.html` for a shareable summary.
7. **AI provenance.** If AI materially shaped code, data, or variables, document `ai_use` and
   write `aesdk agent ai-passport --pap pap.yaml --proposal proposal.json --output ai.lock.json`.
   Archived sessions in `.aesdk/sessions/` are picked up automatically. Never claim a human
   review that did not happen.

## Rules

- Do not invent assumptions, diagnostics, citations, estimator requirements, or AI-use evidence. Ask.
- Put research decisions in `pap.yaml` / `proposal.json`, not only in chat or agent memory, so
  they are checked and reproducible.
- If `aesdk` is missing, try `python -m aesdk ...`; if still missing, offer to install it
  (`python -m pip install aesdk`) in one sentence.
