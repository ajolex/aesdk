# Release Checklist

## Pre-release

- [ ] `pytest -q` passes locally.
- [ ] `python -m build` passes locally.
- [ ] `python -m twine check dist/*` passes locally.
- [ ] CLI smoke checks pass for blocked and regulated examples.
- [ ] Agent smoke checks pass:
  - [ ] `aesdk agent context --method did`
  - [ ] `aesdk agent preflight --method did --pap docs/examples/simulated_did_training_policy/pap.yaml --proposal docs/examples/simulated_did_training_policy/proposal_pass.json`
- [ ] `SECURITY.md` reviewed for current controls and limits.
- [ ] `docs/PROJECT_FUNCTIONALITY.md` reflects actual runtime behavior.
- [ ] `docs/DISTRIBUTION.md` reflects the release process.
- [ ] `CHANGELOG.md` includes the release version.
- [ ] `.gitignore` excludes runtime artifacts and cache files.
- [ ] Public license is chosen and committed.
- [ ] Confirm the PyPI distribution name is available or update `[project].name`.

## Artifact Integrity

- [ ] Generate `.aesdk.json` for example runs.
- [ ] Sign blobs with `aesdk audit sign`.
- [ ] Verify signatures with `aesdk audit verify-signature`.
- [ ] Archive blobs + signatures with release artifacts when appropriate.

## Governance Readiness

- [ ] Rulepack hash is recorded in governance passport.
- [ ] Policy version is set and documented.
- [ ] Conformance/profile expectations are documented per environment.
- [ ] Attestation provider configured (noop for local, endpoint for production).

## Release Actions

- [ ] Create clean commits by feature area.
- [ ] Configure TestPyPI Trusted Publisher for `.github/workflows/publish.yml` and environment `testpypi`.
- [ ] Configure PyPI Trusted Publisher for `.github/workflows/publish.yml` and environment `pypi`.
- [ ] Tag release, for example `v0.1.0`.
- [ ] Push branch, tags, and open PR.
- [ ] Confirm CI green on PR.
- [ ] Confirm publish workflow succeeds on TestPyPI.
- [ ] Confirm publish workflow succeeds on PyPI.

## Post-release

- [ ] Test fresh install from PyPI.
- [ ] Announce release notes.
- [ ] Collect feedback on agent preflight, replay, signing, and attestation integration.
- [ ] Plan next hardening work: container isolation, richer method protocols, and live cloud KMS examples.
