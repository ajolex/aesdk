# AESDK Instructions For Claude

When asked to write econometric analysis code, use AESDK first.

- Load method guidance with `aesdk agent context --method <method>`.
- Run preflight with `aesdk agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict`.
- A `block` result is a hard stop.
- A `warn` result requires researcher review.
- Do not invent assumptions, diagnostics, citations, or estimator requirements.
- Explain AESDK results in plain language for economics RAs and faculty.
