import io
from datetime import date, timedelta

from openpyxl import Workbook

from conftest import Web, admin_web
from audit_manager.models import DueDate, GstReturn, GstReturnType, ItrFiling, TdsReturn, WhatsAppMessage, WhatsAppTemplate, db
from audit_manager.services import whatsapp as wa


def test_type_of_work_and_period_in_messages(world):
    ids = world["ids"]
    a = admin_web(world)
    page = a.get("/whatsapp/").data
    assert b'name="work_type"' in page and b"GST Return" in page and b"Income Tax Return" in page and b"Type of work" in page
    with world["app"].app_context():
        body = WhatsAppTemplate.query.filter_by(name="Due date alert").one().body
        assert "Type of work: *{work_type}*" in body and "Period: *{period}*" in body
    a.post("/whatsapp/compose", {"channel": "whatsapp", "body": body, "work_type": "GST Return", "period": "Oct 2026", "due_date": "20-Nov-2026",
                                 "client_ids": [ids["apex"]]}, content_type="multipart/form-data")
    a.post("/whatsapp/compose", {"channel": "whatsapp", "body": body, "work_type": "Income Tax Return", "period": "", "due_date": "",
                                 "client_ids": [ids["apex"]]}, content_type="multipart/form-data")
    with world["app"].app_context():
        first, second = [m.body for m in WhatsAppMessage.query.order_by(WhatsAppMessage.id)]
        assert "Type of work: *GST Return*\nPeriod: *Oct 2026*\nDue date: *20-Nov-2026*" in first
        assert "Type of work: *Income Tax Return*" in second and "Period:" not in second and "Due date:" not in second  # empty fields leave no gaps
        assert "\n\n\n" not in second and second.startswith("Dear Apex Precision,")
        # label-only lines go; ordinary sentences ending in a colon stay
        assert wa.render("Details:\n\nAmount due: *Rs. {amount}*\nInvoice No.: *{invoice_number}*\nNote: fine") == "Details:\n\nNote: fine"


def test_itr_verification_status_date_and_deadline(world):
    ids = world["ids"]
    a = admin_web(world)
    a.post("/itr/bulk", {"assessment_year": "2026-27", "form_type": "ITR-1"})
    with world["app"].app_context():
        rid = ItrFiling.query.filter_by(client_id=ids["charlie"]).one().id
    filed = date.today() - timedelta(days=10)
    a.post(f"/itr/{rid}/update", {"status": "filed", "filed_date": str(filed), "ack_number": "123", "verification_status": ""})
    page = a.get("/itr").data
    assert b"Verify by" in page and b"ITR-V sent by post" in page and b"e-Verified" in page
    with world["app"].app_context():
        r = db.session.get(ItrFiling, rid)
        assert r.verification_status is None and r.verify_by == filed + timedelta(days=30)
    a.post(f"/itr/{rid}/update", {"status": "filed", "filed_date": str(filed), "verification_status": "itrv_sent", "verification_date": str(filed + timedelta(days=2))})
    with world["app"].app_context():
        r = db.session.get(ItrFiling, rid)
        assert r.verification_status == "itrv_sent" and r.verification_date == filed + timedelta(days=2) and r.verify_by is not None  # posted, not yet received
    a.post(f"/itr/{rid}/update", {"status": "filed", "filed_date": str(filed), "verification_status": "e_verified"})
    with world["app"].app_context():
        r = db.session.get(ItrFiling, rid)
        assert r.verification_status == "e_verified" and r.verification_date == date.today() and r.verify_by is None
    assert b"Verified" in a.get("/itr").data
    csv = a.get("/reports/export.csv?type=itr_status").data.decode("utf-8-sig")
    assert "Verification,Verified On" in csv and "e-Verified" in csv
    # Excel import carries verification too
    wb = Workbook(); ws = wb.active
    ws.append(["Client Code", "PAN", "Assessment Year", "Form", "Status", "Filed Date", "Ack Number", "Verification", "Verification Date"])
    ws.append(["", "AABCA1234F", "2025-26", "ITR-6", "Filed", "20-10-2025", "999", "ITR-V sent by post", "25-10-2025"])
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    a.post("/trackers/import/itr", {"file": (buf, "i.xlsx")}, content_type="multipart/form-data")
    with world["app"].app_context():
        r = ItrFiling.query.filter_by(assessment_year="2025-26").one()
        assert r.verification_status == "itrv_sent" and r.verification_date == date(2025, 10, 25)


