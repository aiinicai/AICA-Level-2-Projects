"""AI service (Phase 4).

Flow: Local Host uploads invoice -> this service calls the AI provider using
AI_API_KEY from the server environment -> returns structured invoice data
(supplier, GSTIN, invoice no/date, lines, taxes) for human review on the Local Host.
The Local Host never calls an AI provider directly and never holds its key.
"""
from __future__ import annotations


class AIService:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def configured(self) -> bool:
        return bool(self._api_key)
