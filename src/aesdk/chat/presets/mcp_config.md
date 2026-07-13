# Connect AESDK to Claude as an MCP connector

This lets Claude (in a chat window) run AESDK's real checks. The server runs
locally on your machine, so your data never leaves it.

## The easy way: two commands

```bash
python -m pip install "aesdk[mcp]"   # install the MCP tools
aesdk connect-claude                 # edit Claude Desktop's config for you
```

`aesdk connect-claude` finds `claude_desktop_config.json`, adds AESDK without
touching any other connectors, and backs up the previous file. Add `--dry-run`
to preview first. Then fully quit and reopen Claude Desktop.

## The manual way (if you prefer to edit the file yourself)

Open Claude Desktop's Settings -> Developer -> Edit Config
(`claude_desktop_config.json`), add the `aesdk` entry, then restart:

```json
{
  "mcpServers": {
    "aesdk": {
      "command": "python",
      "args": ["-m", "aesdk", "mcp"]
    }
  }
}
```

`aesdk mcp` starts the server directly if you want to confirm it runs (Ctrl+C to
stop); normally Claude launches it for you.

## claude.ai custom connector

In claude.ai, add a custom connector pointing at an AESDK MCP endpoint your
team hosts. Because econometrics data is often confidential, prefer the local
Claude Desktop setup above unless your organization runs a trusted internal host.

## What Claude can then do

Once connected, Claude can call these AESDK tools during a chat:

- `list_methods` - the econometric methods AESDK guides
- `method_context` - the guardrails for a chosen method
- `preflight` - validate a pre-analysis plan and proposal (real pass/warn/block)
- `scan_data` - cross-check a local dataset against the declared plan
- `check_ols` - the Wooldridge ten-item OLS assumption checklist on local data

Ask Claude to "use AESDK to check my design before we write code," describe your
study, and it will run these for you and explain the results in plain language.
Code execution is intentionally not exposed over MCP: you get the guardrails and
diagnostics in chat, while governed execution stays in the AESDK CLI.
