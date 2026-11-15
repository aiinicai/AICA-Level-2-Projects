"""Outgoing email using the SMTP details saved in Settings. Password is stored encrypted."""
import base64
import hashlib
import html
import re
import smtplib
import ssl
from email.message import EmailMessage

from cryptography.fernet import Fernet, InvalidToken

from ..config import read_secret
from ..models import FirmSetting

ENCRYPTIONS = {
    "tls": "TLS / STARTTLS (usually port 587)",
    "ssl": "SSL (usually port 465)",
    "none": "None (usually port 25)",
}


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(read_secret("mail.key").encode()).digest())
    return Fernet(key)


def encrypt_password(raw: str) -> str:
    return _fernet().encrypt(raw.encode()).decode()


def _decrypt(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        return None  # key file replaced; re-enter the password in Settings


def is_configured() -> bool:
    return FirmSetting.get("mail_enabled") == "1" and bool(FirmSetting.get("mail_host"))


def signature() -> str:
    """Sign-off block used at the end of emails and messages."""
    s = FirmSetting.all()
    lines = [s.get("firm_partner_name") or "", s.get("firm_name") or "", s.get("firm_phone") or "", s.get("firm_email") or ""]
    return "\n".join(x for x in lines if x)


def plain_text(body: str) -> str:
    return re.sub(r"\*(\S(?:[^*\n]*\S)?)\*", r"\1", body)  # *bold* markers are for WhatsApp/HTML only


def to_html(body: str) -> str:
    """Plain text with *bold* markers -> tidy HTML email (paragraphs, line breaks, bold)."""
    out = []
    for para in re.split(r"\n\s*\n", body.strip()):
        safe = html.escape(para)
        safe = re.sub(r"\*(\S(?:[^*\n]*\S)?)\*", r"<b>\1</b>", safe).replace("\n", "<br>")
        out.append(f'<p style="margin:0 0 14px 0">{safe}</p>')
    return ('<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;line-height:1.55;color:#1f2937;max-width:640px">'
            + "".join(out) + "</div>")


def send_mail(to: str, subject: str, body: str, attachments: list[tuple[str, bytes, str]] | None = None) -> tuple[bool, str]:
    if not is_configured():
        return False, "Email is not set up. Open Settings and fill in the email (SMTP) details first."
    s = FirmSetting.all()
    host, port = s["mail_host"], int(s.get("mail_port") or 587)
    mode = s.get("mail_encryption") or "tls"
    sender = s.get("mail_from_address") or s.get("mail_username")
    if not sender:
        return False, "Set a 'From' email address in Settings."

    msg = EmailMessage()
    msg["From"] = f"{s.get('mail_from_name') or s.get('firm_name') or 'Office Manager'} <{sender}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(plain_text(body))
    msg.add_alternative(to_html(body), subtype="html")
    for name, data, mime in attachments or []:
        maintype, _, subtype = mime.partition("/")
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=name)

    try:
        if mode == "ssl":
            server = smtplib.SMTP_SSL(host, port, timeout=20, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(host, port, timeout=20)
        try:
            server.ehlo()
            if mode == "tls":
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            username, password = s.get("mail_username"), _decrypt(s.get("mail_password"))
            if username and password:
                server.login(username, password)
            server.send_message(msg)
        finally:
            try:
                server.quit()
            except Exception:
                pass
    except smtplib.SMTPAuthenticationError:
        return False, "The mail server rejected the username or password. Gmail and Outlook need an app password."
    except (smtplib.SMTPException, OSError) as e:
        return False, f"Could not send the email: {e}"
    return True, f"Email sent to {to}."
