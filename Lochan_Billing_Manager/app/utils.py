"""
utils.py
--------
Stand-alone helper functions used across the application:

  * Indian GST State/UT code list (for the Place-of-Supply dropdown and for
    auto-deciding CGST+SGST vs. IGST).
  * Indian numbering system (Lakh/Crore) number-to-words conversion for the
    "Amount in words" line on the invoice.
  * Invoice number generation (LC/<FY>/<Mon>/<Seq>, resets every month).
  * Basic field validation helpers (mobile, GSTIN, PAN, required fields).

None of these functions touch the GUI or the JSON database directly, so they
can be unit-tested in isolation.
"""

import re
from datetime import date

from app import config

# ---------------------------------------------------------------------------
# GST State / UT codes (as per CBIC) -- used for the Customer "State" combo
# box and to auto-decide CGST+SGST (intra-state) vs IGST (inter-state).
# ---------------------------------------------------------------------------
GST_STATE_CODES = [
    ("01", "Jammu and Kashmir"),
    ("02", "Himachal Pradesh"),
    ("03", "Punjab"),
    ("04", "Chandigarh"),
    ("05", "Uttarakhand"),
    ("06", "Haryana"),
    ("07", "Delhi"),
    ("08", "Rajasthan"),
    ("09", "Uttar Pradesh"),
    ("10", "Bihar"),
    ("11", "Sikkim"),
    ("12", "Arunachal Pradesh"),
    ("13", "Nagaland"),
    ("14", "Manipur"),
    ("15", "Mizoram"),
    ("16", "Tripura"),
    ("17", "Meghalaya"),
    ("18", "Assam"),
    ("19", "West Bengal"),
    ("20", "Jharkhand"),
    ("21", "Odisha"),
    ("22", "Chattisgarh"),
    ("23", "Madhya Pradesh"),
    ("24", "Gujarat"),
    ("26", "Dadra and Nagar Haveli and Daman and Diu"),
    ("27", "Maharashtra"),
    ("29", "Karnataka"),
    ("30", "Goa"),
    ("31", "Lakshadweep"),
    ("32", "Kerala"),
    ("33", "Tamil Nadu"),
    ("34", "Puducherry"),
    ("35", "Andaman and Nicobar Islands"),
    ("36", "Telangana"),
    ("37", "Andhra Pradesh"),
    ("38", "Ladakh"),
    ("97", "Other Territory"),
    ("99", "Centre Jurisdiction"),
]

STATE_NAME_TO_CODE = {name: code for code, name in GST_STATE_CODES}
STATE_CODE_TO_NAME = {code: name for code, name in GST_STATE_CODES}

MONTH_ABBR = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


# ---------------------------------------------------------------------------
# Financial year helpers
# ---------------------------------------------------------------------------
def financial_year_string(the_date: date) -> str:
    """Return the Indian financial year (Apr-Mar) as 'YY-YY', e.g. '26-27'."""
    year = the_date.year
    if the_date.month >= 4:
        start_year = year
    else:
        start_year = year - 1
    end_year = start_year + 1
    return f"{str(start_year)[-2:]}-{str(end_year)[-2:]}"


def month_abbr(the_date: date) -> str:
    return MONTH_ABBR[the_date.month - 1]


MONTH_FULL = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _ordinal_suffix(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def format_date_display(the_date: date) -> str:
    """e.g. date(2026, 8, 1) -> '1st August, 2026' (matches firm's sample)."""
    day = the_date.day
    return f"{day}{_ordinal_suffix(day)} {MONTH_FULL[the_date.month - 1]}, {the_date.year}"


# ---------------------------------------------------------------------------
# Invoice number generation: LC/<FY>/<Mon>/<Seq>  (sequence resets monthly)
# ---------------------------------------------------------------------------
def generate_invoice_number(the_date: date, existing_numbers) -> str:
    """
    Build the next invoice number for the given date.

    existing_numbers: iterable of all invoice-number strings already saved
    in the database (any format -- non-matching ones are ignored safely).
    """
    fy = financial_year_string(the_date)
    mon = month_abbr(the_date)
    pattern = re.compile(
        rf"^{re.escape(config.INVOICE_PREFIX)}/{re.escape(fy)}/{re.escape(mon)}/(\d+)$"
    )
    max_seq = 0
    for num in existing_numbers:
        m = pattern.match(num.strip()) if isinstance(num, str) else None
        if m:
            seq = int(m.group(1))
            if seq > max_seq:
                max_seq = seq
    next_seq = max_seq + 1
    return f"{config.INVOICE_PREFIX}/{fy}/{mon}/{next_seq:02d}"


# ---------------------------------------------------------------------------
# Number to words (Indian numbering system: Lakh / Crore)
# ---------------------------------------------------------------------------
_ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
    "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
    "Sixteen", "Seventeen", "Eighteen", "Nineteen",
]
_TENS = [
    "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
    "Eighty", "Ninety",
]


def _two_digits_to_words(n: int) -> str:
    if n == 0:
        return ""
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return (_TENS[tens] + (" " + _ONES[ones] if ones else "")).strip()


def _three_digits_to_words(n: int) -> str:
    hundreds, rest = divmod(n, 100)
    parts = []
    if hundreds:
        parts.append(f"{_ONES[hundreds]} Hundred")
    if rest:
        parts.append(_two_digits_to_words(rest))
    return " ".join(parts).strip()


