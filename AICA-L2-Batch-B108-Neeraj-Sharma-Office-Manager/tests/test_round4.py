import io
import zipfile
from datetime import date, datetime, timedelta

from pypdf import PdfReader

from conftest import Web, admin_web
from audit_manager.models import (ActivityLog, Client, ClientCredential, DueDate, FirmSetting, Invoice, Matter, TimeEntry, WhatsAppMessage,
                                  WhatsAppTemplate, db)


def _smtp(monkeypatch, sent):
    class FakeSMTP:
        def __init__(self, *a, **k): pass
        def ehlo(self): pass
        def starttls(self, **k): pass
        def login(self, *a): pass
        def send_message(self, m): sent.append(m)
        def quit(self): pass
        def close(self): pass
    import smtplib
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)


def test_app_is_called_office_manager(world):
    a = admin_web(world)
    page = a.get("/").data
    assert b"Office Manager" in page and b"Audit Manager" not in page


# ------------------------------------------------------------------ due-date master
def test_due_date_master_is_preloaded_and_editable(world):
    a = admin_web(world)
    with world["app"].app_context():
        rows = DueDate.query.all()
        assert len(rows) >= 40
        by = {(d.title, d.period): d.due_date for d in rows}
        assert by[("GSTR-3B (monthly)", "Dec 2026")] == date(2027, 1, 20)
        assert by[("TDS return (quarterly)", "Oct-Dec 2026")] == date(2027, 1, 31)
        assert by[("Advance tax - final instalment (100%)", "FY 2026-27")] == date(2027, 3, 15)
        assert by[("GSTR-9 / GSTR-9C annual return", "FY 2025-26")] == date(2026, 12, 31)
        assert max(d.due_date for d in rows) == date(2027, 3, 31)
        did = next(d.id for d in rows if d.title == "GSTR-9 / GSTR-9C annual return")
        total = len(rows)
    page = a.get("/calendar/due-dates?show=all").data
    assert b"Due Date Master" in page and b"GSTR-9 / GSTR-9C" in page and b"Edit" in page
    a.post("/calendar/due-dates", {"id": did, "title": "GSTR-9 / GSTR-9C annual return", "period": "FY 2025-26", "due_date": "2027-02-28",
                                   "category": "gst", "notes": "Extended"})
    a.post("/calendar/due-dates", {"title": "Office - partner meeting", "due_date": "2027-01-05", "category": "other"})
    with world["app"].app_context():
        assert db.session.get(DueDate, did).due_date == date(2027, 2, 28)
        assert DueDate.query.count() == total + 1
    a.post("/calendar/due-dates", {"action": "load_standard"})
    with world["app"].app_context():  # the edited row no longer matches the standard one, so the standard date comes back alongside it
        assert DueDate.query.count() == total + 2
    e = Web(world["app"]); e.login("emp1@firm.in")
    assert e.get("/calendar/due-dates").status_code == 200
    assert e.post("/calendar/due-dates", {"title": "x", "due_date": "2027-01-05"}).status_code == 403


def test_masters_can_be_edited(world):
    a = admin_web(world)
    assert b"/clients/1/edit" in a.get("/clients/").data  # edit button in the client list
    with world["app"].app_context():
        tid = WhatsAppTemplate.query.filter_by(name="Return filed").one().id
    assert b"Edit template" in a.get(f"/whatsapp/templates?edit={tid}").data
    a.post("/whatsapp/templates", {"id": tid, "name": "Return filed", "category": "compliance", "body": "Dear {client_name},\n\nFiled.\n\nRegards"})
    with world["app"].app_context():
        assert db.session.get(WhatsAppTemplate, tid).body.startswith("Dear {client_name},\n\nFiled.")


