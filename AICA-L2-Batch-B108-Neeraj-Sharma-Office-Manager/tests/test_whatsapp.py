from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

from conftest import Web, admin_web
from audit_manager.models import Client, GstReturn, GstReturnType, WhatsAppMessage, WhatsAppTemplate, db
from audit_manager.services import whatsapp as wa


def test_phone_normalisation(app):
    with app.app_context():
        assert wa.normalize_phone("98765 43210") == "919876543210"
        assert wa.normalize_phone("098765-43210") == "919876543210"
        assert wa.normalize_phone("+91 98765 43210") == "919876543210"
        assert wa.normalize_phone("919876543210") == "919876543210"
        assert wa.normalize_phone("+44 7911 123456") == "447911123456"
        assert wa.normalize_phone("12345") is None and wa.normalize_phone("") is None and wa.normalize_phone(None) is None


def test_links_encode_text():
    l = wa.links("919876543210", "Hi & bye?\nLine 2")
    q = parse_qs(urlparse(l["web"]).query)
    assert q["text"] == ["Hi & bye?\nLine 2"] and q["phone"] == ["919876543210"]
    assert l["desktop"].startswith("whatsapp://send?phone=919876543210&text=")


def test_render_is_safe_with_stray_braces(app):
    with app.app_context():
        assert wa.render("Hi {client_name}, {unknown} {", client_name="A") == "Hi {client_name}, {unknown} {"  # malformed: left as typed
        assert wa.render("Hi {client_name} {unknown}", client_name="A") == "Hi A {unknown}"
    assert wa.money(1234567.5) == "12,34,567.50"


def test_default_templates_seeded(app):
    with app.app_context():
        assert WhatsAppTemplate.query.count() >= 4


def test_bulk_send_and_skip_clients_without_number(world):
    w = admin_web(world)
    ids = world["ids"]
    r = w.post("/whatsapp/compose", {"audience": "client", "body": "Hello {client_name} from {firm_name}",
                                      "client_ids": [ids["apex"], ids["beta"]]}, follow_redirects=True)
    assert b"1 message(s) ready" in r.data and b"skipped" in r.data  # Beta has no mobile
    with world["app"].app_context():
        m = WhatsAppMessage.query.one()
        assert m.phone == "919876543210" and m.body == "Hello Apex Precision from Sharma & Associates" and m.status == "queued"
        mid = m.id
    q = w.get("/whatsapp/queue").data
    assert b"web.whatsapp.com/send?phone=919876543210" in q
    assert w.post(f"/whatsapp/{mid}/opened").status_code == 200
    with world["app"].app_context():
        assert db.session.get(WhatsAppMessage, mid).status == "opened"
    assert b"Hello Apex" in w.get("/whatsapp/history").data


def test_staff_messaging_is_manager_only(world):
    ids = world["ids"]
    with world["app"].app_context():
        from audit_manager.models import User
        db.session.get(User, ids["emp1"]).phone = "9811111111"
        db.session.commit()
    e = Web(world["app"]); e.login("emp2@firm.in")
    assert e.post("/whatsapp/compose", {"audience": "staff", "body": "x", "staff_ids": [ids["emp1"]]}).status_code == 403
    m = admin_web(world)
    m.post("/whatsapp/compose", {"audience": "staff", "body": "Hi {staff_name}", "staff_ids": [ids["emp1"]]})
    with world["app"].app_context():
        row = WhatsAppMessage.query.one()
        assert row.audience == "staff" and row.body == "Hi Emp1" and row.phone == "919811111111"


def test_employee_cannot_message_foreign_clients_or_see_others_queue(world):
    ids = world["ids"]
    with world["app"].app_context():
        db.session.get(Client, ids["beta"]).mobile = "9822222222"
        db.session.commit()
    e = Web(world["app"]); e.login("emp1@firm.in")
    e.post("/whatsapp/compose", {"audience": "client", "body": "Hi", "client_ids": [ids["beta"]]})  # Beta is emp2's client
    with world["app"].app_context():
        assert WhatsAppMessage.query.count() == 0
    a = admin_web(world)
    a.post("/whatsapp/compose", {"audience": "client", "body": "Hi", "client_ids": [ids["beta"]]})
    with world["app"].app_context():
        mid = WhatsAppMessage.query.one().id
    assert b"Hi" not in e.get("/whatsapp/queue").data.replace(b"History", b"").split(b"<tbody>")[1].split(b"</tbody>")[0]
    assert e.post(f"/whatsapp/{mid}/opened").status_code == 403


def test_templates_manager_only_and_unique(world):
    a = admin_web(world)
    a.post("/whatsapp/templates", {"name": "My tpl", "body": "Hello {client_name}"})
    a.post("/whatsapp/templates", {"name": "My tpl", "body": "dup"})
    with world["app"].app_context():
        assert WhatsAppTemplate.query.filter_by(name="My tpl").count() == 1
    e = Web(world["app"]); e.login("emp1@firm.in")
    assert e.get("/whatsapp/templates").status_code == 403


def test_auto_reminders_group_by_client_and_do_not_duplicate(world):
    w = admin_web(world)
    with world["app"].app_context():
        rt = GstReturnType.query.first()
        for per, due in (("2026-08", date.today() - timedelta(days=5)), ("2026-09", date.today() + timedelta(days=3)), ("2026-10", date.today() + timedelta(days=40))):
            db.session.add(GstReturn(client_id=world["ids"]["apex"], return_type_id=rt.id, period=per, due_date=due))
        db.session.add(GstReturn(client_id=world["ids"]["apex"], return_type_id=rt.id, period="2026-07", due_date=date.today() - timedelta(days=30), status="filed"))
        db.session.commit()
    page = w.get("/whatsapp/reminders?days=7").data
    assert b"2026-08" in page and b"2026-09" in page and b"2026-10" not in page and b"2026-07" not in page
    w.post("/whatsapp/reminders", {"days": 7, "client_ids": [world["ids"]["apex"]]})
    with world["app"].app_context():
        m = WhatsAppMessage.query.one()
        assert m.source == "reminder" and "1. " in m.body and "2. " in m.body and "Dear Apex Precision" in m.body
    w.post("/whatsapp/reminders", {"days": 7, "client_ids": [world["ids"]["apex"]]})
    with world["app"].app_context():
        assert WhatsAppMessage.query.count() == 1  # not queued twice