def number_to_indian_words(amount) -> str:
    """
    Convert a non-negative rupee amount (int or float) to words using the
    Indian numbering system (Crore / Lakh / Thousand / Hundred), e.g.:
        147500  -> "One Lakh Forty Seven Thousand Five Hundred"
    Paise (if any) are ignored since invoices are rounded to the rupee.
    """
    n = int(round(amount))
    if n == 0:
        return "Zero"

    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, n = divmod(n, 1000)
    hundred = n

    parts = []
    if crore:
        parts.append(f"{_three_digits_to_words(crore)} Crore")
    if lakh:
        parts.append(f"{_two_digits_to_words(lakh) if lakh < 100 else _three_digits_to_words(lakh)} Lakh")
    if thousand:
        parts.append(f"{_two_digits_to_words(thousand) if thousand < 100 else _three_digits_to_words(thousand)} Thousand")
    if hundred:
        parts.append(_three_digits_to_words(hundred))

    return " ".join(p for p in parts if p).strip()


def amount_in_words_rupees(amount) -> str:
    """Full 'Rupees ... Only' string as printed on the invoice."""
    words = number_to_indian_words(amount)
    return f"Rupees {words} Only"


# ---------------------------------------------------------------------------
# GST split logic: CGST+SGST (intra-state) vs IGST (inter-state)
# ---------------------------------------------------------------------------
def is_intra_state(customer_state_code: str) -> bool:
    """True if the customer is in the same state as the firm (CGST+SGST)."""
    return (customer_state_code or "").strip() == config.FIRM_STATE_CODE


def state_code_from_gstin(gstin: str):
    """Return the 2-digit state code prefix of a GSTIN, or None if invalid."""
    if gstin and len(gstin.strip()) >= 2 and gstin.strip()[:2].isdigit():
        return gstin.strip()[:2]
    return None


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
MOBILE_RE = re.compile(r"^[6-9]\d{9}(\s*,\s*[6-9]\d{9})*$")
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
PAN_RE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")


def is_valid_mobile(value: str) -> bool:
    if not value:
        return True  # optional in many flows; required-ness checked separately
    return bool(MOBILE_RE.match(value.strip()))


def is_valid_gstin(value: str) -> bool:
    if not value:
        return True  # optional field
    return bool(GSTIN_RE.match(value.strip().upper()))


def is_valid_pan(value: str) -> bool:
    if not value:
        return True  # optional field
    return bool(PAN_RE.match(value.strip().upper()))


# ---------------------------------------------------------------------------
# Invoice total computation (shared by the GUI live-preview and the PDF
# generator, so both always agree on the numbers).
# ---------------------------------------------------------------------------
def compute_invoice_totals(items, customer_state_code: str) -> dict:
    """
    items: list of dicts with 'amount' (float) and 'gst_percent' (float).
    customer_state_code: 2-digit GST state code of the customer.

    Returns a dict with per-item computed values plus invoice-level totals:
        {
          "items": [ {..input.., "gst_amount":, "cgst":, "sgst":, "igst":, "total":} ],
          "subtotal", "cgst", "sgst", "igst", "total_gst",
          "grand_total_raw", "round_off", "grand_total", "is_intra_state"
        }
    """
    intra = is_intra_state(customer_state_code)

    computed_items = []
    subtotal = 0.0
    total_cgst = 0.0
    total_sgst = 0.0
    total_igst = 0.0

    for item in items:
        amount = float(item.get("amount") or 0)
        gst_percent = float(item.get("gst_percent") or 0)
        gst_amount = round(amount * gst_percent / 100, 2)

        if intra:
            cgst = round(gst_amount / 2, 2)
            sgst = round(gst_amount - cgst, 2)
            igst = 0.0
        else:
            cgst = 0.0
            sgst = 0.0
            igst = gst_amount

        line_total = round(amount + gst_amount, 2)

        computed_items.append({
            **item,
            "amount": amount,
            "gst_percent": gst_percent,
            "gst_amount": gst_amount,
            "cgst": cgst,
            "sgst": sgst,
            "igst": igst,
            "total": line_total,
        })

        subtotal += amount
        total_cgst += cgst
        total_sgst += sgst
        total_igst += igst

    subtotal = round(subtotal, 2)
    total_cgst = round(total_cgst, 2)
    total_sgst = round(total_sgst, 2)
    total_igst = round(total_igst, 2)
    total_gst = round(total_cgst + total_sgst + total_igst, 2)

    grand_total_raw = round(subtotal + total_gst, 2)

    if config.ROUND_OFF_ENABLED:
        grand_total = float(round(grand_total_raw))
        round_off = round(grand_total - grand_total_raw, 2)
    else:
        grand_total = grand_total_raw
        round_off = 0.0

    return {
        "items": computed_items,
        "subtotal": subtotal,
        "cgst": total_cgst,
        "sgst": total_sgst,
        "igst": total_igst,
        "total_gst": total_gst,
        "grand_total_raw": grand_total_raw,
        "round_off": round_off,
        "grand_total": grand_total,
        "is_intra_state": intra,
    }


def format_gst_rate(rate) -> str:
    """Format a numeric GST rate for display/ledger-naming, e.g. 9.0 -> '9',
    9.5 -> '9.5'. Shared by the PDF generator and the Tally ledger-name
    lookup so both agree on the same rate string."""
    rate = float(rate or 0)
    if rate == int(rate):
        return str(int(rate))
    return f"{rate:.2f}".rstrip("0").rstrip(".")


def format_currency(amount) -> str:
    """Format a number as Indian-style currency grouping, e.g. 1,25,000."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        amount = 0.0
    is_negative = amount < 0
    amount = abs(amount)
    if amount == int(amount):
        s = str(int(amount))
        decimal = ""
    else:
        s = str(int(amount))
        decimal = f".{round((amount - int(amount)) * 100):02d}"

    if len(s) <= 3:
        grouped = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        grouped = ",".join(parts) + "," + last3
    result = grouped + decimal
    return f"-{result}" if is_negative else result
