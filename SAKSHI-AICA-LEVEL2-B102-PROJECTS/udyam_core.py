"""
Udyam (MSME) verification engine - no GUI code in this module.
==============================================================

The parsing, classification and portal-request logic below is carried over
unchanged from the original udyam_verifier.py (Tkinter version).  Only the
CSV input/output helpers that used to live inside the Tkinter App class were
moved into the ResultsStore class at the bottom so that any GUI can use them.

    Official portal : https://udyamregistration.gov.in/
    Verify page     : Home > Print/Verify > Verify Udyam Registration
                      (https://udyamregistration.gov.in/Udyam_Verify.aspx)

The app never solves, guesses or outsources CAPTCHAs, never logs in, makes one
request at a time only when the user presses a button, and waits a few seconds
between lookups.  Verification needs an internet connection.
"""

import csv
import html
import http.cookiejar
import os
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

# --------------------------------------------------------------------------
# Portal constants (verified against the live portal, October 2026)
# --------------------------------------------------------------------------
PORTAL_HOME = "https://udyamregistration.gov.in/Default.aspx"
PORTAL_ROOT = "https://udyamregistration.gov.in/"
VERIFY_URL = "https://udyamregistration.gov.in/Udyam_Verify.aspx"
CAPTCHA_URL = "https://udyamregistration.gov.in/CaptchaControl.aspx"

FIELD_UDYAM = "ctl00$ContentPlaceHolder1$txtUdyamNo"
FIELD_CAPTCHA = "ctl00$ContentPlaceHolder1$txtCaptcha"
FIELD_BUTTON = "ctl00$ContentPlaceHolder1$btnVerify"
BUTTON_VALUE = "Verify"

TIMEOUT_SECONDS = 25
MIN_SECONDS_BETWEEN_LOOKUPS = 4      # be gentle with the portal
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

UDYAM_PATTERN = re.compile(r"^UDYAM-[A-Z]{2}-\d{2}-\d{7}$")

OUTPUT_NAME = "udyam_extractedresults.csv"
OUTPUT_COLUMNS = [
    "udyam_number", "enterprise_name", "enterprise_type", "organisation_type",
    "major_activity", "social_category", "date_of_registration",
    "enterprise_address", "status", "error",
]
DETAIL_COLUMNS = OUTPUT_COLUMNS[1:8]

# Friendly captions for the columns (GUI and Excel only - CSV keeps the keys).
COLUMN_TITLES = {
    "udyam_number": "Udyam Registration No.",
    "enterprise_name": "Name of Enterprise",
    "enterprise_type": "Type of Enterprise",
    "organisation_type": "Type of Organisation",
    "major_activity": "Major Activity",
    "social_category": "Social Category",
    "date_of_registration": "Date of Udyam Registration",
    "enterprise_address": "Official Address of Enterprise",
    "status": "Status",
    "error": "Remarks / Error",
}

# Label text on the portal's result page -> our column.  Matching is done on
# lower-cased labels with punctuation removed; the first matching rule wins.
LABEL_RULES = [
    ("enterprise_name", ["name of enterprise", "name of the enterprise",
                         "enterprise name", "name of unit"]),
    ("organisation_type", ["type of organisation", "type of organization",
                           "organisation type", "organization type"]),
    ("major_activity", ["major activity"]),
    ("social_category", ["social category"]),
    ("date_of_registration", ["date of udyam registration",
                              "date of registration", "registration date",
                              "udyam registration date"]),
    ("enterprise_address", ["official address of enterprise",
                            "official address", "address of enterprise",
                            "enterprise address", "address"]),
]

# Generic one-word labels only count on an exact match (so that e.g.
# "Address of Plant" is not mistaken for the enterprise address).
EXACT_ONLY = {"address"}

# Text the portal may show when the CAPTCHA or the number is rejected.
CAPTCHA_ERROR_HINTS = ["captcha", "verification code", "security code"]
CAPTCHA_ERROR_WORDS = ["invalid", "incorrect", "wrong", "mismatch",
                       "not match", "enter valid", "does not match"]
NOT_FOUND_HINTS = ["not found", "no record", "does not exist", "not exist",
                   "invalid udyam", "not valid", "no data", "not registered",
                   "invalid registration"]


