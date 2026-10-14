# Contributing to AESDK

## Development setup

```bash
python -m pip install -e ".[dev,mcp,llm]"
pre-commit install          # optional: ruff + plugin/knowledge checks on commit
```

## Before you push

```bash
ruff check src tests
python -m pytest -q
python -m aesdk methods validate
python scripts/build_plugin.py   # if you changed method packs, hooks, or Claude templates
```

`tests/unit/agent/test_skills_and_plugin.py` fails if `plugins/aesdk` is out of
date with the package, so regenerate it rather than editing it by hand.

## Where things live

- `src/aesdk/knowledge/packs/*.yaml` and `src/aesdk/governance/rules/*.yaml`:
  econometric guidance and executable rules. Every pack needs matching rule
  coverage and tests.
- `src/aesdk/agent/`: the agent-facing API: intake, preflight, run, report, AI
  passport, hooks (`hooks.py`), transcripts, skills, Claude Code integration.
- `src/aesdk/chat/`: MCP server (supports MCP SDK 1.x and 2.x), chat presets,
  MCP Bundle builder.
- `src/aesdk/llm/`: provider adapters and the `ResearchLLM` archive for
  AI-derived variables.
- `plugins/aesdk` and `.claude-plugin/marketplace.json`: the generated Claude
  Code plugin and its marketplace.
- `evals/`: end-to-end checks that a real coding agent follows AESDK.

## Conventions

- Organize guidance by econometric method/topic; sources are evidence, not file
  identity.
- Agent-facing text is written for researchers who are not programmers: plain
  language, no raw JSON, concern -> why it matters -> fix.
- Do not invent citations. `aesdk cite verify` checks DOIs.
- Record notable changes in `AI_MEMORY.md` (issue, resolution, implications,
  lessons).
