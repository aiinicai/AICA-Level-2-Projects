# =====================================================================================
#  CASH FLOW FORECASTING PRO  -  v1.0
#  Single-file, integrated five-year financial forecasting application (PyQt6).
#
#  Run in IDLE:  Run > Run Module  (F5)
#  Or Terminal:  python3 "Financial Forecast Buidder.py"
#
#  MANUAL INSTALL (one line, if auto-install is blocked):
#  python3 -m pip install --upgrade pip PyQt6 pandas numpy openpyxl matplotlib
#
#  FILE LAYOUT (paste the four parts in order into this one file)
#    Part 1  bootstrap, imports, schema, assumptions, scenarios, historical container
#    Part 2  tolerant Excel parser + historical analysis engine
#    Part 3  forecast engine, model checks, sensitivity, Excel export, demo data, tests
#    Part 4  PyQt6 user interface and application entry point
#
#  MODELLING PRINCIPLE
#    This is one dependency-driven model, not a set of independent formulas:
#      assumptions -> revenue -> operating costs -> EBITDA -> PPE/capex/depreciation
#      -> EBIT -> debt/interest -> PBT -> tax -> PAT -> retained earnings
#      -> working capital -> cash flow -> funding plug -> closing cash -> balance sheet
#    The interest/debt/cash circularity is resolved by damped iteration to a tolerance,
#    which is the deterministic equivalent of Excel's iterative calculation.
# =====================================================================================

from __future__ import annotations

# -------------------------------------------------------------------------------------
# PART 1.1  BOOTSTRAP - install every third-party library BEFORE it is imported
# -------------------------------------------------------------------------------------
import importlib
import subprocess
import sys

APP_NAME = "Cash Flow Forecasting Pro"
APP_VERSION = "1.0"

# (import name, pip name)
REQUIREMENTS = [
    ("PyQt6", "PyQt6"),
    ("numpy", "numpy"),
    ("pandas", "pandas"),
    ("openpyxl", "openpyxl"),
    ("matplotlib", "matplotlib"),
    ("rapidfuzz", "rapidfuzz"),
]

MANUAL_INSTALL_LINE = (
    "python3 -m pip install --upgrade pip PyQt6 pandas numpy openpyxl matplotlib"
)


