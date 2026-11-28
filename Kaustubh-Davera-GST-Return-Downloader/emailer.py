"""Build and send client emails (Gmail SMTP with an App Password)."""
import mimetypes
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from naming import fmt_date, send_by_date

GMAIL_LIMIT_MB = 24


class _Safe(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def build(cfg: dict, client, rows: list[dict]) -> dict:
    """rows: finished job rows of this client with files."""
    files = [f for r in rows for f in r["files"] if os.path.exists(f)]
    forms = []
    periods = []
    for r in rows:
        if r["form_label"] not in forms:
            forms.append(r["form_label"])
        if r["period"] not in periods:
            periods.append(r["period"])
    rows_2b = [r for r in rows if r["form"] == "GSTR2B"]
    tpl = cfg["templates"]["gstr2b" if rows_2b else "returns"]
    if rows_2b:
        y, m = max((r["year"], r["month"]) for r in rows_2b)
        by = fmt_date(send_by_date(y, m, cfg.get("send_by_day", 18)))
    else:
        by = ""
    values = _Safe(
        name=client.display_name,
        legal_name=client.name,
        gstin=client.gstin,
        period=", ".join(periods),
        forms=", ".join(forms),
        file_list="\n".join(f"- {os.path.basename(f)}" for f in files),
        send_by_date=by,
        firm_name=cfg.get("firm_name", ""),
        firm_phone=cfg.get("firm_phone", ""),
    )
    size_mb = sum(os.path.getsize(f) for f in files) / (1024 * 1024)
    return {
        "to": ", ".join(client.emails()),
        "cc": cfg["email"].get("cc", ""),
        "subject": tpl["subject"].format_map(values),
        "body": tpl["body"].format_map(values).rstrip() + "\n",
        "attachments": files,
        "attachment_names": [os.path.basename(f) for f in files],
        "size_mb": round(size_mb, 2),
        "too_big": size_mb > GMAIL_LIMIT_MB,
    }


def _split(addrs: str) -> list[str]:
    return [a.strip() for a in (addrs or "").replace(";", ",").split(",") if a.strip()]


def send(cfg: dict, to: str, cc: str, subject: str, body: str, attachments: list[str]) -> None:
    e = cfg["email"]
    if not e.get("sender_email") or not e.get("app_password"):
        raise ValueError("Email is not set up. Go to Settings and enter the Gmail address and App Password.")
    to_list, cc_list = _split(to), _split(cc)
    if not to_list:
        raise ValueError("No email address for this client.")
    msg = EmailMessage()
    msg["From"] = formataddr((e.get("sender_name") or "", e["sender_email"]))
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = subject
    msg.set_content(body)
    for path in attachments:
        ctype, _ = mimetypes.guess_type(path)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        with open(path, "rb") as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype,
                               filename=os.path.basename(path))
    first = int(e.get("smtp_port") or 587)
    ports = [first] + [p for p in (587, 465) if p != first]
    problems = []
    for port in ports:
        try:
            _send_on(e, port, msg, to_list + cc_list)
            return port
        except smtplib.SMTPAuthenticationError as ex:
            raise ValueError(
                "Gmail rejected the login.\n"
                "- Check the Gmail address in Settings.\n"
                "- Use an App Password (16 letters), not the normal Gmail password.\n"
                "- 2-Step Verification must be ON for that Gmail account.\n"
                f"(Gmail said: {_short(ex)})")
        except smtplib.SMTPRecipientsRefused as ex:
            raise ValueError(f"Gmail refused the recipient address: {', '.join(ex.recipients)}")
        except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, ssl.SSLError,
                ConnectionError, TimeoutError, OSError) as ex:
            problems.append(f"port {port}: {_short(ex)}")
            continue
    raise ValueError(
        "Could not connect to Gmail (" + "; ".join(problems) + ").\n"
        "Usually an antivirus with email scanning (Quick Heal, K7, Kaspersky, etc.) or the office "
        "network/firewall is blocking it. Turn off 'email scanning / mail protection' in the antivirus, "
        "or try on another network (e.g. mobile hotspot) to confirm.")


def _short(ex) -> str:
    t = str(ex) or ex.__class__.__name__
    if isinstance(ex, smtplib.SMTPResponseException):
        t = ex.smtp_error.decode(errors="ignore") if isinstance(ex.smtp_error, bytes) else str(ex.smtp_error)
    return " ".join(t.split())[:160]


def _send_on(e: dict, port: int, msg, rcpts) -> None:
    ctx = ssl.create_default_context()
    host = e.get("smtp_server") or "smtp.gmail.com"
    # local_hostname avoids slow / odd Windows computer names in the SMTP greeting
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=40, context=ctx, local_hostname="localhost")
    else:
        server = smtplib.SMTP(host, port, timeout=40, local_hostname="localhost")
        server.ehlo()
        server.starttls(context=ctx)
        server.ehlo()
    try:
        server.login(e["sender_email"].strip(), e["app_password"].replace(" ", "").strip())
        server.send_message(msg, to_addrs=rcpts)
    finally:
        try:
            server.quit()
        except Exception:
            pass
