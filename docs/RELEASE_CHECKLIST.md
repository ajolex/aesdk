# AESDK Public Release Checklist

Use this checklist before making AESDK public. The goal is not just to publish a Python package. The goal is to make sure an economics RA, professor, or applied research team can install AESDK and use it in an AI-assisted workflow without needing to understand the internals.

## Research-User Readiness

- [ ] The README explains AESDK in plain language for economics researchers.
- [ ] The README shows the simplest workflow: context, preflight, run.
- [ ] The example DiD project runs from copied commands.
- [ ] `AGENTS.md` tells AI agents exactly when to call AESDK.
- [ ] `CLAUDE.md` tells Claude exactly when to call AESDK.
- [ ] No public-facing page suggests AESDK replaces research judgment or peer review.
- [ ] No public-facing page implies the package redistributes textbooks.

## Method and Governance Readiness

- [ ] `aesdk methods validate` returns `knowledge_base=ok`.
- [ ] The supported methods are named clearly:
  - [ ] `ols_cef`
  - [ ] `iv_2sls`
  - [ ] `panel_fe`
  - [ ] `did`
  - [ ] `rdd` as planned/initial support
- [ ] The simulated DiD bad proposal is blocked.
- [ ] The simulated DiD good proposal passes.
- [ ] Replay works for an executed example.

## Package Readiness

- [ ] Apache-2.0 remains the intended public license.
- [ ] `pyproject.toml` has the correct package name.
- [ ] `pyproject.toml` has public metadata: description, authors, keywords, classifiers, URLs.
- [ ] Package data includes method protocols, source metadata, rules, schemas, and agent templates.
- [ ] Generated files such as `dist/`, `build/`, and `*.egg-info/` are not committed.
- [ ] Textbook PDFs and large extracted textbook files are not included in the package.

## Local Verification

- [ ] Tests pass:

```bash
python -m pytest
```

- [ ] Build passes:

```bash
python -m build
```

- [ ] Package check passes:

```bash
python -m twine check dist/*
```

- [ ] Fresh wheel install works:

```bash
python -c "import aesdk as ae; print(ae.agent_context('did').method_id)"
```

## Publishing Setup

- [ ] Confirm the name `aesdk` is available on PyPI, or choose another distribution name.
- [ ] Configure TestPyPI Trusted Publishing:
  - [ ] repository: `ajolex/aesdk`
  - [ ] workflow: `publish.yml`
  - [ ] environment: `testpypi`
- [ ] Configure PyPI Trusted Publishing:
  - [ ] repository: `ajolex/aesdk`
  - [ ] workflow: `publish.yml`
  - [ ] environment: `pypi`
- [ ] CI is green on the release commit.

## Release

- [ ] Update `CHANGELOG.md`.
- [ ] Commit release changes.
- [ ] Tag the release, for example:

```bash
git tag v0.1.0
git push origin main --tags
```

- [ ] Publish to TestPyPI first.
- [ ] Install from TestPyPI in a clean environment.
- [ ] Publish to PyPI.
- [ ] Install from PyPI in a clean environment.

## After Release

- [ ] Ask one RA to try the README workflow from scratch.
- [ ] Ask one faculty/applied researcher to read the README for clarity.
- [ ] Collect confusing points and update docs quickly.
- [ ] Track requested method coverage, especially RDD, matching, synthetic control, and more modern DiD variants.
