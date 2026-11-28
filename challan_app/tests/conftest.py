import os, sys, tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from app.extensions import db


@pytest.fixture()
def app(tmp_path):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "t.db").replace("\\", "/")})
    with app.app_context():
        from app.cli import bootstrap
        from app.sample_data import load_demo
        bootstrap()
        load_demo()
        from app.models import User
        User.query.filter_by(username='admin').first().must_change_password = False
        db.session.commit()
        yield app
        db.session.remove()
        db.engine.dispose()


class Client:
    def __init__(self, app):
        self.c = app.test_client()

    def login(self, user="admin", pw="admin123"):
        r = self.c.get("/login")
        self._csrf()
        r = self.c.post("/login", data={"username": user, "password": pw, "_csrf": self.tok})
        assert r.status_code == 302, r.data[:300]
        return self

    def _csrf(self):
        with self.c.session_transaction() as s:
            s.setdefault("_csrf", "testtoken")
            self.tok = s["_csrf"]

    def get(self, *a, **k):
        return self.c.get(*a, **k)

    def post(self, url, data=None, **k):
        self._csrf()
        data = dict(data or {})
        data["_csrf"] = self.tok
        return self.c.post(url, data=data, **k)


@pytest.fixture()
def client(app):
    return lambda user="admin", pw="admin123": Client(app).login(user, pw)