def test_due_dates_can_be_extended(world):
    ids = world["ids"]
    a = admin_web(world)
    # 1) in the master, keeping the original on record
    with world["app"].app_context():
        d = DueDate.query.filter_by(title="GSTR-9 / GSTR-9C annual return").one()
        did, total = d.id, DueDate.query.count()
    assert b"Extend this due date" in a.get(f"/calendar/due-dates?extend={did}").data
    a.post("/calendar/due-dates", {"action": "extend", "id": did, "new_date": "2027-01-31", "notes": "CBIC notification"})
    with world["app"].app_context():
        d = db.session.get(DueDate, did)
        assert d.due_date == date(2027, 1, 31) and d.original_date == date(2026, 12, 31) and d.notes == "CBIC notification"
    assert b"Extended" in a.get("/calendar/due-dates").data and b"Originally 31 Dec 2026" in a.get("/calendar/due-dates").data
    a.post("/calendar/due-dates", {"action": "load_standard"})
    with world["app"].app_context():
        assert DueDate.query.count() == total  # loading standard dates does not bring the old date back
    # 2) for the returns being tracked: all unfiled ones of that period
    with world["app"].app_context():
        rt = GstReturnType.query.filter_by(frequency="monthly").first().id
    a.post("/gst/bulk", {"return_type_id": rt, "period": "2026-10"})
    with world["app"].app_context():
        apex = GstReturn.query.filter_by(client_id=ids["apex"]).one(); beta = GstReturn.query.filter_by(client_id=ids["beta"]).one()
        apex_id, beta_id, old_due = apex.id, beta.id, apex.due_date
    a.post(f"/gst/{apex_id}/update", {"status": "filed"})
    r = a.post("/trackers/extend/gst", {"return_type_id": rt, "period": "2026-10", "new_date": "2026-11-30"}, follow_redirects=True)
    assert b"for 1 return(s) not yet filed" in r.data
    with world["app"].app_context():
        assert db.session.get(GstReturn, beta_id).due_date == date(2026, 11, 30) and db.session.get(GstReturn, apex_id).due_date == old_due
    # 3) for one client only, from the row itself
    a.post(f"/gst/{beta_id}/update", {"status": "pending", "due_date": "2026-12-05"})
    with world["app"].app_context():
        assert db.session.get(GstReturn, beta_id).due_date == date(2026, 12, 5)
    a.post("/itr/bulk", {"assessment_year": "2026-27", "form_type": "ITR-1"})
    a.post("/trackers/extend/itr", {"assessment_year": "2026-27", "new_date": "2026-09-15"})
    a.post("/tds/bulk", {"financial_year": "2026-27", "quarter": "Q3", "form_type": "26Q"})
    a.post("/trackers/extend/tds", {"financial_year": "2026-27", "quarter": "Q3", "new_date": "2027-02-15"})
    with world["app"].app_context():
        assert {r.due_date for r in ItrFiling.query.all()} == {date(2026, 9, 15)} and TdsReturn.query.one().due_date == date(2027, 2, 15)
    e = Web(world["app"]); e.login("emp1@firm.in")
    assert e.post("/trackers/extend/gst", {"return_type_id": rt, "period": "2026-10", "new_date": "2027-01-01"}).status_code == 403
    for url in ("/gst", "/itr", "/tds"):
        assert b"Due date extended by the department?" in a.get(url).data


def test_help_has_a_picture_for_every_section(world):
    from pathlib import Path

    import audit_manager
    from audit_manager.help_content import GROUPS
    e = Web(world["app"]); e.login("emp1@firm.in")   # every user can open Help
    page = e.get("/help")
    assert page.status_code == 200 and b"Help - how to use Office Manager" in page.data and b'href="/help"' in e.get("/").data
    folder = Path(audit_manager.__file__).parent / "static" / "help"
    count = 0
    for _group, sections in GROUPS:
        for sid, title, pic, _intro, steps in sections:
            f = folder / f"{pic}.jpg"
            assert f.exists() and f.stat().st_size > 15000, pic
            assert steps and f'id="{sid}"'.encode() in page.data and f"help/{pic}.jpg".encode() in page.data
            assert e.get(f"/static/help/{pic}.jpg").status_code == 200
            count += 1
    assert count == len(list(folder.glob("*.jpg"))) == 39  # no picture without text, no text without a picture
    for word in (b"Fetch", b"Extend", b"e-Verified", b"Ctrl + V", b"Type of work", b"error.log"):
        assert word in page.data


