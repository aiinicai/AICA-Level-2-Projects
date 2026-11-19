
# ===========================================================================
# SECTION 2 - LETTER ENGINE
# ---------------------------------------------------------------------------
# Pure logic, no interface code.  Everything the preview shows and everything
# the Word file contains is produced from build_letter_model(), so the two can
# never drift apart.
# ===========================================================================

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

BAD_TOKENS = re.compile(
    r"^(undefined|null|nan|nil|n/a|na|-|--|#n/a|#value!|#ref!)$", re.I)

CATEGORIES = ["Trade Receivable", "Trade Payable",
              "Advance from Customers", "Advance to Vendors"]


# --------------------------------------------------------------- utilities
def clean(value):
    """Normalise any spreadsheet cell into a tidy display string."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, datetime):
        return fmt_date_long(value.date())
    if isinstance(value, date):
        return fmt_date_long(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return ""
        # six places: enough for any balance, and it keeps binary noise such
        # as 7960098.4800000004 out of the preview
        return ("%.6f" % value).rstrip("0").rstrip(".") or "0"
    if isinstance(value, int):
        return str(value)
    text = str(value).replace(" ", " ").strip()
    text = re.sub(r"[ \t]+", " ", text)
    if not text or BAD_TOKENS.match(text):
        return ""
    return text


def to_date(value):
    """Accept a date, datetime, ISO string or common Indian formats."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
                    "%m/%d/%Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(text[:len(text)], pattern).date()
        except ValueError:
            continue
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)),
                        int(match.group(3)))
        except ValueError:
            return None
    return None


def fmt_date_long(value):
    """31 March 2026 - the form used throughout the letters."""
    d = to_date(value)
    if not d:
        return ""
    return "%d %s %d" % (d.day, MONTHS[d.month - 1], d.year)


def iso_date(value):
    d = to_date(value)
    return d.isoformat() if d else ""


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def valid_email(text):
    return bool(EMAIL_RE.match(str(text or "").strip()))


ABBREVIATIONS = {
    "amt": "amount", "bal": "balance", "addr": "address", "ccy": "currency",
    "curr": "currency", "cur": "currency", "a/c": "account", "acc": "account",
    "acct": "account", "nm": "name", "pty": "party", "cust": "customer",
    "vend": "vendor", "supp": "supplier", "o/s": "outstanding",
    "os": "outstanding", "adv": "advance", "mob": "mobile", "ph": "phone",
    "no": "number", "nos": "number", "sr": "serial", "srno": "serial number",
    "desc": "description", "partic": "particulars",
}


