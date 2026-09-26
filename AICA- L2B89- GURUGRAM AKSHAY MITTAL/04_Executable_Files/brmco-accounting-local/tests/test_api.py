"""End-to-end workflow through the HTTP API in demo mode."""
from app.accounting.models import VoucherKind
from app.excel.samples import SAMPLE_ROWS
from tests.conftest import workbook

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def upload(client, path, content, name="file.xlsx"):
    return client.post(path, files={"file": (name, content, XLSX)})


def test_frontend_is_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "BRMCo Accounting Hub" in r.text


def test_template_download(client):
    r = client.get("/api/bank/payment/template")
    assert r.status_code == 200
    assert r.content[:2] == b"PK"


def test_full_sales_workflow_demo(client):
    assert client.post("/api/tally/masters/sync", json={}).json()["results"]["ledger"]["status"] == "ok"

    batch = upload(client, "/api/sales/upload", workbook(VoucherKind.SALES)).json()
    assert batch["errors"] == 0, batch["issues"]
    assert batch["voucher_count"] == 2 and batch["can_post"]
    assert batch["vouchers"][0]["total"] == "118000.00"

    xml = client.get(f"/api/batches/{batch['id']}/xml")
    assert xml.status_code == 200 and b"<VOUCHER" in xml.content

    result = client.post(f"/api/batches/{batch['id']}/post").json()
    assert result["status"] == "SUCCESS" and result["demo_mode"] is True
    assert result["created"] == 2
    assert result["message"].startswith("DEMO MODE")

    history = client.get("/api/history").json()["items"]
    assert history[0]["tally_status"] == "SUCCESS" and history[0]["demo_mode"] == 1
    detail = client.get(f"/api/history/{history[0]['id']}").json()
    assert len(detail["results"]) == 2

    actions = {a["action"] for a in client.get("/api/audit").json()["items"]}
    assert {"EXCEL_UPLOADED", "VALIDATION_PERFORMED", "XML_GENERATED", "XML_DOWNLOADED",
            "TALLY_POST_ATTEMPTED", "TALLY_POST_SUCCESS"} <= actions


def test_invalid_file_cannot_be_posted(client):
    client.post("/api/tally/masters/sync", json={})
    rows = [{**SAMPLE_ROWS[VoucherKind.JOURNAL][0], "debit": 100},
            {**SAMPLE_ROWS[VoucherKind.JOURNAL][1], "credit": 90}]
    batch = upload(client, "/api/journal/upload", workbook(VoucherKind.JOURNAL, rows)).json()
    assert batch["errors"] > 0 and batch["can_post"] is False
    r = client.post(f"/api/batches/{batch['id']}/post")
    assert r.status_code == 400
    assert "validation errors" in r.json()["detail"]
    assert client.get(f"/api/batches/{batch['id']}/xml").status_code == 400


def test_garbage_upload_is_a_friendly_error(client):
    batch = upload(client, "/api/purchase/upload", b"hello", "notes.xlsx").json()
    assert batch["errors"] == 1
    assert "could not be opened" in batch["issues"][0]["message"]


def test_settings_validation(client):
    r = client.put("/api/settings", json={"financial_year": "2026-28"})
    assert r.status_code == 400
    r = client.put("/api/settings", json={"tally_port": 9001})
    assert r.status_code == 200 and r.json()["settings"]["tally_port"] == 9001


def test_live_mode_tally_down(client):
    client.put("/api/settings", json={"demo_mode": False, "tally_port": 1, "require_master_sync": False})
    status = client.get("/api/tally/status").json()
    assert status["connected"] is False
    batch = upload(client, "/api/bank/receipt/upload", workbook(VoucherKind.RECEIPT)).json()
    assert batch["errors"] == 0, batch["issues"]
    result = client.post(f"/api/batches/{batch['id']}/post").json()
    assert result["status"] == "FAILED"
    assert [r["status"] for r in result["results"]] == ["FAILED", "NOT_ATTEMPTED"]


def test_server_unavailable_is_reported(client):
    client.put("/api/settings", json={"server_base_url": "http://127.0.0.1:1"})
    s = client.get("/api/server/status").json()
    assert s["reachable"] is False and s["message"]


def test_no_secrets_in_local_settings(client):
    keys = set(client.get("/api/settings").json()["settings"])
    assert not {k for k in keys if any(w in k for w in ("api_key", "mongodb", "secret", "password"))}
