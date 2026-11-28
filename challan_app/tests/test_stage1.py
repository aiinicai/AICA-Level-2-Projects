import re
from datetime import date, timedelta

from app import gst
from app.extensions import db
from app.models import Challan, Plant, Vendor


def test_gstin_rules():
    assert gst.validate_gstin("27AAPFU0939F1ZV") == []
    assert gst.validate_gstin("27AAPFU0939F1ZX")            # wrong check digit
    assert gst.validate_gstin("27AAPFU0939F1ZV", "29")      # state mismatch
    assert gst.validate_gstin("27AAPFU0939F1")              # too short
    assert gst.pan_from_gstin("27AAPFU0939F1ZV") == "AAPFU0939F"


def test_vendor_master_dupes_and_erp_block(app, client):
    c = client("requester1", "Demo@1234")
    g = gst.make_gstin("27", "AABCQ9999Q")
    data = {"name": "Brand New Calibrators Pvt Ltd", "address": "Pune", "state_code": "27", "pin": "411001", "gstin": g}
    assert c.post("/vendors/new", data).status_code == 302
    assert Vendor.query.filter_by(gstin=g).one().vendor_no.startswith("MV-")
    # same GSTIN -> blocked
    r = c.post("/vendors/new", {**data, "name": "Other name"})
    assert r.status_code == 200 and b"GSTIN already exists" in r.data
    # similar name, different GSTIN -> needs confirmation
    d2 = {**data, "gstin": gst.make_gstin("27", "AABCR8888R"), "name": "Brand New Calibrators Private Limited"}
    assert b"Similar vendor" in c.post("/vendors/new", d2).data
    assert c.post("/vendors/new", {**d2, "confirm_similar": "1"}).status_code == 302
    # state must match GSTIN
    r = c.post("/vendors/new", {**data, "gstin": gst.make_gstin("29", "AABCS7777S"), "state_code": "27", "name": "Zed"})
    assert b"do not match" in r.data


def _form(vendor, **kw):
    p = Plant.query.first()
    f = {"plant_id": p.id, "challan_date": date.today().isoformat(), "vendor_id": vendor.id, "purpose": "Calibration",
         "reason": "Vendor not in ERP", "corrective_action": "Create vendor", "corrective_owner": "Joshi",
         "corrective_target_date": (date.today() + timedelta(days=30)).isoformat(),
         "expected_return_date": (date.today() + timedelta(days=30)).isoformat(), "goods_category": "INPUTS",
         "part_no": ["P1"], "description": ["Gauge"], "hsn": ["9031"], "qty": ["2"], "uom": ["NOS"], "rate": ["1000"],
         "tax_rate": ["18"], "cess_rate": ["0"], "action": "final"}
    f.update(kw)
    return f


def test_mrc_blocked_for_erp_vendor_but_admin_and_mnrc_allowed(app, client):
    erp_v = Vendor.query.filter(Vendor.erp_code.isnot(None)).one()
    r = client("requester1", "Demo@1234").post("/challans/new/MRC", _form(erp_v))
    assert b"now set up in the ERP (Vendor Code: V10045)" in r.data
    assert b"Please generate the returnable challan from the ERP system." in r.data
    assert client("admin").post("/challans/new/MRC", _form(erp_v)).status_code == 302
    nr = _form(erp_v, purpose="Other", purpose_text="x")
    for k in ("corrective_action", "corrective_owner", "corrective_target_date", "expected_return_date"):
        nr.pop(k)
    assert client("requester1", "Demo@1234").post("/challans/new/MNRC", nr).status_code == 302


def test_mandatory_fields_and_tax_split(app, client):
    v = Vendor.query.filter_by(state_code="27").first()
    c = client("requester1", "Demo@1234")
    r = c.post("/challans/new/MRC", _form(v, reason="", corrective_action="", corrective_target_date=""))
    assert r.status_code == 200
    assert b"Reason is required" in r.data
    assert b"Corrective action is mandatory" not in r.data
    r = c.post("/challans/new/MRC", _form(v, hsn=["12"], qty=["0"]))
    assert b"HSN must be 4, 6 or 8 digits" in r.data and b"quantity must be greater than zero" in r.data
    # intra-state -> CGST+SGST ; inter-state (Karnataka vendor) -> IGST
    assert c.post("/challans/new/MRC", _form(v)).status_code == 302
    ch = Challan.query.order_by(Challan.id.desc()).first()
    assert (ch.cgst_total, ch.sgst_total, ch.igst_total) == (180, 180, 0) and not ch.interstate
    kv = Vendor.query.filter_by(state_code="24").first()
    assert c.post("/challans/new/MRC", _form(kv)).status_code == 302
    ch = Challan.query.order_by(Challan.id.desc()).first()
    assert ch.interstate and ch.igst_total == 360 and ch.grand_total == 2360


def test_draft_has_no_number_and_numbers_are_sequential(app, client):
    v = Vendor.query.filter_by(state_code="27").first()
    c = client("requester1", "Demo@1234")
    c.post("/challans/new/MRC", _form(v, action="draft"))
    d = Challan.query.order_by(Challan.id.desc()).first()
    assert d.status == "DRAFT" and d.number is None
    before = Challan.query.filter_by(ctype="MRC", status="FINAL").count()
    c.post(f"/challans/{d.id}/finalize")
    db.session.refresh(d)
    fy = gst.fy_short(gst.fy_of(date.today()))
    assert d.number == f"MRC/{fy}/{before + 1:04d}" and len(d.number) <= 16
