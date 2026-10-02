import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import demo_data  # noqa: E402
from engine import generate, load  # noqa: E402


@pytest.fixture(scope="session")
def rp():
    return load()


# ------------------------------------------------------------------ web app
AS_OF = date(2026, 9, 25)
PASSWORD = "Demo-Pass-2026!"
TEST_ENV = {"SECRET_KEY": "test-secret-key-not-for-production",
            "FERNET_KEY": "0Ynk3Ov8uT8C4H4zYw5y1vQ3yJ9o1r3ZsOJv1gq3mXE="}


@pytest.fixture(scope="session")
def template_db(tmp_path_factory):
    """Migrate + seed once; each test gets a copy (fast, isolated)."""
    import os
    import cli
    os.environ.update(TEST_ENV)
    path = tmp_path_factory.mktemp("tpl") / "template.db"
    url = "sqlite:///" + path.as_posix()
    cli.migrate(url)
    from app import create_app
    app = create_app(DATABASE_URL=url, AS_OF=AS_OF, SESSION_COOKIE_SECURE=False, TESTING=True)
    cli.seed_demo(PASSWORD, AS_OF, quiet=True, app=app)
    from app.models import User, db
    with app.app_context():
        for u in db.session.query(User).all():
            u.must_change_password = False
        db.session.commit()
        db.session.remove()
    db.engine.dispose()
    return path


@pytest.fixture()
def app(template_db, tmp_path, monkeypatch):
    import shutil
    for k, v in TEST_ENV.items():
        monkeypatch.setenv(k, v)
    db_file = tmp_path / "test.db"
    shutil.copy(template_db, db_file)
    from app import create_app
    from app.auth import _rate
    _rate.clear()
    a = create_app(DATABASE_URL="sqlite:///" + db_file.as_posix(), AS_OF=AS_OF, SESSION_COOKIE_SECURE=False,
                   TESTING=True, WTF_CSRF_ENABLED=False, UPLOAD_DIR=tmp_path / "uploads")
    a.config["DB_FILE"] = db_file
    yield a
    from app.models import db
    db.session.remove()
    db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, username, password=PASSWORD):
    return client.post("/login", data={"username": username, "password": password})


@pytest.fixture()
def as_role(app):
    """as_role('article1') -> logged-in test client."""
    def _c(username):
        c = app.test_client()
        r = login(c, username)
        assert r.status_code == 302, r.data[:500]
        return c
    return _c


@pytest.fixture()
def q(app):
    """Run a query inside the app context: q(lambda s, M: ...)."""
    def _q(fn):
        from app import models
        with app.app_context():
            return fn(models.db.session, models)
    return _q


@pytest.fixture()
def demo():
    return demo_data.entities()


@pytest.fixture()
def gen(rp, demo):
    """gen('alpha', as_of, **overrides) -> {(rule_code, period_key[, event_id]): Spec}"""
    def _gen(name, as_of=date(2026, 9, 25), *, facts=None, events=None, persons=None, flags=None,
             decisions=None, settings=None, entity=None):
        d = demo[name]
        specs = generate(entity or d["entity"], d["facts"] if facts is None else facts,
                         d["events"] if events is None else events,
                         d["persons"] if persons is None else persons, rp, as_of,
                         period_flags=d["flags"] if flags is None else flags,
                         decisions=decisions, settings=settings)
        out = {}
        for s in specs:
            k = (s.rule_code, s.period_key) if s.event_id is None else (s.rule_code, s.period_key, s.event_id)
            if s.person_din:
                k = (s.rule_code, s.period_key, s.person_din)
            out[k] = s
        return out
    return _gen
