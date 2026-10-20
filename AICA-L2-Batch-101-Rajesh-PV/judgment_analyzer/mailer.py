"""Delivery of approved emails, plus an audit log.

Three ways to deliver:
* Outlook desktop (Windows): driven through its COM interface (pywin32), so emails are
  created in - and sent from - the user's own Outlook profile (Drafts or Sent Items).
* Any email account over SMTP (Gmail, Microsoft 365 / Outlook.com, Zoho, the firm's own
  server): Python's built-in smtplib over an encrypted connection. Gmail needs 2-Step
  Verification and an App Password; the password is kept in the OS credential vault.
* .eml files that any mail program can open and send.
"""

from __future__ import annotations

import csv
import logging
import os
import re
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage as MimeMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path
from typing import Callable

from .config import user_config_dir
from .email_composer import EmailMessage
from .pdf_processor import CancelledError

log = logging.getLogger(__name__)

MODE_DRAFT = "Outlook draft"
MODE_SEND = "Sent via Outlook"
MODE_EML = "Saved as .eml"
MODE_TEST = "Test to self"
MODE_SMTP = "Sent via email server"

# Provider presets: (host, port, security). Check your provider's current settings if a connection fails.
SMTP_PRESETS: dict[str, tuple[str, int, str]] = {
    "Gmail": ("smtp.gmail.com", 465, "SSL"),
    "Microsoft 365 / Outlook.com": ("smtp.office365.com", 587, "STARTTLS"),
    "Zoho Mail (India)": ("smtp.zoho.in", 465, "SSL"),
    "Other (enter server details)": ("", 587, "STARTTLS"),
}
SMTP_SECURITY = ("SSL", "STARTTLS")
KNOWN_DUAL_PORT_HOSTS = {"smtp.gmail.com", "smtp.office365.com", "smtp.zoho.in", "smtp.zoho.com"}


class MailerError(Exception):
    pass


@dataclass
class DeliveryResult:
    recipient: str
    email: str
    ok: bool
    error: str = ""


# --------------------------------------------------------------- Outlook ---
def outlook_available() -> tuple[bool, str]:
    if not sys.platform.startswith("win"):
        return False, "Outlook integration is available on Windows only."
    try:
        import win32com.client  # noqa: F401
    except ImportError:
        return False, "The 'pywin32' package is missing. Re-run run_windows.bat to install it."
    return True, ""


class OutlookMailer:
    """Create or send emails through the locally installed Outlook desktop app.

    ``dispatch`` can be injected for testing (defaults to win32com Dispatch).
    """

    def __init__(self, sender_email: str = "", dispatch: Callable | None = None):
        self.sender_email = (sender_email or "").strip().lower()
        self._dispatch = dispatch
        self._app = None
        self._account = None

    def _connect(self):
        if self._app is not None:
            return
        if self._dispatch is None:
            ok, why = outlook_available()
            if not ok:
                raise MailerError(why)
            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()  # required on worker threads
            self._dispatch = win32com.client.Dispatch
        try:
            self._app = self._dispatch("Outlook.Application")
        except Exception as exc:
            raise MailerError("Could not start Outlook. Make sure Outlook (desktop) is installed and you are "
                              "signed in, then try again.") from exc
        self._account = self._find_account()

    def _find_account(self):
        if not self.sender_email:
            return None
        try:
            for account in self._app.Session.Accounts:
                if str(getattr(account, "SmtpAddress", "")).strip().lower() == self.sender_email:
                    return account
        except Exception as exc:  # account lookup is best-effort
            log.info("Could not enumerate Outlook accounts: %s", exc)
        return None

    @property
    def account_matched(self) -> bool:
        return self._account is not None

    def deliver(self, message: EmailMessage, send: bool) -> None:
        self._connect()
        try:
            mail = self._app.CreateItem(0)  # 0 = olMailItem
            mail.To = message.to_email
            mail.Subject = message.subject
            mail.HTMLBody = message.html
            if self._account is not None:
                try:
                    mail.SendUsingAccount = self._account
                except Exception as exc:
                    log.info("Could not set sending account: %s", exc)
            if send:
                mail.Send()
            else:
                mail.Save()  # stored in the Drafts folder
        except MailerError:
            raise
        except Exception as exc:
            text = str(exc)
            if "denied" in text.lower() or "security" in text.lower():
                raise MailerError("Outlook blocked the request (programmatic access security). "
                                  "Ask IT to allow programmatic access, or use 'Create drafts'.") from exc
            raise MailerError(f"Outlook error: {text[:200]}") from exc


