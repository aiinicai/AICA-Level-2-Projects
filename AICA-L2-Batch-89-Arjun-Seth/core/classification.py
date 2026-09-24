# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Lease classification engine.

Pure, deterministic functions that replicate the ``Classification`` sheet of
``LeaseIQ_Pro_POC_corrected.xlsx``:

* ASC 842 five-factor finance lease test (rows 6-10, result in B12)
* Ind AS 116 lessee recognition exemption tests (rows 16-17, result in B18,
  rationale in B19)

Pure Python only: no UI-framework imports are allowed in this module. No AI is involved: the classification is a rule-based calculation,
never an LLM output.
"""

# ASC 842 thresholds (Classification sheet, column C)
ASC842_LEASE_TERM_THRESHOLD = 0.75  # term >= 75% of economic life
ASC842_PV_THRESHOLD = 0.90  # PV of payments >= 90% of fair value
# Ind AS 116 short-term lease limit (Classification!C16)
SHORT_TERM_MONTHS = 12

_REQUIRED_KEYS = (
    "lease_term_months",
    "ownership_transfers",
    "bargain_purchase_option",
    "asset_economic_life_months",
    "lease_liability_initial",
    "asset_fair_value",
    "specialized_asset",
    "low_value_election",
)


def _yes_no(inputs: dict, key: str) -> str:
    """Return 'Y' or 'N'. Case-insensitive; anything else is an input error."""
    value = inputs[key]
    text = value.strip().upper() if isinstance(value, str) else None
    if text not in ("Y", "N"):
        raise ValueError("'{}' must be 'Y' or 'N', got {!r}".format(key, value))
    return text


def _number(inputs: dict, key: str) -> float:
    """Return a non-negative float; booleans and non-numbers are input errors."""
    value = inputs[key]
    if isinstance(value, bool):
        raise ValueError("'{}' must be a number, got {!r}".format(key, value))
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("'{}' must be a number, got {!r}".format(key, value)) from None
    if number != number or number < 0:  # NaN or negative
        raise ValueError("'{}' must be a non-negative number, got {!r}".format(key, value))
    return number


def _ratio(numerator: float, denominator: float) -> float:
    """Excel guard: IF(denominator > 0, numerator / denominator, 0)."""
    return numerator / denominator if denominator > 0 else 0.0


def _months(value: float) -> str:
    """Format a month count like Excel's string concatenation (60, not 60.0)."""
    return str(int(value)) if value == int(value) else str(value)


def classify_lease(inputs: dict) -> dict:
    """Classify a lease under ASC 842 and test Ind AS 116 recognition exemptions.

    Required ``inputs`` keys (field keys from the Excel ``Inputs`` sheet):
        lease_term_months, ownership_transfers [Y/N], bargain_purchase_option [Y/N],
        asset_economic_life_months, lease_liability_initial, asset_fair_value,
        specialized_asset [Y/N], low_value_election [Y/N]

    Returns a dict with:
        asc842_classification: "FINANCE LEASE" or "OPERATING LEASE"
        asc842_test_results: list of the 5 tests, in Excel row order, each a dict
            {test, computed_value, threshold, met, rationale} where ``met`` is "Y"/"N"
            and ratio tests carry fractions (0.125 == 12.5%)
        ind_as116_exemption: "EXEMPT" or "ON-BALANCE SHEET"
        ind_as116_rationale: short text explanation

    Raises ValueError for missing keys, non-numeric amounts, or Y/N fields that
    are not Y or N (the code equivalent of the workbook's "REVIEW" checks).
    """
    missing = [key for key in _REQUIRED_KEYS if key not in inputs]
    if missing:
        raise ValueError("Missing required input(s): {}".format(", ".join(missing)))

    term = _number(inputs, "lease_term_months")
    if term <= 0:
        raise ValueError("'lease_term_months' must be greater than 0, got {!r}".format(term))
    economic_life = _number(inputs, "asset_economic_life_months")
    pv_of_payments = _number(inputs, "lease_liability_initial")
    fair_value = _number(inputs, "asset_fair_value")
    ownership = _yes_no(inputs, "ownership_transfers")
    bargain = _yes_no(inputs, "bargain_purchase_option")
    specialized = _yes_no(inputs, "specialized_asset")
    low_value = _yes_no(inputs, "low_value_election")

    # ---- ASC 842 - Five-Factor Finance Lease Test (Classification!A6:E10) ----
    term_ratio = _ratio(term, economic_life)
    pv_ratio = _ratio(pv_of_payments, fair_value)

    tests = [
        {
            "test": "1. Transfer of ownership to lessee",
            "computed_value": ownership,
            "threshold": "Y",
            "met": "Y" if ownership == "Y" else "N",
            "rationale": "Finance criterion if Y",
        },
        {
            "test": "2. Bargain purchase option",
            "computed_value": bargain,
            "threshold": "Y",
            "met": "Y" if bargain == "Y" else "N",
            "rationale": "Finance criterion if Y",
        },
        {
            "test": "3. Lease term \u2265 75% of economic life",
            "computed_value": term_ratio,
            "threshold": ASC842_LEASE_TERM_THRESHOLD,
            "met": "Y" if term_ratio >= ASC842_LEASE_TERM_THRESHOLD else "N",
            "rationale": "term_months / asset_economic_life_months",
        },
        {
            "test": "4. PV of lease payments \u2265 90% of fair value",
            "computed_value": pv_ratio,
            "threshold": ASC842_PV_THRESHOLD,
            "met": "Y" if pv_ratio >= ASC842_PV_THRESHOLD else "N",
            "rationale": "lease_liability_initial / asset_fair_value",
        },
        {
            "test": "5. Specialized asset",
            "computed_value": specialized,
            "threshold": "Y",
            "met": "Y" if specialized == "Y" else "N",
            "rationale": "Finance criterion if Y",
        },
    ]
    any_met = any(t["met"] == "Y" for t in tests)
    asc842_classification = "FINANCE LEASE" if any_met else "OPERATING LEASE"

    # ---- Ind AS 116 recognition exemptions (Classification!A16:B19) ----
    short_term = term <= SHORT_TERM_MONTHS and bargain == "N"
    if short_term:
        exemption = "EXEMPT"
        rationale = (
            "Short-term lease (term \u2264 12 months, no purchase option): "
            "recognition exemption applies."
        )
    elif low_value == "Y":
        exemption = "EXEMPT"
        rationale = "Low-value asset election made: recognition exemption applies."
    else:
        exemption = "ON-BALANCE SHEET"
        if term > SHORT_TERM_MONTHS:
            rationale = (
                "Term of {} months exceeds 12 months and no low-value election: "
                "single lessee model \u2013 recognise ROU asset and lease liability."
            ).format(_months(term))
        else:
            # Term <= 12 months but a purchase option removes the short-term
            # exemption. (The Excel workbook's text says "exceeds 12 months" here,
            # which would be wrong, so the wording is corrected for this case.)
            rationale = (
                "Term of {} months is 12 months or less, but the lease includes a "
                "purchase option so the short-term exemption does not apply, and no "
                "low-value election: single lessee model \u2013 recognise ROU asset "
                "and lease liability."
            ).format(_months(term))

    return {
        "asc842_classification": asc842_classification,
        "asc842_test_results": tests,
        "ind_as116_exemption": exemption,
        "ind_as116_rationale": rationale,
    }
