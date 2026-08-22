"""Tests for the audit trail wiring (company_input.py) and the Human
Review page's pure upsert logic (human_review.py)."""

from __future__ import annotations

from pathlib import Path

from app.core.audit import AuditTrail
from app.core.enums import ExchangeCode
from app.core.models import HumanReview
from app.ui.pages.company_input import run_deterministic_pipeline
from app.ui.pages.human_review import upsert_human_review

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_EXCEL = PROJECT_ROOT / "data" / "sample" / "Sona_BLW_Precis_screener_export.xlsx"
SAMPLE_CSV = PROJECT_ROOT / "data" / "sample" / "SONACOMS_NSE_price_history.csv"


class TestAuditTrailWiring:
    def test_pipeline_records_entries_into_supplied_trail(self):
        trail = AuditTrail()
        run_deterministic_pipeline(
            excel_path=SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd",
            ticker="SONACOMS", exchange=ExchangeCode.NSE, sector="Auto Ancillary",
            csv_path=SAMPLE_CSV, audit_trail=trail,
        )
        assert len(trail) > 0

    def test_pipeline_creates_own_trail_if_none_supplied(self):
        result = run_deterministic_pipeline(
            excel_path=SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd",
            ticker="SONACOMS", exchange=ExchangeCode.NSE, sector=None, csv_path=None,
        )
        assert isinstance(result["audit_trail"], AuditTrail)
        assert len(result["audit_trail"]) > 0

    def test_load_entry_has_correct_source_filename(self):
        trail = AuditTrail()
        run_deterministic_pipeline(
            excel_path=SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd",
            ticker="SONACOMS", exchange=ExchangeCode.NSE, sector=None,
            csv_path=None, audit_trail=trail,
        )
        load_entries = [e for e in trail.entries if "Loaded" in e.claim and "period" in e.claim]
        assert len(load_entries) == 1
        assert load_entries[0].source == SAMPLE_EXCEL.name

    def test_validation_issues_recorded_as_entries(self):
        trail = AuditTrail()
        run_deterministic_pipeline(
            excel_path=SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd",
            ticker="SONACOMS", exchange=ExchangeCode.NSE, sector=None,
            csv_path=None, audit_trail=trail,
        )
        flag_entries = [e for e in trail.entries if "Data validation flag" in e.claim]
        assert len(flag_entries) >= 1

    def test_key_metrics_recorded_with_formula(self):
        trail = AuditTrail()
        run_deterministic_pipeline(
            excel_path=SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd",
            ticker="SONACOMS", exchange=ExchangeCode.NSE, sector=None,
            csv_path=None, audit_trail=trail,
        )
        ebitda_entries = [e for e in trail.entries if e.claim.startswith("EBITDA Margin")]
        assert len(ebitda_entries) > 0
        assert ebitda_entries[0].calculation == "EBITDA / Sales"

    def test_price_history_load_recorded_when_csv_supplied(self):
        trail = AuditTrail()
        run_deterministic_pipeline(
            excel_path=SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd",
            ticker="SONACOMS", exchange=ExchangeCode.NSE, sector=None,
            csv_path=SAMPLE_CSV, audit_trail=trail,
        )
        price_entries = [e for e in trail.entries if "trading day" in e.claim]
        assert len(price_entries) == 1
        assert price_entries[0].source == SAMPLE_CSV.name

    def test_no_price_entry_when_csv_not_supplied(self):
        trail = AuditTrail()
        run_deterministic_pipeline(
            excel_path=SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd",
            ticker="SONACOMS", exchange=ExchangeCode.NSE, sector=None,
            csv_path=None, audit_trail=trail,
        )
        price_entries = [e for e in trail.entries if "trading day" in e.claim]
        assert price_entries == []

    def test_entries_are_exportable_as_dicts(self):
        trail = AuditTrail()
        run_deterministic_pipeline(
            excel_path=SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd",
            ticker="SONACOMS", exchange=ExchangeCode.NSE, sector=None,
            csv_path=None, audit_trail=trail,
        )
        dicts = trail.to_dicts()
        assert len(dicts) == len(trail)
        assert all("claim" in d and "confidence" in d for d in dicts)


class TestHumanReviewUpsert:
    def test_new_review_appended(self):
        reviews = upsert_human_review([], "target_1", "Surendra", True)
        assert len(reviews) == 1
        assert reviews[0].target_id == "target_1"
        assert reviews[0].accepted is True

    def test_re_review_updates_not_duplicates(self):
        reviews = upsert_human_review([], "target_1", "Surendra", True, "first note")
        reviews = upsert_human_review(reviews, "target_1", "Surendra", False, "changed my mind")
        assert len(reviews) == 1
        assert reviews[0].accepted is False
        assert reviews[0].reviewer_notes == "changed my mind"

    def test_different_targets_both_kept(self):
        reviews = upsert_human_review([], "target_1", "Surendra", True)
        reviews = upsert_human_review(reviews, "target_2", "Surendra", False)
        assert len(reviews) == 2
        target_ids = {r.target_id for r in reviews}
        assert target_ids == {"target_1", "target_2"}

    def test_notes_optional(self):
        reviews = upsert_human_review([], "target_1", "Surendra", True)
        assert reviews[0].reviewer_notes is None

    def test_original_list_not_mutated(self):
        original = [HumanReview(target_id="existing", reviewer_name="A", accepted=True)]
        result = upsert_human_review(original, "new_target", "B", False)
        assert len(original) == 1
        assert len(result) == 2

    def test_reviewer_name_recorded_correctly(self):
        reviews = upsert_human_review([], "target_1", "Surendra Agarwal", True)
        assert reviews[0].reviewer_name == "Surendra Agarwal"