# ------------------------------------------------------------------ SMTP ---
@dataclass
class SmtpSettings:
    provider: str = "Gmail"
    host: str = "smtp.gmail.com"
    port: int = 465
    security: str = "SSL"
    username: str = ""

    def validate(self) -> list[str]:
        problems = []
        if not re.match(r"^[A-Za-z0-9.-]{3,253}$", self.host or ""):
            problems.append("Enter the email server name (e.g. smtp.gmail.com).")
        if not 1 <= int(self.port or 0) <= 65535:
            problems.append("Enter a valid server port (465 or 587 for most providers).")
        if self.security not in SMTP_SECURITY:
            problems.append("Security must be SSL or STARTTLS.")
        if not self.username.strip():
            problems.append("Enter the email account user name (usually your full email address).")
        return problems


def _smtp_settings_path() -> Path:
    return user_config_dir() / "smtp_settings.json"


def load_smtp_settings() -> SmtpSettings:
    import json

    try:
        data = json.loads(_smtp_settings_path().read_text(encoding="utf-8"))
        s = SmtpSettings(**{k: v for k, v in data.items() if k in SmtpSettings.__dataclass_fields__})
        s.port = int(s.port)
        return s
    except (OSError, ValueError, TypeError):
        return SmtpSettings()


def save_smtp_settings(settings: SmtpSettings) -> None:
    """Saves server details only - never the password (that goes to the OS credential vault)."""
    import json
    from dataclasses import asdict

    _smtp_settings_path().write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")


def build_mime(message: EmailMessage, sender_name: str, sender_email: str, unsent: bool = False) -> MimeMessage:
    mime = MimeMessage()
    mime["From"] = formataddr((sender_name, sender_email))
    if message.to_email:
        mime["To"] = formataddr((message.to_name, message.to_email))
    mime["Subject"] = message.subject
    mime["Date"] = formatdate(localtime=True)
    mime["Message-ID"] = make_msgid(domain=(sender_email.rsplit("@", 1)[-1] if "@" in sender_email else None))
    if unsent:
        mime["X-Unsent"] = "1"  # Outlook opens it as a draft ready to send
    mime.set_content(message.text)
    mime.add_alternative(message.html, subtype="html")
    return mime


_INVISIBLE_RE = re.compile(r"[\s\u00a0\u200b\u200c\u200d\u2060\ufeff]+")


def normalise_password(host: str, password: str) -> str:
    """Gmail shows App Passwords in four groups ('abcd efgh ijkl mnop'); copying from the web page can bring
    normal or non-breaking spaces and invisible characters. Remove them for Gmail."""
    return _INVISIBLE_RE.sub("", password or "") if "gmail" in (host or "").lower() else (password or "")


def looks_like_gmail_app_password(password: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z]{16}", normalise_password("gmail", password)))


def _cert_issuer(server) -> str:
    try:
        cert = server.sock.getpeercert()
        parts = dict(x[0] for x in cert.get("issuer", ()))
        return parts.get("organizationName") or parts.get("commonName") or ""
    except Exception:  # noqa: BLE001 - informational only
        return ""