def test_contact_person_with_designation_master(world):
    ids = world["ids"]
    a = admin_web(world)
    page = a.get("/clients/new").data
    assert b'name="contact_person"' in page and b"<option >Director</option>" in page and b"Karta" in page
    a.post("/settings/designations", {"designations": "Proprietor\nDirector\nCFO\n\ncfo\n  Company Secretary  "})
    page = a.get("/clients/new").data
    assert b"CFO" in page and b"Company Secretary" in page and b"Karta" not in page and page.count(b">CFO<") == 1  # duplicates and blanks dropped
    assert b"Designation master" in a.get("/settings/").data
    a.post(f"/clients/{ids['apex']}/edit", {"name": "Apex Precision", "pan": "AABCA1234F", "gstin": "03AABCA1234F1Z5", "mobile": "9876543210",
                                           "contact_person": "Rajesh Kumar", "contact_designation": "CFO", "is_itr_applicable": "1"})
    assert b"Rajesh Kumar" in a.get(f"/clients/{ids['apex']}").data and b"(CFO)" in a.get(f"/clients/{ids['apex']}").data
    a.post("/settings/designations", {"designations": "Proprietor\nDirector"})   # CFO removed from the master
    edit = a.get(f"/clients/{ids['apex']}/edit").data
    assert b"<option selected>CFO</option>" in edit  # the client keeps the designation already given
    assert "Rajesh Kumar (CFO)" in a.get("/reports/export.csv?type=client_register").data.decode("utf-8-sig")
    # usable in messages; falls back to the client's name when no contact person is recorded
    a.post("/whatsapp/compose", {"channel": "whatsapp", "body": "Dear {contact_person},\n\nRegarding {client_name}.", "client_ids": [ids["apex"]]}, content_type="multipart/form-data")
    with world["app"].app_context():
        from audit_manager.models import Client
        assert WhatsAppMessage.query.one().body.startswith("Dear Rajesh Kumar,\n\nRegarding Apex Precision.")
        db.session.get(Client, ids["beta"]).mobile = "9822222222"; db.session.commit()
    a.post("/whatsapp/compose", {"channel": "whatsapp", "body": "Dear {contact_person},", "client_ids": [ids["beta"]]}, content_type="multipart/form-data")
    with world["app"].app_context():
        assert WhatsAppMessage.query.order_by(WhatsAppMessage.id.desc()).first().body == "Dear Beta Traders,"
    # Excel import carries both columns
    wb = Workbook(); ws = wb.active
    ws.append(["Name", "PAN", "Contact Person", "Designation"]); ws.append(["Imported With Contact", "IMPCP1111A", "Sunita Rani", "Partner"])
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    a.post("/clients/import", {"file": (buf, "c.xlsx")}, content_type="multipart/form-data")
    with world["app"].app_context():
        from audit_manager.models import Client
        c = Client.query.filter_by(name="Imported With Contact").one()
        assert c.contact_person == "Sunita Rani" and c.contact_designation == "Partner"


def test_arn_and_acknowledgement_numbers_on_all_three_trackers(world):
    ids = world["ids"]
    a = admin_web(world)
    with world["app"].app_context():
        rt = GstReturnType.query.filter_by(frequency="monthly").first().id
    a.post("/gst/bulk", {"return_type_id": rt, "period": "2026-10"}); a.post("/itr/bulk", {"assessment_year": "2026-27", "form_type": "ITR-1"})
    a.post("/tds/bulk", {"financial_year": "2026-27", "quarter": "Q2", "form_type": "26Q"})
    with world["app"].app_context():
        g, i, t = GstReturn.query.first().id, ItrFiling.query.first().id, TdsReturn.query.one().id
    a.post(f"/gst/{g}/update", {"status": "filed", "arn": "AA0311260001234"})
    a.post(f"/itr/{i}/update", {"status": "filed", "ack_number": "412345670311226"})
    a.post(f"/tds/{t}/update", {"status": "filed", "ack_number": "770000123456789", "challan_number": "CH1", "tds_deducted": "1000", "tds_deposited": "1000"})
    with world["app"].app_context():
        assert db.session.get(GstReturn, g).arn == "AA0311260001234" and db.session.get(ItrFiling, i).ack_number == "412345670311226"
        assert db.session.get(TdsReturn, t).ack_number == "770000123456789"
    page = a.get("/tds").data
    assert b'name="ack_number"' in page and b"770000123456789" in page
    assert "770000123456789" in a.get("/reports/export.csv?type=tds_status").data.decode("utf-8-sig")
    # and in bulk from Excel: the same file updates the number on an existing row
    wb = Workbook(); ws = wb.active
    ws.append(["Client Code", "Financial Year", "Quarter", "Form", "Status", "Ack Number"]); ws.append(["CL-0001", "2026-27", "Q2", "26Q", "Filed", "880000999999999"])
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    r = a.post("/trackers/import/tds", {"file": (buf, "t.xlsx")}, content_type="multipart/form-data")
    assert b"1 updated" in r.data
    with world["app"].app_context():
        assert db.session.get(TdsReturn, t).ack_number == "880000999999999"