def norm_header(text):
    """Fold case, punctuation, spacing and common abbreviations together."""
    value = str(text if text is not None else "").lower()
    value = value.replace(" ", " ")
    value = re.sub(r"[_\-.]", " ", value)
    value = re.sub(r"[^a-z0-9/ ]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = " ".join(ABBREVIATIONS.get(word, word) for word in value.split(" "))
    value = re.sub(r"\be mail\b", "email", value)
    return re.sub(r"\s+", " ", value).strip()


def is_numeric_like(text):
    stripped = re.sub(r"[\s,]", "", str(text))
    stripped = re.sub(r"[₹$€£¥]", "", stripped)
    return bool(stripped) and bool(re.match(r"^-?\(?\d*\.?\d+\)?$", stripped))


def col_letter(index):
    letters, n = "", index + 1
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


# ------------------------------------------------------- header detection
HEADER_TERMS = [
    "party", "name", "address", "amount", "balance", "currency", "category",
    "type", "email", "contact", "vendor", "customer", "supplier", "debtor",
    "creditor", "outstanding", "receivable", "payable", "advance", "nature",
    "classification", "particulars", "account", "city", "state", "pincode",
    "gstin", "code", "serial", "phone", "mobile",
]


def _score_header_row(row):
    cells = [c for c in (clean(v) for v in (row or [])) if c]
    if len(cells) < 2:
        return float("-inf")
    unique, numeric, keywords, longs = set(), 0, 0, 0
    for cell in cells:
        unique.add(cell.lower())
        if is_numeric_like(cell):
            numeric += 1
        if len(cell) > 45:
            longs += 1
        folded = norm_header(cell)
        if any(term in folded for term in HEADER_TERMS):
            keywords += 1
    score = len(cells) + len(unique) * 0.6 + keywords * 4.5
    return score - numeric * 3.5 - longs * 2.5


def detect_header_row(grid):
    """Pick the most likely header row; title rows above it are ignored."""
    limit = min(len(grid), 20)
    best, best_score, second = -1, float("-inf"), float("-inf")
    for r in range(limit):
        has_data_below = any(
            any(clean(c) for c in (grid[k] or []))
            for k in range(r + 1, len(grid)))
        score = (_score_header_row(grid[r]) - r * 0.35) if has_data_below \
            else float("-inf")
        if score > best_score:
            second, best_score, best = best_score, score, r
        elif score > second:
            second = score
    if best < 0:
        return {"index": 0, "confidence": "low", "hits": 0}
    hits = 0
    for cell in (clean(v) for v in (grid[best] or [])):
        if cell and any(t in norm_header(cell) for t in HEADER_TERMS):
            hits += 1
    confident = hits >= 2 and best_score >= second + 3
    return {"index": best, "confidence": "high" if confident else "low",
            "hits": hits}


def build_columns(grid, header_index):
    """Return header labels, the data rows below them and column descriptors."""
    header_row = grid[header_index] if header_index < len(grid) else []
    width = max((len(r or []) for r in grid), default=0)
    headers = [clean(header_row[i]) if i < len(header_row) else ""
               for i in range(width)]
    data_rows = [r for r in grid[header_index + 1:]
                 if any(clean(c) for c in (r or []))]
    seen, columns = {}, []
    for c in range(width):
        values = [clean(r[c]) if c < len(r or []) else "" for r in data_rows]
        filled = [v for v in values if v]
        if not headers[c] and not filled:
            continue                                   # entirely blank column
        label = headers[c] or ("Column " + col_letter(c))
        key = label.lower()
        if key in seen:
            seen[key] += 1
            label = "%s (%d)" % (label, seen[key])
        else:
            seen[key] = 1
        columns.append({"index": c, "header": headers[c], "label": label,
                        "values": values, "filled": len(filled)})
    return {"headers": headers, "data_rows": data_rows, "columns": columns}


# --------------------------------------------------------- column mapping
FIELD_DEFS = {
    "partyName": {
        "label": "Party / Name", "required": True, "multi": False,
        "exact": ["party name", "name of party", "name of the party", "party",
                  "name", "customer name", "vendor name", "supplier name",
                  "account name", "counterparty", "counter party",
                  "legal name", "customer", "vendor", "supplier",
                  "debtor name", "creditor name", "party account", "account"],
        "contains": ["party", "counterparty", "legal name", "account name",
                     "customer", "vendor", "supplier", "debtor", "creditor",
                     "name"],
        "penalty": ["contact", "email", "bank", "file", "user", "city",
                    "state", "employee", "signatory"]},
    "address": {
        "label": "Address", "required": False, "multi": True,
        "exact": ["address", "address 1", "address 2", "address 3",
                  "address line 1", "address line 2", "billing address",
                  "mailing address", "registered address", "location", "city",
                  "state", "pincode", "pin code", "postal code", "zip",
                  "country"],
        "contains": ["address", "location", "city", "state", "pincode",
                     "postal", "zip", "country"],
        "penalty": ["email", "website", "ip"]},
    "amount": {
        "label": "Amount / Balance", "required": False, "multi": False,
        "exact": ["amount", "balance", "outstanding", "closing balance",
                  "balance amount", "receivable", "payable", "advance",
                  "outstanding amount", "closing bal", "amount outstanding",
                  "balance as per books", "net balance", "value"],
        "contains": ["amount", "balance", "outstanding", "receivable",
                     "payable", "advance", "value", "debit", "credit"],
        "penalty": ["number", "gstin", "pan", "invoice number", "code",
                    "serial", "phone", "mobile", "days"]},
    "currency": {
        "label": "Currency", "required": False, "multi": False,
        "exact": ["currency", "currency code", "ccy"],
        "contains": ["currency", "ccy"], "penalty": []},
    "category": {
        "label": "Category", "required": False, "multi": False,
        "exact": ["category", "type", "account type", "nature",
                  "balance type", "classification", "nature of balance",
                  "head", "group"],
        "contains": ["category", "type", "nature", "classification",
                     "balance type", "group", "head"],
        "penalty": ["gst", "tax type", "document type", "file type"]},
    "email": {
        "label": "Email", "required": False, "multi": False,
        "exact": ["email", "email id", "email address", "mail id",
                  "contact email"],
        "contains": ["email", "mail id"], "penalty": []},
    "contactPerson": {
        "label": "Contact person", "required": False, "multi": False,
        "exact": ["contact", "contact person", "contact name", "attention",
                  "kind attention", "attn", "concerned person"],
        "contains": ["contact person", "contact name", "attention", "contact"],
        "penalty": ["email", "number", "phone", "mobile"]},
}
FIELD_ORDER = ["partyName", "amount", "category", "currency", "email",
               "contactPerson", "address"]

ISO_CURRENCIES = ["INR", "USD", "EUR", "GBP", "AED", "SGD", "JPY", "AUD",
                  "CAD", "CHF", "CNY", "HKD", "SAR", "ZAR", "NZD", "SEK",
                  "THB", "MYR", "LKR", "BDT", "NPR"]


def _edge_word_match(folded, term):
    """Whole-word prefix / suffix test, so 'serial number' never matches
    'address' merely because the lengths happen to line up."""
    if not term or len(term) > len(folded):
        return False
    if folded[:len(term)] == term and (
            len(folded) == len(term) or folded[len(term)] == " "):
        return True
    at = len(folded) - len(term)
    return folded[at:] == term and (at == 0 or folded[at - 1] == " ")


def _header_score(definition, header):
    folded = norm_header(header)
    if not folded:
        return 0
    score = 0
    if folded in definition["exact"]:
        score = 100
    if score < 78:
        for term in definition["exact"]:
            if _edge_word_match(folded, term):
                score = max(score, 78)
    if score < 78:
        for term in definition["contains"]:
            if term in folded:
                score = max(score, 55 + min(len(term), 14))
    for term in definition["penalty"]:
        if term in folded:
            score -= 45
    return score


def _value_score(field, values):
    present = [v for v in values if v]
    if not present:
        return 0
    if field == "email":
        hits = sum(1 for v in present if valid_email(v))
        return 85 if hits / len(present) > 0.5 else 0
    if field == "currency":
        hits = sum(1 for v in present if v.upper() in ISO_CURRENCIES)
        return 85 if hits / len(present) > 0.6 else 0
    if field == "category":
        hits = sum(1 for v in present if normalize_category(v))
        return 85 if hits / len(present) > 0.5 else 0
    if field == "amount":
        hits = sum(1 for v in present if parse_amount(v)[0] is not None)
        return 45 if hits / len(present) > 0.75 else 0
    if field == "partyName":
        unique = {v.lower() for v in present}
        texty = sum(1 for v in present
                    if not is_numeric_like(v) and re.search(r"[A-Za-z]", v))
        avg_len = sum(len(v) for v in present) / len(present)
        if (texty / len(present) > 0.85 and
                len(unique) / len(present) > 0.6 and avg_len > 4):
            return 25
    return 0


def detect_mapping(columns):
    """Greedy, conflict-free assignment of spreadsheet columns to fields."""
    candidates = []
    for field in FIELD_ORDER:
        definition = FIELD_DEFS[field]
        for column in columns:
            hs = _header_score(definition, column["header"])
            vs = _value_score(field, column["values"])
            total = hs + (vs * 0.6 if hs > 0 else vs)
            if total > 20:
                candidates.append({"field": field, "col": column["index"],
                                   "score": round(total),
                                   "header": column["label"]})
    candidates.sort(key=lambda c: -c["score"])

    mapping = {f: {"field": f, "label": FIELD_DEFS[f]["label"], "cols": [],
                   "status": "missing", "score": 0, "candidates": []}
               for f in FIELD_ORDER}
    for candidate in candidates:
        mapping[candidate["field"]]["candidates"].append(candidate)

    used = {}
    for candidate in candidates:
        entry = mapping[candidate["field"]]
        if FIELD_DEFS[candidate["field"]]["multi"]:
            if candidate["col"] in used or len(entry["cols"]) >= 4:
                continue
            # further address columns need a solid header match, never a weak one
            if entry["cols"] and candidate["score"] < 70:
                continue
            used[candidate["col"]] = candidate["field"]
            entry["cols"].append(candidate["col"])
            entry["score"] = max(entry["score"], candidate["score"])
        else:
            if entry["cols"] or candidate["col"] in used:
                continue
            used[candidate["col"]] = candidate["field"]
            entry["cols"].append(candidate["col"])
            entry["score"] = candidate["score"]

    for field in FIELD_ORDER:
        entry = mapping[field]
        if not entry["cols"]:
            entry["status"] = "missing"
            continue
        rivals = [c for c in entry["candidates"] if c["col"] != entry["cols"][0]]
        near = rivals[0]["score"] if rivals else 0
        entry["status"] = ("detected"
                           if entry["score"] >= 70 and entry["score"] - near >= 12
                           else "review")
        if entry["score"] >= 95:
            entry["status"] = "detected"
    return mapping


# -------------------------------------------------- category normalisation
_ADV_FROM = [r"advance\s*(amount\s*)?received",
             r"advances?\s*from\s*(customer|client|buyer|debtor|party|parties)",
             r"(customer|client|buyer|debtor)s?\s*advances?",
             r"advances?\s*received\s*from", r"unearned\s*(revenue|income)",
             r"income\s*received\s*in\s*advance", r"advance\s*from\s*cust"]
_ADV_TO = [r"advances?\s*(amount\s*)?paid",
           r"advances?\s*to\s*(vendor|supplier|creditor|contractor|party|parties)",
           r"(vendor|supplier|creditor|contractor)s?\s*advances?",
           r"advances?\s*paid\s*to", r"prepaid\s*to\s*(vendor|supplier)",
           r"advance\s*to\s*vend", r"capital\s*advance"]
_TR_RULES = [r"trade\s*receivable", r"accounts?\s*receivable",
             r"(^|\s)receivables?(\s|$)", r"(^|\s)a\s*r(\s|$)",
             r"(^|\s)ar(\s|$)", r"trade\s*ar(\s|$)", r"(sundry\s*)?debtors?",
             r"(^|\s)customers?(\s|$)", r"(^|\s)dr(\s|$)"]
_TP_RULES = [r"trade\s*payable", r"accounts?\s*payable",
             r"(^|\s)payables?(\s|$)", r"(^|\s)a\s*p(\s|$)",
             r"(^|\s)ap(\s|$)", r"trade\s*ap(\s|$)", r"(sundry\s*)?creditors?",
             r"(^|\s)(vendors?|suppliers?)(\s|$)", r"(^|\s)cr(\s|$)"]


def _any_match(rules, text):
    return any(re.search(rule, text) for rule in rules)


def normalize_category(raw):
    """Map a spreadsheet value onto one of the four categories, or None."""
    text = norm_header(raw)
    if not text:
        return None
    for category in CATEGORIES:
        if text == norm_header(category):
            return category
    if "advance" in text or re.search(r"\bprepaid\b", text) or "unearned" in text:
        if _any_match(_ADV_FROM, text):
            return "Advance from Customers"
        if _any_match(_ADV_TO, text):
            return "Advance to Vendors"
        if re.search(r"receivable|debtor|customer|client|buyer", text):
            return "Advance from Customers"
        if re.search(r"payable|creditor|vendor|supplier", text):
            return "Advance to Vendors"
        return None                       # a bare "Advance" is ambiguous
    if _any_match(_TR_RULES, text):
        return "Trade Receivable"
    if _any_match(_TP_RULES, text):
        return "Trade Payable"
    return None


# -------------------------------------------------------- amount handling
_SYMBOLS = [("₹", "INR"), ("rs.", "INR"), ("rs", "INR"), ("inr", "INR"),
            ("us$", "USD"), ("usd", "USD"), ("$", "USD"), ("€", "EUR"),
            ("eur", "EUR"), ("£", "GBP"), ("gbp", "GBP"),
            ("¥", "JPY"), ("jpy", "JPY"), ("aed", "AED"),
            ("sgd", "SGD"), ("aud", "AUD"), ("cad", "CAD"), ("chf", "CHF")]


def parse_amount(raw):
    """Return (value, currency, note).  Handles 1,25,000 / (5,000) / Rs. / Cr."""
    if raw is None or raw == "":
        return (None, None, None)
    if isinstance(raw, bool):
        return (None, None, None)
    if isinstance(raw, (int, float)):
        value = float(raw)
        if value != value or value in (float("inf"), float("-inf")):
            return (None, None, None)
        return (value, None, None)

    text = str(raw).replace(" ", " ").strip()
    if not text or BAD_TOKENS.match(text):
        return (None, None, None)
    lowered = text.lower()
    currency = next((code for token, code in _SYMBOLS if token in lowered), None)

    negative, note = False, None
    if re.match(r"^\(.*\)$", text):
        negative, text = True, text[1:-1]
    if re.search(r"(^|[\s\d])cr\.?$", text, re.I):
        note, text = "Cr", re.sub(r"cr\.?$", "", text, flags=re.I)
    elif re.search(r"(^|[\s\d])dr\.?$", text, re.I):
        note, text = "Dr", re.sub(r"dr\.?$", "", text, flags=re.I)

    body = re.sub(r"[^0-9.,\-]", "", text)
    if not body:
        return (None, currency, None)
    if re.match(r"^-?\d{1,3}(\.\d{3})+(,\d+)?$", body):     # 1.234.567,89
        body = body.replace(".", "").replace(",", ".")
    else:
        body = body.replace(",", "")
    while body.count(".") > 1:
        body = body.replace(".", "", 1)
    try:
        value = float(body)
    except ValueError:
        return (None, currency, None)
    if negative:
        value = -abs(value)
    return (value, currency, note)


def _group_indian(digits):
    """1,25,000 - last three digits, then pairs."""
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def fmt_amount(value, currency=None):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    sign = "-" if number < 0 else ""
    whole, _, frac = ("%.2f" % abs(number)).partition(".")
    if str(currency or "").upper() == "INR":
        grouped = _group_indian(whole)
    else:
        grouped = "{:,}".format(int(whole))
    return "%s%s.%s" % (sign, grouped, frac)


def amount_label(value, currency=None):
    formatted = fmt_amount(value, currency)
    if formatted is None:
        return None
    prefix = (str(currency).upper() + " ") if currency else ""
    return prefix + formatted


# ------------------------------------------------- audit type and period
# auditors   - how the firm is described in "Our ..., [Firm], are engaged"
# engagement - what follows "are engaged in ... of our financial statements"
AUDIT_TYPES = {
    "Statutory Audit":       ("statutory audit",       "Statutory Auditor",
                              "statutory auditors",    "an audit"),
    "Interim Audit":         ("interim audit",         "Statutory Auditor",
                              "auditors",              "an interim audit"),
    "Special Purpose Audit": ("special purpose audit", "Auditor",
                              "auditors",              "a special purpose audit"),
    "Limited Review":        ("limited review",        "Auditor",
                              "auditors",              "a limited review"),
    "Tax Audit":             ("tax audit",             "Tax Auditor",
                              "tax auditors",          "a tax audit"),
    "Other":                 ("audit",                 "Auditor",
                              "auditors",              "an audit"),
}
AUDIT_TYPE_ORDER = ["Statutory Audit", "Interim Audit", "Special Purpose Audit",
                    "Limited Review", "Tax Audit", "Other"]


def audit_phrase(audit_type, other=""):
    """Lower-case noun phrase, e.g. for a heading or a covering e-mail."""
    if audit_type == "Other":
        text = clean(other)
        if not text:
            return "audit"
        text = re.sub(r"^the\s+", "", text, flags=re.I)
        return text[0].lower() + text[1:] if text[:1].isupper() else text
    return AUDIT_TYPES.get(audit_type, AUDIT_TYPES["Statutory Audit"])[0]


def audit_designation(audit_type):
    return AUDIT_TYPES.get(audit_type, ("", "Auditor"))[1]


def auditors_label(audit_type):
    """'Statutory auditors' / 'auditors' / 'tax auditors'."""
    return AUDIT_TYPES.get(audit_type, AUDIT_TYPES["Statutory Audit"])[2]


def engagement_phrase(audit_type, other=""):
    """What the firm is engaged in: 'an audit', 'a limited review', ..."""
    if audit_type == "Other":
        text = clean(other)
        if not text:
            return "an audit"
        text = re.sub(r"^(a|an|the)\s+", "", text, flags=re.I)
        if text[:1].isupper():
            text = text[0].lower() + text[1:]
        return ("an " if text[:1].lower() in "aeiou" else "a ") + text
    return AUDIT_TYPES.get(audit_type, AUDIT_TYPES["Statutory Audit"])[3]


def period_phrase(basis, as_at, period_start=""):
    """'for the year ended X' or 'for the period from X to Y'."""
    end = fmt_date_long(as_at)
    if not end:
        return ""
    if basis == "period":
        start = fmt_date_long(period_start)
        return ("for the period from %s to %s" % (start, end)) if start \
            else ("for the period ended %s" % end)
    return "for the year ended %s" % end


def period_label(basis, as_at, period_start=""):
    phrase = re.sub(r"^for the ", "", period_phrase(basis, as_at, period_start))
    return phrase[:1].upper() + phrase[1:] if phrase else ""


# --------------------------------------------------------- amount in words
# The confirmation formats carry "(In Words: ... only)".  Rupee amounts use
# the Indian system (lakh, crore); every other currency uses the
# international system (million, billion).
ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
        "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
        "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
        "Eighty", "Ninety"]


