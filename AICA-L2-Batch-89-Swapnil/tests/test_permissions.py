"""Golden tests 17–18 and the route × role permission matrix (brief §4, §9)."""
import pytest

ROLES = {"viewer": "VIEWER", "article1": "PREPARER", "manager": "MANAGER", "partner": "PARTNER", "owner": "OWNER"}
ALL = set(ROLES)
PREP_UP = {"article1", "manager", "partner", "owner"}
MGR_UP = {"manager", "partner", "owner"}
PARTNER_UP = {"partner", "owner"}
OWNER = {"owner"}


def obl_id(q, key):
    return q(lambda s, M: s.query(M.Obligation).filter_by(key=key).one().id)


def denied_count(q):
    return q(lambda s, M: s.query(M.AuditLog).filter_by(action="DENIED").count())


# ------------------------------------------------------------ golden 17
def test_g17_preparer_cannot_mark_filed(as_role, q):
    c = as_role("article1")
    oid = obl_id(q, "1:AOC4:FY2026-27")
    before = denied_count(q)
    r = c.post(f"/obligations/{oid}/status", data={"status": "FILED"})
    assert r.status_code == 403
    assert b"A preparer cannot mark an obligation filed. Mark it Ready for review; a partner will confirm." in r.data
    r = c.post(f"/obligations/{oid}/file", data={"srn": "D12345678", "filing_date": "2026-09-01"})
    assert r.status_code == 403
    assert denied_count(q) == before + 2
    assert q(lambda s, M: s.get(M.Obligation, oid).status) == "NOT_STARTED"


def test_g17_preparer_blocked_from_audit_staff_delete(as_role, q):
    c = as_role("article1")
    assert c.get("/admin/audit").status_code == 403
    assert c.get("/admin/users").status_code == 403
    assert c.post("/entities/1/delete").status_code == 403
    assert q(lambda s, M: s.get(M.Entity, 1)) is not None
    rows = q(lambda s, M: [(r.actor_name, r.after_json) for r in s.query(M.AuditLog).filter_by(action="DENIED")])
    assert any("read_audit" in a for _, a in rows) and any("manage_users" in a for _, a in rows)
    assert all(n == "Article Assistant One" for n, _ in rows)


def test_g17_maker_checker(as_role, q):
    m = as_role("manager")
    oid = obl_id(q, "3:MGT7:FY2025-26")
    assert m.post(f"/obligations/{oid}/status", data={"status": "READY_FOR_REVIEW"}).status_code == 302
    r = m.post(f"/obligations/{oid}/status", data={"status": "APPROVED_FOR_FILING"})
    assert r.status_code == 403 and "maker–checker" in r.data.decode()
    assert q(lambda s, M: s.get(M.Obligation, oid).status) == "READY_FOR_REVIEW"
    p = as_role("partner")
    assert p.post(f"/obligations/{oid}/status", data={"status": "APPROVED_FOR_FILING"}).status_code == 302
    o = q(lambda s, M: s.get(M.Obligation, oid))
    assert o.status == "APPROVED_FOR_FILING" and o.reviewer_id != o.ready_by_id


def test_preparer_to_ready_then_partner_files(as_role, q, app):
    oid = obl_id(q, "1:AOC4:FY2026-27")
    a = as_role("article1")
    for s in ("IN_PROGRESS", "READY_FOR_REVIEW"):
        assert a.post(f"/obligations/{oid}/status", data={"status": s}).status_code == 302
    assert a.post(f"/obligations/{oid}/status", data={"status": "APPROVED_FOR_FILING"}).status_code == 403
    p = as_role("partner")
    assert p.post(f"/obligations/{oid}/status", data={"status": "APPROVED_FOR_FILING"}).status_code == 302
    bad = p.post(f"/obligations/{oid}/file", data={"srn": "nope", "filing_date": "2026-09-20",
                                                   "normal_fee_paid": "400", "additional_fee_paid": "0"})
    assert bad.status_code == 422 and b"SRN" in bad.data
    r = p.post(f"/obligations/{oid}/file", data={"srn": "D12345678", "filing_date": "2026-09-20",
                                                 "normal_fee_paid": "400", "additional_fee_paid": "0"})
    assert r.status_code == 302
    f = q(lambda s, M: s.query(M.Filing).filter_by(obligation_id=oid).one())
    assert f.delay_days == 0 and not f.fee_mismatch and f.computed_fee_json["total"] == 400
    assert q(lambda s, M: s.get(M.Obligation, oid).status) == "FILED"


