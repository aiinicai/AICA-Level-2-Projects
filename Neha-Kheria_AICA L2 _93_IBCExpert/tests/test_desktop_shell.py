from pathlib import Path

import pytest

from app.desktop import reserve_loopback_socket


def test_dynamic_socket_is_loopback_and_os_assigned():
    sock = reserve_loopback_socket()
    try:
        host, port = sock.getsockname()
        assert host == "127.0.0.1"
        assert 0 < port <= 65535
    finally:
        sock.close()


fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from app.web.application import create_app


def _setup_and_login(client: TestClient):
    client.get("/setup")
    csrf = client.cookies.get("ibc_csrf")
    client.post("/setup", data={
        "username": "owner",
        "display_name": "Owner",
        "password": "Correct horse battery staple 2026!",
        "password_confirm": "Correct horse battery staple 2026!",
        "csrf_token": csrf,
    })
    client.get("/login")
    csrf = client.cookies.get("ibc_csrf")
    response = client.post("/login", data={
        "username": "owner",
        "password": "Correct horse battery staple 2026!",
        "totp_code": "",
        "csrf_token": csrf,
    }, follow_redirects=False)
    assert response.status_code == 303


def test_trial_and_security_pages_are_connected(tmp_path: Path):
    app = create_app(data_root=tmp_path / "data")
    with TestClient(app) as client:
        _setup_and_login(client)
        dashboard = client.get("/dashboard")
        assert dashboard.status_code == 200
        assert "TRIAL" in dashboard.text
        activation = client.get("/activation")
        assert activation.status_code == 200
        assert "Device / installation request code" in activation.text
        security = client.get("/security")
        assert security.status_code == 200
        assert "Two-step verification" in security.text
