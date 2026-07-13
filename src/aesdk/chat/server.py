"""AESDK Model Context Protocol (MCP) server.

Exposes AESDK's *checking* tools (method context, preflight, data scan, OLS
assumption checklist) to MCP-capable chat clients such as Claude Desktop,
claude.ai custom connectors, and MCP-enabled ChatGPT. This lets researchers get
real pass/warn/block guardrails from inside a chat window instead of a terminal.

It deliberately does NOT expose code execution: chat clients get the guardrails
and diagnostics, not a way to run arbitrary analysis code. Governed execution
stays in the CLI/agent workflow.

The `mcp` package is an optional dependency. Install it with
`pip install aesdk[mcp]`. If it is missing, `build_server()` raises a clear,
actionable error.
"""

from __future__ import annotations

from typing import Any

from aesdk.chat import tools


def _require_mcp():
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised only without the extra
        raise RuntimeError(
            "The AESDK MCP server needs the optional 'mcp' package. "
            "Install it with: pip install aesdk[mcp]"
        ) from exc
    return FastMCP


def build_server():
    """Construct the FastMCP server with AESDK's checking tools registered."""
    FastMCP = _require_mcp()
    server = FastMCP("aesdk")

    @server.tool()
    def list_methods() -> list[dict[str, Any]]:
        """List the econometric methods AESDK can guide (id and display name)."""
        return tools.list_methods()

    @server.tool()
    def method_context(method: str, depth: str = "protocol") -> str:
        """Return AESDK's guardrail context for a method (depth: protocol|full)."""
        return tools.method_context(method, depth=depth)

    @server.tool()
    def preflight(
        method: str,
        pap_yaml: str,
        proposal_json: str = "",
        conformance: str = "strict",
        data_path: str = "",
    ) -> dict[str, Any]:
        """Validate a pre-analysis plan (YAML) and proposal (JSON) and return
        pass/warn/block with plain-language guidance. If data_path is a readable
        local file, the data-aware checks run too."""
        return tools.preflight(
            method=method,
            pap_yaml=pap_yaml,
            proposal=proposal_json or None,
            conformance=conformance,
            data_path=data_path or None,
        )

    @server.tool()
    def scan_data(method: str, pap_yaml: str, data_path: str, conformance: str = "strict") -> dict[str, Any]:
        """Read a local dataset and cross-check the declared PAP structure against it."""
        return tools.scan_data(method=method, pap_yaml=pap_yaml, data_path=data_path, conformance=conformance)

    @server.tool()
    def check_ols(pap_yaml: str, data_path: str) -> dict[str, Any]:
        """Fit the declared OLS model on a local dataset and return the Wooldridge
        ten-item assumption checklist."""
        return tools.check_ols(pap_yaml=pap_yaml, data_path=data_path)

    return server


def run(transport: str = "stdio") -> None:
    """Run the AESDK MCP server (default stdio transport for local connectors)."""
    build_server().run(transport=transport)
