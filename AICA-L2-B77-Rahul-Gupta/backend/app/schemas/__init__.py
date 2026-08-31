"""Shared Pydantic request schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ValuationCaseCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    industry: str = "Food & Beverages"
    entity_type: str = "Private Limited Company"
    valuation_date: str
    currency: str = "INR"
    units: str = "crore"
    purpose: str = "Fund Raising"
    country: str = "India"
    promoter_holding_pct: float = Field(default=100.0, ge=0, le=100)
    total_shares: float = Field(default=0.0, ge=0)
    notes: str = ""


class ApproveValueRequest(BaseModel):
    item_id: str | None = None
    approved_value: float | None = None
    note: str = ""
    approve_all: bool = False
    source: str = "python"  # python | ai | manual — which value to adopt on approve_all


class InterviewAnswerRequest(BaseModel):
    question_id: str
    value: str | float | int | list[str]
    elaboration: str = ""


class AssumptionsUpdate(BaseModel):
    values: dict[str, float | None]
    source: str = "user"


class SimulateRequest(BaseModel):
    overrides: dict[str, float] = {}


class ScenarioSaveRequest(BaseModel):
    name: str
    assumptions: dict[str, float] = {}


class NormalisationDecision(BaseModel):
    action: str  # approve | reject
    adjustment: float | None = None
    reason: str | None = None


class NormalisationCreate(BaseModel):
    period_label: str
    metric: str
    kind: str = "other"
    adjustment: float
    reason: str = ""


class AISettingsUpdate(BaseModel):
    model: str | None = None
    model_display: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    structured_output: bool | None = None
    visual_verification: bool | None = None
    ai_final_report: bool | None = None
    api_key: str | None = None


class ProfileUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    email: str | None = None
    timezone: str | None = None
    date_format: str | None = None
    number_format: str | None = None


class ReportCreate(BaseModel):
    template: str = "comprehensive"
    options: dict = {}
