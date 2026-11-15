import io
from datetime import date, datetime, timedelta
from pathlib import Path

from conftest import Web, admin_web
from audit_manager.models import Client, DueDate, FirmSetting, GstReturn, GstReturnType, Invoice, Task, TimeEntry, WhatsAppMessage, WhatsAppTemplate, db


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


def test_calendar_shows_due_date_master_tasks_and_click_to_add(world):
    a = admin_web(world)
    with world["app"].app_context():
        db.session.add(DueDate(title="Office audit deadline", due_date=date(2027, 1, 9), category="other"))
        db.session.commit()
    page = a.get("/calendar/?year=2027&month=1").data
    assert b"chip master" in page and b"Office audit deadline" in page and b"GSTR-3B (monthly)" in page
    assert b'data-date="2027-01-09"' in page and b'id="taskModal"' in page
    r = a.post("/tasks/add", {"title": "Call client for papers", "due_date": "2027-01-09", "back": "calendar", "priority": "high"})
    assert r.status_code == 302 and "/calendar/" in r.headers["Location"] and "month=1" in r.headers["Location"] and "year=2027" in r.headers["Location"]
    assert b"Call client for papers" in a.get("/calendar/?year=2027&month=1").data
    assert a.post("/tasks/add", {"title": "Plain"}).headers["Location"].endswith("/tasks/")


def test_event_based_messages(world, monkeypatch):
    from audit_manager.services import automation, whatsapp as wa
    sent = []
    _smtp(monkeypatch, sent)
    ids = world["ids"]
    a = admin_web(world)
    page = a.get("/whatsapp/automation").data
    assert b"A return is marked as Filed" in page and b"Edit wording" in page
    with world["app"].app_context():
        rid = GstReturnType.query.filter_by(frequency="monthly").first().id
    a.post("/gst/bulk", {"return_type_id": rid, "period": "2026-10"})
    with world["app"].app_context():
        row_id = GstReturn.query.filter_by(client_id=ids["apex"]).one().id
    a.post(f"/gst/{row_id}/update", {"status": "filed"})
    with world["app"].app_context():
        assert WhatsAppMessage.query.count() == 0  # nothing is switched on yet
    a.post(f"/gst/{row_id}/update", {"status": "pending"})
    a.post("/settings/mail", {"mail_enabled": "1", "mail_host": "smtp.x.in", "mail_port": "587", "mail_from_address": "ca@x.in"})
    a.post("/whatsapp/automation", {"return_filed_whatsapp": "1", "return_filed_email": "1", "invoice_created_email": "1",
                                    "payment_received_whatsapp": "1", "task_assigned_whatsapp": "1", "due_reminder_whatsapp": "1", "auto_due_days": "5"})
    a.post(f"/gst/{row_id}/update", {"status": "filed"})
    a.post(f"/gst/{row_id}/update", {"status": "filed", "arn": "AA1"})  # already filed: no second message
    with world["app"].app_context():
        msgs = WhatsAppMessage.query.order_by(WhatsAppMessage.id).all()
        assert [(m.channel, m.status, m.source) for m in msgs] == [("whatsapp", "queued", "auto"), ("email", "scheduled", "auto")]
        assert "has been filed successfully" in msgs[0].body and "2026-10" in msgs[0].body and "Dear Apex Precision," in msgs[0].body
        assert wa.send_scheduled(datetime.now() + timedelta(minutes=1)) == 1 and sent[0]["To"] == "apex@example.in"
    # invoice created -> email with the PDF attached
    a.post("/billing/new", {"client_id": ids["apex"], "tax_mode": "cgst_sgst", "invoice_date": "2026-11-01", "description": ["Audit"], "quantity": ["1"], "rate": ["1000"], "sac_code": [""]})
    assert len(sent) == 2 and sent[1].get_content_type() == "multipart/mixed"
    names = [p.get_filename() for p in sent[1].iter_attachments()]
    assert names and names[0].endswith(".pdf") and "Invoice raised" in sent[1]["Subject"]
    with world["app"].app_context():
        iid = Invoice.query.one().id
    a.post(f"/billing/{iid}/payment", {"amount": "500", "mode": "upi"})
    a.post("/tasks/add", {"title": "Prepare 3CD", "assigned_to_id": ids["emp1"], "due_date": "2026-12-01"})
    with world["app"].app_context():
        from audit_manager.models import User
        db.session.get(User, ids["emp1"]).phone = "9811111111"; db.session.commit()
    a.post("/tasks/add", {"title": "Prepare 3CB", "assigned_to_id": ids["emp1"], "due_date": "2026-12-01"})
    with world["app"].app_context():
        bodies = [m.body for m in WhatsAppMessage.query.filter_by(channel="whatsapp").order_by(WhatsAppMessage.id)]
        assert any("receipt of *Rs. 500.00*" in b for b in bodies) and any("Prepare 3CB" in b and "Dear Emp1" in b for b in bodies)
        assert not any("Prepare 3CD" in b for b in bodies)  # no phone at that time, so nothing was queued
        # due reminders: once per filing, only inside the window
        beta = GstReturn.query.filter_by(client_id=ids["beta"]).one()
        beta.due_date = date.today() + timedelta(days=4)
        db.session.get(Client, ids["beta"]).mobile = "9822222222"
        db.session.commit()
        assert automation.run_due_reminders() == 1 and automation.run_due_reminders() == 0
        last = WhatsAppMessage.query.order_by(WhatsAppMessage.id.desc()).first()
        assert "due shortly" in last.body and "Dear Beta Traders," in last.body
        beta.due_date = date.today() + timedelta(days=20); db.session.commit()
        assert automation.run_due_reminders() == 0


