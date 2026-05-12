"""Anthropic adapter for AESDK."""
from __future__ import annotations
import os
from aesdk.llm.adapters.base import LLMAdapter, LLMResponse

try:
    import anthropic
except ImportError:
    anthropic = None

class AnthropicAdapter(LLMAdapter):
    def __init__(self, api_key: str | None = None, model: str = "claude-3-5-sonnet-20240620"):
        if anthropic is None:
            raise ImportError("anthropic package is required for AnthropicAdapter")
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = model

    def generate(self, prompt: str, temperature: float = 0.0, max_tokens: int = 2048) -> LLMResponse:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return LLMResponse(
            text=message.content[0].text,
            usage={"input_tokens": message.usage.input_tokens, "output_tokens": message.usage.output_tokens},
            model=self.model
        )
