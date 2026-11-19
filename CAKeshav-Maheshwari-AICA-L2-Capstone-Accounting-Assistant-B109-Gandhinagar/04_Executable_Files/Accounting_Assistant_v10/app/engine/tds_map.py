"""TDS section references: Income-tax Act 1961 sections for transactions before 01-04-2026, Income-tax Act 2025
s.393 table entries from 01-04-2026 (shown with the old section in brackets).

SEED TABLE - verify every row against the bare Act (s.393 tables) and the CBDT notification on payment codes
before relying on it. Secondary sources disagree on some codes and rates. The table is editable per company
(Company settings -> "tds_map")."""
from __future__ import annotations

import re

NEW_ACT_FROM = "20260401"
NA = "NA"                      # party / ledger where TDS is not applicable

# old code -> (new 2025-Act reference, nature, rate ind/HUF %, rate others %, threshold text)
SEED = {
    "194C": ("393(1) Sl. 6(i)", "Contractors / work contract", 1, 2, "₹30,000 single / ₹1,00,000 aggregate"),
    "194J-P": ("393(1) Sl. 6(iii)D(b)", "Professional services, director fees", 10, 10, "₹50,000"),
    "194J-T": ("393(1) Sl. 6(iii)D(a)", "Technical services, call centre, film royalty", 2, 2, "₹50,000"),
    "194I-B": ("393(1) Sl. 2(ii)D(b)", "Rent - land, building, furniture", 10, 10, "₹50,000 per month"),
    "194I-P": ("393(1) Sl. 2(ii)D(a)", "Rent - plant, machinery, equipment", 2, 2, "₹50,000 per month"),
    "194H": ("393(1) Sl. 1(ii)", "Commission / brokerage", 2, 2, "₹20,000"),
    "194D": ("393(1) Sl. 1(i)", "Insurance commission", None, None, "₹20,000"),
    "194A": ("393(1) Sl. 5(ii)/(iii)", "Interest other than on securities", 10, 10, "₹10,000 / ₹50,000"),
    "194Q": ("393(1) Sl. 8(ii)", "Purchase of goods (above ₹50 lakh)", 0.1, 0.1, "Above ₹50,00,000"),
    "194R": ("393(1) Sl. 8(iv)", "Business benefit / perquisite", 10, 10, "₹20,000"),
    "194-IA": ("393(1) Sl. 3(i)", "Transfer of immovable property", 1, 1, "₹50,00,000"),
    "194T": ("393(3) Sl. 7", "Payments to partners", 10, 10, "₹20,000"),
    "194M": ("393(1) Sl. 6(ii)", "Contract / professional fees by individuals not audited", 2, 2, "₹50,00,000"),
    "195": ("393(2) Sl. 17", "Payments to non-residents (other sums)", None, None, "-"),
}
LEGACY_ALIASES = {"194J": "194J-P", "194I": "194I-B", "194-I": "194I-B", "194IA": "194-IA", "194JB": "194J-P",
                  "194JA": "194J-T"}


def normalise(code: str) -> str:
    c = (code or "").strip().upper().replace(" ", "")
    if c in ("NA", "N.A.", "N/A", "NOTAPPLICABLE"):
        return NA
    return LEGACY_ALIASES.get(c, c)


def label(code: str, on_date: str = "", table: dict | None = None) -> str:
    """'194C' before 01-04-2026; '393(1) Sl. 6(i) (old 194C)' from 01-04-2026. 'Not applicable' for NA."""
    c = normalise(code)
    if not c:
        return ""
    if c == NA:
        return "Not applicable"
    old = c.split("-")[0] if c.startswith("194") and c[4:5] == "-" and len(c) > 5 and c[5] in "PTB" else c
    shown_old = {"194J-P": "194J(b)", "194J-T": "194J(a)", "194I-B": "194I(b)", "194I-P": "194I(a)"}.get(c, old)
    if on_date and on_date[:8] < NEW_ACT_FROM:
        return shown_old
    ref = (table or SEED).get(c, SEED.get(c, (None,)))[0]
    return f"{ref} (old {shown_old})" if ref else shown_old


def choices() -> list[tuple[str, str]]:
    """For dropdowns: (code, text)."""
    return [(NA, "Not applicable")] + [(k, f"{k} - {v[1]}") for k, v in SEED.items()]


# ------------------------------------------------------------------ guessing the section from what was booked
_LEDGER_HINTS = [
    (NA, r"insurance|premium|hotel|lodging|boarding|travel|air\s*fare|railway|fuel|petrol|diesel|electricity|"
         r"power|water\s*charges|telephone|mobile|internet|broadband|postage|courier\s*charges?|bank\s*charges|"
         r"stamp|government|govt|municipal|property\s*tax|roc|mca|gst\s*(late|fee)|penalty|interest\s*on\s*(tds|gst)|"
         r"donation|staff\s*welfare|food|refreshment|books\s*&?\s*periodicals|subscription|software\s*licen|"
         r"cloud|aws|google|microsoft|amazon\s*web|rates\s*&\s*taxes"),
    ("194J-P", r"professional|consult|legal|audit\s*fee|advocate|lawyer|ca\s*fee|chartered|retainer|"
               r"director.?s?\s*(sitting\s*)?fee|valuation|architect|doctor|medical\s*fee"),
    ("194J-T", r"technical\s*(service|fee)|call\s*cent|it\s*support|maintenance\s*contract|amc"),
    ("194I-B", r"\brent\b(?!.*(machin|equip|vehicle))|lease\s*rent|office\s*rent|godown\s*rent|warehouse\s*rent"),
    ("194I-P", r"(machin|equip|plant).*(rent|hire)|hire\s*charges"),
    ("194H", r"commission|brokerage"),
    ("194A", r"interest\s*(paid|on\s*(loan|unsecured|deposit))"),
    ("194C", r"contract|labour|labor|job\s*work|transport|freight|cartage|carriage|printing|advertis|"
             r"security\s*(service|charges)|housekeeping|cleaning|catering|manpower|repair|fabricat|packing\s*charges|"
             r"courier\s*service|event"),
]


def guess(expense_ledgers: list[str], party_group: str = "", is_goods_purchase: bool = False) -> str:
    """Most likely section for a party from the expense ledgers it is booked against."""
    text = " | ".join(expense_ledgers).lower()
    if is_goods_purchase and not re.search(r"contract|labour|job\s*work|service", text):
        return "194Q"
    for code, pat in _LEDGER_HINTS:
        if re.search(pat, text):
            return code
    return ""
