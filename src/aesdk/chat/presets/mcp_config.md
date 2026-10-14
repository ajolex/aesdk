# Connect AESDK to Claude as an MCP connector

This lets Claude (in a chat window) run AESDK's real checks. The server runs
locally on your machine, so your data never leaves it.

**Run these on your own computer** (a local terminal), NOT inside a web chat's
code tool. The claude.ai web sandbox is a temporary container that has no Claude
Desktop and is wiped between sessions, so setting up there connects nothing real.

## The easiest way: one file (Claude Desktop extension)

Ask whoever maintains AESDK for your team for `aesdk.mcpb` (they create it with
`aesdk mcpb`), then double-click it, or drag it into Claude Desktop's
Settings -> Extensions. Claude Desktop installs AESDK for you; there is nothing
else to set up.

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

## Claude Code

Install the AESDK plugin (`/plugin marketplace add ajolex/aesdk`, then
`/plugin install aesdk@aesdk`) or run `claude mcp add aesdk -- aesdk mcp`.

## claude.ai custom connector (hosted)

Your team can host AESDK with `aesdk mcp --transport streamable-http --host
0.0.0.0 --port 8000` behind its own authentication, then add that URL as a
custom connector in claude.ai. Because econometrics data is often
confidential, prefer the local Claude Desktop setup above unless your
organization runs a trusted internal host.

## What Claude can then do

Once connected, Claude can call these AESDK tools during a chat:

- `list_methods` - the econometric methods AESDK guides
- `method_context` - the guardrails for a chosen method
- `draft_plan` - draft a pre-analysis plan from your description (asks you for
  missing column names when Claude supports it)
- `preflight` - validate a pre-analysis plan and proposal (real pass/warn/block)
- `scan_data` - cross-check a local dataset against the declared plan
- `check_ols` - the Wooldridge ten-item OLS assumption checklist on local data
- `prepare_record`, `workflow_report`, `ai_passport` - save the audit record,
  a supervisor-readable report, and the AI Replicability Passport in a project
  folder

The checking tools are marked read-only, so Claude can run them without asking
each time. AESDK also offers method guardrails as resources
(`aesdk://methods/did`) and a "design review" prompt.

Ask Claude to "use AESDK to check my design before we write code," describe your
study, and it will run these for you and explain the results in plain language.
Code execution is intentionally not exposed over MCP: you get the guardrails and
diagnostics in chat, while governed execution stays in the AESDK CLI.
