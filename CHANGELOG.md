# Changelog

## 1.0.0 - 2026-03-08

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

### Notes
- Remote attestation and KMS integration are real HTTP integration points; production deployment requires managed endpoints and secrets.