def _two_digits(n):
    if n < 20:
        return ONES[n]
    tens = TENS[n // 10]
    return (tens + " " + ONES[n % 10]) if n % 10 else tens


def _three_digits(n):
    parts = []
    if n >= 100:
        parts.append(ONES[n // 100] + " Hundred")
        n %= 100
    if n:
        parts.append(_two_digits(n))
    return " ".join(parts)


def indian_words(n):
    """1,23,45,678 -> 'One Crore Twenty Three Lakh Forty Five Thousand ...'"""
    if n == 0:
        return "Zero"
    parts = []
    crore, n = divmod(n, 10000000)
    lakh, n = divmod(n, 100000)
    thousand, n = divmod(n, 1000)
    if crore:
        parts.append((indian_words(crore) if crore > 999
                      else _three_digits(crore)) + " Crore")
    if lakh:
        parts.append(_three_digits(lakh) + " Lakh")
    if thousand:
        parts.append(_three_digits(thousand) + " Thousand")
    if n:
        parts.append(_three_digits(n))
    return " ".join(parts)


def international_words(n):
    if n == 0:
        return "Zero"
    parts = []
    for size, name in ((10 ** 12, "Trillion"), (10 ** 9, "Billion"),
                       (10 ** 6, "Million"), (1000, "Thousand")):
        unit, n = divmod(n, size)
        if unit:
            parts.append((international_words(unit) if unit > 999
                          else _three_digits(unit)) + " " + name)
    if n:
        parts.append(_three_digits(n))
    return " ".join(parts)


MAJOR_UNITS = {"INR": "Rupees", "USD": "US Dollars", "EUR": "Euros",
               "GBP": "Pounds", "AED": "Dirhams", "SGD": "Singapore Dollars",
               "AUD": "Australian Dollars", "CAD": "Canadian Dollars",
               "JPY": "Yen", "CHF": "Swiss Francs"}
MINOR_UNITS = {"INR": "Paise", "USD": "Cents", "EUR": "Cents", "GBP": "Pence",
               "AED": "Fils", "SGD": "Cents", "AUD": "Cents", "CAD": "Cents",
               "JPY": "", "CHF": "Rappen"}


def amount_in_words(value, currency=None):
    """e.g. 'Rupees One Lakh Twenty Five Thousand only'."""
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    code = str(currency or "").upper()
    negative = number < 0
    whole = int(abs(number) + 1e-9)
    fraction = int(round((abs(number) - whole) * 100))
    if fraction == 100:
        whole += 1
        fraction = 0
    body = indian_words(whole) if code == "INR" else international_words(whole)
    major = MAJOR_UNITS.get(code, code)
    text = ((major + " ") if major else "") + body
    minor = MINOR_UNITS.get(code, "Cents")
    if fraction and minor:
        text += " and " + _two_digits(fraction) + " " + minor
    if negative:
        text = "Minus " + text
    return re.sub(r"\s+", " ", text).strip() + " only"


# ------------------------------------------------------- category wording
# Taken from the firm's own four confirmation formats.  The letter is written
# by the CLIENT COMPANY to the party and signed by the company's own officer;
# the auditors are named as the people the signed reply must go to.
_LONG_DIFFERENCE = (
    "If the amount is not in agreement with your records, please notify our "
    "auditors directly, with a copy to us, of the amount shown by your "
    "records and, if possible, provide full particulars of the difference and "
    "reconciliation to your records.")
_SHORT_DIFFERENCE = (
    "If the amount is not in agreement with your records, please notify our "
    "auditors directly, with a copy to us, of the amount shown by your "
    "records and, if possible, provide full particulars of the difference and "
    "reconciliation to your records.")

CATEGORY_LANGUAGE = {
    "Trade Receivable": {
        "code": "TR",
        "title": "ACCOUNTS RECEIVABLE/DEBTOR CONFIRMATION",
        "party_label": "Customer Name",
        "request": "you confirm directly to them the amount payable by you to us",
        "statement": "a statement of our account in your books as at that date",
        "record_line": "the amount due from you",
        "no_payment": True,                 # debtor format only
        "difference": _LONG_DIFFERENCE,
        "slip": lambda c: "We hereby confirm that the amount payable by us to " + c,
        "meaning": "Client is owed money by the party."},
    "Trade Payable": {
        "code": "TP",
        "title": "ACCOUNTS PAYABLE/CREDITOR CONFIRMATION",
        "party_label": "Vendor Name",
        "request": "you furnish directly to them the amount of our liability "
                   "to you (if any)",
        "statement": "a statement of our account as at that date",
        "record_line": "the amount due to you",
        "no_payment": False,
        "difference": _SHORT_DIFFERENCE,
        "slip": lambda c: "We hereby confirm that the amount receivable by us from " + c,
        "meaning": "Client owes money to the party."},
    "Advance from Customers": {
        "code": "AFC",
        "title": "ADVANCE FROM CUSTOMER",
        "party_label": "Name",
        "request": "you furnish directly to them the amount of advance "
                   "received from you (if any)",
        "statement": "a statement of our account as at that date",
        "record_line": "the advance amount received from you",
        "no_payment": False,
        "difference": _SHORT_DIFFERENCE,
        "slip": lambda c: "We hereby confirm that the advance amount paid by us to " + c,
        "meaning": "Client has received an advance from the party."},
    "Advance to Vendors": {
        "code": "ATV",
        "title": "ADVANCE PAID TO VENDOR",
        "party_label": "Vendor Name",
        "request": "you furnish directly to them the amount of advance paid "
                   "to you (if any)",
        "statement": "a statement of our account as at that date",
        "record_line": "the advance amount paid to you",
        "no_payment": False,
        "difference": _SHORT_DIFFERENCE,
        "slip": lambda c: "We hereby confirm that the advance amount received by us from " + c,
        "meaning": "Client has paid an advance to the party."},
}



# ------------------------------------------------------------ page fitting
BODY_CPL = 92       # characters per line across the 9,638 twip text column


def _wrapped(text, chars_per_line):
    return max(1, -(-len(str(text or "")) // chars_per_line))


# ------------------------------------------------------------- the letter
def build_letter_model(conf):
    """The single source of truth for the preview and the Word document.

    Follows the firm's own confirmation formats:
        (on the letter head of the Company)        <- optional note
        ACCOUNTS RECEIVABLE/DEBTOR CONFIRMATION    <- title, centred, bold
                                        Date: ...  <- right
        Customer Name / [ADDRESS]                  <- left
        Dear Sir,  ... body ...
        [Partner] / [Firm] (Chartered Accountants) / Email Id:
        Yours faithfully / [Company] / Mr. XX / Director / CFO
        We hereby confirm ... + Name and Title / Company / Signature / Date
    """
    language = CATEGORY_LANGUAGE.get(conf.get("category"))
    if not language:
        raise ValueError("Unknown category: %s" % conf.get("category"))

    client = conf.get("client_name", "")
    as_at = conf.get("as_at") or conf.get("year_end")
    date_label = conf.get("year_end_label") or fmt_date_long(as_at)
    firm = conf.get("firm_name", "")
    auditors = auditors_label(conf.get("audit_type"))
    engagement = engagement_phrase(conf.get("audit_type"),
                                   conf.get("audit_type_other"))

    party = [{"text": conf.get("party_name", ""), "bold": False}]
    for line in conf.get("address_lines") or []:
        if line:
            party.append({"text": line, "bold": False})
    if conf.get("contact_person"):
        party.append({"text": "Kind Attn: " + conf["contact_person"],
                      "bold": False})

    label = amount_label(conf.get("amount"), conf.get("currency"))
    words = amount_in_words(conf.get("amount"), conf.get("currency"))
    code = str(conf.get("currency") or "").upper()

    paras = ["Our %s, %s, are engaged in %s of our financial statements. In "
             "connection therewith, they desire that %s as at %s and %s."
             % (auditors, firm, engagement, language["request"], date_label,
                language["statement"])]
    if label is not None:
        paras.append("According to our records, %s as at %s is %s (In Words: %s)"
                     % (language["record_line"], date_label, label, words))
    else:
        paras.append("According to our records, the %s as at %s is as per the "
                     "statement of account enclosed. Kindly confirm the balance "
                     "appearing in your books as at that date."
                     % (language["record_line"], date_label))
    paras.append("After signing your reply, please e-mail this letter directly "
                 "to our auditors at the following e-mail address:")

    emails = [a.get("email") for a in (conf.get("auditors") or [])
              if valid_email(a.get("email"))]
    auditor_block = []
    if conf.get("partner_name"):
        auditor_block.append({"text": conf["partner_name"], "bold": False})
    auditor_block.append({"text": firm + " (Chartered Accountants)",
                          "bold": False})
    auditor_block.append({"text": "Email ID: " + "; ".join(emails),
                          "bold": False})

    closing = [language["difference"]]
    if language["no_payment"]:
        closing.append("This letter is not a request for payment and "
                       "accordingly please do not enclose a cheque or other "
                       "payment with your confirmation.")
    closing.append("We thank you in advance for your co-operation in complying "
                   "with this request and apologise for any inconvenience caused.")

    # the client company signs, not the audit firm
    signature = [{"text": "Yours faithfully", "bold": False},
                 {"text": client, "bold": False}]
    if conf.get("signatory_name"):
        signature.append({"text": conf["signatory_name"], "bold": False,
                          "gap": True})
    if conf.get("signatory_designation"):
        signature.append({"text": conf["signatory_designation"], "bold": False})

    slip = {
        "sentence": "%s as on %s is %s______________"
                    % (language["slip"](client), date_label,
                       (code + " ") if code else ""),
        "rows": ["Name and Title", "Company / Firm", "Signature", "Date"],
    }

    bulk = (len(party) + len(auditor_block) + len(signature)
            + _wrapped(paras[0], BODY_CPL) + _wrapped(paras[1], BODY_CPL)
            + sum(_wrapped(t, BODY_CPL) for t in closing))

    return {
        "letterhead_note": "(on the letter head of the Company)"
                           if conf.get("letterhead_note") else "",
        "title": language["title"],
        "date_line": "Date: " + (conf.get("letter_date_label") or ""),
        "reference_line": ("Ref: " + conf["reference"])
                          if conf.get("reference") and
                          conf.get("print_reference", True) else "",
        "party_block": party,
        "salutation": "Dear Sir,",
        "paras": paras,
        "auditor_block": auditor_block,
        "closing_paras": closing,
        "signature": signature,
        "slip": slip,
        "compact": bulk >= 26,
        "category": conf.get("category"),
    }
