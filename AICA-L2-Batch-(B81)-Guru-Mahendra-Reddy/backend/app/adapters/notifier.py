"""Alert delivery.

SMS through Twilio, not WhatsApp. The reason is worth recording, because the
WhatsApp path looked finished and was not: Meta's Cloud API only accepts a
free-form message inside a 24-hour window that opens when the *recipient*
messages you first. An alert is business-initiated by definition — it fires
because runway crossed a threshold at 08:00, not because anyone wrote in — so
that window is always shut, and every alert would have needed a pre-approved
template. SMS has no window and no per-message approval.

What SMS does not escape, in India, is DLT: sending on the domestic route
needs the entity, the sender header and the message template registered with
TRAI, and unregistered messages are dropped at the network with no error.
Twilio's international route reaches Indian handsets without that, from an
unbranded number, which is what a demonstration uses. `docs/SMS_SETUP.md`
says so plainly rather than leaving it to be discovered in production.

The n8n path is still here behind the same interface — set CR_ALERT_CHANNEL=n8n
and nothing else changes.

Every attempt is recorded in alert_deliveries whether it succeeded or not,
because Tab 11 asks "Delivered? Read?" and an honest answer sometimes has to
be "no".
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import requests

from app.config import settings
from app.models import Alert, AlertDelivery, AlertRule, User
from app.services.common import Ctx, fmt_date, fmt_inr

TIMEOUT = 15

# One SMS segment is 160 characters of GSM-7. A single character outside that
# alphabet — the rupee sign, an emoji, a typographic dash — switches the whole
# message to UCS-2 and the segment drops to 70. A four-line alert then costs
# six segments instead of two, and the recipient's operator may split it badly.
# So the SMS body is transliterated to GSM-7 before it is sent.
_GSM_SAFE = {
    "₹": "Rs", "—": "-", "–": "-", "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...", "🔴": "", "🟠": "", "⚪": "", "•": "-", " ": " ",
}
SMS_MAX_CHARS = 480          # three segments; longer says nothing more useful


def gsm7(s: str) -> str:
    """Make a string safe for a single-byte SMS alphabet."""
    for bad, good in _GSM_SAFE.items():
        s = s.replace(bad, good)
    s = s.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[ \t]+", " ", s)


# ---------------------------------------------------------------------------
# Message body
# ---------------------------------------------------------------------------
def compose(ctx: Ctx, alert: Alert, escalation: bool = False) -> str:
    """The long form, for email. Keeps the rupee sign and the deep link."""
    lines = [
        f"Cash Runway — {ctx.entity.name}",
        f"{'ESCALATION — unacknowledged. ' if escalation else ''}"
        f"{alert.severity}: {alert.title}",
        "",
        alert.message,
    ]
    if alert.amount_at_stake:
        lines.append(f"\nAmount at stake: {fmt_inr(alert.amount_at_stake)}")
    lines.append(f"As on {fmt_date(ctx.as_on)}.")
    if alert.deep_link:
        lines.append(f"Open: {alert.deep_link}")
    return "\n".join(lines)


def compose_sms(ctx: Ctx, alert: Alert, escalation: bool = False) -> str:
    """The short form. No deep link — it points at localhost, which is useless
    on a phone, and it would cost a segment to say so."""
    head = f"Cash Runway - {ctx.entity.name}"
    subject = (f"{'ESCALATION. ' if escalation else ''}"
               f"{alert.severity.upper()}: {alert.title}")
    parts = [head, subject, alert.message]
    if alert.amount_at_stake:
        parts.append(f"At stake: {fmt_inr(alert.amount_at_stake)}")
    parts.append(f"As on {fmt_date(ctx.as_on)}.")
    body = gsm7("\n".join(p for p in parts if p))
    if len(body) > SMS_MAX_CHARS:
        body = body[:SMS_MAX_CHARS - 1].rstrip() + "…".replace("…", "...")
    return body


def segments(body: str) -> int:
    """How many SMS this will actually cost. Shown in the test result, because
    a demonstration that hides the cost of its own channel is not much of one."""
    unicode_body = any(ord(c) > 127 for c in body)
    size, multi = (70, 67) if unicode_body else (160, 153)
    if len(body) <= size:
        return 1
    return -(-len(body) // multi)


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------
def _send_sms_twilio(to: str, body: str) -> tuple[bool, str | None, str | None]:
    """Twilio's REST API. Returns (ok, provider_message_id, error)."""
    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN):
        return False, None, ("SMS is not configured. Set CR_TWILIO_ACCOUNT_SID and "
                             "CR_TWILIO_AUTH_TOKEN.")
    if not (settings.TWILIO_MESSAGING_SERVICE_SID or settings.TWILIO_FROM):
        return False, None, ("No sender. Set CR_TWILIO_FROM to a Twilio number, or "
                             "CR_TWILIO_MESSAGING_SERVICE_SID to a Messaging Service.")

    url = (f"https://api.twilio.com/2010-04-01/Accounts/"
           f"{settings.TWILIO_ACCOUNT_SID}/Messages.json")
    data = {"To": to if to.startswith("+") else f"+{to}", "Body": body}
    # A Messaging Service wins when both are set: it is the one that carries
    # the sender pool and the compliance registration.
    if settings.TWILIO_MESSAGING_SERVICE_SID:
        data["MessagingServiceSid"] = settings.TWILIO_MESSAGING_SERVICE_SID
    else:
        data["From"] = settings.TWILIO_FROM

    try:
        r = requests.post(url, data=data, timeout=TIMEOUT,
                          auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN))
        payload = r.json() if "json" in (r.headers.get("content-type") or "") else {}
        if r.status_code >= 400:
            # Twilio's own message is more use than the status code — it names
            # the unverified number or the unreachable region outright.
            detail = payload.get("message") or r.text[:300]
            code = payload.get("code")
            return False, None, f"Twilio {code or r.status_code}: {detail}"
        # 'queued' or 'accepted' means Twilio took it, not that a handset saw
        # it. Delivery is asynchronous; without a status webhook this is as far
        # as we can honestly claim.
        return True, payload.get("sid"), None
    except requests.RequestException as e:
        return False, None, f"{type(e).__name__}: {e}"


