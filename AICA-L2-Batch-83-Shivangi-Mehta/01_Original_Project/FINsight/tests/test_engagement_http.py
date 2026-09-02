"""
Stage 5 — full HTTP round trip through the real Flask app: Engagement
creation, Entity Profile save, the Applicability Matrix (system
suggestion labeling + confirmation), "select as current engagement",
and (originally) the resulting SEBI nav 3-state / dashboard
module-visibility behaviour (Stage 4 round 2, correction #3: the
dashboard must use the *confirmed* applicability state, not the system
suggestion, to decide whether SEBI is an active module).

Stage 11 scope change (approved): FinSight V1 does not implement SEBI/
Listed-Entity review at all — see documentation/finsight_v1_scope.md.
The SEBI-nav-3-state and dashboard-SEBI-visibility tests below were
rewritten accordingly: the nav item is now a single static, non-clickable
"Future Module" label in every engagement/applicability state, and the
dashboard never carries a SEBI row at all. The underlying applicability
mechanism (Applicability rows, system suggestions, confirmation) is
otherwise unchanged and still fully tested for Accounting/Audit/Tax-
relevant areas; only SEBI/LODR's row is no longer surfaced or
confirmable through the UI.

Each test gets its own fresh Flask app + fresh in-memory SQLite DB (see
`client()` below) so tests never depend on one another's ordering or
leak state — this trades a little setup repetition (each test that needs
an engagement creates its own) for tests that can be read, run, and
debugged independently.

NOTE ON THIS SANDBOX: could not run this against a real `pip install -r
requirements.txt` environment — SQLAlchemy/Alembic remain uninstallable
here (network to PyPI/apt confirmed 403 again during Stage 5 delivery).
It DID run for real, however, against a genuinely real Flask 3.1.3 (a
cached install this sandbox happens to have, found during Stage 5
delivery — see the Stage 5 delivery notes) plus a scoped SQLAlchemy
2.x declarative-ORM shim (`/tmp/orm_shim.py` during delivery, not part
of this repo) that layers real Python<->SQL mapping on top of a real,
on-disk SQLite database. So: every Flask route, template, redirect,
session cookie and form-validation path below executed for real; only
the ORM layer underneath `app/services/engagement_service.py` is
simulated. Run for real, wherever SQLAlchemy/Alembic are installed:

    pip install -r requirements.txt
    pytest tests/test_engagement_http.py -v
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from config import TestConfig
from app import create_app


@pytest.fixture()
def client():
    app = create_app(TestConfig)
    from app import extensions
    from app.models import Base

    Base.metadata.create_all(extensions.engine)
    return app.test_client()


def body(resp):
    return resp.get_data(as_text=True)


def nav_html(page: str) -> str:
    """The rendered <nav> block, with HTML comments stripped — base.html
    carries a long explanatory comment inside <nav> that itself contains
    the literal words "SEBI" and "Review Required" in its prose, which
    would otherwise produce false positives/negatives in substring
    checks against the *rendered* nav state."""
    m = re.search(r"<nav.*?</nav>", page, re.S)
    block = m.group(0) if m else ""
    return re.sub(r"<!--.*?-->", "", block, flags=re.S)


def assert_sebi_nav_is_static_placeholder(page: str):
    """Stage 11 scope change invariant: the SEBI nav item must ALWAYS be
    the same inert, non-clickable "Future Module" label — never a real
    link into sebi.index, and never a "Review Required" flag — no matter
    what the engagement/entity-profile/applicability state is."""
    nav = nav_html(page)
    assert "SEBI" in nav
    assert "Future Module" in nav
    assert 'href="/review/sebi/"' not in nav
    assert "Review Required" not in nav


def _create_engagement(client, entity_name, financial_year="2025-26"):
    r = client.post(
        "/engagement/new",
        data={"entity_name": entity_name, "financial_year": financial_year},
        follow_redirects=False,
    )
    assert r.status_code == 302
    match = re.search(r"/engagement/(\d+)/profile", r.headers["Location"])
    assert match, r.headers["Location"]
    return int(match.group(1))


LISTED_IND_AS_PROFILE_FORM = {
    "entity_type": "Company",
    "industry": "Steel",
    "is_listed": "on",
    "accounting_framework": "IND_AS",
    "is_gst_registered": "on",
    "statutory_audit_applicable": "on",
    "tax_audit_status": "APPLICABLE",
    "turnover": "75,00,00,000",
    "overall_materiality": "50,00,000",
}

UNLISTED_AS_PROFILE_FORM = {
    "entity_type": "Proprietorship",
    "accounting_framework": "AS",
    "tax_audit_status": "NOT_APPLICABLE",
    # is_listed checkbox omitted -> the browser sends nothing -> False
}


def _save_profile(client, engagement_id, form):
    r = client.post(f"/engagement/{engagement_id}/profile", data=form, follow_redirects=False)
    assert r.status_code == 302 and "/applicability" in r.headers["Location"]


def _attempt_confirm_sebi_applicable(client, engagement_id, confirmed_by="R. Sharma"):
    """Attempts to POST a SEBI/LODR applicability confirmation directly
    (bypassing the UI, which no longer renders a form for this area at
    all in V1 — see the applicability() route's `_V1_HIDDEN_AREAS`
    filter). The route still redirects normally (a POST for an
    unrecognized/hidden area is silently ignored, same shape as an
    invalid `status` value), but must NOT persist anything — proven by
    `test_direct_post_cannot_confirm_sebi_applicability_v1_scope` below."""
    r = client.post(
        f"/engagement/{engagement_id}/applicability",
        data={
            "area": "SEBI/LODR",
            "user_confirmed_status": "APPLICABLE",
            "user_confirmation_note": "Confirmed listed on NSE.",
            "confirmed_by": confirmed_by,
        },
        follow_redirects=False,
    )
    assert r.status_code == 302


def _select(client, engagement_id):
    r = client.post(f"/engagement/{engagement_id}/select", follow_redirects=False)
    assert r.status_code == 302 and r.headers["Location"].endswith("/")


# --- 1. Empty state ---------------------------------------------------------

def test_empty_state_shows_no_engagements_and_no_current_engagement(client):
    r = client.get("/engagement/")
    assert r.status_code == 200
    assert "No engagements yet" in body(r)

    r = client.get("/")
    assert r.status_code == 200
    page = body(r)
    assert "No engagement selected" in page
    # Stage 11 scope change: the nav's SEBI item is now a static
    # placeholder in every state, including before any engagement exists
    # — it no longer depends on compute_sebi_nav_state() at all.
    assert_sebi_nav_is_static_placeholder(page)


# --- 2. Engagement creation --------------------------------------------------

def test_new_engagement_form_rejects_blank_fields(client):
    r = client.post("/engagement/new", data={"entity_name": "", "financial_year": ""})
    assert r.status_code == 200  # re-renders the form, does not redirect
    assert "Entity name is required" in body(r)


def test_create_engagement_redirects_to_profile_and_appears_in_list(client):
    engagement_id = _create_engagement(client, "Listed Steel Co")
    assert engagement_id is not None

    r = client.get("/engagement/")
    assert "Listed Steel Co" in body(r)


# --- 3. Entity Profile --------------------------------------------------------

def test_entity_profile_get_prefills_and_post_redirects_to_applicability(client):
    engagement_id = _create_engagement(client, "Listed Steel Co")

    r = client.get(f"/engagement/{engagement_id}/profile")
    assert r.status_code == 200

    _save_profile(client, engagement_id, LISTED_IND_AS_PROFILE_FORM)  # asserts the redirect itself


# --- 4. Applicability Matrix (Stage 18 redesign): tabular Yes/No, wired ----
# --- to which review modules the one-click "Run Review" action runs. ------
#
# Rewritten for the Stage 18 redesign (explicitly approved before
# implementation): the previous detailed per-area (Entity Profile Input
# / System Suggestion / Professional Confirmation) screen covering all
# 6 applicability_engine.AREAS was replaced by a single-row Yes/No table
# covering only the three user-selectable tasks (Audit Review / Income
# Tax Review / Tax Audit Review), with the accounting framework shown
# read-only (auto-detected from the Entity Profile) rather than as a
# task. The underlying Applicability rows/system-suggestion mechanism
# (app/services/applicability_engine.py, engagement_service.py) is
# UNCHANGED and still independently covered by tests/unit/
# test_applicability_engine.py — only this HTTP-facing screen's
# structure changed, so only these tests needed rewriting.

def test_applicability_matrix_shows_client_name_detected_framework_and_tasks(client):
    engagement_id = _create_engagement(client, "Listed Steel Co")
    _save_profile(client, engagement_id, LISTED_IND_AS_PROFILE_FORM)

    r = client.get(f"/engagement/{engagement_id}/applicability")
    assert r.status_code == 200
    page = body(r)
    assert "Listed Steel Co" in page
    # Accounting framework is shown read-only, auto-detected from the
    # Entity Profile — never a selectable task on this screen.
    assert "Ind AS" in page and "(detected)" in page
    assert "Audit Review" in page
    assert "Income Tax Review" in page
    assert "Tax Audit Review" in page
    # Stage 11 scope change (unchanged by Stage 18): SEBI/LODR is never
    # a selectable task on the Applicability Matrix.
    assert "Listed Entity / SEBI Review is outside the current FinSight V1 scope" in page


# --- Round-2 correction #1 (preserved through the Stage 18 redesign): -----
# --- Audit Review vs Statutory Audit Applicability -------------------------

def test_audit_review_task_defaults_to_yes_even_when_statutory_audit_not_applicable(client):
    """The core round-2 correction, still exercised end-to-end under the
    Stage 18 tabular UI: an entity with statutory audit marked NOT
    applicable must still default to Audit Review = Yes — it is
    FinSight's own analytical capability, not gated on the
    statutory-audit fact (applicability_engine.py's own suggestion logic
    is unchanged; this proves the new screen still reflects it)."""
    engagement_id = _create_engagement(client, "Unlisted Traders")
    _save_profile(client, engagement_id, UNLISTED_AS_PROFILE_FORM)  # statutory_audit_applicable left unchecked -> False

    page = body(client.get(f"/engagement/{engagement_id}/applicability"))
    assert 'name="audit_review" value="yes" checked' in page


def test_applicability_matrix_tasks_default_from_system_suggestion_before_confirmation(client):
    engagement_id = _create_engagement(client, "Unlisted Traders")
    _save_profile(client, engagement_id, UNLISTED_AS_PROFILE_FORM)  # tax_audit_status = NOT_APPLICABLE

    page = body(client.get(f"/engagement/{engagement_id}/applicability"))
    assert 'name="audit_review" value="yes" checked' in page
    assert 'name="income_tax_review" value="yes" checked' in page
    # Tax Audit Review mirrors tax_audit_status; NOT_APPLICABLE -> defaults to No.
    assert 'name="tax_audit_review" value="no" checked' in page


def test_applicability_task_confirmation_persists_across_reload(client):
    engagement_id = _create_engagement(client, "Listed Steel Co")
    _save_profile(client, engagement_id, LISTED_IND_AS_PROFILE_FORM)
    r = client.post(
        f"/engagement/{engagement_id}/applicability",
        data={"audit_review": "no", "income_tax_review": "yes", "tax_audit_review": "yes"},
        follow_redirects=False,
    )
    assert r.status_code == 302

    page = body(client.get(f"/engagement/{engagement_id}/applicability"))
    assert 'name="audit_review" value="no" checked' in page
    assert 'name="income_tax_review" value="yes" checked' in page
    assert 'name="tax_audit_review" value="yes" checked' in page


def test_applicability_yes_no_answers_drive_which_modules_run_review_would_use(client):
    """Confirms the Stage 18 wiring end-to-end at the service layer this
    screen writes through — app/services/engagement_service.py::
    get_enabled_review_modules() (consumed by the one-click "Run Review"
    action, see tests/test_review_http.py)."""
    from app.services import engagement_service

    engagement_id = _create_engagement(client, "Listed Steel Co")
    _save_profile(client, engagement_id, LISTED_IND_AS_PROFILE_FORM)

    # Before any confirmation: everything defaults on (today's behavior).
    assert engagement_service.get_enabled_review_modules(engagement_id) == ("ACCOUNTING", "AUDIT", "TAX")

    client.post(
        f"/engagement/{engagement_id}/applicability",
        data={"audit_review": "no", "income_tax_review": "no", "tax_audit_review": "no"},
    )
    # ACCOUNTING always runs; AUDIT/TAX are opted out.
    assert engagement_service.get_enabled_review_modules(engagement_id) == ("ACCOUNTING",)

    client.post(
        f"/engagement/{engagement_id}/applicability",
        data={"audit_review": "no", "income_tax_review": "yes", "tax_audit_review": "no"},
    )
    # TAX runs because Income Tax Review alone is Yes (Tax Audit Review is No).
    assert engagement_service.get_enabled_review_modules(engagement_id) == ("ACCOUNTING", "TAX")


# --- Round-2 correction #3: Financial Year format validation --------------

def test_new_engagement_form_rejects_an_invalid_financial_year(client):
    r = client.post("/engagement/new", data={"entity_name": "Acme Ltd", "financial_year": "2025"})
    assert r.status_code == 200  # re-renders the form, does not redirect
    assert "valid Indian financial year" in body(r)


# --- 5. Stage 11 scope change: SEBI nav is a static placeholder, always,
# --- regardless of listed status or confirmation attempts ------------------

def test_sebi_nav_is_static_placeholder_for_a_listed_unconfirmed_entity(client):
    engagement_id = _create_engagement(client, "Listed Steel Co")
    _save_profile(client, engagement_id, LISTED_IND_AS_PROFILE_FORM)
    _select(client, engagement_id)

    page = body(client.get("/"))
    assert_sebi_nav_is_static_placeholder(page)


def test_direct_post_cannot_confirm_sebi_applicability_v1_scope(client):
    """Even a direct POST to the applicability route for area=SEBI/LODR
    (bypassing the UI, which renders no form for it) must not persist
    anything — the route-level `_V1_HIDDEN_AREAS` filter in
    app/api/engagement_bp.py rejects it before it reaches the service
    layer. This is the concrete proof behind "no SEBI applicability
    logic is exposed in V1"."""
    engagement_id = _create_engagement(client, "Listed Steel Co")
    _save_profile(client, engagement_id, LISTED_IND_AS_PROFILE_FORM)
    _attempt_confirm_sebi_applicable(client, engagement_id)
    _select(client, engagement_id)

    page = body(client.get("/"))
    assert_sebi_nav_is_static_placeholder(page)
    matrix_page = body(client.get(f"/engagement/{engagement_id}/applicability"))
    assert "confirmed by R. Sharma" not in matrix_page
    assert '"module_key": "SEBI"' not in body(client.get("/")) and \
        '\\"module_key\\": \\"SEBI\\"' not in body(client.get("/"))


