"""Tests for app/reports/history.py's pure functions, session_io.py's
round-trip of report_history, and real AppTest interaction confirming
history accumulates correctly across multiple 'Generate Report' clicks.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.core.enums import ExchangeCode, Recommendation
from app.core.models import Company, InvestmentScore, InvestmentThesis
from app.reports.generator import ReportContext, generate_report
from app.reports.history import ReportHistoryEntry, build_history_entry, summarize_score_progression
from app.ui.session_io import deserialize_session, serialize_session

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _ctx(score_val, rec, thesis_present=True):
    company = Company(name="Sona BLW Precision Forgings Ltd", ticker="SONACOMS", exchange=ExchangeCode.NSE)
    score = InvestmentScore(overall_score=score_val, components=[], weights_used={}) if score_val is not None else None
    thesis = InvestmentThesis(recommendation=rec, core_thesis="Test") if thesis_present else None
    return ReportContext(company=company, investment_score=score, thesis=thesis)


class TestBuildHistoryEntry:
    def test_captures_company_and_score(self):
        ctx = _ctx(75.0, Recommendation.HOLD)
        report_md = generate_report(ctx)
        entry = build_history_entry(ctx, report_md)
        assert entry.company_name == "Sona BLW Precision Forgings Ltd"
        assert entry.ticker == "SONACOMS"
        assert entry.overall_score == 75.0
        assert entry.recommendation == "hold"

    def test_stores_full_markdown_verbatim(self):
        ctx = _ctx(75.0, Recommendation.HOLD)
        report_md = generate_report(ctx)
        entry = build_history_entry(ctx, report_md)
        assert entry.report_markdown == report_md
        assert len(entry.report_markdown) > 100

    def test_missing_score_and_thesis_stored_as_none(self):
        ctx = _ctx(None, None, thesis_present=False)
        report_md = generate_report(ctx)
        entry = build_history_entry(ctx, report_md)
        assert entry.overall_score is None
        assert entry.recommendation is None

    def test_each_entry_gets_a_unique_id(self):
        ctx = _ctx(75.0, Recommendation.HOLD)
        report_md = generate_report(ctx)
        entry1 = build_history_entry(ctx, report_md)
        entry2 = build_history_entry(ctx, report_md)
        assert entry1.entry_id != entry2.entry_id


def _entry(score, report_markdown="x", recommendation=None, day=1):
    e = ReportHistoryEntry(
        company_name="X", ticker="X", overall_score=score,
        recommendation=recommendation, report_markdown=report_markdown,
    )
    e.generated_at = datetime.datetime(2026, 1, day, tzinfo=datetime.timezone.utc)
    return e


class TestSummarizeScoreProgression:
    def test_chronological_ordering(self):
        entries = [_entry(80.0, day=3), _entry(60.0, day=1), _entry(70.0, day=2)]
        rows = summarize_score_progression(entries)
        assert [r["Score"] for r in rows] == ["60.0", "70.0", "80.0"]

    def test_first_entry_has_no_change(self):
        rows = summarize_score_progression([_entry(60.0, day=1)])
        assert rows[0]["Change"] == "\u2014"

    def test_change_computed_correctly_between_consecutive_entries(self):
        entries = [_entry(55.0, day=1), _entry(81.8, day=2)]
        rows = summarize_score_progression(entries)
        assert rows[0]["Score"] == "55.0"
        assert rows[1]["Change"] == "+26.8"

    def test_missing_score_produces_no_fabricated_change(self):
        entries = [_entry(55.0, day=1), _entry(None, day=2)]
        rows = summarize_score_progression(entries)
        assert rows[1]["Score"] == "N/A"
        assert rows[1]["Change"] == "\u2014"

    def test_recommendation_uppercased(self):
        rows = summarize_score_progression([_entry(None, recommendation="buy", day=1)])
        assert rows[0]["Recommendation"] == "BUY"

    def test_no_recommendation_shows_na(self):
        rows = summarize_score_progression([_entry(None, day=1)])
        assert rows[0]["Recommendation"] == "N/A"

    def test_empty_history_returns_empty_rows(self):
        assert summarize_score_progression([]) == []


class TestSessionIoRoundTrip:
    def test_report_history_round_trips(self):
        ctx = _ctx(75.0, Recommendation.HOLD)
        report_md = generate_report(ctx)
        entry = build_history_entry(ctx, report_md)

        session = {"report_history": [entry]}
        restored, warnings = deserialize_session(serialize_session(session))
        assert warnings == []
        assert len(restored["report_history"]) == 1
        assert restored["report_history"][0].report_markdown == entry.report_markdown
        assert restored["report_history"][0].overall_score == 75.0

    def test_multiple_entries_preserve_order_and_content(self):
        entries = []
        for score in (50.0, 65.0, 80.0):
            ctx = _ctx(score, Recommendation.HOLD)
            entries.append(build_history_entry(ctx, generate_report(ctx)))

        session = {"report_history": entries}
        restored, warnings = deserialize_session(serialize_session(session))
        assert warnings == []
        assert [e.overall_score for e in restored["report_history"]] == [50.0, 65.0, 80.0]

    def test_empty_history_round_trips_as_empty(self):
        restored, warnings = deserialize_session(serialize_session({"report_history": []}))
        assert warnings == []
        assert restored["report_history"] == []


class TestRealAppInteraction:
    def _app_with_company(self):
        at = AppTest.from_file(str(PROJECT_ROOT / "app" / "main.py"), default_timeout=30)
        at.session_state["company"] = Company(
            name="Sona BLW Precision Forgings Ltd", ticker="SONACOMS", exchange=ExchangeCode.NSE,
        )
        at.run()
        at.sidebar.radio[0].set_value("Final Thesis & Report").run()
        return at

    def test_generate_report_appends_to_history(self):
        at = self._app_with_company()
        at.session_state["investment_score"] = InvestmentScore(overall_score=55.0, components=[], weights_used={})
        gen_btn = next(b for b in at.button if b.label == "Generate Report")
        gen_btn.click().run()
        assert list(at.exception) == []
        assert len(at.session_state["report_history"]) == 1

    def test_multiple_generations_accumulate_not_overwrite(self):
        at = self._app_with_company()
        for score in (55.0, 68.0, 81.8):
            at.session_state["investment_score"] = InvestmentScore(overall_score=score, components=[], weights_used={})
            gen_btn = next(b for b in at.button if b.label == "Generate Report")
            gen_btn.click().run()
        assert list(at.exception) == []
        history = at.session_state["report_history"]
        assert len(history) == 3
        assert [e.overall_score for e in history] == [55.0, 68.0, 81.8]

    def test_history_section_renders_after_generation(self):
        at = self._app_with_company()
        at.session_state["investment_score"] = InvestmentScore(overall_score=55.0, components=[], weights_used={})
        gen_btn = next(b for b in at.button if b.label == "Generate Report")
        gen_btn.click().run()
        assert list(at.exception) == []
        headers = [h.value for h in at.subheader]
        assert any("Report History" in h for h in headers)
