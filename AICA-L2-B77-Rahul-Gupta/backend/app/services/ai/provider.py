"""AI provider adapter architecture.

The financial engine never depends on a specific model. Providers implement
this interface; Gemini is the default. The browser NEVER calls the provider —
all AI traffic flows React → FastAPI → provider."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AIProviderError(Exception):
    """Raised when the provider fails; core app must degrade gracefully."""


class AIProvider(ABC):
    name: str = "abstract"
    model: str = ""

    @abstractmethod
    def test_connection(self) -> bool: ...

    @abstractmethod
    def verify_document(self, image_path: str, page: int, statement_type: str,
                        unit_name: str, unit_multiplier: float,
                        periods: list[str], items: list[dict]) -> dict[str, Any]: ...

    @abstractmethod
    def generate_question(self, context: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def interpret_answer(self, question: str, answer: str, context: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def generate_insights(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def generate_report_sections(self, payload: dict[str, Any], sections: list[str]) -> dict[str, Any]: ...
