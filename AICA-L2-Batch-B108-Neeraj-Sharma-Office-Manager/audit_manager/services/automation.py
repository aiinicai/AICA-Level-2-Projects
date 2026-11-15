"""Event-based messages: when something happens (a return is filed, an invoice is raised ...) the client gets a message without anyone
writing it. Emails go out by themselves. WhatsApp messages are placed in "WhatsApp ready to send", because WhatsApp needs a person to press Send."""
from datetime import date, datetime, timedelta

from ..models import AutoLog, FirmSetting, GstReturn, ItrFiling, TdsReturn, WhatsAppTemplate, db
from . import mailer
from . import whatsapp as wa

EVENTS = {
    "return_filed": ("A return is marked as Filed", "Auto: Return filed", "client"),
    "invoice_created": ("An invoice is created (the email carries the PDF)", "Auto: Invoice raised", "client"),
    "payment_received": ("A payment is recorded", "Auto: Payment received", "client"),
    "due_reminder": ("A filing that is not yet filed is coming due", "Auto: Due date reminder", "client"),
    "task_assigned": ("A task is given to a staff member", "Auto: Task assigned", "staff"),
}
TEMPLATES = {
    "Auto: Return filed": "Dear {client_name},\n\nWe are pleased to inform you that the following has been filed successfully:\n\n*{period}*\n\n"
                          "Thank you for your co-operation.\n\nRegards,\n{firm_name}\n{firm_phone}",
    "Auto: Invoice raised": "Dear {client_name},\n\nGreetings from {firm_name}.\n\nWe have raised the following invoice for our professional services:\n\n"
                            "Invoice No.: *{invoice_number}*\nAmount: *Rs. {amount}*\nDue date: {due_date}\n\n"
                            "Kindly arrange the payment at your convenience.\n\nRegards,\n{firm_name}\n{firm_phone}",
    "Auto: Payment received": "Dear {client_name},\n\nWe acknowledge with thanks the receipt of *Rs. {amount}* against invoice {invoice_number}.\n\n"
                              "Regards,\n{firm_name}\n{firm_phone}",
    "Auto: Due date reminder": "Dear {client_name},\n\nGreetings from {firm_name}.\n\nThis is a reminder that the following is due shortly:\n\n"
                               "Particulars: *{period}*\nDue date: *{due_date}*\n\nKindly share the pending details at the earliest to avoid late fees.\n\n"
                               "Regards,\n{firm_name}\n{firm_phone}",
    "Auto: Task assigned": "Dear {staff_name},\n\nA task has been assigned to you:\n\n*{period}*\nDue date: {due_date}\n\nRegards,\n{firm_name}",
}


def seed_templates() -> None:
    for name, body in TEMPLATES.items():
        if WhatsAppTemplate.query.filter_by(name=name).first() is None:
            db.session.add(WhatsAppTemplate(name=name, category="auto", body=body))


def is_on(event: str, channel: str) -> bool:
    return FirmSetting.get(f"auto_{event}_{channel}") == "1"


def due_days() -> int:
    try:
        return max(0, min(30, int(FirmSetting.get("auto_due_days") or 3)))
    except ValueError:
        return 3


def fire(event: str, *, client=None, staff=None, values: dict | None = None, attachments=None, user_id=None) -> dict:
    """Returns {'whatsapp': bool, 'email': bool} saying what was prepared."""
    done = {"whatsapp": False, "email": False}
    if event not in EVENTS or not (is_on(event, "whatsapp") or is_on(event, "email")):
        return done
    _label, tpl_name, _who = EVENTS[event]
    tpl = WhatsAppTemplate.query.filter_by(name=tpl_name).first()
    body_tpl = tpl.body if tpl else TEMPLATES[tpl_name]
    firm = FirmSetting.get("firm_name", "our office")
    values = {"firm_name": firm, **(values or {})}
    if client is not None:
        name, mobile, email, ids, aud = client.name, client.mobile, client.email, {"client_id": client.id}, "client"
        values.setdefault("client_name", client.name)
        values.setdefault("contact_person", client.contact_person or client.name)
    elif staff is not None:
        name, mobile, email, ids, aud = staff.name, staff.phone, staff.email, {"staff_id": staff.id}, "staff"
        values.setdefault("staff_name", staff.name)
    else:
        return done
    body = wa.render(body_tpl, **values)
    if is_on(event, "whatsapp") and wa.queue(aud, mobile, name, body, user_id, "auto", **ids):
        done["whatsapp"] = True
    if is_on(event, "email") and email and "@" in email and mailer.is_configured():
        subject = f"{tpl_name.replace('Auto: ', '')} - {firm}"
        if attachments:  # needs the file, so it is sent straight away
            try:
                ok, _msg = mailer.send_mail(email, subject, body, attachments)
            except Exception:
                ok = False
            wa.log_email(aud, email, name, subject, body, user_id, ok, "auto", **ids)
        else:  # handed to the background sender, which runs every minute
            wa.schedule_email(aud, email, name, subject, body, user_id, datetime.now(), "auto", **ids)
        done["email"] = True
    return done


def run_due_reminders(today: date | None = None) -> int:
    """Once per filing: remind the client when an unfiled return is within N days of its due date."""
    if not (is_on("due_reminder", "whatsapp") or is_on("due_reminder", "email")):
        return 0
    today = today or date.today()
    horizon = today + timedelta(days=due_days())
    sent = 0
    jobs = []
    for r in GstReturn.query.filter(GstReturn.status != "filed", GstReturn.due_date >= today, GstReturn.due_date <= horizon):
        jobs.append((f"due:gst:{r.id}:{r.due_date}", r.client, f"{r.return_type.name} for {r.period}", r.due_date))
    for r in ItrFiling.query.filter(ItrFiling.status != "filed", ItrFiling.due_date >= today, ItrFiling.due_date <= horizon):
        jobs.append((f"due:itr:{r.id}:{r.due_date}", r.client, f"Income Tax Return ({r.form_type}) for AY {r.assessment_year}", r.due_date))
    for r in TdsReturn.query.filter(TdsReturn.status != "filed", TdsReturn.due_date >= today, TdsReturn.due_date <= horizon):
        jobs.append((f"due:tds:{r.id}:{r.due_date}", r.client, f"TDS return {r.form_type} {r.quarter} FY {r.financial_year}", r.due_date))
    for key, client, label, due in jobs:
        if client is None or client.archived or db.session.get(AutoLog, key) is not None:
            continue
        result = fire("due_reminder", client=client, values={"period": label, "due_date": f"{due:%d-%b-%Y}"})
        db.session.add(AutoLog(key=key))
        sent += 1 if (result["whatsapp"] or result["email"]) else 0
    db.session.commit()
    return sent
