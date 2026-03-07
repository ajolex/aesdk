---

## The Human-Primacy Principle

> *"A chainsaw in the hands of a master carpenter and a chainsaw in the hands
> of someone who has never built anything produce very different results."*
> — John List, Distinguished Service Professor, University of Chicago

AESDK is built on an explicit human-primacy architecture. This is not a philosophical
preference — it is a structural design constraint enforced throughout the SDK.

### What This Means in Practice

| Layer | How Human Primacy Is Enforced |
|---|---|
| **Protocol** | PAP must be written by the researcher, not the agent. The agent cannot self-register a PAP. |
| **Overrides** | No PAP deviation is auto-approved. All overrides require researcher acknowledgment. |
| **Citations** | Hallucinated citations are a blocking error. The agent cannot insert unverified references. |
| **Reasoning Logs** | The "Why Hook" forces the agent to explain its reasoning to the researcher, not to itself. |
| **Sandbox** | The researcher sees diagnostics before results. The agent does not decide what counts as "good enough." |
| **SCA** | The researcher specifies which dimensions to vary. The agent cannot silently expand or narrow the curve. |

### The "Nearly Right" Problem

As observed in real-world deployments (List, 2025-2026): LLMs frequently produce outputs
that are *nearly right* — plausible-sounding, superficially correct, but subtly wrong in
ways that require deep domain expertise to detect.

In econometrics, "nearly right" is catastrophic:
- A nearly right clustering decision produces anticonservative standard errors
- A nearly right instrument produces a biased 2SLS estimate
- A nearly right parallel trends plot conceals a violated identifying assumption
- A hallucinated citation poisons the entire literature review

AESDK's response: every layer of the SDK is designed to surface "nearly right" failures
to the researcher explicitly, with textbook-grounded explanations of *why* it is wrong,
not just *that* it is wrong.

### What AESDK Is Not

AESDK is not an autonomous research agent. It does not:
- Write papers
- Choose identification strategies
- Decide what counts as a robust result
- Approve its own overrides

The researcher is the master carpenter. AESDK is the chainsaw with a safety guard.