def _pip(args: list) -> bool:
    """Run pip in this same interpreter. Returns True on success."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip"] + list(args))
        return True
    except Exception:
        return False


def ensure_packages() -> None:
    """Import-test each requirement and install only what is missing."""
    missing = []
    for module_name, pip_name in REQUIREMENTS:
        try:
            importlib.import_module(module_name)
        except Exception:
            missing.append((module_name, pip_name))

    if not missing:
        return

    print("=" * 74)
    print(f"{APP_NAME} {APP_VERSION}: preparing environment, please wait ...")
    print(f"Python {sys.version.split()[0]}  |  {len(missing)} library(ies) to install")
    print("=" * 74)

    _pip(["install", "--upgrade", "pip", "--quiet", "--disable-pip-version-check"])

    failed = []
    for module_name, pip_name in missing:
        print(f"  installing {pip_name} ...")
        ok = _pip(["install", "--quiet", "--disable-pip-version-check", pip_name])
        if not ok:
            # Retry into the user site-packages (typical macOS permissions fix).
            ok = _pip(["install", "--quiet", "--user",
                       "--disable-pip-version-check", pip_name])
        importlib.invalidate_caches()
        try:
            importlib.import_module(module_name)
            print(f"  {pip_name}: ready")
        except Exception:
            failed.append(pip_name)
            print(f"  {pip_name}: COULD NOT BE INSTALLED AUTOMATICALLY")

    if failed:
        print("-" * 74)
        print("Please run this once in Terminal, then re-run this file:")
        print("  " + MANUAL_INSTALL_LINE)
        print("-" * 74)
    else:
        print("Environment ready.\n")


ensure_packages()


# -------------------------------------------------------------------------------------
# PART 1.1b  LABEL SUGGESTION SUPPORT
# rapidfuzz gives a much better "did you mean ..." hint on an unrecognised caption.
# If it cannot be installed, difflib is used instead, so the application still runs.
# -------------------------------------------------------------------------------------
try:
    from rapidfuzz import process as _rf_process, fuzz as _rf_fuzz
    _HAVE_RAPIDFUZZ = True
except Exception:
    _HAVE_RAPIDFUZZ = False


def _suggest_line_item(label, candidates):
    """Best guess at the canonical line item behind a caption the parser did not
    recognise. Used only to make a validation message easier to act on; it never
    changes what was actually imported."""
    import difflib as _difflib
    if not candidates:
        return None
    if _HAVE_RAPIDFUZZ:
        match = _rf_process.extractOne(label, candidates, scorer=_rf_fuzz.WRatio)
        return match[0] if match and match[1] >= 55 else None
    close = _difflib.get_close_matches(label, candidates, n=1, cutoff=0.4)
    return close[0] if close else None


# #region agent log
def _agent_dbg(hypothesis_id, location, message, data=None, run_id="syntax-repair"):
    import json, time
    try:
        with open("/Users/shwprabh/.cursor/debug-logs/debug-bd7729.log", "a", encoding="utf-8") as _df:
            _df.write(json.dumps({"sessionId": "bd7729", "runId": run_id, "hypothesisId": hypothesis_id, "location": location, "message": message, "data": data or {}, "timestamp": int(time.time() * 1000)}) + "\n")
    except Exception:
        pass
# #endregion

# -------------------------------------------------------------------------------------
# PART 1.2  IMPORTS (safe now that the bootstrap has completed)
# -------------------------------------------------------------------------------------
import copy
import difflib
import math
import os
import re
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

_agent_dbg("A", "Cash_Flow_Forecasting_Pro_FINAL.py:imports", "imports_ok", {"src_lines": None})

import numpy as np
import pandas as pd

# =====================================================================================
# PART 1.3  UNITS
# All internal calculations are performed in a single base unit: INR lakh.
# Presentation units are applied only at the display / export layer.
# =====================================================================================
BASE_UNIT = "INR lakh"

# Multiplier that converts a value expressed in the detected unit into INR lakh.
UNIT_TO_LAKH: Dict[str, float] = {
    "billion": 10000.0,
    "crore": 100.0,
    "cr": 100.0,
    "million": 10.0,
    "mn": 10.0,
    "lakh": 1.0,
    "lac": 1.0,
    "thousand": 0.01,
    "'000": 0.01,
    "rupees": 1e-5,
    "inr": 1e-5,
}

# Divisor applied to base-unit values purely for on-screen presentation.
DISPLAY_UNITS: Dict[str, float] = {"Rs lakh": 1.0, "Rs crore": 100.0}

DISPLAY_MODES: Tuple[str, ...] = (
    "Rs lakh",
    "Rs crore",
    "% of revenue",
    "Absolute change",
)

# =====================================================================================
# PART 1.4  CANONICAL LINE ITEMS
# Line items are identified semantically (statement + line-item name + financial year).
# No cell reference such as B12 or C17 appears anywhere in this application.
# =====================================================================================
PNL_ROWS: List[str] = [
    "Revenue",
    "Other Income",
    "Cost of Goods Sold",
    "Employee Cost",
    "Other Operating Expenses",
    "EBITDA",
    "Depreciation & Amortisation",
    "EBIT",
    "Finance Cost",
    "PBT",
    "Tax Expense",
    "PAT",
]

BS_ASSETS: List[str] = [
    "Property, Plant and Equipment",
    "Intangible Assets",
    "Investments",
    "Inventory",
    "Trade Receivables",
    "Other Current Assets",
    "Cash and Cash Equivalents",
]

BS_EQUITY: List[str] = ["Share Capital", "Retained Earnings", "Other Reserves"]

BS_LIABS: List[str] = [
    "Borrowings",
    "Lease Liabilities",
    "Deferred Tax Liability",
    "Trade Payables",
    "Other Current Liabilities",
    "Provisions",
    "Current Tax Payable",
    "Opening Reconciliation Item",
]

BS_SUBTOTALS: List[str] = [
    "Total Assets",
    "Total Equity",
    "Total Liabilities",
    "Total Equity and Liabilities",
    "Balance Check",
]

BS_ROWS: List[str] = (
    BS_ASSETS
    + ["Total Assets"]
    + BS_EQUITY
    + ["Total Equity"]
    + BS_LIABS
    + ["Total Liabilities", "Total Equity and Liabilities", "Balance Check"]
)

CF_ROWS: List[str] = [
    "PAT",
    "Depreciation & Amortisation",
    "Change in Working Capital",
    "Other Non-Cash Movements",
    "Cash Flow from Operating Activities",
    "Capital Expenditure",
    "Proceeds from Disposals",
    "Purchase of Investments",
    "Cash Flow from Investing Activities",
    "New Borrowings",
    "Repayment of Borrowings",
    "Lease Principal Repayment",
    "Dividends Paid",
    "Cash Flow from Financing Activities",
    "Net Change in Cash",
    "Opening Cash",
    "Closing Cash",
]

EQUITY_ROWS: List[str] = [
    "Opening Retained Earnings",
    "PAT",
    "Dividends",
    "Other Comprehensive Income",
    "Closing Retained Earnings",
    "Share Capital",
    "Other Reserves",
    "Closing Total Equity",
]

# Items whose economic sign is a cost. Source files may show these as negatives;
# internally they are always stored as positive magnitudes and subtracted explicitly.
COST_ITEMS = {
    "Cost of Goods Sold",
    "Employee Cost",
    "Other Operating Expenses",
    "Depreciation & Amortisation",
    "Finance Cost",
    "Tax Expense",
}

# Minimum line items required before a forecast is considered safe to build.
REQUIRED_HIST: Dict[str, List[str]] = {
    "P&L": ["Revenue", "Cost of Goods Sold", "Employee Cost", "PAT"],
    "Balance Sheet": [
        "Property, Plant and Equipment",
        "Trade Receivables",
        "Inventory",
        "Trade Payables",
        "Cash and Cash Equivalents",
        "Borrowings",
        "Share Capital",
        "Retained Earnings",
    ],
    "Cash Flow": [
        "Cash Flow from Operating Activities",
        "Cash Flow from Investing Activities",
        "Cash Flow from Financing Activities",
        "Closing Cash",
    ],
}

# Short engine keys -> canonical balance sheet line items (used for opening balances).
BS_MAP_KEYS: Dict[str, str] = {
    "PPE": "Property, Plant and Equipment",
    "Intangibles": "Intangible Assets",
    "Investments": "Investments",
    "Inventory": "Inventory",
    "Receivables": "Trade Receivables",
    "OCA": "Other Current Assets",
    "Cash": "Cash and Cash Equivalents",
    "ShareCapital": "Share Capital",
    "RE": "Retained Earnings",
    "OtherReserves": "Other Reserves",
    "Borrowings": "Borrowings",
    "Lease": "Lease Liabilities",
    "DTL": "Deferred Tax Liability",
    "Payables": "Trade Payables",
    "OCL": "Other Current Liabilities",
    "Provisions": "Provisions",
    "TaxPayable": "Current Tax Payable",
}

# =====================================================================================
# PART 1.5  ASSUMPTION SPECIFICATIONS
# Every assumption carries a plain-English statement of what it drives, so the model
# is self-documenting and no line item is left without an explicit driver.
# =====================================================================================
@dataclass(frozen=True)
class ParamSpec:
    key: str
    label: str
    kind: str            # 'percent' | 'days' | 'amount'
    group: str
    driver: str
    trend_capable: bool = False
    lo: float = -1e9
    hi: float = 1e9

    @property
    def suffix(self) -> str:
        return {"percent": " (%)", "days": " (days)", "amount": " (Rs lakh)"}[self.kind]

    @property
    def editor_label(self) -> str:
        return self.label + self.suffix

    def to_display(self, value: float) -> float:
        """Internal value -> value shown in the editor."""
        return value * 100.0 if self.kind == "percent" else value

    def from_display(self, value: float) -> float:
        """Value typed in the editor -> internal value."""
        return value / 100.0 if self.kind == "percent" else value

    def clamp(self, value: float) -> float:
        return float(min(max(value, self.lo), self.hi))

    def decimals(self) -> int:
        return 1 if self.kind == "days" else (2 if self.kind == "percent" else 0)


PARAM_SPECS: List[ParamSpec] = [
    # --- Revenue and margins -----------------------------------------------------------
    ParamSpec("revenue_growth", "Revenue growth", "percent", "Revenue & Margins",
              "Drives revenue, and therefore every cost, working capital and capex line.",
              True, -0.90, 3.00),
    ParamSpec("other_income_pct", "Other income / Revenue", "percent",
              "Revenue & Margins", "Drives other income, and so PBT and PAT.",
              True, 0.0, 0.50),
    ParamSpec("cogs_pct", "COGS / Revenue", "percent", "Revenue & Margins",
              "Drives cost of goods sold, and thereby inventory and payables.",
              True, 0.0, 0.95),
    ParamSpec("employee_pct", "Employee cost / Revenue", "percent", "Revenue & Margins",
              "Drives employee cost and hence EBITDA.", True, 0.0, 0.95),
    ParamSpec("other_opex_pct", "Other opex / Revenue", "percent", "Revenue & Margins",
              "Drives other operating expenses and hence EBITDA.", True, 0.0, 0.95),
    # --- Capex and depreciation --------------------------------------------------------
    ParamSpec("capex_pct", "Capex / Revenue", "percent", "Capex & Depreciation",
              "Drives PPE additions, investing cash outflow and future depreciation.",
              True, 0.0, 0.60),
    ParamSpec("dep_rate", "D&A / Opening PPE", "percent", "Capex & Depreciation",
              "Depreciation rate used by the PPE schedule (rate-based methods).",
              True, 0.0, 0.60),
    ParamSpec("disposal_pct", "Disposals / Opening PPE", "percent",
              "Capex & Depreciation",
              "Drives PPE disposals at book value and the related sale proceeds.",
              False, 0.0, 0.50),
    ParamSpec("amort_rate", "Amortisation / Opening intangibles", "percent",
              "Capex & Depreciation",
              "Drives amortisation of intangible assets within total D&A.",
              False, 0.0, 0.60),
    ParamSpec("investment_pct", "Investment purchases / Revenue", "percent",
              "Capex & Depreciation",
              "Drives purchases of investments shown in investing cash flow.",
              False, 0.0, 0.50),
    # --- Working capital ---------------------------------------------------------------
    ParamSpec("receivable_days", "Receivable days", "days", "Working Capital",
              "Receivables = Revenue x days / 365. Drives CFO and closing cash.",
              True, 0.0, 365.0),
    ParamSpec("inventory_days", "Inventory days", "days", "Working Capital",
              "Inventory = COGS x days / 365. Drives CFO and closing cash.",
              True, 0.0, 365.0),
    ParamSpec("payable_days", "Payable days", "days", "Working Capital",
              "Payables = COGS x days / 365. Drives CFO and closing cash.",
              True, 0.0, 365.0),
    ParamSpec("oca_pct", "Other current assets / Revenue", "percent",
              "Working Capital", "Drives other current assets and the CFO movement.",
              True, 0.0, 0.60),
    ParamSpec("ocl_pct", "Other current liabilities / Revenue", "percent",
              "Working Capital",
              "Drives other current liabilities and the CFO movement.", True, 0.0, 0.60),
    ParamSpec("provisions_pct", "Provisions / Revenue", "percent", "Working Capital",
              "Drives provisions; the year-on-year movement is added back in CFO.",
              True, 0.0, 0.40),
    # --- Financing, tax and distributions ----------------------------------------------
    ParamSpec("interest_rate", "Interest rate on borrowings", "percent",
              "Financing, Tax & Dividend",
              "Applied to average borrowings to derive finance cost.", True, 0.0, 0.50),
    ParamSpec("lease_rate", "Lease interest rate", "percent",
              "Financing, Tax & Dividend",
              "Applied to opening lease liabilities within finance cost.",
              False, 0.0, 0.50),
    ParamSpec("debt_repay_pct", "Scheduled repayment / Opening debt", "percent",
              "Financing, Tax & Dividend",
              "Contractual amortisation of term debt in the debt schedule.",
              False, 0.0, 1.00),
    ParamSpec("lease_repay_pct", "Lease repayment / Opening lease", "percent",
              "Financing, Tax & Dividend",
              "Lease principal repaid, shown in financing cash flow.", False, 0.0, 1.00),
    ParamSpec("new_borrowing", "Planned new borrowing", "amount",
              "Financing, Tax & Dividend",
              "Discretionary drawdown, in addition to any automatic funding plug.",
              False, 0.0, 1e7),
    ParamSpec("tax_rate", "Tax rate", "percent", "Financing, Tax & Dividend",
              "Applied to PBT to derive the tax expense.", True, 0.0, 0.60),
    ParamSpec("tax_payable_pct", "Closing tax payable / Tax expense", "percent",
              "Financing, Tax & Dividend",
              "Tax paid = opening payable + tax expense - closing payable.",
              True, 0.0, 1.00),
    ParamSpec("dividend_payout", "Dividend payout (% of PAT)", "percent",
              "Financing, Tax & Dividend",
              "Drives dividends, retained earnings and financing cash flow.",
              True, 0.0, 1.00),
]

PARAMS: Dict[str, ParamSpec] = {p.key: p for p in PARAM_SPECS}
PARAM_KEYS: List[str] = [p.key for p in PARAM_SPECS]
PARAM_GROUPS: List[str] = list(dict.fromkeys(p.group for p in PARAM_SPECS))

# Methodology options offered per assumption row.
FORECAST_METHODS: Tuple[str, ...] = (
    "Manual",
    "Historical average",
    "Historical CAGR",
    "Linear trend",
)

DEPRECIATION_METHODS: Tuple[str, ...] = (
    "Rate on opening balance",
    "Rate on average balance",
    "Straight line on useful life",
)

# Illustrative starting assumptions for the five forecast years, as specified.
# The user can edit every one of these in the interface.
DEFAULT_ASSUMPTIONS: Dict[str, List[float]] = {
    "revenue_growth":   [0.12, 0.11, 0.10, 0.09, 0.08],
    "other_income_pct": [0.010, 0.010, 0.010, 0.010, 0.010],
    "cogs_pct":         [0.30, 0.30, 0.29, 0.29, 0.28],
    "employee_pct":     [0.33, 0.32, 0.32, 0.31, 0.31],
    "other_opex_pct":   [0.12, 0.12, 0.11, 0.11, 0.11],
    "capex_pct":        [0.08, 0.08, 0.07, 0.07, 0.07],
    "dep_rate":         [0.10, 0.10, 0.09, 0.09, 0.09],
    "disposal_pct":     [0.01, 0.01, 0.01, 0.01, 0.01],
    "amort_rate":       [0.10, 0.10, 0.10, 0.10, 0.10],
    "investment_pct":   [0.00, 0.00, 0.00, 0.00, 0.00],
    "receivable_days":  [55.0, 55.0, 52.0, 50.0, 50.0],
    "inventory_days":   [25.0, 25.0, 24.0, 23.0, 23.0],
    "payable_days":     [45.0, 45.0, 45.0, 45.0, 45.0],
    "oca_pct":          [0.030, 0.030, 0.030, 0.030, 0.030],
    "ocl_pct":          [0.030, 0.030, 0.030, 0.030, 0.030],
    "provisions_pct":   [0.010, 0.010, 0.010, 0.010, 0.010],
    "interest_rate":    [0.09, 0.09, 0.09, 0.09, 0.09],
    "lease_rate":       [0.08, 0.08, 0.08, 0.08, 0.08],
    "debt_repay_pct":   [0.10, 0.10, 0.10, 0.10, 0.10],
    "lease_repay_pct":  [0.15, 0.15, 0.15, 0.15, 0.15],
    "new_borrowing":    [0.0, 0.0, 0.0, 0.0, 0.0],
    "tax_rate":         [0.25, 0.25, 0.25, 0.25, 0.25],
    "tax_payable_pct":  [0.25, 0.25, 0.25, 0.25, 0.25],
    "dividend_payout":  [0.10, 0.10, 0.10, 0.10, 0.10],
}

FORECAST_HORIZON = 5


# =====================================================================================
# PART 1.6  MODEL SETTINGS AND ASSUMPTION SET
# =====================================================================================
@dataclass
class ModelSettings:
    """Global model switches that are not year-specific."""

    minimum_cash: float = 500.0          # Rs lakh floor enforced by the funding plug
    cash_sweep: bool = True              # funding plug ON/OFF
    depreciation_method: str = "Rate on opening balance"
    useful_life: float = 10.0            # years, used by the straight-line method
    tax_credit_on_loss: bool = False     # if False, a loss produces nil tax, not a credit
    reconcile_opening_imbalance: bool = True  # park any source-data residue explicitly

    def copy(self) -> "ModelSettings":
        return copy.deepcopy(self)


@dataclass
class AssumptionSet:
    """All forecast assumptions for one scenario, keyed by parameter and year."""

    years: List[int]
    values: Dict[str, Dict[int, float]]
    methods: Dict[str, str] = field(default_factory=dict)
    settings: ModelSettings = field(default_factory=ModelSettings)
    scenario: str = "Base Case"

    # ---- access ----------------------------------------------------------------------
    def get(self, key: str, year: int) -> float:
        try:
            return float(self.values[key][year])
        except (KeyError, TypeError, ValueError):
            series = DEFAULT_ASSUMPTIONS.get(key, [0.0])
            return float(series[0])

    def set(self, key: str, year: int, value: float) -> None:
        spec = PARAMS.get(key)
        clean = spec.clamp(float(value)) if spec else float(value)
        self.values.setdefault(key, {})[year] = clean

    def method(self, key: str) -> str:
        return self.methods.get(key, "Manual")

    def set_method(self, key: str, method: str) -> None:
        self.methods[key] = method

    def copy(self) -> "AssumptionSet":
        return AssumptionSet(
            years=list(self.years),
            values=copy.deepcopy(self.values),
            methods=dict(self.methods),
            settings=self.settings.copy(),
            scenario=self.scenario,
        )

    # ---- presentation ----------------------------------------------------------------
    def to_frame(self) -> pd.DataFrame:
        """Assumption table for display and Excel export, in display units."""
        columns = {
            f"FY{str(year)[-2:]}": [
                PARAMS[key].to_display(self.get(key, year)) for key in PARAM_KEYS
            ]
            for year in self.years
        }
        frame = pd.DataFrame(columns, index=[PARAMS[k].editor_label for k in PARAM_KEYS])
        frame.insert(0, "Methodology", [self.method(k) for k in PARAM_KEYS])
        frame.insert(1, "Calculation driver", [PARAMS[k].driver for k in PARAM_KEYS])
        return frame

    def settings_frame(self) -> pd.DataFrame:
        s = self.settings
        rows = [
            ("Scenario", self.scenario),
            ("Forecast years", ", ".join(f"FY{y}" for y in self.years)),
            ("Minimum cash balance (Rs lakh)", f"{s.minimum_cash:,.0f}"),
            ("Cash sweep / funding plug", "ON" if s.cash_sweep else "OFF"),
            ("Depreciation methodology", s.depreciation_method),
            ("Assumed useful life (years)", f"{s.useful_life:,.1f}"),
            ("Tax credit recognised on losses", "Yes" if s.tax_credit_on_loss else "No"),
            ("Park opening-balance residue explicitly",
             "Yes" if s.reconcile_opening_imbalance else "No"),
        ]
        return pd.DataFrame(rows, columns=["Model setting", "Value"])

    def signature(self) -> Tuple:
        """Hashable fingerprint. Any change here forces a full model recalculation."""
        return (
            tuple(self.years),
            tuple(sorted((k, tuple(sorted(v.items()))) for k, v in self.values.items())),
            tuple(sorted(self.methods.items())),
            (
                self.settings.minimum_cash,
                self.settings.cash_sweep,
                self.settings.depreciation_method,
                self.settings.useful_life,
                self.settings.tax_credit_on_loss,
                self.settings.reconcile_opening_imbalance,
            ),
        )


def forecast_years(base_year: int, horizon: int = FORECAST_HORIZON) -> List[int]:
    """FY2026 base year -> [2027, 2028, 2029, 2030, 2031]."""
    return [int(base_year) + i for i in range(1, horizon + 1)]


def default_assumptions(years: List[int], scenario: str = "Base Case") -> AssumptionSet:
    """Build the illustrative starting assumption set for the given forecast years."""
    values: Dict[str, Dict[int, float]] = {}
    for key in PARAM_KEYS:
        series = DEFAULT_ASSUMPTIONS.get(key, [0.0])
        values[key] = {}
        for index, year in enumerate(years):
            values[key][int(year)] = float(series[min(index, len(series) - 1)])
    return AssumptionSet(
        years=[int(y) for y in years],
        values=values,
        methods={key: "Manual" for key in PARAM_KEYS},
        settings=ModelSettings(),
        scenario=scenario,
    )


# =====================================================================================
# PART 1.7  SCENARIOS
# Upside and downside are expressed as explicit deltas to the base assumptions, so the
# relationship between the three cases is transparent and auditable.
# =====================================================================================
SCENARIOS: Tuple[str, ...] = ("Base Case", "Upside Case", "Downside Case", "Custom")

SCENARIO_DELTAS: Dict[str, Dict[str, float]] = {
    "Base Case": {},
    "Upside Case": {
        "revenue_growth": +0.030,
        "cogs_pct": -0.015,
        "employee_pct": -0.010,
        "other_opex_pct": -0.005,
        "receivable_days": -3.0,
        "inventory_days": -2.0,
        "payable_days": +2.0,
    },
    "Downside Case": {
        "revenue_growth": -0.040,
        "cogs_pct": +0.020,
        "employee_pct": +0.010,
        "other_opex_pct": +0.010,
        "receivable_days": +6.0,
        "inventory_days": +3.0,
        "payable_days": -3.0,
        "interest_rate": +0.010,
    },
}

SCENARIO_NOTES: Dict[str, str] = {
    "Base Case": "Illustrative management plan using the default assumptions.",
    "Upside Case": "Higher revenue growth, improved margins and tighter working capital.",
    "Downside Case": "Lower growth, margin compression, slower collections, dearer debt.",
    "Custom": "User-defined assumptions, edited directly in the assumptions grid.",
}


def build_scenario(years: List[int], scenario: str) -> AssumptionSet:
    """Base assumptions shifted by the scenario deltas, clamped to sensible limits."""
    assumptions = default_assumptions(years, scenario)
    for key, delta in SCENARIO_DELTAS.get(scenario, {}).items():
        for year in years:
            assumptions.set(key, year, assumptions.get(key, year) + delta)
    return assumptions


# =====================================================================================
# PART 1.8  HISTORICAL MODEL CONTAINER
# =====================================================================================
@dataclass
class HistoricalModel:
    """Standardised historical financials. Every value is in INR lakh."""

    company: str
    years: List[int]
    pnl: pd.DataFrame                       # index = line item, columns = financial year
    balance_sheet: pd.DataFrame
    cash_flow: pd.DataFrame
    schedules: pd.DataFrame = field(default_factory=pd.DataFrame)
    equity: pd.DataFrame = field(default_factory=pd.DataFrame)
    tidy: pd.DataFrame = field(default_factory=pd.DataFrame)
    unit: str = BASE_UNIT
    messages: List[Tuple[str, str]] = field(default_factory=list)
    source_files: List[str] = field(default_factory=list)
    edit_log: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def base_year(self) -> int:
        """The most recent actual year; the forecast is built forward from here."""
        return int(self.years[-1])

    def frame(self, statement: str) -> pd.DataFrame:
        return {
            "P&L": self.pnl,
            "Balance Sheet": self.balance_sheet,
            "Cash Flow": self.cash_flow,
            "Schedules": self.schedules,
            "Equity": self.equity,
        }.get(statement, pd.DataFrame())

    def value(self, statement: str, item: str, year: int, default: float = 0.0) -> float:
        """Safe lookup by statement, line item and financial year."""
        data = self.frame(statement)
        if data is None or data.empty:
            return default
        if item not in data.index or int(year) not in list(data.columns):
            return default
        raw = data.loc[item, int(year)]
        if isinstance(raw, pd.Series):
            raw = raw.iloc[0]
        return default if pd.isna(raw) else float(raw)

    def series(self, statement: str, item: str) -> pd.Series:
        """Full historical series for one line item, indexed by year."""
        return pd.Series(
            {int(y): self.value(statement, item, int(y)) for y in self.years},
            dtype=float,
        )

    def opening_balances(self) -> Dict[str, float]:
        """Base-year closing balance sheet, which opens the forecast."""
        year = self.base_year
        return {
            key: self.value("Balance Sheet", item, year)
            for key, item in BS_MAP_KEYS.items()
        }

    def has(self, statement: str, item: str) -> bool:
        data = self.frame(statement)
        return bool(data is not None and not data.empty and item in data.index)

    def record_count(self) -> int:
        return 0 if self.tidy is None or self.tidy.empty else int(len(self.tidy))

    def set_value(self, statement: str, item: str, year: int, value: float,
                  note: str = "") -> None:
        """Manually overwrite one cell of a standardised statement, keeping an
        audit trail of every such change."""
        frame = self.frame(statement)
        if frame is None or frame.empty:
            return
        if item not in frame.index:
            frame.loc[item] = 0.0
        if int(year) not in list(frame.columns):
            frame[int(year)] = 0.0
        frame.loc[item, int(year)] = float(value)
        self.edit_log.append({
            "when": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "statement": statement,
            "line_item": item,
            "financial_year": int(year),
            "value": float(value),
            "note": note,
        })

    def recompute_subtotals(self) -> None:
        """Recalculate every derived total after a manual edit, so the three
        statements stay internally consistent without the user having to touch a
        subtotal row."""
        years = [int(y) for y in self.years]

        pnl = self.pnl
        for year in years:
            def g(item: str) -> float:
                return float(pnl.loc[item, year]) if item in pnl.index else 0.0
            ebitda = (g("Revenue") - g("Cost of Goods Sold") - g("Employee Cost")
                      - g("Other Operating Expenses"))
            ebit = ebitda - g("Depreciation & Amortisation")
            pbt = ebit + g("Other Income") - g("Finance Cost")
            pat = pbt - g("Tax Expense")
            pnl.loc["EBITDA", year] = ebitda
            pnl.loc["EBIT", year] = ebit
            pnl.loc["PBT", year] = pbt
            pnl.loc["PAT", year] = pat
        self.pnl = _reorder(pnl.fillna(0.0), PNL_ROWS)

        self.balance_sheet = complete_balance_sheet(self.balance_sheet, years)

        cf = self.cash_flow
        for position, year in enumerate(years):
            if position > 0 and "Closing Cash" in cf.index:
                cf.loc["Opening Cash", year] = cf.loc["Closing Cash",
                                                      years[position - 1]]

            def gc(item: str) -> float:
                return float(cf.loc[item, year]) if item in cf.index else 0.0
            net_change = (gc("Cash Flow from Operating Activities")
                          + gc("Cash Flow from Investing Activities")
                          + gc("Cash Flow from Financing Activities"))
            cf.loc["Net Change in Cash", year] = net_change
            if "Opening Cash" in cf.index:
                cf.loc["Closing Cash", year] = gc("Opening Cash") + net_change
        self.cash_flow = _reorder(cf.fillna(0.0), CF_ROWS)


# ---------------------------------------------------------------------------------
# END OF PART 1.
# The file is intentionally not runnable as an application yet - it defines the data
# model only. Paste PART 2 (tolerant Excel parser and historical analysis engine)
# directly beneath this line.
# ---------------------------------------------------------------------------------
# =====================================================================================
# PART 2.1  SHEET AND LABEL RECOGNITION
# Sheets and line items are identified semantically. Column positions may move, labels
# may be worded differently, and the workbook may carry comparative columns.
# =====================================================================================
SCHEDULE_ROWS: List[str] = [
    "Opening PPE",
    "Capex",
    "Disposals",
    "Depreciation Charge",
    "Closing PPE",
    "Opening Debt",
    "New Borrowings",
    "Repayment of Borrowings",
    "Closing Debt",
    "Opening Tax Payable",
    "Tax Expense",
    "Tax Paid",
    "Closing Tax Payable",
]

SHEET_TOKENS: List[Tuple[str, str]] = [
    ("read me", "Read Me"),
    ("readme", "Read Me"),
    ("cover", "Read Me"),
    ("basis of preparation", "Read Me"),
    ("profit and loss", "P&L"),
    ("profit loss", "P&L"),
    ("income statement", "P&L"),
    ("statement of profit", "P&L"),
    ("p and l", "P&L"),
    ("pnl", "P&L"),
    ("p l", "P&L"),
    ("balance sheet", "Balance Sheet"),
    ("financial position", "Balance Sheet"),
    ("statement of assets", "Balance Sheet"),
    ("cash flow", "Cash Flow"),
    ("cashflow", "Cash Flow"),
    ("schedule", "Schedules"),
    ("notes", "Schedules"),
    ("supporting", "Schedules"),
    ("equity", "Equity"),
    ("reserves", "Equity"),
]

SHEET_TOKENS_SHORT: List[Tuple[str, str]] = [
    ("bs", "Balance Sheet"),
    ("cf", "Cash Flow"),
    ("pl", "P&L"),
]

SYNONYMS: Dict[str, Dict[str, List[str]]] = {
    "P&L": {
        "Revenue": [
            "revenue from operations", "revenue", "net sales", "sales", "turnover",
            "income from operations", "operating revenue", "total operating income",
            "sale of products and services", "net revenue",
        ],
        "Other Income": [
            "other income", "non operating income", "other revenue",
            "interest and other income",
        ],
        "Cost of Goods Sold": [
            "cost of goods sold", "cogs", "cost of materials consumed",
            "cost of material consumed", "cost of sales", "material cost",
            "direct cost", "direct costs", "purchases of stock in trade",
            "cost of services delivered", "cost of revenue",
        ],
        "Employee Cost": [
            "employee benefit expenses", "employee benefits expense", "employee cost",
            "employee costs", "personnel cost", "personnel expenses", "staff cost",
            "salaries and wages", "manpower cost", "people cost",
        ],
        "Other Operating Expenses": [
            "other expenses", "other operating expenses", "other operating cost",
            "administrative expenses", "other overheads", "overheads",
            "selling and administrative expenses", "operating and other expenses",
        ],
        "EBITDA": [
            "ebitda", "operating profit", "operating ebitda",
            "earnings before interest tax depreciation and amortisation",
            "operating profit before depreciation",
        ],
        "Depreciation & Amortisation": [
            "depreciation and amortisation", "depreciation and amortization",
            "depreciation amortisation expense", "depreciation expense", "depreciation",
            "amortisation", "amortization", "d and a", "depreciation charge",
        ],
        "EBIT": [
            "ebit", "operating profit after depreciation",
            "profit before interest and tax", "earnings before interest and tax",
        ],
        "Finance Cost": [
            "finance cost", "finance costs", "interest expense", "interest cost",
            "borrowing cost", "interest and finance charges", "interest",
        ],
        "PBT": [
            "profit before tax", "pbt", "profit before taxation",
            "profit loss before tax", "profit before income tax",
        ],
        "Tax Expense": [
            "tax expense", "total tax expense", "income tax expense", "income tax",
            "provision for tax", "provision for taxation", "current tax", "tax",
        ],
        "PAT": [
            "profit after tax", "pat", "profit for the year", "net profit",
            "net income", "profit loss for the period", "profit for the period",
        ],
    },
    "Balance Sheet": {
        "Property, Plant and Equipment": [
            "property plant and equipment", "property plant equipment", "ppe",
            "fixed assets", "tangible assets", "net block", "tangible fixed assets",
        ],
        "Intangible Assets": [
            "intangible assets", "intangibles", "other intangible assets", "goodwill",
            "computer software",
        ],
        "Investments": [
            "investments", "non current investments", "long term investments",
            "financial assets investments", "current investments",
        ],
        "Inventory": [
            "inventories", "inventory", "stock in trade", "closing stock", "stocks",
        ],
        "Trade Receivables": [
            "trade receivables", "debtors", "sundry debtors", "accounts receivable",
            "receivables", "trade and other receivables",
        ],
        "Other Current Assets": [
            "other current assets", "loans and advances", "prepaid expenses",
            "other financial assets", "short term loans and advances",
            "other assets",
        ],
        "Cash and Cash Equivalents": [
            "cash and cash equivalents", "cash and bank", "cash and bank balances",
            "bank balances", "cash", "cash at bank and in hand",
        ],
        "Share Capital": [
            "share capital", "equity share capital", "paid up share capital",
            "issued share capital",
        ],
        "Retained Earnings": [
            "retained earnings", "reserves and surplus",
            "surplus in the statement of profit and loss", "accumulated profits",
            "profit and loss account", "accumulated surplus",
        ],
        "Other Reserves": [
            "other reserves", "other equity", "securities premium", "general reserve",
            "capital reserve", "other components of equity",
        ],
        "Borrowings": [
            "borrowings", "long term borrowings", "short term borrowings", "term loan",
            "term loans", "bank borrowings", "loans from banks", "debt",
            "working capital loan",
        ],
        "Lease Liabilities": [
            "lease liabilities", "lease liability", "finance lease obligations",
            "right of use lease liability",
        ],
        "Deferred Tax Liability": [
            "deferred tax liability", "deferred tax liabilities", "deferred tax net",
            "deferred tax",
        ],
        "Trade Payables": [
            "trade payables", "creditors", "sundry creditors", "accounts payable",
            "payables", "trade and other payables",
        ],
        "Other Current Liabilities": [
            "other current liabilities", "other financial liabilities",
            "other liabilities", "statutory dues payable",
        ],
        "Provisions": [
            "provisions", "short term provisions", "long term provisions",
            "employee provisions", "provision for employee benefits",
        ],
        "Current Tax Payable": [
            "current tax payable", "tax payable", "income tax payable",
            "provision for income tax", "current tax liabilities",
        ],
    },
    "Cash Flow": {
        "PAT": [
            "profit after tax", "profit for the year", "net profit", "pat",
        ],
        "Depreciation & Amortisation": [
            "depreciation and amortisation", "depreciation and amortization",
            "depreciation", "amortisation",
        ],
        "Change in Working Capital": [
            "changes in working capital", "working capital changes",
            "movement in working capital", "change in working capital",
            "net change in working capital",
        ],
        "Other Non-Cash Movements": [
            "other non cash items", "other non cash movements",
            "other adjustments", "non cash adjustments",
        ],
        "Cash Flow from Operating Activities": [
            "net cash from operating activities", "cash flow from operating activities",
            "net cash generated from operating activities",
            "net cash used in operating activities", "cash generated from operations",
            "cfo", "operating activities",
        ],
        "Capital Expenditure": [
            "purchase of property plant and equipment", "capital expenditure", "capex",
            "additions to fixed assets", "purchase of fixed assets",
            "acquisition of property plant and equipment",
        ],
        "Proceeds from Disposals": [
            "proceeds from sale of fixed assets", "proceeds from disposals",
            "sale of property plant and equipment", "proceeds from sale of assets",
        ],
        "Purchase of Investments": [
            "purchase of investments", "investments purchased",
            "investment in mutual funds",
        ],
        "Cash Flow from Investing Activities": [
            "net cash used in investing activities",
            "cash flow from investing activities",
            "net cash from investing activities", "cfi", "investing activities",
        ],
        "New Borrowings": [
            "proceeds from borrowings", "new borrowings",
            "proceeds from long term borrowings", "debt drawdown",
            "proceeds from issue of debt",
        ],
        "Repayment of Borrowings": [
            "repayment of borrowings", "repayment of long term borrowings",
            "debt repayment", "repayment of term loans",
        ],
        "Lease Principal Repayment": [
            "payment of lease liabilities", "lease principal repayment",
            "repayment of lease liabilities",
        ],
        "Dividends Paid": [
            "dividend paid", "dividends paid", "dividend including tax paid",
            "payment of dividend",
        ],
        "Cash Flow from Financing Activities": [
            "net cash used in financing activities",
            "cash flow from financing activities",
            "net cash from financing activities", "cff", "financing activities",
        ],
        "Net Change in Cash": [
            "net increase decrease in cash and cash equivalents",
            "net change in cash", "net increase in cash", "net decrease in cash",
        ],
        "Opening Cash": [
            "cash and cash equivalents at the beginning of the year", "opening cash",
            "opening cash and cash equivalents", "cash at the beginning",
        ],
        "Closing Cash": [
            "cash and cash equivalents at the end of the year", "closing cash",
            "closing cash and cash equivalents", "cash at the end",
        ],
    },
    "Equity": {
        "Opening Retained Earnings": [
            "opening retained earnings", "balance at the beginning of the year",
            "opening balance", "retained earnings opening",
        ],
        "PAT": [
            "profit for the year", "profit after tax", "net profit", "pat",
            "total comprehensive income for the year",
        ],
        "Dividends": [
            "dividends", "dividend paid", "dividend declared", "dividend distribution",
        ],
        "Other Comprehensive Income": [
            "other comprehensive income", "oci", "remeasurement of defined benefit plans",
        ],
        "Closing Retained Earnings": [
            "closing retained earnings", "balance at the end of the year",
            "closing balance", "retained earnings closing",
        ],
        "Share Capital": ["share capital", "equity share capital"],
        "Other Reserves": ["other reserves", "securities premium", "general reserve"],
    },
    "Schedules": {
        "Opening PPE": [
            "opening ppe", "opening gross block", "opening balance ppe",
            "opening property plant and equipment", "opening net block",
        ],
        "Capex": ["additions", "capex", "capital expenditure", "additions during the year"],
        "Disposals": ["disposals", "deletions", "disposals during the year", "sales"],
        "Depreciation Charge": [
            "depreciation charge", "depreciation for the year", "depreciation",
        ],
        "Closing PPE": [
            "closing ppe", "closing net block", "closing balance ppe",
            "closing property plant and equipment",
        ],
        "Opening Debt": ["opening debt", "opening borrowings", "opening balance debt"],
        "New Borrowings": ["new borrowings", "drawdown", "additions to borrowings"],
        "Repayment of Borrowings": ["repayment", "repayment of borrowings", "repayments"],
        "Closing Debt": ["closing debt", "closing borrowings", "closing balance debt"],
        "Opening Tax Payable": ["opening tax payable", "opening provision for tax"],
        "Tax Expense": ["tax expense", "current tax", "provision for tax"],
        "Tax Paid": ["tax paid", "taxes paid", "advance tax paid"],
        "Closing Tax Payable": ["closing tax payable", "closing provision for tax"],
    },
}

ORDER_BY_STATEMENT: Dict[str, List[str]] = {
    "P&L": PNL_ROWS,
    "Balance Sheet": BS_ROWS,
    "Cash Flow": CF_ROWS,
    "Equity": EQUITY_ROWS,
    "Schedules": SCHEDULE_ROWS,
}

# Subtotal and heading labels that must never be captured as a data line item.
EXCLUDE_TOKENS: Tuple[str, ...] = (
    "total assets", "total equity and liabilities", "total liabilities",
    "total current assets", "total non current assets", "total current liabilities",
    "total non current liabilities", "total expenses", "total income", "total equity",
    "grand total", "particulars", "balance check", "assets", "liabilities",
    "equity and liabilities", "current assets", "non current assets",
    "current liabilities", "non current liabilities", "expenses", "income",
    "in lakh", "amount in", "figures in",
)

# Cash flow items normalised to a negative magnitude, so outflows always read negative.
CF_OUTFLOW_ITEMS = {
    "Capital Expenditure",
    "Purchase of Investments",
    "Repayment of Borrowings",
    "Lease Principal Repayment",
    "Dividends Paid",
}


def _norm(text: Any) -> str:
    """Aggressively normalise a label for comparison purposes."""
    value = str(text).lower().replace("&", " and ")
    value = re.sub(r"\(.*?\)", " ", value)
    value = re.sub(r"[^a-z0-9 ]", " ", value)
    value = re.sub(
        r"\b(the|of|for|from|in|on|at|during|year|rs|inr|lakh|lakhs|crore|crores|"
        r"note|notes|as|per|and|a)\b",
        " ",
        value,
    )
    return re.sub(r"\s+", " ", value).strip()


def statement_from_sheet(sheet_name: str) -> str:
    """Map a worksheet name onto a statement, tolerating abbreviations."""
    key = _norm(sheet_name)
    for token, statement in SHEET_TOKENS:
        if token in key:
            return statement
    for token, statement in SHEET_TOKENS_SHORT:
        if key == token or key.startswith(token + " ") or key.endswith(" " + token):
            return statement
    return "Other"


def match_line_item(label: str, statement: str) -> Optional[str]:
    """Map a raw label onto a canonical item: exact, then containment, then fuzzy."""
    norm = _norm(label)
    if not norm or len(norm) < 2:
        return None
    if norm in EXCLUDE_TOKENS:
        return None
    if any(norm == token for token in EXCLUDE_TOKENS):
        return None
    table = SYNONYMS.get(statement, {})
    if not table:
        return None

    # 1. exact match against a canonical name or any synonym
    for canon, alternatives in table.items():
        candidates = [_norm(canon)] + [_norm(a) for a in alternatives]
        if norm in candidates:
            return canon

    # 2. containment and fuzzy similarity, best score wins
    best_item: Optional[str] = None
    best_score = 0.0
    for canon, alternatives in table.items():
        for alternative in [canon] + list(alternatives):
            candidate = _norm(alternative)
            if not candidate:
                continue
            if candidate in norm or norm in candidate:
                shorter = min(len(candidate), len(norm))
                longer = max(len(candidate), len(norm), 1)
                score = 0.88 + 0.10 * (shorter / longer)
            else:
                score = difflib.SequenceMatcher(None, norm, candidate).ratio()
            if score > best_score:
                best_item, best_score = canon, score
    return best_item if best_score >= 0.86 else None


# =====================================================================================
# PART 2.2  YEAR, UNIT AND NUMBER RECOGNITION
# =====================================================================================
YEAR_PATTERNS: List[Tuple[re.Pattern, Any]] = [
    (re.compile(r"fy\s*(\d{4})"), lambda m: int(m.group(1))),
    (re.compile(r"fy\s*[-'\u2019]?\s*(\d{2})\b"), lambda m: 2000 + int(m.group(1))),
    (re.compile(r"(20\d{2})\s*[-/]\s*\d{2}\b"), lambda m: int(m.group(1)) + 1),
    (re.compile(r"\b(19|20)(\d{2})\b"), lambda m: int(m.group(1) + m.group(2))),
]


def extract_year(text: Any) -> Optional[int]:
    """Pull a financial year out of free text such as 'FY2026' or '2025-26'."""
    value = str(text).strip().lower()
    if not value:
        return None
    for pattern, converter in YEAR_PATTERNS:
        match = pattern.search(value)
        if match:
            try:
                year = int(converter(match))
            except Exception:
                continue
            if 1990 <= year <= 2100:
                return year
    return None


def _year_header(value: Any) -> Optional[int]:
    """Single clean predicate: does this cell look like a financial-year heading?"""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return int(value.year)
    if isinstance(value, (int, float, np.integer, np.floating)):
        number = float(value)
        if 1990.0 <= number <= 2100.0 and float(number).is_integer():
            return int(number)
        return None
    if isinstance(value, str):
        return extract_year(value)
    return None


def detect_unit(raw: pd.DataFrame, fallback: str = BASE_UNIT) -> str:
    """Read the reporting unit from any narrative text near the top of a sheet."""
    scan = raw.head(12).values.ravel() if not raw.empty else []
    blob = " ".join(str(v).lower() for v in scan if isinstance(v, str))
    mapping = [
        ("billion", "INR billion"),
        ("crore", "INR crore"),
        ("million", "INR million"),
        ("lakh", "INR lakh"),
        ("lac", "INR lakh"),
        ("thousand", "INR thousand"),
        ("'000", "INR thousand"),
    ]
    for token, unit in mapping:
        if token in blob:
            return unit
    return fallback


def unit_multiplier(unit: str) -> float:
    """Multiplier that converts the detected unit into the base unit (INR lakh)."""
    key = str(unit).lower()
    for token in ("billion", "crore", "million", "lakh", "lac", "thousand", "'000"):
        if token in key:
            return UNIT_TO_LAKH[token]
    return 1.0


def _to_number(value: Any) -> Optional[float]:
    """Parse a cell into a float, understanding commas, currency signs and brackets."""
    if value is None:
        return None
    if isinstance(value, (int, float, np.integer, np.floating)):
        return None if pd.isna(value) else float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text or text in {"-", "--", "nil", "NIL", "na", "NA", "N/A"}:
            return None
        text = text.replace(",", "").replace("\u20b9", "").replace("Rs.", "")
        text = text.replace("Rs", "").replace("INR", "").strip()
        negative = text.startswith("(") and text.endswith(")")
        text = text.strip("()").strip()
        if text.endswith("%"):
            return None
        try:
            number = float(text)
        except Exception:
            return None
        return -number if negative else number
    return None


def _looks_numeric(value: Any) -> bool:
    return _to_number(value) is not None


# =====================================================================================
# PART 2.3  WORKBOOK PARSER
# =====================================================================================
def parse_workbook(path: str) -> Tuple[pd.DataFrame, str, List[Tuple[str, str]]]:
    """Parse one Excel workbook into tidy records. Never uses a cell reference."""
    messages: List[Tuple[str, str]] = []
    records: List[dict] = []
    filename = os.path.basename(path)

    try:
        sheets = pd.read_excel(path, sheet_name=None, header=None, engine="openpyxl")
    except Exception as exc:
        return pd.DataFrame(), "", [("ERROR", f"{filename}: could not be opened ({exc}).")]

    if not sheets:
        return pd.DataFrame(), "", [("ERROR", f"{filename}: contains no worksheets.")]

    # ---- company name and workbook-level unit from the Read Me sheet -----------------
    company = ""
    workbook_unit = BASE_UNIT
    for sheet_name, raw in sheets.items():
        if statement_from_sheet(sheet_name) != "Read Me" or raw.empty:
            continue
        workbook_unit = detect_unit(raw, BASE_UNIT)
        for cell in raw.values.ravel():
            if not isinstance(cell, str):
                continue
            text = cell.strip()
            if re.search(r"(private limited|pvt\.?\s*ltd|limited|ltd\.?|llp|inc\.)",
                         text, re.IGNORECASE) and len(text) <= 120:
                if len(text) > len(company):
                    company = text
    if not company:
        stem = os.path.splitext(filename)[0]
        stem = re.sub(r"[_\-]+", " ", stem)
        stem = re.sub(r"(?i)financials?|statements?|fy\s*\d{2,4}", "", stem)
        company = re.sub(r"\s+", " ", stem).strip().title() or "Company"

    file_year = extract_year(filename)
    sheets_read = 0

    for sheet_name, raw in sheets.items():
        statement = statement_from_sheet(sheet_name)
        if statement in ("Read Me", "Other") or raw is None or raw.empty:
            continue
        if statement not in SYNONYMS:
            continue

        sheet_unit = detect_unit(raw, workbook_unit)
        multiplier = unit_multiplier(sheet_unit)

        # ---- header row = the row containing the most year-like headings -------------
        header_row: Optional[int] = None
        year_columns: Dict[int, int] = {}
        best_count = 0
        scan_depth = min(len(raw), 30)
        for row in range(scan_depth):
            found: Dict[int, int] = {}
            for col in range(raw.shape[1]):
                year = _year_header(raw.iat[row, col])
                if year is not None:
                    found[col] = year
            if len(found) > best_count:
                header_row, year_columns, best_count = row, dict(found), len(found)

        if header_row is None or not year_columns:
            messages.append((
                "WARNING",
                f"{filename} / {sheet_name}: no financial-year column headings were "
                f"recognised, so this sheet was skipped.",
            ))
            continue

        # ---- label column = first non-year column that is predominantly text --------
        label_col = None
        for col in range(raw.shape[1]):
            if col in year_columns:
                continue
            column = raw.iloc[header_row + 1:, col]
            text_cells = sum(1 for v in column if isinstance(v, str) and v.strip())
            if text_cells >= max(3, int(0.20 * max(len(column), 1))):
                label_col = col
                break
        if label_col is None:
            label_col = 0

        rows_captured = 0
        for row in range(header_row + 1, len(raw)):
            label = raw.iat[row, label_col]
            if not isinstance(label, str) or not label.strip():
                continue
            clean_label = label.strip()
            canonical = match_line_item(clean_label, statement)
            for col, year in year_columns.items():
                number = _to_number(raw.iat[row, col])
                if number is None:
                    continue
                value = float(number) * multiplier
                if canonical is None:
                    item = f"[Unmapped] {clean_label}"
                else:
                    item = canonical
                    if statement == "P&L" and item in COST_ITEMS:
                        value = abs(value)
                    elif statement == "Cash Flow" and item in CF_OUTFLOW_ITEMS:
                        value = -abs(value)
                records.append({
                    "company": company,
                    "financial_year": int(year),
                    "statement": statement,
                    "category": "Mapped" if canonical else "Unmapped",
                    "line_item": item,
                    "value": value,
                    "unit": BASE_UNIT,
                    "source_label": clean_label,
                    "source_sheet": str(sheet_name),
                    "source_file": filename,
                    "primary": 1 if (file_year is not None and year == file_year) else 0,
                })
                rows_captured += 1
        if rows_captured:
            sheets_read += 1

    tidy = pd.DataFrame(records)
    if tidy.empty:
        messages.append(("ERROR", f"{filename}: no financial data could be extracted."))
        return tidy, company, messages

    years_found = sorted(int(y) for y in tidy["financial_year"].unique())
    messages.append((
        "OK",
        f"{filename} loaded: {sheets_read} statement sheet(s), {len(tidy)} data points, "
        f"years {', '.join('FY' + str(y) for y in years_found)}, "
        f"unit read as {workbook_unit}.",
    ))
    return tidy, company, messages


# =====================================================================================
# PART 2.4  SUBTOTAL DERIVATION AND STATEMENT COMPLETION
# =====================================================================================
def _blank_frame(index: List[str], years: List[int]) -> pd.DataFrame:
    return pd.DataFrame(0.0, index=index, columns=[int(y) for y in years])


def _reorder(frame: pd.DataFrame, order: List[str]) -> pd.DataFrame:
    ordered = [item for item in order if item in frame.index]
    extra = [item for item in frame.index if item not in ordered]
    return frame.reindex(ordered + extra)


def derive_pnl_subtotals(pnl: pd.DataFrame, years: List[int]) -> pd.DataFrame:
    """Fill any subtotal the source file did not state explicitly."""
    index = list(dict.fromkeys(list(pnl.index) + PNL_ROWS))
    frame = pnl.reindex(index=index, columns=[int(y) for y in years]).astype(float)

    def get(item: str, year: int) -> float:
        raw = frame.loc[item, year]
        return 0.0 if pd.isna(raw) else float(raw)

    for year in [int(y) for y in years]:
        if pd.isna(frame.loc["EBITDA", year]):
            frame.loc["EBITDA", year] = (
                get("Revenue", year)
                - get("Cost of Goods Sold", year)
                - get("Employee Cost", year)
                - get("Other Operating Expenses", year)
            )
        if pd.isna(frame.loc["EBIT", year]):
            frame.loc["EBIT", year] = (
                get("EBITDA", year) - get("Depreciation & Amortisation", year)
            )
        if pd.isna(frame.loc["PBT", year]):
            frame.loc["PBT", year] = (
                get("EBIT", year) + get("Other Income", year) - get("Finance Cost", year)
            )
        pbt_known = not pd.isna(frame.loc["PBT", year])
        pat_known = not pd.isna(frame.loc["PAT", year])
        tax_known = not pd.isna(frame.loc["Tax Expense", year])
        if pbt_known and tax_known and not pat_known:
            frame.loc["PAT", year] = get("PBT", year) - get("Tax Expense", year)
        elif pbt_known and pat_known and not tax_known:
            frame.loc["Tax Expense", year] = get("PBT", year) - get("PAT", year)

    return _reorder(frame.fillna(0.0), PNL_ROWS)


def complete_balance_sheet(bs: pd.DataFrame, years: List[int]) -> pd.DataFrame:
    """Add missing captions, then recompute every subtotal and the balance check."""
    base_items = [i for i in BS_ASSETS + BS_EQUITY + BS_LIABS]
    index = list(dict.fromkeys(list(bs.index) + base_items + BS_SUBTOTALS))
    frame = bs.reindex(index=index, columns=[int(y) for y in years]).astype(float)
    frame = frame.fillna(0.0)

    for year in [int(y) for y in years]:
        assets = sum(float(frame.loc[i, year]) for i in BS_ASSETS if i in frame.index)
        equity = sum(float(frame.loc[i, year]) for i in BS_EQUITY if i in frame.index)
        liabilities = sum(float(frame.loc[i, year]) for i in BS_LIABS if i in frame.index)
        residue = assets - equity - liabilities
        # Park any source-data residue explicitly rather than hiding it.
        if abs(residue) > 0.01:
            frame.loc["Opening Reconciliation Item", year] = (
                float(frame.loc["Opening Reconciliation Item", year]) + residue
            )
            liabilities += residue
        frame.loc["Total Assets", year] = assets
        frame.loc["Total Equity", year] = equity
        frame.loc["Total Liabilities", year] = liabilities
        frame.loc["Total Equity and Liabilities", year] = equity + liabilities
        frame.loc["Balance Check", year] = assets - equity - liabilities

    return _reorder(frame, BS_ROWS)


def derive_cash_flow(cf: pd.DataFrame, pnl: pd.DataFrame, bs: pd.DataFrame,
                     years: List[int]) -> pd.DataFrame:
    """Complete the historical cash flow from the P&L and balance sheet where needed."""
    index = list(dict.fromkeys(list(cf.index) + CF_ROWS))
    frame = cf.reindex(index=index, columns=[int(y) for y in years]).astype(float)
    year_list = [int(y) for y in years]

    for position, year in enumerate(year_list):
        if pd.isna(frame.loc["PAT", year]) and "PAT" in pnl.index:
            frame.loc["PAT", year] = float(pnl.loc["PAT", year])
        if pd.isna(frame.loc["Depreciation & Amortisation", year]) \
                and "Depreciation & Amortisation" in pnl.index:
            frame.loc["Depreciation & Amortisation", year] = float(
                pnl.loc["Depreciation & Amortisation", year]
            )
        if pd.isna(frame.loc["Closing Cash", year]) \
                and "Cash and Cash Equivalents" in bs.index:
            frame.loc["Closing Cash", year] = float(
                bs.loc["Cash and Cash Equivalents", year]
            )
        if pd.isna(frame.loc["Opening Cash", year]):
            if position == 0:
                frame.loc["Opening Cash", year] = np.nan
            else:
                prior = year_list[position - 1]
                frame.loc["Opening Cash", year] = frame.loc["Closing Cash", prior]

        cfo = frame.loc["Cash Flow from Operating Activities", year]
        cfi = frame.loc["Cash Flow from Investing Activities", year]
        cff = frame.loc["Cash Flow from Financing Activities", year]
        if not any(pd.isna(x) for x in (cfo, cfi, cff)):
            frame.loc["Net Change in Cash", year] = float(cfo) + float(cfi) + float(cff)

    return _reorder(frame.fillna(0.0), CF_ROWS)


# =====================================================================================
# PART 2.5  BUILD THE STANDARDISED HISTORICAL MODEL
# =====================================================================================
def build_historical_model(paths: List[str]) -> HistoricalModel:
    """Parse every workbook, resolve duplicate years, validate and standardise."""
    frames: List[pd.DataFrame] = []
    messages: List[Tuple[str, str]] = []
    companies: List[str] = []
    files: List[str] = []

    if not paths:
        raise ValueError("No files were selected.")

    for path in paths:
        tidy, company, msgs = parse_workbook(path)
        messages.extend(msgs)
        files.append(os.path.basename(path))
        if company:
            companies.append(company)
        if not tidy.empty:
            frames.append(tidy)

    if not frames:
        raise ValueError(
            "No readable financial data was found. Please check that the workbooks "
            "contain P&L, Balance Sheet and Cash Flow sheets with financial-year "
            "column headings."
        )

    tidy = pd.concat(frames, ignore_index=True)
    company = max(set(companies), key=companies.count) if companies else "Company"
    if len(set(companies)) > 1:
        messages.append((
            "WARNING",
            "More than one company name was detected across the files ("
            + "; ".join(sorted(set(companies)))
            + f"). Proceeding on the basis that all files relate to '{company}'.",
        ))

    mapped = tidy[tidy["category"] == "Mapped"].copy()
    unmapped = tidy[tidy["category"] == "Unmapped"].copy()
    if mapped.empty:
        raise ValueError("Financial years were found but no line items could be mapped.")

    if not unmapped.empty:
        odd = sorted(set(unmapped["source_label"]))
        shown = ", ".join(odd[:10]) + (" ..." if len(odd) > 10 else "")
        messages.append((
            "WARNING",
            f"{len(odd)} unexpected line item(s) were not recognised and have been "
            f"excluded from the model: {shown}",
        ))

    # ---- duplicate financial years (comparative columns) --------------------------
    duplicates = mapped.groupby(
        ["statement", "line_item", "financial_year"]
    )["source_file"].nunique()
    duplicate_count = int((duplicates > 1).sum())
    if duplicate_count:
        messages.append((
            "WARNING",
            f"{duplicate_count} line item and year combination(s) appeared in more than "
            f"one workbook, which is expected where files carry a comparative column. "
            f"The file that reports each year as its own primary year has been used.",
        ))
    mapped = mapped.sort_values(
        ["primary", "source_file"], ascending=[False, True]
    ).drop_duplicates(
        subset=["statement", "line_item", "financial_year"], keep="first"
    )

    def pivot(statement: str) -> pd.DataFrame:
        subset = mapped[mapped["statement"] == statement]
        if subset.empty:
            return pd.DataFrame()
        frame = subset.pivot_table(
            index="line_item", columns="financial_year", values="value", aggfunc="sum"
        )
        frame.columns = [int(c) for c in frame.columns]
        frame = frame.sort_index(axis=1)
        return _reorder(frame.astype(float), ORDER_BY_STATEMENT.get(statement, []))

    pnl_raw = pivot("P&L")
    bs_raw = pivot("Balance Sheet")
    cf_raw = pivot("Cash Flow")
    equity_raw = pivot("Equity")
    schedules_raw = pivot("Schedules")

    year_set = set()
    for frame in (pnl_raw, bs_raw, cf_raw):
        if not frame.empty:
            year_set.update(int(c) for c in frame.columns)
    years = sorted(year_set)
    if not years:
        raise ValueError("No financial years could be identified in the files.")

    pnl = derive_pnl_subtotals(pnl_raw if not pnl_raw.empty
                               else _blank_frame(PNL_ROWS, years), years)
    bs = complete_balance_sheet(bs_raw if not bs_raw.empty
                                else _blank_frame(BS_ASSETS + BS_EQUITY + BS_LIABS, years),
                                years)
    cf = derive_cash_flow(cf_raw if not cf_raw.empty
                          else _blank_frame(CF_ROWS, years), pnl, bs, years)

    # ---- completeness of required line items --------------------------------------
    for statement, frame, raw in (("P&L", pnl, pnl_raw),
                                  ("Balance Sheet", bs, bs_raw),
                                  ("Cash Flow", cf, cf_raw)):
        for item in REQUIRED_HIST[statement]:
            present = (not raw.empty) and (item in raw.index)
            if not present:
                messages.append((
                    "WARNING",
                    f"{statement}: required line item '{item}' was not found in the "
                    f"source files and has been treated as nil or derived.",
                ))

    gaps = [y for y in range(years[0], years[-1] + 1) if y not in years]
    if gaps:
        messages.append((
            "WARNING",
            "The historical years are not continuous. Missing: "
            + ", ".join(f"FY{g}" for g in gaps),
        ))

    for year in years:
        revenue = float(pnl.loc["Revenue", year]) if "Revenue" in pnl.index else 0.0
        if revenue <= 0:
            messages.append((
                "ERROR",
                f"FY{year}: revenue is nil or negative, so growth-based forecasting "
                f"cannot be performed reliably for that year.",
            ))

    model = HistoricalModel(
        company=company,
        years=[int(y) for y in years],
        pnl=pnl,
        balance_sheet=bs,
        cash_flow=cf,
        schedules=schedules_raw,
        equity=equity_raw,
        tidy=tidy,
        unit=BASE_UNIT,
        messages=messages,
        source_files=files,
    )
    return model


def validation_frame(hist: HistoricalModel) -> pd.DataFrame:
    """Upload and data-validation summary shown on the Import page."""
    rows: List[Tuple[str, str, str]] = []
    for year in hist.years:
        rows.append((f"FY{year} loaded", "PASS",
                     f"Revenue Rs {hist.value('P&L', 'Revenue', year):,.0f} lakh"))
    rows.append((
        "Company identified", "PASS", hist.company,
    ))
    rows.append((
        "Historical years continuous",
        "PASS" if hist.years == list(range(hist.years[0], hist.years[-1] + 1))
        else "WARNING",
        ", ".join(f"FY{y}" for y in hist.years),
    ))
    for year in hist.years:
        residue = hist.value("Balance Sheet", "Balance Check", year)
        rows.append((
            f"FY{year} balance sheet balances",
            "PASS" if abs(residue) < 0.01 else "WARNING",
            "Balanced" if abs(residue) < 0.01
            else f"Residue of Rs {residue:,.2f} lakh parked in a reconciliation line",
        ))
    for statement in ("P&L", "Balance Sheet", "Cash Flow"):
        missing = [i for i in REQUIRED_HIST[statement] if not hist.has(statement, i)]
        rows.append((
            f"{statement} required line items",
            "PASS" if not missing else "WARNING",
            "All present" if not missing else "Derived or nil: " + ", ".join(missing),
        ))
    for level, text in hist.messages:
        if level in ("WARNING", "ERROR"):
            rows.append(("Parser message", level, text))
    return pd.DataFrame(rows, columns=["Check", "Status", "Detail"])



def reconciliation_frame(hist: HistoricalModel) -> pd.DataFrame:
    rows = []
    for stmt in ("P&L","Balance Sheet","Cash Flow"):
        raw = hist.tidy[(hist.tidy["statement"]==stmt) & (hist.tidy["category"]=="Mapped")]
        uploaded_total = float(raw["value"].sum()) if not raw.empty else 0.0
        imported_df = hist.frame(stmt)
        imported_total = float(imported_df.to_numpy(dtype=float).sum()) if imported_df is not None and not imported_df.empty else 0.0
        variance = uploaded_total - imported_total
        rows.append((stmt, uploaded_total, imported_total, variance))
    return pd.DataFrame(rows, columns=["Statement","Total as uploaded","Total as imported","Variance"])


def field_level_reconciliation(hist: HistoricalModel,
                               tolerance: float = 0.05) -> pd.DataFrame:
    """Line-item-by-line-item, year-by-year comparison of every value as uploaded
    against the value actually used in the standardised model. Every difference is
    reported in plain English with a likely cause, a suggested action, and a flag
    for whether it can be corrected automatically."""
    columns = ["Statement", "Line item", "Financial year", "What we found",
               "Uploaded value", "Imported value", "Difference", "Likely cause",
               "Suggested action", "Auto-fixable", "Status", "Reviewer note"]
    if hist.tidy is None or hist.tidy.empty:
        return pd.DataFrame(columns=columns)

    rows: List[Dict[str, Any]] = []
    mapped = hist.tidy[hist.tidy["category"] == "Mapped"].copy()

    for (statement, item, year), grp in mapped.groupby(
            ["statement", "line_item", "financial_year"]):
        imported_value = hist.value(statement, item, int(year))
        distinct = sorted({round(float(v), 2) for v in grp["value"]})

        if len(distinct) > 1:
            files = ", ".join(sorted(set(grp["source_file"])))
            rows.append({
                "Statement": statement,
                "Line item": item,
                "Financial year": int(year),
                "What we found": (
                    str(len(distinct)) + " different figures were uploaded for this "
                    "line item and year (from " + files + ")."),
                "Uploaded value": " / ".join(f"{v:,.1f}" for v in distinct),
                "Imported value": f"{imported_value:,.1f}",
                "Difference": f"{max(distinct) - min(distinct):,.1f}",
                "Likely cause": (
                    "More than one file reports this year, for example one file shows "
                    "it as the latest year and another shows it as a comparative "
                    "column, and the two figures do not agree."),
                "Suggested action": (
                    "Decide which figure is correct, then type it into the editable "
                    "grid lower down this page."),
                "Auto-fixable": False,
                "Status": "Pending",
                "Reviewer note": "",
            })
            continue

        uploaded_value = distinct[0]
        if abs(uploaded_value - imported_value) > tolerance:
            rows.append({
                "Statement": statement,
                "Line item": item,
                "Financial year": int(year),
                "What we found": (
                    "The figure used in the model does not match the figure that was "
                    "uploaded."),
                "Uploaded value": f"{uploaded_value:,.1f}",
                "Imported value": f"{imported_value:,.1f}",
                "Difference": f"{imported_value - uploaded_value:,.1f}",
                "Likely cause": (
                    "Usually a currency-unit conversion, for example crore against "
                    "lakh, or this year being overwritten by another file."),
                "Suggested action": (
                    "Check the reporting unit shown above. If the imported figure is "
                    "wrong, choose Use uploaded value, or correct it in the editable "
                    "grid."),
                "Auto-fixable": True,
                "Status": "Pending",
                "Reviewer note": "",
            })

    unmapped = hist.tidy[hist.tidy["category"] == "Unmapped"]
    for (statement, label, year), grp in unmapped.groupby(
            ["statement", "source_label", "financial_year"]):
        candidates = list(SYNONYMS.get(statement, {}).keys())
        suggestion = _suggest_line_item(label, candidates)
        hint = (" It most closely resembles '" + str(suggestion) + "'."
                if suggestion else "")
        rows.append({
            "Statement": statement,
            "Line item": "[Unrecognised] " + str(label),
            "Financial year": int(year),
            "What we found": (
                "This row was in the uploaded file, but its wording did not match any "
                "line item the model understands, so it was left out of the forecast."),
            "Uploaded value": f"{float(grp['value'].iloc[0]):,.1f}",
            "Imported value": "Not used",
            "Difference": "-",
            "Likely cause": (
                "The caption used in the workbook is non-standard." + hint),
            "Suggested action": (
                "If it is a footnote or memorandum figure, choose Ignore this item. If "
                "it belongs in the forecast, add its value to the closest matching "
                "line in the editable grid."),
            "Auto-fixable": False,
            "Status": "Pending",
            "Reviewer note": "",
        })

    frame = pd.DataFrame(rows, columns=columns)
    if frame.empty:
        return frame
    return frame.sort_values(
        ["Statement", "Financial year", "Line item"]).reset_index(drop=True)

# =====================================================================================
# PART 2.6  HISTORICAL TREND AND RATIO ANALYSIS
# =====================================================================================
def _safe_divide(numerator: float, denominator: float,
                 default: float = float("nan")) -> float:
    if denominator is None or abs(float(denominator)) < 1e-9:
        return default
    return float(numerator) / float(denominator)


def _growth(series: pd.Series) -> pd.Series:
    """Year-on-year growth of a series, expressed as a decimal fraction."""
    out = {}
    years = list(series.index)
    for position, year in enumerate(years):
        if position == 0:
            out[year] = float("nan")
        else:
            prior = float(series.iloc[position - 1])
            out[year] = _safe_divide(float(series.iloc[position]) - prior, abs(prior))
    return pd.Series(out, dtype=float)


def cagr(series: pd.Series) -> float:
    """Compound annual growth rate across the full span of a series."""
    clean = series.dropna()
    if len(clean) < 2:
        return float("nan")
    first, last = float(clean.iloc[0]), float(clean.iloc[-1])
    periods = len(clean) - 1
    if first <= 0 or last <= 0 or periods <= 0:
        return float("nan")
    return (last / first) ** (1.0 / periods) - 1.0


def linear_trend(series: pd.Series, steps_ahead: int = 1) -> float:
    """Ordinary least squares fit extrapolated a given number of periods forward."""
    clean = series.dropna()
    if len(clean) < 2:
        return float(clean.iloc[-1]) if len(clean) == 1 else float("nan")
    x = np.arange(len(clean), dtype=float)
    y = clean.to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope * (len(clean) - 1 + steps_ahead) + intercept)


def capex_series(hist: HistoricalModel) -> pd.Series:
    """Historical capex as a positive magnitude, taken from the cash flow statement."""
    raw = hist.series("Cash Flow", "Capital Expenditure")
    return raw.abs()


def historical_ratios(hist: HistoricalModel) -> pd.DataFrame:
    """Full historical trend analysis: growth, margins, working capital, leverage, cash."""
    years = hist.years
    revenue = hist.series("P&L", "Revenue")
    other_income = hist.series("P&L", "Other Income")
    cogs = hist.series("P&L", "Cost of Goods Sold")
    ebitda = hist.series("P&L", "EBITDA")
    ebit = hist.series("P&L", "EBIT")
    pbt = hist.series("P&L", "PBT")
    pat = hist.series("P&L", "PAT")
    finance_cost = hist.series("P&L", "Finance Cost")
    depreciation = hist.series("P&L", "Depreciation & Amortisation")

    receivables = hist.series("Balance Sheet", "Trade Receivables")
    inventory = hist.series("Balance Sheet", "Inventory")
    payables = hist.series("Balance Sheet", "Trade Payables")
    oca = hist.series("Balance Sheet", "Other Current Assets")
    ocl = hist.series("Balance Sheet", "Other Current Liabilities")
    cash = hist.series("Balance Sheet", "Cash and Cash Equivalents")
    borrowings = hist.series("Balance Sheet", "Borrowings")
    leases = hist.series("Balance Sheet", "Lease Liabilities")
    equity_total = hist.series("Balance Sheet", "Total Equity")

    cfo = hist.series("Cash Flow", "Cash Flow from Operating Activities")
    capex = capex_series(hist)

    debt = borrowings + leases
    net_debt = debt - cash
    working_capital = (receivables + inventory + oca) - (payables + ocl)
    free_cash_flow = cfo - capex

    rows: Dict[str, pd.Series] = {}

    # ---- growth ---------------------------------------------------------------------
    rows["Revenue growth"] = _growth(revenue)
    rows["EBITDA growth"] = _growth(ebitda)
    rows["EBIT growth"] = _growth(ebit)
    rows["PAT growth"] = _growth(pat)
    rows["Capex growth"] = _growth(capex)

    # ---- margins --------------------------------------------------------------------
    rows["EBITDA margin"] = pd.Series(
        {y: _safe_divide(ebitda[y], revenue[y]) for y in years})
    rows["EBIT margin"] = pd.Series(
        {y: _safe_divide(ebit[y], revenue[y]) for y in years})
    rows["PBT margin"] = pd.Series(
        {y: _safe_divide(pbt[y], revenue[y]) for y in years})
    rows["PAT margin"] = pd.Series(
        {y: _safe_divide(pat[y], revenue[y]) for y in years})
    rows["Other income / Revenue"] = pd.Series(
        {y: _safe_divide(other_income[y], revenue[y]) for y in years})
    rows["COGS / Revenue"] = pd.Series(
        {y: _safe_divide(cogs[y], revenue[y]) for y in years})

    # ---- working capital ------------------------------------------------------------
    rows["Receivable days"] = pd.Series(
        {y: _safe_divide(receivables[y] * 365.0, revenue[y]) for y in years})
    rows["Inventory days"] = pd.Series(
        {y: _safe_divide(inventory[y] * 365.0, cogs[y]) for y in years})
    rows["Payable days"] = pd.Series(
        {y: _safe_divide(payables[y] * 365.0, cogs[y]) for y in years})
    rows["Working capital"] = working_capital
    rows["Working capital / Revenue"] = pd.Series(
        {y: _safe_divide(working_capital[y], revenue[y]) for y in years})

    # ---- leverage -------------------------------------------------------------------
    rows["Total debt"] = debt
    rows["Net debt"] = net_debt
    rows["Debt / EBITDA"] = pd.Series(
        {y: _safe_divide(debt[y], ebitda[y]) for y in years})
    rows["Net debt / EBITDA"] = pd.Series(
        {y: _safe_divide(net_debt[y], ebitda[y]) for y in years})
    rows["Debt / Equity"] = pd.Series(
        {y: _safe_divide(debt[y], equity_total[y]) for y in years})
    rows["Interest coverage (EBIT / Finance cost)"] = pd.Series(
        {y: _safe_divide(ebit[y], finance_cost[y]) for y in years})

    # ---- cash conversion ------------------------------------------------------------
    rows["CFO"] = cfo
    rows["CFO / EBITDA"] = pd.Series(
        {y: _safe_divide(cfo[y], ebitda[y]) for y in years})
    rows["CFO / PAT"] = pd.Series(
        {y: _safe_divide(cfo[y], pat[y]) for y in years})
    rows["Free cash flow"] = free_cash_flow
    rows["FCF / Revenue"] = pd.Series(
        {y: _safe_divide(free_cash_flow[y], revenue[y]) for y in years})
    rows["Capex / Revenue"] = pd.Series(
        {y: _safe_divide(capex[y], revenue[y]) for y in years})
    rows["D&A / Revenue"] = pd.Series(
        {y: _safe_divide(depreciation[y], revenue[y]) for y in years})

    frame = pd.DataFrame(rows).T
    frame.columns = [int(c) for c in frame.columns]
    return frame.reindex(columns=sorted(frame.columns))


RATIO_KINDS: Dict[str, str] = {
    "Revenue growth": "percent", "EBITDA growth": "percent", "EBIT growth": "percent",
    "PAT growth": "percent", "Capex growth": "percent", "EBITDA margin": "percent",
    "EBIT margin": "percent", "PBT margin": "percent", "PAT margin": "percent",
    "Other income / Revenue": "percent", "COGS / Revenue": "percent",
    "Receivable days": "days", "Inventory days": "days", "Payable days": "days",
    "Working capital": "amount", "Working capital / Revenue": "percent",
    "Total debt": "amount", "Net debt": "amount", "Debt / EBITDA": "times",
    "Net debt / EBITDA": "times", "Debt / Equity": "times",
    "Interest coverage (EBIT / Finance cost)": "times", "CFO": "amount",
    "CFO / EBITDA": "percent", "CFO / PAT": "percent", "Free cash flow": "amount",
    "FCF / Revenue": "percent", "Capex / Revenue": "percent", "D&A / Revenue": "percent",
}

RATIO_GROUPS: Dict[str, List[str]] = {
    "Growth": ["Revenue growth", "EBITDA growth", "EBIT growth", "PAT growth",
               "Capex growth"],
    "Margins": ["EBITDA margin", "EBIT margin", "PBT margin", "PAT margin",
                "COGS / Revenue", "Other income / Revenue"],
    "Working capital": ["Receivable days", "Inventory days", "Payable days",
                        "Working capital", "Working capital / Revenue"],
    "Leverage": ["Total debt", "Net debt", "Debt / EBITDA", "Net debt / EBITDA",
                 "Debt / Equity", "Interest coverage (EBIT / Finance cost)"],
    "Cash conversion": ["CFO", "CFO / EBITDA", "CFO / PAT", "Free cash flow",
                        "FCF / Revenue", "Capex / Revenue", "D&A / Revenue"],
}


# =====================================================================================
# PART 2.7  HISTORICAL DRIVERS BEHIND "USE HISTORICAL TREND"
# Each assumption is linked to the historical series that implies it, so the average,
# CAGR and linear-trend methodologies are all computed from the actual accounts.
# =====================================================================================
def historical_driver_series(hist: HistoricalModel, key: str) -> pd.Series:
    """The implied historical series for one assumption, in internal units."""
    years = hist.years
    revenue = hist.series("P&L", "Revenue")
    cogs = hist.series("P&L", "Cost of Goods Sold")
    ratios = historical_ratios(hist)

    def ratio(name: str) -> pd.Series:
        if name in ratios.index:
            return ratios.loc[name].astype(float)
        return pd.Series({y: float("nan") for y in years}, dtype=float)

    if key == "revenue_growth":
        return ratio("Revenue growth")
    if key == "other_income_pct":
        return ratio("Other income / Revenue")
    if key == "cogs_pct":
        return ratio("COGS / Revenue")
    if key == "employee_pct":
        employee = hist.series("P&L", "Employee Cost")
        return pd.Series({y: _safe_divide(employee[y], revenue[y]) for y in years})
    if key == "other_opex_pct":
        other_opex = hist.series("P&L", "Other Operating Expenses")
        return pd.Series({y: _safe_divide(other_opex[y], revenue[y]) for y in years})
    if key == "capex_pct":
        return ratio("Capex / Revenue")
    if key == "dep_rate":
        depreciation = hist.series("P&L", "Depreciation & Amortisation")
        ppe = hist.series("Balance Sheet", "Property, Plant and Equipment")
        out = {}
        for position, year in enumerate(years):
            opening = float(ppe.iloc[position - 1]) if position > 0 else float(ppe.iloc[0])
            out[year] = _safe_divide(depreciation[year], opening)
        return pd.Series(out, dtype=float)
    if key == "amort_rate":
        intangibles = hist.series("Balance Sheet", "Intangible Assets")
        depreciation = hist.series("P&L", "Depreciation & Amortisation")
        return pd.Series(
            {y: _safe_divide(depreciation[y] * 0.1, intangibles[y]) for y in years})
    if key == "receivable_days":
        return ratio("Receivable days")
    if key == "inventory_days":
        return ratio("Inventory days")
    if key == "payable_days":
        return ratio("Payable days")
    if key == "oca_pct":
        oca = hist.series("Balance Sheet", "Other Current Assets")
        return pd.Series({y: _safe_divide(oca[y], revenue[y]) for y in years})
    if key == "ocl_pct":
        ocl = hist.series("Balance Sheet", "Other Current Liabilities")
        return pd.Series({y: _safe_divide(ocl[y], revenue[y]) for y in years})
    if key == "provisions_pct":
        provisions = hist.series("Balance Sheet", "Provisions")
        return pd.Series({y: _safe_divide(provisions[y], revenue[y]) for y in years})
    if key == "interest_rate":
        finance_cost = hist.series("P&L", "Finance Cost")
        borrowings = hist.series("Balance Sheet", "Borrowings")
        leases = hist.series("Balance Sheet", "Lease Liabilities")
        debt = borrowings + leases
        out = {}
        for position, year in enumerate(years):
            if position == 0:
                average = float(debt.iloc[0])
            else:
                average = 0.5 * (float(debt.iloc[position - 1]) + float(debt.iloc[position]))
            out[year] = _safe_divide(finance_cost[year], average)
        return pd.Series(out, dtype=float)
    if key == "tax_rate":
        tax = hist.series("P&L", "Tax Expense")
        pbt = hist.series("P&L", "PBT")
        return pd.Series({y: _safe_divide(tax[y], pbt[y]) for y in years})
    if key == "tax_payable_pct":
        payable = hist.series("Balance Sheet", "Current Tax Payable")
        tax = hist.series("P&L", "Tax Expense")
        return pd.Series({y: _safe_divide(payable[y], tax[y]) for y in years})
    if key == "dividend_payout":
        dividends = hist.series("Cash Flow", "Dividends Paid").abs()
        pat = hist.series("P&L", "PAT")
        return pd.Series({y: _safe_divide(dividends[y], pat[y]) for y in years})

    return pd.Series({y: float("nan") for y in years}, dtype=float)


def apply_methodologies(hist: HistoricalModel,
                        assumptions: AssumptionSet) -> AssumptionSet:
    """Overwrite each non-manual assumption using the chosen historical methodology."""
    result = assumptions.copy()
    for key in PARAM_KEYS:
        method = result.method(key)
        if method == "Manual" or not PARAMS[key].trend_capable:
            continue
        series = historical_driver_series(hist, key).replace(
            [np.inf, -np.inf], np.nan).dropna()
        if series.empty:
            continue
        spec = PARAMS[key]
        if method == "Historical average":
            value = float(series.mean())
            for year in result.years:
                result.set(key, year, spec.clamp(value))
        elif method == "Historical CAGR":
            if key == "revenue_growth":
                rate = cagr(hist.series("P&L", "Revenue"))
                value = float(series.mean()) if pd.isna(rate) else float(rate)
                for year in result.years:
                    result.set(key, year, spec.clamp(value))
            else:
                rate = cagr(series)
                last = float(series.iloc[-1])
                if pd.isna(rate):
                    for year in result.years:
                        result.set(key, year, spec.clamp(last))
                else:
                    running = last
                    for year in result.years:
                        running = running * (1.0 + rate)
                        result.set(key, year, spec.clamp(running))
        elif method == "Linear trend":
            for step, year in enumerate(result.years, start=1):
                projected = linear_trend(series, steps_ahead=step)
                if pd.isna(projected):
                    projected = float(series.iloc[-1])
                result.set(key, year, spec.clamp(float(projected)))
    return result


# =====================================================================================
# PART 2.8  DISPLAY FORMATTING AND COMPARATIVE HISTORICAL VIEWS
# =====================================================================================
def format_value(value: Any, kind: str = "amount", divisor: float = 1.0) -> str:
    """Format one number for display, tolerating NaN and infinities."""
    if value is None:
        return "-"
    try:
        number = float(value)
    except Exception:
        return str(value)
    if pd.isna(number) or np.isinf(number):
        return "-"
    if kind == "percent":
        return f"{number * 100:,.1f}%"
    if kind == "times":
        return f"{number:,.2f}x"
    if kind == "days":
        return f"{number:,.0f}"
    if kind == "ratio_pct":
        return f"{number:,.1f}%"
    return f"{number / divisor:,.1f}" if divisor != 1.0 else f"{number:,.0f}"


def _period_growth(series: pd.Series) -> str:
    """CAGR across the period, falling back to year-on-year where only two years exist."""
    clean = series.dropna()
    if len(clean) < 2:
        return "-"
    rate = cagr(clean)
    if pd.isna(rate):
        first, last = float(clean.iloc[0]), float(clean.iloc[-1])
        rate = _safe_divide(last - first, abs(first))
    return format_value(rate, "percent")


def _column_label(year: int) -> str:
    return f"FY{str(int(year))[-2:]}"


def _apply_display_mode(values: pd.Series, mode: str,
                        revenue: pd.Series) -> Tuple[pd.Series, str]:
    """Convert an amount series into the selected presentation basis."""
    if mode == "Rs crore":
        return values / 100.0, "amount_1dp"
    if mode == "% of revenue":
        converted = pd.Series(
            {y: _safe_divide(values[y], revenue[y]) for y in values.index}, dtype=float)
        return converted, "percent"
    if mode == "Absolute change":
        return values.diff(), "amount_1dp"
    return values, "amount"


def comparative_pnl(hist: HistoricalModel, mode: str = "Rs lakh") -> pd.DataFrame:
    """Comparative historical profit and loss with a growth column."""
    revenue = hist.series("P&L", "Revenue")
    amount_rows = ["Revenue", "Other Income", "Cost of Goods Sold", "Employee Cost",
                   "Other Operating Expenses", "EBITDA", "Depreciation & Amortisation",
                   "EBIT", "Finance Cost", "PBT", "Tax Expense", "PAT"]
    margin_after = {"EBITDA": "EBITDA margin", "EBIT": "EBIT margin",
                    "PBT": "PBT margin", "PAT": "PAT margin"}

    records: List[Tuple[str, List[str], str]] = []
    for item in amount_rows:
        series = hist.series("P&L", item)
        converted, kind = _apply_display_mode(series, mode, revenue)
        cells = [format_value(converted[y], "percent" if kind == "percent" else "amount",
                              1.0) if kind == "percent"
                 else (f"{converted[y]:,.1f}" if kind == "amount_1dp"
                       else f"{converted[y]:,.0f}" if not pd.isna(converted[y]) else "-")
                 for y in hist.years]
        records.append((item, cells, _period_growth(series)))
        if item in margin_after:
            margin = pd.Series(
                {y: _safe_divide(series[y], revenue[y]) for y in hist.years}, dtype=float)
            records.append((
                "  " + margin_after[item],
                [format_value(margin[y], "percent") for y in hist.years],
                "-",
            ))

    columns = [_column_label(y) for y in hist.years] + ["Growth"]
    data = [cells + [growth] for _, cells, growth in records]
    return pd.DataFrame(data, index=[label for label, _, _ in records], columns=columns)


def comparative_balance_sheet(hist: HistoricalModel,
                              mode: str = "Rs lakh") -> pd.DataFrame:
    """Comparative balance sheet with year-on-year movement in value and percentage."""
    revenue = hist.series("P&L", "Revenue")
    order = (["ASSETS"] + BS_ASSETS + ["Total Assets", "EQUITY"] + BS_EQUITY
             + ["Total Equity", "LIABILITIES"] + BS_LIABS
             + ["Total Liabilities", "Total Equity and Liabilities", "Balance Check"])

    index: List[str] = []
    data: List[List[str]] = []
    latest = hist.years[-1]
    prior = hist.years[-2] if len(hist.years) > 1 else None

    for item in order:
        if item in ("ASSETS", "EQUITY", "LIABILITIES"):
            index.append(item)
            data.append(["" for _ in hist.years] + ["", ""])
            continue
        if item not in hist.balance_sheet.index:
            continue
        series = hist.series("Balance Sheet", item)
        if item == "Opening Reconciliation Item" and series.abs().max() < 0.01:
            continue
        converted, kind = _apply_display_mode(series, mode, revenue)
        cells = []
        for year in hist.years:
            value = converted[year]
            if kind == "percent":
                cells.append(format_value(value, "percent"))
            elif pd.isna(value):
                cells.append("-")
            elif kind == "amount_1dp":
                cells.append(f"{value:,.1f}")
            else:
                cells.append(f"{value:,.0f}")
        if prior is None:
            movement, percentage = "-", "-"
        else:
            change = float(series[latest]) - float(series[prior])
            movement = f"{change:,.0f}"
            percentage = format_value(_safe_divide(change, abs(float(series[prior]))),
                                      "percent")
        index.append(item)
        data.append(cells + [movement, percentage])

    columns = [_column_label(y) for y in hist.years] + ["YoY movement", "YoY %"]
    return pd.DataFrame(data, index=index, columns=columns)


def comparative_cash_flow(hist: HistoricalModel, mode: str = "Rs lakh") -> pd.DataFrame:
    """Summary historical cash flow: CFO, CFI, CFF, net change and closing cash."""
    revenue = hist.series("P&L", "Revenue")
    rows = [
        ("Cash flow from operating activities", "Cash Flow from Operating Activities"),
        ("Cash flow from investing activities", "Cash Flow from Investing Activities"),
        ("Cash flow from financing activities", "Cash Flow from Financing Activities"),
        ("Net change in cash", "Net Change in Cash"),
        ("Opening cash", "Opening Cash"),
        ("Closing cash", "Closing Cash"),
    ]
    index: List[str] = []
    data: List[List[str]] = []
    for label, item in rows:
        series = hist.series("Cash Flow", item)
        converted, kind = _apply_display_mode(series, mode, revenue)
        cells = []
        for year in hist.years:
            value = converted[year]
            if kind == "percent":
                cells.append(format_value(value, "percent"))
            elif pd.isna(value):
                cells.append("-")
            elif kind == "amount_1dp":
                cells.append(f"{value:,.1f}")
            else:
                cells.append(f"{value:,.0f}")
        index.append(label)
        data.append(cells + [_period_growth(series)])
    columns = [_column_label(y) for y in hist.years] + ["Growth"]
    return pd.DataFrame(data, index=index, columns=columns)


def ratio_display_frame(hist: HistoricalModel,
                        group: Optional[str] = None) -> pd.DataFrame:
    """Historical ratio table formatted for display, optionally limited to one group."""
    ratios = historical_ratios(hist)
    names = RATIO_GROUPS.get(group, list(ratios.index)) if group else list(ratios.index)
    names = [n for n in names if n in ratios.index]
    index: List[str] = []
    data: List[List[str]] = []
    for name in names:
        kind = RATIO_KINDS.get(name, "amount")
        index.append(name)
        data.append([format_value(ratios.loc[name, y], kind) for y in ratios.columns])
    return pd.DataFrame(data, index=index,
                        columns=[_column_label(y) for y in ratios.columns])


# ---------------------------------------------------------------------------------
# END OF PART 2.
# Paste PART 3 (forecast engine, model checks, sensitivity, Excel export, demo data
# and self-tests) directly beneath this line.
# ---------------------------------------------------------------------------------
# =====================================================================================
# PART 3.0  ADDITIONAL IMPORTS FOR THE ENGINE, EXPORT AND DEMO DATA
# =====================================================================================
import tempfile

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

TOL = 0.05          # Rs lakh tolerance used by every reconciliation check
MAX_ITERATIONS = 80  # circularity solver iteration cap
DAMPING = 0.80       # damping applied to the funding plug between iterations


# =====================================================================================
# PART 3.1  PARSER HARDENING OVERRIDE
# A bare numeric cell is only treated as a financial-year heading inside a narrow,
# realistic window. This prevents an ordinary balance-sheet figure such as 2,300 from
# being mistaken for a year when the header row is being located.
# =====================================================================================
def _year_header(value: Any) -> Optional[int]:
    """Does this cell look like a financial-year column heading?"""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return int(value.year)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, np.integer, np.floating)):
        number = float(value)
        if float(number).is_integer() and 2000.0 <= number <= 2060.0:
            return int(number)
        return None
    if isinstance(value, str):
        return extract_year(value)
    return None


# =====================================================================================
# PART 3.2  MODEL OUTPUT CONTAINER
# =====================================================================================
@dataclass
class ModelOutput:
    """The complete forecast. Every frame is indexed by line item, columns are years."""

    company: str
    years: List[int]
    base_year: int
    scenario: str
    pnl: pd.DataFrame
    balance_sheet: pd.DataFrame
    cash_flow: pd.DataFrame
    ppe_schedule: pd.DataFrame
    working_capital_schedule: pd.DataFrame
    debt_schedule: pd.DataFrame
    tax_schedule: pd.DataFrame
    equity_schedule: pd.DataFrame
    ratios: pd.DataFrame = field(default_factory=pd.DataFrame)
    checks: pd.DataFrame = field(default_factory=pd.DataFrame)
    iterations: Dict[int, int] = field(default_factory=dict)
    converged: bool = True
    assumptions: Optional[AssumptionSet] = None

    def frame(self, name: str) -> pd.DataFrame:
        return {
            "P&L": self.pnl,
            "Balance Sheet": self.balance_sheet,
            "Cash Flow": self.cash_flow,
            "PPE Schedule": self.ppe_schedule,
            "Working Capital Schedule": self.working_capital_schedule,
            "Debt Schedule": self.debt_schedule,
            "Tax Schedule": self.tax_schedule,
            "Equity Schedule": self.equity_schedule,
            "Ratios": self.ratios,
        }.get(name, pd.DataFrame())

    def value(self, statement: str, item: str, year: int, default: float = 0.0) -> float:
        data = self.frame(statement)
        if data is None or data.empty or item not in data.index:
            return default
        if int(year) not in list(data.columns):
            return default
        raw = data.loc[item, int(year)]
        return default if pd.isna(raw) else float(raw)

    @property
    def terminal_year(self) -> int:
        return int(self.years[-1])


# =====================================================================================
# PART 3.3  DEPRECIATION
# =====================================================================================
def compute_depreciation(method: str, opening: float, capex: float, disposals: float,
                         rate: float, useful_life: float) -> float:
    """Depreciation for one year on the selected methodology, floored at nil."""
    gross_before_depreciation = max(opening + capex - disposals, 0.0)
    if method == "Rate on average balance":
        charge = rate * 0.5 * (max(opening, 0.0) + gross_before_depreciation)
    elif method == "Straight line on useful life":
        life = max(float(useful_life), 1.0)
        charge = gross_before_depreciation / life
    else:  # "Rate on opening balance" - the default
        charge = rate * max(opening, 0.0)
    # Never depreciate a book value below nil.
    return float(min(max(charge, 0.0), gross_before_depreciation))


# =====================================================================================
# PART 3.4  THE INTEGRATED FORECAST ENGINE
#
# One dependency chain, solved year by year. Within each year the interest / debt /
# cash circularity is resolved by damped fixed-point iteration, which is the
# deterministic equivalent of switching iterative calculation on in Excel.
# =====================================================================================
def run_forecast(hist: HistoricalModel, assumptions: AssumptionSet) -> ModelOutput:
    """Build the fully linked five-year forecast from history plus assumptions."""
    years = [int(y) for y in assumptions.years]
    if not years:
        raise ValueError("No forecast years were specified.")
    settings = assumptions.settings
    base_year = hist.base_year
    opening = hist.opening_balances()

    # ---- opening position, carried forward from the last actual balance sheet --------
    prior = {
        "revenue": hist.value("P&L", "Revenue", base_year),
        "ppe": opening["PPE"],
        "intangibles": opening["Intangibles"],
        "investments": opening["Investments"],
        "inventory": opening["Inventory"],
        "receivables": opening["Receivables"],
        "oca": opening["OCA"],
        "cash": opening["Cash"],
        "borrowings": opening["Borrowings"],
        "lease": opening["Lease"],
        "payables": opening["Payables"],
        "ocl": opening["OCL"],
        "provisions": opening["Provisions"],
        "tax_payable": opening["TaxPayable"],
        "retained_earnings": opening["RE"],
    }
    share_capital = opening["ShareCapital"]
    other_reserves = opening["OtherReserves"]
    deferred_tax = opening["DTL"]
    # Any residue in the source accounts is parked explicitly and carried forward, so a
    # historical imbalance is disclosed rather than silently distorting the forecast.
    reconciliation_item = hist.value(
        "Balance Sheet", "Opening Reconciliation Item", base_year
    ) if settings.reconcile_opening_imbalance else 0.0

    pnl: Dict[int, Dict[str, float]] = {}
    bs: Dict[int, Dict[str, float]] = {}
    cf: Dict[int, Dict[str, float]] = {}
    ppe_sched: Dict[int, Dict[str, float]] = {}
    wc_sched: Dict[int, Dict[str, float]] = {}
    debt_sched: Dict[int, Dict[str, float]] = {}
    tax_sched: Dict[int, Dict[str, float]] = {}
    eq_sched: Dict[int, Dict[str, float]] = {}
    iterations: Dict[int, int] = {}
    converged_all = True

    for year in years:
        a = lambda key: assumptions.get(key, year)

        # -------------------------------------------------------------------------
        # 1. REVENUE  (the single upstream driver)
        # -------------------------------------------------------------------------
        revenue = prior["revenue"] * (1.0 + a("revenue_growth"))
        other_income = revenue * a("other_income_pct")

        # -------------------------------------------------------------------------
        # 2. OPERATING COSTS AND EBITDA
        # -------------------------------------------------------------------------
        cogs = revenue * a("cogs_pct")
        employee = revenue * a("employee_pct")
        other_opex = revenue * a("other_opex_pct")
        ebitda = revenue - cogs - employee - other_opex

        # -------------------------------------------------------------------------
        # 3. PPE SCHEDULE -> DEPRECIATION -> EBIT
        #    Depreciation is produced by the asset roll-forward, never by a
        #    percentage of revenue, and is used once only across all three statements.
        # -------------------------------------------------------------------------
        capex = revenue * a("capex_pct")
        disposals = max(prior["ppe"], 0.0) * a("disposal_pct")
        depreciation = compute_depreciation(
            settings.depreciation_method, prior["ppe"], capex, disposals,
            a("dep_rate"), settings.useful_life,
        )
        closing_ppe = prior["ppe"] + capex - disposals - depreciation

        amortisation = min(max(prior["intangibles"], 0.0) * a("amort_rate"),
                           max(prior["intangibles"], 0.0))
        closing_intangibles = prior["intangibles"] - amortisation
        total_da = depreciation + amortisation
        ebit = ebitda - total_da

        investment_purchases = revenue * a("investment_pct")
        closing_investments = prior["investments"] + investment_purchases

        # -------------------------------------------------------------------------
        # 4. WORKING CAPITAL SCHEDULE (operational drivers, not percentages of PAT)
        # -------------------------------------------------------------------------
        receivables = revenue * a("receivable_days") / 365.0
        inventory = cogs * a("inventory_days") / 365.0
        payables = cogs * a("payable_days") / 365.0
        oca = revenue * a("oca_pct")
        ocl = revenue * a("ocl_pct")
        provisions = revenue * a("provisions_pct")

        wc_closing = (receivables + inventory + oca) - (payables + ocl)
        wc_opening = (prior["receivables"] + prior["inventory"] + prior["oca"]) - (
            prior["payables"] + prior["ocl"])
        # Cash impact: an increase in net working capital consumes cash.
        wc_cash_impact = -(
            (receivables - prior["receivables"])
            + (inventory - prior["inventory"])
            + (oca - prior["oca"])
        ) + ((payables - prior["payables"]) + (ocl - prior["ocl"]))
        provisions_movement = provisions - prior["provisions"]

        # -------------------------------------------------------------------------
        # 5. DEBT, INTEREST, TAX, DIVIDEND AND CASH - solved simultaneously
        # -------------------------------------------------------------------------
        scheduled_repayment = min(
            max(prior["borrowings"], 0.0) * a("debt_repay_pct"),
            max(prior["borrowings"], 0.0),
        )
        planned_borrowing = max(a("new_borrowing"), 0.0)
        lease_repayment = min(
            max(prior["lease"], 0.0) * a("lease_repay_pct"), max(prior["lease"], 0.0))
        closing_lease = prior["lease"] - lease_repayment
        lease_interest = max(prior["lease"], 0.0) * a("lease_rate")

        plug = 0.0
        used_iterations = 0
        year_converged = False
        solved: Dict[str, float] = {}

        for iteration in range(1, MAX_ITERATIONS + 1):
            used_iterations = iteration
            closing_borrowings = (prior["borrowings"] + planned_borrowing + plug
                                  - scheduled_repayment)
            average_borrowings = 0.5 * (prior["borrowings"] + closing_borrowings)
            interest_on_debt = max(average_borrowings, 0.0) * a("interest_rate")
            finance_cost = interest_on_debt + lease_interest

            pbt = ebit + other_income - finance_cost
            if settings.tax_credit_on_loss:
                tax_expense = pbt * a("tax_rate")
            else:
                tax_expense = max(pbt, 0.0) * a("tax_rate")
            pat = pbt - tax_expense

            closing_tax_payable = max(tax_expense, 0.0) * a("tax_payable_pct")
            tax_paid = prior["tax_payable"] + tax_expense - closing_tax_payable
            tax_payable_movement = closing_tax_payable - prior["tax_payable"]

            dividends = max(pat, 0.0) * a("dividend_payout")

            other_non_cash = provisions_movement + tax_payable_movement
            cfo = pat + total_da + wc_cash_impact + other_non_cash
            cfi = -capex + disposals - investment_purchases
            cff = (planned_borrowing + plug - scheduled_repayment - lease_repayment
                   - dividends)
            net_change = cfo + cfi + cff
            closing_cash = prior["cash"] + net_change

            # Funding plug: raise debt only to the extent cash would otherwise fall
            # below the stated minimum. Surplus cash is allowed to accumulate.
            if settings.cash_sweep:
                shortfall = settings.minimum_cash - closing_cash
                target_plug = max(0.0, plug + shortfall)
            else:
                target_plug = 0.0

            solved = {
                "finance_cost": finance_cost, "interest_on_debt": interest_on_debt,
                "pbt": pbt, "tax_expense": tax_expense, "pat": pat,
                "closing_tax_payable": closing_tax_payable, "tax_paid": tax_paid,
                "tax_payable_movement": tax_payable_movement, "dividends": dividends,
                "cfo": cfo, "cfi": cfi, "cff": cff, "net_change": net_change,
                "closing_cash": closing_cash, "closing_borrowings": closing_borrowings,
                "average_borrowings": average_borrowings, "plug": plug,
                "other_non_cash": other_non_cash,
            }

            if abs(target_plug - plug) < 1e-7:
                year_converged = True
                break
            plug = plug + DAMPING * (target_plug - plug)

        if not year_converged:
            converged_all = False
        iterations[year] = used_iterations

        # -------------------------------------------------------------------------
        # 6. EQUITY ROLL-FORWARD
        # -------------------------------------------------------------------------
        opening_re = prior["retained_earnings"]
        oci = 0.0
        closing_re = opening_re + solved["pat"] - solved["dividends"] + oci
        closing_equity = share_capital + closing_re + other_reserves

        # -------------------------------------------------------------------------
        # 7. WRITE THE THREE STATEMENTS
        # -------------------------------------------------------------------------
        pnl[year] = {
            "Revenue": revenue,
            "Other Income": other_income,
            "Cost of Goods Sold": cogs,
            "Employee Cost": employee,
            "Other Operating Expenses": other_opex,
            "EBITDA": ebitda,
            "Depreciation & Amortisation": total_da,
            "EBIT": ebit,
            "Finance Cost": solved["finance_cost"],
            "PBT": solved["pbt"],
            "Tax Expense": solved["tax_expense"],
            "PAT": solved["pat"],
        }

        total_assets = (closing_ppe + closing_intangibles + closing_investments
                        + inventory + receivables + oca + solved["closing_cash"])
        total_liabilities = (solved["closing_borrowings"] + closing_lease + deferred_tax
                             + payables + ocl + provisions
                             + solved["closing_tax_payable"] + reconciliation_item)
        bs[year] = {
            "Property, Plant and Equipment": closing_ppe,
            "Intangible Assets": closing_intangibles,
            "Investments": closing_investments,
            "Inventory": inventory,
            "Trade Receivables": receivables,
            "Other Current Assets": oca,
            "Cash and Cash Equivalents": solved["closing_cash"],
            "Total Assets": total_assets,
            "Share Capital": share_capital,
            "Retained Earnings": closing_re,
            "Other Reserves": other_reserves,
            "Total Equity": closing_equity,
            "Borrowings": solved["closing_borrowings"],
            "Lease Liabilities": closing_lease,
            "Deferred Tax Liability": deferred_tax,
            "Trade Payables": payables,
            "Other Current Liabilities": ocl,
            "Provisions": provisions,
            "Current Tax Payable": solved["closing_tax_payable"],
            "Opening Reconciliation Item": reconciliation_item,
            "Total Liabilities": total_liabilities,
            "Total Equity and Liabilities": closing_equity + total_liabilities,
            "Balance Check": total_assets - closing_equity - total_liabilities,
        }

        cf[year] = {
            "PAT": solved["pat"],
            "Depreciation & Amortisation": total_da,
            "Change in Working Capital": wc_cash_impact,
            "Other Non-Cash Movements": solved["other_non_cash"],
            "Cash Flow from Operating Activities": solved["cfo"],
            "Capital Expenditure": -capex,
            "Proceeds from Disposals": disposals,
            "Purchase of Investments": -investment_purchases,
            "Cash Flow from Investing Activities": solved["cfi"],
            "New Borrowings": planned_borrowing + solved["plug"],
            "Repayment of Borrowings": -scheduled_repayment,
            "Lease Principal Repayment": -lease_repayment,
            "Dividends Paid": -solved["dividends"],
            "Cash Flow from Financing Activities": solved["cff"],
            "Net Change in Cash": solved["net_change"],
            "Opening Cash": prior["cash"],
            "Closing Cash": solved["closing_cash"],
        }

        # -------------------------------------------------------------------------
        # 8. SUPPORTING SCHEDULES
        # -------------------------------------------------------------------------
        ppe_sched[year] = {
            "Opening PPE": prior["ppe"],
            "Capex": capex,
            "Disposals": -disposals,
            "Depreciation Charge": -depreciation,
            "Closing PPE": closing_ppe,
            "Opening Intangibles": prior["intangibles"],
            "Amortisation": -amortisation,
            "Closing Intangibles": closing_intangibles,
            "Total D&A charged to P&L": total_da,
            "Capex / Revenue (%)": _safe_divide(capex, revenue) * 100.0,
        }
        wc_sched[year] = {
            "Trade Receivables": receivables,
            "Inventory": inventory,
            "Other Current Assets": oca,
            "Trade Payables": payables,
            "Other Current Liabilities": ocl,
            "Net Working Capital": wc_closing,
            "Opening Net Working Capital": wc_opening,
            "Movement in Net Working Capital": wc_closing - wc_opening,
            "Cash impact of working capital": wc_cash_impact,
            "Receivable days": a("receivable_days"),
            "Inventory days": a("inventory_days"),
            "Payable days": a("payable_days"),
            "Working capital / Revenue (%)": _safe_divide(wc_closing, revenue) * 100.0,
        }
        debt_sched[year] = {
            "Opening Debt": prior["borrowings"],
            "Planned New Borrowing": planned_borrowing,
            "Funding Plug Drawdown": solved["plug"],
            "Scheduled Repayment": -scheduled_repayment,
            "Closing Debt": solved["closing_borrowings"],
            "Average Debt": solved["average_borrowings"],
            "Interest on Borrowings": solved["interest_on_debt"],
            "Opening Lease Liability": prior["lease"],
            "Lease Repayment": -lease_repayment,
            "Closing Lease Liability": closing_lease,
            "Lease Interest": lease_interest,
            "Total Finance Cost": solved["finance_cost"],
            "Minimum Cash Requirement": settings.minimum_cash,
            "Closing Cash": solved["closing_cash"],
        }
        tax_sched[year] = {
            "PBT": solved["pbt"],
            "Tax rate applied (%)": a("tax_rate") * 100.0,
            "Tax Expense": solved["tax_expense"],
            "Opening Tax Payable": prior["tax_payable"],
            "Tax Paid": -solved["tax_paid"],
            "Closing Tax Payable": solved["closing_tax_payable"],
            "Effective tax rate (%)": _safe_divide(
                solved["tax_expense"], solved["pbt"]) * 100.0,
        }
        eq_sched[year] = {
            "Opening Retained Earnings": opening_re,
            "PAT": solved["pat"],
            "Dividends": -solved["dividends"],
            "Other Comprehensive Income": oci,
            "Closing Retained Earnings": closing_re,
            "Share Capital": share_capital,
            "Other Reserves": other_reserves,
            "Closing Total Equity": closing_equity,
            "Dividend payout applied (%)": a("dividend_payout") * 100.0,
        }

        # -------------------------------------------------------------------------
        # 9. ROLL FORWARD INTO THE NEXT YEAR
        # -------------------------------------------------------------------------
        prior = {
            "revenue": revenue,
            "ppe": closing_ppe,
            "intangibles": closing_intangibles,
            "investments": closing_investments,
            "inventory": inventory,
            "receivables": receivables,
            "oca": oca,
            "cash": solved["closing_cash"],
            "borrowings": solved["closing_borrowings"],
            "lease": closing_lease,
            "payables": payables,
            "ocl": ocl,
            "provisions": provisions,
            "tax_payable": solved["closing_tax_payable"],
            "retained_earnings": closing_re,
        }

    def build(payload: Dict[int, Dict[str, float]], order: List[str]) -> pd.DataFrame:
        frame = pd.DataFrame(payload)
        frame.columns = [int(c) for c in frame.columns]
        ordered = [i for i in order if i in frame.index]
        extra = [i for i in frame.index if i not in ordered]
        return frame.reindex(ordered + extra).astype(float)

    output = ModelOutput(
        company=hist.company,
        years=years,
        base_year=base_year,
        scenario=assumptions.scenario,
        pnl=build(pnl, PNL_ROWS),
        balance_sheet=build(bs, BS_ROWS),
        cash_flow=build(cf, CF_ROWS),
        ppe_schedule=build(ppe_sched, [
            "Opening PPE", "Capex", "Disposals", "Depreciation Charge", "Closing PPE",
            "Opening Intangibles", "Amortisation", "Closing Intangibles",
            "Total D&A charged to P&L", "Capex / Revenue (%)"]),
        working_capital_schedule=build(wc_sched, [
            "Trade Receivables", "Inventory", "Other Current Assets", "Trade Payables",
            "Other Current Liabilities", "Net Working Capital",
            "Opening Net Working Capital", "Movement in Net Working Capital",
            "Cash impact of working capital", "Receivable days", "Inventory days",
            "Payable days", "Working capital / Revenue (%)"]),
        debt_schedule=build(debt_sched, [
            "Opening Debt", "Planned New Borrowing", "Funding Plug Drawdown",
            "Scheduled Repayment", "Closing Debt", "Average Debt",
            "Interest on Borrowings", "Opening Lease Liability", "Lease Repayment",
            "Closing Lease Liability", "Lease Interest", "Total Finance Cost",
            "Minimum Cash Requirement", "Closing Cash"]),
        tax_schedule=build(tax_sched, [
            "PBT", "Tax rate applied (%)", "Tax Expense", "Opening Tax Payable",
            "Tax Paid", "Closing Tax Payable", "Effective tax rate (%)"]),
        equity_schedule=build(eq_sched, EQUITY_ROWS + ["Dividend payout applied (%)"]),
        iterations=iterations,
        converged=converged_all,
        assumptions=assumptions.copy(),
    )
    output.ratios = forecast_ratios(hist, output)
    output.checks = run_model_checks(hist, output)
    return output


# =====================================================================================
# PART 3.5  COMBINED HISTORICAL + FORECAST VIEWS AND RATIOS
# =====================================================================================
def combined_model(hist: HistoricalModel, output: ModelOutput) -> HistoricalModel:
    """Splice history and forecast into one container so ratios span both periods."""
    years = [int(y) for y in hist.years] + [int(y) for y in output.years]

    def splice(left: pd.DataFrame, right: pd.DataFrame,
               order: List[str]) -> pd.DataFrame:
        index = list(dict.fromkeys(order + list(left.index) + list(right.index)))
        a = left.reindex(index=index).astype(float)
        b = right.reindex(index=index).astype(float)
        frame = pd.concat([a, b], axis=1)
        frame.columns = [int(c) for c in frame.columns]
        return frame.reindex(columns=years).fillna(0.0)

    return HistoricalModel(
        company=hist.company,
        years=years,
        pnl=splice(hist.pnl, output.pnl, PNL_ROWS),
        balance_sheet=splice(hist.balance_sheet, output.balance_sheet, BS_ROWS),
        cash_flow=splice(hist.cash_flow, output.cash_flow, CF_ROWS),
        unit=BASE_UNIT,
    )


def forecast_ratios(hist: HistoricalModel, output: ModelOutput) -> pd.DataFrame:
    """Forecast-period ratios, computed on the same basis as the historical analysis."""
    combined = combined_model(hist, output)
    ratios = historical_ratios(combined)
    return ratios.reindex(columns=[int(y) for y in output.years])


def combined_ratios(hist: HistoricalModel, output: ModelOutput) -> pd.DataFrame:
    """Ratios across history and forecast, used by the dashboard charts."""
    return historical_ratios(combined_model(hist, output))


def dashboard_series(hist: HistoricalModel, output: ModelOutput,
                     view: str = "Historical + forecast") -> Dict[str, pd.Series]:
    """The eight chart series required by the management dashboard."""
    combined = combined_model(hist, output)
    ratios = historical_ratios(combined)
    if view == "Historical only":
        years = [int(y) for y in hist.years]
    elif view == "Forecast only":
        years = [int(y) for y in output.years]
    else:
        years = [int(y) for y in combined.years]

    def take(series: pd.Series) -> pd.Series:
        return series.reindex(years).astype(float)

    cfo = combined.cash_flow.loc["Cash Flow from Operating Activities"] \
        if "Cash Flow from Operating Activities" in combined.cash_flow.index \
        else pd.Series(dtype=float)
    capex = combined.cash_flow.loc["Capital Expenditure"].abs() \
        if "Capital Expenditure" in combined.cash_flow.index else pd.Series(dtype=float)

    return {
        "Revenue": take(combined.pnl.loc["Revenue"]),
        "EBITDA": take(combined.pnl.loc["EBITDA"]),
        "EBITDA margin": take(ratios.loc["EBITDA margin"]),
        "PAT": take(combined.pnl.loc["PAT"]),
        "CFO": take(cfo),
        "Capex": take(capex),
        "Closing cash": take(combined.balance_sheet.loc["Cash and Cash Equivalents"]),
        "Net debt": take(ratios.loc["Net debt"]),
        "Working capital": take(ratios.loc["Working capital"]),
        "Revenue growth": take(ratios.loc["Revenue growth"]),
        "Free cash flow": take(ratios.loc["Free cash flow"]),
    }


def kpi_cards(hist: HistoricalModel, output: ModelOutput) -> List[Tuple[str, str, str]]:
    """KPI cards for the terminal forecast year: (label, value, supporting note)."""
    year = output.terminal_year
    ratios = output.ratios
    label = f"FY{str(year)[-2:]}"

    def ratio(name: str) -> float:
        if name in ratios.index and year in ratios.columns:
            raw = ratios.loc[name, year]
            return float("nan") if pd.isna(raw) else float(raw)
        return float("nan")

    revenue = output.value("P&L", "Revenue", year)
    ebitda = output.value("P&L", "EBITDA", year)
    pat = output.value("P&L", "PAT", year)
    cash = output.value("Balance Sheet", "Cash and Cash Equivalents", year)
    cfo = output.value("Cash Flow", "Cash Flow from Operating Activities", year)
    base_revenue = hist.value("P&L", "Revenue", hist.base_year)
    revenue_cagr = cagr(pd.Series({0: base_revenue, 1: revenue})) if base_revenue else 0.0
    span = len(output.years)
    overall = ((revenue / base_revenue) ** (1.0 / span) - 1.0) if base_revenue > 0 else 0.0

    return [
        (f"Revenue {label}", f"{revenue:,.0f}",
         f"CAGR from FY{str(hist.base_year)[-2:]}: {overall * 100:,.1f}%"),
        (f"EBITDA {label}", f"{ebitda:,.0f}", "Rs lakh"),
        (f"EBITDA margin {label}", f"{ratio('EBITDA margin') * 100:,.1f}%",
         "EBITDA / Revenue"),
        (f"PAT {label}", f"{pat:,.0f}",
         f"PAT margin {ratio('PAT margin') * 100:,.1f}%"),
        (f"Closing cash {label}", f"{cash:,.0f}",
         f"Minimum required {output.assumptions.settings.minimum_cash:,.0f}"
         if output.assumptions else "Rs lakh"),
        (f"Net debt {label}", f"{ratio('Net debt'):,.0f}",
         f"Net debt / EBITDA {ratio('Net debt / EBITDA'):,.2f}x"),
        (f"CFO {label}", f"{cfo:,.0f}",
         f"CFO / EBITDA {ratio('CFO / EBITDA') * 100:,.0f}%"),
        (f"Free cash flow {label}", f"{ratio('Free cash flow'):,.0f}",
         f"FCF / Revenue {ratio('FCF / Revenue') * 100:,.1f}%"),
    ]


# =====================================================================================
# PART 3.6  MODEL CHECKS
# =====================================================================================
def _status(condition: bool, warn_only: bool = False) -> str:
    if condition:
        return "PASS"
    return "WARNING" if warn_only else "ERROR"


def run_model_checks(hist: HistoricalModel, output: ModelOutput) -> pd.DataFrame:
    """Every integrity check. Nothing is smoothed over or hidden."""
    rows: List[Tuple[str, str, str, str]] = []
    years = output.years

    # ---- 1. balance sheet balances --------------------------------------------------
    worst = 0.0
    worst_year = years[0]
    for year in years:
        residue = output.value("Balance Sheet", "Balance Check", year)
        if abs(residue) > abs(worst):
            worst, worst_year = residue, year
    rows.append((
        "Balance Sheet balances",
        "Integrity",
        _status(abs(worst) <= TOL),
        "Model Balanced across every forecast year"
        if abs(worst) <= TOL
        else f"Model Out of Balance by Rs {worst:,.2f} lakh in FY{worst_year}",
    ))

    # ---- 2. cash flow reconciles to the balance sheet -------------------------------
    gaps = []
    for year in years:
        cf_cash = output.value("Cash Flow", "Closing Cash", year)
        bs_cash = output.value("Balance Sheet", "Cash and Cash Equivalents", year)
        if abs(cf_cash - bs_cash) > TOL:
            gaps.append(f"FY{year} differs by Rs {cf_cash - bs_cash:,.2f} lakh")
    rows.append((
        "Cash flow closing cash equals Balance Sheet cash", "Integrity",
        _status(not gaps),
        "Reconciled in every year" if not gaps else "; ".join(gaps),
    ))

    # ---- 3. CFO + CFI + CFF equals the movement in cash ----------------------------
    gaps = []
    for year in years:
        total = (output.value("Cash Flow", "Cash Flow from Operating Activities", year)
                 + output.value("Cash Flow", "Cash Flow from Investing Activities", year)
                 + output.value("Cash Flow", "Cash Flow from Financing Activities", year))
        movement = (output.value("Cash Flow", "Closing Cash", year)
                    - output.value("Cash Flow", "Opening Cash", year))
        if abs(total - movement) > TOL:
            gaps.append(f"FY{year}")
    rows.append((
        "Cash flow statement internally consistent", "Integrity", _status(not gaps),
        "CFO + CFI + CFF equals the movement in cash"
        if not gaps else "Mismatch in " + ", ".join(gaps),
    ))

    # ---- 4. retained earnings roll-forward -----------------------------------------
    gaps = []
    for year in years:
        opening = output.value("Equity Schedule", "Opening Retained Earnings", year)
        pat = output.value("Equity Schedule", "PAT", year)
        dividends = output.value("Equity Schedule", "Dividends", year)
        oci = output.value("Equity Schedule", "Other Comprehensive Income", year)
        closing = output.value("Equity Schedule", "Closing Retained Earnings", year)
        bs_closing = output.value("Balance Sheet", "Retained Earnings", year)
        if abs(opening + pat + dividends + oci - closing) > TOL \
                or abs(closing - bs_closing) > TOL:
            gaps.append(f"FY{year}")
    rows.append((
        "Retained earnings reconcile", "Roll-forward", _status(not gaps),
        "Opening + PAT - dividends + OCI equals closing, and agrees to the Balance Sheet"
        if not gaps else "Mismatch in " + ", ".join(gaps),
    ))

    # ---- 5. PPE roll-forward -------------------------------------------------------
    gaps = []
    for year in years:
        opening = output.value("PPE Schedule", "Opening PPE", year)
        capex = output.value("PPE Schedule", "Capex", year)
        disposals = output.value("PPE Schedule", "Disposals", year)
        charge = output.value("PPE Schedule", "Depreciation Charge", year)
        closing = output.value("PPE Schedule", "Closing PPE", year)
        bs_closing = output.value("Balance Sheet", "Property, Plant and Equipment", year)
        if abs(opening + capex + disposals + charge - closing) > TOL \
                or abs(closing - bs_closing) > TOL:
            gaps.append(f"FY{year}")
    rows.append((
        "PPE roll-forward reconciles", "Roll-forward", _status(not gaps),
        "Opening + capex - disposals - depreciation equals closing PPE on the "
        "Balance Sheet" if not gaps else "Mismatch in " + ", ".join(gaps),
    ))

    # ---- 6. depreciation used once only -------------------------------------------
    gaps = []
    for year in years:
        pnl_da = output.value("P&L", "Depreciation & Amortisation", year)
        cf_da = output.value("Cash Flow", "Depreciation & Amortisation", year)
        sched_da = output.value("PPE Schedule", "Total D&A charged to P&L", year)
        if abs(pnl_da - cf_da) > TOL or abs(pnl_da - sched_da) > TOL:
            gaps.append(f"FY{year}")
    rows.append((
        "Depreciation consistent across P&L, cash flow and schedule", "Integrity",
        _status(not gaps),
        "A single depreciation figure flows to all three statements"
        if not gaps else "Mismatch in " + ", ".join(gaps),
    ))

    # ---- 7. debt roll-forward ------------------------------------------------------
    gaps = []
    for year in years:
        opening = output.value("Debt Schedule", "Opening Debt", year)
        planned = output.value("Debt Schedule", "Planned New Borrowing", year)
        plug = output.value("Debt Schedule", "Funding Plug Drawdown", year)
        repayment = output.value("Debt Schedule", "Scheduled Repayment", year)
        closing = output.value("Debt Schedule", "Closing Debt", year)
        bs_closing = output.value("Balance Sheet", "Borrowings", year)
        if abs(opening + planned + plug + repayment - closing) > TOL \
                or abs(closing - bs_closing) > TOL:
            gaps.append(f"FY{year}")
    rows.append((
        "Debt roll-forward reconciles", "Roll-forward", _status(not gaps),
        "Opening + drawdowns - repayments equals closing debt on the Balance Sheet"
        if not gaps else "Mismatch in " + ", ".join(gaps),
    ))

    # ---- 8. finance cost linked to the debt schedule -------------------------------
    gaps = []
    for year in years:
        if abs(output.value("P&L", "Finance Cost", year)
               - output.value("Debt Schedule", "Total Finance Cost", year)) > TOL:
            gaps.append(f"FY{year}")
    rows.append((
        "Finance cost linked to the debt schedule", "Integrity", _status(not gaps),
        "Interest is derived from average debt and the assumed rate"
        if not gaps else "Mismatch in " + ", ".join(gaps),
    ))

    # ---- 9. tax schedule -----------------------------------------------------------
    gaps = []
    for year in years:
        opening = output.value("Tax Schedule", "Opening Tax Payable", year)
        expense = output.value("Tax Schedule", "Tax Expense", year)
        paid = output.value("Tax Schedule", "Tax Paid", year)
        closing = output.value("Tax Schedule", "Closing Tax Payable", year)
        bs_closing = output.value("Balance Sheet", "Current Tax Payable", year)
        pnl_tax = output.value("P&L", "Tax Expense", year)
        if abs(opening + expense + paid - closing) > TOL \
                or abs(closing - bs_closing) > TOL or abs(expense - pnl_tax) > TOL:
            gaps.append(f"FY{year}")
    rows.append((
        "Tax schedule reconciles", "Roll-forward", _status(not gaps),
        "Opening payable + expense - tax paid equals closing payable, which agrees to "
        "the Balance Sheet" if not gaps else "Mismatch in " + ", ".join(gaps),
    ))

    # ---- 10. working capital movement flows to cash flow ---------------------------
    gaps = []
    for year in years:
        if abs(output.value("Working Capital Schedule",
                            "Cash impact of working capital", year)
               - output.value("Cash Flow", "Change in Working Capital", year)) > TOL:
            gaps.append(f"FY{year}")
    rows.append((
        "Working capital movement flows to cash flow", "Integrity", _status(not gaps),
        "The schedule movement is the cash flow line"
        if not gaps else "Mismatch in " + ", ".join(gaps),
    ))

    # ---- 11. no unexpected negative balances --------------------------------------
    negatives: List[str] = []
    watch = ["Cash and Cash Equivalents", "Trade Receivables", "Inventory",
             "Trade Payables", "Property, Plant and Equipment", "Total Equity",
             "Borrowings"]
    for year in years:
        for item in watch:
            value = output.value("Balance Sheet", item, year)
            if value < -TOL:
                negatives.append(f"{item} FY{year} at Rs {value:,.0f} lakh")
    rows.append((
        "No unexpected negative balances", "Plausibility",
        "PASS" if not negatives else "ERROR",
        "All monitored balances are non-negative"
        if not negatives else "; ".join(negatives[:6]),
    ))

    # ---- 12. minimum cash respected ------------------------------------------------
    settings = output.assumptions.settings if output.assumptions else ModelSettings()
    breaches = [f"FY{y}" for y in years
                if output.value("Balance Sheet", "Cash and Cash Equivalents", y)
                < settings.minimum_cash - TOL]
    if settings.cash_sweep:
        rows.append((
            "Minimum cash balance maintained", "Funding",
            _status(not breaches),
            f"Cash stays at or above Rs {settings.minimum_cash:,.0f} lakh, funded by the "
            f"plug where required" if not breaches
            else "Below the minimum in " + ", ".join(breaches),
        ))
    else:
        rows.append((
            "Minimum cash balance maintained", "Funding",
            "PASS" if not breaches else "WARNING",
            "Funding plug is switched OFF; cash is left to find its own level. "
            + ("No shortfall arises." if not breaches
               else "Shortfall in " + ", ".join(breaches)),
        ))

    # ---- 13. structural checks -----------------------------------------------------
    continuous = years == list(range(years[0], years[-1] + 1))
    rows.append((
        "Forecast years are continuous", "Structure", _status(continuous, True),
        ", ".join(f"FY{y}" for y in years),
    ))
    rows.append((
        "Forecast begins in the year after the last actual", "Structure",
        _status(years[0] == hist.base_year + 1, True),
        f"Last actual FY{hist.base_year}, first forecast FY{years[0]}",
    ))
    hist_continuous = hist.years == list(range(hist.years[0], hist.years[-1] + 1))
    rows.append((
        "Historical years correctly identified", "Structure",
        _status(hist_continuous, True),
        ", ".join(f"FY{y}" for y in hist.years),
    ))
    missing: List[str] = []
    for statement in ("P&L", "Balance Sheet", "Cash Flow"):
        missing += [f"{statement}: {i}" for i in REQUIRED_HIST[statement]
                    if not hist.has(statement, i)]
    rows.append((
        "Required historical line items exist", "Structure",
        _status(not missing, True),
        "All required line items were located"
        if not missing else "Derived or nil: " + "; ".join(missing),
    ))

    # ---- 14. solver convergence and plausibility ----------------------------------
    rows.append((
        "Circularity solver converged", "Integrity", _status(output.converged),
        f"Maximum {max(output.iterations.values()) if output.iterations else 0} "
        f"iterations used to resolve interest, debt and cash"
        if output.converged else "The solver did not converge; review the assumptions",
    ))
    ratios = output.ratios
    if "Interest coverage (EBIT / Finance cost)" in ratios.index:
        thin = [f"FY{y}" for y in years
                if not pd.isna(ratios.loc["Interest coverage (EBIT / Finance cost)", y])
                and float(ratios.loc["Interest coverage (EBIT / Finance cost)", y]) < 2.0]
        rows.append((
            "Interest coverage above 2.0x", "Plausibility",
            "PASS" if not thin else "WARNING",
            "Coverage is comfortable throughout"
            if not thin else "Coverage below 2.0x in " + ", ".join(thin),
        ))
    losses = [f"FY{y}" for y in years if output.value("P&L", "PAT", y) < 0]
    rows.append((
        "Profitable in every forecast year", "Plausibility",
        "PASS" if not losses else "WARNING",
        "PAT is positive throughout"
        if not losses else "Loss forecast in " + ", ".join(losses),
    ))

    return pd.DataFrame(rows, columns=["Check", "Category", "Status", "Detail"])


def has_critical_errors(checks: pd.DataFrame) -> bool:
    if checks is None or checks.empty:
        return False
    return bool((checks["Status"] == "ERROR").any())


def check_counts(checks: pd.DataFrame) -> Tuple[int, int, int]:
    if checks is None or checks.empty:
        return 0, 0, 0
    counts = checks["Status"].value_counts()
    return (int(counts.get("PASS", 0)), int(counts.get("WARNING", 0)),
            int(counts.get("ERROR", 0)))

# =====================================================================================
# PART 3.7  SENSITIVITY ANALYSIS
# =====================================================================================
SENSITIVITY_METRICS: Tuple[str, ...] = (
    "EBITDA",
    "Closing cash",
    "PAT",
    "Net debt",
    "Free cash flow",
    "EBITDA margin",
)

METRIC_KIND: Dict[str, str] = {
    "EBITDA": "amount",
    "Closing cash": "amount",
    "PAT": "amount",
    "Net debt": "amount",
    "Free cash flow": "amount",
    "EBITDA margin": "percent",
}


def _metric_value(output: ModelOutput, metric: str) -> float:
    """Pull one headline metric for the terminal forecast year."""
    year = output.terminal_year
    if metric == "EBITDA":
        return output.value("P&L", "EBITDA", year)
    if metric == "PAT":
        return output.value("P&L", "PAT", year)
    if metric == "Closing cash":
        return output.value("Balance Sheet", "Cash and Cash Equivalents", year)
    ratios = output.ratios
    if metric in ratios.index and year in ratios.columns:
        raw = ratios.loc[metric, year]
        return float("nan") if pd.isna(raw) else float(raw)
    return float("nan")


def _shift(assumptions: AssumptionSet, key: str, delta: float) -> AssumptionSet:
    """Return a copy with one assumption shifted by the same delta in every year."""
    shifted = assumptions.copy()
    if abs(delta) > 0:
        for year in shifted.years:
            shifted.set(key, year, shifted.get(key, year) + delta)
    return shifted


def _delta_label(key: str, base_value: float, delta: float) -> str:
    """Label a sensitivity axis by the resulting assumption level, not the delta."""
    spec = PARAMS[key]
    level = spec.clamp(base_value + delta)
    if spec.kind == "percent":
        return f"{level * 100:,.1f}%"
    if spec.kind == "days":
        return f"{level:,.0f}d"
    return f"{level:,.0f}"


def sensitivity_table(hist: HistoricalModel, assumptions: AssumptionSet,
                      row_key: str, row_deltas: List[float],
                      col_key: str, col_deltas: List[float],
                      metric: str = "EBITDA") -> pd.DataFrame:
    """Two-way sensitivity grid, re-running the whole integrated model for each cell."""
    if row_key not in PARAMS or col_key not in PARAMS:
        raise ValueError("Unknown sensitivity driver.")

    first_year = assumptions.years[0]
    row_base = assumptions.get(row_key, first_year)
    col_base = assumptions.get(col_key, first_year)

    grid: List[List[float]] = []
    for row_delta in row_deltas:
        line: List[float] = []
        for col_delta in col_deltas:
            trial = _shift(_shift(assumptions, row_key, row_delta), col_key, col_delta)
            try:
                line.append(_metric_value(run_forecast(hist, trial), metric))
            except Exception:
                line.append(float("nan"))
        grid.append(line)

    index = [_delta_label(row_key, row_base, d) for d in row_deltas]
    columns = [_delta_label(col_key, col_base, d) for d in col_deltas]
    frame = pd.DataFrame(grid, index=index, columns=columns)
    frame.index.name = PARAMS[row_key].label
    frame.columns.name = PARAMS[col_key].label
    return frame


# Standard grids offered on the sensitivity page.
STANDARD_SENSITIVITIES: List[Dict[str, Any]] = [
    {
        "title": "Revenue growth vs EBITDA margin - FY31 EBITDA",
        "row_key": "revenue_growth",
        "row_deltas": [-0.04, -0.02, 0.0, 0.02, 0.04],
        "col_key": "cogs_pct",
        "col_deltas": [0.02, 0.01, 0.0, -0.01, -0.02],
        "metric": "EBITDA",
    },
    {
        "title": "Revenue growth vs closing cash - FY31 closing cash",
        "row_key": "revenue_growth",
        "row_deltas": [-0.04, -0.02, 0.0, 0.02, 0.04],
        "col_key": "receivable_days",
        "col_deltas": [10.0, 5.0, 0.0, -5.0, -10.0],
        "metric": "Closing cash",
    },
    {
        "title": "EBITDA margin vs closing cash - FY31 closing cash",
        "row_key": "cogs_pct",
        "row_deltas": [0.02, 0.01, 0.0, -0.01, -0.02],
        "col_key": "capex_pct",
        "col_deltas": [0.02, 0.01, 0.0, -0.01, -0.02],
        "metric": "Closing cash",
    },
]


def heatmap_colour(value: float, low: float, high: float) -> Tuple[int, int, int]:
    """Red to amber to green interpolation used to shade the sensitivity grids."""
    if pd.isna(value) or high - low < 1e-9:
        return (245, 245, 245)
    position = min(max((float(value) - low) / (high - low), 0.0), 1.0)
    if position < 0.5:
        ratio = position / 0.5
        red = 214 + int((250 - 214) * ratio)
        green = 96 + int((190 - 96) * ratio)
        blue = 77 + int((110 - 77) * ratio)
    else:
        ratio = (position - 0.5) / 0.5
        red = 250 - int((250 - 84) * ratio)
        green = 190 - int((190 - 158) * ratio)
        blue = 110 - int((110 - 90) * ratio)
    return (red, green, blue)


def format_metric(value: float, metric: str) -> str:
    kind = METRIC_KIND.get(metric, "amount")
    if pd.isna(value):
        return "-"
    if kind == "percent":
        return f"{float(value) * 100:,.1f}%"
    return f"{float(value):,.0f}"


# =====================================================================================
# PART 3.8  EXCEL EXPORT
# =====================================================================================
XL_TITLE_FILL = PatternFill("solid", fgColor="1F3864")
XL_HEADER_FILL = PatternFill("solid", fgColor="2E75B6")
XL_SUBTOTAL_FILL = PatternFill("solid", fgColor="DDEBF7")
XL_LABEL_FILL = PatternFill("solid", fgColor="F2F2F2")
XL_PASS_FILL = PatternFill("solid", fgColor="C6EFCE")
XL_WARN_FILL = PatternFill("solid", fgColor="FFEB9C")
XL_ERROR_FILL = PatternFill("solid", fgColor="FFC7CE")

XL_TITLE_FONT = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
XL_HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
XL_BOLD = Font(name="Calibri", size=11, bold=True)
XL_NORMAL = Font(name="Calibri", size=11)
XL_NOTE = Font(name="Calibri", size=9, italic=True, color="595959")

XL_THIN = Side(style="thin", color="BFBFBF")
XL_BORDER = Border(left=XL_THIN, right=XL_THIN, top=XL_THIN, bottom=XL_THIN)

NUMBER_FORMAT = '#,##0;[Red](#,##0)'
DECIMAL_FORMAT = '#,##0.0;[Red](#,##0.0)'

SUBTOTAL_ITEMS = {
    "EBITDA", "EBIT", "PBT", "PAT", "Total Assets", "Total Equity", "Total Liabilities",
    "Total Equity and Liabilities", "Balance Check", "Closing PPE", "Closing Debt",
    "Closing Tax Payable", "Closing Retained Earnings", "Closing Total Equity",
    "Net Working Capital", "Cash Flow from Operating Activities",
    "Cash Flow from Investing Activities", "Cash Flow from Financing Activities",
    "Net Change in Cash", "Closing Cash", "Closing Intangibles",
    "Closing Lease Liability", "Total Finance Cost", "Total D&A charged to P&L",
}


def _sheet_title(worksheet, text: str, span: int, subtitle: str = "") -> int:
    """Write a banner across the top of a worksheet. Returns the next free row."""
    worksheet.merge_cells(start_row=1, start_column=1, end_row=1,
                          end_column=max(span, 2))
    cell = worksheet.cell(row=1, column=1, value=text)
    cell.fill = XL_TITLE_FILL
    cell.font = XL_TITLE_FONT
    cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    worksheet.row_dimensions[1].height = 26
    if subtitle:
        worksheet.merge_cells(start_row=2, start_column=1, end_row=2,
                              end_column=max(span, 2))
        note = worksheet.cell(row=2, column=1, value=subtitle)
        note.font = XL_NOTE
        note.alignment = Alignment(horizontal="left", indent=1)
        return 4
    return 3


def _write_frame(worksheet, frame: pd.DataFrame, start_row: int,
                 label_header: str = "Rs lakh", decimals: bool = False,
                 label_width: int = 42) -> int:
    """Write a DataFrame as a formatted table. Returns the row after the table."""
    if frame is None or frame.empty:
        worksheet.cell(row=start_row, column=1,
                       value="No data available.").font = XL_NOTE
        return start_row + 2

    columns = list(frame.columns)
    header_row = start_row

    cell = worksheet.cell(row=header_row, column=1, value=label_header)
    cell.fill = XL_HEADER_FILL
    cell.font = XL_HEADER_FONT
    cell.border = XL_BORDER
    cell.alignment = Alignment(horizontal="left", indent=1)

    for offset, column in enumerate(columns, start=2):
        if isinstance(column, (int, np.integer)):
            heading = f"FY{str(int(column))[-2:]}"
        else:
            heading = str(column)
        cell = worksheet.cell(row=header_row, column=offset, value=heading)
        cell.fill = XL_HEADER_FILL
        cell.font = XL_HEADER_FONT
        cell.border = XL_BORDER
        cell.alignment = Alignment(horizontal="center")

    row_pointer = header_row + 1
    for item in frame.index:
        label = str(item)
        is_subtotal = label.strip() in SUBTOTAL_ITEMS
        cell = worksheet.cell(row=row_pointer, column=1, value=label)
        cell.font = XL_BOLD if is_subtotal else XL_NORMAL
        cell.border = XL_BORDER
        cell.alignment = Alignment(horizontal="left", indent=1, wrap_text=False)
        if is_subtotal:
            cell.fill = XL_SUBTOTAL_FILL
        else:
            cell.fill = XL_LABEL_FILL

        for offset, column in enumerate(columns, start=2):
            raw = frame.loc[item, column]
            target = worksheet.cell(row=row_pointer, column=offset)
            if isinstance(raw, (int, float, np.integer, np.floating)) \
                    and not pd.isna(raw):
                target.value = float(raw)
                target.number_format = DECIMAL_FORMAT if decimals else NUMBER_FORMAT
                target.alignment = Alignment(horizontal="right")
            else:
                target.value = "-" if (raw is None or pd.isna(raw)) else str(raw)
                target.alignment = Alignment(horizontal="right"
                                             if isinstance(raw, str) else "center")
            target.font = XL_BOLD if is_subtotal else XL_NORMAL
            target.border = XL_BORDER
            if is_subtotal:
                target.fill = XL_SUBTOTAL_FILL
        row_pointer += 1

    worksheet.column_dimensions["A"].width = label_width
    for offset in range(2, len(columns) + 2):
        worksheet.column_dimensions[get_column_letter(offset)].width = 15
    worksheet.freeze_panes = worksheet.cell(row=header_row + 1, column=2)
    return row_pointer + 2


def _write_text_table(worksheet, frame: pd.DataFrame, start_row: int,
                      widths: Optional[List[int]] = None,
                      status_column: Optional[str] = None) -> int:
    """Write a table of text columns, optionally traffic-lighting a status column."""
    if frame is None or frame.empty:
        worksheet.cell(row=start_row, column=1, value="No data.").font = XL_NOTE
        return start_row + 2

    columns = list(frame.columns)
    for offset, column in enumerate(columns, start=1):
        cell = worksheet.cell(row=start_row, column=offset, value=str(column))
        cell.fill = XL_HEADER_FILL
        cell.font = XL_HEADER_FONT
        cell.border = XL_BORDER
        cell.alignment = Alignment(horizontal="left", indent=1)

    row_pointer = start_row + 1
    for _, record in frame.iterrows():
        status = str(record[status_column]) if status_column else ""
        for offset, column in enumerate(columns, start=1):
            value = record[column]
            cell = worksheet.cell(row=row_pointer, column=offset)
            if isinstance(value, (int, float, np.integer, np.floating)) \
                    and not pd.isna(value):
                cell.value = float(value)
                cell.number_format = DECIMAL_FORMAT
                cell.alignment = Alignment(horizontal="right")
            else:
                cell.value = "-" if (value is None or pd.isna(value)) else str(value)
                cell.alignment = Alignment(horizontal="left", indent=1, wrap_text=True)
            cell.font = XL_NORMAL
            cell.border = XL_BORDER
            if status == "PASS":
                cell.fill = XL_PASS_FILL
            elif status == "WARNING":
                cell.fill = XL_WARN_FILL
            elif status == "ERROR":
                cell.fill = XL_ERROR_FILL
        row_pointer += 1

    default_widths = widths or ([46] + [14] * (len(columns) - 2) + [70])
    for offset, width in enumerate(default_widths[:len(columns)], start=1):
        worksheet.column_dimensions[get_column_letter(offset)].width = width
    worksheet.freeze_panes = worksheet.cell(row=start_row + 1, column=1)
    return row_pointer + 2


def export_forecast(path: str, hist: HistoricalModel, output: ModelOutput,
                    assumptions: AssumptionSet) -> str:
    """Write the complete, professionally formatted forecast workbook."""
    workbook = Workbook()
    stamp = datetime.now().strftime("%d %B %Y at %H:%M")
    subtitle = (f"{hist.company}  |  Scenario: {output.scenario}  |  "
                f"All figures in {BASE_UNIT}  |  Generated by {APP_NAME} "
                f"{APP_VERSION} on {stamp}")
    passes, warnings, errors = check_counts(output.checks)

    # ---- 0. cover -------------------------------------------------------------------
    cover = workbook.active
    cover.title = "Cover"
    row = _sheet_title(cover, f"{APP_NAME} - Financial Forecast", 4, subtitle)
    summary = pd.DataFrame(
        [
            ("Company", hist.company),
            ("Historical years", ", ".join(f"FY{y}" for y in hist.years)),
            ("Forecast years", ", ".join(f"FY{y}" for y in output.years)),
            ("Scenario", output.scenario),
            ("Scenario basis", SCENARIO_NOTES.get(output.scenario, "")),
            ("Reporting unit", BASE_UNIT),
            ("Source files", ", ".join(hist.source_files) or "Not recorded"),
            ("Model checks", f"{passes} passed, {warnings} warnings, {errors} errors"),
            ("Balance sheet status",
             "Model Balanced" if not errors else "Review the Model Checks sheet"),
            ("Funding plug",
             "ON" if assumptions.settings.cash_sweep else "OFF"),
            ("Minimum cash balance",
             f"Rs {assumptions.settings.minimum_cash:,.0f} lakh"),
            ("Depreciation methodology", assumptions.settings.depreciation_method),
            ("Generated", stamp),
        ],
        columns=["Item", "Detail"],
    )
    row = _write_text_table(cover, summary, row, widths=[34, 96])
    if errors:
        cell = cover.cell(row=row, column=1,
                          value="WARNING: this forecast contains critical errors. "
                                "Refer to the Model Checks sheet before relying on it.")
        cell.font = Font(name="Calibri", size=11, bold=True, color="9C0006")
        cell.fill = XL_ERROR_FILL

    # ---- 1. assumptions -------------------------------------------------------------
    sheet = workbook.create_sheet("1 Assumptions")
    span = len(assumptions.years) + 3
    row = _sheet_title(sheet, "Forecast Assumptions", span, subtitle)
    row = _write_frame(sheet, assumptions.to_frame(), row,
                       label_header="Assumption", decimals=True, label_width=44)
    sheet.column_dimensions["B"].width = 22
    sheet.column_dimensions["C"].width = 78
    row = _write_text_table(sheet, assumptions.settings_frame(), row, widths=[44, 60])

    # ---- 2-4. historical statements -------------------------------------------------
    for name, frame, title in (
        ("2 Historical P&L", hist.pnl, "Historical Profit and Loss"),
        ("3 Historical Balance Sheet", hist.balance_sheet, "Historical Balance Sheet"),
        ("4 Historical Cash Flow", hist.cash_flow, "Historical Cash Flow Statement"),
    ):
        sheet = workbook.create_sheet(name)
        row = _sheet_title(sheet, title, len(hist.years) + 1, subtitle)
        _write_frame(sheet, frame, row)

    # ---- 5-7. forecast statements ---------------------------------------------------
    for name, frame, title in (
        ("5 Forecast P&L", output.pnl, "Forecast Profit and Loss"),
        ("6 Forecast Balance Sheet", output.balance_sheet, "Forecast Balance Sheet"),
        ("7 Forecast Cash Flow", output.cash_flow, "Forecast Cash Flow Statement"),
    ):
        sheet = workbook.create_sheet(name)
        row = _sheet_title(sheet, title, len(output.years) + 1, subtitle)
        _write_frame(sheet, frame, row)

    # ---- 8. supporting schedules ----------------------------------------------------
    sheet = workbook.create_sheet("8 Schedules")
    row = _sheet_title(sheet, "Supporting Schedules", len(output.years) + 1, subtitle)
    for title, frame in (
        ("Property, plant and equipment", output.ppe_schedule),
        ("Working capital", output.working_capital_schedule),
        ("Debt and finance cost", output.debt_schedule),
        ("Taxation", output.tax_schedule),
        ("Equity and retained earnings", output.equity_schedule),
    ):
        cell = sheet.cell(row=row, column=1, value=title)
        cell.font = XL_BOLD
        row = _write_frame(sheet, frame, row + 1, decimals=True)

    # ---- 9. ratios ------------------------------------------------------------------
    sheet = workbook.create_sheet("9 Ratios")
    combined = combined_ratios(hist, output)
    row = _sheet_title(sheet, "Ratio Analysis - historical and forecast",
                       len(combined.columns) + 1, subtitle)
    for group, names in RATIO_GROUPS.items():
        available = [n for n in names if n in combined.index]
        if not available:
            continue
        cell = sheet.cell(row=row, column=1, value=group)
        cell.font = XL_BOLD
        row = _write_frame(sheet, combined.loc[available], row + 1, decimals=True)

    # ---- 10. model checks -----------------------------------------------------------
    sheet = workbook.create_sheet("10 Model Checks")
    row = _sheet_title(sheet, "Model Integrity Checks", 4, subtitle)
    _write_text_table(sheet, output.checks, row, widths=[52, 18, 14, 78],
                      status_column="Status")

    workbook.save(path)
    return path


def default_export_name(hist: HistoricalModel, output: ModelOutput) -> str:
    company = re.sub(r"[^A-Za-z0-9]+", "_", hist.company).strip("_")[:40]
    scenario = re.sub(r"[^A-Za-z0-9]+", "_", output.scenario).strip("_")
    return (f"{company}_Forecast_FY{output.years[0]}_FY{output.years[-1]}"
            f"_{scenario}_{datetime.now().strftime('%Y%m%d')}.xlsx")


# ---------------------------------------------------------------------------------
# END OF PART 3B.
# Paste PART 3C (demo company workbook generator and self-tests) beneath this line.
# ---------------------------------------------------------------------------------
# =====================================================================================
# PART 3C.1  PARSER HARDENING - normalised subtotal labels
# _norm strips the word "and", so a few exclusion tokens need their normalised twin.
# Reassigning the global is picked up by match_line_item at call time.
# =====================================================================================
EXCLUDE_TOKENS = tuple(dict.fromkeys(
    list(EXCLUDE_TOKENS) + [
        "total equity liabilities",
        "equity liabilities",
        "total shareholders funds",
        "shareholders funds",
        "total sources funds",
        "total application funds",
        "amount",
        "figures",
        "sub total",
        "subtotal",
        "memorandum",
        "memorandum information",
        "key operating metrics",
    ]
))

# =====================================================================================
# PART 3C.2  DEMO COMPANY
# Three internally consistent workbooks are generated from a single driver set, so the
# balance sheet balances to the penny and the cash flow reconciles by construction.
# The three files deliberately differ in layout, wording and column position, and one
# carries memorandum lines that the parser is expected to reject as unmapped.
# =====================================================================================
DEMO_COMPANY = "Pragati Tech Solutions Private Limited"
DEMO_YEARS: List[int] = [2024, 2025, 2026]

DEMO_OPENING: Dict[str, float] = {
    "revenue": 15000.0,
    "ppe": 6000.0,
    "intangibles": 400.0,
    "investments": 200.0,
    "inventory": 370.0,
    "receivables": 2470.0,
    "oca": 450.0,
    "cash": 1200.0,
    "share_capital": 1000.0,
    "other_reserves": 500.0,
    "borrowings": 3500.0,
    "lease": 600.0,
    "dtl": 300.0,
    "payables": 565.0,
    "ocl": 420.0,
    "provisions": 150.0,
    "tax_payable": 120.0,
}

DEMO_DRIVERS: Dict[int, Dict[str, float]] = {
    2024: dict(revenue=17400.0, other_income_pct=0.012, cogs_pct=0.315,
               employee_pct=0.340, other_opex_pct=0.125, capex_pct=0.090,
               dep_rate=0.105, disposal_pct=0.012, amort_rate=0.100,
               receivable_days=58.0, inventory_days=27.0, payable_days=44.0,
               oca_pct=0.030, ocl_pct=0.028, provisions_pct=0.010,
               interest_rate=0.092, lease_rate=0.080, debt_repay_pct=0.100,
               new_borrowing=600.0, lease_repay_pct=0.150, tax_rate=0.252,
               tax_payable_pct=0.250, dividend_payout=0.080),
    2025: dict(revenue=20300.0, other_income_pct=0.011, cogs_pct=0.308,
               employee_pct=0.336, other_opex_pct=0.122, capex_pct=0.085,
               dep_rate=0.102, disposal_pct=0.010, amort_rate=0.100,
               receivable_days=56.0, inventory_days=26.0, payable_days=45.0,
               oca_pct=0.030, ocl_pct=0.029, provisions_pct=0.010,
               interest_rate=0.090, lease_rate=0.080, debt_repay_pct=0.100,
               new_borrowing=400.0, lease_repay_pct=0.150, tax_rate=0.251,
               tax_payable_pct=0.250, dividend_payout=0.090),
    2026: dict(revenue=23150.0, other_income_pct=0.010, cogs_pct=0.302,
               employee_pct=0.332, other_opex_pct=0.120, capex_pct=0.082,
               dep_rate=0.100, disposal_pct=0.010, amort_rate=0.100,
               receivable_days=55.0, inventory_days=25.0, payable_days=45.0,
               oca_pct=0.030, ocl_pct=0.030, provisions_pct=0.010,
               interest_rate=0.089, lease_rate=0.080, debt_repay_pct=0.100,
               new_borrowing=250.0, lease_repay_pct=0.150, tax_rate=0.250,
               tax_payable_pct=0.250, dividend_payout=0.100),
}


def build_demo_financials() -> Dict[str, Dict[int, Dict[str, float]]]:
    """Roll the demo company forward from its opening balance sheet."""
    opening = dict(DEMO_OPENING)

    # Retained earnings is set as the balancing figure, so FY23 balances exactly.
    assets = (opening["ppe"] + opening["intangibles"] + opening["investments"]
              + opening["inventory"] + opening["receivables"] + opening["oca"]
              + opening["cash"])
    liabilities = (opening["borrowings"] + opening["lease"] + opening["dtl"]
                   + opening["payables"] + opening["ocl"] + opening["provisions"]
                   + opening["tax_payable"])
    opening["retained_earnings"] = (assets - liabilities - opening["share_capital"]
                                    - opening["other_reserves"])

    prior = dict(opening)
    share_capital = opening["share_capital"]
    other_reserves = opening["other_reserves"]
    deferred_tax = opening["dtl"]

    pnl: Dict[int, Dict[str, float]] = {}
    bs: Dict[int, Dict[str, float]] = {}
    cf: Dict[int, Dict[str, float]] = {}
    ppe: Dict[int, Dict[str, float]] = {}
    debt: Dict[int, Dict[str, float]] = {}
    tax: Dict[int, Dict[str, float]] = {}
    equity: Dict[int, Dict[str, float]] = {}

    for year in DEMO_YEARS:
        d = DEMO_DRIVERS[year]
        revenue = d["revenue"]
        other_income = revenue * d["other_income_pct"]
        cogs = revenue * d["cogs_pct"]
        employee = revenue * d["employee_pct"]
        other_opex = revenue * d["other_opex_pct"]
        ebitda = revenue - cogs - employee - other_opex

        capex = revenue * d["capex_pct"]
        disposals = prior["ppe"] * d["disposal_pct"]
        depreciation = prior["ppe"] * d["dep_rate"]
        closing_ppe = prior["ppe"] + capex - disposals - depreciation
        amortisation = prior["intangibles"] * d["amort_rate"]
        closing_intangibles = prior["intangibles"] - amortisation
        total_da = depreciation + amortisation
        ebit = ebitda - total_da

        repayment = prior["borrowings"] * d["debt_repay_pct"]
        drawdown = d["new_borrowing"]
        closing_borrowings = prior["borrowings"] + drawdown - repayment
        average_borrowings = 0.5 * (prior["borrowings"] + closing_borrowings)
        interest_on_debt = average_borrowings * d["interest_rate"]
        lease_repayment = prior["lease"] * d["lease_repay_pct"]
        closing_lease = prior["lease"] - lease_repayment
        lease_interest = prior["lease"] * d["lease_rate"]
        finance_cost = interest_on_debt + lease_interest

        pbt = ebit + other_income - finance_cost
        tax_expense = pbt * d["tax_rate"]
        pat = pbt - tax_expense
        closing_tax_payable = tax_expense * d["tax_payable_pct"]
        tax_paid = prior["tax_payable"] + tax_expense - closing_tax_payable
        dividends = pat * d["dividend_payout"]

        receivables = revenue * d["receivable_days"] / 365.0
        inventory = cogs * d["inventory_days"] / 365.0
        payables = cogs * d["payable_days"] / 365.0
        oca = revenue * d["oca_pct"]
        ocl = revenue * d["ocl_pct"]
        provisions = revenue * d["provisions_pct"]

        wc_cash = -((receivables - prior["receivables"])
                    + (inventory - prior["inventory"])
                    + (oca - prior["oca"])) \
            + ((payables - prior["payables"]) + (ocl - prior["ocl"]))
        other_non_cash = ((provisions - prior["provisions"])
                          + (closing_tax_payable - prior["tax_payable"]))

        cfo = pat + total_da + wc_cash + other_non_cash
        cfi = -capex + disposals
        cff = drawdown - repayment - lease_repayment - dividends
        net_change = cfo + cfi + cff
        closing_cash = prior["cash"] + net_change

        closing_re = prior["retained_earnings"] + pat - dividends
        closing_equity = share_capital + closing_re + other_reserves
        total_assets = (closing_ppe + closing_intangibles + prior["investments"]
                        + inventory + receivables + oca + closing_cash)
        total_liabilities = (closing_borrowings + closing_lease + deferred_tax
                             + payables + ocl + provisions + closing_tax_payable)

        pnl[year] = {
            "Revenue": revenue, "Other Income": other_income,
            "Cost of Goods Sold": cogs, "Employee Cost": employee,
            "Other Operating Expenses": other_opex, "EBITDA": ebitda,
            "Depreciation & Amortisation": total_da, "EBIT": ebit,
            "Finance Cost": finance_cost, "PBT": pbt, "Tax Expense": tax_expense,
            "PAT": pat,
            "Total Income": revenue + other_income,
            "Total Expenses": cogs + employee + other_opex,
        }
        bs[year] = {
            "Property, Plant and Equipment": closing_ppe,
            "Intangible Assets": closing_intangibles,
            "Investments": prior["investments"],
            "Inventory": inventory, "Trade Receivables": receivables,
            "Other Current Assets": oca, "Cash and Cash Equivalents": closing_cash,
            "Total Assets": total_assets,
            "Share Capital": share_capital, "Retained Earnings": closing_re,
            "Other Reserves": other_reserves, "Total Equity": closing_equity,
            "Borrowings": closing_borrowings, "Lease Liabilities": closing_lease,
            "Deferred Tax Liability": deferred_tax, "Trade Payables": payables,
            "Other Current Liabilities": ocl, "Provisions": provisions,
            "Current Tax Payable": closing_tax_payable,
            "Total Liabilities": total_liabilities,
            "Total Equity and Liabilities": closing_equity + total_liabilities,
            "Total Non-Current Assets": (closing_ppe + closing_intangibles
                                         + prior["investments"]),
            "Total Current Assets": (inventory + receivables + oca + closing_cash),
            "Total Non-Current Liabilities": (closing_borrowings + closing_lease
                                              + deferred_tax),
            "Total Current Liabilities": (payables + ocl + provisions
                                          + closing_tax_payable),
        }
        cf[year] = {
            "PAT": pat, "Depreciation & Amortisation": total_da,
            "Change in Working Capital": wc_cash,
            "Other Non-Cash Movements": other_non_cash,
            "Cash Flow from Operating Activities": cfo,
            "Capital Expenditure": -capex, "Proceeds from Disposals": disposals,
            "Cash Flow from Investing Activities": cfi,
            "New Borrowings": drawdown, "Repayment of Borrowings": -repayment,
            "Lease Principal Repayment": -lease_repayment,
            "Dividends Paid": -dividends,
            "Cash Flow from Financing Activities": cff,
            "Net Change in Cash": net_change, "Opening Cash": prior["cash"],
            "Closing Cash": closing_cash,
        }
        ppe[year] = {
            "Opening PPE": prior["ppe"], "Capex": capex, "Disposals": -disposals,
            "Depreciation Charge": -depreciation, "Closing PPE": closing_ppe,
        }
        debt[year] = {
            "Opening Debt": prior["borrowings"], "New Borrowings": drawdown,
            "Repayment of Borrowings": -repayment, "Closing Debt": closing_borrowings,
        }
        tax[year] = {
            "Opening Tax Payable": prior["tax_payable"], "Tax Expense": tax_expense,
            "Tax Paid": -tax_paid, "Closing Tax Payable": closing_tax_payable,
        }
        equity[year] = {
            "Opening Retained Earnings": prior["retained_earnings"], "PAT": pat,
            "Dividends": -dividends, "Other Comprehensive Income": 0.0,
            "Closing Retained Earnings": closing_re, "Share Capital": share_capital,
            "Other Reserves": other_reserves,
        }

        prior = {
            "revenue": revenue, "ppe": closing_ppe,
            "intangibles": closing_intangibles, "investments": prior["investments"],
            "inventory": inventory, "receivables": receivables, "oca": oca,
            "cash": closing_cash, "borrowings": closing_borrowings,
            "lease": closing_lease, "payables": payables, "ocl": ocl,
            "provisions": provisions, "tax_payable": closing_tax_payable,
            "retained_earnings": closing_re, "share_capital": share_capital,
            "other_reserves": other_reserves, "dtl": deferred_tax,
        }

    return {"pnl": pnl, "bs": bs, "cf": cf, "ppe": ppe, "debt": debt,
            "tax": tax, "equity": equity}


# ---- label wording, deliberately different in each workbook -------------------------
DEMO_LABELS: Dict[int, Dict[str, str]] = {
    2024: {
        "Revenue": "Revenue from operations",
        "Other Income": "Other income",
        "Cost of Goods Sold": "Cost of materials consumed",
        "Employee Cost": "Employee benefit expenses",
        "Other Operating Expenses": "Other expenses",
        "Depreciation & Amortisation": "Depreciation and amortisation",
        "Finance Cost": "Finance costs",
        "PBT": "Profit before tax",
        "Tax Expense": "Total tax expense",
        "PAT": "Profit for the year",
    },
    2025: {
        "Revenue": "Net sales",
        "Other Income": "Other income",
        "Cost of Goods Sold": "Cost of sales",
        "Employee Cost": "Personnel expenses",
        "Other Operating Expenses": "Other operating expenses",
        "Depreciation & Amortisation": "Depreciation & amortization",
        "Finance Cost": "Interest expense",
        "PBT": "Profit before taxation",
        "Tax Expense": "Income tax expense",
        "PAT": "Net profit",
    },
    2026: {
        "Revenue": "Turnover",
        "Other Income": "Other income",
        "Cost of Goods Sold": "Cost of goods sold",
        "Employee Cost": "Staff cost",
        "Other Operating Expenses": "Administrative expenses",
        "Depreciation & Amortisation": "Depreciation and amortization expense",
        "Finance Cost": "Finance cost",
        "PBT": "Profit before tax",
        "Tax Expense": "Provision for tax",
        "PAT": "Profit after tax",
    },
}

DEMO_UNIT_TEXT: Dict[int, str] = {
    2024: "(All amounts in Rs. lakh unless otherwise stated)",
    2025: "(Amounts in INR lakh)",
    2026: "(Figures in Rs. lakhs)",
}

DEMO_HEADINGS: Dict[int, Any] = {
    2024: lambda y: f"FY{y}",
    2025: lambda y: f"FY {y}",
    2026: lambda y: f"{y - 1}-{str(y)[-2:]}",
}

DEMO_LABEL_COL: Dict[int, int] = {2024: 2, 2025: 1, 2026: 3}

DEMO_FILE_YEARS: Dict[int, List[int]] = {
    2024: [2024],
    2025: [2025, 2024],
    2026: [2026, 2025],
}

D_TITLE_FILL = PatternFill("solid", fgColor="1F3864")
D_HEAD_FILL = PatternFill("solid", fgColor="2E75B6")
D_SUB_FILL = PatternFill("solid", fgColor="DDEBF7")


def _write_demo_sheet(worksheet, title: str, unit_text: str,
                      columns: List[Tuple[int, str]],
                      rows: List[Tuple[str, Optional[Dict[int, float]], bool]],
                      label_col: int) -> None:
    """Write one demo statement sheet with a title block and a year header row."""
    last_col = label_col + len(columns)
    worksheet.merge_cells(start_row=1, start_column=1, end_row=1,
                          end_column=max(last_col, 3))
    cell = worksheet.cell(row=1, column=1, value=title)
    cell.font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    cell.fill = D_TITLE_FILL
    cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    worksheet.row_dimensions[1].height = 24

    note = worksheet.cell(row=2, column=1, value=unit_text)
    note.font = Font(name="Calibri", size=9, italic=True, color="595959")

    header_row = 4
    label_cell = worksheet.cell(row=header_row, column=label_col, value="Particulars")
    label_cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    label_cell.fill = D_HEAD_FILL
    label_cell.alignment = Alignment(horizontal="left", indent=1)
    for offset, (_, heading) in enumerate(columns, start=1):
        head = worksheet.cell(row=header_row, column=label_col + offset, value=heading)
        head.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        head.fill = D_HEAD_FILL
        head.alignment = Alignment(horizontal="center")

    pointer = header_row + 1
    for label, values, bold in rows:
        text = worksheet.cell(row=pointer, column=label_col, value=label)
        text.font = Font(name="Calibri", size=11, bold=bold)
        text.alignment = Alignment(horizontal="left", indent=1)
        if bold:
            text.fill = D_SUB_FILL
        if values is not None:
            for offset, (year, _) in enumerate(columns, start=1):
                if year not in values:
                    continue
                target = worksheet.cell(row=pointer, column=label_col + offset,
                                        value=float(values[year]))
                target.number_format = '#,##0.0;[Red](#,##0.0)'
                target.font = Font(name="Calibri", size=11, bold=bold)
                target.alignment = Alignment(horizontal="right")
                if bold:
                    target.fill = D_SUB_FILL
        pointer += 1

    worksheet.column_dimensions[get_column_letter(label_col)].width = 46
    for offset in range(1, len(columns) + 1):
        worksheet.column_dimensions[
            get_column_letter(label_col + offset)].width = 16


def _demo_rows(section: str, data: Dict[str, Dict[int, Dict[str, float]]],
               labels: Dict[str, str]) -> List[Tuple[str, Optional[Dict[int, float]],
                                                     bool]]:
    """Build the row list for one statement, pivoting the demo data by line item."""
    def pick(bucket: str, item: str) -> Dict[int, float]:
        return {year: values[item]
                for year, values in data[bucket].items() if item in values}

    def label_of(item: str) -> str:
        return labels.get(item, item)

    if section == "pnl":
        return [
            (label_of("Revenue"), pick("pnl", "Revenue"), False),
            (label_of("Other Income"), pick("pnl", "Other Income"), False),
            ("Total income", pick("pnl", "Total Income"), True),
            (label_of("Cost of Goods Sold"), pick("pnl", "Cost of Goods Sold"), False),
            (label_of("Employee Cost"), pick("pnl", "Employee Cost"), False),
            (label_of("Other Operating Expenses"),
             pick("pnl", "Other Operating Expenses"), False),
            ("Total expenses", pick("pnl", "Total Expenses"), True),
            ("EBITDA", pick("pnl", "EBITDA"), True),
            (label_of("Depreciation & Amortisation"),
             pick("pnl", "Depreciation & Amortisation"), False),
            ("EBIT", pick("pnl", "EBIT"), True),
            (label_of("Finance Cost"), pick("pnl", "Finance Cost"), False),
            (label_of("PBT"), pick("pnl", "PBT"), True),
            (label_of("Tax Expense"), pick("pnl", "Tax Expense"), False),
            (label_of("PAT"), pick("pnl", "PAT"), True),
        ]
    if section == "bs":
        return [
            ("ASSETS", None, True),
            ("Non-current assets", None, False),
            ("Property, plant and equipment",
             pick("bs", "Property, Plant and Equipment"), False),
            ("Intangible assets", pick("bs", "Intangible Assets"), False),
            ("Investments", pick("bs", "Investments"), False),
            ("Total non-current assets", pick("bs", "Total Non-Current Assets"), True),
            ("Current assets", None, False),
            ("Inventories", pick("bs", "Inventory"), False),
            ("Trade receivables", pick("bs", "Trade Receivables"), False),
            ("Other current assets", pick("bs", "Other Current Assets"), False),
            ("Cash and cash equivalents",
             pick("bs", "Cash and Cash Equivalents"), False),
            ("Total current assets", pick("bs", "Total Current Assets"), True),
            ("Total assets", pick("bs", "Total Assets"), True),
            ("EQUITY AND LIABILITIES", None, True),
            ("Equity share capital", pick("bs", "Share Capital"), False),
            ("Reserves and surplus", pick("bs", "Retained Earnings"), False),
            ("Other reserves", pick("bs", "Other Reserves"), False),
            ("Total equity", pick("bs", "Total Equity"), True),
            ("Non-current liabilities", None, False),
            ("Long term borrowings", pick("bs", "Borrowings"), False),
            ("Lease liabilities", pick("bs", "Lease Liabilities"), False),
            ("Deferred tax liability", pick("bs", "Deferred Tax Liability"), False),
            ("Total non-current liabilities",
             pick("bs", "Total Non-Current Liabilities"), True),
            ("Current liabilities", None, False),
            ("Trade payables", pick("bs", "Trade Payables"), False),
            ("Other current liabilities",
             pick("bs", "Other Current Liabilities"), False),
            ("Provisions", pick("bs", "Provisions"), False),
            ("Current tax payable", pick("bs", "Current Tax Payable"), False),
            ("Total current liabilities", pick("bs", "Total Current Liabilities"), True),
            ("Total equity and liabilities",
             pick("bs", "Total Equity and Liabilities"), True),
        ]
    if section == "cf":
        return [
            ("A. Cash flow from operating activities", None, True),
            ("Profit for the year", pick("cf", "PAT"), False),
            ("Depreciation and amortisation",
             pick("cf", "Depreciation & Amortisation"), False),
            ("Changes in working capital", pick("cf", "Change in Working Capital"),
             False),
            ("Other non-cash adjustments", pick("cf", "Other Non-Cash Movements"),
             False),
            ("Net cash generated from operating activities",
             pick("cf", "Cash Flow from Operating Activities"), True),
            ("B. Cash flow from investing activities", None, True),
            ("Purchase of property, plant and equipment",
             pick("cf", "Capital Expenditure"), False),
            ("Proceeds from sale of fixed assets",
             pick("cf", "Proceeds from Disposals"), False),
            ("Net cash used in investing activities",
             pick("cf", "Cash Flow from Investing Activities"), True),
            ("C. Cash flow from financing activities", None, True),
            ("Proceeds from borrowings", pick("cf", "New Borrowings"), False),
            ("Repayment of borrowings", pick("cf", "Repayment of Borrowings"), False),
            ("Payment of lease liabilities",
             pick("cf", "Lease Principal Repayment"), False),
            ("Dividend paid", pick("cf", "Dividends Paid"), False),
            ("Net cash used in financing activities",
             pick("cf", "Cash Flow from Financing Activities"), True),
            ("Net increase in cash and cash equivalents",
             pick("cf", "Net Change in Cash"), True),
            ("Cash and cash equivalents at the beginning of the year",
             pick("cf", "Opening Cash"), False),
            ("Cash and cash equivalents at the end of the year",
             pick("cf", "Closing Cash"), True),
        ]
    if section == "schedules":
        employees = {2024: 1180.0, 2025: 1320.0, 2026: 1465.0}
        csr = {2024: 22.4, 2025: 27.1, 2026: 31.8}
        return [
            ("Schedule 1 - Property, plant and equipment", None, True),
            ("Opening net block", pick("ppe", "Opening PPE"), False),
            ("Additions during the year", pick("ppe", "Capex"), False),
            ("Disposals during the year", pick("ppe", "Disposals"), False),
            ("Depreciation for the year", pick("ppe", "Depreciation Charge"), False),
            ("Closing net block", pick("ppe", "Closing PPE"), True),
            ("Schedule 2 - Borrowings", None, True),
            ("Opening borrowings", pick("debt", "Opening Debt"), False),
            ("Drawdown during the year", pick("debt", "New Borrowings"), False),
            ("Repayment during the year",
             pick("debt", "Repayment of Borrowings"), False),
            ("Closing borrowings", pick("debt", "Closing Debt"), True),
            ("Schedule 3 - Taxation", None, True),
            ("Opening provision for tax", pick("tax", "Opening Tax Payable"), False),
            ("Current tax", pick("tax", "Tax Expense"), False),
            ("Taxes paid", pick("tax", "Tax Paid"), False),
            ("Closing provision for tax", pick("tax", "Closing Tax Payable"), True),
            ("Memorandum information", None, True),
            ("Number of employees at year end", employees, False),
            ("Corporate social responsibility contribution", csr, False),
        ]
    if section == "equity":
        return [
            ("Retained earnings", None, True),
            ("Balance at the beginning of the year",
             pick("equity", "Opening Retained Earnings"), False),
            ("Profit for the year", pick("equity", "PAT"), False),
            ("Dividend paid", pick("equity", "Dividends"), False),
            ("Other comprehensive income",
             pick("equity", "Other Comprehensive Income"), False),
            ("Balance at the end of the year",
             pick("equity", "Closing Retained Earnings"), True),
            ("Other components of equity", None, True),
            ("Equity share capital", pick("equity", "Share Capital"), False),
            ("Other reserves", pick("equity", "Other Reserves"), False),
        ]
    return []


def generate_demo_workbooks(folder: Optional[str] = None) -> List[str]:
    """Write the three Pragati Tech demo workbooks and return their paths."""
    target = folder or tempfile.mkdtemp(prefix="CashFlowForecastingPro_Demo_")
    os.makedirs(target, exist_ok=True)
    data = build_demo_financials()
    paths: List[str] = []

    for file_year in DEMO_YEARS:
        workbook = Workbook()
        years = DEMO_FILE_YEARS[file_year]
        heading = DEMO_HEADINGS[file_year]
        columns = [(year, heading(year)) for year in years]
        labels = DEMO_LABELS[file_year]
        unit_text = DEMO_UNIT_TEXT[file_year]
        label_col = DEMO_LABEL_COL[file_year]

        # ---- Read Me -----------------------------------------------------------------
        readme = workbook.active
        readme.title = "Read Me"
        readme["A1"] = DEMO_COMPANY
        readme["A1"].font = Font(name="Calibri", size=14, bold=True, color="1F3864")
        readme["A3"] = f"Audited financial statements for the year ended 31 March " \
                       f"{file_year}"
        readme["A4"] = unit_text
        readme["A6"] = "Contents"
        readme["A6"].font = Font(bold=True)
        for offset, text in enumerate([
            "P&L - Statement of profit and loss",
            "Balance Sheet - Statement of assets and liabilities",
            "Schedules - Supporting schedules and memorandum information",
            "Cash Flow - Statement of cash flows",
            "Equity - Statement of changes in equity",
        ], start=7):
            readme.cell(row=offset, column=1, value=text)
        readme["A13"] = ("Demonstration data generated by "
                         f"{APP_NAME} {APP_VERSION}. Layout, wording and column "
                         "position differ between the three files in order to "
                         "exercise the semantic parser.")
        readme["A13"].font = Font(size=9, italic=True, color="595959")
        readme.column_dimensions["A"].width = 96

        # ---- statements ---------------------------------------------------------------
        for sheet_name, section, title in (
            ("P&L", "pnl", "Statement of Profit and Loss"),
            ("Balance Sheet", "bs", "Balance Sheet"),
            ("Schedules", "schedules", "Supporting Schedules"),
            ("Cash Flow", "cf", "Statement of Cash Flows"),
            ("Equity", "equity", "Statement of Changes in Equity"),
        ):
            worksheet = workbook.create_sheet(sheet_name)
            rows = _demo_rows(section, data, labels)
            _write_demo_sheet(worksheet, title, unit_text, columns, rows, label_col)

        path = os.path.join(
            target, f"Pragati_Tech_Financials_FY{file_year}.xlsx")
        workbook.save(path)
        paths.append(path)

    return paths


def load_demo_model() -> Tuple[HistoricalModel, List[str]]:
    """Generate the demo workbooks and parse them straight back in."""
    paths = generate_demo_workbooks()
    return build_historical_model(paths), paths


# =====================================================================================
# PART 3C.3  SELF-TESTS
# These cover the parser, the three statements, every roll-forward, the propagation of
# each key assumption, the funding plug, the scenarios and the Excel export.
# =====================================================================================
def run_self_tests() -> pd.DataFrame:
    """Run the full test suite and return the results as a table."""
    results: List[Tuple[str, str, str]] = []

    def record(name: str, function) -> None:
        try:
            detail = function()
            results.append((name, "PASS", detail or "OK"))
        except AssertionError as exc:
            results.append((name, "ERROR", f"Assertion failed: {exc}"))
        except Exception as exc:
            results.append((name, "ERROR", f"{type(exc).__name__}: {exc}"))

    try:
        paths = generate_demo_workbooks()
        hist = build_historical_model(paths)
        years = forecast_years(hist.base_year)
        base = build_scenario(years, "Base Case")
        out = run_forecast(hist, base)
    except Exception as exc:
        return pd.DataFrame(
            [("Test harness setup", "ERROR", f"{type(exc).__name__}: {exc}")],
            columns=["Test", "Status", "Detail"],
        )

    terminal = out.terminal_year
    first = years[0]

    def t_parser() -> str:
        assert hist.years == [2024, 2025, 2026], f"years parsed as {hist.years}"
        assert "Pragati" in hist.company, f"company read as {hist.company}"
        revenue = hist.value("P&L", "Revenue", 2026)
        assert abs(revenue - 23150.0) < 1.0, f"FY26 revenue {revenue:,.1f}"
        return (f"FY2024 to FY2026 parsed from three differently formatted files; "
                f"FY26 revenue Rs {revenue:,.0f} lakh")

    def t_unmapped() -> str:
        unmapped = hist.tidy[hist.tidy["category"] == "Unmapped"]
        labels = set(unmapped["source_label"])
        assert any("employees" in l.lower() for l in labels), \
            "memorandum lines were not rejected"
        return f"{len(labels)} memorandum line(s) correctly excluded from the model"

    def t_hist_balance() -> str:
        worst = max(abs(hist.value("Balance Sheet", "Balance Check", y))
                    for y in hist.years)
        assert worst < 0.05, f"historical imbalance of Rs {worst:,.4f} lakh"
        return "Historical balance sheet balances in every year"

    def t_hist_pnl() -> str:
        for year in hist.years:
            ebitda = (hist.value("P&L", "Revenue", year)
                      - hist.value("P&L", "Cost of Goods Sold", year)
                      - hist.value("P&L", "Employee Cost", year)
                      - hist.value("P&L", "Other Operating Expenses", year))
            assert abs(ebitda - hist.value("P&L", "EBITDA", year)) < 0.05, \
                f"FY{year} EBITDA does not foot"
            pat = (hist.value("P&L", "PBT", year)
                   - hist.value("P&L", "Tax Expense", year))
            assert abs(pat - hist.value("P&L", "PAT", year)) < 0.05, \
                f"FY{year} PAT does not foot"
        return "Revenue less costs equals EBITDA, and PBT less tax equals PAT"

    def t_forecast_years() -> str:
        assert years == [2027, 2028, 2029, 2030, 2031], f"forecast years {years}"
        return "FY2027 to FY2031 generated from an FY2026 base year"

    def t_forecast_balance() -> str:
        worst = max(abs(out.value("Balance Sheet", "Balance Check", y)) for y in years)
        assert worst < TOL, f"out of balance by Rs {worst:,.4f} lakh"
        return f"Model Balanced in all five years, worst residue Rs {worst:,.4f} lakh"

    def t_cash_tie() -> str:
        worst = max(abs(out.value("Cash Flow", "Closing Cash", y)
                        - out.value("Balance Sheet", "Cash and Cash Equivalents", y))
                    for y in years)
        assert worst < TOL, f"cash differs by Rs {worst:,.4f} lakh"
        return "Cash flow closing cash equals balance sheet cash in every year"

    def t_cf_internal() -> str:
        for year in years:
            total = (out.value("Cash Flow", "Cash Flow from Operating Activities", year)
                     + out.value("Cash Flow", "Cash Flow from Investing Activities", year)
                     + out.value("Cash Flow", "Cash Flow from Financing Activities", year))
            movement = (out.value("Cash Flow", "Closing Cash", year)
                        - out.value("Cash Flow", "Opening Cash", year))
            assert abs(total - movement) < TOL, f"FY{year} cash flow does not foot"
        return "CFO plus CFI plus CFF equals the movement in cash"

    def t_ppe_roll() -> str:
        for year in years:
            computed = (out.value("PPE Schedule", "Opening PPE", year)
                        + out.value("PPE Schedule", "Capex", year)
                        + out.value("PPE Schedule", "Disposals", year)
                        + out.value("PPE Schedule", "Depreciation Charge", year))
            assert abs(computed - out.value("PPE Schedule", "Closing PPE", year)) < TOL, \
                f"FY{year} PPE roll-forward"
        return "Opening plus capex less disposals and depreciation equals closing PPE"

    def t_debt_roll() -> str:
        for year in years:
            computed = (out.value("Debt Schedule", "Opening Debt", year)
                        + out.value("Debt Schedule", "Planned New Borrowing", year)
                        + out.value("Debt Schedule", "Funding Plug Drawdown", year)
                        + out.value("Debt Schedule", "Scheduled Repayment", year))
            assert abs(computed - out.value("Debt Schedule", "Closing Debt", year)) < TOL, \
                f"FY{year} debt roll-forward"
        return "Debt roll-forward reconciles and ties to the balance sheet"

    def t_equity_roll() -> str:
        for year in years:
            computed = (out.value("Equity Schedule", "Opening Retained Earnings", year)
                        + out.value("Equity Schedule", "PAT", year)
                        + out.value("Equity Schedule", "Dividends", year))
            closing = out.value("Balance Sheet", "Retained Earnings", year)
            assert abs(computed - closing) < TOL, f"FY{year} retained earnings"
        return "Opening retained earnings plus PAT less dividends equals closing"

    def t_tax_roll() -> str:
        for year in years:
            computed = (out.value("Tax Schedule", "Opening Tax Payable", year)
                        + out.value("Tax Schedule", "Tax Expense", year)
                        + out.value("Tax Schedule", "Tax Paid", year))
            closing = out.value("Balance Sheet", "Current Tax Payable", year)
            assert abs(computed - closing) < TOL, f"FY{year} tax payable"
        return "Opening payable plus expense less tax paid equals closing payable"

    def t_depreciation_once() -> str:
        for year in years:
            pnl_da = out.value("P&L", "Depreciation & Amortisation", year)
            cf_da = out.value("Cash Flow", "Depreciation & Amortisation", year)
            sched = out.value("PPE Schedule", "Total D&A charged to P&L", year)
            assert abs(pnl_da - cf_da) < TOL and abs(pnl_da - sched) < TOL, \
                f"FY{year} depreciation is inconsistent"
        return "A single depreciation figure flows to all three statements"

    def t_revenue_propagation() -> str:
        shifted = base.copy()
        shifted.set("revenue_growth", first, 0.20)
        new = run_forecast(hist, shifted)
        moved = []
        for statement, item in (("P&L", "Revenue"), ("P&L", "Cost of Goods Sold"),
                                ("P&L", "EBITDA"), ("P&L", "PAT"),
                                ("Balance Sheet", "Trade Receivables"),
                                ("Balance Sheet", "Inventory"),
                                ("Balance Sheet", "Trade Payables"),
                                ("Balance Sheet", "Retained Earnings"),
                                ("Cash Flow", "Cash Flow from Operating Activities")):
            before = out.value(statement, item, first)
            after = new.value(statement, item, first)
            assert abs(after - before) > 0.5, f"{item} did not respond"
            moved.append(item)
        worst = max(abs(new.value("Balance Sheet", "Balance Check", y)) for y in years)
        assert worst < TOL, "balance sheet broke after the change"
        return (f"Revenue growth 12% to 20% moved {len(moved)} dependent lines and the "
                f"balance sheet still balances")

    def t_receivable_propagation() -> str:
        shifted = base.copy()
        for year in years:
            shifted.set("receivable_days", year, shifted.get("receivable_days", year) + 20)
        new = run_forecast(hist, shifted)
        assert new.value("Balance Sheet", "Trade Receivables", first) > \
            out.value("Balance Sheet", "Trade Receivables", first) + 1, \
            "receivables did not increase"
        assert new.value("Cash Flow", "Cash Flow from Operating Activities", first) < \
            out.value("Cash Flow", "Cash Flow from Operating Activities", first) - 1, \
            "CFO did not fall"
        assert new.value("Balance Sheet", "Cash and Cash Equivalents", terminal) <= \
            out.value("Balance Sheet", "Cash and Cash Equivalents", terminal) + TOL, \
            "closing cash did not respond"
        return "Twenty extra receivable days reduced CFO and closing cash"

    def t_capex_propagation() -> str:
        shifted = base.copy()
        for year in years:
            shifted.set("capex_pct", year, shifted.get("capex_pct", year) + 0.05)
        new = run_forecast(hist, shifted)
        assert new.value("Balance Sheet", "Property, Plant and Equipment", first) > \
            out.value("Balance Sheet", "Property, Plant and Equipment", first) + 1, \
            "closing PPE did not increase"
        assert new.value("Balance Sheet", "Cash and Cash Equivalents", first) < \
            out.value("Balance Sheet", "Cash and Cash Equivalents", first) - 1, \
            "cash did not fall"
        second = years[1]
        assert new.value("P&L", "Depreciation & Amortisation", second) > \
            out.value("P&L", "Depreciation & Amortisation", second) + 0.5, \
            "depreciation did not respond in the following year"
        worst = max(abs(new.value("Balance Sheet", "Balance Check", y)) for y in years)
        assert worst < TOL, "balance sheet broke after the change"
        return ("Higher capex increased PPE, reduced cash and lifted the following "
                "year's depreciation through the PPE schedule")

    def t_interest_propagation() -> str:
        shifted = base.copy()
        for year in years:
            shifted.set("interest_rate", year, shifted.get("interest_rate", year) + 0.05)
        new = run_forecast(hist, shifted)
        assert new.value("P&L", "Finance Cost", first) > \
            out.value("P&L", "Finance Cost", first) + 1, "finance cost did not rise"
        assert new.value("P&L", "PAT", first) < out.value("P&L", "PAT", first) - 1, \
            "PAT did not fall"
        assert new.value("Balance Sheet", "Cash and Cash Equivalents", terminal) < \
            out.value("Balance Sheet", "Cash and Cash Equivalents", terminal) - 1, \
            "closing cash did not respond"
        worst = max(abs(new.value("Balance Sheet", "Balance Check", y)) for y in years)
        assert worst < TOL, "balance sheet broke after the change"
        return "A higher interest rate raised finance cost and reduced PAT and cash"

    def t_dividend_propagation() -> str:
        shifted = base.copy()
        for year in years:
            shifted.set("dividend_payout", year, 0.60)
        new = run_forecast(hist, shifted)
        assert abs(new.value("Cash Flow", "Dividends Paid", first)) > \
            abs(out.value("Cash Flow", "Dividends Paid", first)) + 1, \
            "dividends did not increase"
        assert new.value("Balance Sheet", "Retained Earnings", terminal) < \
            out.value("Balance Sheet", "Retained Earnings", terminal) - 1, \
            "retained earnings did not fall"
        assert new.value("Balance Sheet", "Cash and Cash Equivalents", terminal) < \
            out.value("Balance Sheet", "Cash and Cash Equivalents", terminal) - 1, \
            "cash did not fall"
        worst = max(abs(new.value("Balance Sheet", "Balance Check", y)) for y in years)
        assert worst < TOL, "balance sheet broke after the change"
        return "A higher payout reduced retained earnings and closing cash"

    def t_funding_plug_on() -> str:
        shifted = base.copy()
        shifted.settings.cash_sweep = True
        shifted.settings.minimum_cash = 30000.0
        new = run_forecast(hist, shifted)
        plug = new.value("Debt Schedule", "Funding Plug Drawdown", first)
        cash = new.value("Balance Sheet", "Cash and Cash Equivalents", first)
        assert plug > 1.0, "the funding plug did not draw down"
        assert abs(cash - 30000.0) < 1.0, f"cash settled at Rs {cash:,.1f} lakh"
        worst = max(abs(new.value("Balance Sheet", "Balance Check", y)) for y in years)
        assert worst < TOL, "balance sheet broke with the plug active"
        return (f"With a Rs 30,000 lakh minimum, the plug drew Rs {plug:,.0f} lakh and "
                f"cash settled exactly on the floor")

    def t_funding_plug_off() -> str:
        shifted = base.copy()
        shifted.settings.cash_sweep = False
        shifted.settings.minimum_cash = 30000.0
        new = run_forecast(hist, shifted)
        for year in years:
            plug = new.value("Debt Schedule", "Funding Plug Drawdown", year)
            assert abs(plug) < TOL, f"FY{year} drew a plug while the sweep was off"
        row = new.checks[new.checks["Check"] == "Minimum cash balance maintained"]
        assert not row.empty, "the minimum cash check is missing"
        status = str(row.iloc[0]["Status"])
        assert status == "WARNING", f"shortfall reported as {status}, not a warning"
        return ("With the sweep switched off no debt was raised and the shortfall was "
                "reported as a warning rather than being hidden")

    def t_depreciation_methods() -> str:
        charges: Dict[str, float] = {}
        for method in DEPRECIATION_METHODS:
            shifted = base.copy()
            shifted.settings.depreciation_method = method
            new = run_forecast(hist, shifted)
            charges[method] = new.value("P&L", "Depreciation & Amortisation", first)
            worst = max(abs(new.value("Balance Sheet", "Balance Check", y))
                        for y in years)
            assert worst < TOL, f"{method} broke the balance sheet"
        distinct = len({round(v, 2) for v in charges.values()})
        assert distinct >= 2, "the depreciation methodologies produced identical charges"
        return ("All three depreciation methodologies balance and produce distinct "
                f"charges: {', '.join(f'{k} {v:,.0f}' for k, v in charges.items())}")

    def t_scenarios() -> str:
        revenues: Dict[str, float] = {}
        for scenario in ("Base Case", "Upside Case", "Downside Case"):
            trial = build_scenario(years, scenario)
            result = run_forecast(hist, trial)
            revenues[scenario] = result.value("P&L", "Revenue", terminal)
            worst = max(abs(result.value("Balance Sheet", "Balance Check", y))
                        for y in years)
            assert worst < TOL, f"{scenario} did not balance"
        assert revenues["Upside Case"] > revenues["Base Case"] > \
            revenues["Downside Case"], "the scenarios are not correctly ordered"
        return (f"FY{str(terminal)[-2:]} revenue: upside Rs "
                f"{revenues['Upside Case']:,.0f}, base Rs "
                f"{revenues['Base Case']:,.0f}, downside Rs "
                f"{revenues['Downside Case']:,.0f} lakh")

    def t_methodologies() -> str:
        notes: List[str] = []
        for method in ("Historical average", "Historical CAGR", "Linear trend"):
            trial = base.copy()
            trial.set_method("revenue_growth", method)
            applied = apply_methodologies(hist, trial)
            value = applied.get("revenue_growth", first)
            assert not pd.isna(value), f"{method} produced no value"
            assert abs(value - base.get("revenue_growth", first)) > 1e-6, \
                f"{method} did not override the manual assumption"
            result = run_forecast(hist, applied)
            worst = max(abs(result.value("Balance Sheet", "Balance Check", y))
                        for y in years)
            assert worst < TOL, f"{method} did not balance"
            notes.append(f"{method} {value * 100:,.1f}%")
        return "Revenue growth derived from history: " + ", ".join(notes)

    def t_ratios() -> str:
        margin = out.ratios.loc["EBITDA margin", first]
        expected = (1.0 - base.get("cogs_pct", first) - base.get("employee_pct", first)
                    - base.get("other_opex_pct", first))
        assert abs(float(margin) - expected) < 0.005, \
            f"EBITDA margin {margin:.4f} against expected {expected:.4f}"
        days = out.ratios.loc["Receivable days", first]
        assert abs(float(days) - base.get("receivable_days", first)) < 0.5, \
            "receivable days do not reproduce the assumption"
        return (f"Forecast ratios reproduce the assumptions exactly: FY"
                f"{str(first)[-2:]} EBITDA margin {float(margin) * 100:,.1f}%")

    def t_combined_view() -> str:
        combined = combined_model(hist, out)
        assert combined.years == hist.years + years, "the combined years are wrong"
        assert abs(combined.pnl.loc["Revenue", 2026]
                   - hist.value("P&L", "Revenue", 2026)) < 0.05, \
            "history was altered when splicing"
        cards = kpi_cards(hist, out)
        assert len(cards) == 8, f"{len(cards)} KPI cards instead of eight"
        series = dashboard_series(hist, out, "Historical + forecast")
        assert len(series["Revenue"]) == len(hist.years) + len(years), \
            "the dashboard series is the wrong length"
        return "History and forecast splice cleanly, and eight KPI cards are produced"

    def t_sensitivity() -> str:
        grid = sensitivity_table(
            hist, base, "revenue_growth", [-0.02, 0.0, 0.02],
            "cogs_pct", [0.01, 0.0, -0.01], metric="EBITDA")
        assert grid.shape == (3, 3), f"grid shape {grid.shape}"
        assert not grid.isna().any().any(), "the grid contains blanks"
        assert float(grid.iloc[2, 2]) > float(grid.iloc[0, 0]), \
            "EBITDA does not increase with growth and margin"
        return (f"Sensitivity grid spans Rs {float(grid.values.min()):,.0f} to "
                f"Rs {float(grid.values.max()):,.0f} lakh of FY"
                f"{str(terminal)[-2:]} EBITDA")

    def t_checks_clean() -> str:
        passes, warnings, errors = check_counts(out.checks)
        assert errors == 0, "; ".join(
            out.checks[out.checks["Status"] == "ERROR"]["Check"].tolist())
        assert not has_critical_errors(out.checks), "critical errors were reported"
        assert passes >= 15, f"only {passes} checks passed"
        return f"{passes} checks passed, {warnings} warnings, {errors} errors"

    def t_export() -> str:
        folder = tempfile.mkdtemp(prefix="CashFlowForecastingPro_Test_")
        path = os.path.join(folder, default_export_name(hist, out))
        export_forecast(path, hist, out, base)
        assert os.path.exists(path), "the workbook was not written"
        assert os.path.getsize(path) > 8000, "the workbook is suspiciously small"
        reopened = load_workbook(path, read_only=True)
        names = list(reopened.sheetnames)
        reopened.close()
        for required in ("Cover", "1 Assumptions", "5 Forecast P&L",
                         "6 Forecast Balance Sheet", "8 Schedules", "9 Ratios",
                         "10 Model Checks"):
            assert required in names, f"the sheet '{required}' is missing"
        return f"{len(names)} sheets written and reopened successfully"

    record("Parser reads three differently formatted workbooks", t_parser)
    record("Unexpected memorandum lines are excluded", t_unmapped)
    record("Historical balance sheet balances as supplied", t_hist_balance)
    record("Historical P&L subtotals foot", t_hist_pnl)
    record("Forecast period is FY2027 to FY2031", t_forecast_years)
    record("Forecast balance sheet balances", t_forecast_balance)
    record("Closing cash ties to the balance sheet", t_cash_tie)
    record("Cash flow statement is internally consistent", t_cf_internal)
    record("PPE roll-forward reconciles", t_ppe_roll)
    record("Debt roll-forward reconciles", t_debt_roll)
    record("Retained earnings roll-forward reconciles", t_equity_roll)
    record("Tax schedule reconciles", t_tax_roll)
    record("Depreciation is calculated once only", t_depreciation_once)
    record("Revenue growth propagates through every statement", t_revenue_propagation)
    record("Receivable days flow to CFO and cash", t_receivable_propagation)
    record("Capex flows to PPE, depreciation and cash", t_capex_propagation)
    record("Interest rate flows to finance cost, PAT and cash", t_interest_propagation)
    record("Dividend payout flows to equity and cash", t_dividend_propagation)
    record("Funding plug maintains the minimum cash balance", t_funding_plug_on)
    record("Funding plug switched off discloses the shortfall", t_funding_plug_off)
    record("All depreciation methodologies balance", t_depreciation_methods)
    record("Scenarios are correctly ordered", t_scenarios)
    record("Historical trend methodologies apply", t_methodologies)
    record("Forecast ratios reproduce the assumptions", t_ratios)
    record("Historical and forecast views combine", t_combined_view)
    record("Sensitivity grid behaves sensibly", t_sensitivity)
    record("Model checks report no critical errors", t_checks_clean)
    record("Excel export is written and readable", t_export)

    return pd.DataFrame(results, columns=["Test", "Status", "Detail"])


def self_test_summary(frame: pd.DataFrame) -> Tuple[int, int]:
    """Return (passed, failed) from a self-test results table."""
    if frame is None or frame.empty:
        return 0, 0
    passed = int((frame["Status"] == "PASS").sum())
    return passed, int(len(frame) - passed)


def print_self_tests() -> pd.DataFrame:
    """Run the suite and print a readable report. Useful directly from IDLE."""
    frame = run_self_tests()
    passed, failed = self_test_summary(frame)
    print("=" * 78)
    print(f"{APP_NAME} {APP_VERSION} - self tests: {passed} passed, {failed} failed")
    print("=" * 78)
    for _, record in frame.iterrows():
        marker = "PASS " if record["Status"] == "PASS" else "FAIL "
        print(f"{marker}| {record['Test']}")
        print(f"      {record['Detail']}")
    print("=" * 78)
    return frame


# ---------------------------------------------------------------------------------
# END OF PART 3C.
# Paste PART 4 (PyQt6 interface and application entry point) beneath this line.
# ---------------------------------------------------------------------------------
# =====================================================================================
# PART 4.1  USER INTERFACE IMPORTS
# =====================================================================================
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QColor, QFont, QBrush
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QLineEdit, QDoubleSpinBox, QFileDialog, QFrame,
    QGridLayout, QHBoxLayout, QHeaderView, QLabel, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSizePolicy, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
_agent_dbg("C", "Cash_Flow_Forecasting_Pro_FINAL.py:qt_imports", "qt_imports_ok", {"has_qlineedit": "QLineEdit" in globals()})

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# =====================================================================================
# PART 4.2  PALETTE AND STYLESHEET
# =====================================================================================
PALETTE: Dict[str, str] = {
    "navy": "#12263F",
    "navy_light": "#1D3A5F",
    "teal": "#00A896",
    "teal_dark": "#028090",
    "amber": "#F4A259",
    "coral": "#EF6461",
    "violet": "#7B6CF6",
    "green": "#2FA84F",
    "yellow": "#F2C037",
    "red": "#D64550",
    "ink": "#1B2430",
    "muted": "#5C6B7A",
    "line": "#D8E0E8",
    "panel": "#FFFFFF",
    "canvas": "#F1F5F9",
    "band": "#F7FAFC",
    "chip": "#E8F4F2",
}

CHART_COLOURS: List[str] = [
    PALETTE["teal"], PALETTE["amber"], PALETTE["violet"], PALETTE["coral"],
    PALETTE["teal_dark"], PALETTE["green"],
]

STYLESHEET = f"""
QWidget {{
    background: {PALETTE['canvas']};
    color: {PALETTE['ink']};
    font-family: 'Helvetica Neue', 'Segoe UI', Arial;
    font-size: 13px;
}}
QLabel#AppTitle {{
    color: {PALETTE['navy']};
    background: transparent;
    font-size: 21px;
    font-weight: 700;
}}
QLabel#AppSubtitle {{
    color: {PALETTE['muted']};
    background: transparent;
    font-size: 12px;
}}
QFrame#Banner {{
    background: transparent;
    border: none;
}}
QFrame#Card {{
    background: {PALETTE['panel']};
    border: 1px solid {PALETTE['line']};
    border-radius: 10px;
}}
QFrame#Kpi {{
    background: {PALETTE['panel']};
    border: 1px solid {PALETTE['line']};
    border-left: 5px solid {PALETTE['teal']};
    border-radius: 10px;
}}
QLabel#KpiLabel {{
    color: {PALETTE['muted']};
    font-size: 11px;
    font-weight: 600;
}}
QLabel#KpiValue {{
    color: {PALETTE['navy']};
    font-size: 22px;
    font-weight: 700;
}}
QLabel#KpiNote {{
    color: {PALETTE['muted']};
    font-size: 11px;
}}
QLabel#PageTitle {{
    color: {PALETTE['navy']};
    font-size: 17px;
    font-weight: 700;
}}
QLabel#PageNote {{
    color: {PALETTE['muted']};
    font-size: 12px;
}}
QLabel#SectionCaption {{
    color: {PALETTE['navy']};
    font-size: 13px;
    font-weight: 700;
}}
QPushButton {{
    background: {PALETTE['teal']};
    color: #FFFFFF;
    border: none;
    border-radius: 7px;
    padding: 9px 18px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {PALETTE['teal_dark']}; }}
