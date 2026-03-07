# Release Checklist (v1.0)

## Pre-release
- [ ] `pytest -q` passes locally.
- [ ] CLI smoke checks pass for blocked and regulated examples.
- [ ] `SECURITY.md` reviewed for current controls and limits.
- [ ] `docs/PROJECT_FUNCTIONALITY.md` reflects actual runtime behavior.
- [ ] `.gitignore` excludes runtime artifacts and cache files.

## Artifact integrity
- [ ] Generate `.aesdk.json` for example runs.
- [ ] Sign blobs with `aesdk audit sign`.
- [ ] Verify signatures with `aesdk audit verify-signature`.
- [ ] Archive blobs + signatures with release artifacts.

## Governance readiness
- [ ] Rulepack hash is recorded in governance passport.
- [ ] Policy version is set and documented.
- [ ] Conformance/profile expectations are documented per environment.
- [ ] Attestation provider configured (noop for local, endpoint for production).

## Release actions
- [ ] Create clean commits by feature area.
- [ ] Tag release (`v1.0.0`).
- [ ] Push branch, tags, and open PR.
- [ ] Confirm CI green on PR.

## Post-release
- [ ] Announce upgrade notes.
- [ ] Collect feedback on replay, signing, and attestation integration.
- [ ] Plan v1.1 hardening (KMS provider adapters, stronger sandbox isolation).
