"""AESDK Model Context Protocol (MCP) server.

Exposes AESDK's checking tools to MCP clients (Claude Desktop, Claude Code,
claude.ai custom connectors, and other MCP-capable assistants) so researchers
get real pass/warn/block guardrails inside a chat window.

What the server offers:

- **Tools** with typed, structured output and MCP tool annotations. Checking
  tools are marked read-only so clients can run them without a confirmation
  prompt; the few tools that write project files (audit record, report, AI
  passport) are marked as non-destructive writes.
- **Resources** for method guardrails (``aesdk://methods/{method_id}``), the
  full method reference, and the AESDK workflow.
- **Prompts** for a design review and a plain-language results explanation.
- **Elicitation**: when a plan is being drafted without the outcome,
  treatment, unit, or time variable, the server asks the researcher directly
  (when the client supports it) instead of guessing.

It deliberately does NOT expose code execution: chat gets guardrails and
diagnostics; governed execution stays in the CLI/agent workflow.

The ``mcp`` package is an optional dependency (``pip install "aesdk[mcp]"``).
Both the 1.x SDK (``FastMCP``) and the 2.x SDK (``MCPServer``) are supported.
"""

# No ``from __future__ import annotations`` here: the MCP SDK reads tool
# signatures at registration time, and the output models and Context class are
# defined inside build_server(), so annotations must be evaluated eagerly.

from typing import Any

from aesdk.chat import tools

SERVER_INSTRUCTIONS = (
    "AESDK checks econometric analysis plans before code is written. Call method_context for the "
    "method's guardrails, draft_plan to turn a description into a pre-analysis plan and proposal, "
    "then preflight for the pass/warn/block verdict (pass data_path for a local dataset). A block is a "
    "hard stop; a warning needs the researcher's explicit go-ahead. Explain findings in plain research "
    "language: the concern, why it matters, and the fix. AESDK does not prove a design is correct."
)

READ_ONLY = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
WRITES_PROJECT_FILES = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}


def _require_mcp() -> "tuple[Any, Any, Any]":
    """Return ``(ServerClass, ContextClass, ToolAnnotations)`` for the installed SDK."""

    try:
        from mcp.types import ToolAnnotations  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised only without the extra
        raise RuntimeError(
            "The AESDK MCP server needs the optional 'mcp' package. "
            'Install it with: pip install "aesdk[mcp]"'
        ) from exc
    try:  # MCP Python SDK 2.x
        from mcp.server.mcpserver import Context, MCPServer  # type: ignore

        return MCPServer, Context, ToolAnnotations
    except Exception:
        pass
    try:  # MCP Python SDK 1.x
        from mcp.server.fastmcp import Context, FastMCP  # type: ignore

        return FastMCP, Context, ToolAnnotations
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "The installed 'mcp' package has neither MCPServer (2.x) nor FastMCP (1.x). "
            'Reinstall it with: pip install --upgrade "aesdk[mcp]"'
        ) from exc


def _models():
    """Pydantic models that give each tool a typed output schema."""

    from pydantic import BaseModel, Field

    class MethodInfo(BaseModel):
        method_id: str
        name: str | None = None

    class MethodList(BaseModel):
        methods: list[MethodInfo]

    class Violation(BaseModel):
        rule_id: str
        severity: str = Field(description="block, warn, or info")
        message: str
        guidance: str | None = None

    class PreflightVerdict(BaseModel):
        method_id: str
        status: str = Field(description="pass, warn, or block")
        blocked: bool
        violations: list[Violation]
        explanation: str
        data_scan: dict[str, Any] | None = None

    class DataScan(BaseModel):
        scanned: bool | None = None
        status: str | None = None
        findings: list[dict[str, Any]] = Field(default_factory=list)
        profile: dict[str, Any] = Field(default_factory=dict)
        notes: list[str] = Field(default_factory=list)

    class OLSChecklist(BaseModel):
        fitted: bool
        ols_assumptions: dict[str, Any] | None = None
        findings: list[dict[str, Any]] = Field(default_factory=list)

    class DraftedPlan(BaseModel):
        method_id: str
        pap_yaml: str = Field(description="Draft pre-analysis plan; the researcher must review it.")
        proposal_json: str
        missing: list[str] = Field(description="Facts still needed from the researcher.")
        note: str

    class WrittenFile(BaseModel):
        path: str
        status: str | None = None
        blocked: bool | None = None
        detail: str | None = None

    class MissingDesignFacts(BaseModel):
        outcome: str = Field(default="", description="Outcome variable (column name)")
        treatment: str = Field(default="", description="Treatment or exposure variable (column name)")
        unit: str = Field(default="", description="Unit identifier, e.g. county or student id")
        time: str = Field(default="", description="Time variable, e.g. year (blank for cross-sections)")

    return {
        "MethodInfo": MethodInfo,
        "MethodList": MethodList,
        "Violation": Violation,
        "PreflightVerdict": PreflightVerdict,
        "DataScan": DataScan,
        "OLSChecklist": OLSChecklist,
        "DraftedPlan": DraftedPlan,
        "WrittenFile": WrittenFile,
        "MissingDesignFacts": MissingDesignFacts,
    }


