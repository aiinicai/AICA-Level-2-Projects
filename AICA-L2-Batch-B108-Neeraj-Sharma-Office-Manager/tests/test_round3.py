import io
import os
import zipfile
from datetime import date

from openpyxl import Workbook, load_workbook
from pypdf import PdfReader

from conftest import PNG_1X1, Web, admin_web
from audit_manager.models import (Client, FirmSetting, GstReturn, GstReturnType, Invoice, ItrFiling, ServiceItem, TdsReturn, User,
                                  WhatsAppMessage, WhatsAppTemplate, db)
from audit_manager.services import whatsapp as wa


def _xlsx(rows):
    wb = Workbook(); ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return buf


# ------------------------------------------------------------------ permissions
def test_permissions_grant_and_revoke_modules(world):
    ids = world["ids"]
    a = admin_web(world)
    e = Web(world["app"]); e.login("emp1@firm.in")
    assert e.get("/billing/").status_code == 403 and e.get("/tasks/").status_code == 200
    page = a.get("/staff/permissions")
    assert page.status_code == 200 and b"User permissions" in page.data
    # give emp1 billing, take away tasks; leave everyone else as they are
    form = {f"perm_{ids['emp1']}": ["clients", "trackers", "calendar", "messages", "billing"]}
    for who in ("partner", "manager", "emp2"):
        with world["app"].app_context():
            from audit_manager import perms
            form[f"perm_{ids[who]}"] = sorted(perms.role_default(db.session.get(User, ids[who]).role))
    a.post("/staff/permissions", form)
    assert e.get("/billing/").status_code == 200 and e.get("/billing/new").status_code == 200
    assert e.get("/tasks/").status_code == 403
    nav = e.get("/").data
    assert b"/billing/" in nav and b'href="/tasks/"' not in nav
    assert e.get("/settings/").status_code == 403 and e.get("/reports/").status_code == 403
    m = Web(world["app"]); m.login("manager@firm.in")
    assert m.get("/billing/").status_code == 200  # untouched role keeps its standard access
    assert m.get("/staff/permissions").status_code == 403  # only admin / partner may change permissions
    a.post(f"/staff/permissions/{ids['emp1']}/reset")
    assert e.get("/billing/").status_code == 403 and e.get("/tasks/").status_code == 200


def test_super_admin_cannot_be_locked_out(world):
    a = admin_web(world)
    a.post("/staff/permissions", {f"perm_{world['ids']['admin']}": []})
    assert a.get("/settings/").status_code == 200 and a.get("/clients/").status_code == 200


# ------------------------------------------------------------------ activity log, theme
def test_activity_log_page_with_filters(world):
    a = admin_web(world)
    a.post("/clients/new", {"name": "Logged Co", "pan": "LLLPL1111L"})
    page = a.get("/activity/").data
    assert b"Added client Logged Co" in page and b"data-total" in page
    assert b"Added client Logged Co" not in a.get("/activity/?module=auth").data
    assert b"Added client Logged Co" in a.get(f"/activity/?module=clients&user_id={world['ids']['admin']}&from_date={date.today()}").data
    assert b"Activity log</h2>" not in a.get("/settings/").data  # moved out of Settings
    e = Web(world["app"]); e.login("emp1@firm.in")
    assert e.get("/activity/").status_code == 403


def test_theme_buttons_in_settings_and_account(world):
    a = admin_web(world)
    assert b'name="theme" value="dark"' in a.get("/settings/").data and b'name="theme" value="emerald"' in a.get("/account/password").data
    assert b'select name="theme"' not in a.get("/clients/").data


