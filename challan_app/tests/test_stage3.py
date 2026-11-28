from datetime import date, timedelta
from app.extensions import db
from app.models import Challan, Vendor


def _mrc(status="FINAL"):
    return Challan.query.filter_by(ctype="MRC", status=status).order_by(Challan.id.desc()).first()


def test_ewb_validation_and_status(app, client):
    ch = Challan.query.filter_by(status="FINAL", ewb_status="Pending").first()
    c = client("requester1", "Demo@1234")
    t = date.today().isoformat()
    c.post(f"/challans/{ch.id}/ewb", {"ewb_no": "123", "ewb_date": t, "ewb_valid_upto": t})
    db.session.refresh(ch); assert ch.ewb_status == "Pending"
    c.post(f"/challans/{ch.id}/ewb", {"ewb_no": "341234567891", "ewb_date": t, "ewb_valid_upto": (date.today() + timedelta(days=1)).isoformat()})
    db.session.refresh(ch); assert ch.ewb_status == "Updated" and ch.ewb_no == "341234567891"


def test_partial_then_full_receipt(app, client):
    ch = Challan.query.filter_by(ctype="MRC", return_status="Partially Received").one()
    assert ch.return_status == "Partially Received"
    c = client("requester1", "Demo@1234")
    t = date.today().isoformat()
    r = c.post(f"/challans/{ch.id}/receipt", {"received_date": t, "doc_ref": "GRN/1", f"qty_{ch.lines[0].id}": "9999"})
    db.session.refresh(ch); assert ch.return_status == "Partially Received"        # over-receipt refused
    data = {"received_date": t, "doc_ref": "GRN/2"}
    for l in ch.lines:
        data[f"qty_{l.id}"] = str(l.qty - l.qty_received)
    c.post(f"/challans/{ch.id}/receipt", data)
    db.session.refresh(ch); assert ch.return_status == "Closed"
    # cannot cancel once goods were received
    ap = client("approver1", "Demo@1234")
    ap.post(f"/challans/{ch.id}/cancel", {"reason": "mistake entry"})
    db.session.refresh(ch); assert ch.status == "FINAL"


def test_corrective_state_and_overdue(app):
    states = {c.number: c.corrective_state() for c in Challan.query.filter_by(ctype="MRC")}
    assert "Overdue" in states.values() and "Open" in states.values()
