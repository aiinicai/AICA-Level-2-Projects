import io
import re
import sqlite3
from datetime import date

from openpyxl import Workbook, load_workbook
from pypdf import PdfReader

from conftest import PNG_1X1, Web, admin_web
from audit_manager.models import Client, FirmSetting, GstReturn, GstReturnType, Invoice, ItrFiling, Task, TdsReturn, db
from audit_manager.services import billing as bsvc


def test_excel_import(world):
    w = admin_web(world)
    wb = Workbook(); ws = wb.active
    ws.append(["Name", "Category", "PAN", "GSTIN", "Email", "Mobile"])
    ws.append(["Imported One", "business", "IMPOR1111A", "", "", "9000000001"])
    ws.append(["Imported Two", "individual", "IMPOR2222B", "", "", ""])
    ws.append(["Bad PAN", "business", "xx", "", "", ""])
    ws.append(["Dup Of Apex", "business", "AABCA1234F", "", "", ""])
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    r = w.post("/clients/import", {"file": (buf, "c.xlsx")}, content_type="multipart/form-data", follow_redirects=True)
    assert r.status_code == 200
    with world["app"].app_context():
        assert Client.query.filter(Client.name.in_(["Imported One", "Imported Two"])).count() == 2
        assert Client.query.filter_by(name="Bad PAN").count() == 0
        assert Client.query.filter_by(name="Dup Of Apex").count() == 0
    assert w.get("/clients/import/template.xlsx").status_code == 200
    r = w.post("/clients/import", {"file": (io.BytesIO(b"not excel"), "c.xlsx")}, content_type="multipart/form-data", follow_redirects=True)
    assert b"not a valid" in r.data


def test_bulk_trackers_only_target_applicable_clients_and_are_idempotent(world):
    w = admin_web(world)
    with world["app"].app_context():
        rt = GstReturnType.query.filter_by(frequency="monthly").first()
        rid = rt.id
    w.post("/gst/bulk", {"return_type_id": rid, "period": "bad"})
    with world["app"].app_context():
        assert GstReturn.query.count() == 0
    w.post("/gst/bulk", {"return_type_id": rid, "period": "2026-10"})
    w.post("/gst/bulk", {"return_type_id": rid, "period": "2026-10"})
    w.post("/itr/bulk", {"assessment_year": "2026-27", "form_type": "ITR-1"})
    w.post("/tds/bulk", {"financial_year": "2026-27", "quarter": "Q2", "form_type": "26Q"})
    with world["app"].app_context():
        assert GstReturn.query.count() == 2   # Apex + Beta are GST registered; Charlie is not
        assert ItrFiling.query.count() == 3   # all three have ITR applicable
        assert TdsReturn.query.count() == 1   # only Apex
        row = GstReturn.query.first(); row_id = row.id
    w.post(f"/gst/{row_id}/update", {"status": "filed", "filed_date": "2026-11-10", "arn": "AA123"})
    with world["app"].app_context():
        row = db.session.get(GstReturn, row_id)
        assert row.status == "filed" and row.arn == "AA123"


def test_employee_cannot_bulk_or_touch_foreign_clients(world):
    w = Web(world["app"]); w.login("emp1@firm.in")
    with world["app"].app_context():
        rid = GstReturnType.query.first().id
    assert w.post("/gst/bulk", {"return_type_id": rid, "period": "2026-10"}).status_code == 403
    assert w.post("/gst/add", {"client_id": world["ids"]["beta"], "return_type_id": rid, "period": "2026-10"}).status_code == 403


def test_tasks_flow(world):
    w = Web(world["app"]); w.login("emp1@firm.in")
    w.post("/tasks/add", {"title": "Collect 26AS", "client_id": world["ids"]["apex"], "priority": "high"})
    with world["app"].app_context():
        t = Task.query.one(); tid = t.id
        assert t.assigned_to_id == world["ids"]["emp1"]
    r = w.c.post(f"/tasks/{tid}/status", json={"status": "completed"}, headers={"X-CSRF-Token": w.token()})
    assert r.status_code == 200
    with world["app"].app_context():
        assert db.session.get(Task, tid).status == "completed"
    assert w.c.post(f"/tasks/{tid}/status", json={"status": "completed"}).status_code == 400  # no CSRF header
    w.post("/tasks/add", {"title": "Foreign", "client_id": world["ids"]["beta"]})
    with world["app"].app_context():
        assert Task.query.filter_by(title="Foreign").count() == 0


