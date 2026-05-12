# CLAUDE.md

## AESDK Instructions For Claude

When helping with econometric analysis in this repository, use AESDK as a required preflight guard. The likely user is an economics RA, professor, or applied researcher, not a software engineer.

## Required Workflow

Before writing or running analysis code:

1. Identify the method: `ols_cef`, `iv_2sls`, `panel_fe`, `did`, or `rdd`.
2. Load method guidance:

```bash
aesdk agent context --method <method>
```

3. Run preflight when a PAP and proposal are available:

```bash
aesdk agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict
```

4. If AESDK returns `block`, stop and explain the violated assumption or rule.
5. If AESDK returns `warn`, explain what the researcher must review.
6. Use governed execution when running code:

```bash
aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json --code-file analysis.py
```

## Tone

Explain issues like a careful senior RA:

- clear
- specific
- not overly technical
- honest about what AESDK can and cannot verify

Do not present AESDK as proving a research design is correct. AESDK checks that the proposed workflow follows documented econometric guardrails.