# Programs known to scan e-mail traffic on Windows (process name -> product)
_SECURITY_PROCESSES = {
    "avastsvc.exe": "Avast", "avgsvc.exe": "AVG", "avp.exe": "Kaspersky", "ekrn.exe": "ESET",
    "bdservicehost.exe": "Bitdefender", "vsserv.exe": "Bitdefender", "mcshield.exe": "McAfee",
    "mfefire.exe": "McAfee", "nortonsecurity.exe": "Norton", "ns.exe": "Norton", "scanner.exe": "Quick Heal",
    "emlproxy.exe": "Quick Heal (email protection)", "quhlsvc.exe": "Quick Heal", "k7tsmngr.exe": "K7 Security",
    "k7emlpxy.exe": "K7 Security (email proxy)", "k7rtscan.exe": "K7 Security", "sophosui.exe": "Sophos",
    "savservice.exe": "Sophos", "fortitray.exe": "FortiClient", "fortiproxy.exe": "FortiClient (proxy)",
    "psanhost.exe": "Panda", "wrsa.exe": "Webroot", "mbamservice.exe": "Malwarebytes", "seqrite": "Seqrite",
    "npcsvc.exe": "Net Protector", "netskope": "Netskope", "zsatunnel.exe": "Zscaler",
}


def running_security_software() -> list[str]:
    """Names of antivirus / proxy products running on this Windows PC (best effort, for the connection test)."""
    if not sys.platform.startswith("win"):
        return []
    import subprocess

    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=10,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.lower()
    except Exception:  # noqa: BLE001
        return []
    found = [name for proc, name in _SECURITY_PROCESSES.items() if proc in out]
    return sorted(set(found))


