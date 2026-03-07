# Phase 2 — Replication Trace (`aesdk.trace`, `aesdk.reproduce`)

**Goal:** Make every agentic econometric workflow fully reproducible by a third party
using only the Replication Blob. No black boxes.

---

## 2.1 The Replication Blob (`.aesdk.json`)

Every project produces a single, append-only Replication Blob. It is portable,
human-readable, and machine-replayable.

```json
{
  "blob_version": "1.0.0",
  "project_id": "proj_001",
  "pap_hash": "sha256:abc123...",
  "environment": {
    "python_version": "3.11.7",
    "aesdk_version": "0.3.1",
    "llm_provider": "openai",
    "llm_model": "gpt-4o",
    "llm_version_date": "2025-11",
    "package_hashes": {
      "statsmodels": "0.14.1",
      "linearmodels": "6.0",
      "pandas": "2.1.4"
    }
  },
  "events": [
    {
      "event_id": "evt_001",
      "timestamp": "2026-03-05T14:23:11Z",
      "type": "model_proposal",
      "system_prompt": "...",
      "user_prompt": "Run a DiD on treatment group",
      "llm_seed": 42,
      "llm_temperature": 0.0,
      "raw_output": "...",
      "validation_result": {
        "status": "pass",
        "rules_triggered": []
      },
      "reasoning_log": {
        "summary": "DiD chosen per PAP Section 3. Clustering at state level per W-PANEL-001.",
        "changes": []
      }
    },
    {
      "event_id": "evt_002",
      "type": "code_change",
      "diff": "--- a/analysis.py\n+++ b/analysis.py\n@@ -12,3 +12,3 @@...",
      "reasoning_log": {
        "summary": "Switched from two-way to stacked DiD per Callaway & Sant'Anna (2021) 
                    due to staggered adoption detected in data.",
        "triggered_by": "sandbox_check",
        "override": null
      }
    }
  ]
}
```

**Key design principles:**
- `llm_seed` and `llm_temperature=0.0` are required for deterministic replay
- `pap_hash` links the blob to the exact registered PAP
- All diffs are stored, never overwritten

---

## 2.2 The "Why" Hook — Reasoning Log

Every code change or model modification triggers a mandatory structured reasoning entry.
The agent is prompted by the SDK (not left to volunteer reasoning):

```
SDK PROMPT TO AGENT:
"You have modified the regression specification. Before proceeding, you must provide a 
structured Reasoning Log entry:
1. What changed and why?
2. Which PAP section authorizes this change, or is this an override?
3. Which econometric principle or textbook rule supports this choice?
Respond in JSON format matching the ReasoningLog schema."
```

---

## 2.3 `aesdk.reproduce` — CLI Replication Tool

```bash
# Replay a full agentic workflow from a blob
aesdk reproduce --blob ./collab_study.aesdk.json --output ./replay_output/

# Check for specification drift
aesdk reproduce --blob ./collab_study.aesdk.json --compare ./my_output/ --epsilon 0.05
```

**Drift detection logic:**
- Coefficient drift: Is replicated `β` within `ε` of original? Flag if |Δβ/SE| > 1.96
- Distribution drift: KS-test on residual distributions
- Significance drift: Did any result cross p=0.05 boundary?
- Output: `drift_report.yaml` with per-event comparison

---

## 2.4 Task Checklist

- [ ] Define `.aesdk.json` schema with JSON Schema validation
- [ ] Implement `aesdk.trace.TraceCollector` (wraps all LLM API calls)
- [ ] Implement "Why" Hook: mandatory reasoning prompt injected on code change
- [ ] Implement `ReasoningLog` schema and validator
- [ ] Build `aesdk reproduce` CLI with drift detection
- [ ] Drift metrics: coefficient comparison, KS-test, significance boundary crossing
- [ ] Blob diff viewer: `aesdk diff blob1.aesdk.json blob2.aesdk.json`
- [ ] Integration tests: reproduce known-good workflow, detect injected drift

---

## 2.5 Review Criteria
- Does the blob contain everything needed to replay the workflow cold?
- Is reasoning mandatory and structured (not free-text)?
- Does the reproduce CLI correctly flag coefficient and distribution drift?
- Are LLM seeds enforced at `temperature=0.0`?