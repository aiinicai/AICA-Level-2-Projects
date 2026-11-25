"""Phase 8: approver workflow, role permissions, audit viewer, local time."""
import re
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import session_scope
from app.engine.loader import run_forecast
from app.models import AuditLog, Override
from app.services.auth import create_user
from app.services.settings_service import update_business_settings
from tests.test_phase6_web import PW, app_client, csrf_of, loaded, login, token  # noqa: F401  (fixtures)


@pytest.fixture
def approval_on(loaded):
    with session_scope() as db:
        update_business_settings(db, {"approver_enabled": True}, None)
        create_user(db, "appr1", PW, "approver", must_change_password=False)
    return loaded


def _as(c, user):
    c.post("/logout", data={"csrf_token": token(c)})
    assert login(c, user).status_code == 303
    return c


def _hold(c, key, day, reason="Cash planning"):
    page = c.get("/pdcs?lot=4").text
    return c.post("/items/action", data={"source": "vendor_pdc", "key": key, "action": "hold", "mode": "pdc",
                                         "new_date": day, "reason": reason},
                  headers={"X-CSRF-Token": csrf_of(page), "HX-Request": "true"})


def _key(c):
    return re.search(r'name="key" value="([^"]+)"', c.get("/pdcs?lot=4").text).group(1)


def _holds():
    with session_scope() as db:
        fc = run_forecast(db)
        return {i.key: i.hold.honour_date.isoformat() for i in fc.holds}


def _decide(c, oid, decision, comment=""):
    page = c.get("/approvals").text
    return c.post(f"/approvals/{oid}", data={"decision": decision, "comment": comment, "csrf_token": csrf_of(page)},
                  follow_redirects=True)


def _pending_id(key):
    with session_scope() as db:
        return db.scalars(select(Override).where(Override.source_key == key, Override.is_active.is_(False),
                                                 Override.revoked_at.is_(None))).all()[-1].id


# ------------------------------------------------------------------ approval workflow
def test_hold_waits_for_approval_then_applies(approval_on):
    c = approval_on                                        # signed in as prep1
    key = _key(c)
    r = _hold(c, key, "2027-01-25")
    assert "Waiting for approval" in r.text
    assert key not in _holds()                             # the forecast does not use it yet
    page = c.get("/approvals").text
    assert key.split("|")[0] in page or "Hold cheque" in page
    assert "if approved" in page and "Approve</button>" not in page   # a Preparer cannot approve
    assert '<span class="badge text-bg-warning">1</span>' in c.get("/approvals/count").text
    oid = _pending_id(key)
    r = _decide(c, oid, "approve")
    assert r.status_code == 403                            # role check
    _as(c, "appr1")
    assert "Approve</button>" in c.get("/approvals").text
    r = _decide(c, oid, "approve", "agreed with vendor")
    assert "Approved" in r.text and "Nothing is waiting" in r.text
    assert _holds()[key] == "2027-01-25"
    with session_scope() as db:
        acts = [a.action for a in db.scalars(select(AuditLog).order_by(AuditLog.id))]
        assert "override.request.hold" in acts and "override.approve.hold" in acts


def test_change_keeps_approved_hold_until_decided_and_reject_needs_reason(approval_on):
    c = approval_on
    key = _key(c)
    _hold(c, key, "2027-01-25")
    _as(c, "appr1")
    _decide(c, _pending_id(key), "approve")
    _as(c, "prep1")
    assert "Waiting for approval" in _hold(c, key, "2027-01-28", "Vendor asked").text
    assert _holds()[key] == "2027-01-25"                   # approved hold stays in force
    _as(c, "appr1")
    oid = _pending_id(key)
    assert "give a reason" in _decide(c, oid, "reject").text
    r = _decide(c, oid, "reject", "not agreed")
    assert "Rejected" in r.text and "rejected" in r.text
    assert _holds()[key] == "2027-01-25"
    with session_scope() as db:
        assert "[rejected: not agreed]" in db.get(Override, oid).reason