# ------------------------------------------------------------------ scheduled email
def test_email_can_be_scheduled_sent_later_and_cancelled(world, monkeypatch):
    from audit_manager.services import whatsapp as wa
    sent = []
    _smtp(monkeypatch, sent)
    a = admin_web(world)
    a.post("/settings/mail", {"mail_enabled": "1", "mail_host": "smtp.x.in", "mail_port": "587", "mail_from_address": "ca@x.in"})
    later = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
    r = a.post("/whatsapp/compose", {"channel": "email", "subject": "Reminder", "body": "Dear {client_name},\n\nPlease note.", "send_at": later,
                                      "client_ids": [world["ids"]["apex"]]}, follow_redirects=True)
    assert b"1 email(s) scheduled" in r.data and sent == [] and b"Scheduled" in r.data
    with world["app"].app_context():
        m = WhatsAppMessage.query.one()
        assert m.status == "scheduled" and m.email == "apex@example.in"
        assert wa.send_scheduled(datetime.now()) == 0 and sent == []
        assert wa.send_scheduled(datetime.now() + timedelta(days=3)) == 1
        assert sent[0]["To"] == "apex@example.in" and db.session.get(WhatsAppMessage, m.id).status == "opened"
    a.post("/whatsapp/compose", {"channel": "email", "subject": "Second", "body": "x", "send_at": later, "client_ids": [world["ids"]["apex"]]})
    with world["app"].app_context():
        mid = WhatsAppMessage.query.filter_by(status="scheduled").one().id
    a.post(f"/whatsapp/{mid}/cancel")
    with world["app"].app_context():
        assert wa.send_scheduled(datetime.now() + timedelta(days=3)) == 0 and len(sent) == 1


# ------------------------------------------------------------------ portal logins
def test_portal_logins_are_encrypted_logged_and_access_controlled(world):
    ids = world["ids"]
    a = admin_web(world)
    a.post(f"/clients/{ids['apex']}/credentials", {"portal": "GST Portal", "username": "apex_gst", "password": "S3cret#Pass", "notes": "OTP to owner"})
    with world["app"].app_context():
        row = ClientCredential.query.one()
        assert row.username == "apex_gst" and row.secret and "S3cret#Pass" not in row.secret
        cid = row.id
    page = a.get(f"/clients/{ids['apex']}").data
    assert b"apex_gst" in page and b"S3cret#Pass" not in page and b"Open portal" in page
    r = a.c.post(f"/clients/{ids['apex']}/credentials/{cid}/reveal", headers={"X-CSRF-Token": a.token()})
    assert r.get_json()["password"] == "S3cret#Pass"
    with world["app"].app_context():
        assert ActivityLog.query.filter(ActivityLog.description.like("Viewed the GST Portal password%")).count() == 1
    other = Web(world["app"]); other.login("emp2@firm.in")  # Apex is not emp2's client
    assert other.c.post(f"/clients/{ids['apex']}/credentials/{cid}/reveal", headers={"X-CSRF-Token": other.token()}).status_code == 403
    assert a.c.post(f"/clients/{ids['beta']}/credentials/{cid}/reveal", headers={"X-CSRF-Token": a.token()}).status_code == 404  # wrong client in URL
    z = zipfile.ZipFile(io.BytesIO(a.get("/settings/backup").data))
    assert "mail.key" in z.namelist()  # so saved passwords can be read after a restore


# ------------------------------------------------------------------ invoice link + PDF folder
def test_invoice_whatsapp_link_and_pdf_folder(world, tmp_path):
    a = admin_web(world)
    folder = tmp_path / "Drive" / "Invoices"
    a.post("/settings/office", {"profession": "ca", "invoice_pdf_folder": str(folder), "default_hourly_rate": "1500"})
    a.post("/billing/new", {"client_id": world["ids"]["apex"], "tax_mode": "cgst_sgst", "invoice_date": "2026-11-01",
                            "description": ["Audit fee"], "quantity": ["1"], "rate": ["10000"], "sac_code": ["998221"]})
    with world["app"].app_context():
        inv = Invoice.query.one(); iid, number = inv.id, inv.invoice_number
    a.post(f"/billing/{iid}/whatsapp", {"link": "https://drive.google.com/file/d/abc/view"})
    with world["app"].app_context():
        body = WhatsAppMessage.query.one().body
        assert "https://drive.google.com/file/d/abc/view" in body and body.index("drive.google.com") < body.index("Kindly arrange")
    saved = folder / (number.replace("/", "-") + ".pdf")
    assert saved.exists() and saved.read_bytes()[:4] == b"%PDF"