def downloads_folder():
    """Return the user's Downloads folder (falls back to home folder)."""
    path = Path.home() / "Downloads"
    return path if path.is_dir() else Path.home()


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


def norm_label(text):
    text = clean(text).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalise_udyam(text):
    """Upper-case and tidy a typed number: spaces removed, '_'/'–' -> '-'.
    The result is still checked against UDYAM_PATTERN before any request."""
    s = (text or "").strip().upper()
    s = re.sub(r"\s+", "", s)
    return re.sub(r"[_‐-―]", "-", s)


# --------------------------------------------------------------------------
# HTML parsing (standard library html.parser only)
# --------------------------------------------------------------------------
class FormParser(HTMLParser):
    """Collects hidden inputs of the ASP.NET form and the captcha <img>."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = {}
        self.input_names = set()
        self.captcha_src = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "input" and a.get("name"):
            self.input_names.add(a["name"])
            if (a.get("type") or "").lower() == "hidden":
                self.hidden[a["name"]] = a.get("value") or ""
        elif tag == "img" and "captcha" in (a.get("id") or "").lower():
            self.captcha_src = a.get("src")


class ResultParser(HTMLParser):
    """Turns a page into table rows (lists of cell texts), alert() messages
    and visible text lines.  Nested tables are handled with a stack."""

    BLOCK_TAGS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4",
                  "h5", "h6", "table", "section"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.alerts = []
        self.lines = []
        self._line = []
        self._row_stack = []     # current rows (one per open <tr>)
        self._cell_stack = []    # current cells (one per open <td>/<th>)
        self._skip = 0           # inside <script>/<style>
        self._in_script = False
        self._script_buf = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
            self._in_script = tag == "script"
            self._script_buf = []
            return
        if tag in self.BLOCK_TAGS:
            self._flush_line()
        if tag == "tr":
            self._row_stack.append([])
        elif tag in ("td", "th"):
            self._cell_stack.append({"parts": [], "nested": []})

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            if self._in_script:
                js = "".join(self._script_buf)
                for m in re.finditer(r"alert\(\s*['\"](.+?)['\"]\s*\)", js):
                    self.alerts.append(clean(m.group(1)))
            self._skip = max(0, self._skip - 1)
            self._in_script = False
            return
        if tag in ("td", "th") and self._cell_stack:
            cell = self._cell_stack.pop()
            if cell["nested"]:
                # a table inside this cell (e.g. a multi-line address):
                # keep it readable as "Label: value; Label: value"
                text = "; ".join(": ".join(c for c in r if c)
                                 for r in cell["nested"])
            else:
                text = clean(" ".join(cell["parts"]))
            if self._row_stack:
                self._row_stack[-1].append(text)
        elif tag == "tr" and self._row_stack:
            row = self._row_stack.pop()
            if any(row):
                self.rows.append(row)
                if self._cell_stack:      # row of a table nested in a cell
                    self._cell_stack[-1]["nested"].append(row)
        if tag in self.BLOCK_TAGS:
            self._flush_line()

    def handle_data(self, data):
        if self._skip:
            if self._in_script:
                self._script_buf.append(data)
            return
        if self._cell_stack:
            self._cell_stack[-1]["parts"].append(data)
        self._line.append(data)

    def _flush_line(self):
        text = clean(" ".join(self._line))
        if text:
            self.lines.append(text)
        self._line = []

    def close(self):
        super().close()
        self._flush_line()


def map_label(label):
    n = norm_label(label)
    if not n or len(n) > 60:
        return None
    for column, phrases in LABEL_RULES:
        for phrase in phrases:
            if phrase in EXACT_ONLY:
                hit = n == phrase
            else:
                hit = n == phrase or n.startswith(phrase) or phrase in n
            if hit:
                # avoid "email address"/"address line" style false hits
                if column == "enterprise_address" and any(
                        w in n for w in ("email", "e mail", "web")):
                    continue
                return column
    return None


def extract_details(page_html):
    """Return (details_dict, messages, visible_text)."""
    p = ResultParser()
    p.feed(page_html)
    p.close()
    details = {c: "" for c in DETAIL_COLUMNS}

    # 1) table rows: label, value, label, value, ...
    for row in p.rows:
        cells = [c for c in row]
        for i in range(len(cells) - 1):
            col = map_label(cells[i])
            value = cells[i + 1].strip(" :")
            if col and value and not details[col] and not map_label(value):
                details[col] = value

    # 2) "Label : Value" text lines, or label on one line and value next
    for i, line in enumerate(p.lines):
        if ":" in line:
            label, _, value = line.partition(":")
            col = map_label(label)
            if col and not details[col] and clean(value):
                details[col] = clean(value)
                continue
        col = map_label(line)
        if col and not details[col] and i + 1 < len(p.lines):
            nxt = p.lines[i + 1].strip(" :")
            if nxt and not map_label(nxt):
                details[col] = nxt

    # 3) Micro / Small / Medium - read separately so the rules above are
    #    untouched (the portal shows it in its own small table)
    details["enterprise_type"] = find_enterprise_type(p.rows, p.lines)

    messages = list(p.alerts)
    visible = "\n".join(p.lines)
    return details, messages, visible


# Type of enterprise (MSME classification).  Only these three values are
# accepted, so a neighbouring header or date can never be taken by mistake.
ENTERPRISE_TYPES = {"micro": "Micro", "small": "Small", "medium": "Medium"}
TYPE_LABELS = {"enterprise type", "type of enterprise", "enterprise category",
               "category of enterprise", "msme type", "type of msme",
               "classification", "msme classification"}
YEAR_RE = re.compile(r"(19|20)\d{2}")


def _msme_type(text):
    n = norm_label(text)
    n = re.sub(r"\b(enterprise|enterprises|unit)\b", "", n).strip()
    return ENTERPRISE_TYPES.get(n)


def find_enterprise_type(rows, lines):
    """Return 'Micro', 'Small', 'Medium' or ''.

    The verify page lists one row per classification year, e.g.
        Sl No | Classification Year | Enterprise Type | Classification Date
        1     | 2020-21             | Micro           | 29/06/2020
        2     | 2023-24             | Small           | 01/04/2023
    The row with the latest classification year is the current type."""
    # a) header row naming the column, then data rows below it
    found = []                          # (year, order, type)
    for h, header in enumerate(rows):
        names = [norm_label(c) for c in header]
        col = next((j for j, c in enumerate(names) if c in TYPE_LABELS), None)
        if col is None:
            continue
        ycol = next((j for j, c in enumerate(names) if "year" in c), None)
        for k, row in enumerate(rows[h + 1:], start=h + 1):
            if len(row) <= col:
                continue
            kind = _msme_type(row[col])
            if not kind:
                continue
            year = ""
            if ycol is not None and len(row) > ycol:
                m = YEAR_RE.search(row[ycol])
                year = m.group(0) if m else ""
            found.append((year, k, kind))
        if found:
            break
    if found:
        return max(found)[2]            # latest year, else last row

    # b) "Enterprise Type | Small" side by side in a table row
    for row in rows:
        for i in range(len(row) - 1):
            if norm_label(row[i]) in TYPE_LABELS:
                kind = _msme_type(row[i + 1].strip(" :"))
                if kind:
                    return kind

    # c) "Enterprise Type : Small" or label and value on consecutive lines
    for i, line in enumerate(lines):
        label, sep, value = line.partition(":")
        if sep and norm_label(label) in TYPE_LABELS and _msme_type(value):
            return _msme_type(value)
        if norm_label(line) in TYPE_LABELS and i + 1 < len(lines):
            kind = _msme_type(lines[i + 1].strip(" :"))
            if kind:
                return kind
    return ""


# Static instruction text on the verify page - never treat as an error.
INSTRUCTION_PATTERNS = [
    r"^enter (your|valid)", r"case sensitive", r"^click on verify",
    r"^instructions", r"^\[code", r"^verification code$",
]


def is_instruction(line):
    low = line.lower().strip()
    return any(re.search(p, low) for p in INSTRUCTION_PATTERNS)


def classify_failure(messages, visible):
    """Look for portal messages about a wrong CAPTCHA or unknown number."""
    lines = [l for l in visible.split("\n") if not is_instruction(l)]
    for msg in messages + lines:
        low = msg.lower()
        if any(h in low for h in CAPTCHA_ERROR_HINTS) and any(
                w in low for w in CAPTCHA_ERROR_WORDS):
            return "captcha", msg
    for msg in messages + lines:
        low = msg.lower()
        if any(h in low for h in NOT_FOUND_HINTS) and len(low) < 200:
            return "not_found", msg
    if messages:
        return "other", messages[0]
    return None, ""


# --------------------------------------------------------------------------
# Network client (one cookie-based session, mimicking the portal's own form)
# --------------------------------------------------------------------------
class PortalError(Exception):
    pass


class PortalClient:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        ctx = ssl.create_default_context()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            urllib.request.HTTPSHandler(context=ctx))
        self.hidden = {}
        self.form_ok = False

    def _request(self, url, data=None, referer=None):
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,image/png,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
        }
        if referer:
            headers["Referer"] = referer
        body = None
        if data is not None:
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            headers["Origin"] = "https://udyamregistration.gov.in"
        req = urllib.request.Request(url, data=body, headers=headers)
        try:
            with self.opener.open(req, timeout=TIMEOUT_SECONDS) as resp:
                raw = resp.read()
                ctype = resp.headers.get("Content-Type", "")
                return resp.geturl(), ctype, raw
        except urllib.error.HTTPError as e:
            raise PortalError(f"Portal returned HTTP {e.code} ({e.reason}).")
        except urllib.error.URLError as e:
            reason = e.reason
            if isinstance(reason, socket.timeout):
                raise PortalError("Network timeout - the portal did not respond.")
            raise PortalError(f"Network problem: {reason}")
        except (socket.timeout, TimeoutError):
            raise PortalError("Network timeout - the portal did not respond.")
        except ssl.SSLError as e:
            raise PortalError(f"Secure connection (SSL) problem: {e}")
        except OSError as e:
            raise PortalError(f"Connection problem: {e}")

    @staticmethod
    def _decode(raw, ctype):
        m = re.search(r"charset=([\w-]+)", ctype or "", re.I)
        enc = m.group(1) if m else "utf-8"
        try:
            return raw.decode(enc, errors="replace")
        except LookupError:
            return raw.decode("utf-8", errors="replace")

    def load_form(self):
        """Open the verify page and return the CAPTCHA PNG bytes."""
        url, ctype, raw = self._request(VERIFY_URL, referer=PORTAL_ROOT)
        if "udyam_verify" not in url.lower():
            # The portal sends direct visitors to its home page first.
            self._request(PORTAL_HOME)
            url, ctype, raw = self._request(VERIFY_URL, referer=PORTAL_ROOT)
        if "udyam_verify" not in url.lower():
            raise PortalError("The portal redirected away from the verify "
                              "page. Use 'Open official portal' and "
                              "'Manual entry' for this number.")
        page = self._decode(raw, ctype)
        fp = FormParser()
        fp.feed(page)
        if FIELD_UDYAM not in fp.input_names or FIELD_CAPTCHA not in fp.input_names:
            raise PortalError("The verify page layout has changed (form "
                              "fields not found). Use manual entry.")
        self.hidden = fp.hidden
        captcha_url = urllib.parse.urljoin(VERIFY_URL, fp.captcha_src or CAPTCHA_URL)
        _, img_type, img = self._request(captcha_url, referer=VERIFY_URL)
        if not img.startswith(b"\x89PNG") and not img[:6] in (b"GIF87a", b"GIF89a"):
            raise PortalError(f"Unexpected CAPTCHA image format ({img_type}).")
        self.form_ok = True
        return img

    def submit(self, udyam_number, captcha_text):
        if not self.form_ok:
            raise PortalError("Form not loaded - press 'New CAPTCHA / Retry'.")
        data = dict(self.hidden)
        data["__EVENTTARGET"] = ""
        data["__EVENTARGUMENT"] = ""
        data[FIELD_UDYAM] = udyam_number
        data[FIELD_CAPTCHA] = captcha_text
        data[FIELD_BUTTON] = BUTTON_VALUE
        self.form_ok = False           # each CAPTCHA is single-use
        url, ctype, raw = self._request(VERIFY_URL, data=data, referer=VERIFY_URL)
        return url, self._decode(raw, ctype)


def interpret_response(udyam_number, page_html):
    """Decide what the portal said.  Returns dict with keys:
    outcome ('verified'|'captcha'|'not_found'|'unknown'), details, message,
    visible."""
    details, messages, visible = extract_details(page_html)
    kind, msg = classify_failure(messages, visible)
    has_details = bool(details["enterprise_name"])
    number_on_page = udyam_number.replace("-", "") in re.sub(
        r"[^A-Z0-9]", "", visible.upper())

    if kind == "captcha":
        return dict(outcome="captcha", details=details, visible=visible,
                    message=f"Portal rejected the CAPTCHA: {msg}")
    if has_details and kind in (None, "other"):
        notes = []
        if kind == "other":
            notes.append(f"Portal message: {msg}")
        if not number_on_page:
            notes.append("Details returned, but the number itself was not "
                         "echoed on the page - please double-check.")
        return dict(outcome="verified", details=details, visible=visible,
                    message=" ".join(notes))
    if kind == "not_found":
        return dict(outcome="not_found", details=details, visible=visible,
                    message=f"Portal message: {msg}")
    if kind == "other":
        return dict(outcome="unknown", details=details, visible=visible,
                    message=f"Portal message: {msg}")
    return dict(outcome="unknown", details=details, visible=visible,
                message="Portal did not confirm the registration (no "
                        "registration details found on the returned page; "
                        "wrong CAPTCHA or a changed page layout are likely).")


# --------------------------------------------------------------------------
# Status categories shown in the GUI.  The CSV keeps the original status
# words ("Verified", "Not found", ...) so older results files stay valid.
# --------------------------------------------------------------------------
CAT_VERIFIED = "Verified"
CAT_NOT_VERIFIED = "Not Verified"
CAT_ERROR = "Error"
CAT_PENDING = "Verification Pending"


def status_category(status):
    s = (status or "").lower()
    if s.startswith("verified"):
        return CAT_VERIFIED
    if s.startswith("not found") or s.startswith("invalid format"):
        return CAT_NOT_VERIFIED
    if s.startswith("failed"):
        return CAT_ERROR
    return CAT_PENDING          # Skipped, or not yet processed


# --------------------------------------------------------------------------
# CSV input / results file (moved out of the old Tkinter App class)
# --------------------------------------------------------------------------
def read_input(path):
    """Return the upper-cased numbers in the 'udyam_number' column."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("The file has no header row.")
        col = next((c for c in reader.fieldnames
                    if c and c.strip().lower() == "udyam_number"), None)
        if col is None:
            raise ValueError("No column named 'udyam_number' found.\n"
                             f"Columns found: {', '.join(reader.fieldnames)}")
        out = []
        for row in reader:
            val = (row.get(col) or "").strip().upper()
            if val:
                out.append(val)
        return out


