"""Company Input page.

Uploads a Screener-format Excel (financials), optionally an NSE price
history CSV and/or documents (any combination of annual report,
investor presentation, earnings call transcript, corporate
announcement), and runs the DETERMINISTIC pipeline only (Milestones
1-4 + technical + valuation multiples + rule-based risk detection) — no
LLM calls happen here, so this page works with zero configuration (no
OPENAI_API_KEY needed). Document/AI analysis is a separate, explicit
action on later pages, consistent with human-in-the-loop principles:
nothing AI-generated happens without a deliberate trigger.

Also hosts the manual Promoter Holding/Pledge entry section — this data
is not present in the Screener "Data Sheet" export this project's
loader consumes (see app/analysis/shareholder.py's module docstring),
so it can only ever be manually supplied here, and is always flagged
as such wherever it's used.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import streamlit as st

from app.core.enums import ExchangeCode
from app.core.models import Company
from app.core.audit import AuditTrail
from app.data.financial_data import build_canonical_statements
from app.data.loaders import load_screener_excel
from app.data.market_data import load_nse_csv_price_history
from app.data.validators import run_all_validations
from app.analysis.fundamentals import compute_all_fundamentals
from app.analysis.cashflow import compute_all_cashflow_metrics
from app.analysis.working_capital import compute_all_working_capital_metrics
from app.analysis.shareholder import compute_all_shareholder_metrics
from app.analysis.trends import compute_multi_period_trend
from app.analysis.risk import detect_financial_risks
from app.analysis.technical import compute_all_technical_indicators
from app.valuation.multiples import compute_all_multiples

logger = logging.getLogger(__name__)


def run_deterministic_pipeline(
    excel_path: Path, company_name: str, ticker: str, exchange: ExchangeCode,
    sector: str | None, csv_path: Path | None, audit_trail: AuditTrail | None = None,
) -> dict:
    """Pure orchestration function (no Streamlit calls) — testable
    independently of the UI layer. Returns a dict matching the session
    state keys the dashboard expects.

    If `audit_trail` is supplied, material claims/conclusions from this
    run are recorded into it (Module 11 traceability) — every entry
    carries the actual source filename and, where applicable, the
    calculation formula, so "why do I believe this" is answerable for
    every number that ends up in a generated report.
    """
    trail = audit_trail if audit_trail is not None else AuditTrail()

    raw = load_screener_excel(excel_path, company_name=company_name)
    statements = build_canonical_statements(raw)
    validation_issues = run_all_validations(statements)

    trail.record(
        f"Loaded {len(statements)} period(s) of financial statements for {company_name}",
        source=excel_path.name, confidence="high",
        calculation="load_screener_excel -> build_canonical_statements",
    )
    for issue in validation_issues:
        trail.record(
            f"Data validation flag: {issue.rule}", source=excel_path.name,
            evidence=issue.message, confidence="high",
        )

    latest = statements[-1] if statements else None
    fundamental_metrics = compute_all_fundamentals(statements) if statements else []
    cashflow_metrics = compute_all_cashflow_metrics(statements) if statements else []
    working_capital_metrics = compute_all_working_capital_metrics(statements) if statements else []
    shareholder_metrics = compute_all_shareholder_metrics(statements) if statements else []
    valuation_metrics = compute_all_multiples(latest) if latest else []

    _KEY_METRIC_NAMES = {
        "EBITDA Margin", "ROE", "ROCE", "Debt/Equity", "Revenue CAGR (3yr)",
        "CFO/PAT", "Free Cash Flow",
    }
    if latest is not None:
        for m in fundamental_metrics + cashflow_metrics:
            if m.metric_name in _KEY_METRIC_NAMES and m.status.value == "ok":
                trail.record(
                    f"{m.metric_name} ({m.period}) = {m.value}", source=excel_path.name,
                    calculation=m.formula, confidence="high",
                )

    trends = []
    if statements:
        periods = [s.period for s in statements]
        sales = [s.sales for s in statements]
        trends.append(compute_multi_period_trend("Sales", periods, sales, higher_is_better=True))

    risks = detect_financial_risks(fundamental_metrics + cashflow_metrics, trends)
    for r in risks:
        trail.record(
            f"Financial risk flagged: {r.description}", source=excel_path.name,
            calculation="app.analysis.risk (rule-based, deterministic)",
            confidence="high",
        )

    technical_metrics = []
    price_df = None
    if csv_path is not None:
        price_df = load_nse_csv_price_history(csv_path)
        technical_metrics = compute_all_technical_indicators(price_df["close"], price_df["volume"])
        trail.record(
            f"Loaded {len(price_df)} trading day(s) of price history "
            f"({price_df.index.min().date()} to {price_df.index.max().date()})",
            source=csv_path.name, confidence="high",
        )

    company = Company(name=company_name, ticker=ticker, exchange=exchange, sector=sector)

    return {
        "company": company, "statements": statements, "price_df": price_df,
        "fundamental_metrics": fundamental_metrics, "cashflow_metrics": cashflow_metrics,
        "working_capital_metrics": working_capital_metrics, "shareholder_metrics": shareholder_metrics,
        "technical_metrics": technical_metrics,
        "valuation_metrics": valuation_metrics, "trends": trends, "risks": risks,
        "validation_issues": validation_issues, "audit_trail": trail,
    }


def apply_promoter_override(
    statements: list, promoter_holding_pct: float | None, promoter_pledge_pct: float | None,
) -> list:
    """Pure function: return a new statements list with the LATEST
    period's promoter_holding_pct/promoter_pledge_pct set to the given
    values (None values leave the corresponding field untouched, so a
    caller can set only one of the two). Earlier periods are never
    touched — this is a point-in-time override for the most recent
    filing, not a retroactive assumption applied across history."""
    if not statements:
        return statements
    updated = list(statements)
    update: dict = {}
    if promoter_holding_pct is not None:
        update["promoter_holding_pct"] = promoter_holding_pct
    if promoter_pledge_pct is not None:
        update["promoter_pledge_pct"] = promoter_pledge_pct
    if update:
        updated[-1] = updated[-1].model_copy(update=update)
    return updated


def render() -> None:
    st.header("Company Input")
    st.caption(
        "Load a Screener.in-format Excel export for financials. Price history "
        "(CSV) is optional and unlocks the Technical Dashboard. Any combination "
        "of document types below is optional and unlocks AI-assisted "
        "Business/Management/Risk analysis on later pages — each document's "
        "evidence is tagged with its type so the report can distinguish, e.g., "
        "a claim sourced from an earnings call versus the annual report."
    )

    with st.form("company_input_form"):
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("Company Name", placeholder="e.g. Sona BLW Precision Forgings Ltd")
            ticker = st.text_input("Ticker", placeholder="e.g. SONACOMS")
        with col2:
            exchange = st.selectbox("Exchange", ["NSE", "BSE"])
            sector = st.text_input("Sector (optional)", placeholder="e.g. Auto Ancillary")

        excel_file = st.file_uploader("Financials (Screener.in Excel export)", type=["xlsx"])
        csv_file = st.file_uploader("Price History CSV (NSE export, optional)", type=["csv"])
        shareholding_csv_file = st.file_uploader(
            "Shareholding Pattern CSV (NSE export, optional)", type=["csv"],
            help="NSE's own quarterly Shareholding Pattern export for this symbol. "
                 "Promoter holding is applied to any period whose fiscal year-end "
                 "exactly matches a filing date — periods without an exact match "
                 "stay unavailable rather than approximated from a nearby quarter. "
                 "This file does not contain pledge data.",
        )

        st.markdown("**Documents (optional, any combination)**")
        doc_col1, doc_col2 = st.columns(2)
        with doc_col1:
            annual_report_file = st.file_uploader("Annual Report PDF", type=["pdf"], key="ar_pdf")
            presentation_file = st.file_uploader("Investor Presentation PDF", type=["pdf"], key="ip_pdf")
            transcript_file = st.file_uploader("Earnings Call Transcript PDF", type=["pdf"], key="ect_pdf")
        with doc_col2:
            announcement_file = st.file_uploader("Corporate Announcement PDF", type=["pdf"], key="ca_pdf")
            pledge_file = st.file_uploader(
                "Promoter Pledge Disclosure PDF", type=["pdf"], key="pd_pdf",
                help="A SEBI Regulation 31 (or similar) pledge/encumbrance "
                     "disclosure filing. Extraction happens as an explicit "
                     "step on the Risk Dashboard after upload, not automatically.",
            )

        st.markdown("**Quarterly Updates (optional, any combination)**")
        st.caption(
            "Kept as a distinct source category from the annual-report documents "
            "above — a claim sourced from last quarter's investor meet carries "
            "different recency than one from the annual report, and the report/"
            "audit trail preserves that distinction rather than merging them."
        )
        q_col1, q_col2, q_col3 = st.columns(3)
        with q_col1:
            quarterly_results_file = st.file_uploader(
                "Latest Quarterly Results PDF", type=["pdf"], key="qr_pdf",
            )
        with q_col2:
            quarterly_presentation_file = st.file_uploader(
                "Investor Presentation (Quarterly Meet) PDF", type=["pdf"], key="qip_pdf",
            )
        with q_col3:
            quarterly_transcript_file = st.file_uploader(
                "Transcript of Quarterly Investor Meet PDF", type=["pdf"], key="qt_pdf",
            )

        submitted = st.form_submit_button("Run Analysis")

    if submitted:
        if not company_name or not ticker or not excel_file:
            st.error("Company Name, Ticker, and a Financials Excel file are required.")
        else:
            trail = st.session_state.get("audit_trail") or AuditTrail()

            with st.spinner("Running deterministic analysis pipeline..."):
                try:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        tmp_excel = Path(tmpdir) / "financials.xlsx"
                        tmp_excel.write_bytes(excel_file.getvalue())

                        tmp_csv = None
                        if csv_file is not None:
                            tmp_csv = Path(tmpdir) / "prices.csv"
                            tmp_csv.write_bytes(csv_file.getvalue())

                        result = run_deterministic_pipeline(
                            tmp_excel, company_name, ticker, ExchangeCode(exchange), sector or None,
                            tmp_csv, audit_trail=trail,
                        )

                        from app.documents.extractor import extract_document
                        from app.core.enums import DocumentType

                        all_document_evidence = []
                        for uploaded_file, doc_type, doc_label in (
                            (annual_report_file, DocumentType.ANNUAL_REPORT, "Annual Report"),
                            (presentation_file, DocumentType.INVESTOR_PRESENTATION, "Investor Presentation"),
                            (transcript_file, DocumentType.EARNINGS_CALL_TRANSCRIPT, "Earnings Call Transcript"),
                            (announcement_file, DocumentType.CORPORATE_ANNOUNCEMENT, "Corporate Announcement"),
                            (pledge_file, DocumentType.PLEDGE_DISCLOSURE, "Promoter Pledge Disclosure"),
                            (quarterly_results_file, DocumentType.QUARTERLY_RESULTS, "Quarterly Results"),
                            (quarterly_presentation_file, DocumentType.QUARTERLY_INVESTOR_PRESENTATION,
                             "Quarterly Investor Presentation"),
                            (quarterly_transcript_file, DocumentType.QUARTERLY_MEET_TRANSCRIPT,
                             "Quarterly Meet Transcript"),
                        ):
                            if uploaded_file is None:
                                continue
                            tmp_pdf = Path(tmpdir) / uploaded_file.name
                            tmp_pdf.write_bytes(uploaded_file.getvalue())
                            document_evidence = extract_document(
                                tmp_pdf, source_document=f"{company_name} {doc_label}",
                                document_type=doc_type,
                            )
                            all_document_evidence.extend(document_evidence)
                            flagged = sum(1 for e in document_evidence if e.quarantine_flagged)
                            trail.record(
                                f"Extracted {len(document_evidence)} page(s) from {doc_label.lower()}"
                                + (f" ({flagged} page(s) had content quarantined)" if flagged else ""),
                                source=uploaded_file.name, confidence="high",
                            )

                        result["document_evidence"] = all_document_evidence

                        if shareholding_csv_file is not None:
                            tmp_shareholding = Path(tmpdir) / "shareholding.csv"
                            tmp_shareholding.write_bytes(shareholding_csv_file.getvalue())
                            from app.data.loaders import (
                                apply_shareholding_history_to_statements,
                                load_nse_shareholding_pattern_csv,
                            )
                            # NOTE: compute_all_shareholder_metrics is already
                            # imported at module level (top of this file) — do
                            # NOT re-import it here. A local import anywhere
                            # inside render() makes Python treat the name as
                            # local for the ENTIRE function, shadowing the
                            # module-level import even in code paths that never
                            # execute this branch — this caused a real
                            # UnboundLocalError on the "Apply Promoter Data"
                            # button (a different branch, further down) when a
                            # user never uploaded a shareholding CSV in the
                            # same run.

                            records = load_nse_shareholding_pattern_csv(tmp_shareholding)
                            updated_statements, match_count = apply_shareholding_history_to_statements(
                                result["statements"], records,
                            )
                            result["statements"] = updated_statements
                            result["shareholder_metrics"] = compute_all_shareholder_metrics(updated_statements)

                            if match_count:
                                periods = [s.period for s in updated_statements]
                                holdings = [s.promoter_holding_pct for s in updated_statements]
                                holding_trend = compute_multi_period_trend(
                                    "Promoter Holding", periods, holdings, higher_is_better=True,
                                )
                                result["trends"].append(holding_trend)
                                result["risks"] = detect_financial_risks(
                                    result["fundamental_metrics"] + result["cashflow_metrics"],
                                    result["trends"],
                                )

                            trail.record(
                                f"Applied promoter holding history to {match_count} of "
                                f"{len(result['statements'])} period(s) (exact fiscal year-end date match)",
                                source=shareholding_csv_file.name, confidence="high",
                                evidence=f"{len(records)} filing(s) parsed from the uploaded shareholding-pattern export.",
                            )

                except Exception as exc:
                    logger.exception("Pipeline failed")
                    st.error(f"Analysis failed: {exc}")
                    result = None

            if result is not None:
                for key, value in result.items():
                    if key == "validation_issues":
                        continue
                    st.session_state[key] = value

                # A fresh "Run Analysis" represents a new/re-loaded company
                # dataset — report history from a prior company (or a prior
                # version of this same company's data) is not meaningful to
                # keep mixed in, so it resets here explicitly. This is a
                # deliberate reset, not an accidental data loss: documented
                # in docs/USER_GUIDE.md so it's not a surprise.
                st.session_state["report_history"] = []

                st.success(f"Loaded {len(result['statements'])} periods for {company_name}.")

                issues = result.get("validation_issues", [])
                if issues:
                    st.warning(f"{len(issues)} data validation issue(s) found:")
                    for issue in issues:
                        st.text(f"[{issue.severity.value.upper()}] {issue.rule}: {issue.message}")
                else:
                    st.info("No data validation issues found.")

                if result.get("document_evidence"):
                    from collections import Counter
                    type_counts = Counter(e.document_type.value for e in result["document_evidence"])
                    breakdown = ", ".join(f"{v} page(s) from {k.replace('_', ' ')}" for k, v in type_counts.items())
                    st.info(
                        f"Extracted {len(result['document_evidence'])} total pages ({breakdown}). "
                        "Go to Risk Dashboard or Final Thesis to run AI-assisted analysis on them."
                    )

    # Manual Promoter Holding/Pledge entry — always shown once financials
    # are loaded, regardless of whether THIS rerun just submitted the form
    # above, so it's reachable on a normal page visit too.
    statements = st.session_state.get("statements", [])
    if statements:
        st.markdown("---")
        st.subheader("Promoter Holding / Pledge (Manual Entry)")
        st.caption(
            "Not present in the Screener export this application consumes — "
            "enter it here if you have it (e.g. from the exchange's "
            "shareholding-pattern filing) to unlock these two metrics for the "
            "latest period. Left blank, they stay explicitly unavailable "
            "rather than silently omitted."
        )
        latest = statements[-1]
        col1, col2 = st.columns(2)
        with col1:
            holding_input = st.number_input(
                f"Promoter Holding % ({latest.period})", min_value=0.0, max_value=100.0,
                value=float(latest.promoter_holding_pct * 100) if latest.promoter_holding_pct is not None else 0.0,
                step=0.1, format="%.2f",
            )
        with col2:
            no_pledge_confirmed = st.checkbox(
                "I confirm there is no promoter pledge currently",
                help="Use this when you personally know (e.g. from a recent "
                     "filing or your own tracking) that no promoter shares are "
                     "pledged, even without uploading a document here. This is "
                     "recorded as a USER ASSERTION, distinct from a value "
                     "extracted from an actual pledge-disclosure filing — the "
                     "system never assumes this on its own from the mere "
                     "absence of an uploaded document.",
            )
            pledge_input = st.number_input(
                f"Promoter Pledge % ({latest.period})", min_value=0.0, max_value=100.0,
                value=0.0 if no_pledge_confirmed else (
                    float(latest.promoter_pledge_pct * 100) if latest.promoter_pledge_pct is not None else 0.0
                ),
                step=0.1, format="%.2f", disabled=no_pledge_confirmed,
            )
        if st.button("Apply Promoter Data"):
            effective_pledge = 0.0 if no_pledge_confirmed else pledge_input
            updated_statements = apply_promoter_override(
                statements, holding_input / 100.0, effective_pledge / 100.0,
            )
            st.session_state["statements"] = updated_statements
            st.session_state["shareholder_metrics"] = compute_all_shareholder_metrics(updated_statements)

            trail = st.session_state.get("audit_trail") or AuditTrail()
            pledge_note = (
                "Promoter Pledge recorded as 0% — USER-ASSERTED absence of pledge "
                "(checkbox), not derived from an uploaded pledge-disclosure document."
                if no_pledge_confirmed else
                f"Promoter Pledge manually entered as {pledge_input:.2f}%."
            )
            trail.record(
                f"Promoter Holding manually entered as {holding_input:.2f}% for {latest.period}. {pledge_note}",
                source="Manual UI entry", confidence="medium",
                evidence="Not independently verified by this application.",
            )
            st.session_state["audit_trail"] = trail

            st.success("Promoter data applied to the latest period.")