class SmtpMailer:
    """Send through any SMTP account. ``factory`` can be injected for tests."""

    def __init__(self, settings: SmtpSettings, password: str, sender_name: str, sender_email: str,
                 factory: Callable | None = None, timeout: int = 30):
        self.settings = settings
        self.password = password
        self.sender_name = sender_name
        self.sender_email = sender_email
        self._factory = factory
        self.timeout = timeout
        self._server = None

    def _open(self, host: str, port: int, security: str, local_hostname: str | None):
        import smtplib
        import ssl

        context = ssl.create_default_context()
        if security == "SSL":
            return smtplib.SMTP_SSL(host, port, timeout=self.timeout, context=context, local_hostname=local_hostname)
        server = smtplib.SMTP(host, port, timeout=self.timeout, local_hostname=local_hostname)
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        return server

    def _attempts(self) -> list[tuple[int, str, str | None]]:
        """Configured setting first; then the other standard port, and a plain EHLO name. Some networks and
        antivirus 'mail shields' drop one port/mode but allow the other."""
        s = self.settings
        first = (int(s.port), s.security, None)
        other = (587, "STARTTLS") if s.security == "SSL" else (465, "SSL")
        attempts = [first, (first[0], first[1], "localhost")]
        if s.host.lower() in KNOWN_DUAL_PORT_HOSTS:
            attempts += [(other[0], other[1], None), (other[0], other[1], "localhost")]
        return attempts

    def _connect(self):
        if self._server is not None:
            return
        import smtplib

        s = self.settings
        problems = s.validate()
        if not self.password:
            problems.append("Enter the email account password (for Gmail: an App Password).")
        if problems:
            raise MailerError(" ".join(problems))
        password = normalise_password(s.host, self.password)
        tried, last_exc, server = [], None, None
        if self._factory is not None:
            server = self._factory(s)
        else:
            for port, security, helo in self._attempts():
                try:
                    server = self._open(s.host, port, security, helo)
                    self.used = (port, security)
                    break
                except (OSError, smtplib.SMTPException) as exc:
                    tried.append(f"{port}/{security}: {exc.__class__.__name__} {str(exc)[:80]}".strip())
                    last_exc = exc
                    log.info("SMTP connect %s:%s %s failed: %s", s.host, port, security, exc)
        if server is None:
            import socket
            import ssl

            if isinstance(last_exc, socket.gaierror):
                why = (f"The computer could not look up {s.host} (no internet, a typing mistake in the server name, "
                       "or a network that allows only web browsing through a proxy).")
            elif isinstance(last_exc, ssl.SSLCertVerificationError):
                why = ("The server's security certificate was replaced on this computer - usually antivirus email "
                       "scanning or a company proxy.")
            elif isinstance(last_exc, (TimeoutError, ConnectionRefusedError, socket.timeout)):
                why = "The mail ports 465 and 587 are blocked by a firewall, VPN or the office network."
            else:
                why = ("The connection was closed before the password was checked - typically antivirus email "
                       "protection, a company firewall or a VPN blocking mail traffic.")
            raise MailerError(f"Could not connect to {s.host}. {why} Tried: " + "; ".join(tried) +
                              ". Try another network (e.g. a mobile hotspot) to confirm, then ask IT / switch off the "
                              "antivirus email shield for this app; or use Outlook / .eml delivery.") from last_exc
        try:
            server.login(s.username.strip(), password)
        except smtplib.SMTPAuthenticationError as exc:
            hint = (" For Gmail, turn on 2-Step Verification and use an App Password (Google Account > Security > "
                    "App passwords - 16 letters), not your normal Gmail password." if "gmail" in s.host.lower() else
                    " Check the user name and password. Some Microsoft 365 organisations switch off password "
                    "(SMTP AUTH) sign-in - ask IT or use Outlook delivery.")
            self._quit(server)
            raise MailerError(f"The email server rejected the login.{hint}") from exc
        except (OSError, smtplib.SMTPException) as exc:
            self._quit(server)
            raise MailerError(f"Sign-in to {s.host} failed ({exc.__class__.__name__}: {str(exc)[:120]}).") from exc
        self._server = server

    @staticmethod
    def _quit(server):
        try:
            server.quit()
        except Exception:
            pass

    def diagnose(self) -> list[tuple[str, bool, str]]:
        """Step-by-step connection test for the 'Test sign-in' button: name lookup, network connection on each
        port, secure (TLS) handshake, server greeting, sign-in. Each step says plainly what a failure means."""
        import smtplib
        import socket
        import ssl

        s = self.settings
        steps: list[tuple[str, bool, str]] = []
        try:
            addrs = sorted({a[4][0] for a in socket.getaddrinfo(s.host, None, proto=socket.IPPROTO_TCP)})
            steps.append(("Find the server", True, f"{s.host} -> {', '.join(addrs[:3])}"))
        except OSError as exc:
            steps.append(("Find the server", False, f"{exc}. The computer cannot look up {s.host}: no internet, a "
                                                    "typing mistake in the server name, or a network that only "
                                                    "allows web browsing through a proxy."))
            return steps
        ports = [(int(s.port), s.security)]
        if s.host.lower() in KNOWN_DUAL_PORT_HOSTS:
            ports.append((587, "STARTTLS") if s.security == "SSL" else (465, "SSL"))
        signed_in = False
        intercepted_any = False
        for port, security in ports:
            name = f"Port {port} ({security})"
            try:
                sock = socket.create_connection((s.host, port), timeout=self.timeout)
                sock.close()
            except OSError as exc:
                steps.append((f"{name}: connect", False, f"{exc.__class__.__name__}: {exc}. The port is blocked by a "
                                                         "firewall, VPN or the office network."))
                continue
            steps.append((f"{name}: connect", True, "network connection opened"))
            try:
                server = self._open(s.host, port, security, None)
            except ssl.SSLCertVerificationError as exc:
                steps.append((f"{name}: secure handshake", False,
                              f"{exc}. The server's certificate was replaced on this computer - typically an "
                              "antivirus 'email shield' or a company proxy scanning encrypted mail. Switch off SSL/"
                              "email scanning for this app in the antivirus, or ask IT."))
                continue
            except (OSError, smtplib.SMTPException) as exc:
                steps.append((f"{name}: secure handshake / greeting", False,
                              f"{exc.__class__.__name__}: {str(exc)[:150]}. The connection opened but was closed "
                              "before the server greeted us - this is what antivirus email protection (e.g. Avast, "
                              "AVG, ESET, Kaspersky mail shield), a company firewall or a VPN does to mail traffic. "
                              "The password was not checked yet."))
                continue
            steps.append((f"{name}: secure handshake / greeting", True, "server answered"))
            # Who issued the security certificate? Gmail's is issued by Google. Any other issuer means a
            # program on this computer or the network is opening and re-encrypting the mail traffic.
            issuer = _cert_issuer(server)
            intercepted = bool(issuer) and "google" in s.host.lower() and "google" not in issuer.lower()
            intercepted_any = intercepted_any or intercepted
            if issuer:
                steps.append((f"{name}: certificate", not intercepted,
                              f"issued by {issuer}" + (" - NOT Google: mail traffic is being intercepted by "
                                                       "security software or a company firewall" if intercepted
                                                       else "")))
            try:
                server.ehlo_or_helo_if_needed()
                auth = server.has_extn("auth")
                steps.append((f"{name}: introduce (EHLO)", True,
                              "server offers sign-in" if auth else "server did NOT offer sign-in (AUTH)"))
            except (OSError, smtplib.SMTPException) as exc:
                steps.append((f"{name}: introduce (EHLO)", False, f"{exc.__class__.__name__}: {str(exc)[:150]}"))
                self._quit(server)
                continue
            if signed_in:
                self._quit(server)
                continue
            password = normalise_password(s.host, self.password)
            try:
                server.login(s.username.strip(), password)
                steps.append((f"{name}: sign in", True, f"signed in as {s.username}"))
                signed_in = True
            except smtplib.SMTPAuthenticationError as exc:
                msg = exc.smtp_error.decode(errors="replace") if isinstance(exc.smtp_error, bytes) else str(exc)
                steps.append((f"{name}: sign in", False,
                              f"{msg[:160]}. The server rejected the user name / password. Gmail needs the "
                              f"16-letter App Password (you entered {len(password)} characters)."))
            except smtplib.SMTPServerDisconnected as exc:
                steps.append((f"{name}: sign in", False,
                              f"{exc}. The connection was cut when the password was sent"
                              + (f" (you entered {len(password)} characters" + (
                                  "; a Gmail App Password is exactly 16 letters - your normal Gmail password "
                                  "cannot be used by apps)" if "gmail" in s.host.lower()
                                  and not looks_like_gmail_app_password(password) else ")")) + "."))
            except (OSError, smtplib.SMTPException) as exc:
                steps.append((f"{name}: sign in", False, f"{exc.__class__.__name__}: {str(exc)[:150]}"))
            self._quit(server)
        if not signed_in:
            found = running_security_software()
            if found and intercepted_any:
                steps.append(("Security software running", False,
                              ", ".join(found) + " - it is intercepting mail: switch off its email / SSL "
                                                 "scanning for this app (see README)."))
            elif found:
                steps.append(("Security software running", True,
                              ", ".join(found) + " - not intercepting (the certificate is the server's own)."))
        return steps

    @staticmethod
    def diagnosis_text(steps: list[tuple[str, bool, str]]) -> str:
        return "\n".join(f"{'OK  ' if ok else 'FAIL'}  {step}: {detail}" for step, ok, detail in steps)

    def test(self) -> str:
        self._connect()
        port, security = getattr(self, "used", (self.settings.port, self.settings.security))
        self.close()
        note = "" if (port, security) == (int(self.settings.port), self.settings.security) else \
            f" (port {self.settings.port} was blocked; port {port} {security} worked and will be used)"
        return f"Signed in to {self.settings.host} as {self.settings.username}{note}."

    def deliver(self, message: EmailMessage) -> None:
        import smtplib

        self._connect()
        mime = build_mime(message, self.sender_name, self.sender_email)
        try:
            self._server.send_message(mime)
        except smtplib.SMTPServerDisconnected:
            self._server = None  # one reconnect attempt
            self._connect()
            self._server.send_message(mime)
        except smtplib.SMTPRecipientsRefused as exc:
            raise MailerError("The server refused this recipient address.") from exc
        except (OSError, smtplib.SMTPException) as exc:
            raise MailerError(f"Sending failed: {str(exc)[:200]}") from exc

    def close(self) -> None:
        if self._server is not None:
            try:
                self._server.quit()
            except Exception:
                pass
            self._server = None


