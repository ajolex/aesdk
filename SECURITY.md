# AESDK Security Policy

## Security posture

AESDK enforces governance-first execution. Invalid work is blocked instead of tolerated.

## Implemented controls

### Governance and conformance
- PAP validation is mandatory.
- Rule evaluation returns pass/warn/block.
- Conformance levels:
  - `basic`: rule severities as authored
  - `strict`: warnings escalate to errors
  - `regulated`: warnings and infos escalate to errors

### Policy profiles and passport
- Context-to-profile mapping (`research`, `production`, `regulated`).
- Governance passport stored in blob metadata:
  - policy version
  - profile and conformance
  - rulepack hash
  - attestation evidence

### Trace integrity and replay
- Append-only hash-chained blob events.
- Integrity verification for tamper detection.
- Replay execution for recorded execute events with status/hash comparison.

### Signing and verification
- HMAC signing and verification.
- KMS-HTTP signing and verification integration points.

### Attestation
- Local no-op provider for development.
- HTTP endpoint provider for production integration.

### Sandbox enforcement
- Import allowlist.
- Forbidden call-pattern blocking.
- Syntax/dependency/runtime diagnostics.

## Current limits
- Sandbox is subprocess-based, not full container isolation.
- KMS-HTTP and attestation depend on external service quality and key management.
- Replay is deterministic only when runtime environment/dependencies are controlled.

## Operational recommendations
- Use managed secrets for HMAC/KMS/attestation tokens.
- Run in isolated CI/runtime workers.
- Store blobs/signatures as immutable release artifacts.
- Treat rulepack/profile/policy changes as controlled governance changes.
