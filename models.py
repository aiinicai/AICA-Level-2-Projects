"""Strict provider output contracts, with source quotes for factual verification."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(StrictModel):
    text: str
    source_quote: str = Field(description="An exact supporting excerpt from the notice, not a paraphrase.")


class Deadline(StrictModel):
    exact_date: date | None
    deadline_text: str
    confidence: Literal["high", "medium", "low", "unknown"]
    source_quote: str


class Issue(StrictModel):
    title: str
    department_observation: str
    amount: str | None
    action_requested: str
    source_quote: str


class Analysis(StrictModel):
    is_tax_notice: bool
    notice_type: str | None
    department: str | None
    notice_date: str | None
    assessment_year: str | None
    financial_year: str | None
    sections_mentioned: list[Evidence]
    response_deadline: Deadline
    issues: list[Issue]
    documents_requested: list[Evidence]
    executive_summary: list[str]
    uncertainties: list[str]


class Draft(StrictModel):
    draft_reply: str = Field(min_length=1)
