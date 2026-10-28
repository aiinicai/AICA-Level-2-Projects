"""
Indian Currency Formatting and UI Display Helpers for MarketMatch.
Standard: ₹ 1,23,456.00 format (Lakhs and Crores grouping), DD-MM-YYYY dates.
"""
from decimal import Decimal
from typing import Union
from core.normalise import to_decimal


def format_inr(val: Union[Decimal, float, int, str, None], include_symbol: bool = True) -> str:
    """
    Format number into Indian Rupee format with proper comma separators:
    e.g. 1234567.89 -> '₹ 12,34,567.89'
    Handles negative numbers: -1234567.89 -> '-₹ 12,34,567.89'
    """
    if val is None:
        return "₹ 0.00" if include_symbol else "0.00"

    d = to_decimal(val)
    is_negative = d < Decimal("0.00")
    abs_d = abs(d)

    # Split into integer and decimal parts
    parts = f"{abs_d:.2f}".split(".")
    int_str = parts[0]
    dec_str = parts[1]

    # Indian numbering grouping: rightmost 3 digits, then groups of 2 digits
    if len(int_str) <= 3:
        formatted_int = int_str
    else:
        last3 = int_str[-3:]
        remaining = int_str[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        groups.append(last3)
        formatted_int = ",".join(groups)

    result = f"{formatted_int}.{dec_str}"
    prefix = "-₹ " if (is_negative and include_symbol) else ("-" if is_negative else ("₹ " if include_symbol else ""))
    return f"{prefix}{result}"


def format_pct(val: Union[Decimal, float, int, None]) -> str:
    """Format decimal fraction (0.18) or percentage into '18.00%'."""
    if val is None:
        return "0.00%"
    d = to_decimal(val, round_cents=False)
    if d <= Decimal("1.00") and d > Decimal("0.00"):
        d = d * Decimal("100.00")
    return f"{d:.2f}%"


def status_badge_html(status: str) -> str:
    """Generate color-coded HTML pill badge for statuses."""
    color_map = {
        "Matched": "#28a745",
        "Released": "#28a745",
        "Recovered": "#28a745",
        "Short paid": "#dc3545",
        "Excess paid": "#ffc107",
        "Not paid": "#dc3545",
        "Duplicate": "#fd7e14",
        "Duplicate payout": "#fd7e14",
        "Awaiting release (Timing)": "#17a2b8",
        "Timing difference": "#17a2b8",
        "Deferred": "#17a2b8",
        "Open": "#dc3545",
        "Claimed": "#fd7e14",
        "Rounding": "#6c757d",
        "Unexplained": "#e83e8c"
    }
    bg_color = color_map.get(status, "#6c757d")
    text_color = "#ffffff" if bg_color != "#ffc107" else "#212529"
    return f'<span style="background-color: {bg_color}; color: {text_color}; padding: 3px 8px; border-radius: 12px; font-size: 0.85em; font-weight: 500;">{status}</span>'


def reason_badge_html(reason: str) -> str:
    """Generate HTML badge for discrepancy reason codes."""
    color_map = {
        "Fees": "#6f42c1",
        "Returns/Refunds": "#e83e8c",
        "Timing/Cut-off": "#17a2b8",
        "TCS/TDS": "#20c997",
        "Duplicate": "#fd7e14",
        "Missing payout": "#dc3545",
        "Missing in GST": "#d63384",
        "Rate/Value mismatch": "#ffc107",
        "Place-of-supply": "#0dcaf0",
        "Rounding": "#6c757d",
        "Unexplained": "#b02a37"
    }
    bg_color = color_map.get(reason, "#495057")
    text_color = "#ffffff" if bg_color != "#ffc107" else "#212529"
    return f'<span style="background-color: {bg_color}; color: {text_color}; padding: 3px 8px; border-radius: 12px; font-size: 0.82em; font-weight: 500;">{reason}</span>'
