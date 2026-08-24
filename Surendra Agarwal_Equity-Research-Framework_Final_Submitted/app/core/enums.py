"""Shared enumerations.

These enums are imported by nearly every other module in the application.
Keeping them centralized (rather than redefined per-module) is what makes
it possible to enforce consistent status/confidence semantics across the
deterministic layer (Layers 1-4) and the AI layer (Layer 5).
"""

from __future__ import annotations

from enum import Enum


class DataStatus(str, Enum):
    """Status of a single data point or calculated metric.

    Used instead of silently substituting zero or None when a value
    cannot be determined (Principle 9: handle missing data explicitly).
    """

    OK = "ok"
    MISSING_INPUT = "missing_input"
    INSUFFICIENT_HISTORY = "insufficient_history"
    CALCULATION_ERROR = "calculation_error"
    NOT_APPLICABLE = "not_applicable"
    UNAVAILABLE = "unavailable"


class ConfidenceLevel(str, Enum):
    """Qualitative confidence rating.

    Deliberately not a numeric 0-100 score: a numeric score implies a
    precision that neither the deterministic calculations (which are
    exact, given their inputs) nor the AI interpretations (which are not)
    can honestly support. Numeric confidence invites false precision;
    this enum forces every producer of a confidence rating to justify a
    discrete, defensible category instead.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNAVAILABLE = "unavailable"


class Currency(str, Enum):
    INR = "INR"
    USD = "USD"


class UnitOfMeasure(str, Enum):
    """Units financial figures may arrive in.

    financial_data.py normalizes everything to a single canonical unit
    (INR crore) before any calculation runs. This enum exists so that
    raw-ingestion code can record the *original* unit for lineage even
    after normalization.
    """

    INR_ABSOLUTE = "inr_absolute"
    INR_LAKH = "inr_lakh"
    INR_CRORE = "inr_crore"
    INR_MILLION = "inr_million"
    INR_BILLION = "inr_billion"
    PERCENT = "percent"
    RATIO = "ratio"
    DAYS = "days"
    SHARES = "shares"
    PER_SHARE = "per_share"


class DataSourceType(str, Enum):
    """Where a piece of data originated."""

    CSV_UPLOAD = "csv_upload"
    EXCEL_UPLOAD = "excel_upload"
    JSON_UPLOAD = "json_upload"
    PDF_EXTRACTED = "pdf_extracted"
    MARKET_DATA_API = "market_data_api"
    MANUAL_ENTRY = "manual_entry"
    CALCULATED = "calculated"
    AI_GENERATED = "ai_generated"


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DETERIORATING = "deteriorating"
    MIXED = "mixed"
    INSUFFICIENT_DATA = "insufficient_data"


class RiskCategory(str, Enum):
    FINANCIAL = "financial"
    BUSINESS = "business"
    GOVERNANCE = "governance"
    VALUATION = "valuation"
    MARKET = "market"
    REGULATORY = "regulatory"
    MANAGEMENT_EXECUTION = "management_execution"


class RiskSeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"


class Recommendation(str, Enum):
    BUY = "buy"
    HOLD = "hold"
    AVOID = "avoid"


class InsightLevel(str, Enum):
    """Module 13 human-in-the-loop levels.

    Every piece of content surfaced in the UI or the report must be
    taggable with exactly one of these, so the report generator can
    render the LEVEL 1/2/3 distinction structurally rather than by
    convention.
    """

    LEVEL_1_VERIFIED = "level_1_verified_calculated"
    LEVEL_2_AI_INTERPRETATION = "level_2_ai_interpretation"
    LEVEL_3_HUMAN_VALIDATED = "level_3_human_validated"


class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKING = "blocking"


class DocumentSectionType(str, Enum):
    BUSINESS = "business"
    MANAGEMENT_DISCUSSION = "management_discussion"
    RISK = "risk"
    GOVERNANCE = "governance"
    FINANCIAL_STATEMENTS = "financial_statements"
    AUDITOR_REPORT = "auditor_report"
    UNKNOWN = "unknown"


class DocumentType(str, Enum):
    """What kind of source document a DocumentEvidence came from — kept
    separate from DocumentSectionType (which classifies what's ON a
    given page). A page's section classification is content-based and
    works the same regardless of document type; document_type instead
    lets callers filter/report on WHERE evidence came from (Module 4's
    named input categories: annual reports, investor presentations,
    earnings-call transcripts, corporate announcements — plus their
    quarterly-cadence counterparts below, kept as distinct values rather
    than reused so a report/audit trail can always tell "this claim came
    from the annual investor presentation" apart from "this claim came
    from last quarter's investor presentation" — the two carry
    meaningfully different recency)."""

    ANNUAL_REPORT = "annual_report"
    INVESTOR_PRESENTATION = "investor_presentation"
    EARNINGS_CALL_TRANSCRIPT = "earnings_call_transcript"
    CORPORATE_ANNOUNCEMENT = "corporate_announcement"
    PLEDGE_DISCLOSURE = "pledge_disclosure"
    QUARTERLY_RESULTS = "quarterly_results"
    QUARTERLY_INVESTOR_PRESENTATION = "quarterly_investor_presentation"
    QUARTERLY_MEET_TRANSCRIPT = "quarterly_meet_transcript"
    OTHER = "other"


class ExchangeCode(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
