import io
from datetime import date, timedelta

from openpyxl import Workbook, load_workbook

from app import gst, services as sv
from app.extensions import db
from app.models import Challan, Vendor
from app.uploads import CHALLAN_COLS, VENDOR_COLS
from test_stage1 import _form


def _xlsx(cols, rows):
    wb = Workbook(); ws = wb.active; ws.append([c for c, _ in cols])
    for r in rows:
        ws.append([r.get(f, "") for _, f in cols])
    b = io.BytesIO(); wb.save(b); b.seek(0); return b


def test_all_reports_and_dashboard_render(app, client):
    c = client("approver1", "Demo@1234")
    for name in ("monthly", "range", "gstr1", "pending_ewb", "returnables", "vendors"):
        assert c.get(f"/reports/{name}").status_code == 200, name
        r = c.get(f"/reports/{name}?export=xlsx")
        assert r.status_code == 200 and r.data[:2] == b"PK", name
        load_workbook(io.BytesIO(r.data))
    assert c.get("/reports/").status_code == 200
    assert c.get("/").status_code == 200 and b"Challans per month" in c.get("/").data
    assert c.get("/reports/returnables?only=overdue").status_code == 200


def test_gstr1_counts_cancelled(app, client):
    ap = client("approver1", "Demo@1234")
    ch = Challan.query.filter_by(ctype="MNRC", status="FINAL").first()
    ap.post(f"/challans/{ch.id}/cancel", {"reason": "entered by mistake"})
    r = ap.get("/reports/gstr1?from=2000-01-01&to=2099-12-31&export=xlsx")
    ws = load_workbook(io.BytesIO(r.data)).active
    rows = {row[0]: row for row in ws.iter_rows(min_row=5, values_only=True)}
    mnrc = next(v for k, v in rows.items() if k.startswith("MNRC"))
    assert mnrc[5] == 1 and mnrc[6] == mnrc[4] - 1 and ch.number in mnrc[7]


def test_vendor_upload_validates_then_commits(app, client):
    ad = client("admin")
    good = dict(name="Fresh Tools LLP", address="Nashik", state="Maharashtra", pin="422001", gstin=gst.make_gstin("27", "AAKFF1234F"))
    dup = dict(name="Whatever", address="x", state="27", pin="411001", gstin=Vendor.query.first().gstin)
    bad = dict(name="Bad One", address="x", state="Atlantis", pin="12", gstin="27AAKFF1234F1ZZ")
    before = Vendor.query.count()
    r = ad.post("/upload/vendors", {"file": (_xlsx(VENDOR_COLS, [good, dup, bad]), "v.xlsx")}, content_type="multipart/form-data")
    bid = int(r.headers["Location"].rsplit("/", 1)[1])
    page = ad.get(f"/upload/batch/{bid}").data
    assert b"GSTIN already in master" in page and b"not recognised" in page
    ad.post(f"/upload/batch/{bid}/commit")
    assert Vendor.query.count() == before                              # errors -> nothing committed
    r = ad.post("/upload/vendors", {"file": (_xlsx(VENDOR_COLS, [good]), "v.xlsx")}, content_type="multipart/form-data")
    bid = int(r.headers["Location"].rsplit("/", 1)[1])
    ad.post(f"/upload/batch/{bid}/commit")
    assert Vendor.query.count() == before + 1


def test_historical_challan_upload_keeps_numbers_and_series_continues(app, client):
    ad = client("admin")
    v = Vendor.query.filter_by(state_code="27").first()
    base = dict(ctype="MNRC", number="MNRC/24-25/0007", date="12-08-2024", plant="PNQ1", vendor=v.vendor_no, purpose="Other",
                reason="old", status="FINAL", ewb_no="", line_no=1, part_no="A", description="Item", hsn="8708", qty=2, uom="NOS", rate=100, tax_rate=18)
    rows = [base, {**base, "line_no": 2, "part_no": "B", "qty": 1}, {**base, "number": "MNRC/24-25/0007"}]
    bad = {**base, "number": "MNRC/24-25/0009", "hsn": "ab"}
    r = ad.post("/upload/challans", {"file": (_xlsx(CHALLAN_COLS, [base, {**base, "line_no": 2, "part_no": "B"}, bad]), "c.xlsx")}, content_type="multipart/form-data")
    bid = int(r.headers["Location"].rsplit("/", 1)[1])
    assert b"HSN" in ad.get(f"/upload/batch/{bid}").data
    ok = ad.post("/upload/challans", {"file": (_xlsx(CHALLAN_COLS, [base, {**base, "line_no": 2, "part_no": "B"}]), "c.xlsx")}, content_type="multipart/form-data")
    bid = int(ok.headers["Location"].rsplit("/", 1)[1])
    ad.post(f"/upload/batch/{bid}/commit")
    h = Challan.query.filter_by(number="MNRC/24-25/0007").one()
    assert len(h.lines) == 2 and h.is_historical and h.status == "FINAL" and h.fy == "2024-25"
    # duplicate upload is rejected
    dup = ad.post("/upload/challans", {"file": (_xlsx(CHALLAN_COLS, [base]), "c.xlsx")}, content_type="multipart/form-data")
    assert b"already exists" in ad.get(dup.headers["Location"]).data
    # new issue in FY 2024-25 would continue at 0008 - simulate by counter
    from app.models import Counter
    assert db.session.get(Counter, "MNRC|2024-25").last_no == 7
    assert sv.next_counter("MNRC|2024-25") == 8


def test_templates_download(app, client):
    c = client("admin")
    for k in ("vendors", "challans"):
        r = c.get(f"/upload/template/{k}")
        assert r.status_code == 200 and load_workbook(io.BytesIO(r.data))
