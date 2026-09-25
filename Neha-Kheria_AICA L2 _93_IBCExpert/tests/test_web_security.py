from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from app.web.application import create_app


def test_first_run_setup_login_dashboard_and_csrf(tmp_path: Path):
    app = create_app(data_root=tmp_path / "data")
    with TestClient(app) as client:
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/setup"

        setup = client.get("/setup")
        assert setup.status_code == 200
        csrf = client.cookies.get("ibc_csrf")
        assert csrf
        response = client.post("/setup", data={
            "username": "owner",
            "display_name": "Owner",
            "password": "Correct horse battery staple 2026!",
            "password_confirm": "Correct horse battery staple 2026!",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert response.status_code == 303

        login = client.get("/login")
        csrf = client.cookies.get("ibc_csrf")
        response = client.post("/login", data={
            "username": "owner",
            "password": "Correct horse battery staple 2026!",
            "totp_code": "",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert response.status_code == 303
        assert client.cookies.get("ibc_session")

        dashboard = client.get("/dashboard")
        assert dashboard.status_code == 200
        assert "Active Clients" in dashboard.text
        assert dashboard.headers["x-frame-options"] == "DENY"
        assert "frame-ancestors 'none'" in dashboard.headers["content-security-policy"]

        bad = client.post("/api/v1/clients", json={"name": "Blocked"})
        assert bad.status_code == 403

        good = client.post(
            "/api/v1/clients",
            json={"name": "ABC Limited", "cin": "U12345MH2020PLC123456"},
            headers={"X-CSRF-Token": client.cookies.get("ibc_csrf")},
        )
        assert good.status_code == 201
        listing = client.get("/api/v1/clients")
        assert listing.status_code == 200
        assert listing.json()["items"][0]["name"] == "ABC Limited"


def test_security_cookie_properties_and_no_openapi(tmp_path: Path):
    app = create_app(data_root=tmp_path / "data")
    with TestClient(app) as client:
        assert client.get("/openapi.json").status_code == 404
        setup = client.get("/setup")
        set_cookie = setup.headers.get("set-cookie", "").lower()
        assert "samesite=strict" in set_cookie
