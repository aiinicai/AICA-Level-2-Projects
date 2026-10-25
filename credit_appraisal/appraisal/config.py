"""
config.py
=========
Single source of truth for every tunable number in the appraisal engine:

* NBFC policy guardrails (``PolicyLimits``)
* Risk-scorecard weights, metric bounds and grade bands
* Ratio metadata used for RAG (red/amber/green) colour-coding in the UI
* Small formatting helpers shared by the UI and the memo generator

All monetary values in this application are in ₹ Crore unless stated otherwise.
Ratios are stored as plain fractions internally (0.15 == 15%) and only
formatted as percentages at the presentation layer.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

DAYS_IN_YEAR = 365


# --------------------------------------------------------------------------- #
# 1. Policy guardrails
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PolicyLimits:
    """NBFC credit-policy guardrails applied to the PRO-FORMA (post-loan) position."""

    min_dscr: float = 1.35          # Minimum Debt Service Coverage Ratio (x)
    max_de: float = 3.0             # Maximum Total Debt / Tangible Net Worth (x)
    min_icr: float = 2.0            # Minimum Interest Coverage Ratio (x)
    max_debt_ebitda: float = 4.5    # Maximum Total Debt / EBITDA (x)
    min_facility_cr: float = 10.0   # Facility ticket-size band (₹ Cr)
    max_facility_cr: float = 50.0
    min_security_cover: float = 1.25  # Minimum collateral cover on proposed loan (x)
    min_bureau_score: float = 700.0  # Minimum credit bureau score (300-900 scale); soft check, skipped if not supplied
    critical_dscr: float = 1.0      # Below this the loan cannot be serviced from cash flows

    def with_overrides(self, **kwargs) -> "PolicyLimits":
        return replace(self, **kwargs)


# --------------------------------------------------------------------------- #
# 2. Scorecard
# --------------------------------------------------------------------------- #
# Pillar weights (must sum to 1.0)
PILLAR_WEIGHTS = {
    "Profitability": 0.30,
    "Leverage": 0.30,
    "Liquidity": 0.20,
    "Scale & Vintage": 0.20,
}

# Each metric: (key, label, weight within pillar, worst value, best value)
# Score = linear interpolation between `worst` (0 pts) and `best` (100 pts), clipped.
# "worst" > "best" simply means "lower is better" (e.g. leverage, CCC).
# Keys prefixed pf_ are pro-forma (post-loan) metrics from exposure.py.
SCORING_SPEC = {
    "Profitability": [
        ("ebitda_margin", "EBITDA margin", 0.30, 0.04, 0.20),
        ("npm", "Net profit margin", 0.20, 0.00, 0.08),
        ("roce", "ROCE", 0.30, 0.05, 0.20),
        ("roe", "ROE", 0.20, 0.05, 0.20),
    ],
    "Leverage": [
        ("pf_debt_ebitda", "Pro-forma Debt / EBITDA", 0.30, 6.0, 1.5),
        ("pf_de", "Pro-forma Debt / TNW", 0.25, 4.0, 0.75),
        ("pf_icr", "Pro-forma ICR", 0.20, 1.0, 4.0),
        ("pf_dscr", "Pro-forma DSCR", 0.25, 1.0, 2.0),
    ],
    "Liquidity": [
        ("current_ratio", "Current ratio", 0.30, 0.8, 1.6),
        ("quick_ratio", "Quick ratio", 0.25, 0.5, 1.1),
        ("cash_ratio", "Cash ratio", 0.15, 0.02, 0.20),
        ("ccc", "Cash conversion cycle (days)", 0.30, 150, 30),
    ],
    "Scale & Vintage": [
        ("revenue", "Revenue (₹ Cr)", 0.30, 50, 1500),
        ("vintage", "Years in operation", 0.25, 3, 25),
        ("tnw", "Tangible net worth (₹ Cr)", 0.20, 20, 400),
        # Optional: if no bureau score is supplied it is skipped and the other weights re-normalise
        ("bureau_score", "Credit bureau score (300-900)", 0.25, 550, 800),
    ],
}

# (minimum composite score, grade, label) - evaluated top to bottom
GRADE_BANDS = [
    (80, "A", "Low risk"),
    (65, "B", "Moderate risk"),
    (50, "C", "Elevated risk"),
    (35, "D", "High risk"),
    (0, "E", "Very high risk"),
]
GRADE_ORDER = ["A", "B", "C", "D", "E"]

# Colours reused across the UI
COLORS = {
    "ink": "#1F2A44",
    "teal": "#0F766E",
    "green": "#15803D",
    "amber": "#B45309",
    "red": "#B42318",
    "grey": "#6B7280",
    "green_bg": "rgba(21,128,61,0.16)",
    "amber_bg": "rgba(217,119,6,0.18)",
    "red_bg": "rgba(180,35,24,0.16)",
}
GRADE_COLORS = {"A": "#15803D", "B": "#0F766E", "C": "#B45309", "D": "#C2410C", "E": "#B42318"}


# --------------------------------------------------------------------------- #
# 3. Ratio metadata  (label, category, unit, direction, comfortable, breach)
# --------------------------------------------------------------------------- #
# unit: "pct" | "x" | "days"
# hb  : True if a higher value is better
# good: value at/beyond which the cell is GREEN
# bad : value at/beyond which the cell is RED   (between the two = AMBER)
RATIO_META = {
    # Profitability
    "ebitda_margin": dict(label="EBITDA margin", cat="Profitability", unit="pct", hb=True, good=0.15, bad=0.08),
    "opm": dict(label="Operating profit margin (EBIT/Revenue)", cat="Profitability", unit="pct", hb=True, good=0.10, bad=0.04),
    "npm": dict(label="Net profit margin", cat="Profitability", unit="pct", hb=True, good=0.06, bad=0.02),
    "roe": dict(label="Return on equity", cat="Profitability", unit="pct", hb=True, good=0.15, bad=0.08),
    "roce": dict(label="Return on capital employed", cat="Profitability", unit="pct", hb=True, good=0.15, bad=0.09),
    "roa": dict(label="Return on assets", cat="Profitability", unit="pct", hb=True, good=0.06, bad=0.02),
    # Liquidity
    "current_ratio": dict(label="Current ratio", cat="Liquidity", unit="x", hb=True, good=1.33, bad=1.00),
    "quick_ratio": dict(label="Quick ratio", cat="Liquidity", unit="x", hb=True, good=0.90, bad=0.60),
    "cash_ratio": dict(label="Cash ratio", cat="Liquidity", unit="x", hb=True, good=0.20, bad=0.05),
    "dso": dict(label="Debtor days (DSO)", cat="Working capital", unit="days", hb=False, good=60, bad=90),
    "dio": dict(label="Inventory days (DIO)", cat="Working capital", unit="days", hb=False, good=60, bad=100),
    "dpo": dict(label="Creditor days (DPO)", cat="Working capital", unit="days", hb=True, good=45, bad=20),
    "ccc": dict(label="Cash conversion cycle", cat="Working capital", unit="days", hb=False, good=60, bad=110),
    # Gearing & coverage  (good/bad for the four policy ratios are overwritten from PolicyLimits)
    "de": dict(label="Debt / Tangible net worth", cat="Gearing & coverage", unit="x", hb=False, good=1.5, bad=3.0),
    "tol_tnw": dict(label="Total outside liabilities / TNW", cat="Gearing & coverage", unit="x", hb=False, good=3.0, bad=5.0),
    "debt_ebitda": dict(label="Total debt / EBITDA", cat="Gearing & coverage", unit="x", hb=False, good=3.0, bad=4.5),
    "icr": dict(label="Interest coverage (EBIT/Interest)", cat="Gearing & coverage", unit="x", hb=True, good=3.0, bad=2.0),
    "dscr": dict(label="DSCR (EBITDA - Capex - Tax)/(P+I)", cat="Gearing & coverage", unit="x", hb=True, good=1.75, bad=1.35),
    "dscr_cash": dict(label="DSCR - cash accrual basis (supplementary)", cat="Gearing & coverage", unit="x", hb=True, good=1.75, bad=1.20),
}


def ratio_meta_for(limits: PolicyLimits) -> dict:
    """Return RATIO_META with the four policy-driven RED thresholds aligned to the active policy."""
    meta = {k: dict(v) for k, v in RATIO_META.items()}
    meta["de"]["bad"] = limits.max_de
    meta["de"]["good"] = round(limits.max_de * 0.5, 2)
    meta["debt_ebitda"]["bad"] = limits.max_debt_ebitda
    meta["debt_ebitda"]["good"] = round(limits.max_debt_ebitda * 2 / 3, 2)
    meta["icr"]["bad"] = limits.min_icr
    meta["icr"]["good"] = round(limits.min_icr * 1.5, 2)
    meta["dscr"]["bad"] = limits.min_dscr
    meta["dscr"]["good"] = round(limits.min_dscr * 1.3, 2)
    return meta


def rag_status(value: float, meta: dict) -> str:
    """Classify a ratio value as 'green' / 'amber' / 'red' / 'na'."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "na"
    if meta["hb"]:
        if value >= meta["good"]:
            return "green"
        return "red" if value < meta["bad"] else "amber"
    if value <= meta["good"]:
        return "green"
    return "red" if value > meta["bad"] else "amber"


# --------------------------------------------------------------------------- #
# 4. Formatting helpers
# --------------------------------------------------------------------------- #
def fmt_value(value, unit: str) -> str:
    """Format a number according to its unit. NaN -> 'n.a.', +/-inf -> 'n.m.' (not meaningful)."""
    if value is None:
        return "n.a."
    try:
        if np.isnan(value):
            return "n.a."
        if np.isinf(value):
            return "n.m."
    except TypeError:
        return str(value)
    if unit == "pct":
        return f"{value * 100:.1f}%"
    if unit == "x":
        return f"{value:.2f}x"
    if unit == "days":
        return f"{value:.0f}"
    if unit == "score":
        return f"{value:.0f}"
    if unit == "cr":
        return f"₹{value:,.1f} Cr"
    return f"{value:,.2f}"