def build_server():
    """Construct the MCP server with AESDK's tools, resources, and prompts."""

    ServerClass, Context, ToolAnnotations = _require_mcp()
    m = _models()
    MethodList, PreflightVerdict, DataScan = m["MethodList"], m["PreflightVerdict"], m["DataScan"]
    OLSChecklist, DraftedPlan, WrittenFile = m["OLSChecklist"], m["DraftedPlan"], m["WrittenFile"]
    MissingDesignFacts = m["MissingDesignFacts"]

    from aesdk._version import __version__

    try:
        server = ServerClass("aesdk", instructions=SERVER_INSTRUCTIONS, version=__version__)
    except TypeError:  # 1.x FastMCP has no version kwarg
        server = ServerClass("aesdk", instructions=SERVER_INSTRUCTIONS)

    read_only = ToolAnnotations(**READ_ONLY)
    writes = ToolAnnotations(**WRITES_PROJECT_FILES)

    # ------------------------------------------------------------------ tools

    @server.tool(title="List econometric methods", annotations=read_only)
    def list_methods() -> MethodList:
        """List the econometric methods AESDK can guide (id and display name)."""
        return MethodList.model_validate({"methods": tools.list_methods()})

    @server.tool(title="Method guardrails", annotations=read_only)
    def method_context(method: str, depth: str = "protocol") -> str:
        """Return AESDK's guardrail context for a method as markdown (depth: protocol|full)."""
        return tools.method_context(method, depth=depth)

    @server.tool(title="Draft an analysis plan", annotations=read_only)
    async def draft_plan(
        ctx: Context,
        method: str,
        goal: str,
        outcome: str = "",
        treatment: str = "",
        unit: str = "",
        time: str = "",
        covariates: list[str] | None = None,
        data_path: str = "",
    ) -> DraftedPlan:
        """Draft a reviewable pre-analysis plan (YAML) and proposal (JSON) from a plain description.

        If key design facts are missing, the researcher is asked directly when the client supports
        it; otherwise they are listed in `missing` so the assistant can ask.
        """
        facts = {"outcome": outcome, "treatment": treatment, "unit": unit, "time": time}
        if not (outcome and treatment):
            facts = await _elicit_missing(ctx, MissingDesignFacts, facts)
        result = tools.draft_plan(
            method=method,
            goal=goal,
            covariates=covariates or [],
            data_path=data_path or None,
            **facts,
        )
        return DraftedPlan.model_validate(result)

    @server.tool(title="Methods check (preflight)", annotations=read_only)
    def preflight(
        method: str,
        pap_yaml: str,
        proposal_json: str = "",
        conformance: str = "strict",
        data_path: str = "",
    ) -> PreflightVerdict:
        """Validate a pre-analysis plan (YAML) and proposal (JSON) and return pass/warn/block with
        plain-language guidance. If data_path is a readable local file, the data-aware checks run too."""
        return PreflightVerdict.model_validate(
            tools.preflight(
                method=method,
                pap_yaml=pap_yaml,
                proposal=proposal_json or None,
                conformance=conformance,
                data_path=data_path or None,
            )
        )

    @server.tool(title="Scan a dataset against the plan", annotations=read_only)
    def scan_data(method: str, pap_yaml: str, data_path: str, conformance: str = "strict") -> DataScan:
        """Read a local dataset and cross-check the declared PAP structure against it."""
        return DataScan.model_validate(
            tools.scan_data(method=method, pap_yaml=pap_yaml, data_path=data_path, conformance=conformance)
        )

    @server.tool(title="OLS assumption checklist", annotations=read_only)
    def check_ols(pap_yaml: str, data_path: str) -> OLSChecklist:
        """Fit the declared OLS model on a local dataset and return the Wooldridge ten-item checklist."""
        return OLSChecklist.model_validate(tools.check_ols(pap_yaml=pap_yaml, data_path=data_path))

    @server.tool(title="Save the audit record", annotations=writes)
    def prepare_record(method: str, pap_yaml: str, proposal_json: str, project_dir: str) -> WrittenFile:
        """Save pap.yaml, proposal.json, and the .aesdk.json audit record in a local project folder,
        and record the methods-check verdict. Does not run any analysis code."""
        return WrittenFile.model_validate(
            tools.prepare_record(method=method, pap_yaml=pap_yaml, proposal_json=proposal_json, project_dir=project_dir)
        )

    @server.tool(title="Workflow report", annotations=writes)
    def workflow_report(project_dir: str) -> WrittenFile:
        """Write workflow.html, a supervisor-readable summary of the project's .aesdk.json record."""
        return WrittenFile.model_validate(tools.workflow_report(project_dir=project_dir))

    @server.tool(title="AI Replicability Passport", annotations=writes)
    def ai_passport(project_dir: str) -> WrittenFile:
        """Write ai.lock.json from the ai_use block in the project's pap.yaml/proposal.json, including
        any archived agent sessions in .aesdk/sessions."""
        return WrittenFile.model_validate(tools.ai_passport(project_dir=project_dir))

    # -------------------------------------------------------------- resources

    @server.resource("aesdk://methods", name="methods", title="AESDK methods", mime_type="application/json")
    def methods_resource() -> str:
        import json

        return json.dumps(tools.list_methods(), indent=2)

    @server.resource(
        "aesdk://methods/{method_id}",
        name="method-guardrails",
        title="Method guardrails",
        mime_type="text/markdown",
    )
    def method_resource(method_id: str) -> str:
        return tools.method_context(method_id, depth="protocol")

    @server.resource(
        "aesdk://methods/{method_id}/reference",
        name="method-reference",
        title="Method reference (decision tree, failure modes, recipes)",
        mime_type="text/markdown",
    )
    def method_reference_resource(method_id: str) -> str:
        return tools.method_context(method_id, depth="full")

    @server.resource("aesdk://workflow", name="workflow", title="AESDK workflow", mime_type="text/markdown")
    def workflow_resource() -> str:
        from aesdk.agent.skills import render_workflow_skill

        return render_workflow_skill().split("---\n", 2)[-1]

    # ---------------------------------------------------------------- prompts

    @server.prompt(title="Econometric design review")
    def design_review(description: str, method: str = "") -> str:
        """Review a study design with AESDK before any analysis code is written."""
        method_hint = f" The researcher believes the method is `{method}`." if method else ""
        return (
            "Review this study design with AESDK before any analysis code is written."
            f"{method_hint}\n\nStudy description:\n{description}\n\n"
            "1. Identify and confirm the econometric method in plain language.\n"
            "2. Call method_context, then draft_plan, then preflight (with data_path if a local dataset exists).\n"
            "3. Explain each issue like a careful senior RA: the concern, why it matters, and the fix.\n"
            "4. Treat a block as a hard stop and a warning as needing the researcher's go-ahead.\n"
            "Do not invent assumptions, diagnostics, or citations."
        )

    @server.prompt(title="Explain an AESDK result")
    def explain_result(result_json: str) -> str:
        """Turn an AESDK preflight result into a plain-language explanation for a researcher."""
        return (
            "Explain this AESDK result to a researcher who does not read JSON. Lead with the verdict "
            "(pass, needs attention, or stop), then each issue in one or two plain sentences: the concern, "
            "why it matters, and the fix. Mention rule ids only in parentheses.\n\n" + result_json
        )

    return server


