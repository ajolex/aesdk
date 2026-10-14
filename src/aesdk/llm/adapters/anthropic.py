"""Anthropic (Claude) adapter for AI-derived research variables."""

from __future__ import annotations

import json
from typing import Any

from aesdk.llm.adapters.base import LLMAdapter, LLMResponse

try:
    import anthropic
except ImportError:  # optional extra: pip install "aesdk[llm]"
    anthropic = None

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicAdapter(LLMAdapter):
    """Claude via the Messages API, with structured outputs and batch support.

    - ``effort`` (``low``..``max``) controls thinking depth on current models;
      Claude Opus 5.5 defaults to ``medium``, so set it explicitly for research
      coding work.
    - ``fallbacks="default"`` lets the API re-run a request that a safety
      classifier declines on a fallback model. The model that actually served
      each record is archived (``LLMResponse.model``), so a fallback is visible
      in the data. Pass ``fallbacks=None`` to keep every record on one model.
    """

    provider = "Anthropic"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        *,
        effort: str | None = "high",
        fallbacks: str | None = "default",
        client: Any = None,
    ):
        if client is None:
            if anthropic is None:
                raise ImportError('anthropic package is required for AnthropicAdapter: pip install "aesdk[llm]"')
            client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.client = client
        self.model = model
        self.effort = effort
        self.fallbacks = fallbacks

    def settings(self) -> dict[str, Any]:
        return {"provider": self.provider, "model": self.model, "effort": self.effort, "fallbacks": self.fallbacks}

    def _params(
        self,
        prompt: str,
        *,
        system: str | None,
        schema: dict[str, Any] | None,
        max_tokens: int,
        temperature: float | None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            params["system"] = system
        output_config: dict[str, Any] = {}
        if self.effort:
            output_config["effort"] = self.effort
        if schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": schema}
        if output_config:
            params["output_config"] = output_config
        if temperature is not None:
            # Not a typed SDK parameter any more (current models reject it);
            # sent raw only for older models that still accept it.
            params["extra_body"] = {"temperature": temperature}
        return params

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 16000,
        temperature: float | None = None,
    ) -> LLMResponse:
        params = self._params(prompt, system=system, schema=schema, max_tokens=max_tokens, temperature=temperature)
        if self.fallbacks:
            message = self.client.beta.messages.create(betas=[FALLBACK_BETA], fallbacks=self.fallbacks, **params)
        else:
            message = self.client.messages.create(**params)
        return self._to_response(message, schema is not None)

    def _to_response(self, message: Any, structured: bool) -> LLMResponse:
        stop_reason = getattr(message, "stop_reason", None)
        text = next((block.text for block in message.content if getattr(block, "type", None) == "text"), "")
        refused = stop_reason == "refusal"
        parsed = None
        if structured and text and not refused:
            parsed = json.loads(text)
        usage = getattr(message, "usage", None)
        raw = message.to_dict() if hasattr(message, "to_dict") else {}
        return LLMResponse(
            text=text,
            usage={
                "input_tokens": getattr(usage, "input_tokens", 0) or 0,
                "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            },
            model=getattr(message, "model", None) or self.model,
            requested_model=self.model,
            provider=self.provider,
            request_id=getattr(message, "_request_id", None) or getattr(message, "id", None),
            stop_reason=stop_reason,
            structured=parsed,
            refused=refused,
            raw=raw,
        )

    # ----------------------------------------------------------------- batches

    def submit_batch(
        self,
        prompts: dict[str, str],
        *,
        system: str | None = None,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 16000,
    ) -> str:
        """Submit ``{custom_id: prompt}`` as a Message Batch (50% cheaper, async).

        Batches do not support server-side fallbacks, so every record is served
        by ``self.model``. Returns the batch id to archive and poll.
        """

        requests = [
            {"custom_id": custom_id, "params": self._params(prompt, system=system, schema=schema, max_tokens=max_tokens, temperature=None)}
            for custom_id, prompt in prompts.items()
        ]
        batch = self.client.messages.batches.create(requests=requests)
        return batch.id

    def batch_status(self, batch_id: str) -> str:
        return self.client.messages.batches.retrieve(batch_id).processing_status

    def batch_results(self, batch_id: str, *, structured: bool = False) -> dict[str, LLMResponse | dict[str, Any]]:
        """Return ``{custom_id: LLMResponse}``; failed items map to an error dict.

        Results arrive in any order, so they are keyed by ``custom_id``.
        """

        results: dict[str, LLMResponse | dict[str, Any]] = {}
        for item in self.client.messages.batches.results(batch_id):
            outcome = item.result
            if outcome.type == "succeeded":
                response = self._to_response(outcome.message, structured)
                response.raw.setdefault("batch_id", batch_id)
                results[item.custom_id] = response
            else:
                error = getattr(outcome, "error", None)
                results[item.custom_id] = {
                    "status": outcome.type,
                    "error": getattr(error, "type", None) if error is not None else None,
                }
        return results
