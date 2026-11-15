"""WhatsApp click-to-chat helpers. No WhatsApp API is used: we prepare a message and open WhatsApp Web or the Desktop app."""
import re
from datetime import date, datetime, timedelta
from urllib.parse import quote

from ..models import FirmSetting, GstReturn, Invoice, ItrFiling, TdsReturn, WhatsAppMessage, WhatsAppTemplate, db

PLACEHOLDERS = {
    "client_name": "Client name", "contact_person": "Contact person", "work_type": "Type of work", "firm_name": "Firm name", "staff_name": "Staff name", "period": "Period",
    "due_date": "Due date", "amount": "Amount", "invoice_number": "Invoice no.", "firm_phone": "Firm phone", "partner_name": "Partner name",
}

# name, category, body. *text* shows as bold in WhatsApp and in emails.
DEFAULT_TEMPLATES = [
    ("Document request", "documents",
     "Dear {client_name},\n\nGreetings from {firm_name}.\n\nTo complete the following work on time, we request you to share the required "
     "documents and details at the earliest:\n\nType of work: *{work_type}*\nPeriod: *{period}*\n\nPlease ignore this message if already sent.\n\n"
     "Regards,\n{firm_name}\n{firm_phone}"),
    ("Payment reminder", "billing",
     "Dear {client_name},\n\nGreetings from {firm_name}.\n\nThis is a gentle reminder that the following payment is pending:\n\n"
     "Invoice No.: *{invoice_number}*\nAmount due: *Rs. {amount}*\n\nKindly arrange the payment at your earliest convenience. "
     "Please ignore this message if already paid.\n\nRegards,\n{firm_name}\n{firm_phone}"),
    ("Return filed", "compliance",
     "Dear {client_name},\n\nWe are pleased to inform you that the following has been filed successfully:\n\n"
     "Type of work: *{work_type}*\nPeriod: *{period}*\n\nThank you for your timely co-operation.\n\nRegards,\n{firm_name}\n{firm_phone}"),
    ("Due date alert", "compliance",
     "Dear {client_name},\n\nGreetings from {firm_name}.\n\nThis is to remind you of the following due date:\n\n"
     "Type of work: *{work_type}*\nPeriod: *{period}*\nDue date: *{due_date}*\n\n"
     "Kindly share the pending details well before the due date to avoid late fees and interest.\n\nRegards,\n{firm_name}\n{firm_phone}"),
    ("Staff notice", "staff", "Dear {staff_name},\n\nPlease note the following update from {firm_name}:\n\n\n\nRegards,\n{partner_name}"),
]
WORK_TYPES = ["GST Return", "GST Annual Return", "Income Tax Return", "TDS Return", "Advance Tax", "Tax Audit", "Statutory Audit", "Accounting",
              "ROC Filing", "PF / ESI", "Legal matter", "Other"]
# Wordings shipped in earlier versions; a template still carrying one of these untouched is upgraded to the wording above.
OLD_BODIES = {'Document request': ['Dear {client_name}, please share the documents for {period} at the earliest so we can complete your work on time. Thank you. - {firm_name}', 'Dear {client_name},\n\nGreetings from {firm_name}.\n\nTo complete your *{period}* work on time, we request you to share the required documents and details at the earliest.\n\nPlease ignore this message if already sent.\n\nRegards,\n{firm_name}\n{firm_phone}'], 'Payment reminder': ['Dear {client_name}, this is a gentle reminder that Rs. {amount} is pending against invoice {invoice_number}. Kindly arrange payment. - {firm_name}', 'Dear {client_name},\n\nGreetings from {firm_name}.\n\nThis is a gentle reminder that the following payment is pending:\n\nInvoice No.: *{invoice_number}*\nAmount due: *Rs. {amount}*\n\nKindly arrange the payment at your earliest convenience. Please ignore this message if already paid.\n\nRegards,\n{firm_name}\n{firm_phone}'], 'Return filed': ['Dear {client_name}, your {period} return has been filed successfully. - {firm_name}', 'Dear {client_name},\n\nWe are pleased to inform you that your *{period}* return has been filed successfully.\n\nThank you for your timely co-operation.\n\nRegards,\n{firm_name}\n{firm_phone}'], 'Due date alert': ['Dear {client_name}, your {period} filing is due on {due_date}. Please send the pending details. - {firm_name}', 'Dear {client_name},\n\nGreetings from {firm_name}.\n\nThis is to remind you of the following due date:\n\nParticulars: *{period}*\nDue date: *{due_date}*\n\nKindly share the pending details well before the due date to avoid late fees and interest.\n\nRegards,\n{firm_name}\n{firm_phone}'], 'Staff notice': ['Hi {staff_name}, {firm_name} office update: ', 'Dear {staff_name},\n\nPlease note the following update from {firm_name}:\n\n\n\nRegards,\n{partner_name}']}


