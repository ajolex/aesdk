"""AESDK package."""

from ._version import __version__
from .agent import (
    AgentContext,
    AIPassportResult,
    AnalysisRunResult,
    IntakeResult,
    PreflightResult,
    RuntimeMetadataResult,
    agent_context,
    build_ai_passport,
    draft_pap,
    intake_task,
    preflight,
    run_analysis,
    write_ai_passport,
    write_claude_runtime_metadata,
    write_codex_runtime_metadata,
    write_copilot_runtime_metadata,
    write_workflow_report,
)
from .knowledge import get_knowledge_pack

__all__ = [
    "AgentContext",
    "AIPassportResult",
    "AnalysisRunResult",
    "IntakeResult",
    "PreflightResult",
    "RuntimeMetadataResult",
    "__version__",
    "agent_context",
    "build_ai_passport",
    "draft_pap",
    "get_knowledge_pack",
    "intake_task",
    "preflight",
    "run_analysis",
    "write_ai_passport",
    "write_claude_runtime_metadata",
    "write_codex_runtime_metadata",
    "write_copilot_runtime_metadata",
    "write_workflow_report",
]
