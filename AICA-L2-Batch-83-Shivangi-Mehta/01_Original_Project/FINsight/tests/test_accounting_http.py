"""
Stage 8 — full HTTP round trip through the real Flask app for the
Accounting Review screen: catalogue display, no-engagement banner,
live preview on GET, and persisting exceptions + linked queries on
POST, including the "why flagged" chain being visible on the page.

Stage 8 Round 2 (correction #1): the review is framework-aware, so
every full-round-trip test now also saves an Entity Profile with
`accounting_framework` set before expecting a live review — otherwise
`AccountingFrameworkNotSetError` is raised and the page shows a banner
instead. A dedicated test below (`test_no_entity_profile_shows_error_banner`)
covers that banner path directly. The seeded rule uses the framework-
specific rule_id (AS5-PPI-012 for AS, INDAS8-PPE-012 for Ind AS) rather
than the old framework-agnostic GEN-PPI-012, and a new test asserts an
AS-framework engagement's page never shows Ind AS 8/"prior period error"
text and vice versa.

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


def _save_entity_profile(client, accounting_framework="AS"):
    from app.services import engagement_service

    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    engagement_service.save_entity_profile(engagement_id, {
        "entity_type": "Company",
        "industry": None,
        "is_listed": False,
        "accounting_framework": accounting_framework,
        "is_gst_registered": False,
        "statutory_audit_applicable": False,
        "tax_audit_status": "REQUIRES_REVIEW",
        "consolidated_fs_applicable": False,
        "prior_year_data_available": False,
        "turnover": None,
        "overall_materiality": None,
        "performance_materiality": None,
        "clearly_trivial_threshold": None,
    })


def _csv_bytes(rows) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue()


def _upload_and_confirm_je(client):
    r = client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(_csv_bytes([
            {"Description": "Prior period adjustment for FY24-25 expense", "Debit": 30000, "Credit": 0},
            {"Description": "Routine sale of goods", "Debit": 0, "Credit": 50000},
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
        "target_field__0": "description",
        "target_field__1": "debit_amount",
        "target_field__2": "credit_amount",
    }, follow_redirects=False)
    assert r.status_code == 302

    from app.services import mapping_service
    mapping_service.mark_file_status(file_id, "VALIDATED")
    return file_id


def _seed_ppi_rule(framework="AS"):
    from app import extensions
    from app.models.rules import AccountingRule, Standard

    session = extensions.SessionLocal
    if framework == "AS":
        standard = Standard(framework="AS", code="AS 5", title="Net Profit or Loss for the Period, Prior Period Items and Changes in Accounting Policies")
        rule_id = "AS5-PPI-012"
    else:
        standard = Standard(framework="IND_AS", code="Ind AS 8", title="Accounting Policies, Changes in Accounting Estimates and Errors")
        rule_id = "INDAS8-PPE-012"
    session.add(standard)
    session.commit()
    session.add(AccountingRule(
        rule_id=rule_id, standard_id=standard.standard_id, framework=framework,
        topic="Prior Period Items / Errors — Narration Keyword Check", is_active=True, verification_status="VERIFIED",
    ))
    session.commit()
    return rule_id


# --- no engagement selected --------------------------------------------------

def test_index_with_no_engagement_shows_banner_and_still_shows_catalogue(client):
    _seed_ppi_rule("AS")
    r = client.get("/review/accounting/")
    assert r.status_code == 200
    page = body(r)
    assert "No current engagement selected" in page
    assert "AS5-PPI-012" in page  # catalogue still visible


# --- engagement selected, no seeded rules OR no entity profile --------------

def test_index_with_engagement_but_no_seeded_rules_shows_empty_catalogue(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    r = client.get("/review/accounting/")
    assert r.status_code == 200
    assert "No accounting rules have been seeded yet" in body(r)


def test_no_entity_profile_shows_error_banner(client):
    _create_and_select_engagement(client)
    _seed_ppi_rule("AS")
    # Deliberately no _save_entity_profile() call — no framework known yet.
    r = client.get("/review/accounting/")
    assert r.status_code == 200
    page = body(r)
    assert "Entity Profile" in page
    assert "accounting framework" in page.lower()


# --- full round trip, AS framework -------------------------------------------

def test_get_shows_live_preview_without_persisting(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _upload_and_confirm_je(client)
    _seed_ppi_rule("AS")

    r = client.get("/review/accounting/")
    assert r.status_code == 200
    page = body(r)
    assert "AS5-PPI-012" in page
    assert "1 finding(s)" in page
    assert "No accounting exceptions have been saved for this engagement yet" in page


def test_post_runs_and_persists_exception_visible_on_page(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _upload_and_confirm_je(client)
    _seed_ppi_rule("AS")

    r = client.post("/review/accounting/", follow_redirects=False)
    assert r.status_code == 200
    page = body(r)
    assert "Review run and saved" in page
    assert "1 exception(s) recorded this run" in page
    # The full why-flagged chain should be visible somewhere on the page.
    assert "Potential Inconsistency" in page
    assert "prior period" in page.lower()
    assert "Please confirm whether this entry represents a prior period item" in page
    assert "AS 5" in page

    from app.services import accounting_review_service
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    results = accounting_review_service.get_last_review_results(engagement_id)
    assert len(results) == 1
    assert results[0].exception.rule_id == "AS5-PPI-012"


def test_rerun_via_http_does_not_duplicate(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _upload_and_confirm_je(client)
    _seed_ppi_rule("AS")

    client.post("/review/accounting/", follow_redirects=False)
    client.post("/review/accounting/", follow_redirects=False)

    from app.services import accounting_review_service
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    assert len(accounting_review_service.get_last_review_results(engagement_id)) == 1


# --- framework gating end-to-end (correction #1) -----------------------------

def test_as_engagement_never_shows_ind_as_reference(client):
    # Both frameworks' rules are seeded/coded and BOTH appear in the read-
    # only Rule Catalogue (which lists every rule regardless of framework —
    # that's a catalogue display concern, not an execution one). What must
    # never happen is an Ind AS reference appearing in this AS-framework
    # engagement's actual RESULTS — checked against the persisted records,
    # not fragile whole-page text matching against the catalogue.
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _upload_and_confirm_je(client)
    _seed_ppi_rule("AS")
    _seed_ppi_rule("IND_AS")

    r = client.post("/review/accounting/", follow_redirects=False)
    assert r.status_code == 200
    page = body(r)
    assert "AS 5" in page

    from app.services import accounting_review_service
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    results = accounting_review_service.get_last_review_results(engagement_id)
    assert len(results) == 1
    assert results[0].exception.rule_id == "AS5-PPI-012"
    assert "Ind AS" not in (results[0].exception.standard_reference or "")
    assert "prior period error" not in results[0].exception.description.lower()

    review = accounting_review_service.preview_accounting_review(engagement_id)
    assert review.framework == "AS"
    assert list(review.rule_outcomes.keys()) == ["AS5-PPI-012"]
    assert "INDAS8-PPE-012" not in review.rule_outcomes


def test_ind_as_engagement_never_shows_as_reference(client):
    _create_and_select_engagement(client, entity_name="Beta Industries Ltd")
    _save_entity_profile(client, "IND_AS")
    _upload_and_confirm_je(client)
    _seed_ppi_rule("AS")
    _seed_ppi_rule("IND_AS")

    r = client.post("/review/accounting/", follow_redirects=False)
    assert r.status_code == 200
    page = body(r)
    assert "Ind AS 8" in page

    from app.services import accounting_review_service
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    results = accounting_review_service.get_last_review_results(engagement_id)
    assert len(results) == 1
    assert results[0].exception.rule_id == "INDAS8-PPE-012"
    # The AS framework's own defined term must not leak into an Ind AS finding.
    assert "prior period item" not in results[0].exception.description.lower()

    review = accounting_review_service.preview_accounting_review(engagement_id)
    assert review.framework == "IND_AS"
    assert list(review.rule_outcomes.keys()) == ["INDAS8-PPE-012"]
    assert "AS5-PPI-012" not in review.rule_outcomes
