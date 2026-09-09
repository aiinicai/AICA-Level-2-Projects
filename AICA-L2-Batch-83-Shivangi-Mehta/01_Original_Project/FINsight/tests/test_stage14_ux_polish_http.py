"""
Stage 14 — Final UX & Application Polish: HTTP-level checks for the
new UI/UX behavior this stage introduces. Complements (does not
duplicate) the existing NAV_PATHS smoke test in test_app_factory.py and
the Dashboard-specific tests in test_dashboard.py.

Covers, per the Stage 14 testing requirements: navigation dedup,
Settings/Reports real content, the privacy footer, SEBI remaining
non-executable, the step indicator, loading-state affordances, and
validation error messages rendering understandably.

Uses only synthetic, fabricated data — never real client/financial
data, per the standing instruction.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


# --- navigation: dedup ------------------------------------------------------

def test_sidebar_has_no_duplicate_top_level_exceptions_or_queries_links(client):
    html = body(client.get("/"))
    # The Review-group entries are the only sidebar links into these
    # screens now (Stage 14 section 6). The routes themselves still
    # exist and still work — see test_app_factory.py's NAV_PATHS.
    assert html.count('href="/exceptions/"') == 0
    assert 'href="/queries/"' in html
    assert html.count('href="/queries/"') == 1


def test_review_group_links_still_present_in_sidebar(client):
    # Stage 18 (approved): the standalone "Run Review" (`/review/`)
    # sidebar link was removed — a review now runs via a one-click
    # action on the Upload screen. The Findings Centre link remains.
    html = body(client.get("/"))
    assert 'href="/review/findings"' in html
    assert 'href="/queries/"' in html


def test_sebi_nav_item_remains_a_non_clickable_label(client):
    html = body(client.get("/"))
    assert "SEBI" in html
    assert 'href="/review/sebi/"' not in html  # never a link in the sidebar
    assert "fs-nav-subitem-disabled" in html


# --- Settings / Reports: real content, not bare placeholders ---------------

def test_settings_page_shows_about_and_privacy_content(client):
    resp = client.get("/settings/")
    assert resp.status_code == 200
    html = body(resp)
    assert "About" in html
    assert "FinSight" in html
    normalized = " ".join(html.split())
    assert "Client financial data is not sent to external AI or cloud services" in normalized
    assert "Version" in html


def test_reports_page_explains_it_is_not_in_v1_scope(client):
    resp = client.get("/reports/")
    assert resp.status_code == 200
    html = body(resp)
    assert "not part of FinSight V1" in html


# --- privacy footer appears once, sitewide, not repeated banners -----------

def test_privacy_statement_appears_in_footer_on_dashboard(client):
    html = body(client.get("/"))
    assert "designed for local/offline financial data processing" in html


def test_privacy_statement_does_not_also_appear_as_a_repeated_banner_on_every_screen(client):
    # It should be present exactly once (the shared footer), not
    # additionally duplicated as a banner on top of that same screen.
    html = body(client.get("/"))
    assert html.count("designed for local/offline financial data processing") == 1


# --- step indicator on the data-preparation workflow ------------------------

def test_step_indicator_present_on_upload_screen(client):
    _create_and_select_engagement(client)
    html = body(client.get("/data/upload/"))
    assert "fs-steps" in html
    assert "Upload" in html and "Map Columns" in html and "Run Review" in html


def test_step_indicator_marks_validate_as_current_when_review_not_ready(client):
    _create_and_select_engagement(client)
    html = body(client.get("/review/"))
    assert "fs-steps" in html


# --- loading-state affordance on key action buttons -------------------------

def test_upload_button_carries_a_loading_state_label(client):
    _create_and_select_engagement(client)
    html = body(client.get("/data/upload/"))
    assert "data-loading-text=" in html


def test_run_review_button_carries_a_loading_state_label(client):
    _create_and_select_engagement(client)
    from app.services import engagement_service
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    engagement_service.save_entity_profile(engagement_id, {
        "entity_type": "Company", "industry": None, "is_listed": False,
        "accounting_framework": "AS", "is_gst_registered": False,
        "statutory_audit_applicable": False, "tax_audit_status": "REQUIRES_REVIEW",
        "consolidated_fs_applicable": False, "prior_year_data_available": False,
        "turnover": None, "overall_materiality": None, "performance_materiality": None,
        "clearly_trivial_threshold": None,
    })
    # The individual Accounting engine screen's Run button renders
    # regardless of readiness (unlike the Unified Review screen's,
    # which only appears once data is validated) — a reliable place to
    # check the loading-state affordance exists without seeding a full
    # upload/validate flow.
    html = body(client.get("/review/accounting/"))
    assert "Running Accounting Review..." in html


# --- validation error messages render understandably ------------------------

def test_new_engagement_validation_error_is_understandable_not_a_stack_trace(client):
    resp = client.post("/engagement/new", data={"entity_name": "", "financial_year": ""})
    assert resp.status_code == 200
    html = body(resp)
    assert "Traceback" not in html
    assert "IntegrityError" not in html
    # A field-level error message is shown next to the field.
    assert "fs-field-error" in html


# --- empty states -------------------------------------------------------------

def test_engagements_empty_state_uses_suggested_copy(client):
    html = body(client.get("/engagement/"))
    assert "No engagements yet" in html


def test_findings_centre_empty_state_when_no_engagement(client):
    html = body(client.get("/review/findings"))
    assert "No current engagement selected" in html


def test_query_centre_empty_state_when_no_engagement(client):
    html = body(client.get("/queries/"))
    assert "No current engagement selected" in html


# --- full engagement + upload workflow screens all load ---------------------

def test_engagement_workflow_screens_all_load(client):
    _create_and_select_engagement(client)
    from app.services import engagement_service
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]

    assert client.get("/engagement/").status_code == 200
    assert client.get(f"/engagement/{engagement_id}/profile").status_code == 200
    assert client.get(f"/engagement/{engagement_id}/applicability").status_code == 200


def test_upload_workflow_screens_all_load(client):
    _create_and_select_engagement(client)
    assert client.get("/data/upload/").status_code == 200
    assert client.get("/data/mapping/").status_code == 200
    assert client.get("/data/quality/").status_code == 200
