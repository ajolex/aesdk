"""OpenAI adapter for AESDK."""
from __future__ import annotations
from pathlib import Path
import os
from aesdk.llm.adapters.base import LLMAdapter, LLMResponse

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class OpenAIAdapter(LLMAdapter):
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o"):
        if OpenAI is None:
            raise ImportError("openai package is required for OpenAIAdapter")
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

    def generate(self, prompt: str, temperature: float = 0.0, max_tokens: int = 2048) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return LLMResponse(
            text=response.choices[0].message.content or "",
            usage={"prompt_tokens": response.usage.prompt_tokens, "completion_tokens": response.usage.completion_tokens},
            model=self.model
        )
