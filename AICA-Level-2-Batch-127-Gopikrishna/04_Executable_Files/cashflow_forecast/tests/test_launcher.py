"""Windowless start: first-Admin setup in the browser, demo sign-in hint, launcher start/stop."""
import json
import re
import socket

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import session_scope
from app.models import AuditLog, User
from tests.test_phase6_web import PW, csrf_of

LOCAL = ("127.0.0.1", 50000)
REMOTE = ("10.1.2.3", 50000)


def _client(addr):
    from app.main import create_app
    return TestClient(create_app(), base_url="http://localhost", client=addr)


def test_login_redirects_to_setup_and_first_admin_is_created_locally():
    with _client(LOCAL) as c:
        r = c.get("/login", follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/setup"
        page = c.get("/setup").text
        assert "Create Admin and sign in" in page
        bad = c.post("/setup", data={"username": "boss", "password": PW, "confirm": PW + "x",
                                     "csrf_token": csrf_of(page)})
        assert bad.status_code == 400 and "do not match" in bad.text
        r = c.post("/setup", data={"username": "boss", "full_name": "The Boss", "password": PW, "confirm": PW,
                                   "csrf_token": csrf_of(bad.text)}, follow_redirects=True)
        assert r.status_code == 200 and "Welcome" in r.text
        with session_scope() as db:
            u = db.scalar(select(User))
            assert (u.username, u.role, u.must_change_password) == ("boss", "admin", False)
            assert db.scalar(select(AuditLog).where(AuditLog.action == "setup.first_admin"))
        # once a user exists, setup is closed
        assert c.get("/setup", follow_redirects=False).headers["location"] == "/login"
        r = c.post("/setup", data={"username": "x2", "password": PW, "confirm": PW,
                                   "csrf_token": csrf_of(page)}, follow_redirects=False)
        with session_scope() as db:
            assert db.scalar(select(User).where(User.username == "x2")) is None


def test_setup_refused_from_another_pc():
    with _client(REMOTE) as c:
        page = c.get("/setup").text
        assert "only be created on the PC" in page and "Create Admin" not in page
        tok = re.search(r'"X-CSRF-Token": "([^"]+)"', page).group(1)          # valid token: refused for being remote
        r = c.post("/setup", data={"username": "evil", "password": PW, "confirm": PW, "csrf_token": tok})
        assert r.status_code == 403
        with session_scope() as db:
            assert db.scalar(select(User)) is None


def test_demo_hint_only_on_this_pc(isolated_instance):
    from app.services.auth import create_user
    with _client(LOCAL) as c:
        with session_scope() as db:
            create_user(db, "demo.prep", PW, "preparer")
        assert "Demo sign-in details" not in c.get("/login").text           # no demo file: no hint
        (isolated_instance / "demo_users.txt").write_text("demo.prep  preparer  Synthetic-pw-1", encoding="utf-8")
        assert "Synthetic-pw-1" in c.get("/login").text
    with _client(REMOTE) as r:
        assert "Synthetic-pw-1" not in r.get("/login").text


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_launcher_starts_hidden_and_stops(isolated_instance, monkeypatch):
    from app import launcher
    from app.core import config
    monkeypatch.setenv("CFF_HOST", "127.0.0.1")
    monkeypatch.setenv("CFF_PORT", str(_free_port()))
    config.get_settings.cache_clear()
    url = launcher.start(demo=False, open_browser=False, wait_seconds=60)
    try:
        assert launcher.responding(url)
        info = json.loads((isolated_instance / "app.pid").read_text())
        assert info["url"] == url and launcher._pid_alive(info["pid"])
        assert launcher.start(demo=False, open_browser=False) == url          # second start: reuses it
        assert (isolated_instance / "logs" / "app.log").exists()
    finally:
        assert launcher.stop(demo=False)
    assert not (isolated_instance / "app.pid").exists()
    assert not launcher.responding(url, timeout=1)
    assert launcher.stop(demo=False) is False
