import os
import re
import tempfile
from datetime import date

import pytest

def _make_png():
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (120, 60), (20, 60, 120)).save(buf, "PNG")
    return buf.getvalue()


PNG_1X1 = _make_png()


class Web:
    """Thin wrapper over Flask's test client that handles the CSRF token like a browser would."""

    def __init__(self, app):
        self.app = app
        self.c = app.test_client()

    def token(self):
        with self.c.session_transaction() as s:
            tok = s.get("_csrf")
        if not tok:
            self.c.get("/login", follow_redirects=True)  # renders a page, which issues the token
            with self.c.session_transaction() as s:
                tok = s.get("_csrf")
        return tok

    def get(self, url, **kw):
        return self.c.get(url, **kw)

    def post(self, url, data=None, **kw):
        data = dict(data or {})
        data.setdefault("_csrf", self.token())
        return self.c.post(url, data=data, **kw)

    def login(self, email, password="Passw0rd!x"):
        self.get("/login")
        return self.post("/login", {"email": email, "password": password})

    def logout(self):
        return self.post("/logout")


@pytest.fixture()
def app(monkeypatch):
    tmp = tempfile.mkdtemp()
    monkeypatch.setenv("AUDIT_MANAGER_DATA", tmp)
    from audit_manager import create_app, _failed_logins

    _failed_logins.clear()
    application = create_app({"TESTING": True})
    yield application


@pytest.fixture()
def world(app):
    """A firm with one of each role, plus clients. Returns ids/emails; sign in with Web.login()."""
    from audit_manager.models import Client, FirmSetting, User, db

    with app.app_context():
        FirmSetting.put("firm_name", "Sharma & Associates")
        FirmSetting.put("invoice_prefix", "SA")
        users = {}
        for key, role in [("admin", "super_admin"), ("partner", "partner"), ("manager", "manager"), ("emp1", "employee"), ("emp2", "employee")]:
            u = User(name=key.title(), email=f"{key}@firm.in", role=role)
            u.set_password("Passw0rd!x")
            db.session.add(u)
            users[key] = u
        db.session.flush()
        a = Client(client_code="CL-0001", name="Apex Precision", pan="AABCA1234F", gstin="03AABCA1234F1Z5", mobile="9876543210",
                   email="apex@example.in", is_gst_registered=True, is_itr_applicable=True, is_tds_applicable=True,
                   assigned_to_id=users["emp1"].id)
        b = Client(client_code="CL-0002", name="Beta Traders", pan="BBBCB2345G", is_gst_registered=True, is_itr_applicable=True,
                   assigned_to_id=users["emp2"].id)
        c = Client(client_code="CL-0003", name="Charlie Individual", pan="CCCPC3456H", category="individual", is_itr_applicable=True)
        db.session.add_all([a, b, c])
        db.session.commit()
        return {"app": app, "ids": {"apex": a.id, "beta": b.id, "charlie": c.id, **{k: u.id for k, u in users.items()}}}


@pytest.fixture()
def web(app):
    return Web(app)


def admin_web(world):
    w = Web(world["app"])
    w.login("admin@firm.in")
    return w
