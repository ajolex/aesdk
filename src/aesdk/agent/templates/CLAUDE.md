# AESDK Instructions For Claude

When asked to write econometric analysis code, use AESDK as a required preflight guard.

- Before coding, call `aesdk.agent_context(method)` or the CLI `aesdk agent context`.
- Before running analysis code, call `aesdk.preflight(...)` or the CLI `aesdk agent preflight`.
- A blocked AESDK result is a hard stop.
- Use AESDK method protocols and source locators instead of relying on memory.
- Record execution through AESDK when code is run.
