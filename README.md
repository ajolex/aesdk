# Agentic Econometrics SDK (AESDK)

AESDK is an enforcement-first SDK for LLM-assisted econometric work. It blocks invalid actions, requires a valid Pre-Analysis Plan (PAP), and writes an append-only replication blob (`.aesdk.json`) for reproducibility.

## Quickstart

```bash
pip install -e .
aesdk init --pap docs/examples/did_min_wage/pap.yaml
aesdk validate --pap docs/examples/did_min_wage/pap.yaml --proposal docs/examples/did_min_wage/proposal_blocked.json
aesdk reproduce --blob docs/examples/did_min_wage/.aesdk.json
```

## PAP example

See [docs/examples/did_min_wage/pap.yaml](docs/examples/did_min_wage/pap.yaml) for a complete panel DiD PAP with clustered SE at state level.

## Blocked DiD example

The example proposal intentionally violates two governance rules:
- `W-PANEL-001` (Wooldridge): panel models must use clustered/stronger SEs, but proposal uses `HC3`.
- `AP-DID-003` (Callaway & Sant'Anna, 2021): staggered adoption blocks TWFE.

Expected output from `aesdk validate` includes each rule id, severity, and citation.

## Reproducing from blob

Use:

```bash
aesdk reproduce --blob .aesdk.json
```

MVP behavior verifies the hash chain and prints events in append order.

## Citation integrity (MVP)

`aesdk cite verify --text <file-or->` detects DOI format and can optionally check DOI reachability online.

```bash
aesdk cite verify --text README.md
aesdk cite verify --text README.md --online
```