# ------------------------------------------------------------ .eml files ---
def _safe_name(text: str) -> str:
    return re.sub(r"[^\w\-]+", "_", text).strip("_")[:60] or "email"


def save_eml(message: EmailMessage, folder: str | Path, sender_name: str, sender_email: str) -> Path:
    """Write an unsent email (.eml) that Outlook can open, review and send."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    mime = build_mime(message, sender_name, sender_email, unsent=True)
    path = folder / f"{_safe_name(message.to_name)}_{_safe_name(message.to_email)}.eml"
    path.write_bytes(bytes(mime))
    return path


# ------------------------------------------------------------- audit log ---
AUDIT_FIELDS = ["Timestamp", "Approved by", "Sender email", "Judgment file", "Case title", "Register ref", "Subject",
                "Recipient name", "Recipient email", "Recipient group", "Delivery", "Status", "Error",
                "Content fingerprint"]


AUDIT_FILE_NAME = "email_audit_log.csv"


def downloads_dir() -> Path:
    """The user's Downloads folder (honours a redirected/OneDrive Downloads folder on Windows)."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                            ("Data4", wintypes.BYTE * 8)]

            # FOLDERID_Downloads {374DE290-123F-4565-9164-39C4925E467B}
            fid = GUID(0x374DE290, 0x123F, 0x4565,
                       (wintypes.BYTE * 8)(*[b - 256 if b > 127 else b for b in
                                             (0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B)]))
            buf = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(fid), 0, None, ctypes.byref(buf)) == 0:
                path = Path(buf.value)
                ctypes.windll.ole32.CoTaskMemFree(buf)
                if path.is_dir():
                    return path
        except Exception as exc:  # fall back to the conventional location
            log.info("Could not resolve the Downloads folder: %s", exc)
    path = Path.home() / "Downloads"
    return path if path.is_dir() else Path.home()


