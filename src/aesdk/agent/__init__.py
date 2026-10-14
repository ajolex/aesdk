"""Agent-facing AESDK convenience API.

Attributes are imported lazily (PEP 562) so lightweight entry points such as
the coding-agent hooks (`aesdk.agent.hooks`) start quickly without loading
pandas/statsmodels.
"""

from __future__ import annotations

import importlib
from typing import Any

_EXPORTS = {
    "AIPassportResult": "ai_passport",
    "build_ai_passport": "ai_passport",
    "build_ai_passport_summary": "ai_passport",
    "write_ai_passport": "ai_passport",
    "AgentContext": "context",
    "agent_context": "context",
    "IntakeResult": "intake",
    "intake_prompt": "intake",
    "intake_task": "intake",
    "draft_pap": "pap_draft",
    "PrepareResult": "prepare",
    "prepare": "prepare",
    "PreflightResult": "preflight",
    "preflight": "preflight",
    "write_workflow_report": "report",
    "InteractionLogResult": "review",
    "ReviewDiffResult": "review",
    "append_interaction_log": "review",
    "write_review_diff": "review",
    "AnalysisRunResult": "run",
    "run_analysis": "run",
    "SetupResult": "setup",
    "run_setup": "setup",
    "RuntimeMetadataResult": "runtime_metadata",
    "write_claude_runtime_metadata": "runtime_metadata",
    "write_codex_runtime_metadata": "runtime_metadata",
    "write_copilot_runtime_metadata": "runtime_metadata",
    "summarize_transcript": "transcripts",
    "summarize_sessions": "transcripts",
    "install_claude_hooks": "hooks",
    "write_skills": "skills",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module 'aesdk.agent' has no attribute {name!r}")
    value = getattr(importlib.import_module(f"{__name__}.{module_name}"), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_EXPORTS))
