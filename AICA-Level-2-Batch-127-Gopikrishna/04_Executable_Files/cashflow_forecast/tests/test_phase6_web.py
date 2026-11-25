import re
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import session_scope
from app.models import AuditLog, Override, User
from app.services.auth import create_user

ROOT = Path(__file__).resolve().parents[1]
DAY1 = ROOT / "synthetic_data" / "day1_2026-11-24"
PW = "Test-pass-2468"          # test-only password for synthetic test users


def csrf_of(html: str) -> str:
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


@pytest.fixture
def app_client():
    from app.main import create_app
    application = create_app()                     # creates the tables in the test's own instance
    with session_scope() as db:
        for name, role in (("admin1", "admin"), ("prep1", "preparer"), ("view1", "viewer")):
            create_user(db, name, PW, role, must_change_password=False)
    with TestClient(application, base_url="http://localhost") as c:
        yield c


def login(c: TestClient, user: str, pw: str = PW):
    tok = csrf_of(c.get("/login").text)
    return c.post("/login", data={"username": user, "password": pw, "csrf_token": tok}, follow_redirects=False)


def token(c: TestClient) -> str:
    return csrf_of(c.get("/balances").text)


def upload(c, source, path: Path, tok):
    with path.open("rb") as fh:
        return c.post("/uploads", data={"source": source, "as_of": "2026-11-24", "csrf_token": tok},
                      files={"file": (path.name, fh)}, follow_redirects=True)


@pytest.fixture
def loaded(app_client):
    c = app_client
    assert login(c, "prep1").status_code == 303
    tok = token(c)
    for src, f in [("category_list", "category_list.xlsx"), ("bank_balances", "bank_balances.csv"),
                   ("bank_facility", "bank_facility.csv"), ("collections", "erp_receivables.xlsx"),
                   ("vendor_pdc", "erp_pdc_register.xlsx"), ("bill_discount", "bank_bd_lc.xlsx"),
                   ("other", "other_recurring_wide.xlsx")]:
        r = upload(c, src, DAY1 / f, tok)
        assert r.status_code == 200 and "rejected" not in r.text.split("Upload #")[1][:300], f
    return c


