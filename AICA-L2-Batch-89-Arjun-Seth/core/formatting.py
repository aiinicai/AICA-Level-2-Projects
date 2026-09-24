# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Number and currency formatting (display only).

Pure Python: no UI framework, no database. Calculations always use full-precision numbers;
this module only decides how an amount is SHOWN.

* Number formats: "indian" groups as 5,00,000 (last 3 digits, then pairs) and
  "international" as 5,000,000.
* Currencies: a fixed list of major currencies with symbol and number of decimals.
  No conversion between currencies is ever done - a lease is in ONE currency.
"""
import math
from decimal import ROUND_HALF_UP, Decimal

NUMBER_FORMATS = {
    "indian": "Indian (5,00,000)",
    "international": "International (5,000,000)",
}
DEFAULT_NUMBER_FORMAT = "indian"
DEFAULT_CURRENCY = "INR"

# code: (name, symbol shown before the amount, decimal places)
CURRENCIES = {
    "INR": ("Indian Rupee", "\u20b9", 2),
    "USD": ("US Dollar", "$", 2),
    "GBP": ("British Pound", "\u00a3", 2),
    "EUR": ("Euro", "\u20ac", 2),
    "JPY": ("Japanese Yen", "\u00a5", 0),
    "CNY": ("Chinese Yuan", "CN\u00a5", 2),
    "AUD": ("Australian Dollar", "A$", 2),
    "CAD": ("Canadian Dollar", "C$", 2),
    "CHF": ("Swiss Franc", "CHF", 2),
    "SGD": ("Singapore Dollar", "S$", 2),
    "HKD": ("Hong Kong Dollar", "HK$", 2),
    "NZD": ("New Zealand Dollar", "NZ$", 2),
    "AED": ("UAE Dirham", "AED", 2),
    "SAR": ("Saudi Riyal", "SAR", 2),
    "QAR": ("Qatari Riyal", "QAR", 2),
    "KWD": ("Kuwaiti Dinar", "KWD", 3),
    "ZAR": ("South African Rand", "R", 2),
    "KRW": ("South Korean Won", "\u20a9", 0),
    "SEK": ("Swedish Krona", "SEK", 2),
    "NOK": ("Norwegian Krone", "NOK", 2),
    "DKK": ("Danish Krone", "DKK", 2),
    "PLN": ("Polish Zloty", "PLN", 2),
    "CZK": ("Czech Koruna", "CZK", 2),
    "TRY": ("Turkish Lira", "\u20ba", 2),
    "ILS": ("Israeli Shekel", "\u20aa", 2),
    "MYR": ("Malaysian Ringgit", "RM", 2),
    "THB": ("Thai Baht", "\u0e3f", 2),
    "IDR": ("Indonesian Rupiah", "Rp", 2),
    "PHP": ("Philippine Peso", "\u20b1", 2),
    "VND": ("Vietnamese Dong", "\u20ab", 0),
    "BRL": ("Brazilian Real", "R$", 2),
    "MXN": ("Mexican Peso", "MX$", 2),
    "PKR": ("Pakistani Rupee", "PKR", 2),
    "BDT": ("Bangladeshi Taka", "BDT", 2),
    "LKR": ("Sri Lankan Rupee", "LKR", 2),
    "NPR": ("Nepalese Rupee", "NPR", 2),
}
CURRENCY_CODES = list(CURRENCIES)

# a few things people actually type, mapped to a supported code
_ALIASES = {"\u20b9": "INR", "RS": "INR", "RS.": "INR", "\u00a3": "GBP", "\u20ac": "EUR", "US$": "USD"}


def parse_currency(text):
    """Return the supported 3-letter code for what was typed (case-insensitive), or None."""
    if not isinstance(text, str):
        return None
    cleaned = text.strip().upper()
    if cleaned in CURRENCIES:
        return cleaned
    return _ALIASES.get(cleaned)


def currency_label(code: str) -> str:
    """'INR - Indian Rupee (\u20b9)'; the symbol is left out when it is just the code again."""
    if code not in CURRENCIES:
        return str(code)
    name, symbol, _ = CURRENCIES[code]
    return "{} - {}".format(code, name) if symbol == code else "{} - {} ({})".format(code, name, symbol)


def currency_decimals(code: str) -> int:
    return CURRENCIES[code][2] if code in CURRENCIES else 2


def _group(whole: str, style: str) -> str:
    if len(whole) <= 3:
        return whole
    head, tail = whole[:-3], whole[-3:]
    size = 2 if style == "indian" else 3
    parts = []
    while len(head) > size:
        parts.insert(0, head[-size:])
        head = head[:-size]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def format_number(value, style: str = DEFAULT_NUMBER_FORMAT, decimals: int = 2) -> str:
    """5079693.7337 -> '50,79,693.73' (indian) or '5,079,693.73' (international); None/NaN -> '-'."""
    if style not in NUMBER_FORMATS:
        raise ValueError("number format must be one of {}, got {!r}".format(", ".join(NUMBER_FORMATS), style))
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "-"
    quantum = Decimal(1).scaleb(-decimals)
    amount = Decimal(repr(float(value))).quantize(quantum, rounding=ROUND_HALF_UP)  # round half up, as on paper
    negative = amount < 0
    whole, _, fraction = "{:f}".format(abs(amount)).partition(".")
    text = _group(whole, style) + ("." + fraction if decimals else "")
    return "-" + text if negative else text


def format_money(value, currency: str = DEFAULT_CURRENCY, style: str = DEFAULT_NUMBER_FORMAT) -> str:
    """5079693.73 -> '₹ 50,79,693.73' / '$ 5,079,693.73'. An unknown code is shown as a prefix, never an error."""
    code = parse_currency(currency) or str(currency or DEFAULT_CURRENCY).strip().upper()
    symbol = CURRENCIES[code][1] if code in CURRENCIES else code
    number = format_number(value, style, currency_decimals(code))
    if number == "-":  # nothing to show (None / NaN)
        return "-"
    if number.startswith("-"):
        return "-{} {}".format(symbol, number[1:])
    return "{} {}".format(symbol, number)


def format_approx(value, style: str = DEFAULT_NUMBER_FORMAT) -> str:
    """A rounded, spoken-style size of an amount: 5079693.73 -> '50.8 lakh' (indian) or '5.08 million' (international).

    Amounts below 1 lakh (indian) / 1 million (international) are returned in full ('99,999').
    """
    if style not in NUMBER_FORMATS:
        raise ValueError("number format must be one of {}, got {!r}".format(", ".join(NUMBER_FORMATS), style))
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "-"
    sign, size = ("-" if value < 0 else ""), abs(float(value))
    if style == "indian":
        if size >= 1e7:
            return "{}{} crore".format(sign, format_number(size / 1e7, style, 2))
        if size >= 1e5:
            return "{}{} lakh".format(sign, format_number(size / 1e5, style, 1))
    else:
        if size >= 1e9:
            return "{}{} billion".format(sign, format_number(size / 1e9, style, 2))
        if size >= 1e6:
            return "{}{} million".format(sign, format_number(size / 1e6, style, 2))
    return "{}{}".format(sign, format_number(size, style, 0))


def format_compact_money(value, currency: str = DEFAULT_CURRENCY, style: str = DEFAULT_NUMBER_FORMAT) -> str:
    """A short amount for small spaces: 1346000 -> '\u20b9 13.5 lakh' (indian) or '$ 1.35 million' (international).

    Amounts below 1 lakh / 1 million are shown in full without decimals. None / NaN -> '-'.
    """
    approx = format_approx(value, style)
    if approx == "-":
        return "-"
    code = parse_currency(currency) or str(currency or DEFAULT_CURRENCY).strip().upper()
    symbol = CURRENCIES[code][1] if code in CURRENCIES else code
    if approx.startswith("-"):
        return "-{} {}".format(symbol, approx[1:])
    return "{} {}".format(symbol, approx)