# ------------------------------------------------------------------ hour-based billing
def test_time_sheet_and_billing_by_the_hour(world):
    ids = world["ids"]
    a = admin_web(world)
    assert b'href="/time/"' not in a.get("/").data and a.get("/time/").status_code == 302  # hidden until switched on
    a.post("/settings/office", {"profession": "ca", "hourly_billing": "1"})
    assert b'href="/time/"' in a.get("/").data
    a.post("/time/rates", {"default_hourly_rate": "1000", f"rate_{ids['emp1']}": "1200"})
    e = Web(world["app"]); e.login("emp1@firm.in")
    e.post("/time/add", {"client_id": ids["apex"], "work_date": "2026-11-10", "hours": "1", "minutes": "30", "description": "Drafting reply", "rate": "99999"})
    e.post("/time/add", {"client_id": ids["apex"], "work_date": "2026-11-11", "hours": "2", "description": "Internal review", "billable": "0"})
    assert e.post("/time/add", {"client_id": ids["beta"], "hours": "1"}).status_code == 403  # not emp1's client
    with world["app"].app_context():
        t = TimeEntry.query.filter_by(description="Drafting reply").one()
        assert t.hours == 1.5 and t.rate == 1200 and t.value == 1800  # staff cannot choose their own rate
    a.post("/time/add", {"client_id": ids["apex"], "work_date": "2026-11-12", "hours": "2", "description": "Hearing", "user_id": ids["admin"], "rate": "2500"})
    page = e.get("/time/").data
    assert b"Drafting reply" in page and b"Hearing" not in page and b"Unbilled (1)" in page  # employees see their own time only
    assert e.post("/time/bill", {"client_id": ids["apex"]}).status_code == 403
    r = a.post("/time/bill", {"client_id": ids["apex"], "upto": "2026-11-30", "tax_mode": "cgst_sgst", "style": "detail"}, follow_redirects=True)
    assert b"created from 2 time entries" in r.data
    with world["app"].app_context():
        inv = Invoice.query.one()
        assert inv.taxable_amount == 6800.0 and inv.total_amount == 8024.0 and len(inv.items) == 2
        assert {it.quantity for it in inv.items} == {1.5, 2.0}
        assert TimeEntry.query.filter(TimeEntry.invoice_id == inv.id).count() == 2
        assert TimeEntry.query.filter_by(description="Internal review").one().invoice_id is None
    r = a.post("/time/bill", {"client_id": ids["apex"]}, follow_redirects=True)
    assert b"no unbilled hours" in r.data
    with world["app"].app_context():
        assert Invoice.query.count() == 1


# ------------------------------------------------------------------ registers and own-GST reports
def test_own_gst_reports_add_up(world):
    a = admin_web(world)
    ids = world["ids"]
    a.post("/billing/new", {"client_id": ids["apex"], "tax_mode": "cgst_sgst", "invoice_date": "2026-11-01", "description": ["Audit"], "quantity": ["1"], "rate": ["10000"], "sac_code": ["998221"]})
    a.post("/billing/new", {"client_id": ids["beta"], "tax_mode": "igst", "invoice_date": "2026-11-05", "description": ["ITR"], "quantity": ["2"], "rate": ["1000"], "sac_code": ["998231"]})
    a.post("/billing/new", {"client_id": ids["charlie"], "tax_mode": "exempt", "invoice_date": "2026-12-02", "description": ["Advice"], "quantity": ["1"], "rate": ["500"], "sac_code": ["998231"]})
    from audit_manager.services import reports
    with world["app"].app_context():
        from audit_manager.models import User
        u = db.session.get(User, ids["admin"])
        out = reports.build("own_gst_outward", u)
        assert out["rows"][0][2] == "B2B" and out["rows"][1][2] == "B2C" and out["rows"][0][4] == "03AABCA1234F1Z5"
        assert out["rows"][-1][8:] == [12500.0, 900.0, 900.0, 360.0, 14660.0]
        summ = reports.build("own_gst_summary", u)["rows"]
        assert summ[0] == ["Nov 2026", 2, 12000.0, 0, 900.0, 900.0, 360.0, 2160.0] and summ[1][3] == 500.0 and summ[-1][7] == 2160.0
        sac = {r[0]: r for r in reports.build("own_gst_sac", u)["rows"]}
        assert sac["998221"][2:] == [10000.0, 1800.0, 11800.0] and sac["998231"][2] == 2500.0 and sac["TOTAL"][4] == 14660.0
        reg = reports.build("invoice_register", u, date(2026, 11, 1), date(2026, 11, 30))["rows"]
        assert len(reg) == 3 and reg[-1][8] == 14160.0
        assert len(reports.build("client_register", u)["rows"]) == 3
    for kind in ("own_gst_outward", "invoice_register", "client_register", "receipt_register", "time_register", "matter_register"):
        assert a.get(f"/reports/export.xlsx?type={kind}").status_code == 200 and a.get(f"/reports/export.pdf?type={kind}").data[:4] == b"%PDF"