def seed_templates() -> None:
    if WhatsAppTemplate.query.count() == 0:
        for name, cat, body in DEFAULT_TEMPLATES:
            db.session.add(WhatsAppTemplate(name=name, category=cat, body=body))
        return
    for name, _cat, body in DEFAULT_TEMPLATES:
        row = WhatsAppTemplate.query.filter_by(name=name).first()
        if row is not None and row.body.strip() in {b.strip() for b in OLD_BODIES[name]}:
            row.body = body


def normalize_phone(raw: str | None, default_cc: str | None = None) -> str | None:
    """Digits only with country code, or None if it cannot be a real mobile number."""
    if not raw:
        return None
    cc = re.sub(r"\D", "", default_cc or FirmSetting.get("wa_country_code", "91") or "91")
    digits = re.sub(r"\D", "", raw)
    if raw.strip().startswith("+") or raw.strip().startswith("00"):
        digits = digits[2:] if raw.strip().startswith("00") else digits
        return digits if 10 <= len(digits) <= 15 else None
    digits = digits.lstrip("0") if len(digits) == 11 and digits.startswith("0") else digits
    if len(digits) == 10:
        return cc + digits
    if len(digits) == 10 + len(cc) and digits.startswith(cc):
        return digits
    return None


def links(phone: str, text: str) -> dict:
    t = quote(text, safe="")
    return {
        "web": f"https://web.whatsapp.com/send?phone={phone}&text={t}",
        "desktop": f"whatsapp://send?phone={phone}&text={t}",
        "wa_me": f"https://wa.me/{phone}?text={t}",
    }