def _send_sms_n8n(to: str, body: str, alert: Alert) -> tuple[bool, str | None, str | None]:
    """Alternative path: post to an n8n webhook and let the workflow deliver."""
    if not settings.N8N_WEBHOOK_URL:
        return False, None, "n8n is selected but CR_N8N_WEBHOOK_URL is not set."
    try:
        r = requests.post(settings.N8N_WEBHOOK_URL, timeout=TIMEOUT, json={
            "to": to, "body": body, "severity": alert.severity,
            "title": alert.title, "rule_code": alert.rule_code,
            "amount_at_stake": alert.amount_at_stake, "link": alert.deep_link,
        })
        if r.status_code >= 400:
            return False, None, f"HTTP {r.status_code}: {r.text[:300]}"
        return True, r.headers.get("x-execution-id"), None
    except requests.RequestException as e:
        return False, None, f"{type(e).__name__}: {e}"


def _send_email(to: str, subject: str, body: str) -> tuple[bool, str | None, str | None]:
    if not settings.SMTP_HOST:
        return False, None, "SMTP is not configured."
    import smtplib
    from email.message import EmailMessage
    try:
        msg = EmailMessage()
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=TIMEOUT) as s:
            s.starttls()
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)
        return True, None, None
    except Exception as e:
        return False, None, f"{type(e).__name__}: {e}"


def _dispatch_sms(to: str, body: str, alert: Alert) -> tuple[bool, str | None, str | None]:
    if settings.ALERT_CHANNEL == "n8n":
        return _send_sms_n8n(to, body, alert)
    if settings.ALERT_CHANNEL == "console":
        print(f"\n--- SMS to {to} · {segments(body)} segment(s) ---\n{body}\n")
        return True, "console", None
    return _send_sms_twilio(to, body)


# ---------------------------------------------------------------------------
# Rules written before the channel was SMS say "whatsapp". They mean the same
# thing — the phone in someone's pocket — so they are read as SMS rather than
# silently dropped.
CHANNEL_ALIASES = {"whatsapp": "sms"}


def canonical_channel(name: str) -> str:
    return CHANNEL_ALIASES.get(name.strip().lower(), name.strip().lower())


def recipients_for(ctx: Ctx, rule: AlertRule, channel: str,
                   escalation: bool = False) -> list[str]:
    raw = (rule.escalate_to if escalation and rule.escalate_to else rule.recipients) or ""
    entries = [x.strip() for x in raw.split(",") if x.strip()]
    if channel == "email":
        out = []
        for e in entries:
            if "@" in e:
                out.append(e)
            else:
                u = ctx.db.query(User).filter(User.phone == e).first()
                if u:
                    out.append(u.email)
        if not out:
            out = [u.email for u in ctx.db.query(User)
                   .filter(User.role.in_(["CFO", "Admin"])).all()]
        return out
    return [e for e in entries if "@" not in e]


def send(ctx: Ctx, alert: Alert, rule: AlertRule,
         escalation: bool = False) -> list[dict]:
    """Deliver one alert across every channel its rule specifies."""
    long_body = compose(ctx, alert, escalation=escalation)
    sms_body = compose_sms(ctx, alert, escalation=escalation)
    subject = f"[Cash Runway] {alert.severity}: {alert.title}"
    results: list[dict] = []

    seen: set[str] = set()
    for raw in (rule.channels or "").split(","):
        channel = canonical_channel(raw)
        if not channel or channel in seen:
            continue
        seen.add(channel)
        for to in recipients_for(ctx, rule, channel, escalation):
            if channel == "sms":
                ok, mid, err = _dispatch_sms(to, sms_body, alert)
            elif channel == "email":
                ok, mid, err = _send_email(to, subject, long_body)
            else:
                ok, mid, err = True, "console", None
                print(f"\n--- {channel} to {to} ---\n{long_body}\n")

            ctx.db.add(AlertDelivery(
                alert_id=alert.id, channel=channel, recipient=to,
                sent_on=datetime.now(timezone.utc).replace(tzinfo=None),
                delivered=ok, read=False, provider_message_id=mid, error=err))
            results.append({"channel": channel, "recipient": to, "delivered": ok,
                            "error": err})
    ctx.db.flush()
    return results


def send_test(ctx: Ctx, to: str, channel: str = "sms") -> dict:
    """Used by Setup › Alert Rules to prove delivery works before relying on it."""
    channel = canonical_channel(channel)
    if channel == "sms":
        body = gsm7(f"Cash Runway - test message. If you can read this, alert "
                    f"delivery for {ctx.entity.name} is working. No action needed.")
        ok, mid, err = _dispatch_sms(to, body, Alert(
            entity_id=ctx.entity.id, rule_code="test", severity="Grey",
            title="Test", message=body))
        return {"delivered": ok, "provider_message_id": mid, "error": err,
                "channel": channel, "recipient": to,
                "transport": settings.ALERT_CHANNEL, "segments": segments(body),
                "characters": len(body)}

    body = (f"Cash Runway — test message\n\nIf you can read this, alert delivery for "
            f"{ctx.entity.name} is working. No action needed.")
    ok, mid, err = _send_email(to, "[Cash Runway] Test message", body)
    return {"delivered": ok, "provider_message_id": mid, "error": err,
            "channel": channel, "recipient": to, "transport": "smtp"}
