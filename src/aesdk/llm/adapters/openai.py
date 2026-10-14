"""OpenAI adapter for AI-derived research variables.

The model id is required: hosted model names change often, and a stale default
would silently change which model produced a study's variables.
"""

from __future__ import annotations

import json
from typing import Any

from aesdk.llm.adapters.base import LLMAdapter, LLMResponse

try:
    from openai import OpenAI
except ImportError:  # optional extra: pip install "aesdk[llm]"
    OpenAI = None


class OpenAIAdapter(LLMAdapter):
    provider = "OpenAI"

    def __init__(self, api_key: str | None = None, model: str | None = None, *, client: Any = None):
        if client is None:
            if OpenAI is None:
                raise ImportError('openai package is required for OpenAIAdapter: pip install "aesdk[llm]"')
            client = OpenAI(api_key=api_key) if api_key else OpenAI()
        if not model:
            raise ValueError("OpenAIAdapter needs an explicit model id (record exactly which model you used).")
        self.client = client
        self.model = model

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 16000,
        temperature: float | None = None,
    ) -> LLMResponse:
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        params: dict[str, Any] = {"model": self.model, "messages": messages, "max_completion_tokens": max_tokens}
        if schema is not None:
            params["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "aesdk_output", "schema": schema, "strict": True},
            }
        if temperature is not None:
            params["temperature"] = temperature
        response = self.client.chat.completions.create(**params)
        choice = response.choices[0]
        text = choice.message.content or ""
        refused = bool(getattr(choice.message, "refusal", None))
        usage = getattr(response, "usage", None)
        return LLMResponse(
            text=text,
            usage={
                "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
            },
            model=getattr(response, "model", None) or self.model,
            requested_model=self.model,
            provider=self.provider,
            request_id=getattr(response, "_request_id", None) or getattr(response, "id", None),
            stop_reason=getattr(choice, "finish_reason", None),
            structured=json.loads(text) if schema is not None and text and not refused else None,
            refused=refused,
            raw=response.model_dump() if hasattr(response, "model_dump") else {},
        )