# ------------------------------------------------------------ golden 18
def test_g18_waiver_reason_length(as_role, q):
    oid = obl_id(q, "1:BOARD_MTGS:FY2026-27")
    p = as_role("partner")
    r = p.post(f"/obligations/{oid}/status", data={"status": "WAIVED", "reason": "too short"})
    assert r.status_code == 422 and b"at least 20 characters" in r.data
    reason = "Board meetings tracked in the planner; not an ROC form."
    r = p.post(f"/obligations/{oid}/status", data={"status": "NOT_APPLICABLE", "reason": reason})
    assert r.status_code == 302
    o = q(lambda s, M: s.get(M.Obligation, oid))
    assert o.status == "NOT_APPLICABLE" and o.status_reason == reason
    row = q(lambda s, M: s.query(M.AuditLog).filter_by(action="STATUS_CHANGED", object_id=o.key).one())
    assert "NOT_APPLICABLE" in row.after_json and row.actor_role == "PARTNER"


def test_manager_cannot_waive(as_role, q):
    oid = obl_id(q, "1:BOARD_MTGS:FY2026-27")
    r = as_role("manager").post(f"/obligations/{oid}/status",
                                data={"status": "WAIVED", "reason": "A long enough reason for the waiver."})
    assert r.status_code == 403 and b"Only a partner or owner" in r.data


# -------------------------------------------------------- route x role
def _matrix(q):
    alpha_aoc4 = obl_id(q, "1:AOC4:FY2026-27")
    return [
        ("GET", "/", {}, ALL),
        ("GET", "/work", {}, ALL),
        ("GET", "/entities", {}, ALL),
        ("GET", "/rules/", {}, ALL),
        ("GET", "/rules/AOC4", {}, ALL),
        ("GET", "/entities/1", {}, PREP_UP),                  # viewer has no assigned entities
        ("GET", f"/obligations/{alpha_aoc4}", {}, PREP_UP),
        ("GET", "/entities/new", {}, PREP_UP),
        ("GET", "/entities/1/edit", {}, PREP_UP),
        ("POST", "/entities/1/events", {"type": "ALLOTMENT", "event_date": "2026-09-01", "kind": "RIGHTS"}, PREP_UP),
        ("POST", "/entities/1/facts", {"fy_key": "FY2026-27", "turnover": "4000000"}, PREP_UP),
        ("POST", f"/obligations/{alpha_aoc4}/status", {"status": "IN_PROGRESS"}, PREP_UP),
        ("POST", f"/obligations/{alpha_aoc4}/assign", {"assignee_id": ""}, MGR_UP),
        ("POST", "/entities/1/archive", {}, MGR_UP),
        ("GET", "/admin/audit", {}, MGR_UP),
        ("GET", "/admin/audit.csv", {}, MGR_UP),
        ("POST", f"/obligations/{alpha_aoc4}/file", {"srn": "D1", "filing_date": "2026-09-01"}, PARTNER_UP),
        ("POST", "/entities/1/pan", {}, PARTNER_UP),
        ("POST", "/entities/4/decisions", {"key": "SMALL:FY2024-25", "value": "SMALL",
                                          "reason": "Partner view: new limits apply to late filing."}, PARTNER_UP),
        ("POST", "/rules/AOC4/verify", {"note": "Checked s.137(1) on India Code"}, PARTNER_UP),
        ("POST", "/entities/7/delete", {}, PARTNER_UP),
        ("GET", "/admin/users", {}, OWNER),
        ("POST", "/admin/users/5/unlock", {}, OWNER),
        ("GET", "/admin/settings", {}, OWNER),
        ("POST", "/admin/audit/verify", {}, OWNER),
    ]


@pytest.mark.parametrize("username", list(ROLES))
def test_route_role_matrix(username, as_role, q):
    c = as_role(username)
    failures = []
    for method, path, data, allowed in _matrix(q):
        r = c.get(path) if method == "GET" else c.post(path, data=data)
        ok = (r.status_code != 403) if username in allowed else (r.status_code == 403)
        if not ok or r.status_code >= 500:
            failures.append(f"{method} {path}: got {r.status_code}, allowed={username in allowed}")
    assert not failures, "\n".join(failures)


def test_every_protected_route_is_decorated(app):
    """No view function may skip @require (except the auth pages and static)."""
    open_endpoints = {"static", "auth.login", "auth.logout", "auth.change_password", "auth.totp", "auth.totp_setup"}
    missing = [ep for ep, fn in app.view_functions.items()
               if ep not in open_endpoints and not getattr(fn, "required_permission", None)]
    assert not missing, missing


def test_anonymous_redirected_to_login(client):
    r = client.get("/entities")
    assert r.status_code == 302 and "/login" in r.headers["Location"]
