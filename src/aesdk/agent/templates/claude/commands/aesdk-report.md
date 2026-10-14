---
description: Build the shareable AESDK workflow report (and AI passport when AI was used) for supervisors and reviewers.
---

1. Run `aesdk agent report --blob .aesdk.json --output workflow.html`.
2. If the plan or proposal declares `ai_use`, archive this session with
   `aesdk agent capture-session` and write the passport with `aesdk agent
   ai-passport --pap pap.yaml --proposal proposal.json --output ai.lock.json`.
   Do not mark `human_reviewed: true` unless a person actually reviewed the work.
3. Tell the researcher, in two or three plain sentences, what the report shows and
   where the files are.