# ---------------------------------------------------------------- security
def test_login_required_and_security_headers(app_client):
    r = app_client.get("/forecast", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/login")
    r = app_client.get("/login")
    csp = r.headers["content-security-policy"]
    assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp
    assert r.headers["x-frame-options"] == "DENY" and r.headers["x-content-type-options"] == "nosniff"
    assert "http://" not in r.text and "https://" not in r.text            # no CDN, no outside links


def test_wrong_password_lockout_and_audit(app_client):
    for _ in range(5):
        r = login(app_client, "view1", "wrong-password-1")
        assert r.status_code == 401 and "not correct" in r.text
    r = login(app_client, "view1")                                         # right password, but locked
    assert r.status_code == 401 and "locked" in r.text
    with session_scope() as db:
        assert db.scalar(select(User).where(User.username == "view1")).locked_until is not None
        assert len(db.scalars(select(AuditLog).where(AuditLog.action == "login.failed")).all()) == 5


def test_csrf_required(app_client):
    login(app_client, "prep1")
    r = app_client.post("/balances", data={"bank": "X", "account": "Y", "balance": "1"})
    assert r.status_code == 403 and "expired" in r.text


def test_must_change_password_first(app_client):
    with session_scope() as db:
        create_user(db, "newbie", PW, "viewer")
    r = login(app_client, "newbie")
    assert r.headers["location"] == "/account/password"
    assert app_client.get("/forecast", follow_redirects=False).headers["location"] == "/account/password"
    page = app_client.get("/account/password").text
    assert "hx-get" not in page                       # no background loads on this page (they used to loop)
    r = app_client.get("/exceptions/count", headers={"HX-Request": "true"}, follow_redirects=False)
    assert r.status_code == 204 and r.headers["hx-redirect"] == "/account/password" and r.text == ""
    tok = csrf_of(page)
    r = app_client.post("/account/password", data={"current": PW, "new": "Another-pass-97531",
                                                   "confirm": "Another-pass-97531", "csrf_token": tok},
                        follow_redirects=False)
    assert r.status_code == 303 and app_client.get("/forecast").status_code == 200


def test_viewer_is_read_only(loaded):
    c = loaded
    c.post("/logout", data={"csrf_token": token(c)})
    login(c, "view1")
    assert c.get("/forecast").status_code == 200 and c.get("/pdcs").status_code == 200
    tok = csrf_of(c.get("/forecast").text)
    r = c.post("/items/action", data={"source": "vendor_pdc", "key": "x", "action": "exclude"},
               headers={"X-CSRF-Token": tok, "HX-Request": "true"})
    assert "Only a Preparer or Admin" in r.text
    assert c.get("/admin/settings").status_code == 403
    assert '<option value="hold">' not in c.get("/pdcs").text             # no action drop-down for viewers


# ---------------------------------------------------------------- screens
def test_uploads_exceptions_and_grid(loaded):
    c = loaded
    page = c.get("/uploads").text
    assert "erp_pdc_register.xlsx" in page and "current" in page
    exc = c.get("/exceptions").text
    assert "Visa Renewal Fees" in exc and "Visa &amp; labour fees" in exc
    assert "bill discounted invoice" in exc and "INV-26-1416" in exc
    exc_id = re.search(r'action="/exceptions/(\d+)"', exc).group(1)
    cat_id = re.search(r'<option value="(\d+)" selected>Visa &amp; labour fees', exc).group(1)
    r = c.post(f"/exceptions/{exc_id}", data={"how": "map", "category_id": cat_id, "remember": "1",
                                              "csrf_token": token(c)}, follow_redirects=True)
    assert "The file is now current" in r.text and "No open exceptions" in r.text
    grid = c.get("/forecast").text
    for text in ("01-10 Dec", "Dec 2026 total", "Horizon total", "Vendor PDCs", "Visa &amp; labour fees",
                 "NET FUNDING POSITION AFTER HOLDS", "Are the holds sufficient?", "CURRENT"):
        assert text in grid, text
    cell = re.search(r'hx-get="(/forecast/cell\?lot=1&(?:amp;)?cat=\d+)"', grid).group(1).replace("&amp;", "&")
    assert "item(s)" in c.get(cell).text


def test_hold_from_pdc_list_recalculates(loaded):
    c = loaded
    page = c.get("/pdcs?lot=4").text
    assert "Next honouring date" in page and "NET FUNDING POSITION AFTER HOLDS" in page
    key = re.search(r'name="key" value="([^"]+)"', page).group(1)
    tok = csrf_of(page)
    r = c.post("/items/action", data={"source": "vendor_pdc", "key": key, "action": "hold", "mode": "pdc",
                                      "new_date": "2027-01-25", "reason": "Await delivery note"},
               headers={"X-CSRF-Token": tok, "HX-Request": "true"})
    assert r.headers.get("hx-trigger") == "forecast-changed"
    assert "Held until 25-Jan-2027" in r.text and "On hold" in r.text
    holds = c.get("/holds").text
    assert key in holds and "Await delivery note" in holds and "21-31 Jan" in holds
    r = c.post("/items/action", data={"source": "vendor_pdc", "key": key, "action": "hold", "mode": "pdc",
                                      "new_date": "2026-01-01"}, headers={"X-CSRF-Token": tok, "HX-Request": "true"})
    assert "Not saved" in r.text and "after the cheque date" in r.text and "hx-trigger" not in r.headers
    r = c.post("/items/action", data={"source": "vendor_pdc", "key": key, "action": "release", "mode": "pdc"},
               headers={"X-CSRF-Token": tok, "HX-Request": "true"})
    assert "Hold released" in r.text
    assert key in c.get("/holds").text                                     # now in the history
    with session_scope() as db:
        assert db.scalars(select(Override).where(Override.source_key == key)).one().is_active is False
        assert db.scalar(select(AuditLog).where(AuditLog.action == "override.add.hold")).username == "prep1"


def test_defer_and_back_to_imported(loaded):
    c = loaded
    page = c.get("/pdcs?lot=0").text
    key = re.search(r'name="key" value="([^"]+)"', page).group(1)
    hdr = {"X-CSRF-Token": csrf_of(page), "HX-Request": "true"}
    r = c.post("/items/action", data={"source": "vendor_pdc", "key": key, "action": "defer", "mode": "pdc",
                                      "lot_start": "2026-12-21"}, headers=hdr)
    assert "Defer to lot saved" in r.text and "deferred" in r.text
    r = c.post("/items/action", data={"source": "vendor_pdc", "key": key, "action": "reset", "mode": "pdc"},
               headers=hdr)
    assert "Back to as imported (1 change(s) revoked)" in r.text


def test_balance_entry_and_toggles(loaded):
    c = loaded
    r = c.post("/balances", data={"bank": "Bank E", "account": "EUR 1", "currency": "EUR", "as_of": "2026-11-24",
                                  "balance": "1000", "csrf_token": token(c)}, follow_redirects=True)
    assert "manual rate" in r.text
    r = c.post("/balances", data={"bank": "Bank E", "account": "EUR 1", "currency": "EUR", "as_of": "2026-11-24",
                                  "balance": "1000", "rate": "0.42", "csrf_token": token(c)}, follow_redirects=True)
    assert "Balance saved" in r.text
    base = c.get("/forecast?scenario=1").text
    risk = c.get("/forecast?risk=on", headers={"HX-Request": "true", "HX-Target": "grid-area"}).text
    assert "<html" not in risk and "risk excluded" in risk and "Risk-adjusted collections excluded" in base
    assert "Dec 2026 total" in c.get("/forecast?months=2").text


def test_admin_settings_categories_scenarios(loaded):
    c = loaded
    c.post("/logout", data={"csrf_token": token(c)})
    login(c, "admin1")
    page = c.get("/admin/settings").text
    r = c.post("/admin/settings", data={"horizon_months": "2", "csrf_token": csrf_of(page)}, follow_redirects=True)
    assert "Settings saved: horizon_months" in r.text
    assert "Jan 2027 total" not in c.get("/forecast?months=").text
    r = c.post("/admin/settings", data={"horizon_months": "40", "csrf_token": csrf_of(page)}, follow_redirects=True)
    assert "Not saved" in r.text
    r = c.post("/admin/categories", data={"name": "Insurance", "direction": "outflow", "group": "Overheads",
                                          "order": "95", "treatment": "fixed", "csrf_token": csrf_of(page)},
               follow_redirects=True)
    assert "Category &#39;Insurance&#39; saved" in r.text
    assert "Insurance" in c.get("/forecast").text                          # new row appears at once
    r = c.post("/scenarios", data={"name": "Stress", "exclude_risk": "1", "use_delay": "1",
                                   "csrf_token": csrf_of(page)}, follow_redirects=True)
    assert "Scenario &#39;Stress&#39; saved" in r.text and "Net funding position after holds" in r.text


# ---------------------------------------------------------------- users screen
def _temp_pw(html: str) -> str:
    return re.search(r'id="temp-pw">([^<]+)</code>', html).group(1)


def test_admin_creates_user_with_temporary_password(app_client):
    c = app_client
    login(c, "admin1")
    page = c.get("/admin/users").text
    assert "prep1" in page and "Add a user" in page and '<option value="approver"' not in page
    r = c.post("/admin/users", data={"username": "A.Rahman", "full_name": "A Rahman", "role": "preparer",
                                     "csrf_token": csrf_of(page)})
    assert r.status_code == 200 and "User 'a.rahman' created" in r.text
    temp = _temp_pw(r.text)
    assert temp not in c.get("/admin/users").text                         # shown once only
    with session_scope() as db:
        u = db.scalar(select(User).where(User.username == "a.rahman"))
        assert u.must_change_password and temp not in u.password_hash
        assert db.scalar(select(AuditLog).where(AuditLog.action == "user.create",
                                 AuditLog.entity_key == "a.rahman")).username == "admin1"
    r = c.post("/admin/users", data={"username": "a.rahman", "role": "viewer", "csrf_token": csrf_of(page)},
               follow_redirects=True)
    assert "already exists" in r.text
    c.post("/logout", data={"csrf_token": token(c)})
    assert login(c, "a.rahman", temp).headers["location"] == "/account/password"


def test_reset_password_ends_sessions_and_forces_change(app_client):
    from fastapi.testclient import TestClient as TC
    c = app_client
    other = TC(c.app, base_url="http://localhost")
    assert login(other, "prep1").status_code == 303 and other.get("/forecast").status_code == 200
    login(c, "admin1")
    page = c.get("/admin/users").text
    with session_scope() as db:
        pid = db.scalar(select(User).where(User.username == "prep1")).id
    r = c.post(f"/admin/users/{pid}/reset", data={"csrf_token": csrf_of(page)})
    assert "Password of 'prep1' reset" in r.text
    temp = _temp_pw(r.text)
    assert other.get("/forecast", follow_redirects=False).headers["location"].startswith("/login")
    assert login(other, "prep1").status_code == 401                        # old password no longer works
    assert login(other, "prep1", temp).headers["location"] == "/account/password"
    with session_scope() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "user.password_reset")) is not None


