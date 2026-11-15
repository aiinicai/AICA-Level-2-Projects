"""Phase 4/5: the local server answers what the screens ask, refuses outsiders, and wipes data on close."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.server import AppState, create_app
from app.assistant.service import Assistant

DATA = Path(__file__).parent / "data"
H = {"X-Requested-With": "mis"}


@pytest.fixture()
def client():
    closed = []
    state = AppState(assistant=Assistant(persist=False))
    state.on_close = lambda: (state.store.wipe(), closed.append(1))
    app = create_app(state, Path(__file__).parent.parent / "app" / "static")
    with TestClient(app) as c:
        c.state, c.closed = state, closed
        yield c
    state.store.wipe()


def upload(c, name, **params):
    q = {"filename": name, **params}
    return c.post("/api/import/xml", params=q, content=(DATA / name).read_bytes(), headers={**H, "Content-Type": "application/xml"})


def test_shell_endpoints(client):
    assert client.get("/api/health").json() == {"ok": True}
    assert client.get("/api/auth/state").json()["user"]["role"] == "admin"
    assert client.get("/api/companies").json() == []
    assert "<div id=\"root\">" in client.get("/").text  # the screens are served


def test_writes_need_the_app_header(client):
    assert client.post("/api/demo/load").status_code == 403
    assert client.post("/api/demo/load", headers=H).status_code == 200


def test_other_host_names_are_refused():
    state = AppState(assistant=Assistant(persist=False))
    state.allowed_hosts = {"127.0.0.1:1"}
    with TestClient(create_app(state), base_url="http://evil.example") as c:
        assert c.get("/api/health").status_code == 403
    state.store.wipe()


def test_import_then_reports(client):
    r = upload(client, "masters.xml", newCompany="Test Co")
    assert r.status_code == 200 and r.json()["status"] == "succeeded"
    cid = r.json()["companyId"]
    assert upload(client, "daybook-2024-04.xml", companyId=cid).json()["status"] == "succeeded"
    meta = client.get(f"/api/companies/{cid}/meta").json()
    assert meta["dataFrom"] == "2024-04-01" and meta["financialYears"][0]["label"] == "FY 2024-25" and "Mumbai Branch" in meta["costCentres"]
    d = client.get(f"/api/c/{cid}/dashboard", params={"from": "2024-04-01", "to": "2024-04-30", "compare": "none"}).json()
    assert len(d["kpis"]) >= 16 and d["kpis"][0]["code"] == "revenue"
    assert client.get(f"/api/c/{cid}/pnl").status_code == 200
    assert client.get(f"/api/c/{cid}/ageing", params={"kind": "payable"}).json()["kind"] == "payable"
    assert client.get(f"/api/c/{cid}/ledgers/5", params={"from": "2024-04-01", "to": "2024-04-30"}).json()["ledger"]["id"] == 5
    assert client.get(f"/api/c/{cid}/vouchers/1").json()["id"] == 1
    assert client.get(f"/api/c/{cid}/products").json()["available"] is True
    bs = client.get(f"/api/c/{cid}/bs", params={"from": "2024-04-01", "to": "2024-04-30"}).json()
    assert abs(bs["current"]["totals"]["difference"]) < 1 and bs["comparisonLabel"] == "Comparison period end"
    assert "trend" in client.get(f"/api/c/{cid}/bs/analysis").json() and "byCategory" in client.get(f"/api/c/{cid}/cashflow").json()
    assert client.get(f"/api/c/{cid}/vouchers/99999").status_code == 404
    assert client.get(f"/api/c/{cid}/pnl", params={"from": "2025-01-01", "to": "2024-01-01"}).status_code == 400
    assert client.get("/api/c/77/pnl").status_code == 404


def test_demo_company_is_labelled_and_protected(client):
    cid = client.post("/api/demo/load", headers=H).json()["companyId"]
    c = client.get("/api/companies").json()[0]
    assert c["is_demo"] is True and c["voucher_count"] > 3000
    r = client.post("/api/import/xml", params={"companyId": cid}, content=b"<a/>", headers={**H, "Content-Type": "application/xml"})
    assert r.status_code == 400


def test_broken_upload_is_reported_not_fatal(client):
    r = client.post("/api/import/xml", params={"newCompany": "X"}, content=b"<ENVELOPE><VOUCHER>", headers={**H, "Content-Type": "application/xml"})
    assert r.status_code == 200 and r.json()["status"] == "failed" and "Malformed" in r.json()["error"]


def test_sync_rejects_bad_requests(client):
    def go(body):
        return client.post("/api/tally/sync", json=body, headers=H)
    assert go({"company": "X", "port": 9005, "months": []}).status_code == 400
    assert go({"company": "X", "port": 80, "months": ["2025-04-01"]}).status_code == 400
    assert go({"company": "X", "port": 9005, "months": ["abc"]}).status_code == 400


def test_close_wipes_everything(client):
    client.post("/api/demo/load", headers=H)
    assert client.state.store.scalar("SELECT COUNT(*) FROM vouchers") > 0
    assert client.post("/api/close", headers=H).json() == {"ok": True}
    assert client.state.store.closed and client.closed == [1]


def test_assistant_endpoints_offline(client):
    s = client.get("/api/settings/assistant").json()
    assert s["allowGeneral"] is False and s["model"] == "google/gemma-4-e2b"
    assert client.put("/api/settings/assistant", json={"allowGeneral": True}, headers=H).json()["allowGeneral"] is True
    assert client.put("/api/settings/assistant", json={"baseUrl": "http://example.com/v1"}, headers=H).status_code == 400
    # no company open: asked to open one first
    r = client.post("/api/assistant/chat", json={"question": "revenue?"}, headers=H).json()
    assert r["kind"] == "refused" and "Open a company" in r["answer"]
