from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from app.web.application import create_app


def _setup_login(client: TestClient) -> str:
    client.get("/setup")
    csrf = client.cookies.get("ibc_csrf")
    response = client.post("/setup", data={
        "username": "owner",
        "display_name": "Owner",
        "password": "Correct horse battery staple 2026!",
        "password_confirm": "Correct horse battery staple 2026!",
        "csrf_token": csrf,
    }, follow_redirects=False)
    assert response.status_code == 303
    client.get("/login")
    csrf = client.cookies.get("ibc_csrf")
    response = client.post("/login", data={
        "username": "owner",
        "password": "Correct horse battery staple 2026!",
        "totp_code": "",
        "csrf_token": csrf,
    }, follow_redirects=False)
    assert response.status_code == 303
    return client.cookies.get("ibc_csrf")


def test_document_vault_ui_upload_search_download_and_duplicate(tmp_path: Path):
    app = create_app(data_root=tmp_path / "data")
    with TestClient(app) as client:
        csrf = _setup_login(client)

        create = client.post(
            "/api/v1/clients",
            json={"name": "Vault Client"},
            headers={"X-CSRF-Token": csrf},
        )
        client_id = create.json()["id"]

        page = client.get("/documents")
        assert page.status_code == 200
        assert "Encrypted local vault" in page.text

        payload = b"Confidential claim schedule creditor ALPHA amount INR 50000"
        response = client.post(
            "/documents/upload",
            data={
                "csrf_token": csrf,
                "client_id": str(client_id),
                "matter_id": "",
                "category": "Claim",
                "tags": "creditor, alpha",
                "force_ocr": "",
            },
            files={"file": ("alpha claim.txt", payload, "text/plain")},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"].startswith("/documents?notice=")

        listing = client.get(f"/api/v1/documents?q=ALPHA&client_id={client_id}")
        assert listing.status_code == 200
        item = listing.json()["items"][0]
        assert item["safe_filename"] == "alpha claim.txt"
        assert item["category"] == "Claim"
        document_id = item["id"]

        detail = client.get(f"/documents/{document_id}")
        assert detail.status_code == 200
        assert "Confidential claim schedule" in detail.text
        assert "alpha claim.txt" in detail.text

        download = client.get(f"/documents/{document_id}/download")
        assert download.status_code == 200
        assert download.content == payload
        assert "alpha%20claim.txt" in download.headers["content-disposition"]

        duplicate = client.post(
            "/api/v1/documents/upload",
            data={"client_id": str(client_id), "category": "Claim", "tags": "creditor"},
            files={"file": ("alpha claim.txt", payload, "text/plain")},
            headers={"X-CSRF-Token": csrf},
        )
        assert duplicate.status_code == 200
        assert duplicate.json() == {"id": document_id, "duplicate": True}

        changed = client.post(
            f"/api/v1/documents/{document_id}/metadata",
            json={"category": "Accepted Claim", "tags": ["accepted"], "review_status": "ACCEPTED"},
            headers={"X-CSRF-Token": csrf},
        )
        assert changed.status_code == 200
        updated = client.get(f"/api/v1/documents/{document_id}").json()
        assert updated["category"] == "Accepted Claim"
        assert updated["review_status"] == "ACCEPTED"
        assert updated["tags"] == ["accepted"]


def test_document_upload_rejects_fake_pdf_and_bad_csrf(tmp_path: Path):
    app = create_app(data_root=tmp_path / "data")
    with TestClient(app) as client:
        csrf = _setup_login(client)
        bad_csrf = client.post(
            "/api/v1/documents/upload",
            files={"file": ("note.txt", b"hello", "text/plain")},
            headers={"X-CSRF-Token": "wrong"},
        )
        assert bad_csrf.status_code == 403

        fake = client.post(
            "/api/v1/documents/upload",
            files={"file": ("fake.pdf", b"not a real pdf", "application/pdf")},
            headers={"X-CSRF-Token": csrf},
        )
        assert fake.status_code == 400
        assert "signature" in fake.json()["error"].lower()
