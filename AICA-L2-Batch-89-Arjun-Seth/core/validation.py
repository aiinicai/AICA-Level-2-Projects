# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Human-validation rules for extracted lease data.

Pure Python: no UI-framework imports, no database. The review screen and the "Confirm &
Proceed" step both use these functions, so what the user sees, what gets saved and what
the calculation engine receives can never drift apart.

"Canonical" values are what the engine understands: str, int, float, ``datetime.date`` and
"Y"/"N". Rates (escalation, IBR) are FRACTIONS (0.05 = 5%); the screen shows them as
percentages and converts at the boundary with ``to_widget`` / ``from_widget``.
"""
from datetime import date, timedelta

from core.calculation_engine import _add_months
from core.formatting import DEFAULT_CURRENCY, parse_currency

# (section title, [(field key, label, kind)]) - in the order shown on the review screen.
# kinds: text, longtext, date, int, amount, percent, yn, currency
REVIEW_SECTIONS = [
    (
        "Parties and asset",
        [
            ("lessor", "Lessor", "text"),
            ("lessee", "Lessee", "text"),
            ("asset_type", "Asset type", "text"),
            ("currency", "Currency", "currency"),
        ],
    ),
    (
        "Term",
        [
            ("commencement_date", "Commencement date", "date"),
            ("lease_end_date", "Lease end date", "date"),
            ("lease_term_months", "Lease term (months)", "int"),
        ],
    ),
    (
        "Rent and payments",
        [
            ("base_rent", "Monthly base rent, first lease year", "amount"),
            ("escalation", "Annual rent escalation (%)", "percent"),
            ("prepaid_rent", "Advance (prepaid) rent paid", "amount"),
            ("prepaid_rent_months", "Months covered by the advance rent", "int"),
            ("deposit", "Refundable security deposit", "amount"),
        ],
    ),
    (
        "Other lease costs",
        [
            ("idc", "Initial direct costs", "amount"),
            ("incentives", "Lease incentives received", "amount"),
            ("restoration_cost", "Restoration obligation", "amount"),
        ],
    ),
    (
        "Discount rate and asset",
        [
            ("ibr", "Discount rate / incremental borrowing rate (% per year)", "percent"),
            ("asset_fair_value", "Asset fair value", "amount"),
            ("asset_economic_life_months", "Asset economic life (months)", "int"),
        ],
    ),
    (
        "Classification inputs",
        [
            ("ownership_transfers", "Does ownership transfer to the lessee?", "yn"),
            ("bargain_purchase_option", "Is there a bargain purchase option?", "yn"),
            ("specialized_asset", "Is it a specialized asset?", "yn"),
            ("low_value_election", "Low-value asset election (Ind AS 116)?", "yn"),
        ],
    ),
    (
        "Other terms (for information)",
        [
            ("options", "Renewal / termination / purchase options", "longtext"),
            ("cpi_details", "CPI / variable rent details", "longtext"),
        ],
    ),
]

FIELD_KIND = {key: kind for _, fields in REVIEW_SECTIONS for key, _, kind in fields}
FIELD_LABEL = {key: label for _, fields in REVIEW_SECTIONS for key, label, _ in fields}

# The user MUST supply these (the AI rarely finds them); no safe default exists.
REQUIRED_FIELDS = (
    "commencement_date",
    "lease_term_months",
    "base_rent",
    "ibr",
    "asset_economic_life_months",
    "asset_fair_value",
    "ownership_transfers",
    "bargain_purchase_option",
    "specialized_asset",
    "low_value_election",
)
# Blank means "none": shown as 0 (flagged for the user to confirm) rather than left empty.
DEFAULT_ZERO_FIELDS = (
    "escalation",
    "prepaid_rent",
    "prepaid_rent_months",
    "idc",
    "incentives",
    "restoration_cost",
    "deposit",
)
ENGINE_INPUT_KEYS = (
    "commencement_date",
    "lease_term_months",
    "base_rent",
    "escalation",
    "prepaid_rent",
    "prepaid_rent_months",
    "idc",
    "incentives",
    "restoration_cost",
    "deposit",
    "ibr",
    "asset_economic_life_months",
    "asset_fair_value",
    "ownership_transfers",
    "bargain_purchase_option",
    "specialized_asset",
    "low_value_election",
)
_INT_KEYS = ("lease_term_months", "prepaid_rent_months", "asset_economic_life_months")
_AMOUNT_KEYS = ("base_rent", "prepaid_rent", "idc", "incentives", "restoration_cost", "deposit", "asset_fair_value")
_RATE_KEYS = ("escalation", "ibr")
_YN_KEYS = ("ownership_transfers", "bargain_purchase_option", "specialized_asset", "low_value_election")


# --------------------------------------------------------------------------- #
# Converting between stored text, canonical values and widget values
# --------------------------------------------------------------------------- #
def parse_stored(kind: str, text):
    """Stored text (ExtractedFields.ai_value / final_value) -> canonical value; None if empty/unreadable."""
    if text is None or (isinstance(text, str) and not text.strip()):
        return None
    try:
        if kind == "date":
            return date.fromisoformat(str(text).strip())
        if kind == "int":
            number = float(text)
            return int(number) if number.is_integer() else None
        if kind in ("amount", "percent"):
            return float(text)
        if kind == "yn":
            value = str(text).strip().upper()
            return value if value in ("Y", "N") else None
        if kind == "currency":
            return parse_currency(str(text))  # a supported 3-letter code, or None
        return str(text).strip()
    except (TypeError, ValueError):
        return None


def canonical_to_text(kind: str, value):
    """Canonical value -> text stored in the database (100000.0 -> '100000'; 0.05 -> '0.05')."""
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        raise ValueError("booleans are not valid field values")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return format(value, ".10g")
    return str(value)


def values_equal(kind: str, left, right) -> bool:
    """True if two canonical values are the same (floats compared with a tiny tolerance)."""
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, float) or isinstance(right, float):
        try:
            return abs(float(left) - float(right)) < 1e-9
        except (TypeError, ValueError):
            return False
    return left == right


def default_value(key: str, kind: str, default_currency: str = DEFAULT_CURRENCY):
    """What to pre-fill when the AI found nothing: 0 for 'none' style fields, the user's
    default currency for the currency, else nothing."""
    if key in DEFAULT_ZERO_FIELDS:
        return 0 if kind == "int" else 0.0
    if kind == "currency":
        return parse_currency(default_currency) or DEFAULT_CURRENCY
    return None


def to_widget(kind: str, value):
    """Canonical -> the value shown in the input widget (rates as percentages)."""
    if value is None:
        return None
    if kind == "percent":
        return round(float(value) * 100, 6)
    if kind == "int":
        return int(value)
    if kind == "amount":
        return float(value)
    return value


def from_widget(kind: str, value):
    """Widget value -> canonical (percentages back to fractions; blank text -> None)."""
    if value is None:
        return None
    if kind == "percent":
        return round(float(value) / 100, 10)
    if kind == "int":
        return int(value)
    if kind == "amount":
        return float(value)
    if kind in ("text", "longtext"):
        text = str(value).strip()
        return text or None
    return value


# --------------------------------------------------------------------------- #
# Checking the values before they reach the calculation engine
# --------------------------------------------------------------------------- #
def expected_end_date(commencement: date, term_months: int) -> date:
    """Last day of the lease: commencement + term months, minus one day (Excel EDATE - 1)."""
    return _add_months(commencement, term_months) - timedelta(days=1)


def prepaid_covered_rent(values: dict) -> float:
    """Escalated rent for the first ``prepaid_rent_months`` months (what advance rent should equal)."""
    base = values.get("base_rent") or 0.0
    escalation = values.get("escalation") or 0.0
    months = values.get("prepaid_rent_months") or 0
    return sum(base * (1 + escalation) ** ((n - 1) // 12) for n in range(1, int(months) + 1))


def validate_values(values: dict):
    """Return ``(errors, warnings)`` for the values on the review screen.

    Errors block "Confirm & Proceed"; warnings are shown but do not.
    """
    errors, warnings = [], []
    for key in REQUIRED_FIELDS:
        if values.get(key) is None:
            kind = FIELD_KIND[key]
            errors.append(
                "Please answer: {}".format(FIELD_LABEL[key]) if kind == "yn" else "{} is required".format(FIELD_LABEL[key])
            )

    term = values.get("lease_term_months")
    if term is not None and term < 1:
        errors.append("Lease term must be at least 1 month")
    months = values.get("prepaid_rent_months")
    if term is not None and months is not None and months > term:
        errors.append("Months covered by advance rent ({}) cannot exceed the lease term ({})".format(months, term))
    for key in _AMOUNT_KEYS + _INT_KEYS + _RATE_KEYS:
        value = values.get(key)
        if value is not None and value < 0:
            errors.append("{} cannot be negative".format(FIELD_LABEL[key]))

    commencement, end = values.get("commencement_date"), values.get("lease_end_date")
    if commencement is not None and term is not None and term >= 1 and end is not None:
        expected = expected_end_date(commencement, term)
        if end != expected:
            warnings.append(
                "The lease end date ({}) does not match commencement + term (which gives {}). "
                "Check the commencement date, the term and the end date.".format(end.isoformat(), expected.isoformat())
            )
    life = values.get("asset_economic_life_months")
    if term is not None and life is not None and term > life:
        warnings.append(
            "The lease term ({} months) is longer than the asset's economic life ({} months).".format(term, life)
        )
    prepaid = values.get("prepaid_rent")
    if prepaid is not None and months is not None and (prepaid or months):
        covered = prepaid_covered_rent(values)
        if abs(prepaid - covered) > 1.0:
            warnings.append(
                "Advance rent ({:,.2f}) differs from the rent for the first {} month(s) ({:,.2f}). "
                "For an operating lease the right-of-use asset will not reconcile to zero at the end unless "
                "these match.".format(prepaid, months, covered)
            )
    if values.get("ibr") == 0:
        warnings.append("The discount rate is 0%. Please confirm - it is normally the lessee's borrowing rate.")
    return errors, warnings


def build_engine_inputs(values: dict) -> dict:
    """Canonical review values -> the ``inputs`` dict of ``run_full_calculation``.

    Blank 'none'-style amounts become 0. Raises ValueError listing any missing required field.
    """
    missing = [FIELD_LABEL[key] for key in REQUIRED_FIELDS if values.get(key) is None]
    if missing:
        raise ValueError("Missing required value(s): {}".format(", ".join(missing)))
    inputs = {}
    for key in ENGINE_INPUT_KEYS:
        value = values.get(key)
        if value is None and key in DEFAULT_ZERO_FIELDS:
            value = 0
        if key in _INT_KEYS:
            value = int(value)
        elif key in _AMOUNT_KEYS or key in _RATE_KEYS:
            value = float(value)
        inputs[key] = value
    return inputs


def inputs_to_json(inputs: dict) -> str:
    """Engine inputs as JSON text (dates as ISO strings) for LeaseCase.inputs_json."""
    import json

    return json.dumps({k: (v.isoformat() if isinstance(v, date) else v) for k, v in inputs.items()})


def values_from_stored(record: dict, inputs: dict) -> dict:
    """Rebuild the review-form values of a SAVED lease: its engine inputs plus the lease record's own fields.

    ``record``: lessor, lessee, asset_type, currency, end_date. ``inputs``: the saved engine inputs (dates
    may be ISO strings). The two information-only text fields (options, cpi_details) are not stored, so
    they come back empty. Feeding the result to ``build_engine_inputs`` reproduces the saved inputs.
    """
    values = {key: None for key in FIELD_KIND}
    for key in ENGINE_INPUT_KEYS:
        value = inputs.get(key)
        if key == "commencement_date" and isinstance(value, str):
            value = date.fromisoformat(value)
        values[key] = value
    values["lessor"] = record.get("lessor") or None
    values["lessee"] = record.get("lessee") or None
    values["asset_type"] = record.get("asset_type") or None
    values["currency"] = record.get("currency") or None
    values["lease_end_date"] = record.get("end_date")
    return values


# --------------------------------------------------------------------------- #
# Manual entry (a lease typed in by hand)
# --------------------------------------------------------------------------- #
MANUAL_REQUIRED_PARTIES = ("lessor", "lessee")  # a lease with no parties is not a usable record


def is_missing_message(message: str) -> bool:
    """True for the 'X is required' / 'Please answer: X' messages (something still to fill in)."""
    return message.endswith("is required") or message.startswith("Please answer")


def validate_manual_values(values: dict):
    """``validate_values`` plus the parties (lessor and lessee) that a manually entered lease must have.

    Returns ``(errors, warnings)``; 'still to fill in' messages come first.
    """
    errors, warnings = validate_values(values)
    missing_parties = [
        "{} is required".format(FIELD_LABEL[key]) for key in MANUAL_REQUIRED_PARTIES if not values.get(key)
    ]
    return missing_parties + errors, warnings
