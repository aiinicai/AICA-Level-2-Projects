"""Golden tests 20, 21, 23 and the end-to-end flows of Phase 2."""
import os
import subprocess
import sys
from datetime import date, timedelta

import pyotp
import pytest

from conftest import AS_OF, PASSWORD, ROOT, login


def new_entity(**over):
    d = {"name": "Kappa Test Pvt Ltd", "entity_type": "PRIVATE", "cin": "U62099DL2026PTC009999",
         "incorporation_date": "2026-02-01", "nominal_capital": "1000000", "paid_up_capital": "100000",
         "has_share_capital": "on", "ro_furnished_at_incorporation": "on"}
    d.update(over)
    return d


# ------------------------------------------------------------ golden 20
def test_g20_validations(as_role, q):
    c = as_role("article1")
    r = c.post("/entities/new", data=new_entity(paid_up_capital="2000000"))
    assert r.status_code == 422 and b"Paid-up capital cannot be more than the authorised" in r.data
    r = c.post("/entities/new", data=new_entity(incorporation_date=(AS_OF + timedelta(days=1)).isoformat()))
    assert r.status_code == 422 and b"cannot be in the future" in r.data
    r = c.post("/entities/new", data=new_entity(cin="U62099DL2026PTC00999"))        # 20 characters
    assert r.status_code == 422 and b"exactly 21 characters; this one has 20" in r.data
    r = c.post("/entities/new", data=new_entity(pan="ABC123"))
    assert r.status_code == 422 and b"PAN should be" in r.data
    assert q(lambda s, M: s.query(M.Entity).filter_by(name="Kappa Test Pvt Ltd").count()) == 0


def test_create_entity_generates_and_warns_on_cin_suffix(as_role, q):
    c = as_role("article1")
    r = c.post("/entities/new", data=new_entity(entity_type="OPC", pan="AAECK1234K"), follow_redirects=True)
    assert r.status_code == 200 and b"The CIN says &#39;PTC&#39; but the entity type is OPC" in r.data
    e = q(lambda s, M: s.query(M.Entity).filter_by(name="Kappa Test Pvt Ltd").one())
    assert e.pan_enc and "AAECK1234K" not in e.pan_enc                      # encrypted at rest
    n = q(lambda s, M: s.query(M.Obligation).filter_by(entity_id=e.id).count())
    assert n > 5
    assert b"AAECK****K" in c.get(f"/entities/{e.id}").data              # masked for everyone
    p = as_role("partner")
    assert b"AAECK1234K" in p.post(f"/entities/{e.id}/pan").data         # full PAN to partner, audit-logged
    assert q(lambda s, M: s.query(M.AuditLog).filter_by(action="PAN_REVEALED").count()) == 1


# ------------------------------------------------------------ golden 21
def test_g21_lockout_and_owner_unlock(app, client, as_role, q):
    for i in range(4):
        assert login(client, "viewer", "wrong-password").status_code == 401
    r = login(client, "viewer", "wrong-password")
    assert r.status_code == 423 and b"locked for 15 minutes" in r.data
    r = login(client, "viewer", PASSWORD)                                  # right password, still locked
    assert r.status_code == 423
    fails = q(lambda s, M: s.query(M.LoginAttempt).filter_by(username="viewer", success=False).count())
    assert fails == 6
    assert q(lambda s, M: s.query(M.AuditLog).filter_by(action="ACCOUNT_LOCKED").count()) == 1
    uid = q(lambda s, M: s.query(M.User).filter_by(username="viewer").one().id)
    assert as_role("owner").post(f"/admin/users/{uid}/unlock").status_code == 302
    assert login(app.test_client(), "viewer", PASSWORD).status_code == 302


def test_lock_expires_after_15_minutes(app, client, q):
    for _ in range(5):
        login(client, "viewer", "nope")
    from app.models import User, db, utcnow
    with app.app_context():
        u = db.session.query(User).filter_by(username="viewer").one()
        u.locked_until = utcnow() - timedelta(seconds=1)
        db.session.commit()
    assert login(client, "viewer", PASSWORD).status_code == 302


def test_unknown_and_deactivated_users(app, client, as_role, q):
    assert login(client, "nobody", "whatever").status_code == 401
    uid = q(lambda s, M: s.query(M.User).filter_by(username="viewer").one().id)
    assert as_role("owner").post(f"/admin/users/{uid}/deactivate").status_code == 302
    r = login(app.test_client(), "viewer", PASSWORD)
    assert r.status_code == 403 and b"deactivated" in r.data
    assert q(lambda s, M: s.get(M.User, uid)) is not None               # never hard-deleted


def test_rate_limit(app, client):
    app.config["LOGIN_RATE_LIMIT"] = (3, 60)
    for _ in range(3):
        login(client, "nobody", "x")
    assert login(client, "nobody", "x").status_code == 429


# ------------------------------------------------------------ golden 23
def test_g23_same_db_from_any_working_directory(tmp_path):
    code = "from app.config import Config; print(Config().DATABASE_URL)"
    env = {**os.environ, "PYTHONPATH": str(ROOT), "SECRET_KEY": "x", "FERNET_KEY": "y"}
    env.pop("DATABASE_URL", None)
    urls = set()
    for cwd in (ROOT, tmp_path, ROOT / "app"):
        out = subprocess.run([sys.executable, "-c", code], cwd=cwd, env=env, capture_output=True, text=True, check=True)
        urls.add(out.stdout.strip())
    assert urls == {"sqlite:///" + (ROOT / "instance" / "mca.db").as_posix()}
    env["DATABASE_URL"] = "sqlite:///instance/other.db"                      # relative -> project root
    out = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "sqlite:///" + (ROOT / "instance" / "other.db").as_posix()