# ------------------------------------------------------------------ report header choices
def test_report_header_fields_can_be_hidden(world):
    a = admin_web(world)
    a.post("/settings/firm", {"firm_name": "Sharma & Associates", "firm_frn": "012345N", "firm_pan": "AAAFS1234A", "firm_phone": "9999999999",
                              "firm_partner_name": "CA Neeraj Sharma", "firm_membership_no": "512345",
                              "firm_logo": (io.BytesIO(PNG_1X1), "logo.png")}, content_type="multipart/form-data")
    text = PdfReader(io.BytesIO(a.get("/reports/export.pdf").data)).pages[0].extract_text()
    assert "512345" in text and "012345N" in text
    a.post("/settings/report-header", {"show": ["address", "phone", "frn", "partner_name"]})  # membership no., PAN and logo unticked
    page = a.get("/reports/").data
    assert b"512345" not in page and b"AAAFS1234A" not in page and b"data:image/png" not in page and b"012345N" in page and b"CA Neeraj Sharma" in page
    text = PdfReader(io.BytesIO(a.get("/reports/export.pdf").data)).pages[0].extract_text()
    assert "512345" not in text and "AAAFS1234A" not in text and "012345N" in text
    csv = a.get("/reports/export.csv").data.decode("utf-8-sig")
    assert "512345" not in csv and "9999999999" in csv
    x = load_workbook(io.BytesIO(a.get("/reports/export.xlsx").data))
    assert not x.active._images
    # invoices still carry everything
    a.post("/billing/new", {"client_id": world["ids"]["apex"], "tax_mode": "exempt", "description": ["Fee"], "quantity": ["1"], "rate": ["100"], "sac_code": [""]})
    with world["app"].app_context():
        iid = Invoice.query.one().id
    assert "AAAFS1234A" in PdfReader(io.BytesIO(a.get(f"/billing/{iid}/pdf").data)).pages[0].extract_text()


# ------------------------------------------------------------------ backup to folder, auto, restore
def test_backup_to_folder_keeps_only_the_latest(world, tmp_path, monkeypatch):
    from audit_manager.services import backup
    a = admin_web(world)
    folder = tmp_path / "drive" / "Office Manager Backups"
    r = a.post("/settings/backup/settings", {"backup_folder": "relative/path", "backup_keep": "2"}, follow_redirects=True)
    assert b"full folder path" in r.data
    a.post("/settings/backup/settings", {"backup_folder": str(folder), "backup_keep": "2", "backup_when": "daily"})
    names = iter(["OfficeManager-backup-20260101-000001.zip", "OfficeManager-backup-20260101-000002.zip", "OfficeManager-backup-20260101-000003.zip"])
    monkeypatch.setattr(backup, "file_name", lambda: next(names))
    for _ in range(3):
        r = a.post("/settings/backup/now", follow_redirects=True)
        assert b"Backup saved" in r.data
    files = sorted(f.name for f in folder.glob("*.zip"))
    assert files == ["OfficeManager-backup-20260101-000002.zip", "OfficeManager-backup-20260101-000003.zip"]
    assert "auditmanager.db" in zipfile.ZipFile(folder / files[-1]).namelist()
    with world["app"].app_context():
        assert backup.auto_if_due() is False  # already backed up today
        FirmSetting.put("backup_last_at", "2020-01-01"); db.session.commit()
        monkeypatch.setattr(backup, "file_name", lambda: "OfficeManager-backup-20260102-000001.zip")
        assert backup.auto_if_due() is True
        assert FirmSetting.get("backup_last_result").startswith("OK")


