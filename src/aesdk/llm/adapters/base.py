"""Provider-neutral LLM interface for AI-derived research variables.

When an LLM classifies, extracts, or codes data for a study, the results must
be reproducible *without* calling the model again: models are retired, and the
same prompt can return different text later. Adapters therefore return the full
provenance of every call (model actually served, provider request id, stop
reason, raw response), and :class:`aesdk.llm.archive.ResearchLLM` writes it to
an archive that the AI Replicability Passport can hash.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    text: str
    usage: dict[str, int]
    model: str
    requested_model: str | None = None
    provider: str | None = None
    request_id: str | None = None
    stop_reason: str | None = None
    structured: Any = None
    refused: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


class LLMAdapter(ABC):
    """One request in, one :class:`LLMResponse` out."""

    provider: str = "unknown"
    model: str = ""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 16000,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Send ``prompt``; when ``schema`` (JSON Schema) is given, constrain the
        output to it and return the parsed value in ``LLMResponse.structured``.

        ``temperature`` is sent only when explicitly set: several current models
        reject sampling parameters, and reproducibility comes from archiving
        outputs, not from sampling settings.
        """

    def settings(self) -> dict[str, Any]:
        """Request settings to record in the archive (model, effort, ...)."""
        return {"provider": self.provider, "model": self.model}
