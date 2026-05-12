# AESDK Handoff Notes

This document summarizes the current state of AESDK for a future maintainer or research team lead.

## What AESDK Is Now

AESDK is a Python package for AI-assisted econometric research. Its public purpose is to help RAs and faculty make AI agents follow a documented empirical workflow before writing or running analysis code.

The most important user-facing commands are:

```bash
aesdk agent context --method did
aesdk agent preflight --method did --pap pap.yaml --proposal proposal.json --conformance strict
aesdk agent run --method did --pap pap.yaml --proposal proposal.json --code-file analysis.py
```

The most important Python API is:

```python
import aesdk as ae

gate = ae.preflight(method="did", pap_path="pap.yaml", proposal="proposal.json")
if gate.blocked:
    raise RuntimeError(gate.explain())
```

## Implemented

- Agent-facing API: context, preflight, PAP drafting, governed execution.
- Agent-facing CLI commands.
- `AGENTS.md` and `CLAUDE.md` templates.
- Textbook-backed method protocol registry.
- Source metadata and source locators.
- PAP validation.
- Rule-based pass/warn/block validation.
- Real `statsmodels` helpers for DiD and panel fixed effects.
- Replication blob, replay, signing, and trace export.
- Sandbox controls for agent-run code.
- Simulated DiD example for public demos.
- CI and package build workflow.
- Trusted Publishing workflow for TestPyPI and PyPI.

## Public Release Caveats

Before PyPI publication:

- Choose and commit a real public license.
- Confirm the package name `aesdk` is available.
- Confirm `tools/` textbook PDFs and large extraction artifacts are not included in the package.
- Run the build and fresh wheel install checks in `docs/DISTRIBUTION.md`.

## Good Next Features

- Better RDD support.
- Matching and synthetic-control protocols.
- More modern DiD estimator guidance.
- Cleaner source-page anchors.
- PDF or HTML supervisor reports.
- Container isolation for high-stakes execution.
- Public tutorial notebooks for RAs.