def test_last_admin_guard_unlock_and_deactivate(app_client):
    c = app_client
    login(c, "admin1")
    page = c.get("/admin/users").text
    tok = csrf_of(page)
    with session_scope() as db:
        ids = {u.username: u.id for u in db.scalars(select(User))}
    r = c.post(f"/admin/users/{ids['admin1']}", data={"full_name": "", "role": "viewer", "active": "1",
                                                      "csrf_token": tok}, follow_redirects=True)
    assert "last active Admin" in r.text
    for _ in range(5):
        login(TestClient(c.app, base_url="http://localhost"), "view1", "wrong-password-1")
    assert "Unlock" in c.get("/admin/users").text
    r = c.post(f"/admin/users/{ids['view1']}/unlock", data={"csrf_token": tok}, follow_redirects=True)
    assert "unlocked" in r.text
    r = c.post(f"/admin/users/{ids['view1']}", data={"full_name": "Viewer One", "role": "viewer",
                                                     "csrf_token": tok}, follow_redirects=True)
    assert "saved" in r.text and "inactive" in r.text
    v = TestClient(c.app, base_url="http://localhost")
    assert login(v, "view1").status_code == 401                            # deactivated users cannot sign in
    with session_scope() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "user.update")).after["active"] is False


def test_console_reset_of_forgotten_admin_password(app_client, capsys):
    from app.cli import main
    c = app_client
    for _ in range(5):
        login(c, "admin1", "forgotten-pass-1")                             # locked out
    main(["list-users"])
    assert "locked" in capsys.readouterr().out
    main(["reset-password", "ADMIN1"])
    out = capsys.readouterr().out
    temp = re.search(r"Temporary password:\s+(\S+)", out).group(1)
    assert login(c, "admin1", temp).headers["location"] == "/account/password"
    with pytest.raises(SystemExit):
        main(["reset-password", "nobody"])
    with session_scope() as db:
        a = db.scalar(select(AuditLog).where(AuditLog.action == "user.password_reset"))
        assert a.entity_key == "admin1" and a.after["via"] == "console"


def test_users_screen_is_admin_only(app_client):
    c = app_client
    login(c, "prep1")
    assert c.get("/admin/users").status_code == 403
    r = c.post("/admin/users", data={"username": "x.y", "role": "admin", "csrf_token": token(c)})
    assert r.status_code == 403
    assert "/admin/users" not in c.get("/forecast").text and "Change password" in c.get("/forecast").text


def test_template_download_and_snapshot(loaded):
    c = loaded
    r = c.get("/templates/vendor_pdcs.xlsx")
    assert r.status_code == 200 and r.content[:2] == b"PK"
    assert c.get("/templates/..%2Fapp%2Fmain.py").status_code == 404
    r = c.post("/snapshot", headers={"X-CSRF-Token": token(c), "HX-Request": "true"})
    assert "Snapshot saved" in r.text
