import pytest

from aesdk.core.errors import PAPValidationError
from aesdk.governance.pap import validate_pap_dict


def test_pap_schema_validation_passes(valid_pap_dict: dict) -> None:
    validate_pap_dict(valid_pap_dict)


def test_pap_schema_validation_fails_missing_required(valid_pap_dict: dict) -> None:
    bad = dict(valid_pap_dict)
    bad.pop("identification")
    with pytest.raises(PAPValidationError):
        validate_pap_dict(bad)


def test_pap_schema_accepts_rct_tot_strategy(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "data": {**valid_pap_dict["data"], "structure": "cross-section"},
        "identification": {
            **valid_pap_dict["identification"],
            "strategy": "ToT",
            "standard_errors": "HC3",
        },
        "rct_block": {
            "randomization_unit": "individual",
            "assignment_variable": "assigned",
            "treatment_arms": ["training_offer"],
            "control_group": "no_offer",
            "estimand": "ToT",
        },
    }
    pap.pop("did_block")

    validate_pap_dict(pap)


def test_pap_schema_accepts_ai_use_block(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": ["code_generation", "text_classification"],
            "languages": ["stata", "r"],
            "provider": "Anthropic",
            "model": "claude-sonnet-4.6",
            "model_metadata_source": "agent_reported",
            "temperature": 0,
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_reviewed": True,
            "reproducible_without_ai": True,
            "live_model_required": False,
            "ai_output_used_as_data": True,
            "ai_derived_variables": ["topic_code"],
            "prompt_files": ["prompts/topic_code.md"],
            "output_files": ["outputs/topic_code_raw.jsonl"],
            "input_files": ["data/articles.csv"],
            "code_files": ["analysis.do", "analysis.R"],
            "qa_sample_plan": "Review 10 percent of coded texts.",
            "sensitivity_plan": "Re-estimate excluding uncertain labels.",
        },
    }

    validate_pap_dict(pap)


def test_pap_schema_accepts_single_ai_language(valid_pap_dict: dict) -> None:
    pap = {
        **valid_pap_dict,
        "ai_use": {
            "used": True,
            "role": "code_generation",
            "languages": "stata",
            "agent_tool": "Codex",
            "model_metadata_source": "agent_unavailable",
            "model_metadata_unavailable_reason": "The coding agent did not expose the underlying model id.",
            "runtime_metadata_files": ["codex_runtime.json"],
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "human_reviewed": True,
            "reproducible_without_ai": True,
            "live_model_required": False,
            "prompt_files": ["prompts/code.md"],
            "output_files": ["outputs/code.md"],
            "code_files": ["analysis.do"],
        },
    }

    validate_pap_dict(pap)
