"""Tests for LLM adapters and the reproducibility archive."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import aesdk as ae
import aesdk.llm.adapters.anthropic as anthropic_mod
import aesdk.llm.adapters.openai as openai_mod
from aesdk.llm import AnthropicAdapter, LocalLLMAdapter, OpenAIAdapter, ResearchLLM

SCHEMA = {
    "type": "object",
    "properties": {"label": {"type": "string", "enum": ["eligible", "ineligible"]}},
    "required": ["label"],
    "additionalProperties": False,
}


class FakeMessage(SimpleNamespace):
    def to_dict(self) -> dict:
        return {"id": self.id, "model": self.model, "stop_reason": self.stop_reason}


def _message(text: str, model: str = "claude-opus-5-5", stop_reason: str = "end_turn") -> FakeMessage:
    return FakeMessage(
        id="msg_1",
        _request_id="req_123",
        model=model,
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=4, output_tokens=6),
    )


class FakeAnthropic:
    def __init__(self, reply: FakeMessage):
        self.calls: list[dict] = []
        self.batch_requests: list = []
        outer = self

        class Messages:
            def create(self, **kwargs):
                outer.calls.append({"endpoint": "messages", **kwargs})
                return reply

            class batches:  # noqa: N801
                @staticmethod
                def create(requests):
                    outer.batch_requests = requests
                    return SimpleNamespace(id="msgbatch_1")

                @staticmethod
                def retrieve(batch_id):
                    return SimpleNamespace(processing_status="ended")

                @staticmethod
                def results(batch_id):
                    yield SimpleNamespace(custom_id="b", result=SimpleNamespace(type="succeeded", message=_message('{"label": "ineligible"}')))
                    yield SimpleNamespace(custom_id="a", result=SimpleNamespace(type="errored", error=SimpleNamespace(type="invalid_request")))

        class BetaMessages:
            def create(self, **kwargs):
                outer.calls.append({"endpoint": "beta", **kwargs})
                return reply

        self.messages = Messages()
        self.beta = SimpleNamespace(messages=BetaMessages())


def test_anthropic_defaults_structured_output_and_provenance() -> None:
    client = FakeAnthropic(_message('{"label": "eligible"}'))
    adapter = AnthropicAdapter(client=client)
    response = adapter.generate("Classify this comment", schema=SCHEMA)

    call = client.calls[0]
    assert call["endpoint"] == "beta" and call["fallbacks"] == "default"
    assert call["model"] == "claude-opus-5-5"
    assert call["output_config"] == {"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}}
    assert "temperature" not in call  # current models reject sampling params
    assert response.structured == {"label": "eligible"}
    assert response.request_id == "req_123"
    assert response.model == "claude-opus-5-5" and response.requested_model == "claude-opus-5-5"


def test_anthropic_without_fallbacks_and_refusal() -> None:
    client = FakeAnthropic(_message("", stop_reason="refusal"))
    response = AnthropicAdapter(client=client, fallbacks=None, effort=None, model="claude-sonnet-5-5").generate("x", schema=SCHEMA)
    assert client.calls[0]["endpoint"] == "messages"
    assert "output_config" in client.calls[0] and "effort" not in client.calls[0]["output_config"]
    assert response.refused and response.structured is None


def test_anthropic_batches() -> None:
    client = FakeAnthropic(_message("unused"))
    adapter = AnthropicAdapter(client=client)
    batch_id = adapter.submit_batch({"a": "one", "b": "two"}, schema=SCHEMA)
    assert batch_id == "msgbatch_1"
    assert [r["custom_id"] for r in client.batch_requests] == ["a", "b"]
    assert "fallbacks" not in client.batch_requests[0]["params"]
    results = adapter.batch_results(batch_id, structured=True)
    assert results["b"].structured == {"label": "ineligible"}
    assert results["a"] == {"status": "errored", "error": "invalid_request"}


def test_anthropic_raises_when_package_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(anthropic_mod, "anthropic", None)
    with pytest.raises(ImportError):
        AnthropicAdapter(api_key="key")


def test_openai_adapter_requires_model_and_parses_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict = {}

    class Completions:
        def create(self, **kwargs):
            seen.update(kwargs)
            message = SimpleNamespace(content='{"label": "eligible"}', refusal=None)
            return SimpleNamespace(
                id="chatcmpl-1",
                model="served-model",
                choices=[SimpleNamespace(message=message, finish_reason="stop")],
                usage=SimpleNamespace(prompt_tokens=3, completion_tokens=5),
            )

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    with pytest.raises(ValueError):
        OpenAIAdapter(client=client)
    response = OpenAIAdapter(client=client, model="test-model").generate("hello", schema=SCHEMA)
    assert seen["response_format"]["json_schema"]["schema"] == SCHEMA
    assert "temperature" not in seen
    assert response.structured == {"label": "eligible"}
    assert response.model == "served-model" and response.requested_model == "test-model"


def test_openai_raises_when_package_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openai_mod, "OpenAI", None)
    with pytest.raises(ImportError):
        OpenAIAdapter(api_key="key", model="m")


def test_local_adapter_is_deterministic() -> None:
    adapter = LocalLLMAdapter()
    first, second = adapter.generate("Hello", schema=SCHEMA), adapter.generate("Hello", schema=SCHEMA)
    assert first.request_id == second.request_id
    assert first.structured == {"label": None}


def test_research_llm_archive_feeds_a_passing_passport(valid_pap_dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = FakeAnthropic(_message('{"label": "eligible"}'))
    llm = ResearchLLM(AnthropicAdapter(client=client), archive_dir="ai_archive")
    llm.generate("Classify comment 1", schema=SCHEMA, record_id="c1")
    batch_id = llm.submit_batch({"a": "one", "b": "two"}, schema=SCHEMA)
    llm.collect_batch(batch_id)

    calls = llm.calls()
    assert [c["record_id"] for c in calls] == ["c1", "b"]
    assert calls[0]["served_model"] == "claude-opus-5-5" and calls[0]["request_id"] == "req_123"
    assert calls[1]["batch_id"] == "msgbatch_1"
    assert Path(calls[0]["schema_file"]).exists()

    (tmp_path / "comments.csv").write_text("id,text\nc1,hello\n", encoding="utf-8")
    ai_use = llm.ai_use(
        role="text_classification",
        ai_derived_variables=["label"],
        input_files=["comments.csv"],
        qa_sample_plan="Hand-code a 10% random sample.",
        sensitivity_plan="Re-estimate excluding AI-coded rows.",
    )
    assert ai_use["batch_ids"] == ["msgbatch_1"]
    assert ai_use["model_metadata_source"] == "api_response"

    pap_path = tmp_path / "pap.yaml"
    pap_path.write_text(yaml.safe_dump({**valid_pap_dict, "ai_use": ai_use}, sort_keys=False), encoding="utf-8")
    result = ae.write_ai_passport(pap_path=pap_path)
    passport = json.loads(result.path.read_text(encoding="utf-8"))
    assert result.status == "pass", passport["findings"]
    assert len(passport["artifact_hashes"]["structured_output_schema_files"][0]["sha256"]) == 64
