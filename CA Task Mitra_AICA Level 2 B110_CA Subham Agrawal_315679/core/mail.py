"""Sending e-mail through the firm's SMTP account. Without SMTP settings the mail is saved
as an .eml file in data/outbox (simulated send) so the whole workflow can be demonstrated safely."""
import smtplib, ssl, os, time, re
from email.message import EmailMessage
from . import paths, framework as F


def send_mail(db, to, subject, body):
    host = F.get_setting(db, "smtp_host")
    sender = F.get_setting(db, "smtp_from") or F.get_setting(db, "smtp_user") or "taskmitra@localhost"
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = sender, to, subject
    msg.set_content(body)
    if not host:
        name = re.sub(r"[^A-Za-z0-9]+", "_", subject)[:40] + "_" + str(int(time.time())) + ".eml"
        with open(os.path.join(paths.DATA, "outbox", name), "wb") as f:
            f.write(bytes(msg))
        return "simulated (saved in data/outbox)"
    port = int(F.get_setting(db, "smtp_port", "587") or 587)
    user, pw = F.get_setting(db, "smtp_user"), F.get_setting(db, "smtp_pass")
    if port == 465:
        s = smtplib.SMTP_SSL(host, port, timeout=30, context=ssl.create_default_context())
    else:
        s = smtplib.SMTP(host, port, timeout=30)
        s.starttls(context=ssl.create_default_context())
    try:
        if user:
            s.login(user, pw)
        s.send_message(msg)
    finally:
        s.quit()
    return "sent"