def test_restore_is_validated_and_applied_at_next_start(world, monkeypatch):
    from audit_manager import create_app
    from audit_manager.services import backup
    a = admin_web(world)
    good = a.get("/settings/backup").data
    a.post("/clients/new", {"name": "Added After Backup", "pan": "NNNPN1111N"})
    r = a.post("/settings/backup/restore", {"backup_file": (io.BytesIO(b"junk"), "x.zip"), "confirm": "RESTORE"}, content_type="multipart/form-data", follow_redirects=True)
    assert b"not an Office Manager backup" in r.data
    r = a.post("/settings/backup/restore", {"backup_file": (io.BytesIO(good), "b.zip"), "confirm": "no"}, content_type="multipart/form-data", follow_redirects=True)
    assert b"Type RESTORE" in r.data
    p = Web(world["app"]); p.login("partner@firm.in")
    r = p.post("/settings/backup/restore", {"backup_file": (io.BytesIO(good), "b.zip"), "confirm": "RESTORE"}, content_type="multipart/form-data", follow_redirects=True)
    assert b"Only the Super Admin" in r.data
    r = a.post("/settings/backup/restore", {"backup_file": (io.BytesIO(good), "b.zip"), "confirm": "RESTORE"}, content_type="multipart/form-data", follow_redirects=True)
    assert b"Close Office Manager completely" in r.data
    with world["app"].app_context():
        assert backup.pending_restore()
        assert Client.query.filter_by(name="Added After Backup").count() == 1
        db.session.remove(); db.engine.dispose()
    app2 = create_app({"TESTING": True})  # "restart"
    with app2.app_context():
        assert Client.query.filter_by(name="Added After Backup").count() == 0 and Client.query.count() == 3
        assert not backup.pending_restore()
        from audit_manager.config import data_dir
        assert any(f.name.startswith("before-restore-") for f in data_dir().iterdir())


# ------------------------------------------------------------------ services master
def test_services_master_and_invoice_form(world):
    a = admin_web(world)
    with world["app"].app_context():
        assert ServiceItem.query.count() >= 10
    a.post("/billing/services", {"name": "Net Worth Certificate", "sac_code": "998221", "default_rate": "2500"})
    r = a.post("/billing/services", {"name": "net worth certificate", "sac_code": "1"}, follow_redirects=True)
    assert b"already exists" in r.data
    page = a.get("/billing/new").data
    assert b"Net Worth Certificate" in page and b"svcList" in page and b'"rate": 2500.0' in page
    with world["app"].app_context():
        sid = ServiceItem.query.filter_by(name="Net Worth Certificate").one().id
    a.post("/billing/services", {"id": sid, "name": "Net Worth Certificate", "sac_code": "998221", "default_rate": "3000", "active": "0"})
    assert b"Net Worth Certificate" not in a.get("/billing/new").data  # hidden ones are not suggested
    a.post(f"/billing/services/{sid}/delete")
    with world["app"].app_context():
        assert db.session.get(ServiceItem, sid) is None


# ------------------------------------------------------------------ filing imports
def test_gst_filing_import_monthly_and_quarterly_with_upsert(world):
    a = admin_web(world)
    t = a.get("/trackers/import/gst/template.xlsx")
    assert t.status_code == 200
    assert [c.value for c in load_workbook(io.BytesIO(t.data)).worksheets[0][1]][:6] == ["Client Code", "GSTIN", "PAN", "Client Name", "Return Type", "Period"]
    rows = [["Client Code", "GSTIN", "PAN", "Client Name", "Return Type", "Period", "Due Date", "Status", "Filed Date", "ARN"],
            ["", "03AABCA1234F1Z5", "", "", "GSTR-3B", "2026-10", "20-11-2026", "Filed", "18-11-2026", "AA123"],   # by GSTIN, monthly
            ["CL-0002", "", "", "", "CMP-08", "2026-Q2", "", "", "", ""],                                          # by code, quarterly, default due
            ["", "", "BBBCB2345G", "", "GSTR-1", "2026-Q2", "", "", "", ""],                                       # wrong period for a monthly return
            ["", "", "ZZZZZ0000Z", "", "GSTR-1", "2026-10", "", "", "", ""],                                       # unknown client
            ["CL-0001", "", "", "", "GSTR-1", "2026-10", "32-13-2026", "", "", ""]]                                # bad date
    r = a.post("/trackers/import/gst", {"file": (_xlsx(rows), "g.xlsx")}, content_type="multipart/form-data")
    assert b"2 added" in r.data and b"3 rows with problems" in r.data
    with world["app"].app_context():
        g1 = GstReturn.query.filter_by(period="2026-10").one()
        assert g1.status == "filed" and g1.arn == "AA123" and g1.filed_date == date(2026, 11, 18) and g1.due_date == date(2026, 11, 20)
        g2 = GstReturn.query.filter_by(period="2026-Q2").one()
        assert g2.status == "pending" and g2.due_date is not None and g2.client_id == world["ids"]["beta"]
    rows[1][7], rows[1][8] = "In Progress", ""
    r = a.post("/trackers/import/gst", {"file": (_xlsx(rows[:3]), "g.xlsx")}, content_type="multipart/form-data")
    assert b"0 added" in r.data and b"2 updated" in r.data
    with world["app"].app_context():
        assert GstReturn.query.count() == 2 and GstReturn.query.filter_by(period="2026-10").one().status == "in_progress"


