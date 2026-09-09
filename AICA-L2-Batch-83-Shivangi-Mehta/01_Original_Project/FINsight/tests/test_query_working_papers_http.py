"""
Stage 13 — full HTTP round trip through the real Flask app for the
Query Centre (`/queries/`) and Working Paper (`/exceptions/<id>/`)
screens, plus their integration with Stage 12's Findings Centre.

Mirrors tests/test_review_http.py's fixture shape.

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


def _create_and_select_engagement(client, entity_name="Acme Manufacturing Ltd"):
    r = client.post("/engagement/new", data={"entity_name": entity_name, "financial_year": "2025-26"}, follow_redirects=False)
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


def _seed_and_run_tax_msme(client):
    r = client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(_csv_bytes([
            {"Party Name": "Bright Traders", "Transaction Date": "01-06-2025", "Credit Amount": "50000", "Debit Amount": ""},
        ])), "ap.csv"), "file_type": "AP"},
        content_type="multipart/form-data", follow_redirects=False,
    )
    assert r.status_code == 302

    from app.services import upload_service
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    file_id = upload_service.list_uploads(engagement_id)[-1].file_id

    r = client.post(f"/data/mapping/{file_id}/", data={
        "target_field__0": "party_name", "target_field__1": "transaction_date",
        "target_field__2": "credit_amount", "target_field__3": "debit_amount",
    }, follow_redirects=False)
    assert r.status_code == 302

    from app.services import mapping_service
    mapping_service.mark_file_status(file_id, "VALIDATED")

    from app import extensions
    from app.models.rules import TaxRule
    extensions.SessionLocal.add(TaxRule(
        rule_id="TAX-MSME-013", topic="MSME Delayed-Payment Review Screen",
        is_active=True, verification_status="VERIFIED",
        legislative_act="IT_ACT_1961", provision_reference="Section 43B(h), Income-tax Act, 1961",
        suggested_action="Confirm MSME registration and agreed payment terms before concluding on disallowance.",
    ))
    extensions.SessionLocal.commit()

    r = client.post("/review/", data={"modules": ["TAX"]})
    assert r.status_code == 200

    from app.services import unified_review_service as usvc
    finding = usvc.get_unified_findings(engagement_id)[0]
    return finding.finding_id


# --- no engagement -------------------------------------------------------

def test_query_centre_with_no_engagement_shows_selection_prompt(client):
    r = client.get("/queries/")
    assert r.status_code == 200
    assert "No current engagement selected" in body(r)


# --- exceptions_bp redirect -----------------------------------------------

def test_exceptions_index_renders_the_query_centre_directly(client):
    # Not a redirect (would break the pre-existing Stage 2
    # test_all_nav_pages_load smoke test, which expects every nav path
    # to return 200) — /exceptions/ renders the same Query Centre
    # content queries.index() does.
    r = client.get("/exceptions/")
    assert r.status_code == 200
    assert "Query &amp; Working Papers" in body(r)


def test_working_paper_404s_for_unknown_exception(client):
    _create_and_select_engagement(client)
    r = client.get("/exceptions/999999/")
    assert r.status_code == 404


# --- Query Centre lists real data -----------------------------------------

def test_query_centre_lists_query_after_a_review_run(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    r = client.get("/queries/")
    assert r.status_code == 200
    page = body(r)
    assert "TAX-MSME-013" in page
    assert "Total Queries" in page
    assert f"/exceptions/{exception_id}/" in page


def test_query_centre_filters_by_module(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _seed_and_run_tax_msme(client)

    r = client.get("/queries/?module=ACCOUNTING")
    assert "Queries (0)" in body(r)

    r = client.get("/queries/?module=TAX")
    assert "Queries (1)" in body(r)


def test_query_centre_search_works(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _seed_and_run_tax_msme(client)

    r = client.get("/queries/?search=TAX-MSME-013")
    assert "Queries (1)" in body(r)
    r = client.get("/queries/?search=zzz-not-found")
    assert "Queries (0)" in body(r)


# --- Working Paper: view + edit --------------------------------------------

def test_working_paper_shows_original_finding_and_suggested_query(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    r = client.get(f"/exceptions/{exception_id}/")
    assert r.status_code == 200
    page = body(r)
    assert "FinSight WORKING PAPER".title() in page or "Working Paper" in page
    assert "FinSight Suggested Query" in page
    assert "MSME" in page


def test_working_paper_post_saves_reviewer_edits(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    r = client.post(f"/exceptions/{exception_id}/", data={
        "assigned_to": "Priya",
        "reviewer_query_text": "Confirm MSME status and provide Udyam certificate.",
        "management_response": "Vendor confirmed not registered.",
        "evidence_description": "Vendor declaration letter",
        "evidence_reference": "/local/evidence/vendor.pdf",
        "reviewer_comments": "", "resolution": "",
        "reviewer_notes": "Following up.",
        "status": "UNDER_REVIEW", "status_reason": "",
    })
    assert r.status_code == 200
    page = body(r)
    assert "Saved." in page
    assert "Confirm MSME status and provide Udyam certificate." in page

    from app.services import query_service
    wp = query_service.get_working_paper(exception_id)
    assert wp.query.reviewer_query_text == "Confirm MSME status and provide Udyam certificate."
    assert "Please confirm whether" in wp.query.question_text  # original untouched


def test_reviewed_no_issue_without_reason_shows_error_and_does_not_save(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    r = client.post(f"/exceptions/{exception_id}/", data={
        "assigned_to": "", "reviewer_query_text": "", "management_response": "",
        "evidence_description": "", "evidence_reference": "", "reviewer_comments": "",
        "resolution": "", "reviewer_notes": "", "status": "REVIEWED_NO_ISSUE", "status_reason": "",
    })
    assert r.status_code == 200
    page = body(r)
    assert "requires a status_reason" in page
    assert "Saved." not in page

    from app.services import query_service
    wp = query_service.get_working_paper(exception_id)
    assert wp.exception.status == "OPEN"  # unchanged


def test_reviewed_no_issue_with_reason_saves_successfully(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    r = client.post(f"/exceptions/{exception_id}/", data={
        "assigned_to": "", "reviewer_query_text": "", "management_response": "",
        "evidence_description": "", "evidence_reference": "", "reviewer_comments": "",
        "resolution": "", "reviewer_notes": "",
        "status": "REVIEWED_NO_ISSUE", "status_reason": "Vendor confirmed not MSME-registered.",
    })
    page = body(r)
    assert "Saved." in page
    assert "Cleared" in page  # the reviewer-facing conclusion label


def test_working_paper_shows_audit_trail_after_edits(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    client.post(f"/exceptions/{exception_id}/", data={
        "assigned_to": "", "reviewer_query_text": "edited",
        "management_response": "", "evidence_description": "", "evidence_reference": "",
        "reviewer_comments": "", "resolution": "", "reviewer_notes": "",
        "status": "", "status_reason": "",
    })
    r = client.get(f"/exceptions/{exception_id}/")
    page = body(r)
    assert "Audit Trail" in page
    assert "Query Text Edited" in page


# --- integration with Stage 12 Findings Centre ------------------------------

def test_finding_detail_links_to_working_paper(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    r = client.get(f"/review/findings/TAX/{exception_id}")
    assert r.status_code == 200
    assert f"/exceptions/{exception_id}/" in body(r)


def test_working_paper_links_back_to_finding_detail(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    r = client.get(f"/exceptions/{exception_id}/")
    assert f"/review/findings/TAX/{exception_id}" in body(r)


def test_stage12_findings_centre_continues_to_work(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _seed_and_run_tax_msme(client)
    r = client.get("/review/findings")
    assert r.status_code == 200
    assert "TAX-MSME-013" in body(r)


# --- SEBI stays unavailable --------------------------------------------------

def test_sebi_has_no_working_paper_or_query_centre_route(client):
    _create_and_select_engagement(client)
    r = client.get("/exceptions/1/")
    # No SEBI exception can exist (no SEBI rules run), so this 404s on
    # "not found," not on any SEBI-specific handling — confirming there
    # is no SEBI code path here at all.
    assert r.status_code == 404
    r = client.get("/queries/?module=SEBI")
    assert r.status_code == 200
    assert "Queries (0)" in body(r)


# --- nav ----------------------------------------------------------------------

def test_sidebar_offers_query_and_working_papers_link(client):
    r = client.get("/")
    assert 'href="/queries/"' in body(r)


# --- Stage 18: tabular Query & Working Papers redesign -----------------------
#
# The Query Centre table now shows Sr No / Account Name / Date / Amount /
# Observation / Additional Note / Client Remark, with Additional Note
# (QueryResponse.reviewer_comments) and Client Remark
# (QueryResponse.management_response) editable directly in the row, plus
# a one-click Excel download — all approved before implementation.
# Account Name/Date are deliberately blank (see query_service.py's
# export_working_papers_workbook() docstring) — FinSight does not
# persist a per-transaction link back to a finding.

def test_query_centre_table_shows_stage18_columns(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _seed_and_run_tax_msme(client)

    page = body(client.get("/queries/"))
    assert "Sr No" in page
    assert "Account Name" in page
    assert "Observation" in page
    assert "Additional Note" in page
    assert "Client Remark" in page
    assert "Download Excel" in page


def test_inline_remarks_update_saves_additional_note_and_client_remark(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    r = client.post(
        f"/queries/{exception_id}/update-remarks",
        data={"additional_note": "Please recheck Udyam status.", "client_remark": "Confirmed by client CFO."},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/queries/")

    page = body(client.get("/queries/"))
    assert "Please recheck Udyam status." in page
    assert "Confirmed by client CFO." in page

    from app.services import query_service
    wp = query_service.get_working_paper(exception_id)
    assert wp.response.reviewer_comments == "Please recheck Udyam status."
    assert wp.response.management_response == "Confirmed by client CFO."


def test_inline_remarks_update_preserves_active_filters_on_redirect(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    r = client.post(
        f"/queries/{exception_id}/update-remarks",
        data={"additional_note": "Note", "client_remark": "", "module": "TAX"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "module=TAX" in r.headers["Location"]


def test_inline_remarks_update_404s_for_unknown_exception(client):
    _create_and_select_engagement(client)
    r = client.post("/queries/9999/update-remarks", data={"additional_note": "x", "client_remark": "y"})
    assert r.status_code == 404


# --- Stage 20: inline Status editing on the Query Centre table -------------

def test_query_centre_shows_an_inline_status_dropdown_defaulting_to_open(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    page = body(client.get("/queries/"))
    assert 'name="finding_status"' in page
    # OPEN is offered and pre-selected by default, and other transitions
    # (e.g. UNDER_REVIEW/"Further Review Required") are real, selectable options.
    assert 'value="OPEN" selected' in page
    assert 'value="UNDER_REVIEW"' in page
    assert 'value="CLOSED"' in page


def test_inline_status_update_moves_a_finding_off_open(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    r = client.post(
        f"/queries/{exception_id}/update-remarks",
        data={"additional_note": "", "client_remark": "", "finding_status": "UNDER_REVIEW"},
        follow_redirects=False,
    )
    assert r.status_code == 302

    from app.services import query_service
    wp = query_service.get_working_paper(exception_id)
    assert wp.exception.status == "UNDER_REVIEW"

    page = body(client.get("/queries/"))
    assert 'value="UNDER_REVIEW" selected' in page


def test_inline_status_update_to_closed_works(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    client.post(
        f"/queries/{exception_id}/update-remarks",
        data={"additional_note": "", "client_remark": "", "finding_status": "CLOSED"},
        follow_redirects=False,
    )

    from app.services import query_service
    wp = query_service.get_working_paper(exception_id)
    assert wp.exception.status == "CLOSED"


def test_inline_status_update_leaves_status_unchanged_when_field_omitted(client):
    """Saving just the Additional Note/Client Remark (finding_status not
    submitted at all, or submitted blank) must not silently reset status."""
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    from app.services import query_service
    query_service.update_working_paper(exception_id, status="UNDER_REVIEW")

    client.post(
        f"/queries/{exception_id}/update-remarks",
        data={"additional_note": "just a note", "client_remark": ""},
        follow_redirects=False,
    )

    wp = query_service.get_working_paper(exception_id)
    assert wp.exception.status == "UNDER_REVIEW"


def test_inline_status_reason_required_statuses_are_not_offered_inline(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    page = body(client.get("/queries/"))
    # REVIEWED_NO_ISSUE / NOT_APPLICABLE require a status_reason (no
    # textarea in the inline row) — still Full-Working-Paper-only.
    import re
    select_block = re.search(r'name="finding_status".*?</select>', page, re.S).group(0)
    assert 'value="REVIEWED_NO_ISSUE"' not in select_block
    assert 'value="NOT_APPLICABLE"' not in select_block


def test_inline_status_update_rejecting_a_reason_required_status_redirects_with_error(client):
    """Server-side defense: even though the dropdown never offers
    REVIEWED_NO_ISSUE/NOT_APPLICABLE, a direct POST attempting one
    without a status_reason must be rejected, not silently applied."""
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    exception_id = _seed_and_run_tax_msme(client)

    r = client.post(
        f"/queries/{exception_id}/update-remarks",
        data={"additional_note": "", "client_remark": "", "finding_status": "REVIEWED_NO_ISSUE"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "status_error" in r.headers["Location"]

    from app.services import query_service
    wp = query_service.get_working_paper(exception_id)
    assert wp.exception.status == "OPEN"  # unchanged — the rejected status was never applied

    page = body(client.get(r.headers["Location"]))
    assert "reason" in page.lower()


def test_export_xlsx_downloads_a_real_workbook_with_the_stage18_columns(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _seed_and_run_tax_msme(client)

    r = client.get("/queries/export.xlsx")
    assert r.status_code == 200
    assert r.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "attachment" in r.headers.get("Content-Disposition", "")

    import io as _io
    from openpyxl import load_workbook
    wb = load_workbook(_io.BytesIO(r.get_data()))
    sheet = wb["Working Papers"]
    header = [cell.value for cell in sheet[1]]
    assert header == ["Sr No", "Account Name", "Date", "Amount (INR)", "Observation", "Additional Note", "Client Remark"]
    first_data_row = [cell.value for cell in sheet[2]]
    assert first_data_row[0] == 1  # Sr No
    assert first_data_row[1] is None  # Account Name — blank by design
    assert first_data_row[2] is None  # Date — blank by design


def test_export_xlsx_with_no_engagement_404s(client):
    r = client.get("/queries/export.xlsx")
    assert r.status_code == 404
