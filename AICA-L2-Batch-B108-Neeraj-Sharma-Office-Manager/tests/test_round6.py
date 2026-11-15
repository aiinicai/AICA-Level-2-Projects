import io
from datetime import date, datetime, timedelta

from PIL import Image

from conftest import Web, admin_web
from audit_manager.models import GstReturn, WhatsAppMessage, WhatsAppTemplate, db


def _png(color=(200, 30, 30)):
    buf = io.BytesIO(); Image.new("RGB", (300, 300), color).save(buf, "PNG"); buf.seek(0)
    return buf


def _jpg():
    buf = io.BytesIO(); Image.new("RGB", (300, 200), (10, 120, 60)).save(buf, "JPEG"); buf.seek(0)
    return buf


def test_template_picture_goes_with_whatsapp_and_email(world, monkeypatch):
    from audit_manager.services import whatsapp as wa
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
    ids = world["ids"]
    a = admin_web(world)
    r = a.post("/whatsapp/templates", {"name": "Diwali greeting", "category": "general", "body": "Dear {client_name},\n\nHappy Diwali!\n\nRegards,\n{firm_name}",
                                        "image": (io.BytesIO(b"<svg onload=alert(1)>"), "x.png")}, content_type="multipart/form-data", follow_redirects=True)
    assert b"not a valid PNG or JPG" in r.data
    a.post("/whatsapp/templates", {"name": "Diwali greeting", "category": "general", "body": "Dear {client_name},\n\nHappy Diwali!\n\nRegards,\n{firm_name}",
                                   "image": (_png(), "diwali.png")}, content_type="multipart/form-data")
    with world["app"].app_context():
        t = WhatsAppTemplate.query.filter_by(name="Diwali greeting").one()
        tid, pic = t.id, t.image
        assert pic and pic.endswith(".png")
    img = a.get(f"/whatsapp/picture/{pic}")
    assert img.status_code == 200 and img.data[:4] == b"\x89PNG"
    assert a.get("/whatsapp/picture/..%2F..%2Fauditmanager.db").status_code == 404
    assert Web(world["app"]).get(f"/whatsapp/picture/{pic}").status_code == 302  # needs sign-in
    assert pic.encode() in a.get("/whatsapp/").data and pic.encode() in a.get("/whatsapp/templates").data
    # WhatsApp: the queued message carries the picture and the queue offers to copy it
    a.post("/whatsapp/compose", {"channel": "whatsapp", "template_id": tid, "use_template_image": "1", "body": "Dear {client_name},\n\nHappy Diwali!",
                                 "client_ids": [ids["apex"]]}, content_type="multipart/form-data")
    with world["app"].app_context():
        assert WhatsAppMessage.query.one().image == pic
    q = a.get("/whatsapp/queue").data
    assert b"copy-pic" in q and pic.encode() in q and b"Ctrl" in q
    # unticked: no picture
    a.post("/whatsapp/compose", {"channel": "whatsapp", "template_id": tid, "body": "Plain", "client_ids": [ids["apex"]]}, content_type="multipart/form-data")
    # a one-off upload wins over the template picture
    a.post("/whatsapp/compose", {"channel": "whatsapp", "template_id": tid, "use_template_image": "1", "body": "Own", "client_ids": [ids["apex"]],
                                 "image": (_jpg(), "own.jpg")}, content_type="multipart/form-data")
    with world["app"].app_context():
        rows = WhatsAppMessage.query.order_by(WhatsAppMessage.id).all()
        assert rows[1].image is None and rows[2].image.endswith(".jpg") and rows[2].image != pic
    # Email: attached straight away, and also when scheduled
    a.post("/settings/mail", {"mail_enabled": "1", "mail_host": "smtp.x.in", "mail_port": "587", "mail_from_address": "ca@x.in"})
    a.post("/whatsapp/compose", {"channel": "email", "subject": "Happy Diwali", "template_id": tid, "use_template_image": "1", "body": "Dear {client_name},\n\nHappy Diwali!",
                                 "client_ids": [ids["apex"]]}, content_type="multipart/form-data")
    atts = list(sent[0].iter_attachments())
    assert len(atts) == 1 and atts[0].get_content_type() == "image/png" and atts[0].get_payload(decode=True)[:4] == b"\x89PNG"
    later = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    a.post("/whatsapp/compose", {"channel": "email", "subject": "Later", "template_id": tid, "use_template_image": "1", "body": "x", "send_at": later,
                                 "client_ids": [ids["apex"]]}, content_type="multipart/form-data")
    with world["app"].app_context():
        assert wa.send_scheduled(datetime.now() + timedelta(days=2)) == 1
    assert [x.get_content_type() for x in sent[1].iter_attachments()] == ["image/png"]
    # remove the picture from the template
    a.post("/whatsapp/templates", {"id": tid, "name": "Diwali greeting", "category": "general", "body": "Hi", "remove_image": "1"}, content_type="multipart/form-data")
    with world["app"].app_context():
        assert db.session.get(WhatsAppTemplate, tid).image is None