def test_itr_and_tds_filing_import(world):
    a = admin_web(world)
    itr = [["Client Code", "PAN", "Client Name", "Assessment Year", "Form", "Due Date", "Status", "Filed Date", "Ack Number", "Refund Amount"],
           ["", "CCCPC3456H", "", "2026-27", "ITR-1", "", "", date(2026, 7, 20), 123456789012345, 1500]]
    r = a.post("/trackers/import/itr", {"file": (_xlsx(itr), "i.xlsx")}, content_type="multipart/form-data")
    assert b"1 added" in r.data
    tds = [["Client Code", "PAN", "Client Name", "Financial Year", "Quarter", "Form", "Due Date", "Status", "Filed Date", "TDS Deducted", "TDS Deposited", "Challan Number"],
           ["CL-0001", "", "", "2026-27", "q2", "26q", "", "Filed", "28/10/2026", "45,000", 45000, "CH1"]]
    r = a.post("/trackers/import/tds", {"file": (_xlsx(tds), "t.xlsx")}, content_type="multipart/form-data")
    assert b"1 added" in r.data
    with world["app"].app_context():
        i = ItrFiling.query.one()
        assert i.status == "filed" and i.ack_number == "123456789012345" and i.refund_amount == 1500 and i.filed_date == date(2026, 7, 20)
        t = TdsReturn.query.one()
        assert t.quarter == "Q2" and t.form_type == "26Q" and t.tds_deducted == 45000 and t.filed_date == date(2026, 10, 28)
    assert a.get("/trackers/import/itr/template.xlsx").status_code == 200 and a.get("/trackers/import/tds/template.xlsx").status_code == 200
    e = Web(world["app"]); e.login("emp1@firm.in")
    assert e.get("/trackers/import/gst").status_code == 403
    assert b"Import from Excel" in a.get("/gst").data and b"Import from Excel" in a.get("/tds").data


# ------------------------------------------------------------------ counts
def test_counts_in_filters(world):
    a = admin_web(world)
    with world["app"].app_context():
        rid = GstReturnType.query.filter_by(frequency="monthly").first().id
    a.post("/gst/bulk", {"return_type_id": rid, "period": "2026-10"})
    page = a.get("/gst").data
    assert b"All statuses (2)" in page and b"Pending (2)" in page and b"Filed (0)" in page
    c = a.get("/clients/").data
    assert b"All statuses (3)" in c and b"Active (3)" in c and b'data-total="3"' in c
    assert b"All statuses (0)" in a.get("/billing/").data


# ------------------------------------------------------------------ messaging
def test_templates_are_formatted_and_old_ones_upgraded(app):
    from audit_manager.services.whatsapp import OLD_BODIES, seed_templates
    with app.app_context():
        t = WhatsAppTemplate.query.filter_by(name="Due date alert").one()
        assert t.body.count("\n\n") >= 3 and "Regards," in t.body and "*{due_date}*" in t.body
        t.body = OLD_BODIES["Due date alert"][1]
        mine = WhatsAppTemplate.query.filter_by(name="Return filed").one(); mine.body = "My own wording {client_name}"
        db.session.commit()
        seed_templates(); db.session.commit()
        assert "Regards," in WhatsAppTemplate.query.filter_by(name="Due date alert").one().body
        assert WhatsAppTemplate.query.filter_by(name="Return filed").one().body == "My own wording {client_name}"  # edited ones are left alone


