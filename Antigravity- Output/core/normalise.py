"""
Data Normalisation Utilities for MarketMatch.
Zero-float arithmetic using Decimal, rigorous string IDs, GST 2-digit state codes,
HSN codes, and date parsing.
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime, date
import re
from typing import Optional, Union, Tuple, Any

# Two decimal quantizer for Indian Rupee paise
PAISE_QUANT = Decimal("0.01")
PERCENT_QUANT = Decimal("0.0001")


def to_decimal(val: Any, default: Decimal = Decimal("0.00"), round_cents: bool = True) -> Decimal:
    """
    Safely convert any numeric, string, or float representation to Decimal.
    Rounds to 2 decimal places to eliminate floating point noise (e.g. 11833.809999999996 -> 11833.81).
    """
    if val is None:
        return default
    if isinstance(val, Decimal):
        return val.quantize(PAISE_QUANT, rounding=ROUND_HALF_UP) if round_cents else val
    if isinstance(val, (int, float)):
        # Convert float via string representation to avoid immediate binary float artifacts
        str_val = f"{val:.6f}" if isinstance(val, float) else str(val)
        try:
            d = Decimal(str_val)
            return d.quantize(PAISE_QUANT, rounding=ROUND_HALF_UP) if round_cents else d
        except (InvalidOperation, ValueError):
            return default

    # Handle string inputs (strip currency symbols, spaces, Indian commas, quotes)
    cleaned = str(val).strip().replace("₹", "").replace("INR", "").replace(",", "").replace('"', "").replace("'", "")
    if not cleaned or cleaned.lower() in ("nan", "none", "null", "-", "nil", ""):
        return default

    # Handle negative values formatted as (123.45)
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1].strip()

    # Remove all whitespace (including between '-' and digits)
    cleaned = re.sub(r"\s+", "", cleaned)

    try:
        d = Decimal(cleaned)
        return d.quantize(PAISE_QUANT, rounding=ROUND_HALF_UP) if round_cents else d
    except (InvalidOperation, ValueError):
        return default


def clean_id(val: Any) -> str:
    """
    Read ID columns strictly as text without scientific notation or losing leading zeros.
    Text, trimmed, quotes removed, trailing '.0' removed, uppercase, blank for None/nan.
    """
    if val is None:
        return ""
    if isinstance(val, float):
        # Handle nan
        import math
        if math.isnan(val):
            return ""
        if val.is_integer():
            val_str = str(int(val))
        else:
            val_str = f"{val:.0f}"
    elif isinstance(val, int):
        val_str = str(val)
    else:
        val_str = str(val)

    # Clean quotes and whitespace
    cleaned = val_str.strip().strip('"').strip("'").strip()
    if cleaned.lower() in ("nan", "none", "null", ""):
        return ""

    # Remove trailing .0 if present
    if cleaned.endswith(".0"):
        cleaned = cleaned[:-2]

    # Check for scientific notation like "4.07E+12" or "4.07e+12"
    if "e" in cleaned.lower() and re.match(r"^[-+]?[0-9]*\.?[0-9]+[eE][-+]?[0-9]+$", cleaned):
        try:
            d = Decimal(cleaned)
            cleaned = f"{int(d)}"
        except Exception:
            pass

    return cleaned.upper()


def normalise_rate(val: Any) -> Decimal:
    """
    Normalise GST tax rate to standard fraction representation (e.g. 0.18, 0.05, 0.12).
    Accepts fractions (0.18) or whole percentages (18, 18.0, "18%").
    """
    if val is None:
        return Decimal("0.00")
    if isinstance(val, str):
        val = val.replace("%", "").strip()
    d = to_decimal(val, round_cents=False)
    if d > Decimal("1.00"):
        # Given as 18 -> convert to 0.18
        d = d / Decimal("100.00")
    return d.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def rate_to_display_percent(rate_fraction: Decimal) -> str:
    """
    Convert rate fraction (0.18) to readable percent string '18%'.
    """
    pct = (rate_fraction * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if pct == pct.to_integral():
        return f"{int(pct)}%"
    return f"{pct:.2f}%"


# GST State codes mapping as defined in column_aliases.json
GST_STATE_CODES = {
    "01": "JAMMU & KASHMIR",
    "02": "HIMACHAL PRADESH",
    "03": "PUNJAB",
    "04": "CHANDIGARH",
    "05": "UTTARAKHAND",
    "06": "HARYANA",
    "07": "DELHI",
    "08": "RAJASTHAN",
    "09": "UTTAR PRADESH",
    "10": "BIHAR",
    "11": "SIKKIM",
    "12": "ARUNACHAL PRADESH",
    "13": "NAGALAND",
    "14": "MANIPUR",
    "15": "MIZORAM",
    "16": "TRIPURA",
    "17": "MEGHALAYA",
    "18": "ASSAM",
    "19": "WEST BENGAL",
    "20": "JHARKHAND",
    "21": "ODISHA",
    "22": "CHHATTISGARH",
    "23": "MADHYA PRADESH",
    "24": "GUJARAT",
    "25": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "26": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "27": "MAHARASHTRA",
    "29": "KARNATAKA",
    "30": "GOA",
    "31": "LAKSHADWEEP",
    "32": "KERALA",
    "33": "TAMIL NADU",
    "34": "PUDUCHERRY",
    "35": "ANDAMAN AND NICOBAR ISLANDS",
    "36": "TELANGANA",
    "37": "ANDHRA PRADESH",
    "38": "LADAKH",
    "97": "OTHER TERRITORY"
}

STATE_NAME_ALIASES = {
    "ORISSA": "ODISHA",
    "PONDICHERRY": "PUDUCHERRY",
    "UTTARANCHAL": "UTTARAKHAND",
    "JAMMU AND KASHMIR": "JAMMU & KASHMIR",
    "NEW DELHI": "DELHI",
    "DADRA AND NAGAR HAVELI": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DAMAN AND DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "ANDAMAN & NICOBAR ISLANDS": "ANDAMAN AND NICOBAR ISLANDS"
}

# Reverse lookup: Normalized uppercase state name to 2-digit code
STATE_NAME_TO_CODE = {}
for code, name in GST_STATE_CODES.items():
    STATE_NAME_TO_CODE[name.upper()] = code
for alias, standard in STATE_NAME_ALIASES.items():
    if standard.upper() in STATE_NAME_TO_CODE:
        STATE_NAME_TO_CODE[alias.upper()] = STATE_NAME_TO_CODE[standard.upper()]


def normalise_state(val: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalise place of supply / state to (2-digit GST code, Standard State Name).
    Accepts:
      - '33-Tamil Nadu' or '33 - TAMIL NADU'
      - '33' or 33
      - 'Tamil Nadu' or 'TAMIL NADU' or alias like 'Pondicherry'
    Returns:
      (code, name) e.g. ('33', 'TAMIL NADU'), or (None, None) if unknown.
    """
    if val is None:
        return None, None
    raw = str(val).strip().strip('"').strip("'")
    if not raw or raw.lower() in ("nan", "none", "null"):
        return None, None

    # Check for GST portal format "33-Tamil Nadu"
    match = re.match(r"^(\d{1,2})\s*[-:]\s*(.+)$", raw)
    if match:
        code = match.group(1).zfill(2)
        name = match.group(2).strip().upper()
        if code in GST_STATE_CODES:
            return code, GST_STATE_CODES[code]
        return code, name

    # Check if raw is purely 1 or 2 digits
    if raw.isdigit():
        code = raw.zfill(2)
        if code in GST_STATE_CODES:
            return code, GST_STATE_CODES[code]
        return code, None

    # Pure state name or alias
    cleaned_name = raw.upper().strip()
    cleaned_name = STATE_NAME_ALIASES.get(cleaned_name, cleaned_name)
    if cleaned_name in STATE_NAME_TO_CODE:
        code = STATE_NAME_TO_CODE[cleaned_name]
        return code, GST_STATE_CODES[code]

    # Substring search if slight spelling or spacing difference
    for std_name, code in STATE_NAME_TO_CODE.items():
        if std_name in cleaned_name or cleaned_name in std_name:
            return code, GST_STATE_CODES[code]

    return None, raw.upper()


