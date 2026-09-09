"""
Dashboard screen tests.

Originally a Stage 4 ("Basic UI") test verifying a genuine hard-coded
zero-state payload — the only honest thing to show at the time, since
no rule/exception/query module existed yet.

Stage 14 (Final UX & Application Polish) rewired the Dashboard to real
Stage 12/13 data per the explicit instruction "Use actual application
data. Do NOT hard-code counts. If there is no engagement yet, show a
professional empty state rather than zeros everywhere" — this
deliberately, explicitly supersedes the old always-zero payload shape,
so the assertions below are rewritten to match the new, real behavior
rather than the old fixed one. The empty-state case (no engagement) is
still covered — it's now a real "no engagement" screen rather than a
fake numeric zero state.

Chart *rendering* itself (charts.js/dashboard.js) is JavaScript and out
of pytest's reach.
"""
import io
import re
import sys
import json
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


def _dashboard_payload(html: str) -> dict | None:
    match = re.search(
        r'<script type="application/json" id="fs-dashboard-data">(.*?)</script>',
        html,
        re.S,
    )
    return json.loads(match.group(1)) if match else None


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
    return engagement_id


# --- no engagement: real empty state, not a fake zero payload --------------

def test_dashboard_with_no_engagement_shows_professional_empty_state(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "No engagements yet" in html
    # No fabricated data payload is rendered at all when there is nothing
    # real to show — this is the "professional empty state rather than
    # zeros everywhere" the Stage 14 spec asked for.
    assert _dashboard_payload(html) is None


def test_dashboard_route_renders_real_screen_not_placeholder(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "This section is part of the approved Stage 1 architecture" not in html
    assert "FinSight" in html


def test_dashboard_loads_chart_component_scripts(client):
    html = client.get("/").get_data(as_text=True)
    assert "js/charts.js" in html
    assert "js/dashboard.js" in html
    assert client.get("/static/js/charts.js").status_code == 200
    assert client.get("/static/js/dashboard.js").status_code == 200


# --- with an engagement, before any review: real (not fake) zeros ----------

def test_dashboard_with_engagement_but_no_review_shows_genuine_zeros(client):
    _create_and_select_engagement(client)
    html = client.get("/").get_data(as_text=True)
    data = _dashboard_payload(html)
    assert data is not None
    assert data["engagement"]["entity_name"] == "Acme Manufacturing Ltd"
    assert data["review_summary"]["total_findings"] == 0
    assert all(row["value"] == 0 for row in data["exceptions_by_module"])
    assert data["open_queries"] == 0
    assert data["resolved_queries"] == 0
    # readiness is real (no uploads yet), not fabricated as "ready"
    assert data["readiness"]["ready"] is False


def test_dashboard_module_set_is_always_accounting_audit_tax(client):
    """FinSight V1 scope: SEBI is deferred, never a dashboard module."""
    _create_and_select_engagement(client)
    data = _dashboard_payload(client.get("/").get_data(as_text=True))
    labels = {row["label"] for row in data["exceptions_by_module"]}
    assert labels == {"Accounting", "Audit", "Tax"}
    assert "SEBI" not in labels


# --- with a real review run: genuinely non-zero, no hard-coding ------------

def test_dashboard_reflects_real_findings_after_a_review_run(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _seed_and_run_tax_msme(client)

    data = _dashboard_payload(client.get("/").get_data(as_text=True))
    assert data["review_summary"]["total_findings"] == 1
    tax_row = next(r for r in data["exceptions_by_module"] if r["label"] == "Tax")
    assert tax_row["value"] == 1
    assert data["readiness"]["ready"] is True


def test_dashboard_reflects_real_query_status_after_a_review_run(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _seed_and_run_tax_msme(client)

    data = _dashboard_payload(client.get("/").get_data(as_text=True))
    assert data["query_summary"]["total"] == 1
    assert data["open_queries"] == 1  # freshly-raised query, nothing resolved yet
    assert data["resolved_queries"] == 0


def test_dashboard_high_level_stat_cards_use_real_numbers(client):
    _create_and_select_engagement(client)
    _save_entity_profile(client, "AS")
    _seed_and_run_tax_msme(client)

    html = client.get("/").get_data(as_text=True)
    # The stat-card labels are still on screen and the underlying JSON
    # payload backs them with real, non-fabricated numbers (checked
    # above) — this just confirms the labels made it into the rendered
    # HTML with the new layout.
    assert "Total Findings" in html
    assert "Open Queries" in html
    assert "Resolved Queries" in html


# --- no numeric risk score is fabricated -------------------------------------

def test_dashboard_does_not_render_a_fabricated_risk_score_gauge(client):
    """No weighted risk-scoring algorithm exists anywhere in FinSight
    (see app/api/dashboard_bp.py's module docstring) — a gauge that can
    only ever read 0 would itself be exactly the kind of hard-coded
    figure Stage 14 prohibits, so it was removed rather than faked."""
    _create_and_select_engagement(client)
    html = client.get("/").get_data(as_text=True)
    assert "fs-chart-gauge" not in html
    assert "Overall Risk Score" not in html
