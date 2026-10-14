"""Deterministic offline adapter for tests and dry runs (no network)."""

from __future__ import annotations

import hashlib
from typing import Any

from aesdk.llm.adapters.base import LLMAdapter, LLMResponse


class LocalLLMAdapter(LLMAdapter):
    provider = "local"
    model = "local-mock"

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 16000,
        temperature: float | None = None,
    ) -> LLMResponse:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]
        structured = None
        if schema is not None:
            structured = {key: None for key in (schema.get("properties") or {})}
        return LLMResponse(
            text=f"[Local Mock Response to: {prompt[:50]}...]",
            usage={"input_tokens": 0, "output_tokens": 0},
            model=self.model,
            requested_model=self.model,
            provider=self.provider,
            request_id=f"local-{digest}",
            stop_reason="end_turn",
            structured=structured,
        )
