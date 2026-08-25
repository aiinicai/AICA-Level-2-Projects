"""Provider boundary for maker, checker, and entailment LLM calls."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pydantic import BaseModel, ConfigDict

from amg.models import (
    AssertionType,
    CandidateFact,
    CheckerVerdict,
    EntailmentVerdict,
    ServedBy,
    SourceType,
)


class ProviderUnavailable(RuntimeError):
    """A provider could not safely serve a request and fallback is required."""


class ProviderCallResult(BaseModel):
    """Honest report of the backend that actually served the latest call."""

    model_config = ConfigDict(frozen=True)

    provider_name: str
    model: str
    served_by: ServedBy
    was_fallback: bool


class LLMProvider(ABC):
    """Common contract implemented by live and deterministic LLM backends."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the human-readable backend name."""

    @abstractmethod
    def extract_candidates(self, user_text: str) -> list[CandidateFact]:
        """Propose facts from one direct user turn."""

    @abstractmethod
    def check_candidate(
        self,
        content: str,
        assertion_type: AssertionType,
        source_type: SourceType,
    ) -> CheckerVerdict:
        """Independently check one narrowly scoped candidate."""

    @abstractmethod
    def check_entailment(
        self, new_fact: str, existing_fact: str
    ) -> EntailmentVerdict:
        """Decide whether two fact texts are mutually exclusive."""
