"""Tests for app/ui/session_io.py's save/reload serialization, and the
sidebar UI wiring in dashboard.py.

Round-trip tests use real Sona BLW data (statements, price history,
document evidence) rather than synthetic fixtures throughout, since the
whole point of this feature is faithfully restoring a genuine working
session.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.core.audit import AuditTrail
from app.core.enums import DocumentType, ExchangeCode
from app.core.models import Company, HumanReview
from app.analysis.fundamentals import compute_ebitda_margin, compute_roe
from app.analysis.risk import detect_financial_risks
from app.data.market_data import load_nse_csv_price_history
from app.documents.extractor import extract_document
from app.ui.session_io import deserialize_session, serialize_session

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_CSV = PROJECT_ROOT / "data" / "sample" / "SONACOMS_NSE_price_history.csv"
SAMPLE_PLEDGE_PDF = PROJECT_ROOT / "data" / "sample" / "SONACOMS_pledge_disclosure_2021.pdf"


class TestRoundTripRealData:
    def test_company_round_trips(self, sona_blw_statements):
        company = Company(name="Sona BLW Precision Forgings Ltd", ticker="SONACOMS",
                           exchange=ExchangeCode.NSE, sector="Auto Ancillary")
        session = {"company": company}
        restored, warnings = deserialize_session(serialize_session(session))
        assert warnings == []
        assert restored["company"].name == company.name
        assert restored["company"].ticker == company.ticker

    def test_statements_round_trip_exactly(self, sona_blw_statements):
        session = {"statements": sona_blw_statements}
        restored, warnings = deserialize_session(serialize_session(session))
        assert warnings == []
        assert len(restored["statements"]) == len(sona_blw_statements)
        fy26_original = sona_blw_statements[-1]
        fy26_restored = restored["statements"][-1]
        assert fy26_restored.sales == fy26_original.sales
        assert fy26_restored.net_profit == fy26_original.net_profit
        assert fy26_restored.period == fy26_original.period

    def test_price_dataframe_round_trips_exactly(self):
        df = load_nse_csv_price_history(SAMPLE_CSV)
        session = {"price_df": df}
        restored, warnings = deserialize_session(serialize_session(session))
        assert warnings == []
        assert restored["price_df"].shape == df.shape
        assert (restored["price_df"]["close"] == df["close"]).all()
        assert (restored["price_df"]["volume"] == df["volume"]).all()

    def test_none_price_dataframe_round_trips_as_none(self):
        session = {"price_df": None}
        restored, warnings = deserialize_session(serialize_session(session))
        assert restored["price_df"] is None
        assert warnings == []

    def test_metrics_round_trip(self, sona_blw_statements):
        fy26 = sona_blw_statements[-1]
        metrics = [compute_ebitda_margin(fy26), compute_roe(fy26)]
        session = {"fundamental_metrics": metrics}
        restored, warnings = deserialize_session(serialize_session(session))
        assert warnings == []
        assert len(restored["fundamental_metrics"]) == 2
        assert restored["fundamental_metrics"][0].value == metrics[0].value
        assert restored["fundamental_metrics"][0].formula == metrics[0].formula

    def test_risks_round_trip(self, sona_blw_statements):
        fy26 = sona_blw_statements[-1]
        from app.analysis.fundamentals import compute_debt_to_equity

        metrics = [compute_debt_to_equity(fy26)]
        risks = detect_financial_risks(metrics)
        session = {"risks": risks}
        restored, warnings = deserialize_session(serialize_session(session))
        assert warnings == []
        assert len(restored["risks"]) == len(risks)

    def test_document_evidence_round_trips_with_real_pdf(self):
        evidence = extract_document(
            SAMPLE_PLEDGE_PDF, source_document="Sona BLW Pledge Disclosure",
            document_type=DocumentType.PLEDGE_DISCLOSURE,
        )
        session = {"document_evidence": evidence}
        restored, warnings = deserialize_session(serialize_session(session))
        assert warnings == []
        assert len(restored["document_evidence"]) == len(evidence)
        assert restored["document_evidence"][3].raw_text == evidence[3].raw_text
        assert restored["document_evidence"][0].document_type == DocumentType.PLEDGE_DISCLOSURE

    def test_audit_trail_round_trips(self):
        trail = AuditTrail()
        trail.record("Loaded 10 periods", source="test.xlsx", confidence="high")
        trail.record("EBITDA Margin = 0.25", source="test.xlsx", calculation="EBITDA/Sales", confidence="high")
        session = {"audit_trail": trail}
        restored, warnings = deserialize_session(serialize_session(session))
        assert warnings == []
        assert len(restored["audit_trail"]) == 2
        assert restored["audit_trail"].entries[0].claim == "Loaded 10 periods"
        assert restored["audit_trail"].entries[1].calculation == "EBITDA/Sales"

    def test_none_audit_trail_round_trips_as_empty_trail(self):
        session = {"audit_trail": None}
        restored, warnings = deserialize_session(serialize_session(session))
        assert warnings == []
        assert len(restored["audit_trail"]) == 0

    def test_human_reviews_round_trip(self):
        review = HumanReview(target_id="interp_1", reviewer_name="Surendra", accepted=True, reviewer_notes="Looks right")
        session = {"human_reviews": [review]}
        restored, warnings = deserialize_session(serialize_session(session))
        assert warnings == []
        assert restored["human_reviews"][0].reviewer_name == "Surendra"
        assert restored["human_reviews"][0].accepted is True
        assert restored["human_reviews"][0].reviewer_notes == "Looks right"

    def test_plain_fields_round_trip(self):
        session = {
            "reviewer_name": "Surendra Agarwal",
            "weight_sliders": {"Fundamentals": 40.0, "Valuation": 20.0},
            "sensitivity_grid": {"10.0%": {"5.0%": 150.0, "6.0%": None}},
        }
        restored, warnings = deserialize_session(serialize_session(session))
        assert warnings == []
        assert restored["reviewer_name"] == "Surendra Agarwal"
        assert restored["weight_sliders"] == {"Fundamentals": 40.0, "Valuation": 20.0}
        assert restored["sensitivity_grid"] == {"10.0%": {"5.0%": 150.0, "6.0%": None}}

    def test_full_realistic_session_round_trips_with_zero_warnings(self, sona_blw_statements):
        fy26 = sona_blw_statements[-1]
        company = Company(name="Sona BLW Precision Forgings Ltd", ticker="SONACOMS", exchange=ExchangeCode.NSE)
        session = {
            "company": company,
            "statements": sona_blw_statements,
            "price_df": load_nse_csv_price_history(SAMPLE_CSV),
            "fundamental_metrics": [compute_ebitda_margin(fy26), compute_roe(fy26)],
            "risks": detect_financial_risks([compute_ebitda_margin(fy26)]),
            "audit_trail": AuditTrail(),
            "reviewer_name": "Surendra",
        }
        json_text = serialize_session(session)
        restored, warnings = deserialize_session(json_text)
        assert warnings == []
        assert restored["company"].ticker == "SONACOMS"
        assert len(restored["statements"]) == 10


class TestSchemaVersionMismatch:
    def test_mismatched_schema_version_warns_but_still_attempts_restore(self):
        import json
        from app.ui.session_io import SCHEMA_VERSION

        session = {"reviewer_name": "Test"}
        envelope = json.loads(serialize_session(session))
        envelope["schema_version"] = SCHEMA_VERSION + 99
        restored, warnings = deserialize_session(json.dumps(envelope))
        assert any("schema_version" in w for w in warnings)
        assert restored["reviewer_name"] == "Test"


class TestPartialCorruption:
    def test_one_corrupted_field_does_not_block_others(self):
        import json

        company = Company(name="Test Co", ticker="TEST", exchange=ExchangeCode.NSE)
        session = {"company": company, "reviewer_name": "Surendra"}
        envelope = json.loads(serialize_session(session))
        envelope["data"]["company"] = {"name": "Test Co"}
        restored, warnings = deserialize_session(json.dumps(envelope))

        assert len(warnings) == 1
        assert "company" in warnings[0]
        assert restored["company"] is None
        assert restored["reviewer_name"] == "Surendra"


class TestErrorHandling:
    def test_invalid_json_raises_value_error(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            deserialize_session("not valid json{{{")

    def test_missing_data_envelope_raises_value_error(self):
        with pytest.raises(ValueError, match="data"):
            deserialize_session('{"no_data_key": true}')

    def test_empty_session_serializes_and_restores_without_error(self):
        json_text = serialize_session({})
        restored, warnings = deserialize_session(json_text)
        assert warnings == []
        assert restored["statements"] == []
        assert restored["company"] is None


class TestSidebarUiRendering:
    def _app(self):
        return AppTest.from_file(str(PROJECT_ROOT / "app" / "main.py"), default_timeout=30)

    def test_save_load_controls_render_without_company(self):
        at = self._app()
        at.run()
        assert list(at.exception) == []
        captions = [c.value for c in at.sidebar.caption]
        assert any("Load a company first" in c for c in captions)

    def test_save_button_appears_once_company_loaded(self):
        at = self._app()
        at.session_state["company"] = Company(name="Test Co", ticker="TEST", exchange=ExchangeCode.NSE)
        at.run()
        assert list(at.exception) == []
        # Streamlit 1.41.1's AppTest does not expose a typed
        # `.download_button` accessor (added in a later version) — the
        # generic `.get("download_button")` lookup is the correct way
        # to query it against this project's actually-pinned version.
        assert len(at.get("download_button")) >= 1