def test_invoice_totals_numbering_and_payments(world):
    t = bsvc.compute_totals([{"quantity": 2, "rate": 5000.0}], 1000.0, "cgst_sgst", 9, 9, 18)
    assert (t["taxable_amount"], t["cgst_amount"], t["sgst_amount"], t["total_amount"]) == (9000.0, 810.0, 810.0, 10620.0)
    assert bsvc.compute_totals([{"quantity": 1, "rate": 1000.0}], 0, "igst", 9, 9, 18)["total_amount"] == 1180.0
    assert bsvc.compute_totals([{"quantity": 1, "rate": 1000.0}], 0, "exempt", 9, 9, 18)["total_amount"] == 1000.0
    assert bsvc.compute_totals([{"quantity": 1, "rate": 100.0}], 999, "exempt", 9, 9, 18)["total_amount"] == 0.0

    w = admin_web(world)
    assert w.get("/billing/new").status_code == 200
    form = {"client_id": world["ids"]["apex"], "tax_mode": "cgst_sgst", "invoice_date": "2026-11-01", "description": ["Audit fee", "Return filing"],
            "quantity": ["1", "1"], "rate": ["10000", "2000"], "sac_code": ["998221", ""]}
    r = w.post("/billing/new", form, follow_redirects=True)
    assert b"Invoice SA/" in r.data
    w.post("/billing/new", form)
    with world["app"].app_context():
        invs = Invoice.query.order_by(Invoice.id).all()
        assert len(invs) == 2 and invs[0].invoice_number != invs[1].invoice_number
        assert invs[0].total_amount == 14160.0 and invs[0].status in ("unpaid", "sent", "draft", "pending")
        iid = invs[0].id
    w.post(f"/billing/{iid}/payment", {"amount": "5000", "mode": "upi"})
    with world["app"].app_context():
        i = db.session.get(Invoice, iid); assert i.paid_amount == 5000.0 and i.status == "partially_paid"
    w.post(f"/billing/{iid}/payment", {"amount": "999999", "mode": "upi"})  # overpayment refused
    with world["app"].app_context():
        assert db.session.get(Invoice, iid).paid_amount == 5000.0
    w.post(f"/billing/{iid}/payment", {"amount": "9160", "mode": "bank"})
    with world["app"].app_context():
        assert db.session.get(Invoice, iid).status == "paid"
    pdf = w.get(f"/billing/{iid}/pdf")
    assert pdf.status_code == 200 and pdf.data[:4] == b"%PDF"
    assert "Sharma & Associates" in PdfReader(io.BytesIO(pdf.data)).pages[0].extract_text()


def _set_firm(w):
    w.post("/settings/firm", {"firm_name": "Sharma & Associates", "firm_address": "Main Bazar, Abohar", "firm_phone": "9999999999",
                              "firm_email": "ca@sharma.in", "firm_frn": "012345N", "firm_pan": "AAAFS1234A", "firm_gstin": "03AAAFS1234A1Z1",
                              "firm_partner_name": "CA Neeraj Sharma", "firm_membership_no": "512345", "invoice_prefix": "SA",
                              "default_cgst_rate": "9", "default_sgst_rate": "9", "default_igst_rate": "18",
                              "firm_logo": (io.BytesIO(PNG_1X1), "logo.png")}, content_type="multipart/form-data")


def test_logo_validation(world):
    w = admin_web(world)
    r = w.post("/settings/firm", {"firm_name": "X", "firm_logo": (io.BytesIO(b"<script>alert(1)</script>"), "logo.png")},
               content_type="multipart/form-data", follow_redirects=True)
    assert b"valid PNG or JPG" in r.data or b"not a valid" in r.data or b"image" in r.data
    from audit_manager.services import letterhead
    with world["app"].app_context():
        assert letterhead.logo_bytes() is None
    _set_firm(w)
    with world["app"].app_context():
        assert letterhead.logo_bytes()


def test_reports_all_formats_carry_letterhead(world):
    w = admin_web(world)
    _set_firm(w)
    w.post("/gst/bulk", {"return_type_id": 1, "period": "2026-10"})
    from audit_manager.services import reports
    for kind in reports.TYPES:
        page = w.get(f"/reports/?type={kind}")
        assert page.status_code == 200, kind
        assert b"Sharma &amp; Associates" in page.data and b"CA Neeraj Sharma" in page.data and b"data:image/png;base64" in page.data, kind
        pdf = w.get(f"/reports/export.pdf?type={kind}")
        assert pdf.data[:4] == b"%PDF", kind
        text = PdfReader(io.BytesIO(pdf.data)).pages[0].extract_text()
        assert "Sharma & Associates" in text and "012345N" in text and "CA Neeraj Sharma" in text, kind
        csv = w.get(f"/reports/export.csv?type={kind}").data.decode("utf-8-sig")
        assert "Sharma & Associates" in csv.splitlines()[0] or "Sharma & Associates" in csv[:400], kind
        x = load_workbook(io.BytesIO(w.get(f"/reports/export.xlsx?type={kind}").data))
        vals = " ".join(str(c.value) for row in x.active.iter_rows(max_row=8) for c in row if c.value)
        assert "Sharma & Associates" in vals and "012345N" in vals, kind
        assert x.active._images, kind  # logo embedded