# ------------------------------------------------------ password & first login
def test_first_login_forces_password_change(app, q):
    from app.models import User, db
    with app.app_context():
        db.session.query(User).filter_by(username="viewer").one().must_change_password = True
        db.session.commit()
    c = app.test_client()
    assert login(c, "viewer").status_code == 302
    r = c.get("/")
    assert r.status_code == 302 and "/change-password" in r.headers["Location"]
    for bad, msg in [("short", b"at least 12"), ("password1234", b"commonly used"), ("viewer-long-pass-1", b"username")]:
        r = c.post("/change-password", data={"current": PASSWORD, "new": bad, "again": bad})
        assert r.status_code == 422 and msg in r.data
    r = c.post("/change-password", data={"current": PASSWORD, "new": "Tulsi-Garden-77", "again": "Tulsi-Garden-77"})
    assert r.status_code == 302
    assert c.get("/").status_code == 200
    assert login(app.test_client(), "viewer", "Tulsi-Garden-77").status_code == 302


# ------------------------------------------------------------ sessions
def test_idle_timeout_and_owner_revoke(app, as_role, q):
    c = as_role("manager")
    assert c.get("/").status_code == 200
    from app.models import UserSession, db, utcnow
    with app.app_context():
        s = db.session.query(UserSession).filter(UserSession.revoked_at.is_(None)).order_by(
            UserSession.created_at.desc()).first()
        s.last_seen_at = utcnow() - timedelta(minutes=31)
        db.session.commit()
    r = c.get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    c2 = as_role("manager")
    sid = q(lambda s, M: s.query(M.UserSession).filter(M.UserSession.revoked_at.is_(None)).order_by(
        M.UserSession.created_at.desc()).first().id)
    assert as_role("owner").post(f"/admin/sessions/{sid}/revoke").status_code == 302
    assert c2.get("/").status_code == 302


def test_absolute_session_life(app, as_role):
    c = as_role("manager")
    from app.models import UserSession, db, utcnow
    with app.app_context():
        for s in db.session.query(UserSession).all():
            s.expires_at = utcnow() - timedelta(seconds=1)
        db.session.commit()
    assert c.get("/").status_code == 302


def test_logout_revokes_server_session(as_role, q):
    c = as_role("manager")
    assert c.post("/logout").status_code == 302
    assert c.get("/").status_code == 302


# ------------------------------------------------------------------ TOTP
def test_totp_enrol_and_required_for_partners(app, as_role, q):
    o = as_role("owner")
    assert o.post("/admin/settings", data={"firm_name": "Demo & Co.", "firm_address": "Delhi", "firm_signatory": "P",
                                           "srn_regex": r"^[A-Z][0-9]{8}$", "totp_required_for_partners": "on",
                                           "adt1_for_first_auditor": "on", "retention_years": "8",
                                           "brand_primary": "#1f3a5f", "brand_accent": "#c9a227"}).status_code == 302
    p = app.test_client()
    login(p, "partner")
    r = p.get("/")
    assert r.status_code == 302 and "/totp/setup" in r.headers["Location"]
    p.get("/totp/setup")
    with p.session_transaction() as sess:
        secret = sess["totp_pending"]
    assert p.post("/totp/setup", data={"code": pyotp.TOTP(secret).now()}).status_code == 302
    assert p.get("/").status_code == 200
    # next sign-in needs the code
    p2 = app.test_client()
    login(p2, "partner")
    assert "/totp" in p2.get("/").headers["Location"]
    assert p2.post("/totp", data={"code": "000000"}).status_code == 401
    assert p2.post("/totp", data={"code": pyotp.TOTP(secret).now()}).status_code == 302
    assert p2.get("/").status_code == 200
    # a manager is not forced
    m = app.test_client()
    login(m, "manager")
    assert m.get("/").status_code == 200


# ------------------------------------------------------------ CSRF & headers
def test_csrf_enforced(app, template_db, tmp_path, monkeypatch):
    from conftest import TEST_ENV
    import shutil
    from app import create_app
    from app.auth import _rate
    _rate.clear()
    db_file = tmp_path / "csrf.db"
    shutil.copy(template_db, db_file)
    a = create_app(DATABASE_URL="sqlite:///" + db_file.as_posix(), AS_OF=AS_OF, SESSION_COOKIE_SECURE=False, TESTING=True)
    c = a.test_client()
    r = c.post("/login", data={"username": "partner", "password": PASSWORD})
    assert r.status_code == 400 and b"Form expired" in r.data


def test_security_and_cache_headers(as_role):
    c = as_role("manager")
    r = c.get("/entities")
    h = r.headers
    assert "nonce-" in h["Content-Security-Policy"] and "'unsafe-inline'" not in h["Content-Security-Policy"]
    assert h["X-Frame-Options"] == "DENY" and h["X-Content-Type-Options"] == "nosniff"
    assert h["Referrer-Policy"] == "same-origin" and h["Cache-Control"] == "no-store"
    assert "max-age" in c.get("/static/app.css").headers["Cache-Control"]


def test_session_cookie_flags(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] and app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    from app.config import Config
    assert Config().SESSION_COOKIE_SECURE is True                           # default for real runs


# -------------------------------------------------------- recompute & history
def test_agm_entry_recomputes_and_keeps_history(as_role, q):
    c = as_role("article1")
    key = "1:AOC4:FY2026-27"
    before = q(lambda s, M: s.query(M.Obligation).filter_by(key=key).one())
    assert before.due_date == date(2028, 1, 30) and before.provisional
    # AGM for FY2026-27 is in the future relative to AS_OF, so the UI refuses it...
    r = c.post("/entities/1/facts", data={"fy_key": "FY2026-27", "agm_date": "2027-09-15"}, follow_redirects=True)
    assert b"cannot be in the future" in r.data
    # ...but an actual AGM on a past FY moves dates and keeps history
    c.post("/entities/1/facts", data={"fy_key": "FY2026-27", "paid_up_capital": "100000", "turnover": "4000000",
                                      "auditor_appointed_at_agm": "yes"})
    g = as_role("manager")
    r = g.post("/entities/2/events", data={"type": "DIRECTOR_APPOINTED", "event_date": "2026-09-01"}, follow_redirects=True)
    assert b"exactly 8 digits" in r.data                                      # typed form needs the DIN
    g.post("/entities/2/events", data={"type": "DIRECTOR_APPOINTED", "event_date": "2026-09-01", "din": "10000999",
                                       "person_name": "Nisha Newcomer", "din_allotment_date": "2026-08-20",
                                       "designation": "Additional Director"})
    o = q(lambda s, M: s.query(M.Obligation).filter_by(key="2:DIR12:EVT-2026-09-01:" + str(
        s.query(M.Event).filter_by(entity_id=2).one().id)).one())
    assert o.due_date == date(2026, 10, 1)
    link = q(lambda s, M: s.query(M.EntityPerson).join(M.Person).filter(M.Person.din == "10000999").one())
    assert link.entity_id == 2 and link.designation == "Additional Director"
    # the new director's triennial KYC (DIN allotted FY 2026-27 -> 30-06-2030) now exists
    assert q(lambda s, M: s.query(M.Obligation).filter(M.Obligation.key.like("person:10000999:DIR3KYC_TRIENNIAL%")).one().due_date) == date(2030, 6, 30)


