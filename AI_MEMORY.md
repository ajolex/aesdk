### 2026-05-13 - Bug - Changelog Audit Hardening
- **Issue:** The changelog audit found that recent AESDK features were mostly implemented, but agent preflight and run status semantics had small guardrail gaps.
- **Resolution:** Hardened preflight so requested method context must match both the PAP strategy and proposal estimator, made `AnalysisRunResult.blocked` include sandbox execution blocks, and added regression coverage for Stata replay language preservation plus GCP/Azure KMS injected-client paths.
- **Implications:** Changed `src/aesdk/agent/preflight.py`, `src/aesdk/agent/run.py`, `src/aesdk/trace/kms_providers.py`, `tests/unit/agent/test_agent_api.py`, `tests/unit/trace/test_kms_signing.py`, and `tests/integration/test_replay_workflow.py`; full suite passed with 65 tests.
- **Difficulty:** Medium - the audit involved reconciling two subagent passes and separating real defects from already-modified working-tree changes.
- **Lessons:** For agent-facing research guardrails, preflight must check consistency across requested method, PAP strategy, and proposal estimator, and result flags must reflect both governance and execution blocks.
### 2026-05-13 - Feature - Python/Stata/R Guardrail Parity
- **Issue:** AESDK had Python-first execution and knowledge packaging while Stata and R needed to match the public package surface analysts expect in development economics workflows.
- **Resolution:** Added Stata and R execution dispatch behind preflight, R package allowlisting, replay language normalization, CLI sandbox diagnostics, official software source validation, and Python/R/Stata recipe parity for public packs where mature sources exist.
- **Implications:** Updated sandbox runner/whitelist, agent and CLI run paths, trace replay, knowledge packs, official software source metadata, docs, templates, and tests; nonlinear DiD remains explicitly R-only until mature Python/Stata recipes are registered.
- **Difficulty:** Hard - Required reconciling runtime behavior, audit-trace semantics, package data, econometric recipe coverage, and documented exceptions across multiple public surfaces.
- **Lessons:** When adding a language bridge, audit execution cwd, runtime diagnostics, replay metadata, import/package allowlists, official recipe sources, package-data inclusion, and per-pack parity tests together.
### 2026-05-13 - Bug - Panel Cluster Declaration Guardrails
- **Issue:** Panel proposals could claim clustered or two-way-clustered inference without declaring the cluster level or both cluster dimensions.
- **Resolution:** Added Wooldridge panel rules blocking missing cluster levels and one-dimensional two-way clustering, plus validator helpers for parsing scalar and list-valued cluster declarations.
- **Implications:** Changed `src/aesdk/protocol/validator.py`, `src/aesdk/governance/rules/wooldridge_panel.rules.yaml`, and `tests/unit/protocol/test_validator_rules.py`; full suite passed with 78 tests.
- **Difficulty:** Medium - The fix required extending the safe rule-expression evaluator while preserving existing panel and DiD validation behavior.
- **Lessons:** Inference guardrails must force cluster levels and multiway cluster dimensions into the PAP/proposal record rather than treating the word "clustered" as sufficient.