def test_csv_formula_injection_is_neutralised(world):
    w = admin_web(world)
    w.post("/clients/new", {"name": "=HYPERLINK(\"http://x\")", "pan": "FFFPF1111F"})
    csv = w.get("/reports/export.csv?type=client_compliance").data.decode("utf-8-sig")
    assert '\n=HYPERLINK' not in csv and ',=HYPERLINK' not in csv and '"=HYPERLINK' not in csv


def test_mail_settings_encrypted_and_test_email(world, monkeypatch):
    w = admin_web(world)
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None, **kw): sent["conn"] = (host, port)
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, **kw): sent["tls"] = True
        def login(self, u, p): sent["login"] = (u, p)
        def send_message(self, m): sent["to"] = m["To"]; sent["subject"] = m["Subject"]
        def ehlo(self): pass
        def quit(self): pass

    import smtplib
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    r = w.post("/settings/mail", {"mail_enabled": "1", "mail_host": "", "mail_port": "587", "mail_from_address": "x@y.in"}, follow_redirects=True)
    assert b"fill in the host" in r.data
    w.post("/settings/mail", {"mail_enabled": "1", "mail_host": "smtp.example.in", "mail_port": "587", "mail_encryption": "tls",
                              "mail_username": "ca@example.in", "mail_password": "s3cret-pass", "mail_from_address": "ca@example.in", "mail_from_name": "Sharma & Co"})
    with world["app"].app_context():
        stored = FirmSetting.get("mail_password")
        assert stored and "s3cret-pass" not in stored
    page = w.get("/settings/").data
    assert b"s3cret-pass" not in page and b"Saved (leave blank to keep)" in page
    w.post("/settings/mail/test", {"test_to": "me@example.in"})
    assert sent["to"] == "me@example.in" and sent["login"] == ("ca@example.in", "s3cret-pass") and sent["conn"] == ("smtp.example.in", 587)
    w.post("/settings/mail", {"mail_enabled": "1", "mail_host": "smtp.example.in", "mail_port": "587", "mail_from_address": "ca@example.in"})
    with world["app"].app_context():
        assert FirmSetting.get("mail_password") == stored  # blank keeps existing


def test_backup_download_is_a_zip_with_the_database(world, tmp_path):
    import zipfile
    w = admin_web(world)
    r = w.get("/settings/backup")
    assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.data))
    p = tmp_path / "b.db"; p.write_bytes(z.read("auditmanager.db"))
    con = sqlite3.connect(p)
    assert con.execute("select count(*) from client").fetchone()[0] == 3
    con.close()
    assert Web(world["app"]).get("/settings/backup").status_code == 302


def test_password_change(world):
    w = Web(world["app"]); w.login("emp1@firm.in")
    r = w.post("/account/password", {"current": "wrong", "new": "NewPassw0rd!", "new2": "NewPassw0rd!"}, follow_redirects=True)
    w.post("/account/password", {"current": "Passw0rd!x", "new": "NewPassw0rd!", "new2": "NewPassw0rd!"})
    w.logout()
    assert w.login("emp1@firm.in", "NewPassw0rd!").status_code in (302, 200)
    assert b"Dashboard" in w.get("/").data


# ------------------------------------------------------------------ look-ups, themes, UI helpers
def test_pan_is_taken_from_gstin_on_save_and_import(world):
    w = admin_web(world)
    w.post("/clients/new", {"name": "Auto Pan Ltd", "gstin": "03QQQCQ1234F1Z5"})
    with world["app"].app_context():
        c = Client.query.filter_by(name="Auto Pan Ltd").one()
        assert c.pan == "QQQCQ1234F" and c.is_gst_registered and c.client_code
    wb = Workbook(); ws = wb.active
    ws.append(["Name", "PAN", "GSTIN"]); ws.append(["Imp Auto", "", "27WWWCW1234F1Z5"])
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    w.post("/clients/import", {"file": (buf, "c.xlsx")}, content_type="multipart/form-data")
    with world["app"].app_context():
        assert Client.query.filter_by(name="Imp Auto").one().pan == "WWWCW1234F"


