"""Local/Mock adapter for AESDK development."""
from __future__ import annotations
from aesdk.llm.adapters.base import LLMAdapter, LLMResponse

class LocalLLMAdapter(LLMAdapter):
    def generate(self, prompt: str, temperature: float = 0.0, max_tokens: int = 2048) -> LLMResponse:
        return LLMResponse(
            text=f"[Local Mock Response to: {prompt[:50]}...]",
            usage={"prompt_tokens": 0, "completion_tokens": 0},
            model="local-mock"
        )