QPushButton:pressed {{ background: {PALETTE['navy_light']}; }}
QPushButton:disabled {{ background: #D3DCE6; color: #334155; }}
QPushButton#Secondary {{
    background: {PALETTE['panel']};
    color: {PALETTE['navy']};
    border: 1px solid {PALETTE['teal']};
}}
QPushButton#Secondary:hover {{ background: {PALETTE['chip']}; }}
QPushButton#Accent {{ background: #E08A2E; color: #111111; }}
QPushButton#Accent:hover {{ background: #E8913F; }}
QPushButton#Toggle {{
    background: {PALETTE['band']};
    color: {PALETTE['navy']};
    border: 1px solid {PALETTE['line']};
    border-radius: 7px;
    padding: 8px 12px;
    font-weight: 700;
    text-align: left;
}}
QPushButton#Toggle:hover {{ background: {PALETTE['chip']}; }}
QTabWidget::pane {{
    background: {PALETTE['canvas']};
    border-top: 3px solid {PALETTE['teal']};
}}
QTabBar::tab {{
    background: {PALETTE['navy_light']};
    color: #C9D9EA;
    padding: 11px 22px;
    margin-right: 2px;
    font-weight: 600;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
}}
QTabBar::tab:selected {{ background: {PALETTE['teal']}; color: #FFFFFF; }}
QTabBar::tab:hover:!selected {{ background: {PALETTE['navy']}; color: #FFFFFF; }}
QTableWidget {{
    background: {PALETTE['panel']};
    gridline-color: {PALETTE['line']};
    border: 1px solid {PALETTE['line']};
    border-radius: 8px;
    selection-background-color: {PALETTE['chip']};
    selection-color: {PALETTE['ink']};
}}
QHeaderView::section {{
    background: {PALETTE['navy']};
    color: #FFFFFF;
    padding: 7px;
    border: none;
    border-right: 1px solid {PALETTE['navy_light']};
    font-weight: 600;
}}
QTableCornerButton::section {{ background: {PALETTE['navy']}; border: none; }}
QComboBox, QDoubleSpinBox {{
    background: {PALETTE['panel']};
    border: 1px solid {PALETTE['line']};
    border-radius: 6px;
    padding: 5px 8px;
    min-height: 20px;
}}
QComboBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {PALETTE['teal']}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QCheckBox {{ spacing: 8px; font-weight: 600; color: {PALETTE['navy']}; }}
QScrollArea {{ border: none; background: {PALETTE['canvas']}; }}
QScrollBar:vertical {{
    background: {PALETTE['canvas']}; width: 11px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #B9C6D4; border-radius: 5px; min-height: 30px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
"""

STATUS_COLOURS: Dict[str, Tuple[str, str]] = {
    "PASS": ("#E4F5E9", PALETTE["green"]),
    "OK": ("#E4F5E9", PALETTE["green"]),
    "WARNING": ("#FEF6DC", "#9C7A0B"),
    "ERROR": ("#FDE7E9", PALETTE["red"]),
}


# =====================================================================================
# PART 4.3  SHARED APPLICATION STATE
# The UI never calculates anything. It edits assumptions, asks the engine to rebuild the
# whole model, and displays whatever comes back.
# =====================================================================================
class AppState:
    """Holds the loaded history, the live assumptions and the current model output."""

    def __init__(self) -> None:
        self.hist: Optional[HistoricalModel] = None
        self.assumptions: Optional[AssumptionSet] = None
        self.effective: Optional[AssumptionSet] = None
        self.output: Optional[ModelOutput] = None
        self.scenario: str = "Base Case"
        self.paths: List[str] = []
        self.last_error: str = ""

    @property
    def loaded(self) -> bool:
        return self.hist is not None

    @property
    def ready(self) -> bool:
        return self.output is not None

    def load_files(self, paths: List[str]) -> None:
        self.hist = build_historical_model(paths)
        self.paths = list(paths)
        self.scenario = "Base Case"
        self.assumptions = build_scenario(forecast_years(self.hist.base_year),
                                         "Base Case")
        self.output = None

    def set_scenario(self, scenario: str) -> None:
        if self.hist is None or self.assumptions is None:
            return
        self.scenario = scenario
        if scenario == "Custom":
            self.assumptions.scenario = "Custom"
        else:
            methods = dict(self.assumptions.methods)
            settings = self.assumptions.settings.copy()
            self.assumptions = build_scenario(forecast_years(self.hist.base_year),
                                             scenario)
            self.assumptions.methods = methods
            self.assumptions.settings = settings

    def mark_custom(self) -> None:
        self.scenario = "Custom"
        if self.assumptions is not None:
            self.assumptions.scenario = "Custom"

    def recalculate(self) -> ModelOutput:
        """Rebuild the entire integrated model from the current assumptions."""
        if self.hist is None or self.assumptions is None:
            raise ValueError("No historical data has been loaded.")
        self.effective = apply_methodologies(self.hist, self.assumptions)
        self.effective.scenario = self.assumptions.scenario
        self.output = run_forecast(self.hist, self.effective)
        return self.output


# =====================================================================================
# PART 4.4  REUSABLE WIDGETS
# =====================================================================================
def make_card(title: str = "") -> Tuple[QFrame, QVBoxLayout]:
    """A white rounded panel with an optional caption. Returns (frame, body layout)."""
    card = QFrame()
    card.setObjectName("Card")
    outer = QVBoxLayout(card)
    outer.setContentsMargins(14, 12, 14, 14)
    outer.setSpacing(9)
    if title:
        caption = QLabel(title)
        caption.setObjectName("SectionCaption")
        outer.addWidget(caption)
    return card, outer


class Section(QWidget):
    """An expandable section, used to keep each page uncluttered."""

    def __init__(self, title: str, expanded: bool = True) -> None:
        super().__init__()
        self._title = title
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.toggle = QPushButton()
        self.toggle.setObjectName("Toggle")
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.clicked.connect(self._flip)
        layout.addWidget(self.toggle)

        self.body = QFrame()
        self.body.setObjectName("Card")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(14, 12, 14, 14)
        self.body_layout.setSpacing(10)
        layout.addWidget(self.body)

        self._expanded = expanded
        self._refresh()

    def _flip(self) -> None:
        self._expanded = not self._expanded
        self._refresh()

    def _refresh(self) -> None:
        arrow = "\u25BC" if self._expanded else "\u25B6"
        self.toggle.setText(f"  {arrow}   {self._title}")
        self.body.setVisible(self._expanded)

    def add(self, widget: QWidget) -> None:
        self.body_layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        self.body_layout.addLayout(layout)


class KpiCard(QFrame):
    """A single headline metric card."""

    def __init__(self, label: str, value: str, note: str = "",
                 accent: str = PALETTE["teal"]) -> None:
        super().__init__()
        self.setObjectName("Kpi")
        self.setStyleSheet(f"QFrame#Kpi {{ border-left: 5px solid {accent}; }}")
        self.setMinimumHeight(92)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(2)
        self.label = QLabel(label.upper())
        self.label.setObjectName("KpiLabel")
        self.value = QLabel(value)
        self.value.setObjectName("KpiValue")
        self.note = QLabel(note)
        self.note.setObjectName("KpiNote")
        self.note.setWordWrap(True)
        layout.addWidget(self.label)
        layout.addWidget(self.value)
        layout.addWidget(self.note)

    def update_card(self, value: str, note: str = "") -> None:
        self.value.setText(value)
        self.note.setText(note)


class DataFrameTable(QTableWidget):
    """Read-only table that renders a DataFrame, with subtotal and status highlighting."""

    def __init__(self, min_height: int = 200) -> None:
        super().__init__()
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)
        self.setMinimumHeight(min_height)
        self.setWordWrap(False)

    def load(self, frame: pd.DataFrame, corner: str = "Rs lakh", decimals: int = 0,
             status_column: Optional[str] = None,
             colour_fn=None, label_width: int = 300,
             show_index: bool = True) -> None:
        self.clear()
        if frame is None or frame.empty:
            self.setRowCount(1)
            self.setColumnCount(1)
            self.setHorizontalHeaderLabels(["Information"])
            self.setItem(0, 0, QTableWidgetItem("No data available."))
            return

        columns = [str(c) for c in frame.columns]
        offset = 1 if show_index else 0
        self.setRowCount(len(frame.index))
        self.setColumnCount(len(columns) + offset)
        headers = ([corner] if show_index else []) + columns
        self.setHorizontalHeaderLabels(headers)

        for row_index, label in enumerate(frame.index):
            text = str(label)
            is_subtotal = text.strip() in SUBTOTAL_ITEMS or text.isupper()
            if show_index:
                item = QTableWidgetItem("   " + text if text.startswith("  ") else text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft
                                      | Qt.AlignmentFlag.AlignVCenter)
                if is_subtotal:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setBackground(QBrush(QColor(PALETTE["band"])))
                self.setItem(row_index, 0, item)

            status = ""
            if status_column and status_column in frame.columns:
                status = str(frame.loc[label, status_column])

            for column_index, column in enumerate(frame.columns):
                raw = frame.loc[label, column]
                if isinstance(raw, (int, float, np.integer, np.floating)) \
                        and not pd.isna(raw):
                    display = f"{float(raw):,.{decimals}f}"
                    align = Qt.AlignmentFlag.AlignRight
                elif raw is None or (isinstance(raw, float) and pd.isna(raw)):
                    display = "-"
                    align = Qt.AlignmentFlag.AlignRight
                else:
                    display = str(raw)
                    align = (Qt.AlignmentFlag.AlignLeft if len(display) > 14
                             else Qt.AlignmentFlag.AlignRight)
                cell = QTableWidgetItem(display)
                cell.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if is_subtotal:
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)
                    cell.setBackground(QBrush(QColor(PALETTE["band"])))
                if status in STATUS_COLOURS:
                    background, foreground = STATUS_COLOURS[status]
                    cell.setBackground(QBrush(QColor(background)))
                    cell.setForeground(QBrush(QColor(foreground)))
                    if str(column) == status_column:
                        font = cell.font()
                        font.setBold(True)
                        cell.setFont(font)
                if colour_fn is not None:
                    colour = colour_fn(str(label), str(column), raw)
                    if colour is not None:
                        cell.setBackground(QBrush(QColor(*colour)))
                self.setItem(row_index, column_index + offset, cell)

        header = self.horizontalHeader()
        if show_index:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            self.setColumnWidth(0, label_width)
        for index in range(offset, self.columnCount()):
            header.setSectionResizeMode(index, QHeaderView.ResizeMode.Stretch)
        self.resizeRowsToContents()


class ChartCanvas(FigureCanvas):
    """A small matplotlib canvas styled to match the application."""

    def __init__(self, height: float = 2.7) -> None:
        self.figure_object = Figure(figsize=(5.4, height), dpi=100,
                                    facecolor=PALETTE["panel"])
        super().__init__(self.figure_object)
        self.setMinimumHeight(int(height * 100))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def plot(self, title: str, series_map: Dict[str, pd.Series],
             kinds: Optional[Dict[str, str]] = None, percent: bool = False,
             split_year: Optional[int] = None, ylabel: str = "Rs lakh") -> None:
        """Draw one chart. Bars and lines may be mixed on the same axes."""
        self.figure_object.clear()
        axes = self.figure_object.add_subplot(111)
        axes.set_facecolor(PALETTE["panel"])
        kinds = kinds or {}

        cleaned = {name: series.dropna() for name, series in series_map.items()
                   if series is not None and not series.dropna().empty}
        if not cleaned:
            axes.text(0.5, 0.5, "No data", ha="center", va="center",
                      color=PALETTE["muted"], transform=axes.transAxes)
            axes.set_axis_off()
            self.figure_object.tight_layout()
            self.draw()
            return

        years: List[int] = sorted({int(y) for series in cleaned.values()
                                   for y in series.index})
        positions = np.arange(len(years), dtype=float)
        bar_names = [n for n in cleaned if kinds.get(n, "bar") == "bar"]
        line_names = [n for n in cleaned if kinds.get(n, "bar") == "line"]
        width = 0.78 / max(len(bar_names), 1)

        for index, name in enumerate(bar_names):
            values = [float(cleaned[name].get(year, np.nan)) for year in years]
            shift = (index - (len(bar_names) - 1) / 2.0) * width
            axes.bar(positions + shift, values, width=width, label=name,
                     color=CHART_COLOURS[index % len(CHART_COLOURS)],
                     edgecolor="white", linewidth=0.6, zorder=3)

        for index, name in enumerate(line_names):
            values = [float(cleaned[name].get(year, np.nan)) for year in years]
            axes.plot(positions, values, marker="o", markersize=5, linewidth=2.2,
                      label=name,
                      color=CHART_COLOURS[(index + len(bar_names)) % len(CHART_COLOURS)],
                      zorder=4)

        if split_year is not None and split_year in years:
            boundary = years.index(split_year) + 0.5
            axes.axvspan(boundary, len(years) - 0.4, color=PALETTE["chip"],
                         alpha=0.55, zorder=1)
            axes.axvline(boundary, color=PALETTE["muted"], linewidth=1.0,
                         linestyle="--", zorder=2)

        axes.set_title(title, fontsize=11, fontweight="bold", color=PALETTE["navy"],
                       loc="left", pad=9)
        axes.set_xticks(positions)
        axes.set_xticklabels([f"FY{str(y)[-2:]}" for y in years], fontsize=9)
        axes.tick_params(axis="y", labelsize=9)
        axes.grid(axis="y", color=PALETTE["line"], linewidth=0.7, zorder=0)
        axes.set_axisbelow(True)
        for edge in ("top", "right"):
            axes.spines[edge].set_visible(False)
        for edge in ("left", "bottom"):
            axes.spines[edge].set_color(PALETTE["line"])

        if percent:
            axes.yaxis.set_major_formatter(
                matplotlib.ticker.FuncFormatter(lambda v, _: f"{v * 100:,.0f}%"))
        else:
            axes.yaxis.set_major_formatter(
                matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
            axes.set_ylabel(ylabel, fontsize=9, color=PALETTE["muted"])

        if len(cleaned) > 1:
            axes.legend(fontsize=8, frameon=False, ncol=min(len(cleaned), 3),
                        loc="upper left")
        self.figure_object.tight_layout()
        self.draw()


def page_heading(title: str, note: str) -> QWidget:
    holder = QWidget()
    layout = QVBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 4)
    layout.setSpacing(2)
    heading = QLabel(title)
    heading.setObjectName("PageTitle")
    caption = QLabel(note)
    caption.setObjectName("PageNote")
    caption.setWordWrap(True)
    layout.addWidget(heading)
    layout.addWidget(caption)
    return holder


def scroll_page() -> Tuple[QWidget, QVBoxLayout]:
    """A vertically scrolling page body. Returns (scroll area, content layout)."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    holder = QWidget()
    layout = QVBoxLayout(holder)
    layout.setContentsMargins(16, 14, 16, 18)
    layout.setSpacing(12)
    area.setWidget(holder)
    return area, layout


def labelled(text: str, widget: QWidget) -> QWidget:
    """A small inline control with a caption above it."""
    holder = QWidget()
    layout = QVBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(3)
    caption = QLabel(text.upper())
    caption.setObjectName("KpiLabel")
    layout.addWidget(caption)
    layout.addWidget(widget)
    return holder


# =====================================================================================
# PART 4.5  PAGE 1 - IMPORT, DIFFERENCES AND EDITING
# =====================================================================================
class DifferenceTable(QTableWidget):
    """Read-only list of every place where the uploaded figure and the figure used
    in the model differ, or where a row could not be recognised. It reports the
    facts only; corrections are made in the editable grid below it."""

    COLUMNS = ["Statement", "Line item", "Financial year", "Uploaded value",
               "Imported value", "Difference", "What we found", "Likely cause"]

    def __init__(self) -> None:
        super().__init__()
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)
        self.setMinimumHeight(280)
        self.setWordWrap(False)

    def load(self, frame: pd.DataFrame) -> None:
        self.clear()
        if frame is None or frame.empty:
            self.setRowCount(1)
            self.setColumnCount(1)
            self.setHorizontalHeaderLabels(["Result"])
            item = QTableWidgetItem(
                "No differences were found. Every uploaded figure agrees with the "
                "figure used in the model.")
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.setItem(0, 0, item)
            self.setColumnWidth(0, 720)
            return

        data = frame.reset_index(drop=True)
        self.setRowCount(len(data))
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)

        for row in range(len(data)):
            record = data.iloc[row]
            unrecognised = str(record.get("Line item", "")).startswith("[Unrecognised]")
            for col, name in enumerate(self.COLUMNS):
                text = str(record.get(name, ""))
                cell = QTableWidgetItem(text)
                cell.setToolTip(text)
                cell.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                if name in ("Uploaded value", "Imported value", "Difference",
                            "Financial year"):
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                          | Qt.AlignmentFlag.AlignVCenter)
                else:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignLeft
                                          | Qt.AlignmentFlag.AlignVCenter)
                if unrecognised:
                    cell.setBackground(QBrush(QColor("#FEF6DC")))
                self.setItem(row, col, cell)

        widths = [95, 240, 70, 100, 100, 90, 300, 320]
        for col, width in enumerate(widths[:self.columnCount()]):
            self.setColumnWidth(col, width)
        self.resizeRowsToContents()


class EditableStatementTable(QTableWidget):
    """A read and write grid onto one standardised historical statement. Bold subtotal
    rows are always recalculated automatically and cannot be typed into."""

    def __init__(self) -> None:
        super().__init__()
        self.verticalHeader().setVisible(True)
        self.setMinimumHeight(420)
        self._years: List[int] = []
        self._items: List[str] = []

    def load(self, frame: pd.DataFrame) -> None:
        self.clear()
        if frame is None or frame.empty:
            self._years, self._items = [], []
            self.setRowCount(1)
            self.setColumnCount(1)
            self.setHorizontalHeaderLabels(["Information"])
            self.setItem(0, 0, QTableWidgetItem("No data available."))
            return

        self._years = [int(c) for c in frame.columns]
        self._items = [str(i) for i in frame.index]
        self.setRowCount(len(self._items))
        self.setColumnCount(len(self._years))
        self.setHorizontalHeaderLabels([f"FY{str(y)[-2:]}" for y in self._years])
        self.setVerticalHeaderLabels(self._items)

        for row, item in enumerate(self._items):
            is_subtotal = item.strip() in SUBTOTAL_ITEMS
            for col, year in enumerate(self._years):
                raw = frame.loc[frame.index[row], frame.columns[col]]
                value = 0.0 if pd.isna(raw) else float(raw)
                cell = QTableWidgetItem(f"{value:,.2f}")
                cell.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                      | Qt.AlignmentFlag.AlignVCenter)
                if is_subtotal:
                    cell.setFlags(Qt.ItemFlag.ItemIsEnabled
                                  | Qt.ItemFlag.ItemIsSelectable)
                    cell.setBackground(QBrush(QColor(PALETTE["band"])))
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)
                else:
                    cell.setFlags(Qt.ItemFlag.ItemIsEnabled
                                  | Qt.ItemFlag.ItemIsSelectable
                                  | Qt.ItemFlag.ItemIsEditable)
                self.setItem(row, col, cell)

        for col in range(len(self._years)):
            self.setColumnWidth(col, 120)
        self.verticalHeader().setMinimumWidth(290)
        self.resizeRowsToContents()

    def edited_values(self) -> Dict[Tuple[str, int], float]:
        """Every editable cell whose text parses as a number."""
        out: Dict[Tuple[str, int], float] = {}
        for row, item in enumerate(self._items):
            if item.strip() in SUBTOTAL_ITEMS:
                continue
            for col, year in enumerate(self._years):
                cell = self.item(row, col)
                if cell is None:
                    continue
                text = cell.text().replace(",", "").strip()
                if not text or text == "-":
                    continue
                try:
                    out[(item, int(year))] = float(text)
                except ValueError:
                    continue
        return out