def test_client_save_with_owner_and_shared_staff(world):
    w = admin_web(world)
    ids = world["ids"]
    r = w.post("/clients/new", {"name": "Shared Co", "gstin": "03SSSCS1234F1Z5", "pincode": "152116", "city": "Abohar", "state": "Punjab",
                                "assigned_to_id": ids["emp1"], "staff_ids": [ids["emp2"], ids["manager"]], "is_itr_applicable": "1"}, follow_redirects=True)
    assert r.status_code == 200 and b"Shared Co" in r.data
    with world["app"].app_context():
        c = Client.query.filter_by(name="Shared Co").one()
        assert len(c.staff) == 2 and c.assigned_to_id == ids["emp1"]


def test_pincode_lookup_online_and_offline(world, monkeypatch):
    from audit_manager.services import lookup
    w = admin_web(world)

    class R:
        def json(self): return [{"Status": "Success", "PostOffice": [{"District": "Fazilka", "State": "Punjab"}]}]
    monkeypatch.setattr(lookup.requests, "get", lambda *a, **k: R())
    lookup._pin_cache.clear()
    assert w.get("/lookup/pincode/152116").get_json() == {"ok": True, "city": "Fazilka", "state": "Punjab", "source": "India Post"}

    def boom(*a, **k): raise lookup.requests.ConnectionError()
    monkeypatch.setattr(lookup.requests, "get", boom)
    d = w.get("/lookup/pincode/400001").get_json()
    assert d["ok"] and d["state"] == "Maharashtra" and d["source"] == "offline"
    assert w.get("/lookup/pincode/12").get_json()["ok"] is False
    assert Web(world["app"]).get("/lookup/pincode/400001").status_code == 302  # sign-in needed


def test_gst_portal_lookup_with_user_captcha(world, monkeypatch):
    from audit_manager.services import lookup
    w = admin_web(world)
    calls = {}

    class Resp:
        def __init__(self, content=b"", data=None): self.content, self._d, self.headers = content, data, {"Content-Type": "image/png"}
        def raise_for_status(self): pass
        def json(self): return self._d

    class FakeSession:
        headers = {}
        def __init__(self): self.headers = {}
        def get(self, url, **k): return Resp(content=b"PNGDATA")
        def post(self, url, json=None, **k):
            calls["sent"] = json
            if json["captcha"] == "bad":
                return Resp(data={"errorCode": "SWEB_9000", "message": "Enter valid Letters shown"})
            return Resp(data={"lgnm": "NEERAJ KUMAR", "tradeNam": "APEX TRADERS", "sts": "Active", "ctb": "Proprietorship", "rgdt": "01/07/2017",
                              "pradr": {"adr": "Shop 4, Main Bazar, Abohar, Fazilka, Punjab, 152116"}})
    monkeypatch.setattr(lookup.requests, "Session", FakeSession)
    img = w.get("/lookup/gst/captcha")
    assert img.status_code == 200 and img.data == b"PNGDATA"
    hdr = {"X-CSRF-Token": w.token()}
    d = w.c.post("/lookup/gst", json={"gstin": "03AABCA1234F1Z5", "captcha": "bad"}, headers=hdr).get_json()
    assert d["ok"] is False and d["captcha"] is True
    w.get("/lookup/gst/captcha")
    d = w.c.post("/lookup/gst", json={"gstin": "03aabca1234f1z5", "captcha": "x7k2p"}, headers=hdr).get_json()
    assert d["ok"] and d["name"] == "APEX TRADERS" and d["legal_name"] == "NEERAJ KUMAR" and d["pan"] == "AABCA1234F"
    assert d["pincode"] == "152116" and d["state"] == "Punjab" and d["address"].startswith("Shop 4, Main Bazar")
    assert calls["sent"] == {"gstin": "03AABCA1234F1Z5", "captcha": "x7k2p"}
    assert w.c.post("/lookup/gst", json={"gstin": "nonsense", "captcha": "x"}, headers=hdr).get_json()["ok"] is False
    assert w.c.post("/lookup/gst", json={"gstin": "03AABCA1234F1Z5", "captcha": "x"}).status_code == 400  # CSRF


def test_theme_choice_is_per_user_and_pages_have_back_button(world):
    w = admin_web(world)
    page = w.get("/clients/").data
    assert b'data-theme="navy"' in page and b'id="backBtn"' in page and b"js/app.js" in page
    w.post("/account/theme", {"theme": "dark"})
    assert b'data-theme="dark"' in w.get("/clients/").data and b'data-bs-theme="dark"' in w.get("/clients/").data
    w.post("/account/theme", {"theme": "not-a-theme"})
    assert b'data-theme="dark"' in w.get("/clients/").data
    other = Web(world["app"]); other.login("emp1@firm.in")
    assert b'data-theme="navy"' in other.get("/clients/").data
    assert b"gstFetchBtn" in w.get("/clients/new").data and b"400 x 160" in w.get("/settings/").data
    assert b"Download sample template" in w.get("/clients/import").data