def test_due_date_change_is_audited(app, q):
    """Entering an AGM date moves AOC-4 and writes DUE_DATE_CHANGED with before/after (history)."""
    from app.models import AnnualFacts, Entity, Obligation, db
    from app.services import sync_entity
    with app.app_context():
        f = db.session.query(AnnualFacts).filter_by(entity_id=4, fy_key="FY2025-26").one()
        f.agm_date = date(2026, 9, 20)
        sync_entity(db.session.get(Entity, 4), AS_OF)
        db.session.commit()
        o = db.session.query(Obligation).filter_by(key="4:AOC4:FY2025-26").one()
        assert o.due_date == date(2026, 10, 20) and not o.provisional
    row = q(lambda s, M: s.query(M.AuditLog).filter_by(action="DUE_DATE_CHANGED", object_id="4:AOC4:FY2025-26").one())
    assert "2026-10-30" in row.before_json and "2026-10-20" in row.after_json


def test_recompute_idempotent_preserves_status(app, q):
    from app.services import recompute_all
    with app.app_context():
        s1 = recompute_all(AS_OF)
        s2 = recompute_all(AS_OF)
    assert s2["inserted"] == 0 and s2["updated"] == 0 and s2["superseded"] == 0
    assert q(lambda s, M: s.query(M.Obligation).filter_by(key="2:AOC4_OPC:FY2025-26").one().status) == "READY_FOR_REVIEW"
    keys = q(lambda s, M: [o.key for o in s.query(M.Obligation).all()])
    assert len(keys) == len(set(keys))


def test_rollover_adds_new_fy_and_supersedes_not_deletes(app, q):
    from app.models import Entity, Obligation, PeriodFlag, db
    from app.services import recompute_all, sync_entity
    with app.app_context():
        n = db.session.query(Obligation).count()
        recompute_all(date(2027, 4, 1))
        assert db.session.query(Obligation).filter_by(key="3:AOC4:FY2027-28").count() == 1
        assert db.session.query(Obligation).count() > n
        flag = db.session.query(PeriodFlag).filter_by(entity_id=1, period_key="FY2025-26").one()
        flag.value = False
        sync_entity(db.session.get(Entity, 1), AS_OF)
        db.session.commit()
        o = db.session.query(Obligation).filter_by(key="1:DPT3:FY2025-26").one()
        assert o.superseded_at is not None and o.status == "FILED"          # kept, never deleted