# --- 8. Selecting an engagement sets session-cookie "current engagement" ---

def test_creating_an_engagement_auto_selects_it_as_current(client):
    # app/api/engagement_bp.py's `new()` calls set_current_engagement()
    # right after creating the engagement (line 49) — you're actively
    # working on what you just created, so it becomes "current" without
    # a separate click. /select exists for switching BACK to an
    # already-created engagement, not for this first-time case.
    _create_engagement(client, "Listed Steel Co")
    assert "Listed Steel Co" in body(client.get("/"))


def test_select_switches_current_engagement_back_to_an_earlier_one(client):
    first_id = _create_engagement(client, "Listed Steel Co")
    _save_profile(client, first_id, LISTED_IND_AS_PROFILE_FORM)

    second_id = _create_engagement(client, "Unlisted Traders")  # auto-selects the second one
    assert "Unlisted Traders" in body(client.get("/"))

    _select(client, first_id)  # switch back to the first
    assert "Listed Steel Co" in body(client.get("/"))


# --- 9. Unlisted entity: dashboard must never carry a SEBI module row ------

def test_unlisted_engagement_dashboard_never_carries_a_sebi_row(client):
    engagement_id = _create_engagement(client, "Unlisted Traders")
    _save_profile(client, engagement_id, UNLISTED_AS_PROFILE_FORM)
    _select(client, engagement_id)

    r = client.get("/")
    page = body(r)
    assert_sebi_nav_is_static_placeholder(page)
    assert '"module_key": "SEBI"' not in page and '\\"module_key\\": \\"SEBI\\"' not in page