def test_client_wise_hourly_rate_wins(world):
    ids = world["ids"]
    a = admin_web(world)
    a.post("/settings/office", {"profession": "ca", "hourly_billing": "1", "default_hourly_rate": "1000"})
    assert b"Hourly billing rate for this client" in a.get(f"/clients/{ids['apex']}/edit").data
    a.post(f"/clients/{ids['apex']}/edit", {"name": "Apex Precision", "pan": "AABCA1234F", "gstin": "03AABCA1234F1Z5", "mobile": "9876543210",
                                           "email": "apex@example.in", "hourly_rate": "3500", "assigned_to_id": ids["emp1"], "is_itr_applicable": "1"})
    a.post("/time/rates", {"default_hourly_rate": "1000", f"rate_{ids['emp1']}": "1200", f"rate_{ids['emp2']}": "1500"})
    e1 = Web(world["app"]); e1.login("emp1@firm.in"); e1.post("/time/add", {"client_id": ids["apex"], "hours": "1"})
    e2 = Web(world["app"]); e2.login("emp2@firm.in"); e2.post("/time/add", {"client_id": ids["beta"], "hours": "1"})
    with world["app"].app_context():
        assert TimeEntry.query.filter_by(client_id=ids["apex"]).one().rate == 3500   # the client's own rate
        assert TimeEntry.query.filter_by(client_id=ids["beta"]).one().rate == 1500   # no client rate: the staff rate
    a.post("/settings/office", {"profession": "ca"})  # switch hourly billing off
    assert b"Hourly billing rate for this client" not in a.get(f"/clients/{ids['apex']}/edit").data
    with world["app"].app_context():
        assert db.session.get(Client, ids["apex"]).hourly_rate == 3500  # an ordinary edit without the box does not wipe it


def test_invoice_preview_and_inline_pdf(world):
    a = admin_web(world)
    a.post("/billing/new", {"client_id": world["ids"]["apex"], "tax_mode": "cgst_sgst", "invoice_date": "2026-11-01", "due_date": "2026-11-30",
                            "description": ["Statutory Audit Fee"], "quantity": ["1"], "rate": ["10000"], "sac_code": ["998221"]})
    with world["app"].app_context():
        iid = Invoice.query.one().id
    assert b"Preview / Print" in a.get(f"/billing/{iid}").data
    page = a.get(f"/billing/{iid}/preview")
    assert page.status_code == 200
    for bit in (b"TAX INVOICE", b"Statutory Audit Fee", b"CGST @ 9%", b"11,800.00", b"Apex Precision", b"window.print()"):
        assert bit in page.data, bit
    r = a.get(f"/billing/{iid}/pdf?inline=1")
    assert r.data[:4] == b"%PDF" and "attachment" not in r.headers["Content-Disposition"]
    assert "attachment" in a.get(f"/billing/{iid}/pdf").headers["Content-Disposition"]


def test_desktop_window_saves_downloads_to_the_downloads_folder(world, tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    a = admin_web(world)
    for url, ext, magic in (("/reports/export.pdf?type=client_register", ".pdf", b"%PDF"), ("/reports/export.xlsx?type=client_register", ".xlsx", b"PK"),
                            ("/reports/export.csv?type=client_register", ".csv", b"\xef\xbb\xbf"), ("/settings/backup", ".zip", b"PK"),
                            ("/clients/import/template.xlsx", ".xlsx", b"PK")):
        d = a.get(url + ("&" if "?" in url else "?") + "save=1").get_json()
        assert d and d["ok"], url
        f = Path(d["path"])
        assert f.parent == tmp_path / "Downloads" and f.suffix == ext and f.read_bytes().startswith(magic), url
    first = a.get("/reports/export.pdf?type=client_register&save=1").get_json()["name"]
    assert "(1)" in first  # a second download never overwrites the first
    # another PC on the network never writes to the host's disk
    r = a.c.get("/reports/export.pdf?type=client_register&save=1", environ_base={"REMOTE_ADDR": "192.168.1.50"})
    assert r.data[:4] == b"%PDF"
    assert a.get("/reports/export.pdf?type=client_register").data[:4] == b"%PDF"  # normal download unchanged