def default_audit_dir() -> Path:
    override = os.environ.get("JIA_AUDIT_DIR")  # used by tests / IT pre-configuration
    return Path(override) if override else downloads_dir()


def audit_log_path(folder: str | Path | None = None) -> Path:
    """Audit log file inside ``folder`` (the Downloads folder when not set)."""
    base = Path(folder) if folder else default_audit_dir()
    return base / AUDIT_FILE_NAME


def carry_over_audit(dest: Path) -> Path | None:
    """If ``dest`` doesn't exist yet, copy the log written by earlier versions (app data folder or,
    on Windows, the old AppData location) so earlier rows aren't lost. Returns the source copied."""
    if dest.exists():
        return None
    import shutil

    candidates = [user_config_dir() / AUDIT_FILE_NAME]
    if sys.platform.startswith("win"):
        candidates.append(Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
                          / "JudgmentInsightAnalyzer" / AUDIT_FILE_NAME)
    for src in candidates:
        try:
            if src.is_file() and src.resolve() != dest.resolve():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                log.info("Copied earlier audit log to %s", dest)
                return src
        except OSError as exc:
            log.info("Could not copy earlier audit log from %s: %s", src, exc)
    return None


def read_audit_rows(path: str | Path) -> list[dict]:
    """Read the audit log whatever its layout. Older logs have a 12-column header (no 'Register ref' /
    'Recipient group') with 14-column rows appended under it. Each row is
    matched by its own length: rows with as many values as the header use the header, rows with as many
    values as the current layout use the current column order."""
    with Path(path).open(newline="", encoding="utf-8-sig") as fh:
        raw = [r for r in csv.reader(fh) if any(c.strip() for c in r)]
    if not raw:
        return []
    header, out = raw[0], []
    for row in raw[1:]:
        if len(row) == len(AUDIT_FIELDS) and (len(row) != len(header) or header == AUDIT_FIELDS):
            out.append(dict(zip(AUDIT_FIELDS, row)))
        elif len(row) == len(header):
            out.append(dict(zip(header, row)))
        else:  # unexpected shape: keep everything, in order, rather than lose data
            keys = AUDIT_FIELDS if len(row) > len(header) else header
            out.append(dict(zip(keys, row)))
    return out