def test_no_self_approval_and_withdraw_and_supersede(approval_on):
    c = approval_on
    _as(c, "admin1")
    key = _key(c)
    _hold(c, key, "2027-01-25")
    first = _pending_id(key)
    _hold(c, key, "2027-01-26")                            # supersedes the first request
    second = _pending_id(key)
    assert second != first
    with session_scope() as db:
        assert db.get(Override, first).revoked_at is not None
    assert "own" in c.get("/approvals").text
    assert "cannot approve your own" in _decide(c, second, "approve").text
    assert "Request withdrawn" in _decide(c, second, "withdraw").text
    assert key not in _holds()
    assert "withdrawn / superseded" in c.get("/approvals").text


def test_release_applies_at_once_with_approval_on(approval_on):
    c = approval_on
    key = _key(c)
    _hold(c, key, "2027-01-25")
    _as(c, "appr1")
    _decide(c, _pending_id(key), "approve")
    _as(c, "prep1")
    page = c.get("/pdcs?lot=4").text
    r = c.post("/items/action", data={"source": "vendor_pdc", "key": key, "action": "release", "mode": "pdc"},
               headers={"X-CSRF-Token": csrf_of(page), "HX-Request": "true"})
    assert "Hold released" in r.text and key not in _holds()


# ------------------------------------------------------------------ roles
@pytest.mark.parametrize("user,expect", [
    ("admin1", {"/forecast": 200, "/exports": 200, "/approvals": 200, "/audit": 200, "/admin/users": 200,
                "/admin/settings": 200}),
    ("prep1", {"/forecast": 200, "/exports": 200, "/approvals": 200, "/audit": 403, "/admin/users": 403,
               "/admin/settings": 403}),
    ("appr1", {"/forecast": 200, "/exports": 200, "/approvals": 200, "/audit": 200, "/admin/users": 403,
               "/admin/settings": 403}),
    ("view1", {"/forecast": 200, "/exports": 200, "/approvals": 200, "/audit": 403, "/admin/users": 403,
               "/admin/settings": 403}),
])
def test_role_matrix(approval_on, user, expect):
    c = _as(approval_on, user)
    for path, code in expect.items():
        assert c.get(path).status_code == code, (user, path)
    nav = c.get("/forecast").text
    assert ("/audit\"" in nav) == (expect["/audit"] == 200)
    page = c.get("/pdcs?lot=4").text
    can_edit = user in ("admin1", "prep1")
    assert ('<option value="hold">' in page) == can_edit
    if not can_edit:
        r = c.post("/items/action", data={"source": "vendor_pdc", "key": "x", "action": "exclude"},
                   headers={"X-CSRF-Token": csrf_of(page), "HX-Request": "true"})
        assert "Only a Preparer or Admin" in r.text
        r = c.post("/balances", data={"bank": "B", "account": "A", "balance": "1", "csrf_token": csrf_of(page)})
        assert r.status_code == 403


# ------------------------------------------------------------------ audit viewer
def test_audit_viewer_filters_and_csv(approval_on):
    c = approval_on
    key = _key(c)
    _hold(c, key, "2027-01-25")
    _as(c, "admin1")
    page = c.get("/audit?user=prep1&action=override").text
    assert "override.request.hold" in page and "login.ok" not in page
    assert "login.ok" in c.get("/audit?action=login").text
    assert "No entries match" in c.get("/audit?text=no-such-key-xyz").text
    c.get("/audit?date_from=bad")                                         # bad date is ignored, not an error
    r = c.get("/audit.csv?user=prep1&action=override")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    body = r.content.decode("utf-8-sig")
    assert "override.request.hold" in body and "time (local)" in body
    with session_scope() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "audit.download")).username == "admin1"


def test_csv_cells_cannot_run_as_formulas():
    from app.routers.review import _safe
    assert _safe("=HYPERLINK(1)") == "'=HYPERLINK(1)" and _safe("INV-1") == "INV-1" and _safe(None) == ""


def test_times_are_shown_in_oman_time():
    from app.web.templating import dmy
    assert dmy(datetime(2026, 11, 24, 6, 5)) == "24-Nov-2026 10:05"