async def _elicit_missing(ctx: Any, schema: Any, facts: dict[str, str]) -> dict[str, str]:
    """Ask the researcher for missing design facts; fall back silently if unsupported."""

    try:
        answer = await ctx.elicit(
            message=(
                "To draft the analysis plan, AESDK needs a few facts about your data. "
                "Please give the column names (leave blank if not applicable)."
            ),
            schema=schema,
        )
    except Exception:
        return facts
    if getattr(answer, "action", None) != "accept" or getattr(answer, "data", None) is None:
        return facts
    data = answer.data.model_dump() if hasattr(answer.data, "model_dump") else dict(answer.data)
    return {key: facts.get(key) or str(data.get(key) or "") for key in facts}


def run(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the AESDK MCP server.

    ``stdio`` (default) is for local connectors such as Claude Desktop and
    Claude Code. ``streamable-http`` serves an organization-hosted endpoint;
    it binds to localhost unless ``host`` is set, because the data tools read
    local files.
    """

    server = build_server()
    if transport == "stdio":
        server.run(transport="stdio")
        return
    if transport not in {"streamable-http", "sse"}:
        raise ValueError("transport must be stdio, streamable-http, or sse")
    settings = getattr(server, "settings", None)
    if settings is not None and hasattr(settings, "host"):  # 1.x reads host/port from settings
        settings.host = host
        settings.port = port
        server.run(transport=transport)
    else:  # 2.x takes them as run() keyword arguments
        server.run(transport=transport, host=host, port=port)


__all__ = ["READ_ONLY", "SERVER_INSTRUCTIONS", "WRITES_PROJECT_FILES", "build_server", "run"]
