"""Base LLM interface for AESDK."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class LLMResponse:
    text: str
    usage: dict[str, int]
    model: str

class LLMAdapter(ABC):
    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.0, max_tokens: int = 2048) -> LLMResponse:
        ...
