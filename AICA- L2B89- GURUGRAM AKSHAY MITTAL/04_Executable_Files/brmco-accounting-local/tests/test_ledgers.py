"""Reviewed ledger creation in Tally."""
import xml.etree.ElementTree as ET

import pytest
from pydantic import ValidationError

from app.accounting.models import VoucherKind
from app.excel.samples import GSTIN_ABC, SAMPLE_ROWS
from app.tally import client as tally_client
from app.tally.master_xml import NewLedger, ledger_import_envelope
from tests.conftest import workbook

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture(autouse=True)
def reset_demo_ledgers():
    tally_client.DEMO_CREATED_LEDGERS.clear()
    yield
    tally_client.DEMO_CREATED_LEDGERS.clear()


def test_ledger_xml():
    xml = ledger_import_envelope([
        NewLedger(name="M&M Logicorp Private Limited", parent="Sundry Debtors", bill_wise=True, gstin=GSTIN_ABC),
        NewLedger(name="Output CGST", parent="Duties & Taxes", gst_duty_head="Central Tax"),
    ], company="Test Co")
    root = ET.fromstring(xml)
    assert root.findtext(".//REPORTNAME") == "All Masters"
    assert root.findtext(".//SVCURRENTCOMPANY") == "Test Co"
    party, tax = root.findall(".//LEDGER")
    assert party.get("NAME") == "M&M Logicorp Private Limited" and party.get("ACTION") == "Create"
    assert party.findtext("PARENT") == "Sundry Debtors"
    assert party.findtext("ISBILLWISEON") == "Yes"
    assert party.findtext("PARTYGSTIN") == GSTIN_ABC
    assert party.findtext("LEDSTATENAME") == "Maharashtra"          # derived from GSTIN
    assert party.findtext("GSTREGISTRATIONTYPE") == "Regular"
    assert tax.findtext("TAXTYPE") == "GST" and tax.findtext("GSTDUTYHEAD") == "Central Tax"


def test_ledger_validation():
    with pytest.raises(ValidationError):
        NewLedger(name="  ", parent="Sundry Debtors")
    with pytest.raises(ValidationError):
        NewLedger(name="X", parent="Sundry Debtors", gstin="27ABCDE1234F1Z9")   # bad checksum
    with pytest.raises(ValidationError):
        NewLedger(name="X", parent="Sundry Debtors", gstin=GSTIN_ABC, state="Gujarat")
    with pytest.raises(ValidationError):
        NewLedger(name="X", parent="Duties & Taxes", gst_duty_head="VAT")


def test_missing_ledgers_create_and_revalidate(client):
    client.post("/api/tally/masters/sync", json={})
    rows = [dict(r) for r in SAMPLE_ROWS[VoucherKind.SALES]]
    rows[0]["customer_ledger"] = "M&M Logicorp Private Limited"
    rows[0]["sales_ledger"] = "Sales - Freight"
    batch = client.post("/api/sales/upload", files={"file": ("s.xlsx", workbook(VoucherKind.SALES, rows), XLSX)}).json()
    assert batch["missing_ledgers"] == 2 and batch["can_post"] is False

    missing = client.get(f"/api/batches/{batch['id']}/missing-ledgers").json()["ledgers"]
    by_name = {m["name"]: m for m in missing}
    assert by_name["M&M Logicorp Private Limited"]["parent"] == "Sundry Debtors"
    assert by_name["M&M Logicorp Private Limited"]["gstin"] == rows[0]["customer_gstin"]
    assert by_name["M&M Logicorp Private Limited"]["bill_wise"] is True
    assert by_name["Sales - Freight"]["parent"] == "Sales Accounts"

    payload = [{k: m[k] for k in ("name", "parent", "bill_wise", "gst_duty_head", "gst_registration_type",
                                   "gstin", "state")} for m in missing]
    r = client.post("/api/tally/ledgers", json={"ledgers": payload}).json()
    assert r["status"] == "SUCCESS" and r["created"] == 2 and r["resynced"] is True

    again = client.post(f"/api/batches/{batch['id']}/revalidate").json()
    assert again["errors"] == 0, again["issues"]
    assert again["can_post"] is True

    actions = {a["action"] for a in client.get("/api/audit").json()["items"]}
    assert {"LEDGER_CREATE_ATTEMPTED", "LEDGER_CREATED"} <= actions


def test_create_rejects_existing_or_unknown_group(client):
    client.post("/api/tally/masters/sync", json={})
    r = client.post("/api/tally/ledgers", json={"ledgers": [{"name": "abc traders", "parent": "Sundry Debtors"}]})
    assert r.status_code == 400 and "already exists" in r.json()["detail"]
    r = client.post("/api/tally/ledgers", json={"ledgers": [{"name": "New Co", "parent": "No Such Group"}]})
    assert r.status_code == 400 and "does not exist" in r.json()["detail"]
    r = client.post("/api/tally/ledgers", json={"ledgers": [{"name": "", "parent": "Sundry Debtors"}]})
    assert r.status_code == 422 and "Line 1" in r.json()["detail"]


def test_tax_ledger_suggestion(client):
    client.post("/api/tally/masters/sync", json={})
    client.put("/api/settings", json={"output_cgst_ledger": "CGST Output 9%"})
    batch = client.post("/api/sales/upload", files={"file": ("s.xlsx", workbook(VoucherKind.SALES), XLSX)}).json()
    missing = client.get(f"/api/batches/{batch['id']}/missing-ledgers").json()["ledgers"]
    assert missing == [{**missing[0], "name": "CGST Output 9%", "parent": "Duties & Taxes",
                        "gst_duty_head": "Central Tax"}]
