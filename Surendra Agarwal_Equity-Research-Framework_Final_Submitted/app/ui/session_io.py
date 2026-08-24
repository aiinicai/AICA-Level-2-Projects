"""Session save/reload - serializes/deserializes the dashboard's session
state to/from a single JSON file, so a user can resume exactly where
they left off without re-uploading source files or re-running any
analysis (including LLM calls, which cost time and money).

Deliberately saves the COMPUTED RESULTS (statements, metrics, risks,
thesis, etc.), not the original uploaded Excel/PDF/CSV bytes - smaller
file, faster reload, and avoids re-transmitting a multi-megabyte annual
report PDF just to restore a session.

Load is best-effort: if the app's data models have changed since a file
was saved (e.g. a field renamed), each session-state key is restored
independently, and a failure restoring one key is reported as a warning
rather than aborting the entire load - partial restoration is far more
useful than an all-or-nothing failure for what is, after all, a working
session someone is trying to get back.
"""

from __future__ import annotations

import io
import json
import logging
from datetime import datetime, timezone

import pandas as pd

from app.core.audit import AuditTrail
from app.core.models import (
    AIInterpretation,
    AuditTrailEntry,
    Company,
    DocumentEvidence,
    FinancialStatement,
    HumanReview,
    InvestmentScore,
    InvestmentThesis,
    MetricResult,
    RiskItem,
    TrendResult,
)
from app.analysis.peers import PeerCompanyMultiples, PeerComparisonResult
from app.reports.history import ReportHistoryEntry
from app.valuation.dcf import DCFAssumptions
from app.valuation.scenarios import ScenarioSet

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

_LIST_MODEL_FIELDS: dict[str, type] = {
    "statements": FinancialStatement,
    "fundamental_metrics": MetricResult,
    "cashflow_metrics": MetricResult,
    "working_capital_metrics": MetricResult,
    "shareholder_metrics": MetricResult,
    "technical_metrics": MetricResult,
    "valuation_metrics": MetricResult,
    "trends": TrendResult,
    "risks": RiskItem,
    "business_interpretations": AIInterpretation,
    "management_interpretations": AIInterpretation,
    "governance_interpretations": AIInterpretation,
    "human_reviews": HumanReview,
    "document_evidence": DocumentEvidence,
    "peer_comparisons": PeerComparisonResult,
    "peers": PeerCompanyMultiples,
    "report_history": ReportHistoryEntry,
}

_SINGLE_MODEL_FIELDS: dict[str, type] = {
    "company": Company,
    "investment_score": InvestmentScore,
    "thesis": InvestmentThesis,
    "last_dcf_assumptions": DCFAssumptions,
    "scenario_set": ScenarioSet,
}

_PLAIN_FIELDS = ("reviewer_name", "sensitivity_grid", "weight_sliders")

# Every session_state key this module reads/writes — the single source
# of truth for "what is a tracked analysis field" versus incidental
# Streamlit widget-internal keys (e.g. "slider_Fundamentals",
# "session_upload") that live in the same st.session_state dict but are
# NOT part of the saved session. Callers (dashboard.py) build their
# snapshot from exactly this list via .get() rather than ever calling
# dict(st.session_state) directly — see dashboard.py's
# _render_session_save_load() docstring for why that matters.
TRACKED_SESSION_KEYS: tuple[str, ...] = (
    *_LIST_MODEL_FIELDS.keys(), *_SINGLE_MODEL_FIELDS.keys(),
    *_PLAIN_FIELDS, "audit_trail", "price_df",
)


def serialize_session(session_state: dict) -> str:
    """Serialize the meaningful subset of session_state into a JSON
    string. Unknown/extra keys in session_state are ignored - only the
    fields this module knows about are saved."""
    data: dict = {}

    for key in _LIST_MODEL_FIELDS:
        items = session_state.get(key) or []
        data[key] = [item.model_dump(mode="json") for item in items]

    for key in _SINGLE_MODEL_FIELDS:
        value = session_state.get(key)
        data[key] = value.model_dump(mode="json") if value is not None else None

    for key in _PLAIN_FIELDS:
        data[key] = session_state.get(key)

    audit_trail = session_state.get("audit_trail")
    data["audit_trail"] = audit_trail.to_dicts() if audit_trail is not None else []

    price_df = session_state.get("price_df")
    if price_df is not None:
        buf = io.StringIO()
        price_df.to_csv(buf)
        data["price_df_csv"] = buf.getvalue()
    else:
        data["price_df_csv"] = None

    envelope = {
        "schema_version": SCHEMA_VERSION,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    return json.dumps(envelope, indent=2)


def deserialize_session(json_text: str) -> tuple[dict, list[str]]:
    """Parse a previously-saved session JSON string. Returns
    (session_state_updates, warnings) - warnings lists every field that
    could not be restored (with a reason), so a caller can surface them
    to the user rather than silently losing part of the session.

    Never raises for a per-field problem; only raises if the top-level
    JSON itself is unparseable or missing the expected envelope shape,
    since at that point there's nothing usable to return at all.
    """
    try:
        envelope = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Session file is not valid JSON: {exc}") from exc

    if "data" not in envelope:
        raise ValueError("Session file is missing the expected 'data' envelope.")

    schema_version = envelope.get("schema_version")
    warnings: list[str] = []
    if schema_version != SCHEMA_VERSION:
        warnings.append(
            f"Session file was saved with schema_version={schema_version!r}, "
            f"this app expects {SCHEMA_VERSION!r} - restoration will still be "
            "attempted field-by-field, but some fields may not restore cleanly."
        )

    raw = envelope["data"]
    result: dict = {}

    for key, model_cls in _LIST_MODEL_FIELDS.items():
        try:
            items = raw.get(key) or []
            result[key] = [model_cls(**d) for d in items]
        except Exception as exc:
            warnings.append(f"Could not restore '{key}': {exc}")
            result[key] = []

    for key, model_cls in _SINGLE_MODEL_FIELDS.items():
        try:
            value = raw.get(key)
            result[key] = model_cls(**value) if value is not None else None
        except Exception as exc:
            warnings.append(f"Could not restore '{key}': {exc}")
            result[key] = None

    for key in _PLAIN_FIELDS:
        result[key] = raw.get(key)

    try:
        audit_entries_raw = raw.get("audit_trail") or []
        audit_entries = [AuditTrailEntry(**d) for d in audit_entries_raw]
        result["audit_trail"] = AuditTrail.from_entries(audit_entries)
    except Exception as exc:
        warnings.append(f"Could not restore 'audit_trail': {exc}")
        result["audit_trail"] = None

    price_df_csv = raw.get("price_df_csv")
    if price_df_csv:
        try:
            result["price_df"] = pd.read_csv(io.StringIO(price_df_csv), index_col=0, parse_dates=True)
        except Exception as exc:
            warnings.append(f"Could not restore 'price_df': {exc}")
            result["price_df"] = None
    else:
        result["price_df"] = None

    return result, warnings