def test_upload_checks(as_role, q, app):
    import io
    oid = q(lambda s, M: s.query(M.Obligation).filter_by(key="1:AOC4:FY2026-27").one().id)
    p = as_role("partner")
    q(lambda s, M: (setattr(s.get(M.Obligation, oid), "status", "APPROVED_FOR_FILING"), s.commit()))
    data = {"srn": "D12345678", "filing_date": "2026-09-20", "normal_fee_paid": "400", "additional_fee_paid": "0",
            "attachment": (io.BytesIO(b"MZ\x90\x00 not a pdf"), "challan.pdf")}
    r = p.post(f"/obligations/{oid}/file", data=data, content_type="multipart/form-data")
    assert r.status_code == 422 and b"PDF or PNG" in r.data
    data["attachment"] = (io.BytesIO(b"%PDF-1.4 demo challan"), "challan.pdf")
    data["additional_fee_paid"] = "50"
    r = p.post(f"/obligations/{oid}/file", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert b"differ from the engine" in r.data                                 # fee mismatch flagged
    f = q(lambda s, M: s.query(M.Filing).filter_by(obligation_id=oid).one())
    assert f.fee_mismatch and f.attachment_path.endswith(".pdf") and "challan" not in f.attachment_path
    assert not (ROOT / "app" / "static" / f.attachment_path).exists()
    d = p.get(f"/files/{f.id}")
    assert d.status_code == 200 and d.data.startswith(b"%PDF")
    assert as_role("viewer").get(f"/files/{f.id}").status_code == 403


def test_decision_resolves_ambiguity(as_role, q):
    assert q(lambda s, M: s.query(M.Obligation).filter_by(key="4:MGT7:FY2024-25").one().needs_decision) == "SMALL:FY2024-25"
    p = as_role("partner")
    assert p.post("/entities/4/decisions", data={"key": "SMALL:FY2024-25", "value": "NOT_SMALL",
                                                 "reason": "short"}).status_code == 303
    p.post("/entities/4/decisions", data={"key": "SMALL:FY2024-25", "value": "NOT_SMALL",
                                          "reason": "Filed in Oct 2025 under the old limits; not small."})
    o = q(lambda s, M: s.query(M.Obligation).filter_by(key="4:MGT7:FY2024-25").one())
    assert o.needs_decision is None and o.form == "MGT-7"


def test_rule_verification_signoff(as_role, q):
    p = as_role("partner")
    assert b"Unverified" in p.get("/rules/AOC4").data
    p.post("/rules/AOC4/verify", data={"note": "Checked s.137(1) text on India Code, 25-09-2026"})
    r = p.get("/rules/AOC4")
    assert b"Partner Demo" in r.data
    oid = q(lambda s, M: s.query(M.Obligation).filter_by(key="3:AOC4:FY2025-26").one().id)
    assert b"Verified by Partner Demo" in p.get(f"/obligations/{oid}").data


@pytest.mark.parametrize("path", ["/", "/entities", "/entities/1", "/entities/3", "/entities/6", "/work", "/rules/",
                                  "/rules/DIR3KYC_TRIENNIAL", "/admin/users", "/admin/audit", "/admin/settings"])
def test_pages_render_for_owner(as_role, path):
    r = as_role("owner").get(path)
    assert r.status_code == 200, r.data[:300]


def test_obligation_pages_render(as_role, q):
    c = as_role("owner")
    ids = q(lambda s, M: [o.id for o in s.query(M.Obligation).filter(M.Obligation.superseded_at.is_(None)).all()])
    for oid in ids[::7]:
        assert c.get(f"/obligations/{oid}").status_code == 200
    theta = q(lambda s, M: s.query(M.Obligation).filter_by(key="8:AOC4:FY2023-24").one().id)
    r = c.get(f"/obligations/{theta}?what_if=2026-09-10")
    assert b"CCFS_2026" in r.data and "₹7,200".encode() in r.data


# ======================================================== Phase 3 screens
def test_wizard_company_end_to_end(as_role, q, app):
    c = as_role("article1")
    assert c.get("/entities/onboard").status_code == 200
    r = c.post("/entities/onboard?step=1", data={"name": "Iota Wizard Pvt Ltd", "entity_type": "PRIVATE",
                                                 "cin": "U62099DL2025PTC007777", "pan": "AAECI7777I",
                                                 "incorporation_date": "2025-06-10", "nominal_capital": "1,00,000",
                                                 "paid_up_capital": "100000", "has_share_capital": "on"})
    assert r.status_code == 302 and "step=2" in r.headers["Location"]
    with c.session_transaction() as s:
        assert "AAECI7777I" not in str(s["wiz"]) and s["wiz"]["entity"]["pan_enc"]      # no plain PAN in the cookie
    page = c.get("/entities/onboard?step=2").data
    assert b"31-03-2026" in page and b"31-12-2026" in page                                 # first FY end, first AGM
    c.post("/entities/onboard?step=2", data={})
    r = c.post("/entities/onboard?step=3", data={"din0": "10000101", "din1": "10000888", "name1": "Omar Onboard",
                                                 "allot1": "2025-06-01", "desig1": "Director"})
    assert r.status_code == 302
    c.post("/entities/onboard?step=4", data={"paid_up_capital": "100000", "turnover": "2500000"})
    preview = c.get("/entities/onboard?step=5")
    assert preview.status_code == 200 and b"obligations will be created" in preview.data and b"INC-20A" in preview.data
    r = c.post("/entities/onboard?step=5")
    assert r.status_code == 302
    e = q(lambda s, M: s.query(M.Entity).filter_by(name="Iota Wizard Pvt Ltd").one())
    assert e.preparer_id is not None
    assert q(lambda s, M: s.query(M.EntityPerson).filter_by(entity_id=e.id).count()) == 2
    assert q(lambda s, M: s.query(M.AnnualFacts).filter_by(entity_id=e.id, fy_key="FY2025-26").one().turnover) == 2_500_000
    assert q(lambda s, M: s.query(M.Obligation).filter_by(key=f"{e.id}:AOC4:FY2025-26").one().due_date) == date(2027, 1, 30)   # first AGM: 9 months
    assert c.get(f"/entities/{e.id}").status_code == 200


def test_wizard_validation_and_llp_election(as_role):
    c = as_role("article1")
    r = c.post("/entities/onboard?step=1", data={"name": "X", "entity_type": "PRIVATE", "incorporation_date": "2030-01-01"})
    assert r.status_code == 422 and b"cannot be in the future" in r.data
    assert c.get("/entities/onboard?step=3").status_code == 302                    # cannot skip ahead
    c.post("/entities/onboard?step=1", data={"name": "Kappa Wizard LLP", "entity_type": "LLP", "cin": "ABZ-4321",
                                             "incorporation_date": "2025-11-20", "llp_contribution": "200000"})
    page = c.get("/entities/onboard?step=2").data
    assert b"31-03-2026" in page and b"31-03-2027" in page and b"elected the longer" in page
    c.post("/entities/onboard?step=2", data={"elect_longer": "on"})
    c.post("/entities/onboard?step=3", data={})
    c.post("/entities/onboard?step=4", data={"turnover": "500000"})
    assert b"30-05-2027" in c.get("/entities/onboard?step=5").data


def test_typed_events(as_role, q):
    c = as_role("manager")
    page = c.get("/entities/5/events/new?type=CHARGE_CREATED")
    assert page.status_code == 200 and b"Amount secured" in page.data and b"CHG-1" in page.data
    frag = c.get("/entities/5/events/new?type=ALLOTMENT", headers={"HX-Request": "true"})
    assert frag.status_code == 200 and b"<html" not in frag.data and b"PAS-3" in frag.data
    c.post("/entities/5/events", data={"type": "AUTH_CAPITAL_INCREASE", "event_date": "2026-09-20",
                                       "new_authorised": "6,00,00,000"})
    assert q(lambda s, M: s.get(M.Entity, 5).nominal_capital) == 60_000_000
    assert q(lambda s, M: s.query(M.Obligation).filter(M.Obligation.key.like("5:SH7:%")).count()) == 1
    c.post("/entities/5/events", data={"type": "DIRECTOR_RESIGNED", "event_date": "2026-09-21", "din": "10000301"})
    link = q(lambda s, M: s.query(M.EntityPerson).join(M.Person).filter(M.EntityPerson.entity_id == 5, M.Person.din == "10000301").one())
    assert link.ceased_on == date(2026, 9, 21)
    assert q(lambda s, M: s.query(M.Obligation).filter(M.Obligation.key.like("5:DIR11:%")).count()) == 1
    r = c.post("/entities/5/events", data={"type": "DIRECTOR_RESIGNED", "event_date": "2026-09-22", "din": "10000101"},
               follow_redirects=True)
    assert b"is not a current director" in r.data
    r = c.post("/entities/5/events", data={"type": "PARTNER_CHANGE", "event_date": "2026-09-22"}, follow_redirects=True)
    assert b"applies to this entity" in r.data                                       # LLP event on a company
    r = c.post("/entities/5/events", data={"type": "BOARD_MEETING", "event_date": "2027-06-01"}, follow_redirects=True)
    assert b"more than 90 days ahead" in r.data


def test_llp_partner_admission(as_role, q):
    c = as_role("manager")
    c.post("/entities/6/events", data={"type": "PARTNER_CHANGE", "event_date": "2026-09-10", "change": "ADMISSION",
                                       "din": "10000666", "person_name": "Priya Partner", "din_allotment_date": "2026-09-01"})
    assert q(lambda s, M: s.query(M.Obligation).filter(M.Obligation.key.like("6:LLP_FORM4:%")).one().due_date) == date(2026, 10, 10)
    assert q(lambda s, M: s.query(M.EntityPerson).join(M.Person).filter(M.Person.din == "10000666").one().designation) == "Designated Partner"


def test_facts_screen(as_role, q):
    c = as_role("article1")
    r = c.get("/entities/1/facts")
    assert r.status_code == 200 and b"Drives" in r.data and b"FY2026-27" in r.data
    r = c.post("/entities/1/facts", data={"fy_key": "FY2026-27", "paid_up_capital": "1,00,000", "turnover": "40,00,000",
                                          "has_subs_assoc_jv": "yes"})
    assert r.status_code == 302 and "/facts" in r.headers["Location"]
    assert q(lambda s, M: s.query(M.Obligation).filter_by(key="1:AOC4_CFS:FY2026-27").count()) == 1
    assert c.post("/entities/1/facts", data={"fy_key": "FY1999-00"}).status_code == 303
    assert as_role("viewer").get("/entities/1/facts").status_code == 403


def test_directors_view(as_role, q):
    c = as_role("partner")
    r = c.get("/directors")
    assert r.status_code == 200 and b"Anil Placeholder" in r.data and b"Sunita Fictional" in r.data
    pid = q(lambda s, M: s.query(M.Person).filter_by(din="10000301").one().id)
    page = c.get(f"/directors/{pid}")
    assert page.status_code == 200 and b"30-06-2028" in page.data
    assert page.data.count(b"Gamma Industries") >= 1 and b"Epsilon Infra" in page.data
    c.post(f"/directors/{pid}/detail-change", data={"event_date": "2026-09-01", "changed": "email"})
    assert q(lambda s, M: s.query(M.Obligation).filter_by(key="person:10000301:DIR3KYC_CHANGE:CHG-2026-09-01").one().due_date) == date(2026, 10, 1)
    assert c.post(f"/directors/{pid}/kyc-override", data={"first_due": "2029-06-30", "reason": "short"}).status_code == 303
    c.post(f"/directors/{pid}/kyc-override", data={"first_due": "2029-06-30",
                                                   "reason": "Partner reading of rule 12A for this DIN history."})
    assert q(lambda s, M: s.query(M.Obligation).filter_by(key="person:10000301:DIR3KYC_TRIENNIAL:KYC-CYCLE-2026-27..2028-29").count()) == 1
    c.post(f"/directors/{pid}/edit", data={"email": "x@example.invalid", "dsc_expiry": "2027-01-01", "din_status": "APPROVED"})
    assert q(lambda s, M: s.get(M.Person, pid).dsc_expiry) == date(2027, 1, 1)
    a = as_role("article1")
    assert b"Ravi Demo-Kumar" in a.get("/directors").data and b"Anil Placeholder" not in a.get("/directors").data
    assert a.get(f"/directors/{pid}").status_code == 403


def test_fee_calculator(as_role):
    c = as_role("viewer")
    r = c.get("/tools/fees?rule=AOC4&entity_id=&etype=PRIVATE&nominal=500000&due=2024-10-30&filed=2026-09-10")
    assert r.status_code == 200 and "₹7,200".encode() in r.data and b"CCFS_2026" in r.data and b"Estimate" in r.data
    frag = c.get("/tools/fees?rule=LLP_FORM11&etype=LLP&contribution=800000&small=yes&due=2026-05-30&filed=2026-09-20",
                 headers={"HX-Request": "true"})
    assert b"<html" not in frag.data and "₹1,650".encode() in frag.data
    assert b"Choose a form" in c.get("/tools/fees?rule=AOC4").data
    p = as_role("partner")
    assert "₹4,400".encode() in p.get("/tools/fees?rule=ADT1&etype=PRIVATE&nominal=500000&due=2024-01-10&filed=2024-04-28").data
    assert p.get("/tools/fees?rule=AOC4&entity_id=8&due=2024-10-30&filed=2026-09-10").status_code == 200


def test_board_planner(as_role):
    c = as_role("manager")
    r = c.get("/tools/board?entity_id=3")
    assert r.status_code == 200 and b"Regular" in r.data and b"No Board meeting recorded" in r.data
    for d in ("2026-01-10", "2026-06-15"):
        c.post("/entities/3/events", data={"type": "BOARD_MEETING", "event_date": d})
    r = c.get("/tools/board?entity_id=3")
    assert b"156 days" in r.data and b"more than 120" in r.data and b"Breach" in r.data
    r = c.get("/tools/board?entity_id=1")
    assert b"Relaxed" in r.data
    assert b"do not apply" in c.get("/tools/board?entity_id=2").data               # single-director OPC
    assert c.get("/tools/board?entity_id=6").status_code == 404                    # LLP


def test_work_queue_htmx_and_bulk_assign(as_role, q):
    a = as_role("article1")
    r = a.get("/work?sort=entity")
    assert r.status_code == 200
    oid = q(lambda s, M: s.query(M.Obligation).filter_by(key="1:AOC4:FY2026-27").one().id)
    q(lambda s, M: (setattr(s.get(M.Obligation, oid), "assignee_id", s.query(M.User).filter_by(username="article1").one().id), s.commit()))
    r = a.post(f"/obligations/{oid}/status", data={"status": "IN_PROGRESS"}, headers={"HX-Request": "true"})
    assert r.status_code == 200 and f'id="obl-{oid}"'.encode() in r.data and b"<html" not in r.data
    r = a.post(f"/obligations/{oid}/status", data={"status": "FILED"}, headers={"HX-Request": "true"})
    assert r.status_code == 403 and r.headers["HX-Retarget"] == "#htmx-alerts" and b"A preparer cannot" in r.data
    r = a.post(f"/obligations/{oid}/status", data={"status": "ROC_APPROVED"}, headers={"HX-Request": "true"})
    assert r.status_code == 422 and b"cannot move" in r.data
    m = as_role("manager")
    ids = q(lambda s, M: [o.id for o in s.query(M.Obligation).filter(M.Obligation.entity_id == 3).limit(3)])
    uid = q(lambda s, M: s.query(M.User).filter_by(username="article1").one().id)
    assert m.post("/work/assign", data={"ids": ids, "assignee_id": uid}).status_code == 302
    assert q(lambda s, M: all(s.get(M.Obligation, i).assignee_id == uid for i in ids))
    assert b"Team queue" in m.get("/work?scope=team").data and b"Unassigned" in m.get("/work?scope=unassigned").data
    assert a.post("/work/assign", data={"ids": ids, "assignee_id": uid}).status_code == 403
    assert m.post("/work/assign", data={"assignee_id": uid}).status_code == 303


def test_notes_and_documents(as_role, q):
    import io
    c = as_role("article1")
    c.post("/entities/1/notes", data={"notes": "Client prefers e-mail reminders."})
    assert q(lambda s, M: s.get(M.Entity, 1).notes) == "Client prefers e-mail reminders."
    r = c.post("/entities/1/documents", data={"title": "COI", "file": (io.BytesIO(b"%PDF-1.7 coi"), "coi.pdf")},
               content_type="multipart/form-data")
    assert r.status_code == 302
    doc = q(lambda s, M: s.query(M.Document).one())
    assert doc.stored_name.endswith(".pdf") and doc.original_name == "coi.pdf"
    assert c.get(f"/documents/{doc.id}").data.startswith(b"%PDF")
    bad = c.post("/entities/1/documents", data={"file": (io.BytesIO(b"<script>"), "x.pdf")},
                 content_type="multipart/form-data", follow_redirects=True)
    assert b"Only PDF or PNG" in bad.data
    assert as_role("viewer").get(f"/documents/{doc.id}").status_code == 403


def test_entity_filters(as_role):
    c = as_role("partner")
    r = c.get("/entities?health=overdue")
    assert b"Theta Foods" in r.data and b"Eta Consulting" not in r.data
    r = c.get("/entities?type=LLP")
    assert b"Zeta Advisors" in r.data and b"Gamma" not in r.data
    assert c.get("/entities?roc=RoC-Delhi&rm=2&health=due30").status_code == 200
    assert c.get("/entities?health=clear").status_code == 200


@pytest.mark.parametrize("user", ["viewer", "article1", "manager", "partner", "owner"])
def test_every_screen_renders_per_role(as_role, user):
    c = as_role(user)
    for path in ["/", "/work", "/entities", "/directors", "/tools/fees", "/tools/board", "/rules/", "/rules/AOC4"]:
        r = c.get(path)
        assert r.status_code == 200, (user, path, r.status_code)
        assert b"Chartered Accountants" in r.data and b"monogram" in r.data


# ======================================================== Phase 4
def _ics_lines(body: bytes) -> list[str]:
    text = body.decode("utf-8")
    assert "\r\n" in text and "\n" not in text.replace("\r\n", "")          # CRLF only (RFC 5545 §3.1)
    physical = text.split("\r\n")
    assert all(len(p.encode("utf-8")) <= 75 for p in physical), "a line exceeds 75 octets"
    logical = []
    for p in physical:                                                        # unfold
        if p.startswith(" ") and logical:
            logical[-1] += p[1:]
        elif p:
            logical.append(p)
    return logical


def test_ics_export_is_valid_rfc5545(as_role, q):
    r = as_role("partner").get("/calendar.ics?scope=firm")
    assert r.status_code == 200 and r.mimetype == "text/calendar" and "attachment" in r.headers["Content-Disposition"]
    lines = _ics_lines(r.data)
    assert lines[0] == "BEGIN:VCALENDAR" and lines[-1] == "END:VCALENDAR" and "VERSION:2.0" in lines
    assert lines.count("BEGIN:VEVENT") == lines.count("END:VEVENT") > 50
    assert lines.count("BEGIN:VALARM") == lines.count("END:VALARM")
    uids = [ln for ln in lines if ln.startswith("UID:")]
    assert len(uids) == len(set(uids))
    theta = next(i for i, ln in enumerate(lines) if ln.startswith("UID:8-AOC4-FY2023-24"))
    block = lines[theta - 1: theta + 12]
    assert "DTSTART;VALUE=DATE:20241030" in block and "DTEND;VALUE=DATE:20241031" in block
    assert any(ln.startswith("SUMMARY:AOC-4 — Theta Foods Pvt Ltd") for ln in block)
    assert any("\\n" in ln and ln.startswith("DESCRIPTION:") for ln in block)       # escaped newlines
    assert q(lambda s, M: s.query(M.AuditLog).filter_by(action="ICS_EXPORTED").count()) == 1


def test_ics_mine_and_entity_scopes(as_role):
    a = as_role("article1")
    mine = _ics_lines(a.get("/calendar.ics?scope=mine").data)
    assert mine.count("BEGIN:VEVENT") > 0
    ent = _ics_lines(a.get("/calendar.ics?scope=entity&entity_id=1").data)
    assert all("Theta" not in ln for ln in ent if ln.startswith("SUMMARY:"))
    assert a.get("/calendar.ics?scope=entity&entity_id=3").status_code == 404        # not assigned to her


def test_ics_escape_and_fold_unit():
    from app.exports import ics_escape, ics_fold
    assert ics_escape("a,b;c\\d\ne") == "a\\,b\\;c\\\\d\\ne"
    long = "SUMMARY:" + "₹" * 40                                                      # 3-byte characters
    parts = ics_fold(long).split("\r\n")
    assert all(len(p.encode()) <= 75 for p in parts)
    assert parts[0] + "".join(p[1:] for p in parts[1:]) == long


def test_calendar_views(as_role):
    c = as_role("manager")
    r = c.get("/calendar?month=2026-10")
    assert r.status_code == 200 and b"October 2026" in r.data and b"cal-item" in r.data
    r = c.get("/calendar?view=agenda&from=2026-09-25&to=2026-12-31&entity_id=3")
    assert r.status_code == 200 and b"Gamma Industries Pvt Ltd</a>" in r.data and b"Theta Foods Pvt Ltd</a>" not in r.data
    assert c.get("/calendar?month=bad").status_code == 200
    assert c.get("/calendar?form=AOC4&staff=3").status_code == 200


def test_register_and_overdue_excel_open_and_check(as_role):
    import io
    from datetime import datetime as dt
    from openpyxl import load_workbook
    c = as_role("partner")
    r = c.get("/reports/register.xlsx")
    assert r.status_code == 200 and r.mimetype.endswith("spreadsheetml.sheet")
    wb = load_workbook(io.BytesIO(r.data))
    assert wb.sheetnames == ["About", "Compliance register"]
    ws = wb["Compliance register"]
    headers = [c.value for c in ws[1]]
    assert headers[:6] == ["Entity / person", "CIN / DIN", "Form", "Period", "Due date", "Health"]
    assert ws.max_row > 100 and ws.freeze_panes == "A2"
    assert isinstance(ws["E2"].value, dt) and ws["E2"].number_format == "DD-MM-YYYY"
    assert "INTERNAL" in str(wb["About"]["B7"].value)
    r = c.get("/reports/overdue.xlsx")
    ws = load_workbook(io.BytesIO(r.data))["Overdue & fee exposure"]
    theta = [row for row in ws.iter_rows(min_row=2, values_only=True) if row[0] == "Theta Foods Pvt Ltd" and row[1] == "AOC-4"]
    assert theta and theta[0][4] == 695 and theta[0][8] == 69900                      # ₹400 + 695 × ₹100


def test_reports_page_and_kpis(as_role):
    r = as_role("manager").get("/reports")
    assert r.status_code == 200 and b"Entity compliance score" in r.data and b"Staff productivity" in r.data
    assert "₹".encode() in r.data


def test_client_letter_blocked_until_rules_verified(as_role, q):
    import re
    p = as_role("partner")
    r = p.get("/letters?entity_id=2&from=2026-09-01&to=2026-12-31")
    assert r.status_code == 409 and b"Export blocked" in r.data and b"AOC4_OPC" in r.data
    assert q(lambda s, M: s.query(M.AuditLog).filter_by(action="EXPORT_BLOCKED").count()) == 1
    codes = re.search(rb'<span class="mono">([A-Z0-9_, ]+)</span>', r.data).group(1).decode().split(", ")
    for code in codes:
        p.post(f"/rules/{code}/verify", data={"note": f"Checked {code} against the primary source (test)"})
    r = p.get("/letters?entity_id=2&from=2026-09-01&to=2026-12-31")
    assert r.status_code == 200 and b"Subject: MCA / ROC compliances" in r.data and b"AOC-4" in r.data
    assert b"Signed audited financial statements" in r.data and b"nonce=" in r.data
    row = q(lambda s, M: s.query(M.AuditLog).filter_by(action="CLIENT_LETTER").one())
    assert "2:AOC4_OPC:FY2025-26" in row.after_json
    assert p.get("/letters").status_code == 200


def test_reminders_idempotent_and_notifications(app, as_role, q):
    from app.exports import run_reminders
    with app.app_context():
        first = run_reminders(date(2026, 9, 20))            # Beta AOC-4 (OPC) due 27-09-2026 -> T-7
        again = run_reminders(date(2026, 9, 20))
    assert first["notifications"] > 0 and again["notifications"] == 0
    rows = q(lambda s, M: [(s.get(M.User, n.user_id).username, n.kind)
                           for n in s.query(M.Notification).join(M.Obligation, M.Notification.obligation_id == M.Obligation.id).filter(M.Obligation.key == "2:AOC4_OPC:FY2025-26")])
    assert ("article1", "T-7") in rows and ("partner", "T-7") in rows              # assignee + RM
    with app.app_context():
        run_reminders(date(2026, 9, 28))                    # first overdue day
    assert q(lambda s, M: s.query(M.Notification).filter_by(kind="OVERDUE").count()) > 0
    a = as_role("article1")
    page = a.get("/notifications")
    assert page.status_code == 200 and b"T-7" in page.data
    assert b'class="count"' in a.get("/").data
    a.post("/notifications/read")
    assert b'class="count"' not in a.get("/").data


def test_nightly_job(app, q):
    from app.exports import nightly
    with app.app_context():
        stats = nightly(date(2027, 4, 1), catch_up=True)
    assert stats["entities"] == 8 and stats["inserted"] > 0 and stats["notifications"] > 0 and stats["emails"] == 0
    assert q(lambda s, M: s.query(M.Obligation).filter_by(key="3:AOC4:FY2027-28").count()) == 1


def _app_with_rulepack_copy(template_db, tmp_path):
    import shutil
    from app import create_app
    from app.auth import _rate
    _rate.clear()
    shutil.copytree(ROOT / "rulepack", tmp_path / "rulepack")
    shutil.copy(template_db, tmp_path / "rp.db")
    return create_app(DATABASE_URL="sqlite:///" + (tmp_path / "rp.db").as_posix(), AS_OF=AS_OF, TESTING=True,
                      SESSION_COOKIE_SECURE=False, WTF_CSRF_ENABLED=False, RULEPACK_DIR=tmp_path / "rulepack")


def test_g24_rule_edit_publish_diff_and_fresh_due_date(template_db, tmp_path):
    a = _app_with_rulepack_copy(template_db, tmp_path)
    o = a.test_client()
    assert login(o, "owner").status_code == 302
    assert o.post("/rules/publish").status_code == 302                              # publish 2026.09.25-1
    from app.models import AuditLog, Obligation, db
    with a.app_context():
        oid = db.session.query(Obligation).filter_by(key="1:INC20A:ONCE").one().id
    before = o.get(f"/obligations/{oid}")
    assert b"19-07-2026" in before.data and before.headers["Cache-Control"] == "no-store"
    path = tmp_path / "rulepack" / "companies_onetime.yaml"
    text = path.read_text(encoding="utf-8")
    bad = o.post("/rules/edit/companies_onetime.yaml",
                 data={"content": text.replace("anchor: INCORPORATION", "anchor: WHENEVER", 1)})
    assert bad.status_code == 422 and b"code=FIRST_BM" in bad.data and path.read_text(encoding="utf-8") == text
    marker = "    offset: {days: 180}\n    recurrence: once\n    fee_regime: MULTIPLIER"
    assert marker in text
    new = text.replace(marker, marker.replace("180", "150"))
    assert o.post("/rules/edit/companies_onetime.yaml", data={"content": new}).status_code == 302
    o.post("/rules/edit/VERSION", data={"content": "2026.09.25-2"})
    after = o.get(f"/obligations/{oid}")
    assert b"19-06-2026" in after.data and b"2026.09.25-2" in after.data and after.headers["Cache-Control"] == "no-store"
    diff = o.get("/rules/versions")
    assert b"INC20A" in diff.data and b"has not been published" in diff.data
    assert o.post("/rules/publish").status_code == 302
    assert b"No differences" in o.get("/rules/versions?a=2026.09.25-2&b=current").data
    assert b"INC20A" in o.get("/rules/versions?a=2026.09.25-1&b=2026.09.25-2").data
    with a.app_context():
        assert db.session.query(AuditLog).filter_by(action="RULEPACK_EDITED").count() == 2
        assert db.session.query(AuditLog).filter_by(action="DUE_DATE_CHANGED", object_id="1:INC20A:ONCE").count() == 1
    o.post("/rules/edit/VERSION", data={"content": "2026.09.25-1"})                  # re-using a published version
    r = o.post("/rules/publish", follow_redirects=True)
    assert b"already published with different content" in r.data
    db.session.remove()
    db.engine.dispose()


def test_rule_edit_and_publish_owner_only(as_role):
    p = as_role("partner")
    assert p.get("/rules/edit/fees.yaml").status_code == 403
    assert p.post("/rules/publish").status_code == 403
    assert as_role("owner").get("/rules/edit/nope.yaml").status_code == 404
    assert as_role("viewer").get("/rules/versions").status_code == 200


def test_regulatory_update_log(as_role, q):
    o = as_role("owner")
    r = o.post("/rules/updates", data={"number": "G.S.R. 943(E)", "issued_on": "2025-12-31",
                                       "url": "https://example.invalid/gsr943",
                                       "summary": "DIR-3 KYC made triennial from 31-03-2026",
                                       "codes": ["DIR3KYC_ANNUAL", "DIR3KYC_TRIENNIAL"],
                                       "rel_DIR3KYC_ANNUAL": "closed", "rel_DIR3KYC_TRIENNIAL": "created"})
    assert r.status_code == 302
    page = o.get("/rules/updates")
    assert b"G.S.R. 943(E)" in page.data and b"closed DIR3KYC_ANNUAL" in page.data
    assert b"G.S.R. 943(E)" in o.get("/rules/DIR3KYC_TRIENNIAL").data
    assert o.post("/rules/updates", data={"number": "x"}).status_code == 303
    assert o.post("/rules/updates", data={"number": "GC 1", "issued_on": "2026-01-01", "summary": "long enough summary",
                                          "url": "javascript:alert(1)"}).status_code == 303
    assert as_role("partner").post("/rules/updates", data={"number": "x"}).status_code == 403


def test_scheduler_registers_nightly_job(app):
    from app.exports import start_scheduler
    sched = start_scheduler(app)
    try:
        job = sched.get_job("nightly")
        assert job is not None and "hour='1'" in str(job.trigger) and "minute='0'" in str(job.trigger)
        assert job.next_run_time.utcoffset().total_seconds() == 5.5 * 3600         # 01:00 IST
    finally:
        sched.shutdown(wait=False)


def test_email_digest_via_fake_smtp(app, monkeypatch):
    import smtplib
    from app.exports import run_reminders, send_digests
    from app.models import Notification, User, db
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            assert host == "smtp.example.invalid" and port == 587

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            pass

        def login(self, user, pw):
            assert user == "mailer"

        def send_message(self, m):
            sent.append(m)

    with app.app_context():
        assert send_digests({1: []}) == 0                                         # SMTP not configured
        run_reminders(date(2026, 9, 20))
        u = db.session.query(User).filter_by(username="article1").one()
        u.email = "article1@example.invalid"
        db.session.commit()
        notes = db.session.query(Notification).filter_by(user_id=u.id).all()
        monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
        monkeypatch.setenv("SMTP_HOST", "smtp.example.invalid")
        monkeypatch.setenv("SMTP_USER", "mailer")
        assert send_digests({u.id: notes, 999: notes}) == 1
    assert sent and sent[0]["To"] == "article1@example.invalid" and "reminder" in sent[0]["Subject"]
    assert "AOC-4" in sent[0].get_content()
