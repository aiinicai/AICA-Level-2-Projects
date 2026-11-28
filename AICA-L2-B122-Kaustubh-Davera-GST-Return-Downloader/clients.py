"""Read / validate / update the client list Excel file."""
import re
from dataclasses import dataclass, field, asdict
from datetime import date, datetime

import openpyxl

HEADER_ALIASES = {
    "gstin": ["gstin", "gst no", "gstno", "gst number", "gstin no"],
    "name": ["name", "client name", "party name", "legal name", "client"],
    "trade_name": ["trade name", "tradename", "trade"],
    "email": ["email", "email id", "emailid", "e mail", "e mail id", "mail id", "mail"],
    "login_id": ["login id", "loginid", "user id", "userid", "username", "user name", "login"],
    "password": ["password", "pass", "pwd"],
    "filing": ["filing", "filing type", "return type", "frequency", "monthly quarterly"],
    "pwd_updated": ["password updated", "pwd updated", "password changed", "password date",
                    "password updated on"],
}
HEADER_TITLES = {
    "gstin": "GSTIN", "name": "Name", "trade_name": "Trade Name", "email": "Email ID",
    "login_id": "Login ID", "password": "Password", "filing": "Filing",
    "pwd_updated": "Password Updated",
}
REQUIRED = ("gstin", "login_id", "password")
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
EMAIL_RE = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$")
DATE_FMT = "%d-%b-%Y"


class ClientFileError(Exception):
    pass


@dataclass
class Client:
    gstin: str
    name: str
    trade_name: str = ""
    email: str = ""
    login_id: str = ""
    password: str = ""
    filing: str = "Monthly"
    pwd_updated: str = ""
    row: int = 0
    issues: list = field(default_factory=list)   # [(level, message)] level: error|warn

    @property
    def display_name(self) -> str:
        return self.trade_name or self.name or self.gstin

    @property
    def quarterly(self) -> bool:
        return self.filing.strip().lower().startswith("q")

    @property
    def has_error(self) -> bool:
        return any(lvl == "error" for lvl, _ in self.issues)

    def emails(self) -> list[str]:
        return [e.strip() for e in re.split(r"[,;]", self.email or "") if e.strip()]

    def pwd_age_days(self) -> int | None:
        if not self.pwd_updated:
            return None
        try:
            d = datetime.strptime(self.pwd_updated, DATE_FMT).date()
        except ValueError:
            return None
        return (date.today() - d).days

    def public(self) -> dict:
        """For the UI (no password)."""
        d = asdict(self)
        d.pop("password")
        d["display_name"] = self.display_name
        d["has_password"] = bool(self.password)
        d["pwd_age_days"] = self.pwd_age_days()
        return d


def _norm(s) -> str:
    return re.sub(r"[\s_\-./]+", " ", str(s or "")).strip().lower()


def _find_header(ws):
    for r in range(1, min(ws.max_row, 10) + 1):
        cmap = {}
        for c in range(1, ws.max_column + 1):
            n = _norm(ws.cell(r, c).value)
            if not n:
                continue
            for key, aliases in HEADER_ALIASES.items():
                if key not in cmap and n in aliases:
                    cmap[key] = c
                    break
        if all(k in cmap for k in REQUIRED):
            return r, cmap
    raise ClientFileError(
        "Could not find the header row. Row 1 must have these columns:\n"
        "GSTIN | Name | Trade Name | Email ID | Login ID | Password"
    )


def _text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def _password(v):
    """Return (password_string, issue_or_None). Never strips spaces."""
    if v is None:
        return "", None
    if isinstance(v, (datetime, date)):
        return str(v), "Password was converted to a date by Excel. Retype it with the column set to Text"
    if isinstance(v, bool):
        return str(v), "Password was converted to TRUE/FALSE by Excel. Retype it with the column set to Text"
    if isinstance(v, (int, float)):
        s = str(int(v)) if float(v).is_integer() else repr(v)
        return s, f"Password was converted to a number ({s}). Set the column to Text and retype it"
    return str(v), None


