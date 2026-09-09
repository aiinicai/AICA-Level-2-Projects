"""
Stage 2 smoke test: confirm the skeleton actually boots and every
approved nav destination resolves. Originally written when every nav
route was a placeholder that never touched the database, so `_client()`
never needed a schema on its in-memory DB.

Stage 5 update (test-fixture-only, not an app/schema change): `/engagement/`
is now a real, DB-backed route (app/api/engagement_bp.py), so `_client()`
must build the schema on its `sqlite:///:memory:` DB before hitting nav
paths — exactly what a real deployment already has in place via Alembic
migration before the app ever serves a request. `create_app()` itself
deliberately does NOT run migrations (Stage 2 design — migrations are a
separate, explicit step, not implicit app-factory behaviour), so this is
the test's own responsibility, not something to add to app/__init__.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import TestConfig
from app import create_app


def _client():
    app = create_app(TestConfig)
    from app import extensions
    from app.models import Base

    Base.metadata.create_all(extensions.engine)
    return app.test_client()


def test_health_check():
    client = _client()
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["ai_enabled"] is False  # AI off by default — approved architecture


NAV_PATHS = [
    "/",
    "/engagement/",
    "/data/upload/",
    "/data/mapping/",
    "/data/quality/",
    "/review/accounting/",
    "/review/audit/",
    "/review/tax/",
    "/review/sebi/",
    "/exceptions/",
    "/queries/",
    "/reports/",
    "/settings/",
    "/faq/",
]


def test_all_nav_pages_load():
    client = _client()
    for path in NAV_PATHS:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} returned {resp.status_code}"


def test_internal_api_stubs():
    client = _client()
    assert client.get("/api/risk/ping").status_code == 200
    ai_resp = client.get("/api/ai/ping")
    assert ai_resp.status_code == 200
    assert ai_resp.get_json()["enabled"] is False