class ImportPage(QWidget):
    """Import historical statements, see exactly where the upload and the model
    differ, and correct any figure directly in the editable grid."""

    def __init__(self, state: AppState, on_loaded, on_updated) -> None:
        super().__init__()
        self.state = state
        self.on_loaded = on_loaded
        self.on_updated = on_updated

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        area, body = scroll_page()
        outer.addWidget(area)

        body.addWidget(page_heading(
            "Import historical financial statements",
            "Select between one and ten Excel workbooks. Line items are identified by "
            "statement name, line-item name and financial year, so column positions "
            "and wording may differ between files and no cell references are used.",
        ))

        card, layout = make_card("Data source")
        buttons = QHBoxLayout()
        buttons.setSpacing(9)
        self.select_button = QPushButton("Select Excel files...")
        self.select_button.clicked.connect(self._choose_files)
        buttons.addWidget(self.select_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.status = QLabel("No files loaded yet.")
        self.status.setObjectName("PageNote")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        body.addWidget(card)

        self.totals_section = Section(
            "Totals reconciliation (uploaded against imported)", True)
        self.recon_table = DataFrameTable(170)
        self.totals_section.add(self.recon_table)
        body.addWidget(self.totals_section)

        self.difference_section = Section(
            "Differences found between uploaded and imported data", True)
        difference_note = QLabel(
            "Each row below shows one figure that does not agree, identified by "
            "statement, line item and financial year, or one row whose wording could "
            "not be recognised. Correct anything that matters in the editable grid "
            "below, then re-check.")
        difference_note.setObjectName("PageNote")
        difference_note.setWordWrap(True)
        self.difference_section.add(difference_note)

        difference_controls = QHBoxLayout()
        self.recheck_button = QPushButton("Re-check differences")
        self.recheck_button.setObjectName("Secondary")
        self.recheck_button.clicked.connect(self._refresh_differences)
        difference_controls.addWidget(self.recheck_button)
        difference_controls.addStretch(1)
        self.difference_section.add_layout(difference_controls)

        self.difference_table = DifferenceTable()
        self.difference_section.add(self.difference_table)
        self.difference_result = QLabel("")
        self.difference_result.setObjectName("PageNote")
        self.difference_result.setWordWrap(True)
        self.difference_section.add(self.difference_result)
        body.addWidget(self.difference_section)

        self.checklist_section = Section("Technical checklist (for reference)", False)
        self.checklist_table = DataFrameTable(220)
        self.checklist_section.add(self.checklist_table)
        body.addWidget(self.checklist_section)

        self.edit_section = Section(
            "Edit imported data (correct any import issue directly)", True)
        edit_controls = QHBoxLayout()
        self.edit_choice = QComboBox()
        self.edit_choice.addItems(
            ["P&L", "Balance Sheet", "Cash Flow", "Schedules", "Equity"])
        self.edit_choice.currentTextChanged.connect(self._load_editable)
        edit_controls.addWidget(labelled("Statement", self.edit_choice))
        edit_controls.addStretch(1)
        self.revert_button = QPushButton("Discard unsaved changes")
        self.revert_button.setObjectName("Secondary")
        self.revert_button.clicked.connect(self._load_editable)
        edit_controls.addWidget(self.revert_button)
        self.save_edits_button = QPushButton("Save changes and recalculate")
        self.save_edits_button.setObjectName("Accent")
        self.save_edits_button.clicked.connect(self._save_edits)
        edit_controls.addWidget(self.save_edits_button)
        self.edit_section.add_layout(edit_controls)
        edit_note = QLabel(
            "Every number is editable except the bold subtotal rows, which are always "
            "recalculated automatically so the statements keep balancing. Saving "
            "rebuilds the whole forecast from the corrected history.")
        edit_note.setObjectName("PageNote")
        edit_note.setWordWrap(True)
        self.edit_section.add(edit_note)
        self.editable_table = EditableStatementTable()
        self.edit_section.add(self.editable_table)
        self.edit_result = QLabel("")
        self.edit_result.setObjectName("PageNote")
        self.edit_result.setWordWrap(True)
        self.edit_section.add(self.edit_result)
        body.addWidget(self.edit_section)

        self.preview_section = Section("Imported data preview", False)
        controls = QHBoxLayout()
        self.preview_choice = QComboBox()
        self.preview_choice.addItems(
            ["P&L", "Balance Sheet", "Cash Flow", "Schedules", "Equity",
             "Standardised records"])
        self.preview_choice.currentTextChanged.connect(self._refresh_preview)
        controls.addWidget(labelled("View", self.preview_choice))
        controls.addStretch(1)
        self.preview_section.add_layout(controls)
        self.preview_table = DataFrameTable(300)
        self.preview_section.add(self.preview_table)
        body.addWidget(self.preview_section)

        body.addStretch(1)

    # ---- loading ---------------------------------------------------------------------
    def _choose_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select historical financial statements", "",
            "Excel workbooks (*.xlsx *.xlsm);;All files (*)")
        if paths:
            if len(paths) > 10:
                QMessageBox.warning(self, APP_NAME,
                                    "Please select no more than ten workbooks.")
                return
            self._load(paths)

    def _load(self, paths: List[str]) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.state.load_files(paths)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self, APP_NAME,
                "The financial data could not be imported.\n\n"
                + type(exc).__name__ + ": " + str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()

        hist = self.state.hist
        errors = sum(1 for level, _ in hist.messages if level == "ERROR")
        warnings = sum(1 for level, _ in hist.messages if level == "WARNING")
        loaded = "  ".join("\u2713 FY" + str(y) + " loaded" for y in hist.years)
        self.status.setText(
            "<b>" + hist.company + "</b><br>" + loaded + "<br>"
            + format(hist.record_count(), ",") + " standardised data points from "
            + str(len(hist.source_files)) + " file(s). "
            + str(warnings) + " warning(s), " + str(errors) + " error(s). "
            + "Base year for the forecast: FY" + str(hist.base_year) + ".")

        self.recon_table.load(reconciliation_frame(hist), corner="Statement",
                              decimals=2, label_width=220)
        self.checklist_table.load(validation_frame(hist), corner="Check",
                                  status_column="Status", label_width=330)
        self.edit_result.setText("")
        self._refresh_differences()
        self._load_editable()
        self._refresh_preview()
        self.on_loaded()

    # ---- differences -------------------------------------------------------------------
    def _refresh_differences(self) -> None:
        hist = self.state.hist
        if hist is None:
            return
        issues = field_level_reconciliation(hist)
        self.difference_table.load(issues)
        self.recon_table.load(reconciliation_frame(hist), corner="Statement",
                              decimals=2, label_width=220)
        if issues.empty:
            self.difference_result.setText(
                "No differences remain between the uploaded files and the model.")
        else:
            unrecognised = sum(
                1 for value in issues["Line item"]
                if str(value).startswith("[Unrecognised]"))
            mismatched = len(issues) - unrecognised
            self.difference_result.setText(
                str(mismatched) + " figure(s) differ from the uploaded workbooks and "
                + str(unrecognised) + " uploaded row(s) were not recognised. Rows "
                "shaded amber were left out of the forecast entirely.")

    # ---- editable grid ------------------------------------------------------------------
    def _load_editable(self) -> None:
        hist = self.state.hist
        if hist is None:
            return
        self.editable_table.load(hist.frame(self.edit_choice.currentText()))

    def _save_edits(self) -> None:
        hist = self.state.hist
        if hist is None:
            QMessageBox.information(self, APP_NAME,
                                    "Please import at least one workbook first.")
            return
        statement = self.edit_choice.currentText()
        changes = self.editable_table.edited_values()
        applied = 0
        for (item, year), value in changes.items():
            current = hist.value(statement, item, year)
            if abs(current - value) > 1e-6:
                hist.set_value(statement, item, year, value,
                               note="Manual edit on the Import page")
                applied += 1

        if not applied:
            self.edit_result.setText("No changes were detected, so nothing was saved.")
            return

        hist.recompute_subtotals()
        self.edit_result.setText(
            str(applied) + " figure(s) saved to the " + statement + ". Subtotals have "
            "been recalculated and the forecast has been rebuilt. "
            + str(len(hist.edit_log)) + " manual edit(s) recorded in this session.")
        self._load_editable()
        self._refresh_differences()
        self._refresh_preview()
        self.on_updated()

    # ---- raw preview ---------------------------------------------------------------------
    def _refresh_preview(self) -> None:
        hist = self.state.hist
        if hist is None:
            return
        choice = self.preview_choice.currentText()
        if choice == "Standardised records":
            tidy = hist.tidy.copy()
            columns = ["financial_year", "statement", "line_item", "value", "unit",
                       "source_label", "source_file"]
            tidy = tidy[[c for c in columns if c in tidy.columns]].head(400)
            tidy.index = range(1, len(tidy) + 1)
            self.preview_table.load(tidy, corner="#", decimals=1, label_width=60)
        else:
            self.preview_table.load(hist.frame(choice), corner="Rs lakh", decimals=1,
                                    label_width=330)


