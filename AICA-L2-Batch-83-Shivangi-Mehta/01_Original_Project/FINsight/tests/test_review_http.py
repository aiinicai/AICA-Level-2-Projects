"""
Stage 12 — full HTTP round trip through the real Flask app for the
Unified Review Engine: Review Configuration (module checkboxes, all
selected by default, no SEBI option), the readiness-gate banner before
data is ready, running and persisting across modules, the Result
Summary, the Unified Findings Centre with filters, and the Finding
Detail page.

Mirrors tests/test_accounting_http.py / test_tax_http.py's fixture
shape. Also re-confirms (lightly) that the three individual engine
screens are untouched and still reachable directly, since Stage 12 must
not require visiting them separately, not remove them.

Uses only synthetic, fabricated CSV content — never real client or
financial data, per the standing instruction.
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest

from config import TestConfig
from app import create_app


@pytest.fixture()
def client(tmp_path):
    class IsolatedConfig(TestConfig):
        DATA_INPUT_DIR = tmp_path / "data_input"

    app = create_app(IsolatedConfig)
    from app import extensions
    from app.models import Base

    Base.metadata.create_all(extensions.engine)
    return app.test_client()


def body(resp):
    return resp.get_data(as_text=True)


def _create_and_select_engagement(client, entity_name="Acme Manufacturing Ltd", financial_year="2025-26"):
    r = client.post(
        "/engagement/new",
        data={"entity_name": entity_name, "financial_year": financial_year},
        follow_redirects=False,
    )
    assert r.status_code == 302


def _save_entity_profile(client, accounting_framework="AS"):
    from app.services import engagement_service

    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    engagement_service.save_entity_profile(engagement_id, {
        "entity_type": "Company", "industry": None, "is_listed": False,
        "accounting_framework": accounting_framework, "is_gst_registered": False,
        "statutory_audit_applicable": False, "tax_audit_status": "REQUIRES_REVIEW",
        "consolidated_fs_applicable": False, "prior_year_data_available": False,
        "turnover": None, "overall_materiality": None, "performance_materiality": None,
        "clearly_trivial_threshold": None,
    })


def _csv_bytes(rows) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue()


def _upload_map_validate(client, file_type, filename, rows, field_names):
    r = client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(_csv_bytes(rows)), filename), "file_type": file_type},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302

    from app.services import upload_service
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    file_id = upload_service.list_uploads(engagement_id)[-1].file_id

    r = client.post(f"/data/mapping/{file_id}/", data={
        f"target_field__{i}": field for i, field in enumerate(field_names)
    }, follow_redirects=False)
    assert r.status_code == 302

    from app.services import mapping_service
    mapping_service.mark_file_status(file_id, "VALIDATED")
    return file_id


def _seed_tax_msme_rule():
    from app import extensions
    from app.models.rules import TaxRule
    extensions.SessionLocal.add(TaxRule(
        rule_id="TAX-MSME-013", topic="MSME Delayed-Payment Review Screen",
        is_active=True, verification_status="VERIFIED",
        legislative_act="IT_ACT_1961", provision_reference="Section 43B(h), Income-tax Act, 1961",
        suggested_action="Confirm MSME registration and agreed payment terms before concluding on disallowance.",
    ))
    extensions.SessionLocal.commit()


# --- no engagement ------------------------------------------------------------

def test_review_index_with_no_engagement_shows_selection_prompt(client):
    r = client.get("/review/")
    assert r.status_code == 200
    assert "No current engagement selected" in body(r)


def test_findings_centre_with_no_engagement_shows_selection_prompt(client):
    r = client.get("/review/findings")
    assert r.status_code == 200
    assert "No current engagement selected" in body(r)


# --- readiness gate -------------------------------------------------------

def test_review_blocked_with_exact_required_message_before_any_upload(client):
    _create_and_select_engagement(client)
    r = client.get("/review/")
    assert r.status_code == 200
    assert "Review cannot be started until the data mapping and validation are completed." in body(r)


def test_review_blocked_shows_upload_status_table_when_a_file_is_not_yet_validated(client):
    _create_and_select_engagement(client)
    r = client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(_csv_bytes([{"Description": "x", "Debit": 1, "Credit": 0}])), "je.csv"),
              "file_type": "JE"},
        content_type="multipart/form-data",
    )
    assert r.status_code == 302

    r = client.get("/review/")
    page = body(r)
    assert "Review cannot be started" in page
    assert "je.csv" in page
    assert "Upload Status" in page


def test_post_run_review_refuses_to_run_when_not_ready(client):
    _create_and_select_engagement(client)
    r = client.post("/review/", data={"modules": ["ACCOUNTING", "AUDIT", "TAX"]})
    assert r.status_code == 200
    page = body(r)
    assert "Review cannot be started until the data mapping and validation are completed." in page
    assert "Review Result Summary" not in page


# --- module checkboxes, no SEBI ----------------------------------------------

def test_configuration_screen_defaults_all_three_modules_checked_and_has_no_sebi_option(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _upload_map_validate(client, "AP", "ap.csv", [
        {"Party Name": "Bright Traders", "Transaction Date": "01-06-2025", "Credit Amount": "50000", "Debit Amount": ""},
    ], ["party_name", "transaction_date", "credit_amount", "debit_amount"])
    r = client.get("/review/")
    page = body(r)
    assert 'name="modules" value="ACCOUNTING"' in page
    assert 'name="modules" value="AUDIT"' in page
    assert 'name="modules" value="TAX"' in page
    assert 'value="ACCOUNTING" checked' in page
    assert 'value="AUDIT" checked' in page
    assert 'value="TAX" checked' in page
    assert 'name="modules" value="SEBI"' not in page
    assert "outside current V1 scope, not selectable" in page


# --- full run: all three modules ---------------------------------------------

def test_running_all_three_modules_persists_and_shows_result_summary(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _upload_map_validate(client, "AP", "ap.csv", [
        {"Party Name": "Bright Traders", "Transaction Date": "01-06-2025", "Credit Amount": "50000", "Debit Amount": ""},
    ], ["party_name", "transaction_date", "credit_amount", "debit_amount"])
    _seed_tax_msme_rule()

    r = client.post("/review/", data={"modules": ["ACCOUNTING", "AUDIT", "TAX"]})
    assert r.status_code == 200
    page = body(r)
    assert "Review Result Summary" in page
    assert "1 finding(s) recorded this run" in page
    assert "Tax" in page and "Completed" in page

    from app.services import unified_review_service as usvc
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    findings = usvc.get_unified_findings(engagement_id)
    assert len(findings) == 1
    assert findings[0].module == "TAX"


def test_running_only_the_selected_modules(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _upload_map_validate(client, "AP", "ap.csv", [
        {"Party Name": "Bright Traders", "Transaction Date": "01-06-2025", "Credit Amount": "50000", "Debit Amount": ""},
    ], ["party_name", "transaction_date", "credit_amount", "debit_amount"])
    _seed_tax_msme_rule()

    r = client.post("/review/", data={"modules": ["ACCOUNTING"]})
    assert r.status_code == 200

    from app.services import unified_review_service as usvc
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    summary = usvc.preview_unified_review(engagement_id, ("ACCOUNTING",))
    assert [o.module for o in summary.module_outcomes] == ["ACCOUNTING"]
    # Tax's MSME rule never ran on this POST, so it never persisted anything.
    assert usvc.get_unified_findings(engagement_id) == []


def test_rerun_via_http_does_not_duplicate(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _upload_map_validate(client, "AP", "ap.csv", [
        {"Party Name": "Bright Traders", "Transaction Date": "01-06-2025", "Credit Amount": "50000", "Debit Amount": ""},
    ], ["party_name", "transaction_date", "credit_amount", "debit_amount"])
    _seed_tax_msme_rule()

    client.post("/review/", data={"modules": ["TAX"]})
    client.post("/review/", data={"modules": ["TAX"]})

    from app.services import unified_review_service as usvc
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    assert len(usvc.get_unified_findings(engagement_id)) == 1


# --- Unified Findings Centre --------------------------------------------------

def test_findings_centre_lists_finding_and_links_to_detail(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _upload_map_validate(client, "AP", "ap.csv", [
        {"Party Name": "Bright Traders", "Transaction Date": "01-06-2025", "Credit Amount": "50000", "Debit Amount": ""},
    ], ["party_name", "transaction_date", "credit_amount", "debit_amount"])
    _seed_tax_msme_rule()
    client.post("/review/", data={"modules": ["TAX"]})

    r = client.get("/review/findings")
    assert r.status_code == 200
    page = body(r)
    assert "TAX-MSME-013" in page
    assert "MSME Delayed-Payment Review Screen" in page
    assert "Total Findings" in page
    assert "/review/findings/TAX/1" in page


def test_findings_centre_module_filter_narrows_results(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _upload_map_validate(client, "AP", "ap.csv", [
        {"Party Name": "Bright Traders", "Transaction Date": "01-06-2025", "Credit Amount": "50000", "Debit Amount": ""},
    ], ["party_name", "transaction_date", "credit_amount", "debit_amount"])
    _seed_tax_msme_rule()
    client.post("/review/", data={"modules": ["TAX"]})

    r = client.get("/review/findings?module=ACCOUNTING")
    page = body(r)
    assert "Findings (0)" in page

    r = client.get("/review/findings?module=TAX")
    page = body(r)
    assert "Findings (1)" in page
    assert "TAX-MSME-013" in page


def test_finding_detail_page_shows_tax_specific_fields(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _upload_map_validate(client, "AP", "ap.csv", [
        {"Party Name": "Bright Traders", "Transaction Date": "01-06-2025", "Credit Amount": "50000", "Debit Amount": ""},
    ], ["party_name", "transaction_date", "credit_amount", "debit_amount"])
    _seed_tax_msme_rule()
    client.post("/review/", data={"modules": ["TAX"]})

    r = client.get("/review/findings/TAX/1")
    assert r.status_code == 200
    page = body(r)
    assert "Tax-Specific" in page
    assert "IT_ACT_1961" in page
    assert "Section 43B(h)" in page


def test_finding_detail_page_404s_for_unknown_finding(client):
    _create_and_select_engagement(client)
    r = client.get("/review/findings/TAX/999999")
    assert r.status_code == 404


def test_finding_detail_page_404s_for_sebi_module(client):
    _create_and_select_engagement(client)
    r = client.get("/review/findings/SEBI/1")
    assert r.status_code == 404


# --- individual engines remain independently reachable and unaffected -------

def test_individual_engine_screens_still_work_directly(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    for path in ("/review/accounting/", "/review/audit/", "/review/tax/"):
        r = client.get(path)
        assert r.status_code == 200


def test_sidebar_offers_findings_centre_alongside_the_three_engines(client):
    # Stage 18 (approved): the standalone "Run Review" sidebar link was
    # removed — running a review is now a one-click action on the
    # Upload screen (see tests/test_stage18_upload_automation.py). The
    # `/review/` route itself is untouched and still fully works; only
    # this sidebar link is gone, so this test no longer asserts it.
    r = client.get("/")
    page = body(r)
    assert 'href="/review/findings"' in page
    assert 'href="/review/accounting/"' in page
    assert 'href="/review/audit/"' in page
    assert 'href="/review/tax/"' in page