def _date_text(v) -> str:
    if isinstance(v, (datetime, date)):
        return v.strftime(DATE_FMT)
    s = _text(v)
    for fmt in (DATE_FMT, "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).strftime(DATE_FMT)
        except ValueError:
            pass
    return s


def load_clients(path: str) -> list[Client]:
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except FileNotFoundError:
        raise ClientFileError(f"Client file not found:\n{path}")
    except PermissionError:
        raise ClientFileError("The client Excel file is locked. Close it in Excel and try again.")
    ws = wb.worksheets[0]
    hdr, cmap = _find_header(ws)
    clients = []
    for r in range(hdr + 1, ws.max_row + 1):
        def get(key, raw=False):
            c = cmap.get(key)
            return ws.cell(r, c).value if c else None
        gstin = _text(get("gstin")).upper().replace(" ", "")
        if not gstin:
            continue
        pwd, pwd_issue = _password(get("password"))
        cl = Client(
            gstin=gstin,
            name=_text(get("name")) or gstin,
            trade_name=_text(get("trade_name")),
            email=_text(get("email")),
            login_id=_text(get("login_id")),
            password=pwd,
            filing=_text(get("filing")) or "Monthly",
            pwd_updated=_date_text(get("pwd_updated")),
            row=r,
        )
        if pwd_issue:
            cl.issues.append(("error", pwd_issue))
        clients.append(cl)
    wb.close()
    validate(clients)
    return clients


def validate(clients: list[Client]) -> None:
    seen = {}
    for c in clients:
        c.issues = [i for i in c.issues if i[1].startswith("Password was converted")]
        if not GSTIN_RE.match(c.gstin):
            c.issues.append(("warn", "GSTIN format looks wrong"))
        if not c.login_id:
            c.issues.append(("error", "Login ID missing"))
        if not c.password:
            c.issues.append(("error", "Password missing"))
        elif c.password != c.password.strip():
            c.issues.append(("error", "Password starts or ends with a space"))
        if not c.email:
            c.issues.append(("warn", "Email ID missing"))
        elif not all(EMAIL_RE.match(e) for e in c.emails()):
            c.issues.append(("warn", "Email ID looks wrong"))
        if c.gstin in seen:
            c.issues.append(("warn", f"Duplicate GSTIN (also row {seen[c.gstin]})"))
        else:
            seen[c.gstin] = c.row


def _ensure_column(ws, hdr, cmap, key):
    if key in cmap:
        return cmap[key]
    col = ws.max_column + 1
    ws.cell(hdr, col).value = HEADER_TITLES[key]
    cmap[key] = col
    return col


def _set_text(cell, value: str) -> None:
    """Write a value as plain text, even if it starts with = + - @ (no formula)."""
    cell.value = value
    cell.data_type = "s"
    cell.number_format = "@"
    if value[:1] in ("=", "+", "-", "@"):
        try:
            cell.quotePrefix = True
        except Exception:
            pass


def save_client(path: str, original_gstin: str | None, data: dict) -> None:
    """Update an existing row (found by original GSTIN) or append a new one.

    data keys: gstin, name, trade_name, email, login_id, password (optional: only
    written when not None), filing.
    """
    try:
        wb = openpyxl.load_workbook(path)
    except PermissionError:
        raise ClientFileError("The client Excel file is open in Excel. Close it and click Save again.")
    ws = wb.worksheets[0]
    hdr, cmap = _find_header(ws)

    row = None
    if original_gstin:
        gcol = cmap["gstin"]
        for r in range(hdr + 1, ws.max_row + 1):
            if _text(ws.cell(r, gcol).value).upper().replace(" ", "") == original_gstin.upper():
                row = r
                break
        if row is None:
            raise ClientFileError(f"GSTIN {original_gstin} not found in the Excel file. Click Reload.")
    else:
        new_gstin = (data.get("gstin") or "").upper().strip()
        gcol = cmap["gstin"]
        for r in range(hdr + 1, ws.max_row + 1):
            if _text(ws.cell(r, gcol).value).upper().replace(" ", "") == new_gstin:
                raise ClientFileError(f"GSTIN {new_gstin} already exists (row {r}).")
        row = ws.max_row + 1

    for key in ("gstin", "name", "trade_name", "email", "login_id", "filing"):
        if key in data and data[key] is not None:
            col = _ensure_column(ws, hdr, cmap, key)
            val = str(data[key]).strip()
            if key == "gstin":
                val = val.upper().replace(" ", "")
            _set_text(ws.cell(row, col), val)

    pwd = data.get("password")
    if pwd is not None and pwd != "":
        col = cmap["password"]
        cell = ws.cell(row, col)
        _set_text(cell, str(pwd))      # stored exactly as typed, as text
        ucol = _ensure_column(ws, hdr, cmap, "pwd_updated")
        ws.cell(row, ucol).value = date.today().strftime(DATE_FMT)
        ws.cell(row, ucol).number_format = "@"

    try:
        wb.save(path)
    except PermissionError:
        raise ClientFileError("The client Excel file is open in Excel. Close it and click Save again.")
    finally:
        wb.close()


def create_template(path: str) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clients"
    heads = ["GSTIN", "Name", "Trade Name", "Email ID", "Login ID", "Password", "Filing", "Password Updated"]
    ws.append(heads)
    for col, w in zip("ABCDEFGH", (20, 32, 28, 32, 18, 18, 12, 18)):
        ws.column_dimensions[col].width = w
    for r in range(1, 1001):
        ws.cell(r, 6).number_format = "@"   # Password column as Text
        ws.cell(r, 8).number_format = "@"
    ws.freeze_panes = "A2"
    wb.save(path)
