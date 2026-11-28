"""Pure GST / formatting helpers (no database, no Flask) so they are easy to test."""
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

STATES = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "25": "Daman & Diu (old code)", "26": "Dadra & Nagar Haveli and Daman & Diu", "27": "Maharashtra",
    "28": "Andhra Pradesh (old code)", "29": "Karnataka", "30": "Goa", "31": "Lakshadweep",
    "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry", "35": "Andaman & Nicobar Islands",
    "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh", "97": "Other Territory",
    "99": "Centre Jurisdiction",
}
# Union territories without a legislature: intra-state supply attracts CGST + UTGST (not SGST)
UTGST_CODES = {"04", "25", "26", "31", "35", "38"}

GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
HSN_RE = re.compile(r"^\d{4}(\d{2}(\d{2})?)?$")
PIN_RE = re.compile(r"^[1-9][0-9]{5}$")
VEHICLE_RE = re.compile(r"^([A-Z]{2}\d{1,2}[A-Z]{0,3}\d{4}|\d{2}BH\d{4}[A-Z]{1,2}|TMP\d{6,7})$")
EWB_RE = re.compile(r"^\d{12}$")
_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin_checksum(first14):
    factor, total = 2, 0
    for ch in reversed(first14):
        digit = factor * _CHARS.index(ch)
        factor = 1 if factor == 2 else 2
        total += digit // 36 + digit % 36
    return _CHARS[(36 - total % 36) % 36]


def make_gstin(state_code, pan, entity="1"):
    """Build a GSTIN with a correct check digit (used for sample data and tests)."""
    base = f"{state_code}{pan}{entity}Z"
    return base + gstin_checksum(base)


def norm_gstin(g):
    return (g or "").strip().upper().replace(" ", "")


def validate_gstin(g, state_code=None):
    """Return a list of error strings (empty list = valid)."""
    g = norm_gstin(g)
    if len(g) != 15:
        return ["GSTIN must be exactly 15 characters."]
    if not GSTIN_RE.match(g):
        return ["GSTIN format is invalid (expected 99AAAAA9999A9Z9)."]
    errs = []
    if g[:2] not in STATES:
        errs.append(f"GSTIN starts with unknown state code {g[:2]}.")
    if g[14] != gstin_checksum(g[:14]):
        errs.append("GSTIN check digit is wrong - please re-check for a typing mistake.")
    if state_code and g[:2] != state_code:
        errs.append(f"GSTIN's first two digits ({g[:2]}) do not match state code {state_code}.")
    return errs


def pan_from_gstin(g):
    g = norm_gstin(g)
    return g[2:12] if len(g) == 15 else None


def valid_hsn(h):
    return bool(HSN_RE.match((h or "").strip()))


def norm_vehicle(v):
    return re.sub(r"[\s\-]", "", (v or "").upper())


def state_label(code):
    return f"{code} - {STATES.get(code, '?')}"


def state_code_from_text(text):
    """Accept '27', '27 - Maharashtra' or 'Maharashtra'; return the code or None."""
    t = (text or "").strip()
    if not t:
        return None
    if t[:2].isdigit() and t[:2] in STATES:
        return t[:2]
    low = t.lower()
    for c, n in STATES.items():
        if n.lower() == low or n.lower().startswith(low):
            return c
    return None


def tax_labels(state_code):
    return ("CGST", "UTGST" if state_code in UTGST_CODES else "SGST", "IGST")


# ---------- financial year ----------
def fy_of(d):
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y}-{str(y + 1)[2:]}"


def fy_short(fy):
    return f"{fy[2:4]}-{fy[5:]}"


def fy_range(fy):
    y = int(fy[:4])
    return date(y, 4, 1), date(y + 1, 3, 31)


# ---------- money ----------
def D(x, default=None):
    if x is None or (isinstance(x, str) and not x.strip()):
        return default
    try:
        return Decimal(str(x).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return default


def q2(x):
    return Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_line(qty, rate, tax_rate, cess_rate, interstate):
    taxable = q2(qty * rate)
    out = {"taxable": taxable, "cgst": Decimal("0.00"), "sgst": Decimal("0.00"),
           "igst": Decimal("0.00"), "cess": q2(taxable * cess_rate / 100)}
    if interstate:
        out["igst"] = q2(taxable * tax_rate / 100)
    else:
        half = q2(taxable * tax_rate / 200)
        out["cgst"], out["sgst"] = half, half
    return out


def inr(x):
    """Indian digit grouping: 12,34,567.89"""
    if x is None:
        return ""
    x = q2(x)
    s = f"{abs(x):.2f}"
    whole, frac = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts) + "," + tail
    return ("-" if x < 0 else "") + whole + "." + frac


_ONES = ("Zero One Two Three Four Five Six Seven Eight Nine Ten Eleven Twelve Thirteen Fourteen Fifteen "
         "Sixteen Seventeen Eighteen Nineteen").split()
_TENS = "_ _ Twenty Thirty Forty Fifty Sixty Seventy Eighty Ninety".split()


def _below_100(n):
    return _ONES[n] if n < 20 else _TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")


def _below_1000(n):
    s = ""
    if n >= 100:
        s = _ONES[n // 100] + " Hundred"
        n %= 100
        if n:
            s += " "
    return s + (_below_100(n) if n else "")


def _words(n):
    parts = []
    for div, name in ((10000000, "Crore"), (100000, "Lakh"), (1000, "Thousand")):
        if n >= div:
            parts.append(_below_1000(n // div) + " " + name)
            n %= div
    if n:
        parts.append(_below_1000(n))
    return " ".join(parts)


def amount_in_words(amount):
    amount = q2(amount)
    rupees = int(amount)
    paise = int((amount - rupees) * 100)
    out = "Rupees " + (_words(rupees) if rupees else "Zero")
    if paise:
        out += " and " + _below_100(paise) + " Paise"
    return out + " Only"


def normalize_name(name):
    n = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower().replace("&", " and "))
    stop = {"pvt", "private", "ltd", "limited", "llp", "inc", "co", "company", "and", "the", "corp", "corporation"}
    return " ".join(w for w in n.split() if w not in stop)