def normalise_hsn(val: Any) -> str:
    """
    Normalise HSN / SAC code as clean string without decimal points or trailing spaces.
    e.g. 33049930.0 -> '33049930', '3304' -> '3304'.
    """
    return clean_id(val)


def match_hsn(mtr_hsn: str, gst_hsn: str) -> Tuple[bool, str]:
    """
    Compare MTR HSN and GST HSN:
    Match exact first, then on first 4 digits.
    Returns: (matched: bool, method: 'exact' | '4digit_prefix' | 'none')
    """
    h1 = clean_id(mtr_hsn)
    h2 = clean_id(gst_hsn)
    if not h1 or not h2:
        return False, "none"
    if h1 == h2:
        return True, "exact"
    if len(h1) >= 4 and len(h2) >= 4 and h1[:4] == h2[:4]:
        return True, "4digit_prefix"
    return False, "none"


def parse_date(val: Any) -> Optional[datetime]:
    """
    Parse date from varied Amazon export formats (datetime objects, ISO strings,
    '3 May 2026 9:09:23 am UTC', '2026-03-04 15:07:12', '04/03/2026', etc.).
    Returns Python datetime object or None.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day)

    raw = str(val).strip().strip('"').strip("'")
    if not raw or raw.lower() in ("nan", "none", "null", ""):
        return None

    # Remove trailing timezones like "UTC" or "+05:30"
    cleaned = re.sub(r"\s+UTC$", "", raw, flags=re.IGNORECASE).strip()

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%d %b %Y %I:%M:%S %p",
        "%d %b %Y %H:%M:%S",
        "%d %B %Y %I:%M:%S %p",
        "%d %B %Y %H:%M:%S",
        "%d %b %Y",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    # Try dateutil if available
    try:
        from dateutil import parser
        return parser.parse(cleaned)
    except Exception:
        return None


def to_iso_date(dt: Optional[datetime]) -> str:
    """Format datetime as ISO string YYYY-MM-DD."""
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d")


def to_display_date(dt: Optional[Union[datetime, str]]) -> str:
    """Format datetime or ISO string to Indian UI standard DD-MM-YYYY."""
    if not dt:
        return ""
    if isinstance(dt, str):
        parsed = parse_date(dt)
        if not parsed:
            return dt
        return parsed.strftime("%d-%m-%Y")
    return dt.strftime("%d-%m-%Y")