def repair_audit_log(path: str | Path) -> bool:
    """If the log's header is not the current one, rewrite it with the current header and every row in the
    right columns. The original file is kept as a backup. Returns True if the file was repaired."""
    path = Path(path)
    if not path.exists():
        return False
    with path.open(newline="", encoding="utf-8-sig") as fh:
        header = next(csv.reader(fh), [])
    if header == AUDIT_FIELDS:
        return False
    rows = read_audit_rows(path)
    import shutil
    from datetime import datetime

    backup = path.with_name(f"{path.stem}_before_repair_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}")
    shutil.copy2(path, backup)
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=AUDIT_FIELDS, extrasaction="ignore", restval="")
        writer.writeheader()
        writer.writerows(rows)
    log.info("Audit log header repaired (%d rows); original kept as %s", len(rows), backup.name)
    return True


def append_audit(rows: list[dict], path: Path | None = None) -> Path:
    path = Path(path) if path else audit_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    repair_audit_log(path)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=AUDIT_FIELDS, extrasaction="ignore")
        if new:
            writer.writeheader()
        writer.writerows(rows)
    return path


def audit_xlsx_path(csv_path: Path) -> Path:
    return Path(csv_path).with_suffix(".xlsx")


def write_audit_xlsx(csv_path: str | Path) -> Path | None:
    """Formatted Excel copy of the audit log (table with borders, bold header, filters), rebuilt from the
    CSV - the CSV stays the master record because it can be appended safely. Returns None if the Excel
    copy is open (locked) or cannot be written; the CSV is still complete."""
    from openpyxl import Workbook

    from .recipients import style_table

    csv_path = Path(csv_path)
    if not csv_path.exists():
        return None
    records = read_audit_rows(csv_path)
    rows = [AUDIT_FIELDS] + [[rec.get(k, "") for k in AUDIT_FIELDS] for rec in records]
    wb = Workbook()
    ws = wb.active
    ws.title = "Email audit log"
    for row in rows:
        ws.append(row)
    widths = {"Timestamp": 18, "Approved by": 18, "Sender email": 28, "Judgment file": 30, "Case title": 40,
              "Register ref": 15, "Subject": 50, "Recipient name": 24, "Recipient email": 30,
              "Recipient group": 14, "Delivery": 16, "Status": 10, "Error": 40, "Content fingerprint": 20}
    head = rows[0]
    wrap = [i + 1 for i, h in enumerate(head) if h in ("Case title", "Subject", "Error")]
    style_table(ws, len(head), data_rows=max(len(rows) - 1, 1), widths=[widths.get(h, 16) for h in head],
                wrap_cols=wrap)
    from openpyxl.styles import Font

    status_col = head.index("Status") + 1 if "Status" in head else None
    if status_col:
        for r in range(2, len(rows) + 1):
            cell = ws.cell(r, status_col)
            cell.font = Font(bold=True, color="1E7B3A" if str(cell.value).lower() in ("ok", "sent", "created",
                                                                                       "saved", "success")
                             else "C62828")
    out = audit_xlsx_path(csv_path)
    try:
        wb.save(out)
    except OSError as exc:  # open in Excel
        log.info("Formatted audit log not refreshed (%s)", exc)
        return None
    return out


