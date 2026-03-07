# AESDK — MVP Roadmap & Milestone Summary

## Recommended Build Order

| Phase | Module | MVP Priority | Est. Complexity |
|---|---|---|---|
| 1 | `aesdk.protocol` — PAP validation, state machine, rule registry | 🔴 Core | High |
| 2 | `aesdk.trace` / `aesdk.reproduce` — Replication Blob, Why Hook | 🔴 Core | Medium |
| 3 | `aesdk.sandbox` — Isolated execution, econometric diagnostics | 🔴 Core | High |
| 4 | `aesdk.curve` — Specification Curve Automation | 🟡 Differentiator | High |
| 5 | `aesdk.plugins` — Extension architecture, community | 🟢 Ecosystem | Medium |

---

## MVP Definition (Phases 1–3)

The MVP is complete when a researcher can:
1. Write a `.pap.yaml` file and have the SDK validate it against a governance rule set
2. Have an agent propose a DiD model and receive a pass/block/override decision with a textbook citation
3. Have that model execute in a sandboxed environment with automatic diagnostic checks
4. Receive a portable `.aesdk.json` Replication Blob that a third party can replay

**Stretch goal for MVP:** A working specification curve for the replayed workflow.

---

## Suggested Tech Stack

| Component | Choice | Rationale |
|---|---|---|
| Core SDK | Python 3.11+ | Dominant in econometrics + ML |
| PAP/Rule Schema | YAML + JSON Schema (pydantic) | Human-readable + validated |
| Sandbox | Docker (primary), venv (fallback) | Reproducibility |
| Econometrics | `statsmodels`, `linearmodels`, `pyfixest` | Best-in-class for Python |
| Async Execution | `asyncio` + `concurrent.futures` | Parallel SCA runs |
| LLM Layer | `openai`, `anthropic` SDK + adapter pattern | Swappable |
| Tracing | Append-only JSON + SHA256 hash | Tamper-evident |
| CLI | `typer` or `click` | Ergonomic, testable |
| Plotting | `matplotlib` + `plotly` | Static + interactive |
| Testing | `pytest` + `hypothesis` | Property-based tests for validators |

---

## Governance First Principle

> **No rule ships without a citation. No citation ships without a test.**

Every validator in the governance rule registry must:
- Be traceable to a specific textbook, chapter, and equation/page
- Have a unit test that demonstrates the pass and fail condition
- Be tagged with a severity level (`error`, `warning`, `info`)

This is what differentiates AESDK from a prompt template library.

---

## Open Questions for Design Decisions

1. **PAP Registration:** Should the SDK support on-chain or timestamped PAP registration
   (e.g., OSF pre-registration API) for stronger anti-p-hacking guarantees?
2. **Multi-Agent:** Should the SDK support multi-agent flows (e.g., one agent proposes,
   a "critic agent" validates, a "reviewer agent" writes the reasoning log)?
3. **DAG Integration:** Should identification strategy validation include DAG-based
   checks (using `pgmpy` or `dowhy`) for confounder detection per Hernan & Robins?
4. **R/Stata Bridge:** Should `aesdk.sandbox` support execution of R or Stata code
   (via `rpy2` or subprocess) for cross-language reproducibility?
5. **Journal Integration:** Should `aesdk.reproduce` be able to verify a Replication Blob
   against a published paper's stated specification (journal-partnership model)?