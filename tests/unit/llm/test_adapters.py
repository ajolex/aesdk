"""Tests for LLM adapters."""

from __future__ import annotations

import pytest

import aesdk.llm.adapters.anthropic as anthropic_mod
import aesdk.llm.adapters.openai as openai_mod
from aesdk.llm.adapters.anthropic import AnthropicAdapter
from aesdk.llm.adapters.local import LocalLLMAdapter
from aesdk.llm.adapters.openai import OpenAIAdapter


def test_local_adapter() -> None:
    adapter = LocalLLMAdapter()
    response = adapter.generate("Hello")
    assert "Local Mock Response" in response.text
    assert response.model == "local-mock"


def test_openai_adapter_generates_with_unified_interface(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeUsage:
        prompt_tokens = 3
        completion_tokens = 5

    class FakeMessage:
        content = "openai-response"

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletions:
        def create(self, **kwargs):  # noqa: ANN003
            assert kwargs["model"] == "test-model"
            return type("Response", (), {"choices": [FakeChoice()], "usage": FakeUsage()})()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, api_key=None):  # noqa: ANN001
            self.chat = FakeChat()

    monkeypatch.setattr(openai_mod, "OpenAI", FakeOpenAI)
    response = OpenAIAdapter(api_key="key", model="test-model").generate("hello")
    assert response.text == "openai-response"
    assert response.usage == {"prompt_tokens": 3, "completion_tokens": 5}
    assert response.model == "test-model"


def test_openai_adapter_raises_when_package_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openai_mod, "OpenAI", None)
    with pytest.raises(ImportError):
        OpenAIAdapter(api_key="key")


def test_anthropic_adapter_generates_with_unified_interface(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeUsage:
        input_tokens = 4
        output_tokens = 6

    class FakeContent:
        text = "anthropic-response"

    class FakeMessages:
        def create(self, **kwargs):  # noqa: ANN003
            assert kwargs["model"] == "test-model"
            return type("Response", (), {"content": [FakeContent()], "usage": FakeUsage()})()

    class FakeAnthropicClient:
        def __init__(self, api_key=None):  # noqa: ANN001
            self.messages = FakeMessages()

    fake_module = type("FakeAnthropicModule", (), {"Anthropic": FakeAnthropicClient})
    monkeypatch.setattr(anthropic_mod, "anthropic", fake_module)
    response = AnthropicAdapter(api_key="key", model="test-model").generate("hello")
    assert response.text == "anthropic-response"
    assert response.usage == {"input_tokens": 4, "output_tokens": 6}
    assert response.model == "test-model"


def test_anthropic_adapter_raises_when_package_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(anthropic_mod, "anthropic", None)
    with pytest.raises(ImportError):
        AnthropicAdapter(api_key="key")
