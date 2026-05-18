"""Agent-facing AESDK convenience API."""

from .ai_passport import AIPassportResult, build_ai_passport, build_ai_passport_summary, write_ai_passport
from .context import AgentContext, agent_context
from .intake import IntakeResult, intake_prompt, intake_task
from .pap_draft import draft_pap
from .prepare import PrepareResult, prepare
from .preflight import PreflightResult, preflight
from .report import write_workflow_report
from .review import InteractionLogResult, ReviewDiffResult, append_interaction_log, write_review_diff
from .run import AnalysisRunResult, run_analysis
from .runtime_metadata import (
    RuntimeMetadataResult,
    write_claude_runtime_metadata,
    write_codex_runtime_metadata,
    write_copilot_runtime_metadata,
)

__all__ = [
    "AgentContext",
    "AIPassportResult",
    "AnalysisRunResult",
    "IntakeResult",
    "InteractionLogResult",
    "PreflightResult",
    "PrepareResult",
    "ReviewDiffResult",
    "RuntimeMetadataResult",
    "agent_context",
    "append_interaction_log",
    "build_ai_passport",
    "build_ai_passport_summary",
    "draft_pap",
    "intake_prompt",
    "intake_task",
    "prepare",
    "preflight",
    "run_analysis",
    "write_ai_passport",
    "write_claude_runtime_metadata",
    "write_codex_runtime_metadata",
    "write_copilot_runtime_metadata",
    "write_review_diff",
    "write_workflow_report",
]
