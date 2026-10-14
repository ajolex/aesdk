"""AESDK package.

Public names are imported lazily (PEP 562) so ``import aesdk`` and the
coding-agent hook entry point stay fast; the first access loads the module.
"""

from __future__ import annotations

import importlib
from typing import Any

from ._version import __version__

_EXPORTS = {
    "AgentContext": "aesdk.agent",
    "AIPassportResult": "aesdk.agent",
    "AnalysisRunResult": "aesdk.agent",
    "AssumptionCheck": "aesdk.data",
    "DataProfile": "aesdk.data",
    "DataScanResult": "aesdk.data",
    "OLSDiagnosticsReport": "aesdk.data",
    "IntakeResult": "aesdk.agent",
    "InteractionLogResult": "aesdk.agent",
    "PreflightResult": "aesdk.agent",
    "PrepareResult": "aesdk.agent",
    "ReviewDiffResult": "aesdk.agent",
    "RuntimeMetadataResult": "aesdk.agent",
    "SetupResult": "aesdk.agent",
    "agent_context": "aesdk.agent",
    "append_interaction_log": "aesdk.agent",
    "build_ai_passport": "aesdk.agent",
    "build_ai_passport_summary": "aesdk.agent",
    "draft_pap": "aesdk.agent",
    "get_knowledge_pack": "aesdk.knowledge",
    "intake_prompt": "aesdk.agent",
    "intake_task": "aesdk.agent",
    "ols_assumption_report": "aesdk.data",
    "prepare": "aesdk.agent",
    "preflight": "aesdk.agent",
    "resolve_data_path": "aesdk.data",
    "run_analysis": "aesdk.agent",
    "run_setup": "aesdk.agent",
    "scan_data": "aesdk.data",
    "write_ai_passport": "aesdk.agent",
    "write_claude_runtime_metadata": "aesdk.agent",
    "write_codex_runtime_metadata": "aesdk.agent",
    "write_copilot_runtime_metadata": "aesdk.agent",
    "write_review_diff": "aesdk.agent",
    "write_workflow_report": "aesdk.agent",
}

__all__ = sorted([*_EXPORTS, "__version__"])


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module 'aesdk' has no attribute {name!r}")
    value = getattr(importlib.import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_EXPORTS))