# =====================================================================================
# PART 4.6  PAGE 2 - HISTORICAL ANALYSIS
# =====================================================================================
class HistoricalPage(QWidget):
    """Comparative statements and the full historical trend analysis."""

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        area, body = scroll_page()
        outer.addWidget(area)

        self.heading = page_heading("Historical analysis", "Load financial data first.")
        body.addWidget(self.heading)

        card, layout = make_card("Presentation")
        controls = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItems(list(DISPLAY_MODES))
        self.mode.currentTextChanged.connect(self.refresh)
        controls.addWidget(labelled("Units", self.mode))
        controls.addStretch(1)
        layout.addLayout(controls)
        body.addWidget(card)

        self.pnl_section = Section("Profit and loss", True)
        self.pnl_table = DataFrameTable(320)
        self.pnl_section.add(self.pnl_table)
        body.addWidget(self.pnl_section)

        self.bs_section = Section("Balance sheet", False)
        self.bs_table = DataFrameTable(420)
        self.bs_section.add(self.bs_table)
        body.addWidget(self.bs_section)

        self.cf_section = Section("Cash flow", False)
        self.cf_table = DataFrameTable(220)
        self.cf_section.add(self.cf_table)
        body.addWidget(self.cf_section)

        self.trend_section = Section("Trend analysis", True)
        trend_controls = QHBoxLayout()
        self.group = QComboBox()
        self.group.addItems(list(RATIO_GROUPS.keys()))
        self.group.currentTextChanged.connect(self._refresh_trends)
        trend_controls.addWidget(labelled("Ratio group", self.group))
        trend_controls.addStretch(1)
        self.trend_section.add_layout(trend_controls)
        self.ratio_table = DataFrameTable(240)
        self.trend_section.add(self.ratio_table)

        charts = QGridLayout()
        charts.setSpacing(10)
        self.chart_growth = ChartCanvas(2.7)
        self.chart_margin = ChartCanvas(2.7)
        self.chart_wc = ChartCanvas(2.7)
        self.chart_cash = ChartCanvas(2.7)
        for index, canvas in enumerate(
                [self.chart_growth, self.chart_margin, self.chart_wc, self.chart_cash]):
            frame, inner = make_card()
            inner.addWidget(canvas)
            charts.addWidget(frame, index // 2, index % 2)
        self.trend_section.add_layout(charts)
        body.addWidget(self.trend_section)

        body.addStretch(1)

    def refresh(self) -> None:
        hist = self.state.hist
        if hist is None:
            return
        mode = self.mode.currentText()
        decimals = 0
        self.pnl_table.load(comparative_pnl(hist, mode), corner=mode,
                            decimals=decimals, label_width=300)
        self.bs_table.load(comparative_balance_sheet(hist, mode), corner=mode,
                           label_width=300)
        self.cf_table.load(comparative_cash_flow(hist, mode), corner=mode,
                           label_width=320)
        self.heading.layout().itemAt(1).widget().setText(
            f"{hist.company}. Historical years "
            f"{', '.join('FY' + str(y) for y in hist.years)}, all figures originally in "
            f"{hist.unit}. Growth is the compound rate across the period.")
        self._refresh_trends()

    def _refresh_trends(self) -> None:
        hist = self.state.hist
        if hist is None:
            return
        self.ratio_table.load(ratio_display_frame(hist, self.group.currentText()),
                              corner="Ratio", label_width=320)
        ratios = historical_ratios(hist)

        self.chart_growth.plot(
            "Revenue and EBITDA growth",
            {"Revenue growth": ratios.loc["Revenue growth"],
             "EBITDA growth": ratios.loc["EBITDA growth"]},
            kinds={"Revenue growth": "bar", "EBITDA growth": "line"}, percent=True)
        self.chart_margin.plot(
            "Margins",
            {"EBITDA margin": ratios.loc["EBITDA margin"],
             "EBIT margin": ratios.loc["EBIT margin"],
             "PAT margin": ratios.loc["PAT margin"]},
            kinds={"EBITDA margin": "bar", "EBIT margin": "line",
                   "PAT margin": "line"}, percent=True)
        self.chart_wc.plot(
            "Working capital days",
            {"Receivable days": ratios.loc["Receivable days"],
             "Inventory days": ratios.loc["Inventory days"],
             "Payable days": ratios.loc["Payable days"]},
            kinds={"Receivable days": "bar", "Inventory days": "bar",
                   "Payable days": "bar"}, ylabel="Days")
        self.chart_cash.plot(
            "Cash generation",
            {"CFO": ratios.loc["CFO"], "Free cash flow": ratios.loc["Free cash flow"],
             "Net debt": ratios.loc["Net debt"]},
            kinds={"CFO": "bar", "Free cash flow": "bar", "Net debt": "line"})


# ---------------------------------------------------------------------------------
# END OF PART 4A.
# Paste PART 4B (assumptions page, results dashboard, checks and export, main window
# and the application entry point) beneath this line.
# ---------------------------------------------------------------------------------
# =====================================================================================
# PART 4.7  ADDITIONAL IMPORT
# Explicitly load the ticker submodule used by the chart axis formatters.
# =====================================================================================
import matplotlib.ticker  # noqa: E402


# =====================================================================================
# PART 4.8  PAGE 3 - FORECAST AND ASSUMPTIONS
# Editing any cell writes back to the AssumptionSet and triggers a full rebuild of the
# integrated model, so a single change flows through every statement and ratio.
# =====================================================================================
class AssumptionsPage(QWidget):

    def __init__(self, state: AppState, on_changed) -> None:
        super().__init__()
        self.state = state
        self.on_changed = on_changed
        self._loading = False
        self._editors: Dict[Tuple[str, int], QDoubleSpinBox] = {}
        self._methods: Dict[str, QComboBox] = {}

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(260)
        self._timer.timeout.connect(self._commit)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        area, body = scroll_page()
        outer.addWidget(area)

        self.heading = page_heading(
            "Forecast assumptions",
            "Load financial data first.")
        body.addWidget(self.heading)

        card, layout = make_card("Scenario and model settings")
        row_one = QHBoxLayout()
        row_one.setSpacing(12)
        self.scenario = QComboBox()
        self.scenario.addItems(list(SCENARIOS))
        self.scenario.currentTextChanged.connect(self._scenario_changed)
        row_one.addWidget(labelled("Scenario", self.scenario))

        self.minimum_cash = QDoubleSpinBox()
        self.minimum_cash.setRange(0.0, 1e7)
        self.minimum_cash.setDecimals(0)
        self.minimum_cash.setSingleStep(100.0)
        self.minimum_cash.setValue(500.0)
        self.minimum_cash.valueChanged.connect(self._settings_changed)
        row_one.addWidget(labelled("Minimum cash (Rs lakh)", self.minimum_cash))

        self.depreciation = QComboBox()
        self.depreciation.addItems(list(DEPRECIATION_METHODS))
        self.depreciation.currentTextChanged.connect(self._settings_changed)
        row_one.addWidget(labelled("Depreciation methodology", self.depreciation))

        self.useful_life = QDoubleSpinBox()
        self.useful_life.setRange(1.0, 60.0)
        self.useful_life.setDecimals(1)
        self.useful_life.setValue(10.0)
        self.useful_life.valueChanged.connect(self._settings_changed)
        row_one.addWidget(labelled("Useful life (years)", self.useful_life))
        row_one.addStretch(1)
        layout.addLayout(row_one)

        row_two = QHBoxLayout()
        row_two.setSpacing(16)
        self.sweep = QCheckBox("Cash sweep / funding plug: ON")
        self.sweep.setChecked(True)
        self.sweep.stateChanged.connect(self._sweep_changed)
        row_two.addWidget(self.sweep)
        self.tax_credit = QCheckBox("Recognise a tax credit on losses")
        self.tax_credit.stateChanged.connect(self._settings_changed)
        row_two.addWidget(self.tax_credit)
        self.reset_button = QPushButton("Reset to scenario defaults")
        self.reset_button.setObjectName("Secondary")
        self.reset_button.clicked.connect(self._reset)
        row_two.addWidget(self.reset_button)
        row_two.addStretch(1)
        layout.addLayout(row_two)

        self.scenario_note = QLabel("")
        self.scenario_note.setObjectName("PageNote")
        self.scenario_note.setWordWrap(True)
        layout.addWidget(self.scenario_note)
        body.addWidget(card)

        
        self.recalc_local = QPushButton("Recalculate model")
        self.recalc_local.setObjectName("Accent")
        self.recalc_local.clicked.connect(self._commit)
        layout.addWidget(self.recalc_local)

        self.grid_section = Section("Assumption grid", True)
        note = QLabel(
            "Percentages are entered as percentages and days as days. Choosing a "
            "methodology other than Manual derives the assumption from the historical "
            "accounts and locks the cells for that row.")
        note.setObjectName("PageNote")
        note.setWordWrap(True)
        self.grid_section.add(note)
        self.grid = QTableWidget()
        self.grid.setMinimumHeight(560)
        self.grid.verticalHeader().setVisible(False)
        self.grid_section.add(self.grid)
        body.addWidget(self.grid_section)

        self.driver_section = Section("Calculation drivers", False)
        self.driver_table = DataFrameTable(300)
        self.driver_section.add(self.driver_table)
        body.addWidget(self.driver_section)

        body.addStretch(1)

    # ---- construction ----------------------------------------------------------------
    def rebuild(self) -> None:
        """Build the editable grid for the current forecast years."""
        assumptions = self.state.assumptions
        hist = self.state.hist
        if assumptions is None or hist is None:
            return
        self._loading = True
        self._editors.clear()
        self._methods.clear()

        years = assumptions.years
        self.grid.clear()
        self.grid.setRowCount(len(PARAM_KEYS) + len(PARAM_GROUPS))
        self.grid.setColumnCount(2 + len(years))
        self.grid.setHorizontalHeaderLabels(
            ["Assumption", "Methodology"] + [f"FY{str(y)[-2:]}" for y in years])

        row = 0
        for group in PARAM_GROUPS:
            banner = QTableWidgetItem(group.upper())
            font = banner.font()
            font.setBold(True)
            banner.setFont(font)
            banner.setBackground(QBrush(QColor(PALETTE["navy"])))
            banner.setForeground(QBrush(QColor("#FFFFFF")))
            self.grid.setItem(row, 0, banner)
            for column in range(1, self.grid.columnCount()):
                filler = QTableWidgetItem("")
                filler.setBackground(QBrush(QColor(PALETTE["navy"])))
                self.grid.setItem(row, column, filler)
            row += 1

            for key in [k for k in PARAM_KEYS if PARAMS[k].group == group]:
                spec = PARAMS[key]
                label = QTableWidgetItem(spec.editor_label)
                label.setToolTip(spec.driver)
                self.grid.setItem(row, 0, label)

                combo = QComboBox()
                if spec.trend_capable:
                    combo.addItems(list(FORECAST_METHODS))
                else:
                    combo.addItems(["Manual"])
                combo.setCurrentText(assumptions.method(key))
                combo.currentTextChanged.connect(
                    lambda text, k=key: self._method_changed(k, text))
                self._methods[key] = combo
                self.grid.setCellWidget(row, 1, combo)

                for offset, year in enumerate(years):
                    editor = QDoubleSpinBox()
                    editor.setDecimals(spec.decimals())
                    editor.setRange(spec.to_display(spec.lo), spec.to_display(spec.hi))
                    editor.setSingleStep(1.0 if spec.kind != "amount" else 50.0)
                    editor.setValue(spec.to_display(assumptions.get(key, year)))
                    editor.setAlignment(Qt.AlignmentFlag.AlignRight)
                    editor.valueChanged.connect(
                        lambda value, k=key, y=year: self._value_changed(k, y, value))
                    self._editors[(key, year)] = editor
                    self.grid.setCellWidget(row, 2 + offset, editor)
                row += 1

        header = self.grid.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.grid.setColumnWidth(0, 300)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.grid.setColumnWidth(1, 160)
        for index in range(2, self.grid.columnCount()):
            header.setSectionResizeMode(index, QHeaderView.ResizeMode.Stretch)
        self.grid.resizeRowsToContents()

        settings = assumptions.settings
        self.minimum_cash.setValue(settings.minimum_cash)
        self.depreciation.setCurrentText(settings.depreciation_method)
        self.useful_life.setValue(settings.useful_life)
        self.sweep.setChecked(settings.cash_sweep)
        self.tax_credit.setChecked(settings.tax_credit_on_loss)
        self.scenario.setCurrentText(self.state.scenario)

        self.heading.layout().itemAt(1).widget().setText(
            f"{hist.company}. Forecast period "
            f"{', '.join('FY' + str(y) for y in years)}, built forward from the "
            f"FY{hist.base_year} actual balance sheet. Any change recalculates the "
            f"complete model automatically.")
        self.scenario_note.setText(SCENARIO_NOTES.get(self.state.scenario, ""))
        self._loading = False
        self._apply_locks()

    def _apply_locks(self) -> None:
        """Grey out rows whose values are derived from history."""
        assumptions = self.state.assumptions
        if assumptions is None:
            return
        for key in PARAM_KEYS:
            manual = assumptions.method(key) == "Manual"
            for year in assumptions.years:
                editor = self._editors.get((key, year))
                if editor is not None:
                    editor.setEnabled(manual)
                    editor.setStyleSheet(
                        "" if manual else f"background: {PALETTE['band']}; "
                                          f"color: {PALETTE['muted']};")

    def refresh_derived(self) -> None:
        """Show the values the engine actually used, including derived rows."""
        effective = self.state.effective
        assumptions = self.state.assumptions
        if effective is None or assumptions is None:
            return
        self._loading = True
        for key in PARAM_KEYS:
            if assumptions.method(key) == "Manual":
                continue
            spec = PARAMS[key]
            for year in assumptions.years:
                editor = self._editors.get((key, year))
                if editor is not None:
                    editor.setValue(spec.to_display(effective.get(key, year)))
        self._loading = False
        self.driver_table.load(effective.to_frame().drop(columns=[]),
                               corner="Assumption", decimals=2, label_width=300)

    # ---- events ----------------------------------------------------------------------
    def _value_changed(self, key: str, year: int, value: float) -> None:
        if self._loading or self.state.assumptions is None:
            return
        self.state.assumptions.set(key, year, PARAMS[key].from_display(float(value)))
        self.state.mark_custom()
        self._loading = True
        self.scenario.setCurrentText("Custom")
        self._loading = False
        self.scenario_note.setText(SCENARIO_NOTES["Custom"])
        self._timer.start()

    def _method_changed(self, key: str, method: str) -> None:
        if self._loading or self.state.assumptions is None:
            return
        self.state.assumptions.set_method(key, method)
        self._apply_locks()
        self._timer.start()

    def _settings_changed(self, *_args) -> None:
        if self._loading or self.state.assumptions is None:
            return
        settings = self.state.assumptions.settings
        settings.minimum_cash = float(self.minimum_cash.value())
        settings.depreciation_method = self.depreciation.currentText()
        settings.useful_life = float(self.useful_life.value())
        settings.tax_credit_on_loss = self.tax_credit.isChecked()
        self._timer.start()

    def _sweep_changed(self, *_args) -> None:
        if self.state.assumptions is None:
            return
        self.state.assumptions.settings.cash_sweep = self.sweep.isChecked()
        self.sweep.setText("Cash sweep / funding plug: "
                           + ("ON" if self.sweep.isChecked() else "OFF"))
        if not self._loading:
            self._timer.start()

    def _scenario_changed(self, scenario: str) -> None:
        if self._loading or self.state.hist is None:
            return
        self.state.set_scenario(scenario)
        self.rebuild()
        self._commit()

    def _reset(self) -> None:
        if self.state.hist is None:
            return
        scenario = self.state.scenario if self.state.scenario != "Custom" else "Base Case"
        self.state.set_scenario(scenario)
        self.state.scenario = scenario
        self.rebuild()
        self._commit()

    def _commit(self) -> None:
        self.on_changed()


# =====================================================================================
# PART 4.9  PAGE 4 - RESULTS
# =====================================================================================
class ResultsPage(QWidget):

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self._cards: List[KpiCard] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        area, body = scroll_page()
        outer.addWidget(area)

        self.heading = page_heading("Forecast results", "Load financial data first.")
        body.addWidget(self.heading)

        kpi_card, kpi_layout = make_card("Management dashboard")
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(10)
        kpi_layout.addLayout(self.kpi_grid)
        body.addWidget(kpi_card)

        self.chart_section = Section("Charts", True)
        chart_controls = QHBoxLayout()
        self.view = QComboBox()
        self.view.addItems(["Historical + forecast", "Historical only", "Forecast only"])
        self.view.currentTextChanged.connect(self._refresh_charts)
        chart_controls.addWidget(labelled("Period shown", self.view))
        chart_controls.addStretch(1)
        self.chart_section.add_layout(chart_controls)

        grid = QGridLayout()
        grid.setSpacing(10)
        self.charts: List[ChartCanvas] = []
        for index in range(8):
            canvas = ChartCanvas(2.6)
            frame, inner = make_card()
            inner.addWidget(canvas)
            grid.addWidget(frame, index // 2, index % 2)
            self.charts.append(canvas)
        self.chart_section.add_layout(grid)
        body.addWidget(self.chart_section)

        self.statement_section = Section("Forecast statements", True)
        statement_controls = QHBoxLayout()
        self.statement = QComboBox()
        self.statement.addItems(["P&L", "Balance Sheet", "Cash Flow", "Ratios"])
        self.statement.currentTextChanged.connect(self._refresh_statements)
        statement_controls.addWidget(labelled("Statement", self.statement))
        self.include_history = QCheckBox("Include historical years")
        self.include_history.setChecked(True)
        self.include_history.stateChanged.connect(self._refresh_statements)
        statement_controls.addWidget(self.include_history)
        statement_controls.addStretch(1)
        self.statement_section.add_layout(statement_controls)
        self.statement_table = DataFrameTable(420)
        self.statement_section.add(self.statement_table)
        body.addWidget(self.statement_section)

        self.schedule_section = Section("Supporting schedules", False)
        schedule_controls = QHBoxLayout()
        self.schedule = QComboBox()
        self.schedule.addItems(["PPE Schedule", "Working Capital Schedule",
                                "Debt Schedule", "Tax Schedule", "Equity Schedule"])
        self.schedule.currentTextChanged.connect(self._refresh_schedules)
        schedule_controls.addWidget(labelled("Schedule", self.schedule))
        schedule_controls.addStretch(1)
        self.schedule_section.add_layout(schedule_controls)
        self.schedule_table = DataFrameTable(320)
        self.schedule_section.add(self.schedule_table)
        body.addWidget(self.schedule_section)

        self.sensitivity_section = Section("Sensitivity analysis", False)
        sens_controls = QHBoxLayout()
        drivers = [k for k in PARAM_KEYS if PARAMS[k].trend_capable]
        self.sens_choice = QComboBox()
        self.sens_choice.addItems([grid_spec["title"]
                                   for grid_spec in STANDARD_SENSITIVITIES]
                                  + ["Custom pair"])
        self.sens_choice.currentTextChanged.connect(self._sens_choice_changed)
        sens_controls.addWidget(labelled("Grid", self.sens_choice))
        self.sens_row = QComboBox()
        self.sens_col = QComboBox()
        for combo in (self.sens_row, self.sens_col):
            for key in drivers:
                combo.addItem(PARAMS[key].label, key)
        self.sens_row.setCurrentIndex(0)
        self.sens_col.setCurrentIndex(min(2, self.sens_col.count() - 1))
        sens_controls.addWidget(labelled("Rows", self.sens_row))
        sens_controls.addWidget(labelled("Columns", self.sens_col))
        self.sens_metric = QComboBox()
        self.sens_metric.addItems(list(SENSITIVITY_METRICS))
        sens_controls.addWidget(labelled("Metric", self.sens_metric))
        self.sens_button = QPushButton("Run sensitivity")
        self.sens_button.clicked.connect(self._run_sensitivity)
        sens_controls.addWidget(self.sens_button)
        sens_controls.addStretch(1)
        self.sensitivity_section.add_layout(sens_controls)
        self.sens_note = QLabel("Each cell re-runs the complete integrated model.")
        self.sens_note.setObjectName("PageNote")
        self.sens_note.setWordWrap(True)
        self.sensitivity_section.add(self.sens_note)
        self.sens_table = DataFrameTable(240)
        self.sensitivity_section.add(self.sens_table)
        body.addWidget(self.sensitivity_section)

        body.addStretch(1)
        self._sens_choice_changed(self.sens_choice.currentText())

    # ---- refresh ---------------------------------------------------------------------
    def refresh(self) -> None:
        output = self.state.output
        hist = self.state.hist
        if output is None or hist is None:
            return
        self.heading.layout().itemAt(1).widget().setText(
            f"{hist.company}. Scenario: {output.scenario}. Forecast "
            f"FY{output.years[0]} to FY{output.terminal_year}, all figures in "
            f"{BASE_UNIT}. Every figure below is derived from the same dependency chain.")

        cards = kpi_cards(hist, output)
        if len(self._cards) != len(cards):
            while self.kpi_grid.count():
                item = self.kpi_grid.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self._cards = []
            for index, (label, value, note) in enumerate(cards):
                card = KpiCard(label, value, note,
                               CHART_COLOURS[index % len(CHART_COLOURS)])
                self.kpi_grid.addWidget(card, index // 4, index % 4)
                self._cards.append(card)
        else:
            for card, (label, value, note) in zip(self._cards, cards):
                card.label.setText(label.upper())
                card.update_card(value, note)

        self._refresh_charts()
        self._refresh_statements()
        self._refresh_schedules()

    def _refresh_charts(self) -> None:
        output = self.state.output
        hist = self.state.hist
        if output is None or hist is None:
            return
        view = self.view.currentText()
        series = dashboard_series(hist, output, view)
        split = hist.base_year if view == "Historical + forecast" else None

        self.charts[0].plot("Revenue and EBITDA",
                            {"Revenue": series["Revenue"], "EBITDA": series["EBITDA"]},
                            kinds={"Revenue": "bar", "EBITDA": "bar"},
                            split_year=split)
        self.charts[1].plot("EBITDA margin",
                            {"EBITDA margin": series["EBITDA margin"]},
                            kinds={"EBITDA margin": "line"}, percent=True,
                            split_year=split)
        self.charts[2].plot("Profit after tax", {"PAT": series["PAT"]},
                            kinds={"PAT": "bar"}, split_year=split)
        self.charts[3].plot("CFO versus capex",
                            {"CFO": series["CFO"], "Capex": series["Capex"],
                             "Free cash flow": series["Free cash flow"]},
                            kinds={"CFO": "bar", "Capex": "bar",
                                   "Free cash flow": "line"},
                            split_year=split)
        self.charts[4].plot("Closing cash", {"Closing cash": series["Closing cash"]},
                            kinds={"Closing cash": "bar"}, split_year=split)
        self.charts[5].plot("Net debt", {"Net debt": series["Net debt"]},
                            kinds={"Net debt": "line"}, split_year=split)
        self.charts[6].plot("Working capital",
                            {"Working capital": series["Working capital"]},
                            kinds={"Working capital": "bar"}, split_year=split)
        self.charts[7].plot("Revenue growth",
                            {"Revenue growth": series["Revenue growth"]},
                            kinds={"Revenue growth": "bar"}, percent=True,
                            split_year=split)

    def _refresh_statements(self) -> None:
        output = self.state.output
        hist = self.state.hist
        if output is None or hist is None:
            return
        choice = self.statement.currentText()
        include = self.include_history.isChecked()

        if choice == "Ratios":
            frame = combined_ratios(hist, output) if include else output.ratios
            display = frame.copy()
            display.columns = [f"FY{str(int(c))[-2:]}" for c in display.columns]
            rows: List[str] = []
            data: List[List[str]] = []
            for group, names in RATIO_GROUPS.items():
                available = [n for n in names if n in display.index]
                if not available:
                    continue
                rows.append(group.upper())
                data.append(["" for _ in display.columns])
                for name in available:
                    rows.append(name)
                    data.append([format_value(display.loc[name, column],
                                              RATIO_KINDS.get(name, "amount"))
                                 for column in display.columns])
            table = pd.DataFrame(data, index=rows, columns=list(display.columns))
            self.statement_table.load(table, corner="Ratio", label_width=320)
            return

        if include:
            combined = combined_model(hist, output)
            frame = combined.frame(choice)
        else:
            frame = output.frame(choice)
        display = frame.copy()
        display.columns = [f"FY{str(int(c))[-2:]}" for c in display.columns]
        self.statement_table.load(display, corner="Rs lakh", decimals=0,
                                  label_width=320)

    def _refresh_schedules(self) -> None:
        output = self.state.output
        if output is None:
            return
        frame = output.frame(self.schedule.currentText()).copy()
        frame.columns = [f"FY{str(int(c))[-2:]}" for c in frame.columns]
        self.schedule_table.load(frame, corner="Rs lakh", decimals=1, label_width=320)

    # ---- sensitivity -----------------------------------------------------------------
    def _sens_choice_changed(self, title: str) -> None:
        custom = title == "Custom pair"
        self.sens_row.setEnabled(custom)
        self.sens_col.setEnabled(custom)
        self.sens_metric.setEnabled(custom)
        if not custom:
            for spec in STANDARD_SENSITIVITIES:
                if spec["title"] == title:
                    self.sens_row.setCurrentText(PARAMS[spec["row_key"]].label)
                    self.sens_col.setCurrentText(PARAMS[spec["col_key"]].label)
                    self.sens_metric.setCurrentText(spec["metric"])
                    break

    def _run_sensitivity(self) -> None:
        hist = self.state.hist
        effective = self.state.effective
        if hist is None or effective is None:
            return
        title = self.sens_choice.currentText()
        spec = next((s for s in STANDARD_SENSITIVITIES if s["title"] == title), None)

        if spec is not None:
            row_key, col_key = spec["row_key"], spec["col_key"]
            row_deltas, col_deltas = spec["row_deltas"], spec["col_deltas"]
            metric = spec["metric"]
        else:
            row_key = self.sens_row.currentData()
            col_key = self.sens_col.currentData()
            metric = self.sens_metric.currentText()
            if row_key == col_key:
                QMessageBox.information(
                    self, APP_NAME,
                    "Please choose two different drivers for the rows and columns.")
                return

            def steps(key: str) -> List[float]:
                kind = PARAMS[key].kind
                if kind == "percent":
                    return [-0.04, -0.02, 0.0, 0.02, 0.04]
                if kind == "days":
                    return [-10.0, -5.0, 0.0, 5.0, 10.0]
                return [-500.0, -250.0, 0.0, 250.0, 500.0]

            row_deltas, col_deltas = steps(row_key), steps(col_key)

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            grid = sensitivity_table(hist, effective, row_key, row_deltas,
                                     col_key, col_deltas, metric)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, APP_NAME,
                                 f"The sensitivity could not be produced.\n\n{exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        values = grid.to_numpy(dtype=float)
        finite = values[np.isfinite(values)]
        low = float(finite.min()) if finite.size else 0.0
        high = float(finite.max()) if finite.size else 1.0
        kind = METRIC_KIND.get(metric, "amount")

        display = pd.DataFrame(
            [[format_metric(grid.loc[r, c], metric) for c in grid.columns]
             for r in grid.index],
            index=grid.index, columns=grid.columns)

        lookup = {(str(r), str(c)): float(grid.loc[r, c])
                  for r in grid.index for c in grid.columns}

        def colour(row_label: str, column: str, _value) -> Optional[Tuple[int, int, int]]:
            raw = lookup.get((row_label, column))
            return None if raw is None else heatmap_colour(raw, low, high)

        self.sens_table.load(display, corner=f"{PARAMS[row_key].label} / "
                                             f"{PARAMS[col_key].label}",
                             colour_fn=colour, label_width=200)
        year = self.state.output.terminal_year if self.state.output else 0
        unit = "" if kind == "percent" else " (Rs lakh)"
        self.sens_note.setText(
            f"FY{str(year)[-2:]} {metric}{unit}. Rows vary {PARAMS[row_key].label.lower()}, "
            f"columns vary {PARAMS[col_key].label.lower()}. Range "
            f"{format_metric(low, metric)} to {format_metric(high, metric)}. "
            f"{values.size} full model runs.")


# =====================================================================================
# PART 4.10  PAGE 5 - CHECKS AND EXPORT
# =====================================================================================
class ChecksPage(QWidget):

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        area, body = scroll_page()
        outer.addWidget(area)

        self.heading = page_heading("Model checks and export",
                                    "Load financial data first.")
        body.addWidget(self.heading)

        card, layout = make_card("Status")
        self.banner = QLabel("No forecast has been calculated yet.")
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet(
            f"background: {PALETTE['band']}; border-radius: 8px; padding: 12px; "
            f"font-weight: 700; color: {PALETTE['navy']};")
        layout.addWidget(self.banner)

        buttons = QHBoxLayout()
        buttons.setSpacing(9)
        self.export_button = QPushButton("Export forecast to Excel")
        self.export_button.clicked.connect(self._export)
        self.test_button = QPushButton("Run built-in self tests")
        self.test_button.setObjectName("Secondary")
        self.test_button.clicked.connect(self._self_tests)
        buttons.addWidget(self.export_button)
        buttons.addWidget(self.test_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        body.addWidget(card)

        self.check_section = Section("Integrity checks", True)
        self.check_table = DataFrameTable(420)
        self.check_section.add(self.check_table)
        body.addWidget(self.check_section)

        self.test_section = Section("Self test results", False)
        self.test_table = DataFrameTable(300)
        self.test_section.add(self.test_table)
        body.addWidget(self.test_section)

        body.addStretch(1)

    def refresh(self) -> None:
        output = self.state.output
        if output is None:
            return
        passes, warnings, errors = check_counts(output.checks)
        residues = [abs(output.value("Balance Sheet", "Balance Check", y))
                    for y in output.years]
        worst = max(residues) if residues else 0.0
        if worst < TOL:
            verdict = "Model Balanced"
            colour = PALETTE["green"]
            background = "#E4F5E9"
        else:
            verdict = f"Model Out of Balance by Rs {worst:,.2f} lakh"
            colour = PALETTE["red"]
            background = "#FDE7E9"
        self.banner.setText(
            f"{verdict}  |  {passes} checks passed, {warnings} warnings, "
            f"{errors} errors  |  Scenario: {output.scenario}  |  "
            f"Circularity solver: "
            f"{'converged' if output.converged else 'did not converge'}")
        self.banner.setStyleSheet(
            f"background: {background}; border-radius: 8px; padding: 12px; "
            f"font-weight: 700; color: {colour};")
        self.check_table.load(output.checks, corner="Check", status_column="Status",
                              label_width=340)
        self.heading.layout().itemAt(1).widget().setText(
            "Every reconciliation is shown below. An imbalance is always reported and "
            "never hidden, and a forecast containing critical errors cannot be exported "
            "without an explicit confirmation.")

    def _export(self) -> None:
        hist = self.state.hist
        output = self.state.output
        effective = self.state.effective
        if hist is None or output is None or effective is None:
            QMessageBox.information(self, APP_NAME,
                                    "Please import data and calculate a forecast first.")
            return

        if has_critical_errors(output.checks):
            failed = output.checks[output.checks["Status"] == "ERROR"]["Check"].tolist()
            answer = QMessageBox.warning(
                self, APP_NAME,
                "This forecast contains critical errors:\n\n"
                + "\n".join(f"  \u2022  {name}" for name in failed[:8])
                + "\n\nExporting is not recommended. Continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return

        suggested = os.path.join(os.path.expanduser("~"),
                                 default_export_name(hist, output))
        path, _ = QFileDialog.getSaveFileName(
            self, "Export forecast", suggested, "Excel workbook (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            export_forecast(path, hist, output, effective)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, APP_NAME,
                                 f"The workbook could not be written.\n\n"
                                 f"{type(exc).__name__}: {exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        QMessageBox.information(
            self, APP_NAME,
            "The forecast was exported successfully.\n\n"
            "Eleven sheets were written, covering the assumptions, the historical and "
            "forecast statements, the supporting schedules, the ratios and the model "
            f"checks.\n\n{path}")

    def _self_tests(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            frame = run_self_tests()
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, APP_NAME, f"The tests could not run.\n\n{exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        self.test_table.load(frame, corner="Test", status_column="Status",
                             label_width=340)
        self.test_section._expanded = True
        self.test_section._refresh()
        passed, failed = self_test_summary(frame)
        icon = (QMessageBox.Icon.Information if failed == 0
                else QMessageBox.Icon.Warning)
        box = QMessageBox(self)
        box.setIcon(icon)
        box.setWindowTitle(APP_NAME)
        box.setText(f"{passed} tests passed and {failed} failed.")
        box.setInformativeText(
            "The suite proves the parser, the three statements, every roll-forward, the "
            "propagation of each key assumption, the funding plug, the scenarios and the "
            "Excel export." if failed == 0
            else "Please review the failures listed in the Self test results section.")
        box.exec()


# =====================================================================================
# PART 4.11  MAIN WINDOW
# =====================================================================================
class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.state = AppState()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1420, 940)
        self.setMinimumSize(1120, 720)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- banner -------------------------------------------------------------------
        banner = QFrame()
        banner.setObjectName("Banner")
        banner.setFixedHeight(74)
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(20, 12, 20, 12)
        banner_layout.setSpacing(16)

        titles = QVBoxLayout()
        titles.setSpacing(1)
        title = QLabel(APP_NAME)
        title.setObjectName("AppTitle")
        subtitle = QLabel("Integrated five-year forecasting - profit and loss, balance "
                          "sheet, cash flow and supporting schedules, fully linked")
        subtitle.setObjectName("AppSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        banner_layout.addLayout(titles)
        banner_layout.addStretch(1)

        self.status_label = QLabel("Import historical statements to begin.")
        self.status_label.setObjectName("AppSubtitle")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight
                                      | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMaximumWidth(460)
        banner_layout.addWidget(self.status_label)

        self.recalc_button = QPushButton("Recalculate model (moved to Forecast tab)")
        self.recalc_button.setObjectName("Accent")
        self.recalc_button.setEnabled(False)
        self.recalc_button.setEnabled(False)
        
        layout.addWidget(banner)

        # ---- tabs ---------------------------------------------------------------------
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs)

        self.import_page = ImportPage(self.state, self._on_loaded,
                                      self._on_data_updated)
        self.historical_page = HistoricalPage(self.state)
        self.assumptions_page = AssumptionsPage(self.state, self.recalculate)
        self.results_page = ResultsPage(self.state)
        self.checks_page = ChecksPage(self.state)

        self.tabs.addTab(self.import_page, "  1  Import  ")
        self.tabs.addTab(self.historical_page, "  2  Historical Analysis  ")
        self.tabs.addTab(self.assumptions_page, "  3  Forecast & Assumptions  ")
        self.tabs.addTab(self.results_page, "  4  Results  ")
        self.tabs.addTab(self.checks_page, "  5  Checks & Export  ")
        for index in range(1, 5):
            pass  # demo-tab-disable removed

    # ---- coordination ------------------------------------------------------------------
    def _on_loaded(self) -> None:
        """Called once history has been imported successfully."""
        for index in range(1, 5):
            self.tabs.setTabEnabled(index, True)
        
        self.historical_page.refresh()
        self.assumptions_page.rebuild()
        self.recalculate()
        self.tabs.setCurrentIndex(1)

    def _on_data_updated(self) -> None:
        """Called after the historical data has been corrected or edited in place,
        without moving the user away from the Import tab."""
        if not self.state.loaded:
            return
        self.historical_page.refresh()
        self.assumptions_page.rebuild()
        self.recalculate()

    def recalculate(self) -> None:
        """Rebuild the whole model, then refresh every dependent page."""
        if not self.state.loaded:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            output = self.state.recalculate()
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self.state.last_error = f"{type(exc).__name__}: {exc}"
            self.status_label.setText("The model could not be calculated.")
            QMessageBox.critical(
                self, APP_NAME,
                f"The forecast could not be calculated.\n\n{self.state.last_error}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        self.assumptions_page.refresh_derived()
        self.results_page.refresh()
        self.checks_page.refresh()

        passes, warnings, errors = check_counts(output.checks)
        residues = [abs(output.value("Balance Sheet", "Balance Check", y))
                    for y in output.years]
        worst = max(residues) if residues else 0.0
        verdict = ("Model Balanced" if worst < TOL
                   else f"Out of balance by Rs {worst:,.2f} lakh")
        self.status_label.setText(
            f"{self.state.hist.company}  |  FY{output.years[0]}-FY{output.terminal_year}"
            f"  |  {output.scenario}  |  {verdict}  |  {passes} pass, "
            f"{warnings} warn, {errors} error")


# =====================================================================================
# PART 4.12  ENTRY POINT
# =====================================================================================
def launch() -> int:
    """Start the application. Safe to call repeatedly from IDLE."""
    # #region agent log
    _agent_dbg("D", "Cash_Flow_Forecasting_Pro_FINAL.py:launch", "launch_entered", {})
    # #endregion
    application = QApplication.instance() or QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setStyleSheet(STYLESHEET)
    base_font = QFont("Helvetica Neue" if sys.platform == "darwin" else "Segoe UI", 10)
    application.setFont(base_font)

    window = MainWindow()
    window.show()

    global _WINDOW
    _WINDOW = window  # keep a reference so the window is not garbage collected

    print("-" * 74)
    print(f"{APP_NAME} {APP_VERSION} is running.")
    print("If the window is not visible, check the Dock or use Mission Control;")
    print("on macOS a Qt window occasionally opens behind IDLE.")
    print("-" * 74)
    return application.exec()


_WINDOW: Optional[QMainWindow] = None

if __name__ == "__main__":
    # #region agent log
    _src = open(__file__, encoding="utf-8").read()
    _agent_dbg("A", "Cash_Flow_Forecasting_Pro_FINAL.py:main", "main_guard", {"test_mode": "--test" in sys.argv, "future_import_count": _src.count("from __future__ import annotations"), "lines": _src.count("\\n")+1})
    # #endregion
    if "--test" in sys.argv:
        print_self_tests()
    else:
        try:
            sys.exit(launch())
        except SystemExit:
            raise
        except Exception:
            print("The application stopped unexpectedly:\n")
            traceback.print_exc()
            print("\nIf a library is missing, run this once in Terminal:")
            print("  " + MANUAL_INSTALL_LINE)
