# AESDK Security And Research Integrity Notes

AESDK is not a cybersecurity product. It is a research-workflow guardrail for AI-assisted econometric analysis.

The security goal is practical:

> Do not let an AI agent quietly run analysis code that violates documented econometric or reproducibility rules.

## What AESDK Protects Against

AESDK helps reduce these risks:

- an AI agent skipping a pre-analysis plan
- an AI agent using the wrong inference choice
- an AI agent running code after a blocked validation
- an AI agent leaving no record of what it did
- an AI agent inventing or loosely handling citations
- accidental changes to analysis code without an audit trail

## Main Controls

### Preflight Before Execution

AESDK checks the PAP and proposal before analysis code runs. Results are:

- `pass`: continue
- `warn`: researcher review needed
- `block`: stop

In strict workflows, warnings can be escalated to blocking errors.

### Reproducibility Record

AESDK records analysis events in an `.aesdk.json` file. The record is hash-chained so tampering can be detected.

### Replay

AESDK can replay recorded execution events:

```bash
aesdk reproduce --blob .aesdk.json --replay
```

Replay is most reliable when the same code, data, dependencies, and runtime environment are available.

### Sandboxed Execution

AESDK uses a subprocess sandbox with:

- import allowlists
- blocked dangerous calls such as `eval`, `exec`, and file-opening calls
- syntax, dependency, and runtime diagnostics
- subprocess timeouts
- CPU and memory limits on Unix-like systems

This is useful, but it is not the same as full container or virtual-machine isolation.

### Signing

AESDK can sign replication records:

- HMAC for local or CI workflows
- KMS-HTTP for managed signing services
- optional adapters for AWS KMS, GCP Cloud KMS, and Azure Key Vault

Signing helps detect changes to audit records after the fact.

## Current Limits

AESDK does not:

- prove an empirical design is correct
- prevent every possible unsafe code pattern
- replace Docker, Podman, or managed isolated compute
- make replay deterministic if data or dependencies change
- make AI-generated citations trustworthy without verification

For high-stakes or regulated work, run AESDK inside an isolated compute environment and store audit files in immutable storage.

## Recommended Research Practice

- Keep PAPs under version control.
- Treat `block` as a hard stop.
- Require human acknowledgement for `warn`.
- Store `.aesdk.json` files with project outputs.
- Re-run `aesdk reproduce --replay` before sharing results.
- Verify citations in AI-generated literature reviews or method descriptions.
- Treat method-rule changes as research-governance changes, not casual edits.
