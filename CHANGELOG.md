# Changelog

## 0.1.0 - 2026-05-13

### Added

- Agent-facing API:
  - `aesdk.agent_context`
  - `aesdk.preflight`
  - `aesdk.draft_pap`
  - `aesdk.run_analysis`
- Agent CLI:
  - `aesdk agent context`
  - `aesdk agent preflight`
  - `aesdk agent draft-pap`
  - `aesdk agent run`
  - `aesdk agent template`
- Stata `.do` file and R script execution support behind the same preflight gate and replay audit trail.
- Bundled `AGENTS.md` and `CLAUDE.md` templates.
- Textbook-backed knowledge registry and method protocols.
- Source locators for local textbook-derived SDK context.
- Real Knowledge Packs with estimator decision trees, assumptions, diagnostics, failure modes, code recipes, reporting checklists, maturity labels, and source anchors.
- Metadata-only source inventory and topic locator reports for all local textbook/source PDFs.
- Deep knowledge audit script for page-by-page local PDF scanning and pack coverage reports.
- Starter packs for matching, synthetic control, nonlinear DiD, GMM, limited dependent variable models, and time-series econometrics.
- AI source-audited maturity upgrade for the new brain packs, marked pending final human econometrician signoff.
- Real `statsmodels`-based DiD and panel fixed-effects helpers.
- Simulated DiD training-policy example.
- Provider-based KMS adapters for KMS-HTTP, AWS KMS, GCP KMS, and Azure Key Vault.
- CSV and styled HTML trace exporters.
- Public distribution docs and Trusted Publishing workflows.

### Notes

- AESDK is licensed under Apache-2.0.
- Textbook PDFs are local source material and should not be distributed inside the package.

## Historical Scaffold - 2026-03-08

### Added

- Enforcement-first PAP/rules/validation workflow with explicit pass/warn/block outcomes.
- Policy profiles and conformance levels (`basic`, `strict`, `regulated`).
- Governance passport metadata in replication blob.
- Remote attestation hooks with real HTTP endpoint provider support.
- Append-only replication blob integrity verification and execute-event replay execution.
- Signed audit artifacts:
  - HMAC signing/verification
  - KMS-HTTP signing/verification integration hooks
- Sandbox import allowlist and forbidden-call enforcement.
- CLI additions:
  - policy/profile options in `init` and `validate`
  - enhanced `reproduce --replay`
  - `audit sign` and `audit verify-signature`
- CI workflow with blocked DiD and regulated signed-audit smoke checks.
- Regulated profile example under `docs/examples/regulated_profile`.

### Changed

- Security documentation updated to reflect conformance, passport, signature, and attestation behavior.
- Functionality documentation expanded for developer handover and audit readiness.