def test_gst_filing_history_from_portal(world, monkeypatch):
    from audit_manager.services import lookup
    ids = world["ids"]
    calls = []

    class Resp:
        def __init__(self, content=b"", data=None): self.content, self._d, self.headers = content, data, {"Content-Type": "image/png"}
        def raise_for_status(self): pass
        def json(self): return self._d

    class FakeSession:
        def __init__(self): self.headers = {}
        def get(self, url, **k): return Resp(content=b"PNG")
        def post(self, url, json=None, **k):
            calls.append(url.rsplit("/", 1)[-1])
            if url.endswith("taxpayerDetails"):
                if json["captcha"] == "bad":
                    return Resp(data={"errorCode": "SWEB_9000", "message": "Enter valid Letters shown"})
                return Resp(data={"lgnm": "APEX", "sts": "Active"})
            return Resp(data={"filingStatus": [[
                {"fy": "2026-2027", "taxp": "October", "mof": "ONLINE", "dof": "18/11/2026", "rtntype": "GSTR3B", "arn": "AA0311260000001", "status": "Filed"},
                {"fy": "2026-2027", "taxp": "October", "mof": "ONLINE", "dof": "10/11/2026", "rtntype": "GSTR1", "arn": "AA0311260000002", "status": "Filed"},
                {"fy": "2025-2026", "taxp": "January", "mof": "ONLINE", "dof": "19/02/2026", "rtntype": "GSTR3B", "arn": "AA0302260000003", "status": "Filed"},
                {"fy": "2025-2026", "taxp": "Annual", "mof": "ONLINE", "dof": "20/12/2026", "rtntype": "GSTR9", "arn": "AA0312260000004", "status": "Filed"},
                {"fy": "2026-2027", "taxp": "November", "mof": "", "dof": "", "rtntype": "GSTR3B", "arn": "", "status": "Not Filed"},
                {"fy": "2026-2027", "taxp": "October", "mof": "ONLINE", "dof": "12/11/2026", "rtntype": "GSTR2X", "arn": "X", "status": "Filed"}]]})
    monkeypatch.setattr(lookup.requests, "Session", FakeSession)
    a = admin_web(world)
    assert b"Fetch GST filing history" in a.get(f"/clients/{ids['apex']}").data
    assert b"Fetch GST filing history" not in a.get(f"/clients/{ids['charlie']}").data  # no GSTIN
    hdr = {"X-CSRF-Token": a.token()}
    a.get("/lookup/gst/captcha")
    d = a.c.post("/lookup/gst/history", json={"client_id": ids["apex"], "captcha": "bad"}, headers=hdr).get_json()
    assert d["ok"] is False and d["captcha"] is True
    a.get("/lookup/gst/captcha")
    d = a.c.post("/lookup/gst/history", json={"client_id": ids["apex"], "captcha": "ab12"}, headers=hdr).get_json()
    assert d["ok"] and d["created"] == 4 and d["skipped"] == 2 and d["unknown_types"] == ["GSTR2X"]
    assert calls[-2:] == ["taxpayerDetails", "taxpayerReturnDetails"]
    with world["app"].app_context():
        rows = {(r.return_type.name, r.period): r for r in GstReturn.query.filter_by(client_id=ids["apex"])}
        assert set(rows) == {("GSTR-3B", "2026-10"), ("GSTR-1", "2026-10"), ("GSTR-3B", "2026-01"), ("GSTR-9", "2025-26")}
        r = rows[("GSTR-3B", "2026-10")]
        assert r.status == "filed" and r.filed_date == date(2026, 11, 18) and r.arn == "AA0311260000001" and r.due_date == date(2026, 11, 20)
    a.get("/lookup/gst/captcha")
    d = a.c.post("/lookup/gst/history", json={"client_id": ids["apex"], "captcha": "ab12"}, headers=hdr).get_json()
    assert d["created"] == 0 and d["updated"] == 4  # fetching again never duplicates
    other = Web(world["app"]); other.login("emp2@firm.in")
    assert other.c.post("/lookup/gst/history", json={"client_id": ids["apex"], "captcha": "x"}, headers={"X-CSRF-Token": other.token()}).status_code == 403
    # the other reply style some GST systems use
    alt = lookup.parse_filings({"EFiledlist": [{"arn": "A1", "ret_prd": "022026", "dof": "09-03-2026", "rtntype": "GSTR1", "status": "Filed"}]})
    assert alt == [{"type": "GSTR1", "year": 2026, "month": 2, "filed": date(2026, 3, 9), "arn": "A1", "status": "Filed"}]
