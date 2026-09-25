from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from app.web.application import create_app

PASSWORD = "Correct horse battery staple 2026!"


def logged_in(tmp_path: Path):
    app = create_app(data_root=tmp_path / "data")
    client = TestClient(app)
    client.__enter__()
    client.get("/setup")
    csrf = client.cookies.get("ibc_csrf")
    client.post("/setup", data={
        "username": "owner", "display_name": "Owner", "password": PASSWORD,
        "password_confirm": PASSWORD, "csrf_token": csrf,
    })
    client.get("/login")
    csrf = client.cookies.get("ibc_csrf")
    response = client.post("/login", data={
        "username": "owner", "password": PASSWORD, "totp_code": "", "csrf_token": csrf,
    }, follow_redirects=False)
    assert response.status_code == 303
    return app, client


def test_v1_status_client_detail_update_and_status(tmp_path: Path):
    app, client = logged_in(tmp_path)
    try:
        status = client.get("/api/v1/status")
        assert status.status_code == 200
        payload = status.json()
        assert payload["api_version"] == "v1"
        assert payload["offline_only"] is True
        assert payload["internet_updates_enabled"] is False
        assert payload["database"] == "local"

        csrf = client.cookies.get("ibc_csrf")
        created = client.post("/api/v1/clients", json={"name": "API Client"}, headers={"X-CSRF-Token": csrf})
        assert created.status_code == 201
        client_id = created.json()["id"]
        detail = client.get(f"/api/v1/clients/{client_id}")
        assert detail.status_code == 200
        row_version = detail.json()["row_version"]

        updated = client.put(
            f"/api/v1/clients/{client_id}",
            json={"name": "API Client Updated", "row_version": row_version},
            headers={"X-CSRF-Token": csrf},
        )
        assert updated.status_code == 200
        assert client.get(f"/api/v1/clients/{client_id}").json()["name"] == "API Client Updated"

        archived = client.post(f"/api/v1/clients/{client_id}/status/archive", headers={"X-CSRF-Token": csrf})
        assert archived.status_code == 200
        assert app.state.db.execute("SELECT status FROM clients WHERE id=?", (client_id,)).fetchone()[0] == "ARCHIVED"
    finally:
        client.__exit__(None, None, None)


def test_v1_major_read_contracts_are_authenticated_and_available(tmp_path: Path):
    _, client = logged_in(tmp_path)
    try:
        for path in (
            "/api/v1/dashboard",
            "/api/v1/licence",
            "/api/v1/legal/statutes",
            "/api/v1/legal/judgments",
            "/api/v1/workflow/instances",
            "/api/v1/forms",
            "/api/v1/backups",
            "/api/v1/plugins",
            "/api/v1/review-queue",
        ):
            response = client.get(path)
            assert response.status_code == 200, (path, response.text)
    finally:
        client.__exit__(None, None, None)


def test_v1_mutations_require_csrf(tmp_path: Path):
    _, client = logged_in(tmp_path)
    try:
        assert client.post("/api/v1/backups/create", json={}).status_code == 403
        assert client.post("/api/v1/recommendations/generate", json={"matter_id": 1}).status_code == 403
    finally:
        client.__exit__(None, None, None)
