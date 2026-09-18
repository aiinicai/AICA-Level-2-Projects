"""End-to-end API tests: auth, RBAC, document upload, and the full
maker-checker approval flow, exercised through FastAPI's TestClient against
a real (temporary, file-based) SQLite database -- not mocks.

The test database is set up BEFORE importing any ``webapi`` module, since
``webapi.database`` binds its SQLAlchemy engine to ``DATABASE_URL`` at
import time. Each test gets a clean slate via the ``client`` fixture, which
drops and recreates every table.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_TEST_DB_PATH = Path(tempfile.gettempdir()) / "cadocuflow_webapi_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ["DOCUFLOW_ADMIN_USERNAME"] = "admin"
os.environ["DOCUFLOW_ADMIN_PASSWORD"] = "AdminPass123!"
os.environ["DOCUFLOW_STORAGE_DIR"] = str(Path(tempfile.gettempdir()) / "cadocuflow_webapi_test_storage")

from fastapi.testclient import TestClient  # noqa: E402

from webapi.app import app  # noqa: E402
from webapi.database import Base, engine  # noqa: E402


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def _login(client, username, password) -> str:
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_user(client, admin_token, username, role, password="Password123!"):
    resp = client.post(
        "/users",
        json={"username": username, "email": f"{username}@example.com", "full_name": username, "password": password, "role": role},
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ------------------------------------------------------------------ auth/RBAC

def test_admin_bootstrap_and_login(client):
    token = _login(client, "admin", "AdminPass123!")
    assert token

    resp = client.get("/users/me", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["role"] == "Administrator"


def test_login_with_wrong_password_fails(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_unauthenticated_request_rejected(client):
    resp = client.get("/documents")
    assert resp.status_code == 401


def test_non_admin_cannot_create_users(client):
    admin_token = _login(client, "admin", "AdminPass123!")
    _create_user(client, admin_token, "maker1", "Maker")
    maker_token = _login(client, "maker1", "Password123!")

    resp = client.post(
        "/users",
        json={"username": "sneaky", "email": "sneaky@example.com", "full_name": "x", "password": "Password123!", "role": "Administrator"},
        headers=_auth_headers(maker_token),
    )
    assert resp.status_code == 403


def test_deactivated_user_token_immediately_rejected(client):
    admin_token = _login(client, "admin", "AdminPass123!")
    user = _create_user(client, admin_token, "temp_user", "Maker")
    user_token = _login(client, "temp_user", "Password123!")

    # Token works before deactivation.
    assert client.get("/users/me", headers=_auth_headers(user_token)).status_code == 200

    client.patch(f"/users/{user['id']}/deactivate", headers=_auth_headers(admin_token))

    # Same token, now rejected -- deactivation takes effect immediately, not
    # only after the token would naturally expire.
    resp = client.get("/users/me", headers=_auth_headers(user_token))
    assert resp.status_code == 401


# -------------------------------------------------------------- documents

def test_create_document_with_file(client):
    admin_token = _login(client, "admin", "AdminPass123!")
    resp = client.post(
        "/documents?title=Engagement Letter&client_name=Test Client",
        files={"file": ("agreement.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["title"] == "Engagement Letter"
    assert data["status"] == "Draft"
    assert len(data["versions"]) == 1
    assert data["versions"][0]["filename"] == "agreement.pdf"


def test_new_version_resets_prepared_document_to_draft(client):
    admin_token = _login(client, "admin", "AdminPass123!")
    _create_user(client, admin_token, "maker1", "Maker")
    maker_token = _login(client, "maker1", "Password123!")

    doc = client.post(
        "/documents?title=Doc",
        files={"file": ("v1.pdf", b"v1", "application/pdf")},
        headers=_auth_headers(maker_token),
    ).json()

    client.post(f"/documents/{doc['id']}/actions", json={"action": "submit_for_review"}, headers=_auth_headers(maker_token))

    resp = client.post(
        f"/documents/{doc['id']}/versions",
        files={"file": ("v2.pdf", b"v2 -- changed content", "application/pdf")},
        headers=_auth_headers(maker_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Draft"  # content change invalidated the in-progress review
    assert len(resp.json()["versions"]) == 2


# ---------------------------------------------------- maker-checker end to end

def test_full_maker_checker_flow_with_role_and_separation_enforcement(client):
    admin_token = _login(client, "admin", "AdminPass123!")
    _create_user(client, admin_token, "maker1", "Maker")
    _create_user(client, admin_token, "checker1", "Checker")
    _create_user(client, admin_token, "signer1", "Signatory")
    _create_user(client, admin_token, "auditor1", "Auditor")
    _create_user(client, admin_token, "approver1", "Approver")

    maker_token = _login(client, "maker1", "Password123!")
    checker_token = _login(client, "checker1", "Password123!")
    signer_token = _login(client, "signer1", "Password123!")
    auditor_token = _login(client, "auditor1", "Password123!")
    approver_token = _login(client, "approver1", "Password123!")

    doc = client.post(
        "/documents?title=GST Reply",
        files={"file": ("reply.pdf", b"content", "application/pdf")},
        headers=_auth_headers(maker_token),
    ).json()
    doc_id = doc["id"]

    def act(token, action, expect_status=200):
        resp = client.post(f"/documents/{doc_id}/actions", json={"action": action}, headers=_auth_headers(token))
        assert resp.status_code == expect_status, resp.text
        return resp

    act(maker_token, "submit_for_review")
    act(maker_token, "send_to_checker")

    # The maker cannot approve their own submission.
    act(maker_token, "approve", expect_status=409)

    act(checker_token, "approve")
    act(signer_token, "start_signing")
    act(signer_token, "confirm_signed")
    act(auditor_token, "verify")
    resp = act(approver_token, "release")
    assert resp.json()["status"] == "Released"

    act_history = client.get(f"/documents/{doc_id}/actions", headers=_auth_headers(admin_token)).json()
    actions_performed = [a["action"] for a in act_history]
    assert actions_performed == ["submit_for_review", "send_to_checker", "approve", "start_signing", "confirm_signed", "verify", "release"]


def test_wrong_role_cannot_approve(client):
    admin_token = _login(client, "admin", "AdminPass123!")
    _create_user(client, admin_token, "maker1", "Maker")
    maker_token = _login(client, "maker1", "Password123!")

    doc = client.post(
        "/documents?title=Doc",
        files={"file": ("v1.pdf", b"v1", "application/pdf")},
        headers=_auth_headers(maker_token),
    ).json()
    client.post(f"/documents/{doc['id']}/actions", json={"action": "submit_for_review"}, headers=_auth_headers(maker_token))
    client.post(f"/documents/{doc['id']}/actions", json={"action": "send_to_checker"}, headers=_auth_headers(maker_token))

    # Maker (not Checker/Approver/Admin) cannot approve.
    resp = client.post(f"/documents/{doc['id']}/actions", json={"action": "approve"}, headers=_auth_headers(maker_token))
    assert resp.status_code == 409


def test_invalid_action_for_current_state_rejected(client):
    admin_token = _login(client, "admin", "AdminPass123!")
    doc = client.post(
        "/documents?title=Doc",
        files={"file": ("v1.pdf", b"v1", "application/pdf")},
        headers=_auth_headers(admin_token),
    ).json()

    # Cannot "approve" a document still in Draft.
    resp = client.post(f"/documents/{doc['id']}/actions", json={"action": "approve"}, headers=_auth_headers(admin_token))
    assert resp.status_code == 409


def test_documents_are_isolated_per_actor_but_visible_to_all_authenticated(client):
    admin_token = _login(client, "admin", "AdminPass123!")
    _create_user(client, admin_token, "maker1", "Maker")
    _create_user(client, admin_token, "auditor1", "Auditor")
    maker_token = _login(client, "maker1", "Password123!")
    auditor_token = _login(client, "auditor1", "Password123!")

    client.post("/documents?title=Doc A", files={"file": ("a.pdf", b"a", "application/pdf")}, headers=_auth_headers(maker_token))

    resp = client.get("/documents", headers=_auth_headers(auditor_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "Doc A"


def test_reject_action_available_and_recorded(client):
    admin_token = _login(client, "admin", "AdminPass123!")
    _create_user(client, admin_token, "maker1", "Maker")
    _create_user(client, admin_token, "checker1", "Checker")
    maker_token = _login(client, "maker1", "Password123!")
    checker_token = _login(client, "checker1", "Password123!")

    doc = client.post(
        "/documents?title=Doc", files={"file": ("v1.pdf", b"v1", "application/pdf")}, headers=_auth_headers(maker_token)
    ).json()
    client.post(f"/documents/{doc['id']}/actions", json={"action": "submit_for_review"}, headers=_auth_headers(maker_token))
    client.post(f"/documents/{doc['id']}/actions", json={"action": "send_to_checker"}, headers=_auth_headers(maker_token))

    resp = client.post(
        f"/documents/{doc['id']}/actions", json={"action": "reject", "comment": "Missing signature page"},
        headers=_auth_headers(checker_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Rejected"

    actions = client.get(f"/documents/{doc['id']}/actions", headers=_auth_headers(admin_token)).json()
    assert actions[-1]["comment"] == "Missing signature page"
