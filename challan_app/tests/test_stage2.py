import threading
from datetime import date, timedelta

from app import gst, services as sv
from app.extensions import db
from app.models import Challan, User, Vendor, Plant
from test_stage1 import _form


def test_pages_render_and_print(app, client):
    c = client("approver1", "Demo@1234")
    for url in ("/", "/challans", "/challans/new/MRC", "/challans/new/MNRC", "/vendors", "/vendors/new"):
        assert c.get(url).status_code == 200, url
    ch = Challan.query.filter_by(status="FINAL").first()
    for url in (f"/challans/{ch.id}", f"/challans/{ch.id}/edit"):
        assert c.get(url).status_code in (200, 302), url
    r = c.get(f"/challans/{ch.id}/print")
    assert r.status_code == 200
    for t in (b"Original for Consignee", b"Duplicate for Transporter", b"Triplicate for Consignor", ch.number.encode()):
        assert t in r.data
    assert b"wm" not in r.data.split(b"</style>")[1]      # no watermark on a live challan


def test_edit_rules_and_cancel_watermark(app, client):
    ch = Challan.query.filter_by(status="FINAL", ctype="MNRC").first()
    req = client("requester1", "Demo@1234")
    assert req.get(f"/challans/{ch.id}/edit").status_code == 302        # finalised -> not editable by requester
    assert client("admin").get(f"/challans/{ch.id}/edit").status_code == 200
    assert req.post(f"/challans/{ch.id}/cancel", {"reason": "wrong party"}).status_code == 403
    ap = client("approver1", "Demo@1234")
    ap.post(f"/challans/{ch.id}/cancel", {"reason": ""})
    db.session.refresh(ch); assert ch.status == "FINAL"                  # reason mandatory
    ap.post(f"/challans/{ch.id}/cancel", {"reason": "Issued to wrong party"})
    db.session.refresh(ch)
    assert ch.status == "CANCELLED" and ch.number
    assert b"CANCELLED</div>" in ap.get(f"/challans/{ch.id}/print").data
    assert ap.post(f"/challans/{ch.id}/ewb", {}).status_code == 302


def test_concurrent_saves_get_unique_gapless_numbers(app):
    uid = User.query.filter_by(username="requester1").one().id
    vid = Vendor.query.filter_by(state_code="27").first().id
    base = Challan.query.filter_by(ctype="MNRC", status="FINAL").count()
    errors, N = [], 12

    def worker():
        try:
            with app.app_context():
                u = db.session.get(User, uid)
                v = db.session.get(Vendor, vid)
                class F(dict):
                    def getlist(self, k): return {"part_no": ["X"], "description": ["d"], "hsn": ["9031"], "qty": ["1"],
                        "uom": ["NOS"], "rate": ["10"], "tax_rate": ["18"], "cess_rate": ["0"]}.get(k, [])
                f = F(plant_id=str(Plant.query.first().id), challan_date=date.today().isoformat(), vendor_id=str(v.id),
                      purpose="Other", purpose_text="t", reason="r")
                h, ls, errs = sv.parse_challan_form(f, "MNRC", u)
                assert not errs, errs
                ch = Challan(ctype="MNRC", created_by=u.username)
                sv.apply_challan(ch, h, ls); db.session.add(ch); db.session.flush()
                sv.finalize(ch, u); db.session.commit()
                db.session.remove()
        except Exception as e:  # noqa
            errors.append(repr(e))

    ts = [threading.Thread(target=worker) for _ in range(N)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert not errors, errors
    seqs = sorted(c.seq_no for c in Challan.query.filter_by(ctype="MNRC", status="FINAL", fy=gst.fy_of(date.today())))
    assert seqs == list(range(1, base + N + 1))
