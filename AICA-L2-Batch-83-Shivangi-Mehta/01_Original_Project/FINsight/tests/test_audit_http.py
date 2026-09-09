"""
Stage 9 — full HTTP round trip through the real Flask app for the
Audit Review screen: catalogue display, no-engagement banner, live
preview on GET, and persisting exceptions + linked queries on POST,
including the "why flagged" chain (Audit Area / SA reference /
Assertions / Suggested Audit Procedure / Suggested Evidence /
Suggested Query) being visible on the page. Mirrors
tests/test_accounting_http.py.

Deliberate Stage 9 difference: NO Entity Profile / accounting_framework
precondition — a dedicated test below
(`test_review_runs_with_no_entity_profile_saved`) confirms the Audit
Review page works fine with no Entity Profile at all, unlike
Accounting's `AccountingFrameworkNotSetError` banner path.

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
    r = client.post(
        "/engagement/new",
        data={"entity_name": entity_name, "financial_year": "2025-26"},
        follow_redirects=False,
    )
    assert r.status_code == 302


def _csv_bytes(rows) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue()


def _upload_and_confirm_je(client):
    # 2026-03-28 is a Saturday — matches AUD-JE-002's weekend heuristic.
    r = client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(_csv_bytes([
            {"Is Manual Entry": "Yes", "Transaction Date": "2026-03-28", "Description": "Adjustment entry"},
            {"Is Manual Entry": "No", "Transaction Date": "2026-03-30", "Description": "Routine entry"},
        ])), "je.csv"), "file_type": "JE"},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302

    from app.services import upload_service
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    file_id = upload_service.list_uploads(engagement_id)[0].file_id

    r = client.post(f"/data/mapping/{file_id}/", data={
        "target_field__0": "is_manual_entry",
        "target_field__1": "transaction_date",
        "target_field__2": "description",
    }, follow_redirects=False)
    assert r.status_code == 302

    from app.services import mapping_service
    mapping_service.mark_file_status(file_id, "VALIDATED")
    return file_id


def _seed_je002_rule():
    from app import extensions
    from app.models.rules import AuditAssertion, AuditRule, AuditRuleAssertion, Standard

    session = extensions.SessionLocal
    standard = Standard(framework="SA", code="SA 240", title="The Auditor's Responsibilities Relating to Fraud")
    session.add(standard)
    session.commit()
    session.add(AuditRule(
        rule_id="AUD-JE-002", standard_id=standard.standard_id, topic="Manual Journal Entry Posted on a Non-Business Day",
        is_active=True, verification_status="VERIFIED", related_sa="SA 240", audit_area="Journal Entry Testing",
        suggested_audit_procedure="Consider whether a brief inquiry is warranted.",
        suggested_evidence="Journal voucher, explanation for the posting date.",
        logic_summary=(
            "FinSight Analytical Test — not prescribed by the cited SA: manual entries "
            "(is_manual_entry truthy) whose transaction_date falls on a Saturday or Sunday "
            "are flagged as a low-risk/advisory review item. No posting-timestamp field "
            "exists in the schema, so off-hours weekday posting is out of scope, not inferred."
        ),
    ))
    occurrence = AuditAssertion(code="OCCURRENCE", label="Occurrence")
    session.add(occurrence)
    session.commit()
    session.add(AuditRuleAssertion(rule_id="AUD-JE-002", assertion_id=occurrence.assertion_id))
    session.commit()
    return "AUD-JE-002"


# --- no engagement selected --------------------------------------------------

def test_index_with_no_engagement_shows_banner_and_still_shows_catalogue(client):
    _seed_je002_rule()
    r = client.get("/review/audit/")
    assert r.status_code == 200
    page = body(r)
    assert "No current engagement selected" in page
    assert "AUD-JE-002" in page  # catalogue still visible


# --- engagement selected, no seeded rules ------------------------------------

def test_index_with_engagement_but_no_seeded_rules_shows_empty_catalogue(client):
    _create_and_select_engagement(client)
    r = client.get("/review/audit/")
    assert r.status_code == 200
    assert "No audit rules have been seeded yet" in body(r)


# --- no Entity Profile precondition (Stage 9's defining difference) --------

def test_review_runs_with_no_entity_profile_saved(client):
    # Deliberately never saves an Entity Profile — Audit has no framework
    # precondition and must still run cleanly (unlike Accounting's
    # AccountingFrameworkNotSetError banner).
    _create_and_select_engagement(client)
    _upload_and_confirm_je(client)
    _seed_je002_rule()

    r = client.get("/review/audit/")
    assert r.status_code == 200
    page = body(r)
    assert "Entity Profile" not in page
    assert "AUD-JE-002" in page
    assert "1 finding(s)" in page


# --- full round trip ---------------------------------------------------------

def test_get_shows_live_preview_without_persisting(client):
    _create_and_select_engagement(client)
    _upload_and_confirm_je(client)
    _seed_je002_rule()

    r = client.get("/review/audit/")
    assert r.status_code == 200
    page = body(r)
    assert "AUD-JE-002" in page
    assert "1 finding(s)" in page
    assert "No audit exceptions have been saved for this engagement yet" in page


def test_post_runs_and_persists_exception_visible_on_page(client):
    _create_and_select_engagement(client)
    _upload_and_confirm_je(client)
    _seed_je002_rule()

    r = client.post("/review/audit/", follow_redirects=False)
    assert r.status_code == 200
    page = body(r)
    assert "Review run and saved" in page
    assert "1 exception(s) recorded this run" in page
    # The full why-flagged chain should be visible somewhere on the page:
    # label, audit area, SA reference, assertion, suggested procedure/evidence/query.
    assert "Review Required" in page
    assert "Journal Entry Testing" in page
    assert "SA 240" in page
    assert "OCCURRENCE" in page
    assert "Consider whether a brief inquiry is warranted." in page
    assert "Journal voucher, explanation for the posting date." in page
    assert "Please confirm the business reason" in page
    # Stage 9 closure metadata refinement: SA Reference vs FinSight Analytical
    # Test must be visibly distinguished on the page, not just in code/seed data.
    assert "SA Reference (authoritative)" in page
    assert "FinSight Analytical Test" in page
    assert "Saturday or Sunday" in page

    from app.services import audit_review_service
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    results = audit_review_service.get_last_review_results(engagement_id)
    assert len(results) == 1
    assert results[0].exception.rule_id == "AUD-JE-002"
    assert results[0].exception.module == "AUDIT"
    assert results[0].exception.standard_reference == "SA 240"
    assert results[0].assertions == ["OCCURRENCE"]


def test_rerun_via_http_does_not_duplicate(client):
    _create_and_select_engagement(client)
    _upload_and_confirm_je(client)
    _seed_je002_rule()

    client.post("/review/audit/", follow_redirects=False)
    client.post("/review/audit/", follow_redirects=False)

    from app.services import audit_review_service
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    assert len(audit_review_service.get_last_review_results(engagement_id)) == 1


def test_persisted_exception_never_uses_an_accounting_only_label(client):
    # A structural, not merely conventional, check that the page never
    # surfaces an Accounting-only label for an Audit finding.
    _create_and_select_engagement(client)
    _upload_and_confirm_je(client)
    _seed_je002_rule()

    r = client.post("/review/audit/", follow_redirects=False)
    page = body(r)
    assert "Potential Accounting Exception" not in page
    assert "Potential Inconsistency" not in page