def test_due_date_master_options(world):
    with world["app"].app_context():
        opts = wa.due_date_options(date(2026, 11, 15))
        labels = [o["label"] for o in opts]
        assert "GSTR-3B - 20-Nov-2026" in labels and any(l.startswith("TDS Return - 31-Oct-2026") for l in labels)
        o = next(o for o in opts if o["label"].startswith("GSTR-3B"))
        assert o["period"] == "GSTR-3B for Oct 2026" and o["due_date"] == "20-Nov-2026"
    page = admin_web(world).get("/whatsapp/").data
    assert b'id="dueMaster"' in page and b"field-chip" in page and b'draggable="true"' in page and b'data-work="GSTR-3B (monthly)"' in page


def test_bulk_email_from_compose(world, monkeypatch):
    a = admin_web(world)
    r = a.post("/whatsapp/compose", {"channel": "email", "subject": "Hi", "body": "x", "client_ids": [world["ids"]["apex"]]}, follow_redirects=True)
    assert b"Email is not set up" in r.data
    sent = []

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
    a.post("/settings/mail", {"mail_enabled": "1", "mail_host": "smtp.x.in", "mail_port": "587", "mail_from_address": "ca@x.in"})
    r = a.post("/whatsapp/compose", {"channel": "email", "subject": "Due date - {period}", "period": "GSTR-3B for Oct 2026", "due_date": "20-Nov-2026",
                                      "body": "Dear {client_name},\n\nYour *{period}* is due on *{due_date}*.\n\nRegards,\n{firm_name}",
                                      "client_ids": [world["ids"]["apex"], world["ids"]["beta"]]}, follow_redirects=True)
    assert b"1 email(s) sent" in r.data and b"1 skipped" in r.data  # Beta has no email
    m = sent[0]
    assert m["To"] == "apex@example.in" and m["Subject"] == "Due date - GSTR-3B for Oct 2026"
    plain = m.get_body(("plain",)).get_content(); html = m.get_body(("html",)).get_content()
    assert "Your GSTR-3B for Oct 2026 is due on 20-Nov-2026." in plain and "*" not in plain and "Dear Apex Precision," in plain
    assert "<b>20-Nov-2026</b>" in html and html.count("<p") == 3 and "Regards,<br>Sharma &amp; Associates" in html
    with world["app"].app_context():
        row = WhatsAppMessage.query.one()
        assert row.channel == "email" and row.status == "opened" and row.subject.startswith("Due date")
    assert b"Email" in a.get("/whatsapp/history").data


def test_invoice_can_be_sent_by_whatsapp(world):
    a = admin_web(world)
    a.post("/billing/new", {"client_id": world["ids"]["apex"], "tax_mode": "cgst_sgst", "invoice_date": "2026-11-01", "due_date": "2026-11-30",
                            "description": ["Audit fee"], "quantity": ["1"], "rate": ["10000"], "sac_code": ["998221"]})
    with world["app"].app_context():
        iid = Invoice.query.one().id
    assert b"bi-whatsapp" in a.get(f"/billing/{iid}").data
    r = a.post(f"/billing/{iid}/whatsapp", follow_redirects=True)
    assert b"web.whatsapp.com/send?phone=919876543210" in r.data
    with world["app"].app_context():
        m = WhatsAppMessage.query.one()
        assert "Invoice No.: *SA/" in m.body and "Rs. 11,800.00" in m.body and "30-Nov-2026" in m.body and m.body.count("\n") >= 8
