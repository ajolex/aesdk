# Agentic Econometrics SDK (AESDK)

AESDK is a policy-enforced SDK for LLM-assisted econometrics. It blocks invalid work by design and keeps an auditable replication record.

## Key capabilities

- PAP required before execution.
- Rules engine with pass/warn/block outcomes.
- Conformance levels: `basic`, `strict`, `regulated`.
- Context profiles: `research`, `production`, `regulated`.
- Governance passport metadata embedded in blob.
- Full replay execution for recorded execute events.
- Signed audit artifacts:
  - HMAC signing/verification
  - KMS-HTTP signing/verification hooks
- Remote attestation hooks:
  - no-op local provider
  - HTTP endpoint provider

## Quickstart

```bash
pip install -e .
aesdk init --pap docs/examples/did_min_wage/pap.yaml --context production --conformance strict --policy-version 1.2.0
aesdk validate --pap docs/examples/did_min_wage/pap.yaml --proposal docs/examples/did_min_wage/proposal_blocked.json --conformance strict
aesdk reproduce --blob docs/examples/did_min_wage/.aesdk.json --replay
```

## Signed audits

```bash
aesdk audit sign --blob docs/examples/regulated_profile/.aesdk.json --mode hmac --secret your-secret --key-id local
aesdk audit verify-signature --blob docs/examples/regulated_profile/.aesdk.json --signature docs/examples/regulated_profile/.aesdk.json.sig.json --secret your-secret
```

## KMS-HTTP signing integration

```bash
aesdk audit sign --blob docs/examples/regulated_profile/.aesdk.json --mode kms-http --kms-endpoint https://kms.example --key-id key-1 --kms-token TOKEN
aesdk audit verify-signature --blob docs/examples/regulated_profile/.aesdk.json --signature docs/examples/regulated_profile/.aesdk.json.sig.json --kms-endpoint https://kms.example --kms-token TOKEN
```

## Docs

- Functionality: `docs/PROJECT_FUNCTIONALITY.md`
- Security: `SECURITY.md`
- Release checklist: `docs/RELEASE_CHECKLIST.md`
