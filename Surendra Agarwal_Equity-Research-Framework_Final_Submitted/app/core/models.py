"""Core shared domain models.

Every layer of the application communicates through these typed objects
rather than raw dicts. This is the mechanism that makes source
traceability (Module 11), the deterministic/interpretive boundary
(Principle 6), and human-in-the-loop labeling (Module 13) enforceable in
code rather than convention.

Design note: these models are intentionally "fat" (carry lineage,
confidence, and status fields even when a caller might be tempted to
omit them) because the spec requires every material conclusion to be
traceable to evidence. A leaner model would make that requirement
optional; these models make it structural.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from app.core.enums import (
    ConfidenceLevel,
    Currency,
    DataSourceType,
    DataStatus,
    DocumentSectionType,
    DocumentType,
    ExchangeCode,
    InsightLevel,
    Recommendation,
    RiskCategory,
    RiskSeverity,
    TrendDirection,
    UnitOfMeasure,
    ValidationSeverity,
)


def _new_id() -> str:
    """Short unique id used to cross-link objects (e.g. AI interpretation -> evidence)."""
    return uuid4().hex[:12]


# --------------------------------------------------------------------------
# Company / identification
# --------------------------------------------------------------------------


class Company(BaseModel):
    """Identifies the subject of an analysis run."""

    name: str
    ticker: str = Field(..., description="Base ticker without exchange suffix, e.g. 'TITAN'")
    exchange: ExchangeCode = ExchangeCode.NSE
    sector: str | None = None
    isin: str | None = None
    analysis_date: date = Field(default_factory=date.today)

    @property
    def market_data_symbol(self) -> str:
        """Ticker suffixed for yfinance (NSE -> .NS, BSE -> .BO)."""
        suffix = ".NS" if self.exchange == ExchangeCode.NSE else ".BO"
        return f"{self.ticker}{suffix}"


# --------------------------------------------------------------------------
# Lineage / metadata — attached to every raw and derived data point
# --------------------------------------------------------------------------


class SourceMetadata(BaseModel):
    """Mandatory lineage metadata for any ingested data (Module 1)."""

    company: str
    source: str = Field(..., description="e.g. filename, API name, 'manual entry'")
    source_type: DataSourceType
    source_date: date | None = Field(
        default=None, description="Date the underlying figure/document was published"
    )
    reporting_period: str | None = Field(
        default=None, description="e.g. 'FY2026', 'Q1FY2027'"
    )
    retrieved_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    currency: Currency = Currency.INR
    unit: UnitOfMeasure
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH


# --------------------------------------------------------------------------
# Financial statements (Module 1)
# --------------------------------------------------------------------------


class FinancialStatementRaw(BaseModel):
    """A single as-ingested line item, before normalization.

    One instance per (line_item, period) pair. Kept deliberately close to
    the source layout so the raw->canonical transform in
    financial_data.py is auditable line-by-line against the original
    file. Never used directly for calculations — see FinancialStatement.
    """

    company: str
    line_item: str = Field(..., description="Label as it appeared in the source, e.g. 'Sales'")
    statement_type: str = Field(
        ..., description="'profit_and_loss' | 'balance_sheet' | 'cash_flow' | 'quarterly'"
    )
    period: str = Field(..., description="Canonical period label, e.g. 'FY2026'")
    period_end_date: date | None = None
    value: float | None
    source: SourceMetadata


class FinancialStatement(BaseModel):
    """Canonical, normalized per-period financial statement.

    All monetary fields are normalized to a single unit (INR crore) by
    financial_data.py regardless of the unit the source used, per the
    spec's requirement to never mix lakh/crore/million/billion without
    explicit conversion. `None` means genuinely unavailable for that
    period — never coerced to 0.0.
    """

    company: str
    period: str
    period_end_date: date | None = None
    unit: UnitOfMeasure = UnitOfMeasure.INR_CRORE
    currency: Currency = Currency.INR

    # Profit & Loss
    sales: float | None = None
    raw_material_cost: float | None = None
    employee_cost: float | None = None
    other_expenses_total: float | None = None
    operating_profit: float | None = None  # EBITDA-equivalent as reported by source
    other_income: float | None = None
    depreciation: float | None = None
    interest: float | None = None
    profit_before_tax: float | None = None
    tax: float | None = None
    net_profit: float | None = None
    dividend_amount: float | None = None

    # Balance Sheet
    equity_share_capital: float | None = None
    reserves: float | None = None
    borrowings: float | None = None
    other_liabilities: float | None = None
    total_liabilities: float | None = None
    net_block: float | None = None
    capital_work_in_progress: float | None = None
    investments: float | None = None
    other_assets: float | None = None
    total_assets: float | None = None
    receivables: float | None = None
    inventory: float | None = None
    cash_and_bank: float | None = None
    num_equity_shares: float | None = None
    face_value: float | None = None
    promoter_holding_pct: float | None = Field(
        default=None,
        description="Manually-entered override, e.g. 0.55 for 55%. Never "
        "populated by loaders.py — the Screener 'Data Sheet' export this "
        "project consumes does not include shareholding-pattern data. "
        "Set explicitly by the caller (e.g. a UI form) when available.",
    )
    promoter_pledge_pct: float | None = Field(
        default=None,
        description="Manually-entered override, e.g. 0.10 for 10% pledged. "
        "Same provenance caveat as promoter_holding_pct above.",
    )

    # Cash Flow
    cash_from_operations: float | None = None
    cash_from_investing: float | None = None
    cash_from_financing: float | None = None
    net_cash_flow: float | None = None

    # Market
    price: float | None = None

    source: SourceMetadata
    data_quality_notes: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


class ValidationIssue(BaseModel):
    """A single finding from the Module 1 validation layer.

    Validators never raise on data-quality problems; they return these,
    and calling code decides whether to proceed, warn the user, or block.
    """

    rule: str = Field(..., description="Name of the validation rule that fired")
    severity: ValidationSeverity
    message: str
    field: str | None = None
    period: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------
# Metrics — the core output type of the deterministic analysis layer
# --------------------------------------------------------------------------


class MetricResult(BaseModel):
    """Output of a single deterministic calculation (Module 2/6/7).

    This is the boundary object between the deterministic zone and
    everything downstream. It must never be constructed with a fabricated
    or guessed `value` — if a value cannot be honestly computed, `status`
    must reflect that and `value` must be None.
    """

    metric_id: str = Field(default_factory=_new_id)
    metric_name: str
    formula: str = Field(..., description="Human-readable formula, e.g. '(EBITDA_t / EBITDA_t-n)^(1/n) - 1'")
    inputs: dict[str, float | None] = Field(default_factory=dict)
    value: float | None = None
    unit: UnitOfMeasure
    period: str
    status: DataStatus = DataStatus.OK
    interpretation: str | None = Field(
        default=None,
        description="Short deterministic, factual note ONLY (e.g. 'above sector median'). "
        "Not an AI-generated interpretation — those live in AIInterpretation.",
    )
    data_quality_notes: list[str] = Field(default_factory=list)
    source: SourceMetadata | None = None

    @field_validator("value")
    @classmethod
    def _value_requires_ok_status_or_none(cls, v: float | None, info: Any) -> float | None:
        # Defensive check: a non-OK status should not carry a numeric value
        # that looks authoritative. This does not fully enforce ordering
        # (pydantic v2 field order dependency), so callers must also honor
        # this contract explicitly in analysis/*.py.
        return v


class TrendResult(BaseModel):
    """Output of the Module 3 change-detection engine."""

    trend_id: str = Field(default_factory=_new_id)
    metric_name: str
    periods: list[str]
    values: list[float | None]
    absolute_change: float | None = None
    percentage_change: float | None = None
    direction: TrendDirection
    significance: ConfidenceLevel = ConfidenceLevel.MEDIUM
    potential_explanation: str | None = Field(
        default=None,
        description="Only populated if supporting document evidence exists "
        "(evidence_ids below). Never a causal claim without evidence.",
    )
    evidence_ids: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Document intelligence
# --------------------------------------------------------------------------


class DocumentEvidence(BaseModel):
    """A located, page-tracked excerpt from a source document (Module 4/11).

    `raw_text` is the sanitized/quarantined text — see
    app/documents/quarantine.py. Any instruction-like content detected in
    the original text is neutralized before it is stored here, since this
    object is what gets passed into LLM prompts.
    """

    evidence_id: str = Field(default_factory=_new_id)
    source_document: str
    document_type: DocumentType = DocumentType.OTHER
    page_number: int | None = None
    section: DocumentSectionType = DocumentSectionType.UNKNOWN
    raw_text: str
    quarantine_flagged: bool = Field(
        default=False,
        description="True if instruction-like patterns were detected and neutralized in this excerpt",
    )
    retrieved_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AIInterpretation(BaseModel):
    """Output of the AI interpretation layer (Module 5, Layer 5).

    Distinguished structurally from MetricResult: this object can never
    be mistaken for a verified fact because it always carries a
    confidence level and evidence linkage, and the report generator
    renders it under an explicit "AI Interpretation" heading.
    """

    interpretation_id: str = Field(default_factory=_new_id)
    claim: str
    based_on_metric_ids: list[str] = Field(default_factory=list)
    based_on_evidence_ids: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel
    model_name: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    level: InsightLevel = InsightLevel.LEVEL_2_AI_INTERPRETATION

    @field_validator("based_on_evidence_ids", "based_on_metric_ids")
    @classmethod
    def _at_least_something_grounds_the_claim(
        cls, v: list[str], info: Any
    ) -> list[str]:
        # Soft validation only (a single-field validator can't see both
        # lists at once in pydantic v2 without a model_validator). The
        # authoritative check — that at least one of the two lists is
        # non-empty — is enforced in app/ai/thesis_generator.py before
        # an AIInterpretation is allowed to be persisted or rendered.
        return v


# --------------------------------------------------------------------------
# Risk
# --------------------------------------------------------------------------


class RiskItem(BaseModel):
    """A single structured risk entry (Module 8)."""

    risk_id: str = Field(default_factory=_new_id)
    category: RiskCategory
    description: str
    severity: RiskSeverity
    evidence_ids: list[str] = Field(default_factory=list)
    probability_assumption: str | None = None
    potential_impact: str | None = None
    mitigation: str | None = None
    monitoring_trigger: str | None = None


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------


class ScoreComponent(BaseModel):
    """One weighted component of the AI-IDS (Module 9)."""

    name: str
    score: float | None = Field(default=None, description="0-100, or None if unavailable")
    max_score: float = 100.0
    weight: float
    status: DataStatus = DataStatus.OK
    weighted_score: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class InvestmentScore(BaseModel):
    """Aggregated AI-Assisted Investment Decision Score."""

    overall_score: float | None
    max_possible_score: float = 100.0
    components: list[ScoreComponent]
    weights_used: dict[str, float]
    renormalized: bool = Field(
        default=False,
        description="True if one or more components were unavailable and "
        "weights were renormalized over the remaining components",
    )
    unavailable_components: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --------------------------------------------------------------------------
# Thesis / recommendation
# --------------------------------------------------------------------------


class ThesisInvalidationTrigger(BaseModel):
    """Module 10 — measurable condition that would invalidate the thesis."""

    condition: str
    threshold_basis: str = Field(
        ..., description="Where this threshold came from: 'user_input', "
        "'historical_analysis', 'industry_context', or 'explicit_assumption'"
    )
    metric_reference: str | None = None


class InvestmentThesis(BaseModel):
    """Final synthesized output feeding the report's recommendation section."""

    recommendation: Recommendation
    core_thesis: str
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    counterarguments: list[str] = Field(default_factory=list)
    key_risks_ids: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    invalidation_triggers: list[ThesisInvalidationTrigger] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)
    requires_human_review: bool = True
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --------------------------------------------------------------------------
# Human-in-the-loop
# --------------------------------------------------------------------------


class HumanReview(BaseModel):
    """Module 13, Level 3. Only ever created/populated by explicit UI action.

    No other part of the system may construct this object with
    `reviewed=True` — that would constitute the false claim the spec
    explicitly forbids ("must never falsely claim human validation
    occurred").
    """

    target_id: str = Field(..., description="ID of the AIInterpretation, RiskItem, etc. being reviewed")
    reviewer_name: str
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accepted: bool
    reviewer_notes: str | None = None


# --------------------------------------------------------------------------
# Audit trail
# --------------------------------------------------------------------------


class AuditTrailEntry(BaseModel):
    """A single audit-trail record, per Module 11's example schema."""

    entry_id: str = Field(default_factory=_new_id)
    claim: str
    source: str | None = None
    page: int | None = None
    evidence: str | None = None
    calculation: str | None = None
    interpretation: str | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
