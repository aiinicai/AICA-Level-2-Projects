"""
Stage 10 — full HTTP round trip through the real Flask app for the Tax
Review screen: catalogue display, no-engagement banner, live preview on
GET, persisting exceptions + linked queries on POST, and the
Act-transition (Decision 1) precondition banner. Mirrors
tests/test_audit_http.py.

Deliberate Stage 10 difference from Audit: an engagement whose
financial year falls under the (unverified) Income-tax Act, 2025 must
show a clear banner and run zero rules, never crash and never silently
produce no findings without explanation
(`test_new_act_engagement_shows_banner_and_runs_no_rules`).

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


def _csv_bytes(rows) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue()


def _upload_and_confirm_ap(client):
    # A payable to "Bright Traders" recorded at the very start of the FY
    # with no further movement — well past TAX-MSME-013's 45-day ageing
    # window as of FY end, and well above its ₹1,000 noise floor.
    r = client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(_csv_bytes([
            {"Party Name": "Bright Traders", "Transaction Date": "01-06-2025", "Credit Amount": "50000", "Debit Amount": ""},
        ])), "ap.csv"), "file_type": "AP"},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302

    from app.services import upload_service
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    file_id = upload_service.list_uploads(engagement_id)[0].file_id

    r = client.post(f"/data/mapping/{file_id}/", data={
        "target_field__0": "party_name",
        "target_field__1": "transaction_date",
        "target_field__2": "credit_amount",
        "target_field__3": "debit_amount",
    }, follow_redirects=False)
    assert r.status_code == 302

    from app.services import mapping_service
    mapping_service.mark_file_status(file_id, "VALIDATED")
    return file_id


def _seed_msme013_rule():
    from app import extensions
    from app.models.rules import TaxRule

    session = extensions.SessionLocal
    session.add(TaxRule(
        rule_id="TAX-MSME-013", topic="MSME Delayed-Payment Review Screen",
        is_active=True, verification_status="VERIFIED",
        legislative_act="IT_ACT_1961", provision_reference="Section 43B(h), Income-tax Act, 1961",
        applicable_from_ay="AY 2026-27",
        logic_summary=(
            "FinSight Analytical Test — a FinSight ageing approximation, not itself prescribed by "
            "Section 43B(h): net payable aged 45+ days since last recorded movement, above a "
            "FinSight noise floor."
        ),
        verified_source="https://www.incometaxindia.gov.in/w/section-43b-42",
        suggested_action="Confirm MSME registration and agreed payment terms before concluding on disallowance.",
    ))
    session.commit()
    return "TAX-MSME-013"


# --- no engagement selected --------------------------------------------------

def test_index_with_no_engagement_shows_banner_and_still_shows_catalogue(client):
    _seed_msme013_rule()
    r = client.get("/review/tax/")
    assert r.status_code == 200
    page = body(r)
    assert "No current engagement selected" in page
    assert "TAX-MSME-013" in page  # catalogue still visible


# --- engagement selected, no seeded rules ------------------------------------

def test_index_with_engagement_but_no_seeded_rules_shows_empty_catalogue(client):
    _create_and_select_engagement(client)
    r = client.get("/review/tax/")
    assert r.status_code == 200
    assert "No tax rules have been seeded yet" in body(r)


# --- Act-transition precondition (Stage 10's defining difference) ----------

def test_new_act_engagement_shows_banner_and_runs_no_rules(client):
    _create_and_select_engagement(client, financial_year="2026-27")
    _seed_msme013_rule()

    r = client.get("/review/tax/")
    assert r.status_code == 200
    page = body(r)
    assert "Income-tax Act, 2025" in page
    assert "TAX-MSME-013" in page  # catalogue still visible even though no review ran

    r = client.post("/review/tax/", follow_redirects=False)
    assert r.status_code == 200
    page = body(r)
    assert "Income-tax Act, 2025" in page
    assert "Review run and saved" not in page


def test_old_act_engagement_runs_without_a_banner(client):
    _create_and_select_engagement(client, financial_year="2025-26")
    _upload_and_confirm_ap(client)
    _seed_msme013_rule()

    r = client.get("/review/tax/")
    assert r.status_code == 200
    page = body(r)
    assert "TAX-MSME-013" in page
    assert "1 finding(s)" in page


# --- full round trip ---------------------------------------------------------

def test_get_shows_live_preview_without_persisting(client):
    _create_and_select_engagement(client)
    _upload_and_confirm_ap(client)
    _seed_msme013_rule()

    r = client.get("/review/tax/")
    assert r.status_code == 200
    page = body(r)
    assert "TAX-MSME-013" in page
    assert "1 finding(s)" in page
    assert "No tax exceptions have been saved for this engagement yet" in page


def test_post_runs_and_persists_exception_visible_on_page(client):
    _create_and_select_engagement(client)
    _upload_and_confirm_ap(client)
    _seed_msme013_rule()

    r = client.post("/review/tax/", follow_redirects=False)
    assert r.status_code == 200
    page = body(r)
    assert "Review run and saved" in page
    assert "1 exception(s) recorded this run" in page
    # The wording layer's non-definitive label, never a confirmed disallowance.
    assert "Potential MSME Payment Review" in page
    assert "MSME Delayed-Payment Review Screen" in page
    assert "Section 43B(h), Income-tax Act, 1961" in page
    assert "Bright Traders" in page

    from app.services import tax_review_service
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    results = tax_review_service.get_last_review_results(engagement_id)
    assert len(results) == 1
    assert results[0].exception.rule_id == "TAX-MSME-013"
    assert results[0].exception.module == "TAX"
    assert results[0].exception.standard_reference == "Section 43B(h), Income-tax Act, 1961"


def test_rerun_via_http_does_not_duplicate(client):
    _create_and_select_engagement(client)
    _upload_and_confirm_ap(client)
    _seed_msme013_rule()

    client.post("/review/tax/", follow_redirects=False)
    client.post("/review/tax/", follow_redirects=False)

    from app.services import tax_review_service
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    assert len(tax_review_service.get_last_review_results(engagement_id)) == 1


def test_persisted_exception_never_states_a_confirmed_disallowance(client):
    # A structural, not merely conventional, check that the page never
    # surfaces language claiming a disallowance/violation is confirmed.
    _create_and_select_engagement(client)
    _upload_and_confirm_ap(client)
    _seed_msme013_rule()

    r = client.post("/review/tax/", follow_redirects=False)
    page = body(r)
    assert "confirmed violation" not in page.lower()
    assert "non-compliant" not in page.lower()
    assert "definitively" not in page.lower()
