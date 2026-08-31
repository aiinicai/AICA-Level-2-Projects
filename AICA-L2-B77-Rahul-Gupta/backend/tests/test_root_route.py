"""The API root must signpost the web app rather than 404.

Opening :8000 in a browser expecting the UI used to return a bare
{"detail":"Not Found"}, which reads like a broken backend when the server is
running fine. The root route explains where the app actually is.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_returns_a_signpost_not_a_404():
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    # must point at the web app, not just say "ok"
    assert body["app_url"].startswith("http")
    assert body["api_docs"] == "/docs"


def test_health_endpoint_still_works():
    """Pre-existing probe — guards against a duplicate route shadowing it."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"], "the original health payload includes the app name"


def test_no_duplicate_route_paths_are_registered():
    """A second @app.get on an existing path silently shadows the first."""
    seen = [(r.path, tuple(sorted(r.methods))) for r in app.routes
            if hasattr(r, "methods") and r.methods]
    assert len(seen) == len(set(seen)), f"duplicate routes: {sorted(seen)}"


def test_root_is_hidden_from_the_openapi_schema():
    """Signposting is a convenience, not part of the documented API surface."""
    assert "/" not in client.get("/openapi.json").json()["paths"]