class ResultsStore:
    """The append-only results CSV (one row per finished number)."""

    def __init__(self, path=None):
        self.path = Path(path) if path else downloads_folder() / OUTPUT_NAME

    def exists(self):
        return self.path.exists()

    def upgrade_header(self):
        """A results file made by an older version lacks newer columns
        (e.g. enterprise_type).  Rewrite it with the current header so new
        rows line up; existing rows are kept, new columns left blank.
        Raises OSError if the file cannot be rewritten (open in Excel)."""
        if not self.path.exists():
            return
        with open(self.path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            if header == OUTPUT_COLUMNS:
                return
            rows = list(reader)
        tmp = self.path.with_name(self.path.name + ".tmp")
        with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c) or "" for c in OUTPUT_COLUMNS})
        os.replace(tmp, self.path)

    def verified_numbers(self):
        """Numbers already marked Verified in the existing file."""
        self.upgrade_header()
        done = set()
        with open(self.path, newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if (r.get("status") or "").startswith("Verified"):
                    done.add((r.get("udyam_number") or "").upper())
        return done

    def start_new(self):
        """Create / overwrite the file with just the header row."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS).writeheader()

    def append(self, row):
        """Append one row; raises OSError (e.g. file open in Excel)."""
        full = {c: row.get(c, "") for c in OUTPUT_COLUMNS}
        if not self.path.exists():
            self.start_new()
        else:
            self.upgrade_header()
        with open(self.path, "a", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS).writerow(full)

    def read_all(self):
        if not self.path.exists():
            return []
        with open(self.path, newline="", encoding="utf-8-sig") as f:
            return [{c: (r.get(c) or "") for c in OUTPUT_COLUMNS}
                    for r in csv.DictReader(f)]