# ------------------------------------------------------------------ advocates
def test_advocate_mode_labels_and_matters(world):
    ids = world["ids"]
    a = admin_web(world)
    assert b"Matters &amp; Hearings" not in a.get("/").data  # hidden for a CA office
    a.post("/settings/firm", {"firm_name": "Sharma Law Chambers", "firm_frn": "P/1234/2010", "firm_partner_name": "Adv. Neeraj Sharma", "firm_membership_no": "214"})
    a.post("/settings/office", {"profession": "advocate"})
    home = a.get("/").data
    assert b"Matters &amp; Hearings" in home
    assert b"Bar Council Enrolment No." in a.get("/settings/").data
    text = PdfReader(io.BytesIO(a.get("/reports/export.pdf").data)).pages[0].extract_text()
    assert "Advocate" in text and "Chartered Accountant" not in text and "Enrl. No.: P/1234/2010" in text
    a.post("/matters/", {"client_id": ids["apex"], "title": "Apex vs State Bank", "case_number": "CS 45/2026", "court": "Civil Judge, Abohar",
                         "opposite_party": "State Bank", "stage": "Evidence", "next_hearing": str(date.today() + timedelta(days=3))})
    with world["app"].app_context():
        mid = Matter.query.one().id
    page = a.get("/matters/").data
    assert b"Apex vs State Bank" in page and b"Hearings in 7 days (1)" in page and b"Open (1)" in page
    a.post("/matters/", {"id": mid, "client_id": ids["apex"], "title": "Apex vs State Bank", "status": "closed"})
    assert b"Closed (1)" in a.get("/matters/").data
    e = Web(world["app"]); e.login("emp2@firm.in")
    assert b"Apex vs State Bank" not in e.get("/matters/?status=closed").data  # other staff's client
    assert e.post("/matters/", {"client_id": ids["apex"], "title": "x"}).status_code == 403


# ------------------------------------------------------------------ backup timing and data folder
def test_backup_on_open_and_close_choice(world, tmp_path):
    from audit_manager.services import backup
    a = admin_web(world)
    folder = tmp_path / "bk"
    a.post("/settings/backup/settings", {"backup_folder": str(folder), "backup_keep": "30", "backup_when": "close"})
    with world["app"].app_context():
        assert backup.on_open() is False and backup.auto_if_due() is False
        assert backup.on_close() is True and len(list(folder.glob("OfficeManager-backup-*.zip"))) == 1
    a.post("/settings/backup/settings", {"backup_folder": str(folder), "backup_keep": "30", "backup_when": "open_close"})
    with world["app"].app_context():
        assert backup.when() == "open_close" and backup.on_open() is True
    page = a.get("/settings/").data
    assert b"Every time the app is closed" in page and b"On opening and on closing" in page


def test_data_folder_can_be_moved_to_another_drive(world, tmp_path):
    from audit_manager import config, create_app
    a = admin_web(world)
    old = config.data_dir()
    target = tmp_path / "D-drive" / "Office Manager Data"
    r = a.post("/settings/data-folder", {"data_folder": "not/absolute"}, follow_redirects=True)
    assert b"full folder path" in r.data
    p = Web(world["app"]); p.login("partner@firm.in")
    assert b"Only the Super Admin" in p.post("/settings/data-folder", {"data_folder": str(target)}, follow_redirects=True).data
    r = a.post("/settings/data-folder", {"data_folder": str(target)}, follow_redirects=True)
    assert b"Close Office Manager completely" in r.data and config.pending_move() == str(target)
    assert config.data_dir() == old  # nothing moves while the app is running
    with world["app"].app_context():
        db.session.remove(); db.engine.dispose()
    app2 = create_app({"TESTING": True})  # "restart"
    assert config.data_dir() == target and (target / "auditmanager.db").exists() and (old / "auditmanager.db").exists()
    with app2.app_context():
        assert Client.query.count() == 3 and FirmSetting.get("firm_name") == "Sharma & Associates"
    w = Web(app2)
    assert w.login("admin@firm.in").status_code == 302  # same session key and passwords after the move
