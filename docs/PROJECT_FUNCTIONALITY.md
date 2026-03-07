# AESDK Project Functionality Document

## Purpose

AESDK enforces scientific-method guardrails for LLM-assisted econometrics and provides auditable reproducibility artifacts.

## Functional pillars

1. PAP-first protocol gating.
2. Rule-based governance validation.
3. Conformance-level enforcement (`basic`, `strict`, `regulated`).
4. Policy profiles by context (`research`, `production`, `regulated`).
5. Governance passport metadata for each run.
6. Append-only hash-chained replication blob.
7. Full replay execution for execute events.
8. Signed audit artifacts (HMAC + KMS-HTTP integration).
9. Remote attestation hooks (noop + endpoint).
10. Sandboxed execution controls.

## Governance passport schema (stored in blob metadata)

- `policy_version`
- `policy_profile`
- `execution_context`
- `conformance_level`
- `rulepack_hash`
- `generated_at`
- `attestation`:
  - `provider`
  - `statement`
  - `timestamp`
  - `details`

## Signing models

### HMAC
- Local/shared-secret signing.
- Fast path for internal CI and dev environments.

### KMS-HTTP
- Signs/verifies blob hash via external HTTP service (`/sign`, `/verify`).
- Intended for enterprise key custody and central audit workflows.

## Replay model

`aesdk reproduce --replay`:
- verifies blob integrity
- re-runs recorded execute-event code through sandbox runner
- compares recorded vs replay status
- compares recorded vs recomputed code hash
- can fail on mismatch

## CLI summary

- `aesdk init`
  - profile/conformance/policy version
  - optional attestation endpoint + token
- `aesdk validate`
  - conformance-aware validation
- `aesdk reproduce`
  - integrity + full replay checks
- `aesdk audit sign`
  - hmac or kms-http signing
- `aesdk audit verify-signature`
  - signature verification by algorithm
- `aesdk cite verify`
  - citation checks

## Example packs

- `docs/examples/did_min_wage`:
  - blocked DiD governance example
- `docs/examples/regulated_profile`:
  - regulated profile pass path and signed audit flow

## CI behavior

CI executes:
- full test suite
- blocked DiD smoke checks
- regulated profile signed-audit verification

## Remaining hardening opportunities

- provider-specific KMS adapters (AWS/GCP/Azure) on top of KMS-HTTP contract
- containerized sandbox isolation with resource/network policy
- signed replay reports for external auditors