class _Safe(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def render(body: str, **values) -> str:
    base = _Safe({k: "" for k in PLACEHOLDERS})
    base["firm_phone"] = FirmSetting.get("firm_phone", "") or ""
    base["partner_name"] = FirmSetting.get("firm_partner_name", "") or FirmSetting.get("firm_name", "") or ""
    base.update({k: ("" if v is None else str(v)) for k, v in values.items()})
    try:
        lines = []
        for ln in body.split("\n"):
            fields = re.findall(r"\{([a-z_]+)\}", ln)
            # a "Label: {field}" line whose fields are all empty is dropped, so unused fields leave no gaps in the message
            if fields and re.match(r"\s*[^:{}]{1,30}:\s*\*?\s*(Rs\.\s*)?\{", ln) and not any(str(base[k]).strip() for k in fields):
                continue
            lines.append(ln.format_map(base))
        text = "\n".join(lines)
        return re.sub(r"\n{3,}", "\n\n", text).strip()
    except (ValueError, IndexError, KeyError):
        return body  # a stray brace in a hand-typed template must not crash sending


def money(v: float) -> str:
    s = f"{abs(v):.2f}"
    whole, dec = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return f"{whole}.{dec}"


def pending_items(client_ids: list[int], within_days: int = 7, today: date | None = None) -> dict[int, list[str]]:
    """{client_id: [text lines]} for unfiled work overdue or due within N days, and unpaid invoices past/near due."""
    today = today or date.today()
    horizon = today + timedelta(days=within_days)
    out: dict[int, list[str]] = {}

    def add(cid, text):
        out.setdefault(cid, []).append(text)

    def when(d):
        return f"overdue since {d:%d-%b-%Y}" if d < today else f"due {d:%d-%b-%Y}"

    if not client_ids:
        return out
    for r in GstReturn.query.filter(GstReturn.client_id.in_(client_ids), GstReturn.status != "filed", GstReturn.due_date.isnot(None), GstReturn.due_date <= horizon):
        add(r.client_id, f"{r.return_type.name} {r.period} ({when(r.due_date)})")
    for r in ItrFiling.query.filter(ItrFiling.client_id.in_(client_ids), ItrFiling.status != "filed", ItrFiling.due_date.isnot(None), ItrFiling.due_date <= horizon):
        add(r.client_id, f"{r.form_type} AY {r.assessment_year} ({when(r.due_date)})")
    for r in TdsReturn.query.filter(TdsReturn.client_id.in_(client_ids), TdsReturn.status != "filed", TdsReturn.due_date.isnot(None), TdsReturn.due_date <= horizon):
        add(r.client_id, f"TDS {r.form_type} {r.quarter} FY {r.financial_year} ({when(r.due_date)})")
    for i in Invoice.query.filter(Invoice.client_id.in_(client_ids), Invoice.balance > 0.01, Invoice.due_date.isnot(None), Invoice.due_date <= horizon):
        add(i.client_id, f"Invoice {i.invoice_number}: Rs. {money(i.balance)} ({when(i.due_date)})")
    return out


def reminder_text(client_name: str, lines: list[str], firm: str) -> str:
    body = "\n".join(f"{n}. {l}" for n, l in enumerate(lines, 1))
    phone = FirmSetting.get("firm_phone", "") or ""
    return (f"Dear {client_name},\n\nGreetings from {firm}.\n\nThis is a gentle reminder regarding the following pending matters:\n\n{body}\n\n"
            f"Kindly share the required details / arrange the payment at the earliest. Please ignore if already done.\n\nRegards,\n{firm}"
            + (f"\n{phone}" if phone else ""))


def due_date_options(today: date | None = None) -> list[dict]:
    """The due-date master for messages: statutory dates worked out from the GST/ITR/TDS set-up plus your own calendar rules."""
    from ..models import ComplianceRule, GstReturnType
    from . import compliance as comp

    today = today or date.today()
    out = []

    def add(label, period, due):
        if due:
            out.append({"label": f"{label} - {due:%d-%b-%Y}" + (" (date passed)" if due < today else ""), "work": label, "period": period, "due_date": f"{due:%d-%b-%Y}", "sort": due.isoformat()})

    py, pm = comp._add_months(today.year, today.month, -1)
    for rt in GstReturnType.query.filter_by(active=True):
        if rt.frequency == "monthly":
            for y, m in ((py, pm), (today.year, today.month)):
                due = comp.gst_due_date(rt, f"{y}-{m:02d}")
                if due and due >= today:
                    add(rt.name, f"{rt.name} for {date(y, m, 1):%b %Y}", due)
                    break
        elif rt.frequency == "quarterly":
            q = (today.month - 1) // 3  # last completed calendar quarter
            y, q = (today.year - 1, 4) if q == 0 else (today.year, q)
            span = ["Jan-Mar", "Apr-Jun", "Jul-Sep", "Oct-Dec"][q - 1]
            add(rt.name, f"{rt.name} for {span} {y}", comp.gst_due_date(rt, f"{y}-Q{q}"))
    fy = today.year if today.month >= 4 else today.year - 1
    ay = f"{fy + 1}-{str(fy + 2)[2:]}"
    add("Income Tax Return", f"Income Tax Return AY {ay}", comp.itr_due_date(ay))
    months_in = (today.month - 4) % 12
    done_q = months_in // 3  # completed quarters in this financial year
    tfy, tq = (fy - 1, 4) if done_q == 0 else (fy, done_q)
    tfy_label = f"{tfy}-{str(tfy + 1)[2:]}"
    add("TDS Return", f"TDS return Q{tq} FY {tfy_label}", comp.tds_due_date(tfy_label, f"Q{tq}"))
    for rule in ComplianceRule.query.filter_by(active=True).order_by(ComplianceRule.title):
        try:
            if rule.frequency == "yearly" and rule.due_month:
                due = comp._safe_date(today.year, rule.due_month, rule.due_day or 1)
                if due < today:
                    due = comp._safe_date(today.year + 1, rule.due_month, rule.due_day or 1)
            else:
                due = comp._safe_date(today.year, today.month, rule.due_day or 1)
                if due < today:
                    ny, nm = comp._add_months(today.year, today.month, 1)
                    due = comp._safe_date(ny, nm, rule.due_day or 1)
            add(rule.title, rule.title, due)
        except (ValueError, TypeError):
            continue
    out.sort(key=lambda d: d["sort"])
    return out


def schedule_email(audience, email, name, subject, body, user_id, send_at, source="scheduled", client_id=None, staff_id=None, image=None) -> WhatsAppMessage:
    m = WhatsAppMessage(image=image, audience=audience, client_id=client_id, staff_id=staff_id, recipient_name=f"{name} <{email}>"[:200], phone="", email=email,
                        body=body.strip(), source=source, created_by_id=user_id, channel="email", subject=(subject or "")[:200],
                        status="scheduled", send_at=send_at)
    db.session.add(m)
    return m


def send_scheduled(now: datetime | None = None) -> int:
    """Send emails whose time has come. Runs every minute while the app is open on the host PC."""
    from . import mailer

    now = now or datetime.now()
    due = WhatsAppMessage.query.filter(WhatsAppMessage.status == "scheduled", WhatsAppMessage.send_at <= now).limit(50).all()
    sent = 0
    for m in due:
        from . import pictures

        pic = pictures.attachment(m.image)
        ok, _msg = mailer.send_mail(m.email or "", m.subject or "", m.body, [pic] if pic else None)
        m.status, m.opened_at = ("opened", datetime.utcnow()) if ok else ("skipped", None)
        sent += 1 if ok else 0
    if due:
        db.session.commit()
    return sent


def log_email(audience, email, name, subject, body, user_id, ok: bool, source="manual", client_id=None, staff_id=None, image=None) -> WhatsAppMessage:
    m = WhatsAppMessage(email=email, image=image, audience=audience, client_id=client_id, staff_id=staff_id, recipient_name=name, phone="",
                        body=body.strip(), source=source, created_by_id=user_id, channel="email", subject=(subject or "")[:200],
                        status="opened" if ok else "skipped", opened_at=datetime.utcnow() if ok else None)
    m.recipient_name = f"{name} <{email}>"[:200]
    db.session.add(m)
    return m


def queue(audience, phone_raw, name, body, user_id, source="manual", client_id=None, staff_id=None, image=None) -> WhatsAppMessage | None:
    phone = normalize_phone(phone_raw)
    if not phone or not body.strip():
        return None
    m = WhatsAppMessage(audience=audience, client_id=client_id, staff_id=staff_id, recipient_name=name, phone=phone, body=body.strip(),
                        source=source, created_by_id=user_id, image=image)
    db.session.add(m)
    return m