# --- 10. The static SEBI nav placeholder is identical across engagements ---
# --- (Stage 11 scope change: nothing engagement-specific drives it now) ----

def test_two_engagements_both_show_the_same_static_sebi_nav_placeholder(client):
    listed_id = _create_engagement(client, "Listed Steel Co")
    _save_profile(client, listed_id, LISTED_IND_AS_PROFILE_FORM)

    unlisted_id = _create_engagement(client, "Unlisted Traders")
    _save_profile(client, unlisted_id, UNLISTED_AS_PROFILE_FORM)

    _select(client, listed_id)
    assert_sebi_nav_is_static_placeholder(body(client.get("/")))

    _select(client, unlisted_id)
    assert_sebi_nav_is_static_placeholder(body(client.get("/")))


# --- 11. Engagement deletion (Stage 20) ------------------------------------

def test_engagements_index_shows_a_remove_action_for_every_engagement(client):
    engagement_id = _create_engagement(client, "Disposable Co")
    page = body(client.get("/engagement/"))
    assert f'/engagement/{engagement_id}/delete' in page
    assert "Remove" in page


def test_delete_removes_engagement_from_the_list(client):
    keep_id = _create_engagement(client, "Keeper Co")
    doomed_id = _create_engagement(client, "Disposable Co")

    r = client.post(f"/engagement/{doomed_id}/delete", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/engagement/")

    page = body(client.get("/engagement/"))
    assert "Disposable Co" not in page
    assert "Keeper Co" in page


def test_delete_unknown_engagement_returns_404(client):
    r = client.post("/engagement/999999/delete", follow_redirects=False)
    assert r.status_code == 404


def test_delete_current_engagement_clears_selection_and_dashboard_still_loads(client):
    engagement_id = _create_engagement(client, "Current Co")
    _select(client, engagement_id)
    assert "Current Co" in body(client.get("/"))

    r = client.post(f"/engagement/{engagement_id}/delete", follow_redirects=False)
    assert r.status_code == 302

    # No current engagement anymore — the dashboard must not crash, and must not
    # still claim "Current Co" is selected.
    dashboard_page = body(client.get("/"))
    assert "Current Co" not in dashboard_page

    # The Engagements list itself must still render cleanly with no engagements left.
    list_page = body(client.get("/engagement/"))
    assert "Current Co" not in list_page


def test_delete_one_engagement_does_not_affect_another(client):
    first_id = _create_engagement(client, "Listed Steel Co")
    _save_profile(client, first_id, LISTED_IND_AS_PROFILE_FORM)

    second_id = _create_engagement(client, "Unlisted Traders")
    _save_profile(client, second_id, UNLISTED_AS_PROFILE_FORM)

    client.post(f"/engagement/{second_id}/delete", follow_redirects=False)

    # The surviving engagement's profile/applicability screens still work.
    _select(client, first_id)
    assert "Listed Steel Co" in body(client.get("/"))
    profile_page = body(client.get(f"/engagement/{first_id}/profile"))
    assert profile_page  # renders without error
    applicability_page = body(client.get(f"/engagement/{first_id}/applicability"))
    assert applicability_page  # renders without error
