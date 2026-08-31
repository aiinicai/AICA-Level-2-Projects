"""Phase 0 exit test — the app boots and the health endpoint answers (§16)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["clauses_loaded"] == 6
    assert body["template_version"] == "0.1.0-phase1"


def test_startup_self_check_surfaces_needs_review() -> None:
    """The needs_review list is a deliverable (§20), not an internal detail."""
    with TestClient(app) as client:
        body = client.get("/health").json()
    assert body["needs_review"]
    assert "caro.viii" in body["needs_review"]


def test_pdf_degrades_gracefully_when_soffice_absent() -> None:
    """§1 — PDF is optional; absence must not break startup."""
    with TestClient(app) as client:
        body = client.get("/health").json()
    assert body["pdf_enabled"] is False
