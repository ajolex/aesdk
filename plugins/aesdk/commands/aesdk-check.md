---
description: Run the AESDK econometrics methods check on this project's analysis plan and explain the result in plain language.
argument-hint: "[method id, e.g. did, iv_2sls, experimental_rct]"
---

Run the AESDK methods check for this project. Method (may be empty): $ARGUMENTS

1. If there is no `pap.yaml`/`proposal.json` yet, ask the researcher to describe
   the analysis in a sentence or two, then draft them with `aesdk agent intake
   --prompt "<their words>" --method <method> --output-dir .`.
2. Run `aesdk agent prepare --method <method> --pap pap.yaml --proposal
   proposal.json --output-dir .` and then `aesdk agent preflight --method
   <method> --pap pap.yaml --proposal proposal.json --conformance strict`.
3. Explain the verdict like a careful senior RA: for each issue, the concern, why
   it matters, and the fix. A block is a hard stop; a warning needs the
   researcher's explicit go-ahead. Do not dump raw output.