# ------------------------------------------------------------ batch send ---
def deliver_batch(
    messages: list[EmailMessage],
    mode: str,
    audit_base: dict,
    outlook: OutlookMailer | None = None,
    eml_folder: str | Path | None = None,
    progress: Callable[[int, int, str], None] | None = None,
    cancel_event: threading.Event | None = None,
    pause_s: float = 0.4,
    audit_path: str | Path | None = None,
    on_warning: Callable[[str], None] | None = None,
    smtp: SmtpMailer | None = None,
    groups: list[str] | None = None,
) -> list[DeliveryResult]:
    """Deliver one message per recipient, record every outcome in the audit log."""
    results: list[DeliveryResult] = []
    audit_rows: list[dict] = []
    total = len(messages)
    try:
        for i, msg in enumerate(messages, 1):
            if cancel_event is not None and cancel_event.is_set():
                raise CancelledError()
            if progress:
                progress(i - 1, total, f"Preparing email {i} of {total} ({msg.to_name})...")
            try:
                if mode == MODE_SMTP or (mode == MODE_TEST and smtp is not None):
                    if smtp is None:
                        raise MailerError("No email account has been set up.")
                    smtp.deliver(msg)
                elif mode in (MODE_DRAFT, MODE_SEND, MODE_TEST):
                    if outlook is None:
                        raise MailerError("Outlook is not available.")
                    outlook.deliver(msg, send=mode in (MODE_SEND, MODE_TEST))
                elif mode == MODE_EML:
                    save_eml(msg, eml_folder or ".", audit_base.get("Approved by", ""),
                             audit_base.get("Sender email", ""))
                else:
                    raise MailerError(f"Unknown delivery mode: {mode}")
                results.append(DeliveryResult(msg.to_name, msg.to_email, True))
            except MailerError as exc:
                results.append(DeliveryResult(msg.to_name, msg.to_email, False, str(exc)))
                group = groups[i - 1] if groups and i <= len(groups) else ""
                if i == 1 and ("Could not start Outlook" in str(exc) or "rejected the login" in str(exc)
                               or "Could not connect" in str(exc) or "Enter the" in str(exc)):
                    # No point trying the rest if the mail program / server can't be used at all.
                    audit_rows.append(_audit_row(audit_base, msg, mode, results[-1], group))
                    break
            group = groups[i - 1] if groups and i <= len(groups) else ""
            audit_rows.append(_audit_row(audit_base, msg, mode, results[-1], group))
            if pause_s and i < total:
                time.sleep(pause_s)
        if progress:
            progress(total, total, "Done.")
    finally:
        if smtp is not None:
            smtp.close()
        if audit_rows:
            try:
                written = append_audit(audit_rows, audit_path)
                if write_audit_xlsx(written) is None and on_warning:
                    on_warning("The Excel copy of the audit log is open - close it to refresh it (the log itself "
                               "was saved).")
            except OSError as exc:
                # e.g. file open in Excel (locked) or folder offline: keep a copy in the app data folder.
                fallback = user_config_dir() / AUDIT_FILE_NAME
                log.error("Could not write audit log %s (%s); writing to %s instead", audit_path, exc, fallback)
                append_audit(audit_rows, fallback)
                if on_warning:
                    on_warning(f"The audit log could not be updated (is it open in Excel?). This batch was "
                               f"recorded in {fallback} instead.")
    log.info("Email batch: mode=%s, %d ok, %d failed", mode, sum(r.ok for r in results),
             sum(not r.ok for r in results))
    return results


def _audit_row(base: dict, msg: EmailMessage, mode: str, result: DeliveryResult, group: str = "") -> dict:
    return {
        **base,
        "Recipient group": group,
        "Timestamp": datetime.now().strftime("%d %b %Y %H:%M:%S"),
        "Subject": msg.subject,
        "Recipient name": msg.to_name,
        "Recipient email": msg.to_email,
        "Delivery": mode,
        "Status": "OK" if result.ok else "FAILED",
        "Error": result.error,
    }
