#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 MF X-RAY  --  AI-Powered Mutual Fund Portfolio Intelligence & Risk Analysis
================================================================================

 ICAI AI Level 2 Capstone Project
 Version : 1.0.0 (Prototype)

 ONE-LINE INSTALL (run this in a terminal if automatic installation below
 ever fails):

    pip install pandas numpy matplotlib openpyxl python-docx

 HOW TO RUN
 ----------
   1. Save this file as MF_XRay.py
   2. Open it in IDLE (or double-click it, or run "python MF_XRay.py")
   3. Press F5 (or just run it)
   4. The application window opens
   5. Click "Load Demo Portfolio" on the Dashboard to explore every module

 IMPORTANT
 ---------
 This application ships with a built-in SAMPLE / DEMO mutual-fund dataset.
 The funds, NAVs, returns, holdings and historical prices are entirely
 FICTIONAL and created only to demonstrate the analytics in this tool.
 They must NOT be treated as real market data, and nothing produced by this
 application is investment advice.

 CODE ORGANISATION (all in this one file, top to bottom)
 ---------------------------------------------------------------------------
   1.  Dependency installation
   2.  Imports
   3.  Configuration (app info, colours, assumptions, thresholds)
   4.  Sample / demo data (funds, holdings, sectors, synthetic NAV history)
   5.  Data models (Fund, PortfolioEntry, Portfolio)
   6.  Financial calculations (allocation, effective exposure, overlap...)
   7.  Risk calculations (volatility, Sharpe ratio, max drawdown)
   8.  Concentration & Portfolio Health Score
   9.  Alert engine (rule-based)
  10.  AI insight / explainability engine (rule-based NLG + Q&A)
  11.  What-if simulator
  12.  SIP analysis (XIRR)
  13.  Report generation (Excel + Word)
  14.  GUI components (Tkinter application)
  15.  Application startup
 ---------------------------------------------------------------------------
"""

# =============================================================================
# SECTION 1 : DEPENDENCY INSTALLATION
# -----------------------------------------------------------------------------
# This block runs BEFORE any optional third-party library is imported. If a
# required package is missing, it is installed automatically with pip and
# execution continues. tkinter is part of the Python standard library and
# cannot be installed with pip, so it is handled separately with a clear
# message if it is not available.
# =============================================================================
import sys
import subprocess
import importlib

# module import name -> pip package name
_REQUIRED_PACKAGES = {
    "pandas": "pandas",
    "numpy": "numpy",
    "matplotlib": "matplotlib",
    "openpyxl": "openpyxl",
    "docx": "python-docx",
}


def _ensure_dependencies():
    """Check every required third-party package and pip-install any that
    are missing before the rest of the application imports them."""
    missing_pip_names = []
    for module_name, pip_name in _REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing_pip_names.append(pip_name)

    if missing_pip_names:
        print("MF X-Ray: installing missing packages -> " + ", ".join(missing_pip_names))
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing_pip_names])
            print("MF X-Ray: package installation complete.")
        except Exception as exc:  # pragma: no cover - environment specific
            print("MF X-Ray: automatic installation failed (%s)." % exc)
            print("Please install the missing packages manually, for example:")
            print("    pip install " + " ".join(missing_pip_names))
            sys.exit(1)


_ensure_dependencies()

# tkinter ships with standard Python installers on Windows/macOS. On some
# Linux distributions it must be installed via the OS package manager
# (e.g. "sudo apt install python3-tk"), since it is not a pip package.
try:
    import tkinter  # noqa: F401
except ImportError:  # pragma: no cover - environment specific
    print("=" * 70)
    print("ERROR: The 'tkinter' module was not found in this Python installation.")
    print("tkinter is part of the Python standard library and ships with the")
    print("official Windows and macOS installers from python.org.")
    print("On Linux, install it with your package manager, for example:")
    print("    Ubuntu/Debian : sudo apt install python3-tk")
    print("    Fedora        : sudo dnf install python3-tkinter")
    print("Then re-run this application.")
    print("=" * 70)
    sys.exit(1)

# =============================================================================
# SECTION 2 : IMPORTS
# =============================================================================
import math
import zlib
import traceback
from datetime import datetime, date, timedelta

from tkinter import (
    Tk, Toplevel, Frame, LabelFrame, Label, Button, Entry, Text, Canvas,
    Scrollbar, StringVar, DoubleVar, BooleanVar, END, BOTH, LEFT,
    RIGHT, TOP, BOTTOM, X, Y, W, E, N, S, NW, CENTER, HORIZONTAL, VERTICAL,
    DISABLED, NORMAL,
)
from tkinter import ttk, messagebox, filedialog, font as tkfont

import pandas as pd
import numpy as np

import openpyxl
from openpyxl.styles import Font as XLFont, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

# matplotlib is imported, but the Tk-specific backend is initialised lazily
# (see _ensure_mpl_backend in Section 14) so that this application still
# starts and remains fully usable -- with tables instead of charts -- on a
# machine where the Tk/Agg graphics backend cannot be initialised.
import matplotlib
matplotlib.use("Agg")  # safe default; switched to TkAgg lazily when a chart is first drawn
import matplotlib.pyplot as plt


# =============================================================================
# SECTION 3 : CONFIGURATION
# =============================================================================
APP_NAME = "MF X-Ray"
APP_FULL_TITLE = "MF X-RAY"
APP_SUBTITLE = "AI-Powered Mutual Fund Portfolio Intelligence & Risk Analysis"
APP_VERSION = "1.0.0 (Prototype)"
DEMO_DATA_LABEL = "DEMO DATA / SAMPLE DATA"

DISCLAIMER_SHORT = (
    "This application is intended for educational and analytical purposes only. "
    "It does not constitute investment advice or a recommendation to buy, hold "
    "or sell any security or mutual fund."
)

DISCLAIMER_FULL = (
    "MF X-Ray is an educational and analytical portfolio-intelligence tool. "
    "The calculations and analytical scores generated by this application are "
    "for demonstration and decision-support purposes only and should not be "
    "interpreted as investment advice, a guarantee of future returns, or a "
    "recommendation to buy, hold or sell any mutual fund or security."
)

DEMO_DATA_DISCLAIMER = (
    "Demo Data: The mutual-fund and market data included in this prototype are "
    "illustrative/sample data and should not be treated as current market "
    "information."
)

# ----- Colour palette (professional financial-dashboard style) -------------
COLORS = {
    "bg": "#F4F6F9",
    "sidebar": "#12233F",
    "sidebar_active": "#1B3A63",
    "sidebar_text": "#E7EDF6",
    "header_bg": "#0E1B33",
    "accent": "#1F6FEB",
    "accent_dark": "#124C9C",
    "green": "#1E8E5A",
    "red": "#C0392B",
    "amber": "#B7791F",
    "card_bg": "#FFFFFF",
    "text_dark": "#1B2430",
    "text_muted": "#5B6675",
    "border": "#D7DEE8",
}

RISK_BUCKET_COLORS = {
    "Low": COLORS["green"],
    "Moderate": COLORS["amber"],
    "High": COLORS["red"],
}

# ----- User-configurable analytical assumptions -----------------------------
# Every assumption used anywhere in a calculation is defined here, in one
# place, so it is visible and (where practical) editable from the GUI.
ASSUMPTIONS = {
    "risk_free_rate_pct": 6.0,      # used for Sharpe Ratio -- editable in Risk Analysis tab
    "nav_history_months": 60,       # length of the simulated sample NAV history
    "sip_fallback_growth_pct": 10.0,  # assumed annual growth used ONLY when a SIP
                                       # simulation runs beyond the sample NAV history
}

# ----- MF X-Ray analytical thresholds (NOT official regulatory limits) -----
# Labelled everywhere in the UI/reports as "MF X-Ray Analytical Threshold".
THRESHOLDS = {
    "high_overlap_pct": 40.0,             # fund-pair overlap considered "high"
    "high_stock_exposure_pct": 8.0,       # single-stock effective exposure considered "high"
    "high_sector_exposure_pct": 30.0,     # single-sector effective exposure considered "high"
    "high_fund_concentration_pct": 40.0,  # single fund's share of the portfolio considered "high"
    "top5_concentration_watch_pct": 40.0,
    "top10_concentration_watch_pct": 60.0,
}

METHODOLOGY_OVERLAP_TEXT = (
    "MF X-Ray Overlap Methodology: for any two funds, the overlap percentage "
    "is the sum, across every company held by BOTH funds, of the SMALLER of "
    "the two portfolio weights for that company. A value of 100% would mean "
    "the two funds are identical in composition; 0% means they share no "
    "common holdings. This is a portfolio-similarity measure created for "
    "this application and is not an official / regulatory calculation."
)

METHODOLOGY_HEALTH_TEXT = (
    "MF X-Ray Portfolio Health Score is an analytical score out of 100, built "
    "from six transparent, independently-visible components: Diversification "
    "(20), Fund Overlap (20), Stock Concentration (20), Sector Concentration "
    "(15), Volatility (15) and Maximum Drawdown (10). Each component is scored "
    "from the portfolio's own calculated metrics against a reference point "
    "defined inside this application (shown alongside each component). This "
    "is an MF X-Ray analytical score created for this application and is NOT "
    "an official rating from any regulator, AMC or rating agency."
)


def clamp(value, lo, hi):
    """Constrain a numeric value to the inclusive range [lo, hi]."""
    return max(lo, min(hi, value))


def format_inr(amount, decimals=0):
    """Format a number using the Indian numbering system (lakh/crore commas)
    with a Rupee symbol, e.g. 1234567 -> '₹12,34,567'."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return str(amount)
    negative = amount < 0
    amount = abs(amount)
    whole = f"{amount:.{decimals}f}"
    int_part, _, dec_part = whole.partition(".")
    if len(int_part) > 3:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        int_part = ",".join(groups) + "," + last3
    text = "₹" + int_part + (("." + dec_part) if decimals else "")
    return ("-" + text) if negative else text


def format_pct(value, decimals=1):
    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return str(value)


def safe_div(numerator, denominator, default=0.0):
    try:
        if denominator in (0, 0.0, None):
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default


def stable_seed(text, salt=0):
    """A deterministic (non-random-per-run) integer seed derived from a
    string, used only to generate the reproducible sample NAV history."""
    return (zlib.crc32(text.encode("utf-8")) + salt) % (2 ** 31)


# =============================================================================
# SECTION 4 : SAMPLE / DEMO DATA
# -----------------------------------------------------------------------------
# Every company, sector, fund name and holding below is FICTIONAL and created
# purely to demonstrate the analytics in this application. Overlapping
# holdings between funds are deliberately included so that the Portfolio
# X-Ray, Overlap Analyzer and Sector Analysis modules produce meaningful,
# demonstrable results.
#
# Design note for future versions: this section is the ONLY place that needs
# to change to plug in real / official mutual-fund data (see Section 15,
# "Future Version Architecture"). Every calculation downstream reads funds
# through the FUNDS dictionary of Fund objects, never these raw literals
# directly, so a real data-loader only needs to populate the same structure.
# =============================================================================

TODAY = date.today()
PORTFOLIO_DATE = date(TODAY.year, TODAY.month, 1) - timedelta(days=1)  # last day of previous month

# ----- Fictional companies grouped by sector --------------------------------
COMPANY_SECTOR_MAP = {
    "Northbridge Bank": "Financial Services",
    "Sunrise Finance Corp": "Financial Services",
    "Capital Shield Insurance": "Financial Services",
    "Meridian Housing Finance": "Financial Services",
    "Bluepeak Software": "Information Technology",
    "Innoware Technologies": "Information Technology",
    "Digitronics Systems": "Information Technology",
    "Vitalcure Pharma": "Healthcare",
    "Wellmed Labs": "Healthcare",
    "Genexa Healthcare": "Healthcare",
    "Everyday Consumables": "Consumer Goods",
    "Radiant FMCG": "Consumer Goods",
    "Urban Retail Mart": "Consumer Goods",
    "Ironforge Engineering": "Industrials",
    "Skyline Infra Projects": "Industrials",
    "Precision Auto Components": "Industrials",
    "Sunfield Energy": "Energy",
    "Novagen Power": "Energy",
    "Orbit Telecom": "Telecommunications",
    "Granite Cement Works": "Materials",
    "Alloycraft Metals": "Materials",
}

# ----- Fund metadata ---------------------------------------------------------
# risk_level must be one of: "Low", "Moderately Low", "Moderate",
# "Moderately High", "High", "Very High"  (used for sample-volatility mapping)
FUND_META = {
    "Growth Equity Fund": {
        "category": "Equity - Multi Cap Fund",
        "nav": 45.32, "aum_cr": 3200, "expense_ratio_pct": 1.85,
        "return_1y_pct": 18.4, "cagr_3y_pct": 21.7, "cagr_5y_pct": 16.9,
        "risk_level": "Very High", "equity_pct": 96.0, "debt_pct": 2.0, "cash_pct": 2.0,
        "benchmark": "Nifty 500 TRI", "portfolio_date": PORTFOLIO_DATE,
    },
    "Bluechip Equity Fund": {
        "category": "Equity - Large Cap Fund",
        "nav": 78.10, "aum_cr": 5400, "expense_ratio_pct": 1.65,
        "return_1y_pct": 14.2, "cagr_3y_pct": 16.8, "cagr_5y_pct": 14.1,
        "risk_level": "High", "equity_pct": 94.0, "debt_pct": 3.0, "cash_pct": 3.0,
        "benchmark": "Nifty 100 TRI", "portfolio_date": PORTFOLIO_DATE,
    },
    "Balanced Advantage Fund": {
        "category": "Hybrid - Dynamic Asset Allocation Fund",
        "nav": 32.55, "aum_cr": 2100, "expense_ratio_pct": 1.55,
        "return_1y_pct": 11.1, "cagr_3y_pct": 12.4, "cagr_5y_pct": 10.8,
        "risk_level": "Moderate", "equity_pct": 65.0, "debt_pct": 30.0, "cash_pct": 5.0,
        "benchmark": "CRISIL Hybrid 50+50 Moderate Index", "portfolio_date": PORTFOLIO_DATE,
    },
    "Flexi Cap Fund": {
        "category": "Equity - Flexi Cap Fund",
        "nav": 56.90, "aum_cr": 2850, "expense_ratio_pct": 1.75,
        "return_1y_pct": 16.9, "cagr_3y_pct": 19.3, "cagr_5y_pct": 15.6,
        "risk_level": "Very High", "equity_pct": 92.0, "debt_pct": 4.0, "cash_pct": 4.0,
        "benchmark": "Nifty 500 TRI", "portfolio_date": PORTFOLIO_DATE,
    },
    "Mid Cap Growth Fund": {
        "category": "Equity - Mid Cap Fund",
        "nav": 61.25, "aum_cr": 1650, "expense_ratio_pct": 1.95,
        "return_1y_pct": 22.6, "cagr_3y_pct": 24.8, "cagr_5y_pct": 18.2,
        "risk_level": "Very High", "equity_pct": 97.0, "debt_pct": 1.0, "cash_pct": 2.0,
        "benchmark": "Nifty Midcap 150 TRI", "portfolio_date": PORTFOLIO_DATE,
    },
}

# ----- Underlying holdings (company -> weight %, as % of total fund corpus) -
# Weights deliberately overlap across funds. The remainder up to each fund's
# Equity % is bucketed as "Other Equity Holdings" (not individually named),
# which mirrors how real factsheets show only the top holdings.
FUND_HOLDINGS = {
    "Growth Equity Fund": {
        "Northbridge Bank": 8.5, "Bluepeak Software": 7.2, "Vitalcure Pharma": 6.1,
        "Everyday Consumables": 5.4, "Ironforge Engineering": 4.8, "Sunrise Finance Corp": 4.5,
        "Innoware Technologies": 4.0, "Sunfield Energy": 3.6, "Skyline Infra Projects": 3.2,
        "Urban Retail Mart": 2.9,
    },
    "Bluechip Equity Fund": {
        "Northbridge Bank": 9.1, "Sunrise Finance Corp": 6.8, "Bluepeak Software": 6.0,
        "Capital Shield Insurance": 5.5, "Vitalcure Pharma": 5.2, "Everyday Consumables": 4.9,
        "Digitronics Systems": 4.1, "Orbit Telecom": 3.5, "Radiant FMCG": 3.0,
        "Ironforge Engineering": 2.6,
    },
    "Balanced Advantage Fund": {
        "Northbridge Bank": 5.0, "Bluepeak Software": 4.2, "Wellmed Labs": 3.8,
        "Everyday Consumables": 3.3, "Meridian Housing Finance": 3.0, "Sunfield Energy": 2.6,
        "Precision Auto Components": 2.2, "Granite Cement Works": 1.9, "Urban Retail Mart": 1.7,
        "Innoware Technologies": 1.5,
    },
    "Flexi Cap Fund": {
        "Bluepeak Software": 8.8, "Northbridge Bank": 6.4, "Genexa Healthcare": 5.9,
        "Innoware Technologies": 5.1, "Skyline Infra Projects": 4.6, "Sunrise Finance Corp": 4.2,
        "Radiant FMCG": 3.8, "Novagen Power": 3.3, "Alloycraft Metals": 2.7,
        "Digitronics Systems": 2.4,
    },
    "Mid Cap Growth Fund": {
        "Skyline Infra Projects": 6.5, "Precision Auto Components": 5.8, "Genexa Healthcare": 5.2,
        "Novagen Power": 4.7, "Granite Cement Works": 4.1, "Wellmed Labs": 3.6,
        "Orbit Telecom": 3.2, "Urban Retail Mart": 2.9, "Ironforge Engineering": 2.6,
        "Innoware Technologies": 2.3,
    },
}

# Sample-volatility mapping used only to generate the synthetic NAV history
_RISK_MONTHLY_SIGMA = {
    "Low": 0.012, "Moderately Low": 0.018, "Moderate": 0.028,
    "Moderately High": 0.042, "High": 0.052, "Very High": 0.065,
}


def _generate_sample_nav_history(months=None):
    """Builds a reproducible, clearly-synthetic monthly NAV history for every
    sample fund, ending at each fund's Portfolio Date with its stated current
    NAV. This is SAMPLE / SIMULATED data for demonstration only -- it is not
    a real historical price series."""
    months = months or ASSUMPTIONS["nav_history_months"]
    history = {}
    for name, meta in FUND_META.items():
        rng = np.random.default_rng(stable_seed(name))
        annual_return = meta["cagr_3y_pct"] / 100.0
        monthly_mu = (1.0 + annual_return) ** (1.0 / 12.0) - 1.0
        monthly_sigma = _RISK_MONTHLY_SIGMA.get(meta["risk_level"], 0.04)

        shocks = rng.normal(loc=monthly_mu, scale=monthly_sigma, size=months)
        # Build the series backwards from the known current NAV so the
        # series ends exactly at today's stated NAV.
        navs_forward_factors = np.cumprod(1.0 + shocks)
        end_nav = meta["nav"]
        start_nav = end_nav / navs_forward_factors[-1]
        nav_values = [start_nav] + list(start_nav * navs_forward_factors)

        end_date = pd.Timestamp(meta["portfolio_date"])
        dates = pd.date_range(end=end_date, periods=months + 1, freq="ME")
        history[name] = pd.Series(nav_values, index=dates, name=name)
    return history


FUND_NAV_HISTORY = _generate_sample_nav_history()


# =============================================================================
# SECTION 5 : DATA MODELS
# =============================================================================
class Fund:
    """A single mutual-fund scheme: metadata + underlying holdings.

    Holding this as a small class (rather than raw dicts scattered through
    the app) is what lets Section 15 ("Future Version Architecture") swap in
    a real data source later without touching any calculation function --
    every calculation below reads Fund objects, never the sample dicts
    directly.
    """

    def __init__(self, name, meta, holdings):
        self.name = name
        self.category = meta["category"]
        self.nav = float(meta["nav"])
        self.aum_cr = float(meta["aum_cr"])
        self.expense_ratio_pct = float(meta["expense_ratio_pct"])
        self.return_1y_pct = float(meta["return_1y_pct"])
        self.cagr_3y_pct = float(meta["cagr_3y_pct"])
        self.cagr_5y_pct = float(meta["cagr_5y_pct"])
        self.risk_level = meta["risk_level"]
        self.equity_pct = float(meta["equity_pct"])
        self.debt_pct = float(meta["debt_pct"])
        self.cash_pct = float(meta["cash_pct"])
        self.benchmark = meta["benchmark"]
        self.portfolio_date = meta["portfolio_date"]
        # {company_name: weight_pct_of_fund_corpus}
        self.holdings = dict(holdings)

    @property
    def named_holdings_pct(self):
        return sum(self.holdings.values())

    @property
    def other_holdings_pct(self):
        return max(0.0, self.equity_pct - self.named_holdings_pct)

    def top_holdings(self, n=10):
        return sorted(self.holdings.items(), key=lambda kv: kv[1], reverse=True)[:n]

    def sector_allocation(self):
        """Aggregate this single fund's named holdings into sector weights."""
        sectors = {}
        for company, weight in self.holdings.items():
            sector = COMPANY_SECTOR_MAP.get(company, "Others")
            sectors[sector] = sectors.get(sector, 0.0) + weight
        if self.other_holdings_pct > 0:
            sectors["Others / Unclassified"] = sectors.get("Others / Unclassified", 0.0) + self.other_holdings_pct
        return sectors

    def to_dict(self):
        d = {
            "name": self.name, "category": self.category, "nav": self.nav,
            "aum_cr": self.aum_cr, "expense_ratio_pct": self.expense_ratio_pct,
            "return_1y_pct": self.return_1y_pct, "cagr_3y_pct": self.cagr_3y_pct,
            "cagr_5y_pct": self.cagr_5y_pct, "risk_level": self.risk_level,
            "equity_pct": self.equity_pct, "debt_pct": self.debt_pct,
            "cash_pct": self.cash_pct, "benchmark": self.benchmark,
            "portfolio_date": str(self.portfolio_date), "holdings": dict(self.holdings),
        }
        return d


def _build_funds():
    funds = {}
    for name, meta in FUND_META.items():
        funds[name] = Fund(name, meta, FUND_HOLDINGS.get(name, {}))
    return funds


FUNDS = _build_funds()


class PortfolioEntry:
    """One line of the investor's portfolio: an investment into one fund."""

    def __init__(self, fund_name, amount, method="Lump Sum", inv_date=None):
        if fund_name not in FUNDS:
            raise ValueError(f"Unknown fund: {fund_name}")
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Investment amount must be greater than zero.")
        if method not in ("Lump Sum", "SIP"):
            raise ValueError("Investment method must be 'Lump Sum' or 'SIP'.")
        self.fund_name = fund_name
        self.amount = amount
        self.method = method
        self.inv_date = inv_date or date.today()

    def to_dict(self):
        return {
            "fund_name": self.fund_name, "amount": self.amount,
            "method": self.method, "inv_date": str(self.inv_date),
        }

    @staticmethod
    def from_dict(d):
        inv_date = d.get("inv_date")
        if isinstance(inv_date, str) and inv_date:
            try:
                inv_date = datetime.strptime(inv_date, "%Y-%m-%d").date()
            except ValueError:
                inv_date = date.today()
        return PortfolioEntry(d["fund_name"], d["amount"], d.get("method", "Lump Sum"), inv_date)


class Portfolio:
    """The investor's full set of PortfolioEntry lines, plus the aggregate
    calculations that only need the entries themselves (allocation, totals).
    Everything that also needs fund holdings (exposure, overlap, sector,
    risk...) lives in Section 6/7 as free functions that take a Portfolio."""

    def __init__(self, entries=None):
        self.entries = list(entries) if entries else []

    def add(self, fund_name, amount, method="Lump Sum", inv_date=None):
        self.entries.append(PortfolioEntry(fund_name, amount, method, inv_date))

    def remove_fund(self, fund_name):
        self.entries = [e for e in self.entries if e.fund_name != fund_name]

    def clear(self):
        self.entries = []

    def is_empty(self):
        return len(self.entries) == 0

    def fund_names(self):
        # preserves insertion order, de-duplicated
        seen = []
        for e in self.entries:
            if e.fund_name not in seen:
                seen.append(e.fund_name)
        return seen

    def amount_by_fund(self):
        """Aggregate amount per fund (an investor may have added the same
        fund more than once, e.g. lump sum + SIP)."""
        totals = {}
        for e in self.entries:
            totals[e.fund_name] = totals.get(e.fund_name, 0.0) + e.amount
        return totals

    def total_investment(self):
        return sum(e.amount for e in self.entries)

    def copy_without(self, fund_name):
        """Return a new Portfolio excluding a given fund -- used by the
        What-If Simulator."""
        return Portfolio([e for e in self.entries if e.fund_name != fund_name])

    def to_dict_list(self):
        return [e.to_dict() for e in self.entries]

    @staticmethod
    def from_dict_list(items):
        p = Portfolio()
        for d in items:
            p.entries.append(PortfolioEntry.from_dict(d))
        return p


def demo_portfolio():
    """The preloaded demonstration portfolio described in the spec: four
    funds with deliberately overlapping holdings so every module has
    something meaningful to show immediately."""
    p = Portfolio()
    p.add("Growth Equity Fund", 200000, "Lump Sum", PORTFOLIO_DATE - timedelta(days=730))
    p.add("Bluechip Equity Fund", 300000, "Lump Sum", PORTFOLIO_DATE - timedelta(days=540))
    p.add("Flexi Cap Fund", 250000, "SIP", PORTFOLIO_DATE - timedelta(days=365))
    p.add("Mid Cap Growth Fund", 150000, "SIP", PORTFOLIO_DATE - timedelta(days=180))
    return p


# =============================================================================
# SECTION 6 : FINANCIAL CALCULATIONS
# -----------------------------------------------------------------------------
# These functions use ONLY user-entered portfolio amounts -- no assumed or
# invented investment values anywhere.
# =============================================================================
def calc_allocation(portfolio: Portfolio) -> pd.DataFrame:
    """Fund-wise allocation table: amount invested and % of total portfolio,
    plus each fund's own metadata, for the funds actually held."""
    totals = portfolio.amount_by_fund()
    total_investment = sum(totals.values())
    rows = []
    for fund_name, amount in totals.items():
        fund = FUNDS[fund_name]
        rows.append({
            "Fund": fund_name,
            "Category": fund.category,
            "Amount": amount,
            "Allocation %": safe_div(amount, total_investment) * 100.0,
            "Expense Ratio %": fund.expense_ratio_pct,
            "Risk Level": fund.risk_level,
            "Equity %": fund.equity_pct,
            "Debt %": fund.debt_pct,
            "Cash %": fund.cash_pct,
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Allocation %", ascending=False).reset_index(drop=True)
    return df


def calc_weighted_metric(allocation_df: pd.DataFrame, column: str) -> float:
    """Investment-weighted average of any per-fund metric column, e.g. the
    weighted expense ratio or weighted equity %."""
    if allocation_df.empty:
        return 0.0
    total = allocation_df["Amount"].sum()
    if total <= 0:
        return 0.0
    return float((allocation_df[column] * allocation_df["Amount"]).sum() / total)


def calc_effective_exposure(portfolio: Portfolio) -> pd.DataFrame:
    """The core Portfolio X-Ray calculation: for every underlying company,
    combine its weight in each held fund with the amount invested in that
    fund to get the investor's effective rupee exposure and effective %.

    Example (as in the spec): Fund A = Rs.5,00,000 holding Company X at 10%,
    Fund B = Rs.5,00,000 holding Company X at 8% ->
        Fund A exposure to X = 5,00,000 x 10% = 50,000
        Fund B exposure to X = 5,00,000 x 8%  = 40,000
        Total exposure to X  = 90,000 on a Rs.10,00,000 portfolio = 9.0%
    """
    totals = portfolio.amount_by_fund()
    total_investment = sum(totals.values())
    exposure = {}   # company -> amount
    contributors = {}  # company -> {fund_name: amount}

    for fund_name, amount in totals.items():
        fund = FUNDS[fund_name]
        for company, weight_pct in fund.holdings.items():
            company_amount = amount * (weight_pct / 100.0)
            exposure[company] = exposure.get(company, 0.0) + company_amount
            contributors.setdefault(company, {})[fund_name] = company_amount

    rows = []
    for company, amount in exposure.items():
        rows.append({
            "Company": company,
            "Sector": COMPANY_SECTOR_MAP.get(company, "Others"),
            "Exposure Amount": amount,
            "Effective Exposure %": safe_div(amount, total_investment) * 100.0,
            "Funds Holding It": ", ".join(sorted(contributors[company].keys())),
            "Number of Funds": len(contributors[company]),
            "_contributors": contributors[company],
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Effective Exposure %", ascending=False).reset_index(drop=True)
    return df


def calc_overlap_matrix(fund_names):
    """Fund x fund overlap matrix using the MF X-Ray Overlap Methodology:
    overlap(A, B) = sum over companies held by BOTH funds of min(weight_in_A,
    weight_in_B). This looks only at the two funds' own portfolios (not the
    investor's amounts), which is the standard way to compare two SCHEMES.
    Returns a DataFrame indexed and columned by fund name."""
    n = len(fund_names)
    matrix = pd.DataFrame(0.0, index=fund_names, columns=fund_names)
    for i, a in enumerate(fund_names):
        holdings_a = FUNDS[a].holdings
        for j, b in enumerate(fund_names):
            if i == j:
                matrix.loc[a, b] = 100.0
                continue
            holdings_b = FUNDS[b].holdings
            common = set(holdings_a) & set(holdings_b)
            overlap_pct = sum(min(holdings_a[c], holdings_b[c]) for c in common)
            matrix.loc[a, b] = overlap_pct
    return matrix


def overlap_pairs_sorted(overlap_matrix: pd.DataFrame):
    """Unique fund pairs (A, B, overlap%) sorted from highest to lowest,
    excluding a fund paired with itself."""
    pairs = []
    funds = list(overlap_matrix.index)
    for i in range(len(funds)):
        for j in range(i + 1, len(funds)):
            a, b = funds[i], funds[j]
            pairs.append((a, b, float(overlap_matrix.loc[a, b])))
    pairs.sort(key=lambda t: t[2], reverse=True)
    return pairs


def calc_sector_exposure(exposure_df: pd.DataFrame, total_investment: float) -> pd.DataFrame:
    """Aggregate the effective stock-level exposure into sector-level
    effective exposure, and count how many distinct funds contribute to
    each sector."""
    if exposure_df.empty:
        return pd.DataFrame(columns=["Sector", "Exposure Amount", "Effective Exposure %", "Funds Contributing"])
    rows = {}
    for _, r in exposure_df.iterrows():
        sector = r["Sector"]
        entry = rows.setdefault(sector, {"amount": 0.0, "funds": set()})
        entry["amount"] += r["Exposure Amount"]
        entry["funds"].update(r["_contributors"].keys())
    out = [{
        "Sector": sector, "Exposure Amount": v["amount"],
        "Effective Exposure %": safe_div(v["amount"], total_investment) * 100.0,
        "Funds Contributing": len(v["funds"]),
    } for sector, v in rows.items()]
    df = pd.DataFrame(out).sort_values("Effective Exposure %", ascending=False).reset_index(drop=True)
    return df


def calc_concentration(exposure_df: pd.DataFrame) -> dict:
    """Top-5 / top-10 stock concentration and the single largest holding."""
    if exposure_df.empty:
        return {"top5_pct": 0.0, "top10_pct": 0.0, "largest_company": None, "largest_pct": 0.0}
    sorted_df = exposure_df.sort_values("Effective Exposure %", ascending=False)
    top5_pct = float(sorted_df.head(5)["Effective Exposure %"].sum())
    top10_pct = float(sorted_df.head(10)["Effective Exposure %"].sum())
    top_row = sorted_df.iloc[0]
    return {
        "top5_pct": top5_pct, "top10_pct": top10_pct,
        "largest_company": top_row["Company"], "largest_pct": float(top_row["Effective Exposure %"]),
    }


def calc_fund_concentration(allocation_df: pd.DataFrame) -> dict:
    if allocation_df.empty:
        return {"largest_fund": None, "largest_fund_pct": 0.0}
    top = allocation_df.sort_values("Allocation %", ascending=False).iloc[0]
    return {"largest_fund": top["Fund"], "largest_fund_pct": float(top["Allocation %"])}


# =============================================================================
# SECTION 7 : RISK CALCULATIONS
# -----------------------------------------------------------------------------
# All figures in this section are computed from the SAMPLE / SIMULATED NAV
# history described in Section 4, clearly labelled as such everywhere they
# are shown. No historical data is fabricated to look official; it is a
# reproducible synthetic series built from each fund's own stated CAGR and
# risk level, for demonstration only.
# =============================================================================
def get_fund_monthly_returns(fund_name: str) -> pd.Series:
    nav = FUND_NAV_HISTORY[fund_name]
    return nav.pct_change().dropna()


def calc_volatility_pct(returns: pd.Series) -> float:
    """Annualised volatility (standard deviation of monthly returns x sqrt(12)),
    expressed as a percentage."""
    if returns is None or len(returns) < 2:
        return 0.0
    return float(returns.std(ddof=1) * math.sqrt(12) * 100.0)


def calc_annualised_return_pct(returns: pd.Series) -> float:
    if returns is None or len(returns) == 0:
        return 0.0
    growth = float((1.0 + returns).prod())
    months = len(returns)
    if growth <= 0 or months == 0:
        return 0.0
    return (growth ** (12.0 / months) - 1.0) * 100.0


def calc_sharpe_ratio(returns: pd.Series, risk_free_rate_pct: float) -> float:
    """Sharpe Ratio = (annualised return - risk-free rate) / annualised
    volatility. The risk-free rate is an explicit, user-configurable
    assumption (see Risk Analysis tab), never hidden."""
    vol = calc_volatility_pct(returns)
    if vol == 0:
        return 0.0
    ann_return = calc_annualised_return_pct(returns)
    return (ann_return - risk_free_rate_pct) / vol


def calc_max_drawdown_pct(nav_series: pd.Series) -> float:
    """Maximum historical peak-to-trough decline, as a negative percentage."""
    if nav_series is None or len(nav_series) < 2:
        return 0.0
    running_max = nav_series.cummax()
    drawdown = (nav_series - running_max) / running_max
    return float(drawdown.min() * 100.0)


def calc_fund_risk_table(fund_names, risk_free_rate_pct) -> pd.DataFrame:
    rows = []
    for name in fund_names:
        returns = get_fund_monthly_returns(name)
        nav = FUND_NAV_HISTORY[name]
        rows.append({
            "Fund": name,
            "Volatility % (annualised)": calc_volatility_pct(returns),
            "Sharpe Ratio": calc_sharpe_ratio(returns, risk_free_rate_pct),
            "Max Drawdown %": calc_max_drawdown_pct(nav),
        })
    return pd.DataFrame(rows)


def calc_portfolio_risk(allocation_df: pd.DataFrame, risk_free_rate_pct: float) -> dict:
    """Portfolio-level risk as the investment-weighted average of each
    fund's own risk metrics. This is a simplified analytical approximation
    that ignores correlation between funds -- explicitly disclosed as an
    MF X-Ray assumption/limitation rather than presented as a precise
    portfolio-level statistical calculation."""
    if allocation_df.empty:
        return {"volatility_pct": 0.0, "sharpe_ratio": 0.0, "max_drawdown_pct": 0.0}
    risk_df = calc_fund_risk_table(allocation_df["Fund"].tolist(), risk_free_rate_pct)
    merged = allocation_df.merge(risk_df, on="Fund", how="left")
    total = merged["Amount"].sum()
    return {
        "volatility_pct": float(safe_div((merged["Volatility % (annualised)"] * merged["Amount"]).sum(), total)),
        "sharpe_ratio": float(safe_div((merged["Sharpe Ratio"] * merged["Amount"]).sum(), total)),
        "max_drawdown_pct": float(safe_div((merged["Max Drawdown %"] * merged["Amount"]).sum(), total)),
    }


# =============================================================================
# SECTION 8 : PORTFOLIO HEALTH SCORE
# -----------------------------------------------------------------------------
# A transparent, fully-visible 0-100 analytical score. Every reference point
# used below is a constant defined here (not hidden inside a formula), and
# is reproduced verbatim in the GUI's "Methodology" panel and in every
# report export, per component.
# =============================================================================
HEALTH_WEIGHTS = {
    "diversification": 20, "overlap": 20, "stock_concentration": 20,
    "sector_concentration": 15, "volatility": 15, "drawdown": 10,
}
HEALTH_REFERENCE_POINTS = {
    "fund_count_full_credit": 5,      # number of funds at which the "fund count" part maxes out
    "top5_reference_pct": 60.0,       # top-5 stock concentration % that scores 0
    "sector_reference_pct": 50.0,     # single-sector exposure % that scores 0
    "volatility_reference_pct": 35.0, # annualised portfolio volatility % that scores 0
    "drawdown_reference_pct": 50.0,   # |max drawdown| % that scores 0
}


def calc_health_score(allocation_df, overlap_pairs, concentration, sector_df, risk) -> dict:
    w = HEALTH_WEIGHTS
    ref = HEALTH_REFERENCE_POINTS

    if allocation_df.empty:
        components = {k: 0.0 for k in w}
        return {"components": components, "total": 0, "max_components": w}

    num_funds = allocation_df["Fund"].nunique()
    max_fund_pct = float(allocation_df["Allocation %"].max())

    # Diversification (fund-count component + fund-concentration component)
    fund_count_score = min(num_funds, ref["fund_count_full_credit"]) / ref["fund_count_full_credit"] * (w["diversification"] * 0.5)
    fund_conc_score = clamp(1 - max_fund_pct / 100.0, 0, 1) * (w["diversification"] * 0.5)
    diversification_score = fund_count_score + fund_conc_score

    # Overlap (based on the average of all pairwise overlaps among held funds)
    if overlap_pairs:
        avg_overlap = sum(p[2] for p in overlap_pairs) / len(overlap_pairs)
    else:
        avg_overlap = 0.0
    overlap_score = clamp(1 - avg_overlap / 100.0, 0, 1) * w["overlap"]

    # Stock concentration (top-5 effective exposure vs. reference point)
    top5_pct = concentration.get("top5_pct", 0.0)
    stock_conc_score = clamp(1 - top5_pct / ref["top5_reference_pct"], 0, 1) * w["stock_concentration"]

    # Sector concentration (largest single sector vs. reference point)
    top_sector_pct = float(sector_df["Effective Exposure %"].max()) if not sector_df.empty else 0.0
    sector_conc_score = clamp(1 - top_sector_pct / ref["sector_reference_pct"], 0, 1) * w["sector_concentration"]

    # Volatility
    volatility_score = clamp(1 - risk.get("volatility_pct", 0.0) / ref["volatility_reference_pct"], 0, 1) * w["volatility"]

    # Drawdown
    drawdown_score = clamp(1 - abs(risk.get("max_drawdown_pct", 0.0)) / ref["drawdown_reference_pct"], 0, 1) * w["drawdown"]

    components = {
        "diversification": round(diversification_score, 1),
        "overlap": round(overlap_score, 1),
        "stock_concentration": round(stock_conc_score, 1),
        "sector_concentration": round(sector_conc_score, 1),
        "volatility": round(volatility_score, 1),
        "drawdown": round(drawdown_score, 1),
    }
    total = round(sum(components.values()))
    return {
        "components": components, "total": int(clamp(total, 0, 100)), "max_components": w,
        "avg_overlap_pct": avg_overlap, "top_sector_pct": top_sector_pct,
    }


def health_score_risk_bucket(total_score: int) -> str:
    if total_score >= 70:
        return "Low"
    if total_score >= 45:
        return "Moderate"
    return "High"


# =============================================================================
# SECTION 9 : ALERT ENGINE (rule-based, driven only by calculated metrics)
# =============================================================================
def generate_alerts(allocation_df, overlap_pairs, exposure_df, sector_df, concentration, fund_concentration) -> list:
    alerts = []
    t = THRESHOLDS

    for a, b, pct in overlap_pairs:
        if pct >= t["high_overlap_pct"]:
            alerts.append({
                "severity": "High", "category": "High Overlap",
                "message": f"'{a}' and '{b}' have significant underlying holding overlap "
                           f"({format_pct(pct)}, MF X-Ray Analytical Threshold: {format_pct(t['high_overlap_pct'])})."
            })

    if not exposure_df.empty:
        for _, r in exposure_df.head(10).iterrows():
            if r["Effective Exposure %"] >= t["high_stock_exposure_pct"]:
                alerts.append({
                    "severity": "Medium", "category": "High Concentration",
                    "message": f"'{r['Company']}' represents a relatively high proportion of your "
                               f"effective portfolio exposure ({format_pct(r['Effective Exposure %'])})."
                })

    if not sector_df.empty:
        for _, r in sector_df.iterrows():
            if r["Effective Exposure %"] >= t["high_sector_exposure_pct"]:
                alerts.append({
                    "severity": "Medium", "category": "Sector Concentration",
                    "message": f"'{r['Sector']}' represents a significant share of the portfolio "
                               f"({format_pct(r['Effective Exposure %'])})."
                })

    if concentration.get("top5_pct", 0) >= t["top5_concentration_watch_pct"]:
        alerts.append({
            "severity": "Medium", "category": "Concentration Watch",
            "message": f"Your top 5 effective stock holdings represent "
                       f"{format_pct(concentration['top5_pct'])} of the portfolio "
                       f"(MF X-Ray Analytical Threshold: {format_pct(t['top5_concentration_watch_pct'])})."
        })

    if fund_concentration.get("largest_fund_pct", 0) >= t["high_fund_concentration_pct"]:
        alerts.append({
            "severity": "High", "category": "Fund Concentration",
            "message": f"Your portfolio allocation is heavily concentrated in one fund "
                       f"('{fund_concentration['largest_fund']}' at "
                       f"{format_pct(fund_concentration['largest_fund_pct'])})."
        })

    severity_rank = {"High": 0, "Medium": 1, "Info": 2}
    alerts.sort(key=lambda a: severity_rank.get(a["severity"], 3))
    return alerts


def alerts_to_df(alerts: list) -> pd.DataFrame:
    """Presentation-friendly (Title Case) version of the alerts list, used
    by both the GUI tables and the report exports."""
    if not alerts:
        return pd.DataFrame(columns=["Severity", "Category", "Message"])
    return pd.DataFrame([
        {"Severity": a["severity"], "Category": a["category"], "Message": a["message"]} for a in alerts
    ])


# =============================================================================
# SECTION 10 : AI INSIGHT / EXPLAINABILITY ENGINE
# -----------------------------------------------------------------------------
# This is a RULE-BASED explainability layer (see Section 33 of the spec: no
# "fake AI"). It never invents numbers -- every sentence below is built by
# substituting already-calculated values into a template. It is architected
# so a real LLM could later generate the prose from the same metrics dict
# (see answer_question, which would become the natural place to route a
# question + this same metrics payload to an LLM in a future version).
# =============================================================================
def generate_ai_narrative(metrics: dict) -> str:
    if not metrics.get("has_portfolio"):
        return ("Load or build a portfolio to generate AI insights. MF X-Ray explains your "
                "portfolio only from numbers it has actually calculated -- it will not "
                "speculate without data.")

    alloc = metrics["allocation_df"]
    exposure = metrics["exposure_df"]
    sector_df = metrics["sector_df"]
    conc = metrics["concentration"]
    health = metrics["health"]
    overlap_pairs = metrics["overlap_pairs"]
    num_funds = alloc["Fund"].nunique()

    top_company = conc.get("largest_company")
    top_company_pct = conc.get("largest_pct", 0.0)
    top_sector_row = sector_df.iloc[0] if not sector_df.empty else None
    top_pair = overlap_pairs[0] if overlap_pairs else None

    sentences = []
    sentences.append(
        f"Your portfolio contains {num_funds} mutual fund{'s' if num_funds != 1 else ''} "
        f"totalling {format_inr(metrics['total_investment'])}."
    )
    if top_pair and top_pair[2] >= THRESHOLDS["high_overlap_pct"] * 0.5:
        sentences.append(
            f"Although these are different schemes, several underlying companies are common "
            f"across them -- '{top_pair[0]}' and '{top_pair[1]}' alone share "
            f"{format_pct(top_pair[2])} of their portfolios (MF X-Ray Overlap Methodology)."
        )
    if top_company:
        sentences.append(
            f"The highest effective exposure is to '{top_company}' at {format_pct(top_company_pct)} "
            f"of your total portfolio."
        )
    if top_sector_row is not None:
        sentences.append(
            f"'{top_sector_row['Sector']}' is also your largest sector exposure at "
            f"{format_pct(top_sector_row['Effective Exposure %'])}."
        )
    sentences.append(
        f"Your top 5 effective stock holdings account for {format_pct(conc.get('top5_pct', 0))} of the "
        f"portfolio, and the top 10 account for {format_pct(conc.get('top10_pct', 0))}."
    )
    sentences.append(
        f"The MF X-Ray Portfolio Health Score for this portfolio is {health['total']}/100 "
        f"(risk bucket: {health_score_risk_bucket(health['total'])})."
    )
    if top_pair and top_pair[2] >= THRESHOLDS["high_overlap_pct"]:
        sentences.append(
            "This indicates that your portfolio may carry higher concentration risk than the "
            "number of funds alone would suggest. Consider reviewing whether this overlap is "
            "intentional, and whether the sector and stock concentrations shown above match your "
            "own comfort with risk."
        )
    else:
        sentences.append(
            "Overall, overlap and concentration levels are within the reference ranges used by "
            "this application, but you should still review the sector and stock breakdown above "
            "against your own comfort with risk."
        )
    return " ".join(sentences)


def answer_question(question: str, metrics: dict) -> str:
    """A small, deterministic keyword-matching Q&A layer over the ALREADY
    CALCULATED metrics dict. It never invents information: if the data
    needed to answer is not available, it says so explicitly."""
    if not question or not question.strip():
        return "Please type a question, e.g. 'Which companies have the highest exposure?'"
    q = question.lower().strip()

    if not metrics.get("has_portfolio"):
        return "Insufficient data available to answer this question. Please build or load a portfolio first."

    exposure = metrics["exposure_df"]
    sector_df = metrics["sector_df"]
    overlap_pairs = metrics["overlap_pairs"]
    conc = metrics["concentration"]
    risk_df = metrics.get("risk_df")
    health = metrics["health"]
    alloc = metrics["allocation_df"]

    def top_n_companies(n=5):
        if exposure.empty:
            return "Insufficient data available to answer this question."
        lines = [f"{r['Company']} ({format_pct(r['Effective Exposure %'])})" for _, r in exposure.head(n).iterrows()]
        return "The highest effective exposures are: " + "; ".join(lines) + "."

    if any(k in q for k in ["explain", "like a ca", "summar"]):
        return generate_ai_narrative(metrics)

    if "overlap" in q and any(k in q for k in ["most", "which two", "highest", "top"]):
        if not overlap_pairs:
            return "Insufficient data available to answer this question."
        a, b, pct = overlap_pairs[0]
        return f"'{a}' and '{b}' overlap the most, at {format_pct(pct)} (MF X-Ray Overlap Methodology)."

    if "sector" in q and any(k in q for k in ["highest", "most", "top", "largest"]):
        if sector_df.empty:
            return "Insufficient data available to answer this question."
        top = sector_df.iloc[0]
        return f"'{top['Sector']}' has the highest effective exposure, at {format_pct(top['Effective Exposure %'])}."

    if "highest exposure" in q or ("top" in q and "compan" in q) or ("top" in q and "stock" in q):
        return top_n_companies(5)

    if "concentrat" in q:
        if exposure.empty:
            return "Insufficient data available to answer this question."
        return (f"Your top 5 holdings represent {format_pct(conc['top5_pct'])} and your top 10 represent "
                f"{format_pct(conc['top10_pct'])} of the portfolio. The single largest holding is "
                f"'{conc['largest_company']}' at {format_pct(conc['largest_pct'])}. This is driven by overlap "
                f"between funds as much as by any single fund's own concentration -- see the Overlap Analyzer.")

    if "risk" in q and ("contribut" in q or "most" in q or "which fund" in q):
        if risk_df is None or risk_df.empty:
            return "Insufficient data available to answer this question."
        merged = alloc.merge(risk_df, on="Fund", how="left")
        merged["Risk Contribution"] = merged["Volatility % (annualised)"] * merged["Amount"]
        top = merged.sort_values("Risk Contribution", ascending=False).iloc[0]
        return (f"'{top['Fund']}' contributes the most to portfolio risk, with an annualised volatility of "
                f"{format_pct(top['Volatility % (annualised)'])} on an allocation of {format_pct(top['Allocation %'])}.")

    if "chang" in q:
        return ("Insufficient data available to answer this question. Save at least two portfolio "
                "snapshots on the 'Portfolio Changes' tab and compare them to see what changed.")

    if "health" in q or "score" in q:
        return (f"Your MF X-Ray Portfolio Health Score is {health['total']}/100 "
                f"(risk bucket: {health_score_risk_bucket(health['total'])}). "
                f"See the Portfolio X-Ray tab's Methodology panel for exactly how each component is scored.")

    return "Insufficient data available to answer this question. Try rephrasing, or use one of the example questions."


def compute_all_metrics(portfolio: Portfolio, risk_free_rate_pct: float = None) -> dict:
    """The single place that ties Sections 6-9 together into one metrics
    dict. Every GUI tab (Section 14) and every report export (Section 13)
    is built from the output of this one function, so the whole
    application always shows numbers that are consistent with each other."""
    if risk_free_rate_pct is None:
        risk_free_rate_pct = ASSUMPTIONS["risk_free_rate_pct"]

    allocation_df = calc_allocation(portfolio)
    has_portfolio = not allocation_df.empty
    total_investment = portfolio.total_investment()

    if not has_portfolio:
        empty_df = pd.DataFrame()
        return {
            "has_portfolio": False, "allocation_df": empty_df, "total_investment": 0.0,
            "weighted_expense_ratio": 0.0, "weighted_equity_pct": 0.0, "weighted_debt_pct": 0.0,
            "weighted_cash_pct": 0.0, "exposure_df": empty_df, "sector_df": empty_df,
            "overlap_matrix": empty_df, "overlap_pairs": [], "concentration": calc_concentration(empty_df),
            "fund_concentration": calc_fund_concentration(empty_df), "risk_df": empty_df,
            "risk": {"volatility_pct": 0.0, "sharpe_ratio": 0.0, "max_drawdown_pct": 0.0},
            "health": {"components": {k: 0.0 for k in HEALTH_WEIGHTS}, "total": 0, "max_components": HEALTH_WEIGHTS},
            "alerts": [], "risk_free_rate_pct": risk_free_rate_pct,
        }

    fund_names = allocation_df["Fund"].tolist()
    exposure_df = calc_effective_exposure(portfolio)
    sector_df = calc_sector_exposure(exposure_df, total_investment)
    overlap_matrix = calc_overlap_matrix(fund_names)
    overlap_pairs = overlap_pairs_sorted(overlap_matrix)
    concentration = calc_concentration(exposure_df)
    fund_concentration = calc_fund_concentration(allocation_df)
    risk_df = calc_fund_risk_table(fund_names, risk_free_rate_pct)
    risk = calc_portfolio_risk(allocation_df, risk_free_rate_pct)
    health = calc_health_score(allocation_df, overlap_pairs, concentration, sector_df, risk)
    alerts = generate_alerts(allocation_df, overlap_pairs, exposure_df, sector_df, concentration, fund_concentration)

    return {
        "has_portfolio": True,
        "allocation_df": allocation_df,
        "total_investment": total_investment,
        "weighted_expense_ratio": calc_weighted_metric(allocation_df, "Expense Ratio %"),
        "weighted_equity_pct": calc_weighted_metric(allocation_df, "Equity %"),
        "weighted_debt_pct": calc_weighted_metric(allocation_df, "Debt %"),
        "weighted_cash_pct": calc_weighted_metric(allocation_df, "Cash %"),
        "exposure_df": exposure_df,
        "sector_df": sector_df,
        "overlap_matrix": overlap_matrix,
        "overlap_pairs": overlap_pairs,
        "concentration": concentration,
        "fund_concentration": fund_concentration,
        "risk_df": risk_df,
        "risk": risk,
        "health": health,
        "alerts": alerts,
        "risk_free_rate_pct": risk_free_rate_pct,
    }


# =============================================================================
# SECTION 11 : WHAT-IF SIMULATOR
# -----------------------------------------------------------------------------
# Pure simulation: recomputes every metric on a hypothetical portfolio and
# returns a Before/After comparison. It never issues a buy/sell instruction.
# =============================================================================
def simulate_remove_fund(portfolio: Portfolio, fund_name: str, risk_free_rate_pct: float) -> dict:
    before = compute_all_metrics(portfolio, risk_free_rate_pct)
    after_portfolio = portfolio.copy_without(fund_name)
    after = compute_all_metrics(after_portfolio, risk_free_rate_pct)
    return {"before": before, "after": after, "removed_fund": fund_name, "after_portfolio": after_portfolio}


def whatif_summary_row(label, metrics):
    if not metrics.get("has_portfolio"):
        return {
            "Metric": label, "Total Investment": 0.0, "Avg. Pairwise Overlap %": 0.0,
            "Top 5 Concentration %": 0.0, "Largest Sector %": 0.0, "Health Score": 0,
        }
    overlap_pairs = metrics["overlap_pairs"]
    avg_overlap = sum(p[2] for p in overlap_pairs) / len(overlap_pairs) if overlap_pairs else 0.0
    sector_df = metrics["sector_df"]
    top_sector_pct = float(sector_df["Effective Exposure %"].max()) if not sector_df.empty else 0.0
    return {
        "Metric": label,
        "Total Investment": metrics["total_investment"],
        "Avg. Pairwise Overlap %": avg_overlap,
        "Top 5 Concentration %": metrics["concentration"]["top5_pct"],
        "Largest Sector %": top_sector_pct,
        "Health Score": metrics["health"]["total"],
    }


# =============================================================================
# SECTION 12 : SIP ANALYSIS (including XIRR)
# =============================================================================
def calc_xirr(cashflows, guess=0.15):
    """Newton-Raphson XIRR for a list of (date, amount) cashflows (outflows
    negative, inflows positive). Falls back to a bisection search if Newton's
    method fails to converge. Returns None if a rate cannot be found."""
    if not cashflows or len(cashflows) < 2:
        return None
    d0 = cashflows[0][0]

    def npv(rate):
        try:
            return sum(cf / ((1.0 + rate) ** (safe_div((d - d0).days, 365.0))) for d, cf in cashflows)
        except (OverflowError, ZeroDivisionError):
            return float("inf")

    def dnpv(rate):
        total = 0.0
        for d, cf in cashflows:
            t = safe_div((d - d0).days, 365.0)
            try:
                total += -t * cf / ((1.0 + rate) ** (t + 1))
            except (OverflowError, ZeroDivisionError):
                return float("inf")
        return total

    rate = guess
    for _ in range(100):
        f = npv(rate)
        fp = dnpv(rate)
        if fp == 0 or not math.isfinite(fp):
            break
        new_rate = rate - f / fp
        if not math.isfinite(new_rate) or new_rate <= -0.999:
            break
        if abs(new_rate - rate) < 1e-7:
            return new_rate * 100.0
        rate = new_rate

    # Fallback: bisection over a wide, sane range
    lo, hi = -0.9, 10.0
    f_lo, f_hi = npv(lo), npv(hi)
    if not (math.isfinite(f_lo) and math.isfinite(f_hi)) or f_lo * f_hi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < 1e-6:
            return mid * 100.0
        if f_lo * f_mid < 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return ((lo + hi) / 2.0) * 100.0


def _nav_on_or_after(fund_name, target_date):
    """Look up the sample NAV for a fund on/after a given date. If the date
    is beyond the sample history, the NAV is extrapolated forward using the
    MF X-Ray SIP fallback growth assumption (clearly labelled to the user)."""
    series = FUND_NAV_HISTORY[fund_name]
    ts = pd.Timestamp(target_date)
    if ts <= series.index[-1]:
        idx = series.index.searchsorted(ts)
        idx = min(idx, len(series) - 1)
        return float(series.iloc[idx]), False
    months_beyond = (ts.year - series.index[-1].year) * 12 + (ts.month - series.index[-1].month)
    monthly_growth = (1.0 + ASSUMPTIONS["sip_fallback_growth_pct"] / 100.0) ** (1.0 / 12.0)
    return float(series.iloc[-1] * (monthly_growth ** max(months_beyond, 0))), True


def simulate_sip(fund_name, monthly_amount, start_date, installments):
    if monthly_amount <= 0:
        raise ValueError("Monthly SIP amount must be greater than zero.")
    if installments <= 0:
        raise ValueError("Number of instalments must be greater than zero.")

    cashflows = []
    total_units = 0.0
    used_assumption = False
    schedule = []
    for i in range(int(installments)):
        inst_date = _add_months(start_date, i)
        nav, extrapolated = _nav_on_or_after(fund_name, inst_date)
        used_assumption = used_assumption or extrapolated
        units = monthly_amount / nav
        total_units += units
        cashflows.append((inst_date, -monthly_amount))
        schedule.append({"Instalment #": i + 1, "Date": inst_date, "NAV": nav, "Units": units})

    latest_nav, latest_extrapolated = _nav_on_or_after(fund_name, _add_months(start_date, installments - 1))
    current_value = total_units * latest_nav
    invested_total = monthly_amount * installments
    abs_return_pct = safe_div(current_value - invested_total, invested_total) * 100.0

    xirr_cashflows = cashflows + [(cashflows[-1][0], current_value)]
    xirr_pct = calc_xirr(xirr_cashflows)

    return {
        "fund_name": fund_name, "invested_total": invested_total, "units": total_units,
        "current_value": current_value, "abs_return_pct": abs_return_pct, "xirr_pct": xirr_pct,
        "used_extrapolation_assumption": used_assumption or latest_extrapolated,
        "schedule": schedule,
    }


def _add_months(d, n):
    month = d.month - 1 + n
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                       31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)


# =============================================================================
# SECTION 13 : REPORT GENERATION (Excel + Word)
# =============================================================================
_XL_HEADER_FILL = PatternFill(start_color="12233F", end_color="12233F", fill_type="solid")
_XL_HEADER_FONT = XLFont(color="FFFFFF", bold=True)
_XL_TITLE_FONT = XLFont(bold=True, size=14, color="12233F")
_XL_THIN_BORDER = Border(*([Side(style="thin", color="D7DEE8")] * 4))


def _xl_write_title(ws, text, row=1):
    ws.cell(row=row, column=1, value=text).font = _XL_TITLE_FONT
    return row + 2


def _xl_write_df(ws, df: pd.DataFrame, start_row=1, exclude_cols=None):
    exclude_cols = exclude_cols or []
    cols = [c for c in df.columns if c not in exclude_cols]
    for j, col in enumerate(cols, start=1):
        cell = ws.cell(row=start_row, column=j, value=str(col))
        cell.font = _XL_HEADER_FONT
        cell.fill = _XL_HEADER_FILL
        cell.border = _XL_THIN_BORDER
    for i, (_, row) in enumerate(df.iterrows(), start=start_row + 1):
        for j, col in enumerate(cols, start=1):
            value = row[col]
            if isinstance(value, (np.floating, float)):
                value = round(float(value), 2)
            elif isinstance(value, (np.integer,)):
                value = int(value)
            ws.cell(row=i, column=j, value=value).border = _XL_THIN_BORDER
    for j, col in enumerate(cols, start=1):
        width = max(12, min(40, len(str(col)) + 4))
        ws.column_dimensions[get_column_letter(j)].width = width
    return start_row + len(df) + 2


def export_to_excel(path, portfolio: Portfolio, metrics: dict):
    if not metrics.get("has_portfolio"):
        raise ValueError("Cannot export a report for an empty portfolio.")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # 1. Portfolio Summary
    ws = wb.create_sheet("Portfolio Summary")
    r = _xl_write_title(ws, f"{APP_FULL_TITLE} - Portfolio Summary  ({DEMO_DATA_LABEL})")
    summary_df = pd.DataFrame([
        {"Metric": "Total Investment", "Value": format_inr(metrics["total_investment"])},
        {"Metric": "Number of Funds", "Value": metrics["allocation_df"]["Fund"].nunique()},
        {"Metric": "Weighted Expense Ratio %", "Value": round(metrics["weighted_expense_ratio"], 2)},
        {"Metric": "Weighted Equity %", "Value": round(metrics["weighted_equity_pct"], 2)},
        {"Metric": "Weighted Debt %", "Value": round(metrics["weighted_debt_pct"], 2)},
        {"Metric": "Weighted Cash %", "Value": round(metrics["weighted_cash_pct"], 2)},
        {"Metric": "Portfolio Health Score", "Value": f"{metrics['health']['total']} / 100"},
        {"Metric": "Risk Bucket", "Value": health_score_risk_bucket(metrics["health"]["total"])},
        {"Metric": "Risk-Free Rate Assumption %", "Value": metrics["risk_free_rate_pct"]},
        {"Metric": "Report Generated On", "Value": datetime.now().strftime("%d-%b-%Y %H:%M")},
    ])
    _xl_write_df(ws, summary_df, r)

    # 2. Fund Allocation
    ws = wb.create_sheet("Fund Allocation")
    r = _xl_write_title(ws, "Fund-wise Allocation")
    _xl_write_df(ws, metrics["allocation_df"], r)

    # 3. Fund Analysis
    ws = wb.create_sheet("Fund Analysis")
    row = _xl_write_title(ws, "Fund Analysis (funds held in this portfolio)")
    for fund_name in metrics["allocation_df"]["Fund"]:
        fund = FUNDS[fund_name]
        ws.cell(row=row, column=1, value=fund_name).font = XLFont(bold=True, size=12)
        row += 1
        info_df = pd.DataFrame([
            {"Field": "Category", "Value": fund.category},
            {"Field": "NAV", "Value": fund.nav},
            {"Field": "AUM (Rs. Cr)", "Value": fund.aum_cr},
            {"Field": "Expense Ratio %", "Value": fund.expense_ratio_pct},
            {"Field": "1Y Return %", "Value": fund.return_1y_pct},
            {"Field": "3Y CAGR %", "Value": fund.cagr_3y_pct},
            {"Field": "5Y CAGR %", "Value": fund.cagr_5y_pct},
            {"Field": "Risk Level", "Value": fund.risk_level},
            {"Field": "Benchmark", "Value": fund.benchmark},
        ])
        row = _xl_write_df(ws, info_df, row)

    # 4. Underlying Holdings
    ws = wb.create_sheet("Underlying Holdings")
    row = _xl_write_title(ws, "Underlying Holdings by Fund")
    for fund_name in metrics["allocation_df"]["Fund"]:
        fund = FUNDS[fund_name]
        ws.cell(row=row, column=1, value=fund_name).font = XLFont(bold=True, size=12)
        row += 1
        hold_df = pd.DataFrame(
            [{"Company": c, "Sector": COMPANY_SECTOR_MAP.get(c, "Others"), "Weight %": w}
             for c, w in fund.top_holdings(50)]
        )
        row = _xl_write_df(ws, hold_df, row)

    # 5. Stock Exposure (Portfolio X-Ray)
    ws = wb.create_sheet("Stock Exposure (X-Ray)")
    r = _xl_write_title(ws, "Portfolio X-Ray - Effective Stock Exposure")
    _xl_write_df(ws, metrics["exposure_df"], r, exclude_cols=["_contributors"])

    # 6. Overlap Analysis
    ws = wb.create_sheet("Overlap Analysis")
    r = _xl_write_title(ws, "Fund Overlap Matrix (%)")
    overlap_display = metrics["overlap_matrix"].reset_index().rename(columns={"index": "Fund"})
    r = _xl_write_df(ws, overlap_display, r)
    ws.cell(row=r, column=1, value=METHODOLOGY_OVERLAP_TEXT).alignment = Alignment(wrap_text=True)
    ws.row_dimensions[r].height = 45

    # 7. Sector Analysis
    ws = wb.create_sheet("Sector Analysis")
    r = _xl_write_title(ws, "Sector-wise Effective Exposure")
    _xl_write_df(ws, metrics["sector_df"], r)

    # 8. Risk Analysis
    ws = wb.create_sheet("Risk Analysis")
    r = _xl_write_title(ws, f"Risk Analysis  (Sample/Simulated NAV history; risk-free rate assumption: {metrics['risk_free_rate_pct']}%)")
    r = _xl_write_df(ws, metrics["risk_df"], r)
    portfolio_risk_df = pd.DataFrame([{
        "Metric": "Portfolio (weighted average)",
        "Volatility % (annualised)": round(metrics["risk"]["volatility_pct"], 2),
        "Sharpe Ratio": round(metrics["risk"]["sharpe_ratio"], 2),
        "Max Drawdown %": round(metrics["risk"]["max_drawdown_pct"], 2),
    }])
    _xl_write_df(ws, portfolio_risk_df, r)

    # 9. Alerts
    ws = wb.create_sheet("Alerts")
    r = _xl_write_title(ws, "Alerts")
    alerts_df = alerts_to_df(metrics["alerts"])
    _xl_write_df(ws, alerts_df, r)

    # 10. AI Insights
    ws = wb.create_sheet("AI Insights")
    r = _xl_write_title(ws, "AI Insights (rule-based explainability)")
    ws.cell(row=r, column=1, value=generate_ai_narrative(metrics)).alignment = Alignment(wrap_text=True)
    ws.column_dimensions["A"].width = 110
    ws.row_dimensions[r].height = 90

    # 11. Methodology
    ws = wb.create_sheet("Methodology")
    row = _xl_write_title(ws, "Methodology & Assumptions")
    for text in [DISCLAIMER_FULL, DEMO_DATA_DISCLAIMER, METHODOLOGY_OVERLAP_TEXT, METHODOLOGY_HEALTH_TEXT]:
        ws.cell(row=row, column=1, value=text).alignment = Alignment(wrap_text=True)
        ws.row_dimensions[row].height = 45
        row += 2
    ws.column_dimensions["A"].width = 110

    wb.save(path)
    return path


def _docx_add_heading(doc, text, level=1):
    return doc.add_heading(text, level=level)


def _docx_add_table_from_df(doc, df: pd.DataFrame, exclude_cols=None, max_rows=100):
    exclude_cols = exclude_cols or []
    cols = [c for c in df.columns if c not in exclude_cols]
    table = doc.add_table(rows=1, cols=len(cols))
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0].cells
    for j, col in enumerate(cols):
        hdr[j].text = str(col)
        for p in hdr[j].paragraphs:
            for run in p.runs:
                run.bold = True
    for _, row in df.head(max_rows).iterrows():
        cells = table.add_row().cells
        for j, col in enumerate(cols):
            value = row[col]
            if isinstance(value, (np.floating, float)):
                value = f"{float(value):,.2f}"
            cells[j].text = str(value)
    return table


def export_to_word(path, portfolio: Portfolio, metrics: dict):
    if not metrics.get("has_portfolio"):
        raise ValueError("Cannot export a report for an empty portfolio.")

    doc = Document()

    # ---- Cover page ----
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(APP_FULL_TITLE)
    run.bold = True
    run.font.size = Pt(30)
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = sub.add_run(APP_SUBTITLE)
    sub_run.italic = True
    sub_run.font.size = Pt(13)
    demo = doc.add_paragraph()
    demo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    demo.add_run(DEMO_DATA_LABEL).bold = True
    meta_p = doc.add_paragraph()
    meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta_p.add_run(f"Report generated on {datetime.now().strftime('%d-%b-%Y %H:%M')}")
    doc.add_page_break()

    # ---- Executive summary ----
    _docx_add_heading(doc, "Executive Summary", level=1)
    doc.add_paragraph(generate_ai_narrative(metrics))

    # ---- Portfolio overview ----
    _docx_add_heading(doc, "Portfolio Overview", level=1)
    overview_df = pd.DataFrame([
        {"Metric": "Total Investment", "Value": format_inr(metrics["total_investment"])},
        {"Metric": "Number of Funds", "Value": metrics["allocation_df"]["Fund"].nunique()},
        {"Metric": "Weighted Expense Ratio", "Value": format_pct(metrics["weighted_expense_ratio"])},
        {"Metric": "Weighted Equity / Debt / Cash",
         "Value": f"{metrics['weighted_equity_pct']:.1f}% / {metrics['weighted_debt_pct']:.1f}% / {metrics['weighted_cash_pct']:.1f}%"},
        {"Metric": "Portfolio Health Score", "Value": f"{metrics['health']['total']} / 100 ({health_score_risk_bucket(metrics['health']['total'])})"},
    ])
    _docx_add_table_from_df(doc, overview_df)

    # ---- Fund-wise analysis ----
    _docx_add_heading(doc, "Fund-wise Analysis", level=1)
    for fund_name in metrics["allocation_df"]["Fund"]:
        fund = FUNDS[fund_name]
        _docx_add_heading(doc, fund_name, level=2)
        info_df = pd.DataFrame([
            {"Field": "Category", "Value": fund.category},
            {"Field": "NAV", "Value": fund.nav},
            {"Field": "Expense Ratio", "Value": format_pct(fund.expense_ratio_pct)},
            {"Field": "1Y / 3Y / 5Y Returns", "Value": f"{fund.return_1y_pct:.1f}% / {fund.cagr_3y_pct:.1f}% / {fund.cagr_5y_pct:.1f}%"},
            {"Field": "Risk Level", "Value": fund.risk_level},
            {"Field": "Benchmark", "Value": fund.benchmark},
        ])
        _docx_add_table_from_df(doc, info_df)
        doc.add_paragraph("Top Holdings:")
        top_df = pd.DataFrame([{"Company": c, "Weight %": w} for c, w in fund.top_holdings(5)])
        _docx_add_table_from_df(doc, top_df)

    # ---- Portfolio X-Ray ----
    doc.add_page_break()
    _docx_add_heading(doc, "Portfolio X-Ray - Top Underlying Exposures", level=1)
    doc.add_paragraph(
        "Effective exposure combines each fund's holding weight with the amount you have "
        "invested in that fund (see Methodology for a worked example)."
    )
    _docx_add_table_from_df(doc, metrics["exposure_df"].head(15), exclude_cols=["_contributors"])

    # ---- Overlap analysis ----
    _docx_add_heading(doc, "Overlap Analysis", level=1)
    doc.add_paragraph(METHODOLOGY_OVERLAP_TEXT)
    overlap_display = metrics["overlap_matrix"].reset_index().rename(columns={"index": "Fund"})
    _docx_add_table_from_df(doc, overlap_display)

    # ---- Sector concentration ----
    _docx_add_heading(doc, "Sector Concentration", level=1)
    _docx_add_table_from_df(doc, metrics["sector_df"])

    # ---- Risk analysis ----
    doc.add_page_break()
    _docx_add_heading(doc, "Risk Analysis", level=1)
    doc.add_paragraph(
        f"Assumption - Risk-free rate used: {metrics['risk_free_rate_pct']}% "
        "(user-configurable analytical assumption). Figures are computed from the "
        "sample/simulated NAV history bundled with this prototype."
    )
    _docx_add_table_from_df(doc, metrics["risk_df"])

    # ---- Portfolio Health Score ----
    _docx_add_heading(doc, "Portfolio Health Score", level=1)
    doc.add_paragraph(METHODOLOGY_HEALTH_TEXT)
    comp_df = pd.DataFrame([
        {"Component": k.replace("_", " ").title(), "Score": v, "Out of": metrics["health"]["max_components"][k]}
        for k, v in metrics["health"]["components"].items()
    ])
    _docx_add_table_from_df(doc, comp_df)
    doc.add_paragraph(f"Total Portfolio Health Score: {metrics['health']['total']} / 100").runs[0].bold = True

    # ---- Key observations / Alerts ----
    _docx_add_heading(doc, "Key Observations & Alerts", level=1)
    if metrics["alerts"]:
        for a in metrics["alerts"]:
            doc.add_paragraph(f"[{a['severity']}] {a['category']}: {a['message']}", style="List Bullet")
    else:
        doc.add_paragraph("No threshold-based alerts were triggered for this portfolio.")

    # ---- Methodology ----
    doc.add_page_break()
    _docx_add_heading(doc, "Methodology", level=1)
    doc.add_paragraph(METHODOLOGY_OVERLAP_TEXT)
    doc.add_paragraph(METHODOLOGY_HEALTH_TEXT)
    doc.add_paragraph(
        "MF X-Ray Analytical Thresholds used for alerts: " +
        "; ".join(f"{k.replace('_', ' ')} = {v}" for k, v in THRESHOLDS.items()) + "."
    )

    # ---- Disclaimer ----
    _docx_add_heading(doc, "Disclaimer", level=1)
    doc.add_paragraph(DISCLAIMER_FULL)
    doc.add_paragraph(DEMO_DATA_DISCLAIMER)

    doc.save(path)
    return path


# =============================================================================
# SECTION 14 : GUI COMPONENTS
# =============================================================================
SECTION_NAMES = [
    "Dashboard", "My Portfolio", "Fund Analysis", "Portfolio X-Ray", "Overlap Analyzer",
    "Sector Analysis", "Risk Analysis", "Portfolio Changes", "What-If Simulator",
    "SIP Analysis", "AI Insights", "Reports", "Data Management", "About",
]

_MPL_STATE = {"ready": False, "FigureCanvasTkAgg": None, "Figure": None}


def _ensure_mpl_backend():
    """Lazily switch matplotlib to the interactive Tk backend the first time
    a chart is actually drawn. If this fails for any reason (e.g. Tcl/Tk
    graphics libraries missing), charts degrade gracefully to a text note
    instead of crashing the application -- tables remain fully available."""
    if _MPL_STATE["ready"]:
        return True
    try:
        matplotlib.use("TkAgg", force=True)
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        _MPL_STATE["FigureCanvasTkAgg"] = FigureCanvasTkAgg
        _MPL_STATE["Figure"] = Figure
        _MPL_STATE["ready"] = True
        return True
    except Exception as exc:  # pragma: no cover - environment specific
        print("MF X-Ray: chart backend unavailable, falling back to tables only:", exc)
        return False


class ScrollableFrame(Frame):
    """A Frame that scrolls vertically -- used as the container for every
    section so the app is usable even on smaller screens (Section 27)."""

    def __init__(self, parent, bg=None):
        super().__init__(parent, bg=bg or COLORS["bg"])
        canvas = Canvas(self, bg=bg or COLORS["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient=VERTICAL, command=canvas.yview)
        self.inner = Frame(canvas, bg=bg or COLORS["bg"])

        self.inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=self.inner, anchor=NW)
        canvas.configure(yscrollcommand=vsb.set)

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            delta = -1 * (event.delta // 120) if event.delta else 0
            if delta:
                canvas.yview_scroll(int(delta), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)   # Windows / macOS
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Linux
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)


class MFXRayApp:
    """The main Tkinter application. This class only builds and refreshes
    widgets; every number it displays comes from the pure functions in
    Sections 6-13 above via compute_all_metrics()."""

    def __init__(self, root):
        self.root = root
        self.debug_mode = BooleanVar(value=False)
        self.portfolio = Portfolio()
        self.snapshots = {}          # label -> metrics dict (a saved point-in-time exposure)
        self.risk_free_rate = DoubleVar(value=ASSUMPTIONS["risk_free_rate_pct"])
        self.current_section = "Dashboard"
        self.last_analysis_time = None
        self.last_export_path = None
        self._metrics = compute_all_metrics(self.portfolio, self.risk_free_rate.get())

        self._setup_window()
        self._build_style()
        self._build_header()
        self._build_body()
        self.show_section("Dashboard")

    # ------------------------------------------------------------------ #
    # Window / layout scaffolding
    # ------------------------------------------------------------------ #
    def _setup_window(self):
        self.root.title(f"{APP_FULL_TITLE} - {APP_SUBTITLE}")
        try:
            self.root.state("zoomed")           # Windows
        except Exception:
            try:
                self.root.attributes("-zoomed", True)  # some Linux window managers
            except Exception:
                w = self.root.winfo_screenwidth()
                h = self.root.winfo_screenheight()
                self.root.geometry(f"{max(1200, w - 100)}x{max(800, h - 100)}+20+20")
        self.root.minsize(1100, 700)
        self.root.configure(bg=COLORS["bg"])

    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 10), background="white",
                         fieldbackground="white")
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"),
                         background=COLORS["accent"], foreground="white")
        style.map("Treeview.Heading", background=[("active", COLORS["accent_dark"])])
        style.configure("Nav.TButton", font=("Segoe UI", 11), padding=8)
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(14, 6))

    def _build_header(self):
        header = Frame(self.root, bg=COLORS["header_bg"], height=92)
        header.pack(side=TOP, fill=X)
        header.pack_propagate(False)

        left = Frame(header, bg=COLORS["header_bg"])
        left.pack(side=LEFT, fill=Y, padx=20, pady=8)
        Label(left, text=APP_FULL_TITLE, font=("Segoe UI", 22, "bold"),
              fg="white", bg=COLORS["header_bg"]).pack(anchor=W)
        Label(left, text=APP_SUBTITLE, font=("Segoe UI", 10),
              fg="#B9C6DA", bg=COLORS["header_bg"]).pack(anchor=W)
        Label(left, text=DISCLAIMER_SHORT, font=("Segoe UI", 8), wraplength=760, justify=LEFT,
              fg="#8FA0BC", bg=COLORS["header_bg"]).pack(anchor=W, pady=(4, 0))

        right = Frame(header, bg=COLORS["header_bg"])
        right.pack(side=RIGHT, fill=Y, padx=20, pady=10)
        self.status_label = Label(right, justify=RIGHT, font=("Segoe UI", 9),
                                   fg="#D7E2F2", bg=COLORS["header_bg"])
        self.status_label.pack(anchor=E)
        ttk.Button(right, text="Load Demo Portfolio", style="Accent.TButton",
                   command=self.load_demo_portfolio).pack(anchor=E, pady=(6, 0))
        self._refresh_status_label()

    def _refresh_status_label(self):
        last = self.last_analysis_time.strftime("%d-%b-%Y %H:%M") if self.last_analysis_time else "Not yet run"
        self.status_label.configure(text=(
            f"{DEMO_DATA_LABEL}\n"
            f"Funds available: {len(FUNDS)}   |   Version: {APP_VERSION}\n"
            f"Last analysis: {last}"
        ))

    def _build_body(self):
        body = Frame(self.root, bg=COLORS["bg"])
        body.pack(side=TOP, fill=BOTH, expand=True)

        self.sidebar = Frame(body, bg=COLORS["sidebar"], width=230)
        self.sidebar.pack(side=LEFT, fill=Y)
        self.sidebar.pack_propagate(False)

        self.nav_buttons = {}
        for name in SECTION_NAMES:
            btn = Button(self.sidebar, text=name, anchor=W, relief="flat",
                         bg=COLORS["sidebar"], fg=COLORS["sidebar_text"], activebackground=COLORS["sidebar_active"],
                         activeforeground="white", bd=0, font=("Segoe UI", 11), padx=18, pady=10,
                         command=lambda n=name: self.show_section(n))
            btn.pack(fill=X)
            self.nav_buttons[name] = btn

        self.content_outer = Frame(body, bg=COLORS["bg"])
        self.content_outer.pack(side=LEFT, fill=BOTH, expand=True)

        self.footer = Frame(self.root, bg=COLORS["border"], height=24)
        self.footer.pack(side=BOTTOM, fill=X)
        self.footer_label = Label(self.footer, text=DISCLAIMER_FULL, font=("Segoe UI", 8),
                                   fg=COLORS["text_muted"], bg=COLORS["border"], wraplength=1400)
        self.footer_label.pack(side=LEFT, padx=10)

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #
    def show_section(self, name):
        self.current_section = name
        for n, btn in self.nav_buttons.items():
            btn.configure(bg=COLORS["sidebar_active"] if n == name else COLORS["sidebar"])

        for child in self.content_outer.winfo_children():
            child.destroy()

        scrollable = ScrollableFrame(self.content_outer)
        scrollable.pack(fill=BOTH, expand=True)
        parent = scrollable.inner

        metrics = self.recompute_metrics()
        builder = getattr(self, "_build_" + name.lower().replace(" ", "_").replace("-", "_"))
        try:
            builder(parent, metrics)
        except Exception as exc:  # Section 31: never show a raw crash to the user
            self._render_error(parent, exc)

    def _render_error(self, parent, exc):
        Label(parent, text="Something went wrong while displaying this section.",
              font=("Segoe UI", 12, "bold"), fg=COLORS["red"], bg=COLORS["bg"]).pack(anchor=W, padx=20, pady=(20, 4))
        Label(parent, text=str(exc), font=("Segoe UI", 10), fg=COLORS["text_muted"],
              bg=COLORS["bg"], wraplength=900, justify=LEFT).pack(anchor=W, padx=20)
        if self.debug_mode.get():
            box = Text(parent, height=18, wrap="none")
            box.insert("1.0", traceback.format_exc())
            box.configure(state=DISABLED)
            box.pack(fill=BOTH, expand=True, padx=20, pady=10)

    def recompute_metrics(self):
        self._metrics = compute_all_metrics(self.portfolio, self.risk_free_rate.get())
        self.last_analysis_time = datetime.now()
        self._refresh_status_label()
        return self._metrics

    def refresh_current_section(self):
        self.show_section(self.current_section)

    # ------------------------------------------------------------------ #
    # Small reusable widget builders
    # ------------------------------------------------------------------ #
    def _section_title(self, parent, title, subtitle=None):
        Label(parent, text=title, font=("Segoe UI", 18, "bold"), fg=COLORS["text_dark"],
              bg=COLORS["bg"]).pack(anchor=W, padx=24, pady=(20, 0))
        if subtitle:
            Label(parent, text=subtitle, font=("Segoe UI", 10), fg=COLORS["text_muted"],
                  bg=COLORS["bg"], wraplength=1100, justify=LEFT).pack(anchor=W, padx=24, pady=(2, 10))
        else:
            Frame(parent, bg=COLORS["bg"], height=10).pack()

    def _card(self, parent, **pack_kw):
        outer = Frame(parent, bg=COLORS["bg"])
        outer.pack(fill=X, padx=24, pady=8, **pack_kw)
        card = Frame(outer, bg=COLORS["card_bg"], highlightbackground=COLORS["border"], highlightthickness=1)
        card.pack(fill=BOTH, expand=True)
        return card

    def _kpi_row(self, parent, kpis):
        """kpis: list of (title, value, subtitle_or_None, color_or_None)"""
        row = Frame(parent, bg=COLORS["bg"])
        row.pack(fill=X, padx=16, pady=8)
        for title, value, subtitle, color in kpis:
            cell = Frame(row, bg=COLORS["card_bg"], highlightbackground=COLORS["border"], highlightthickness=1)
            cell.pack(side=LEFT, fill=BOTH, expand=True, padx=8, pady=4, ipady=10)
            Label(cell, text=title, font=("Segoe UI", 9, "bold"), fg=COLORS["text_muted"],
                  bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
            Label(cell, text=str(value), font=("Segoe UI", 20, "bold"),
                  fg=color or COLORS["text_dark"], bg=COLORS["card_bg"]).pack(anchor=W, padx=14)
            if subtitle:
                Label(cell, text=subtitle, font=("Segoe UI", 8), fg=COLORS["text_muted"],
                      bg=COLORS["card_bg"], wraplength=180, justify=LEFT).pack(anchor=W, padx=14, pady=(0, 8))
            else:
                Frame(cell, bg=COLORS["card_bg"], height=8).pack()
        return row

    def _make_table(self, parent, df: pd.DataFrame, height=10, col_formats=None, exclude_cols=None,
                     highlight_top=0, highlight_color="#FFF3CD"):
        """Builds a scrollable ttk.Treeview from a DataFrame. col_formats is
        an optional {column_name: callable(value)->str} map."""
        exclude_cols = exclude_cols or []
        col_formats = col_formats or {}
        cols = [c for c in df.columns if c not in exclude_cols]

        wrapper = Frame(parent, bg=COLORS["card_bg"])
        wrapper.pack(fill=BOTH, expand=True, padx=10, pady=10)

        tree = ttk.Treeview(wrapper, columns=cols, show="headings", height=height)
        for c in cols:
            tree.heading(c, text=c)
            width = 260 if c.lower() in ("company", "fund", "sector", "funds holding it", "message", "category") else 140
            tree.column(c, width=width, anchor=W if width == 260 else CENTER)

        vsb = ttk.Scrollbar(wrapper, orient=VERTICAL, command=tree.yview)
        hsb = ttk.Scrollbar(wrapper, orient=HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        wrapper.grid_rowconfigure(0, weight=1)
        wrapper.grid_columnconfigure(0, weight=1)

        tree.tag_configure("highlight", background=highlight_color)

        for i, (_, row) in enumerate(df.iterrows()):
            values = []
            for c in cols:
                v = row[c]
                if c in col_formats:
                    v = col_formats[c](v)
                elif isinstance(v, float):
                    v = f"{v:,.2f}"
                values.append(v)
            tag = "highlight" if highlight_top and i < highlight_top else ""
            tree.insert("", "end", values=values, tags=(tag,) if tag else ())

        if df.empty:
            Label(wrapper, text="No data to display.", bg=COLORS["card_bg"],
                  fg=COLORS["text_muted"]).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        return tree

    def _embed_figure(self, parent, draw_fn, figsize=(6, 4)):
        """draw_fn(ax) draws onto a matplotlib Axes. Falls back to a plain
        text note if the Tk chart backend isn't available in this
        environment (see _ensure_mpl_backend)."""
        if not _ensure_mpl_backend():
            Label(parent, text="(Chart preview unavailable in this environment -- see the table above/below for the same data.)",
                  bg=COLORS["card_bg"], fg=COLORS["text_muted"], font=("Segoe UI", 9, "italic")).pack(pady=10)
            return None
        Figure_ = _MPL_STATE["Figure"]
        FigureCanvasTkAgg_ = _MPL_STATE["FigureCanvasTkAgg"]
        fig = Figure_(figsize=figsize, dpi=100)
        ax = fig.add_subplot(111)
        try:
            draw_fn(ax)
        except Exception as exc:
            Label(parent, text=f"(Could not render chart: {exc})", bg=COLORS["card_bg"],
                  fg=COLORS["text_muted"]).pack(pady=10)
            return None
        fig.tight_layout()
        canvas = FigureCanvasTkAgg_(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=BOTH, expand=True, padx=10, pady=10)
        return canvas

    def _empty_state(self, parent, message="No portfolio yet. Add funds under 'My Portfolio', or click 'Load Demo Portfolio' above."):
        box = Frame(parent, bg=COLORS["card_bg"], highlightbackground=COLORS["border"], highlightthickness=1)
        box.pack(fill=X, padx=24, pady=40, ipady=30)
        Label(box, text=message, font=("Segoe UI", 12), fg=COLORS["text_muted"],
              bg=COLORS["card_bg"], wraplength=700, justify=CENTER).pack()
        ttk.Button(box, text="Load Demo Portfolio", style="Accent.TButton",
                   command=self.load_demo_portfolio).pack(pady=10)

    def _methodology_box(self, parent, text):
        box = Frame(parent, bg="#EEF3FB", highlightbackground=COLORS["border"], highlightthickness=1)
        box.pack(fill=X, padx=24, pady=(4, 14))
        Label(box, text="Methodology", font=("Segoe UI", 9, "bold"), fg=COLORS["accent_dark"],
              bg="#EEF3FB").pack(anchor=W, padx=12, pady=(8, 0))
        Label(box, text=text, font=("Segoe UI", 9), fg=COLORS["text_dark"], bg="#EEF3FB",
              wraplength=1100, justify=LEFT).pack(anchor=W, padx=12, pady=(2, 8))

    # ------------------------------------------------------------------ #
    # Portfolio-mutating actions (shared by several tabs)
    # ------------------------------------------------------------------ #
    def load_demo_portfolio(self):
        if not self.portfolio.is_empty():
            if not messagebox.askyesno("Load Demo Portfolio",
                                        "This will replace your current portfolio with the demo portfolio. Continue?"):
                return
        self.portfolio = demo_portfolio()
        messagebox.showinfo("Demo Portfolio Loaded",
                             "The demo portfolio (4 funds, Rs.9,00,000 total) has been loaded.")
        self.show_section("Dashboard")

    def clear_portfolio(self):
        if self.portfolio.is_empty():
            return
        if messagebox.askyesno("Clear Portfolio", "Remove all funds from the current portfolio?"):
            self.portfolio.clear()
            self.refresh_current_section()

    def add_fund_to_portfolio(self, fund_name, amount_str, method, date_str):
        try:
            if not fund_name:
                raise ValueError("Please select a fund.")
            try:
                amount = float(str(amount_str).replace(",", "").strip())
            except ValueError:
                raise ValueError("Investment amount must be a number.")
            if amount <= 0:
                raise ValueError("Investment amount must be greater than zero.")
            inv_date = date.today()
            if date_str:
                try:
                    inv_date = datetime.strptime(date_str.strip(), "%d-%m-%Y").date()
                except ValueError:
                    raise ValueError("Investment date must be in DD-MM-YYYY format.")
            self.portfolio.add(fund_name, amount, method, inv_date)
        except ValueError as exc:
            messagebox.showerror("Cannot Add Fund", str(exc))
            return
        self.refresh_current_section()

    def remove_fund_from_portfolio(self, fund_name):
        if not fund_name:
            messagebox.showinfo("Remove Fund", "Please select a fund row to remove first.")
            return
        self.portfolio.remove_fund(fund_name)
        self.refresh_current_section()

    def save_snapshot(self, label):
        label = (label or "").strip()
        if not label:
            messagebox.showerror("Save Snapshot", "Please enter a name for this snapshot.")
            return
        if self.portfolio.is_empty():
            messagebox.showerror("Save Snapshot", "Cannot save a snapshot of an empty portfolio.")
            return
        metrics = compute_all_metrics(self.portfolio, self.risk_free_rate.get())
        self.snapshots[label] = {
            "saved_on": datetime.now(), "metrics": metrics,
            "portfolio": Portfolio(list(self.portfolio.entries)),
        }
        messagebox.showinfo("Snapshot Saved", f"Snapshot '{label}' saved with {len(self.portfolio.entries)} holdings.")
        self.refresh_current_section()

    def export_report(self, kind):
        if not self._metrics.get("has_portfolio"):
            messagebox.showerror("Export Report", "Build or load a portfolio before exporting a report.")
            return
        ext = "xlsx" if kind == "excel" else "docx"
        default_name = f"MF_XRay_Report_{date.today().strftime('%Y%m%d')}"
        path = filedialog.asksaveasfilename(
            title=f"Save {kind.title()} Report", defaultextension=f".{ext}", initialfile=default_name,
            filetypes=[(f"{kind.title()} file", f"*.{ext}")],
        )
        if not path:
            return
        try:
            if kind == "excel":
                export_to_excel(path, self.portfolio, self._metrics)
            else:
                export_to_word(path, self.portfolio, self._metrics)
            self.last_export_path = path
            messagebox.showinfo("Export Complete", f"Report saved to:\n{path}")
            self.refresh_current_section()
        except Exception as exc:
            messagebox.showerror("Export Failed", f"Could not create the report.\n\n{exc}")
            if self.debug_mode.get():
                traceback.print_exc()

    def run_sip_calculation(self, fund_name, amount_str, start_str, installments_str, result_holder):
        try:
            amount = float(str(amount_str).replace(",", "").strip())
            installments = int(str(installments_str).strip())
            start_dt = datetime.strptime(start_str.strip(), "%d-%m-%Y").date()
            result = simulate_sip(fund_name, amount, start_dt, installments)
            result_holder(result, None)
        except Exception as exc:
            result_holder(None, str(exc))

    # ------------------------------------------------------------------ #
    # SECTION: Dashboard
    # ------------------------------------------------------------------ #
    def _build_dashboard(self, parent, metrics):
        self._section_title(parent, "Dashboard", "A one-page snapshot of your current portfolio.")

        if not metrics["has_portfolio"]:
            self._empty_state(parent)
            return

        health = metrics["health"]
        risk_bucket = health_score_risk_bucket(health["total"])
        overlap_pairs = metrics["overlap_pairs"]
        avg_overlap = sum(p[2] for p in overlap_pairs) / len(overlap_pairs) if overlap_pairs else 0.0
        top_sector = metrics["sector_df"].iloc[0] if not metrics["sector_df"].empty else None
        top_stock_pct = metrics["concentration"].get("largest_pct", 0.0)
        top_stock_name = metrics["concentration"].get("largest_company", "-")

        kpis = [
            ("TOTAL INVESTMENT", format_inr(metrics["total_investment"]), None, COLORS["accent_dark"]),
            ("NUMBER OF FUNDS", metrics["allocation_df"]["Fund"].nunique(), None, COLORS["text_dark"]),
            ("EQUITY EXPOSURE", format_pct(metrics["weighted_equity_pct"], 0), "Weighted across funds", COLORS["text_dark"]),
            ("HIGHEST SECTOR EXPOSURE", format_pct(top_sector["Effective Exposure %"]) if top_sector is not None else "-",
             top_sector["Sector"] if top_sector is not None else "", COLORS["text_dark"]),
        ]
        self._kpi_row(parent, kpis)
        kpis2 = [
            ("HIGHEST STOCK EXPOSURE", format_pct(top_stock_pct), top_stock_name, COLORS["text_dark"]),
            ("AVG. PORTFOLIO OVERLAP", format_pct(avg_overlap), "Average of every fund pair", COLORS["amber"] if avg_overlap >= THRESHOLDS["high_overlap_pct"] else COLORS["text_dark"]),
            ("PORTFOLIO HEALTH SCORE", f"{health['total']} / 100", "MF X-Ray analytical score", RISK_BUCKET_COLORS.get(risk_bucket)),
            ("RISK LEVEL", risk_bucket, "Derived from Health Score", RISK_BUCKET_COLORS.get(risk_bucket)),
        ]
        self._kpi_row(parent, kpis2)

        cols_frame = Frame(parent, bg=COLORS["bg"])
        cols_frame.pack(fill=X, padx=16)
        left = Frame(cols_frame, bg=COLORS["bg"])
        left.pack(side=LEFT, fill=BOTH, expand=True)
        right = Frame(cols_frame, bg=COLORS["bg"])
        right.pack(side=LEFT, fill=BOTH, expand=True)

        # Allocation pie chart (left)
        card = Frame(left, bg=COLORS["card_bg"], highlightbackground=COLORS["border"], highlightthickness=1)
        card.pack(fill=BOTH, expand=True, padx=8, pady=4)
        Label(card, text="Portfolio Allocation", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
        alloc = metrics["allocation_df"]

        def draw_pie(ax):
            ax.pie(alloc["Allocation %"], labels=alloc["Fund"], autopct="%1.1f%%", startangle=90,
                   textprops={"fontsize": 8})
            ax.set_title("Fund-wise Allocation", fontsize=10)

        self._embed_figure(card, draw_pie, figsize=(5, 4))

        # Alerts + AI insight (right)
        card2 = Frame(right, bg=COLORS["card_bg"], highlightbackground=COLORS["border"], highlightthickness=1)
        card2.pack(fill=BOTH, expand=True, padx=8, pady=4)
        Label(card2, text="Top Alerts", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 4))
        alerts = metrics["alerts"][:4]
        if not alerts:
            Label(card2, text="No threshold-based alerts triggered for this portfolio.",
                  bg=COLORS["card_bg"], fg=COLORS["text_muted"]).pack(anchor=W, padx=14)
        for a in alerts:
            color = COLORS["red"] if a["severity"] == "High" else COLORS["amber"]
            row = Frame(card2, bg=COLORS["card_bg"])
            row.pack(fill=X, padx=14, pady=3, anchor=W)
            Label(row, text=f"[{a['severity']}]", fg=color, bg=COLORS["card_bg"],
                  font=("Segoe UI", 9, "bold")).pack(side=LEFT)
            Label(row, text=f" {a['category']}: {a['message']}", bg=COLORS["card_bg"], fg=COLORS["text_dark"],
                  wraplength=480, justify=LEFT, font=("Segoe UI", 9)).pack(side=LEFT)

        Label(card2, text="AI Insight", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(14, 2))
        Label(card2, text=generate_ai_narrative(metrics), bg=COLORS["card_bg"], fg=COLORS["text_dark"],
              wraplength=520, justify=LEFT, font=("Segoe UI", 9)).pack(anchor=W, padx=14, pady=(0, 14))

        Label(parent, text=DEMO_DATA_DISCLAIMER, font=("Segoe UI", 8, "italic"),
              fg=COLORS["text_muted"], bg=COLORS["bg"]).pack(anchor=W, padx=24, pady=(6, 16))

    # ------------------------------------------------------------------ #
    # SECTION: My Portfolio
    # ------------------------------------------------------------------ #
    def _build_my_portfolio(self, parent, metrics):
        self._section_title(parent, "My Portfolio",
                             "Add the mutual funds you hold, with the amount actually invested in each. "
                             "Only figures you enter are used anywhere in this application.")

        form_card = self._card(parent)
        form = Frame(form_card, bg=COLORS["card_bg"])
        form.pack(fill=X, padx=16, pady=16)

        Label(form, text="Fund", bg=COLORS["card_bg"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=W, padx=4)
        Label(form, text="Investment Amount (Rs.)", bg=COLORS["card_bg"], font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky=W, padx=4)
        Label(form, text="Method", bg=COLORS["card_bg"], font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky=W, padx=4)
        Label(form, text="Investment Date (DD-MM-YYYY)", bg=COLORS["card_bg"], font=("Segoe UI", 9, "bold")).grid(row=0, column=3, sticky=W, padx=4)

        fund_var = StringVar(value=list(FUNDS.keys())[0])
        amount_var = StringVar()
        method_var = StringVar(value="Lump Sum")
        date_var = StringVar(value=date.today().strftime("%d-%m-%Y"))

        ttk.Combobox(form, textvariable=fund_var, values=list(FUNDS.keys()), state="readonly", width=26).grid(row=1, column=0, padx=4, pady=6)
        Entry(form, textvariable=amount_var, width=18).grid(row=1, column=1, padx=4)
        ttk.Combobox(form, textvariable=method_var, values=["Lump Sum", "SIP"], state="readonly", width=12).grid(row=1, column=2, padx=4)
        Entry(form, textvariable=date_var, width=16).grid(row=1, column=3, padx=4)
        ttk.Button(form, text="Add Fund", style="Accent.TButton",
                   command=lambda: self.add_fund_to_portfolio(fund_var.get(), amount_var.get(), method_var.get(), date_var.get())
                   ).grid(row=1, column=4, padx=10)

        if metrics["has_portfolio"]:
            alloc = metrics["allocation_df"]
            table_card = self._card(parent)
            Label(table_card, text="Current Holdings", font=("Segoe UI", 12, "bold"),
                  bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
            self._make_table(table_card, alloc, height=8,
                              col_formats={"Amount": lambda v: format_inr(v), "Allocation %": format_pct,
                                           "Expense Ratio %": format_pct, "Equity %": format_pct,
                                           "Debt %": format_pct, "Cash %": format_pct})

            remove_row = Frame(table_card, bg=COLORS["card_bg"])
            remove_row.pack(fill=X, padx=14, pady=(0, 12))
            remove_var = StringVar(value=alloc["Fund"].iloc[0])
            Label(remove_row, text="Remove fund:", bg=COLORS["card_bg"]).pack(side=LEFT)
            ttk.Combobox(remove_row, textvariable=remove_var, values=alloc["Fund"].tolist(),
                         state="readonly", width=28).pack(side=LEFT, padx=6)
            ttk.Button(remove_row, text="Remove", command=lambda: self.remove_fund_from_portfolio(remove_var.get())).pack(side=LEFT, padx=6)
            ttk.Button(remove_row, text="Clear Entire Portfolio", command=self.clear_portfolio).pack(side=LEFT, padx=16)

            summary_card = self._card(parent)
            Label(summary_card, text="Portfolio Summary", font=("Segoe UI", 12, "bold"),
                  bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 4))
            summary_text = (
                f"Total Investment: {format_inr(metrics['total_investment'])}    |    "
                f"Number of Funds: {alloc['Fund'].nunique()}    |    "
                f"Weighted Expense Ratio: {format_pct(metrics['weighted_expense_ratio'])}    |    "
                f"Weighted Exposure -> Equity {format_pct(metrics['weighted_equity_pct'])} / "
                f"Debt {format_pct(metrics['weighted_debt_pct'])} / Cash {format_pct(metrics['weighted_cash_pct'])}"
            )
            Label(summary_card, text=summary_text, bg=COLORS["card_bg"], fg=COLORS["text_dark"],
                  wraplength=1100, justify=LEFT, font=("Segoe UI", 9)).pack(anchor=W, padx=14, pady=(0, 14))
        else:
            self._empty_state(parent, "No holdings added yet. Use the form above, or click 'Load Demo Portfolio' in the header.")

    # ------------------------------------------------------------------ #
    # SECTION: Fund Analysis
    # ------------------------------------------------------------------ #
    def _build_fund_analysis(self, parent, metrics):
        self._section_title(parent, "Fund Analysis", "Inspect any of the funds in the MF X-Ray sample dataset in detail.")

        control = Frame(parent, bg=COLORS["bg"])
        control.pack(fill=X, padx=24)
        Label(control, text="Select Fund:", bg=COLORS["bg"], font=("Segoe UI", 10, "bold")).pack(side=LEFT)
        fund_var = StringVar(value=list(FUNDS.keys())[0])
        combo = ttk.Combobox(control, textvariable=fund_var, values=list(FUNDS.keys()), state="readonly", width=30)
        combo.pack(side=LEFT, padx=8)

        holder = Frame(parent, bg=COLORS["bg"])
        holder.pack(fill=BOTH, expand=True)

        def render(*_):
            for w in holder.winfo_children():
                w.destroy()
            fund = FUNDS[fund_var.get()]

            top = Frame(holder, bg=COLORS["bg"])
            top.pack(fill=X)
            left = self._card_in(top)
            Label(left, text="Fund Overview", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 4))
            for label, value in [
                ("Category", fund.category), ("NAV", f"{fund.nav:.2f}"), ("AUM", f"Rs. {fund.aum_cr:,.0f} Cr"),
                ("Expense Ratio", format_pct(fund.expense_ratio_pct)), ("Risk Level", fund.risk_level),
                ("Benchmark", fund.benchmark), ("Portfolio Date", fund.portfolio_date.strftime("%d-%b-%Y")),
            ]:
                self._kv_line(left, label, value)
            Frame(left, bg=COLORS["card_bg"], height=10).pack()

            mid = self._card_in(top)
            Label(mid, text="Performance", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 4))
            for label, value in [("1 Year Return", fund.return_1y_pct), ("3 Year CAGR", fund.cagr_3y_pct),
                                  ("5 Year CAGR", fund.cagr_5y_pct)]:
                self._kv_line(mid, label, format_pct(value))
            Label(mid, text="Asset Allocation", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(14, 4))
            for label, value in [("Equity %", fund.equity_pct), ("Debt %", fund.debt_pct), ("Cash %", fund.cash_pct)]:
                self._kv_line(mid, label, format_pct(value))
            Frame(mid, bg=COLORS["card_bg"], height=10).pack()

            bottom = Frame(holder, bg=COLORS["bg"])
            bottom.pack(fill=BOTH, expand=True)
            left2 = self._card_in(bottom)
            Label(left2, text="Top Holdings", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
            holdings_df = pd.DataFrame([{"Company": c, "Sector": COMPANY_SECTOR_MAP.get(c, "Others"), "Weight %": w}
                                         for c, w in fund.top_holdings(10)])
            self._make_table(left2, holdings_df, height=10, col_formats={"Weight %": format_pct})
            if fund.other_holdings_pct > 0:
                Label(left2, text=f"Other/unlisted equity holdings: {format_pct(fund.other_holdings_pct)}",
                      bg=COLORS["card_bg"], fg=COLORS["text_muted"], font=("Segoe UI", 8, "italic")).pack(anchor=W, padx=14, pady=(0, 10))

            right2 = self._card_in(bottom)
            Label(right2, text="Sector Allocation (this fund only)", font=("Segoe UI", 12, "bold"),
                  bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
            sector_alloc = fund.sector_allocation()
            sector_df = pd.DataFrame(sorted(sector_alloc.items(), key=lambda kv: kv[1], reverse=True),
                                      columns=["Sector", "Weight %"])
            self._make_table(right2, sector_df, height=10, col_formats={"Weight %": format_pct})

        combo.bind("<<ComboboxSelected>>", render)
        render()

    def _card_in(self, parent):
        outer = Frame(parent, bg=COLORS["bg"])
        outer.pack(side=LEFT, fill=BOTH, expand=True, padx=8, pady=8)
        card = Frame(outer, bg=COLORS["card_bg"], highlightbackground=COLORS["border"], highlightthickness=1)
        card.pack(fill=BOTH, expand=True)
        return card

    def _kv_line(self, parent, label, value):
        row = Frame(parent, bg=COLORS["card_bg"])
        row.pack(fill=X, padx=14, pady=1)
        Label(row, text=label + ":", bg=COLORS["card_bg"], fg=COLORS["text_muted"],
              font=("Segoe UI", 9), width=16, anchor=W).pack(side=LEFT)
        Label(row, text=str(value), bg=COLORS["card_bg"], fg=COLORS["text_dark"],
              font=("Segoe UI", 9, "bold")).pack(side=LEFT)

    # ------------------------------------------------------------------ #
    # SECTION: Portfolio X-Ray (core feature)
    # ------------------------------------------------------------------ #
    def _build_portfolio_x_ray(self, parent, metrics):
        self._section_title(parent, "Portfolio X-Ray",
                             "Combines every fund's underlying holdings with the amount you have invested in "
                             "each fund, to show your TRUE effective exposure to every underlying company -- "
                             "looking through the mutual-fund wrapper.")
        if not metrics["has_portfolio"]:
            self._empty_state(parent)
            return

        example = self._card(parent)
        Label(example, text="Worked Example", font=("Segoe UI", 11, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 2))
        Label(example, text=(
            "If Fund A (Rs.5,00,000 invested) holds Company X at 10%, and Fund B (Rs.5,00,000 invested) holds "
            "Company X at 8%, your effective exposure to Company X = (5,00,000 x 10%) + (5,00,000 x 8%) = "
            "Rs.90,000, i.e. 9.0% of a Rs.10,00,000 portfolio."
        ), bg=COLORS["card_bg"], fg=COLORS["text_muted"], wraplength=1100, justify=LEFT,
              font=("Segoe UI", 9)).pack(anchor=W, padx=14, pady=(0, 10))

        table_card = self._card(parent)
        Label(table_card, text="Effective Stock Exposure (sorted highest first, top 5 highlighted)",
              font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
        display_df = metrics["exposure_df"].drop(columns=["_contributors"])
        self._make_table(table_card, display_df, height=14, highlight_top=5,
                          col_formats={"Exposure Amount": format_inr, "Effective Exposure %": format_pct})

        self._methodology_box(parent,
            "Effective Exposure % = (sum across every fund holding this company of amount invested in that fund "
            "x that fund's weight in the company) / total portfolio investment. This is a straightforward "
            "look-through calculation, not an estimate.")

    # ------------------------------------------------------------------ #
    # SECTION: Overlap Analyzer
    # ------------------------------------------------------------------ #
    def _build_overlap_analyzer(self, parent, metrics):
        self._section_title(parent, "Overlap Analyzer",
                             "Identifies companies held by more than one of your funds, and measures how "
                             "similar each pair of funds is in composition.")
        if not metrics["has_portfolio"]:
            self._empty_state(parent)
            return

        overlap_matrix = metrics["overlap_matrix"]
        matrix_card = self._card(parent)
        Label(matrix_card, text="Fund Overlap Matrix (%)", font=("Segoe UI", 12, "bold"),
              bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
        matrix_display = overlap_matrix.reset_index().rename(columns={"index": "Fund"})
        fmt = {c: format_pct for c in matrix_display.columns if c != "Fund"}
        self._make_table(matrix_card, matrix_display, height=min(10, len(matrix_display) + 1), col_formats=fmt)

        cols_frame = Frame(parent, bg=COLORS["bg"])
        cols_frame.pack(fill=BOTH, expand=True, padx=16)
        left = self._card_in(cols_frame)
        Label(left, text="Overlap Heatmap", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))

        def draw_heatmap(ax):
            data = overlap_matrix.values
            im = ax.imshow(data, cmap="OrRd", vmin=0, vmax=100)
            labels = [n if len(n) < 14 else n[:12] + "…" for n in overlap_matrix.index]
            ax.set_xticks(range(len(labels)))
            ax.set_yticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
            ax.set_yticklabels(labels, fontsize=7)
            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    ax.text(j, i, f"{data[i, j]:.0f}", ha="center", va="center", fontsize=7,
                            color="white" if data[i, j] > 55 else "black")
            ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        self._embed_figure(left, draw_heatmap, figsize=(5.5, 4.5))

        right = self._card_in(cols_frame)
        Label(right, text="Companies Held by Multiple Funds", font=("Segoe UI", 12, "bold"),
              bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
        overlap_stocks = metrics["exposure_df"][metrics["exposure_df"]["Number of Funds"] > 1].drop(columns=["_contributors"])
        self._make_table(right, overlap_stocks, height=10,
                          col_formats={"Exposure Amount": format_inr, "Effective Exposure %": format_pct})

        pairs_card = self._card(parent)
        Label(pairs_card, text="Fund Pairs, Highest Overlap First", font=("Segoe UI", 12, "bold"),
              bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
        pairs_df = pd.DataFrame(metrics["overlap_pairs"], columns=["Fund A", "Fund B", "Overlap %"])
        pairs_df["Flag"] = pairs_df["Overlap %"].apply(
            lambda v: "HIGH OVERLAP" if v >= THRESHOLDS["high_overlap_pct"] else "")
        self._make_table(pairs_card, pairs_df, height=min(8, len(pairs_df) + 1), col_formats={"Overlap %": format_pct})

        self._methodology_box(parent, METHODOLOGY_OVERLAP_TEXT)

    # ------------------------------------------------------------------ #
    # SECTION: Sector Analysis
    # ------------------------------------------------------------------ #
    def _build_sector_analysis(self, parent, metrics):
        self._section_title(parent, "Sector Analysis", "Aggregates your effective underlying exposure by sector.")
        if not metrics["has_portfolio"]:
            self._empty_state(parent)
            return

        sector_df = metrics["sector_df"].copy()
        sector_df["High Concentration?"] = sector_df["Effective Exposure %"].apply(
            lambda v: "Yes (MF X-Ray Analytical Threshold)" if v >= THRESHOLDS["high_sector_exposure_pct"] else "")

        cols_frame = Frame(parent, bg=COLORS["bg"])
        cols_frame.pack(fill=BOTH, expand=True, padx=16)
        left = self._card_in(cols_frame)
        Label(left, text="Sector Exposure", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
        self._make_table(left, sector_df, height=12,
                          col_formats={"Exposure Amount": format_inr, "Effective Exposure %": format_pct})

        right = self._card_in(cols_frame)
        Label(right, text="Sector Allocation Chart", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))

        def draw_donut(ax):
            ax.pie(sector_df["Effective Exposure %"], labels=sector_df["Sector"], autopct="%1.1f%%",
                   startangle=90, wedgeprops={"width": 0.42}, textprops={"fontsize": 7})
            ax.set_title("Effective Sector Exposure", fontsize=10)

        self._embed_figure(right, draw_donut, figsize=(5.5, 4.5))

        self._methodology_box(parent,
            f"MF X-Ray Analytical Threshold for 'high sector concentration': {format_pct(THRESHOLDS['high_sector_exposure_pct'])} "
            f"of the portfolio's effective exposure. Sectors are assigned using this application's own sample "
            f"company-to-sector mapping; a future version can source this from an official classification.")

    # ------------------------------------------------------------------ #
    # SECTION: Risk Analysis
    # ------------------------------------------------------------------ #
    def _build_risk_analysis(self, parent, metrics):
        self._section_title(parent, "Risk Analysis",
                             "Volatility, Sharpe Ratio and Maximum Drawdown, computed from the sample/simulated "
                             "NAV history bundled with this prototype.")

        assump = self._card(parent)
        row = Frame(assump, bg=COLORS["card_bg"])
        row.pack(fill=X, padx=14, pady=12)
        Label(row, text="Assumption -- Risk-Free Rate:", bg=COLORS["card_bg"],
              font=("Segoe UI", 10, "bold")).pack(side=LEFT)
        rf_var = StringVar(value=str(self.risk_free_rate.get()))
        Entry(row, textvariable=rf_var, width=8).pack(side=LEFT, padx=8)
        Label(row, text="% per annum  (used only for the Sharpe Ratio -- change and recalculate anytime)",
              bg=COLORS["card_bg"], fg=COLORS["text_muted"], font=("Segoe UI", 9)).pack(side=LEFT)

        def recalc():
            try:
                self.risk_free_rate.set(float(rf_var.get()))
            except ValueError:
                messagebox.showerror("Invalid Value", "Risk-free rate must be a number.")
                return
            self.refresh_current_section()

        ttk.Button(row, text="Recalculate", command=recalc).pack(side=LEFT, padx=12)

        if not metrics["has_portfolio"]:
            self._empty_state(parent)
            return

        table_card = self._card(parent)
        Label(table_card, text="Fund-wise Risk Metrics (sample/simulated NAV history)", font=("Segoe UI", 12, "bold"),
              bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
        self._make_table(table_card, metrics["risk_df"], height=8,
                          col_formats={"Volatility % (annualised)": format_pct, "Max Drawdown %": format_pct,
                                       "Sharpe Ratio": lambda v: f"{v:.2f}"})

        risk = metrics["risk"]
        self._kpi_row(parent, [
            ("PORTFOLIO VOLATILITY (ANNUALISED)", format_pct(risk["volatility_pct"]), "Weighted average of fund volatility", None),
            ("PORTFOLIO SHARPE RATIO", f"{risk['sharpe_ratio']:.2f}", f"Risk-free rate: {self.risk_free_rate.get()}%", None),
            ("PORTFOLIO MAX DRAWDOWN", format_pct(risk["max_drawdown_pct"]), "Weighted average of fund drawdowns", None),
        ])

        self._methodology_box(parent,
            "Portfolio-level figures are the investment-weighted average of each fund's own volatility, "
            "Sharpe Ratio and maximum drawdown. This is a simplified analytical approximation that does NOT "
            "account for correlation between funds -- a genuinely diversified portfolio's real volatility "
            "would typically be somewhat lower than this weighted average. " + DEMO_DATA_DISCLAIMER)

    # ------------------------------------------------------------------ #
    # SECTION: Portfolio Changes
    # ------------------------------------------------------------------ #
    def _build_portfolio_changes(self, parent, metrics):
        self._section_title(parent, "Portfolio Changes",
                             "Save the current portfolio as a snapshot, then compare any two snapshots to see "
                             "what changed.")

        save_card = self._card(parent)
        row = Frame(save_card, bg=COLORS["card_bg"])
        row.pack(fill=X, padx=14, pady=12)
        Label(row, text="Snapshot Name:", bg=COLORS["card_bg"], font=("Segoe UI", 10, "bold")).pack(side=LEFT)
        name_var = StringVar(value=date.today().strftime("Snapshot %d-%b-%Y"))
        Entry(row, textvariable=name_var, width=30).pack(side=LEFT, padx=8)
        ttk.Button(row, text="Save Current Portfolio as Snapshot", style="Accent.TButton",
                   command=lambda: self.save_snapshot(name_var.get())).pack(side=LEFT, padx=8)

        if not self.snapshots:
            self._empty_state(parent, "No snapshots saved yet. Build/load a portfolio, then save it as a snapshot above.")
            return

        list_card = self._card(parent)
        Label(list_card, text="Saved Snapshots", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
        snap_rows = pd.DataFrame([
            {"Snapshot": label, "Saved On": v["saved_on"].strftime("%d-%b-%Y %H:%M"),
             "Total Investment": v["metrics"]["total_investment"], "Funds": v["metrics"]["allocation_df"]["Fund"].nunique()}
            for label, v in self.snapshots.items()
        ])
        self._make_table(list_card, snap_rows, height=min(6, len(snap_rows) + 1), col_formats={"Total Investment": format_inr})

        if len(self.snapshots) < 2:
            Label(parent, text="Save at least one more snapshot to compare changes over time.",
                  bg=COLORS["bg"], fg=COLORS["text_muted"]).pack(anchor=W, padx=24, pady=10)
            return

        compare_card = self._card(parent)
        row2 = Frame(compare_card, bg=COLORS["card_bg"])
        row2.pack(fill=X, padx=14, pady=12)
        labels = list(self.snapshots.keys())
        prev_var = StringVar(value=labels[0])
        curr_var = StringVar(value=labels[-1])
        Label(row2, text="Previous:", bg=COLORS["card_bg"]).pack(side=LEFT)
        ttk.Combobox(row2, textvariable=prev_var, values=labels, state="readonly", width=24).pack(side=LEFT, padx=6)
        Label(row2, text="Current:", bg=COLORS["card_bg"]).pack(side=LEFT, padx=(14, 0))
        ttk.Combobox(row2, textvariable=curr_var, values=labels, state="readonly", width=24).pack(side=LEFT, padx=6)

        result_holder = Frame(parent, bg=COLORS["bg"])
        result_holder.pack(fill=BOTH, expand=True)

        def compare(*_):
            for w in result_holder.winfo_children():
                w.destroy()
            prev_metrics = self.snapshots[prev_var.get()]["metrics"]
            curr_metrics = self.snapshots[curr_var.get()]["metrics"]
            diff_df = self._exposure_diff(prev_metrics["exposure_df"], curr_metrics["exposure_df"])

            card = self._card_wrap(result_holder)
            Label(card, text="Stock-Level Changes", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
            self._make_table(card, diff_df, height=12, col_formats={
                "Previous %": format_pct, "Current %": format_pct, "Change (pp)": lambda v: f"{v:+.2f} pp"})

            sector_diff = self._sector_diff(prev_metrics["sector_df"], curr_metrics["sector_df"])
            card2 = self._card_wrap(result_holder)
            Label(card2, text="Sector-Level Changes", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
            self._make_table(card2, sector_diff, height=8, col_formats={
                "Previous %": format_pct, "Current %": format_pct, "Change (pp)": lambda v: f"{v:+.2f} pp"})

        ttk.Button(row2, text="Compare", style="Accent.TButton", command=compare).pack(side=LEFT, padx=16)
        compare()

    def _card_wrap(self, parent):
        card = Frame(parent, bg=COLORS["card_bg"], highlightbackground=COLORS["border"], highlightthickness=1)
        card.pack(fill=X, padx=24, pady=8)
        return card

    @staticmethod
    def _exposure_diff(prev_df, curr_df):
        prev = {r["Company"]: r["Effective Exposure %"] for _, r in prev_df.iterrows()} if not prev_df.empty else {}
        curr = {r["Company"]: r["Effective Exposure %"] for _, r in curr_df.iterrows()} if not curr_df.empty else {}
        companies = set(prev) | set(curr)
        rows = []
        for c in companies:
            p, cu = prev.get(c, 0.0), curr.get(c, 0.0)
            change = cu - p
            if c not in prev:
                status = "New Holding"
            elif c not in curr:
                status = "Removed Holding"
            elif change > 0.05:
                status = "Increased"
            elif change < -0.05:
                status = "Reduced"
            else:
                status = "No Material Change"
            rows.append({"Company": c, "Previous %": p, "Current %": cu, "Change (pp)": change, "Status": status})
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.reindex(df["Change (pp)"].abs().sort_values(ascending=False).index).reset_index(drop=True)
        return df

    @staticmethod
    def _sector_diff(prev_df, curr_df):
        prev = {r["Sector"]: r["Effective Exposure %"] for _, r in prev_df.iterrows()} if not prev_df.empty else {}
        curr = {r["Sector"]: r["Effective Exposure %"] for _, r in curr_df.iterrows()} if not curr_df.empty else {}
        sectors = set(prev) | set(curr)
        rows = []
        for s in sectors:
            p, cu = prev.get(s, 0.0), curr.get(s, 0.0)
            rows.append({"Sector": s, "Previous %": p, "Current %": cu, "Change (pp)": cu - p})
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.reindex(df["Change (pp)"].abs().sort_values(ascending=False).index).reset_index(drop=True)
        return df

    # ------------------------------------------------------------------ #
    # SECTION: What-If Simulator
    # ------------------------------------------------------------------ #
    def _build_what_if_simulator(self, parent, metrics):
        self._section_title(parent, "What-If Simulator",
                             "Simulate removing a fund from your portfolio and see how every metric would change. "
                             "This is a simulation only -- MF X-Ray does not issue buy/sell recommendations.")
        if not metrics["has_portfolio"]:
            self._empty_state(parent)
            return

        control = self._card(parent)
        row = Frame(control, bg=COLORS["card_bg"])
        row.pack(fill=X, padx=14, pady=12)
        Label(row, text="Remove Fund:", bg=COLORS["card_bg"], font=("Segoe UI", 10, "bold")).pack(side=LEFT)
        fund_names = metrics["allocation_df"]["Fund"].tolist()
        remove_var = StringVar(value=fund_names[0])
        ttk.Combobox(row, textvariable=remove_var, values=fund_names, state="readonly", width=28).pack(side=LEFT, padx=8)

        result_holder = Frame(parent, bg=COLORS["bg"])
        result_holder.pack(fill=BOTH, expand=True)

        def run_simulation():
            for w in result_holder.winfo_children():
                w.destroy()
            sim = simulate_remove_fund(self.portfolio, remove_var.get(), self.risk_free_rate.get())
            before_row = whatif_summary_row("Before", sim["before"])
            after_row = whatif_summary_row(f"After removing '{remove_var.get()}'", sim["after"])
            summary_df = pd.DataFrame([before_row, after_row])

            card = self._card_wrap(result_holder)
            Label(card, text="Before vs. After", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
            self._make_table(card, summary_df, height=2, col_formats={
                "Total Investment": format_inr, "Avg. Pairwise Overlap %": format_pct,
                "Top 5 Concentration %": format_pct, "Largest Sector %": format_pct})

            if sim["after"]["has_portfolio"]:
                diff_df = self._exposure_diff(sim["before"]["exposure_df"], sim["after"]["exposure_df"])
                diff_df = diff_df[diff_df["Change (pp)"].abs() > 0.01]
                card2 = self._card_wrap(result_holder)
                Label(card2, text="Underlying Exposure Changes", font=("Segoe UI", 12, "bold"),
                      bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
                self._make_table(card2, diff_df, height=10, col_formats={
                    "Previous %": format_pct, "Current %": format_pct, "Change (pp)": lambda v: f"{v:+.2f} pp"})
            else:
                Label(result_holder, text="Removing this fund would leave the portfolio empty.",
                      bg=COLORS["bg"], fg=COLORS["text_muted"]).pack(anchor=W, padx=24, pady=10)

        ttk.Button(row, text="Run What-If Simulation", style="Accent.TButton", command=run_simulation).pack(side=LEFT, padx=12)
        run_simulation()

    # ------------------------------------------------------------------ #
    # SECTION: SIP Analysis
    # ------------------------------------------------------------------ #
    def _build_sip_analysis(self, parent, metrics):
        self._section_title(parent, "SIP Analysis",
                             "A Systematic Investment Plan (SIP) is an investment METHOD, not a separate "
                             "product -- it simply means investing a fixed amount into the same mutual fund "
                             "SCHEME every month.")

        form = self._card(parent)
        grid = Frame(form, bg=COLORS["card_bg"])
        grid.pack(fill=X, padx=14, pady=14)
        Label(grid, text="Fund", bg=COLORS["card_bg"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=W, padx=6)
        Label(grid, text="Monthly SIP Amount (Rs.)", bg=COLORS["card_bg"], font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky=W, padx=6)
        Label(grid, text="Start Date (DD-MM-YYYY)", bg=COLORS["card_bg"], font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky=W, padx=6)
        Label(grid, text="Number of Instalments", bg=COLORS["card_bg"], font=("Segoe UI", 9, "bold")).grid(row=0, column=3, sticky=W, padx=6)

        fund_var = StringVar(value=list(FUNDS.keys())[0])
        amount_var = StringVar(value="10000")
        start_var = StringVar(value=(date.today().replace(day=1) - timedelta(days=730)).strftime("%d-%m-%Y"))
        inst_var = StringVar(value="24")

        ttk.Combobox(grid, textvariable=fund_var, values=list(FUNDS.keys()), state="readonly", width=26).grid(row=1, column=0, padx=6, pady=6)
        Entry(grid, textvariable=amount_var, width=16).grid(row=1, column=1, padx=6)
        Entry(grid, textvariable=start_var, width=16).grid(row=1, column=2, padx=6)
        Entry(grid, textvariable=inst_var, width=10).grid(row=1, column=3, padx=6)

        result_holder = Frame(parent, bg=COLORS["bg"])
        result_holder.pack(fill=BOTH, expand=True)

        def calculate():
            for w in result_holder.winfo_children():
                w.destroy()

            def handle(result, error):
                if error:
                    messagebox.showerror("SIP Calculation Failed", error)
                    return
                card = self._card_wrap(result_holder)
                Label(card, text=f"SIP Result -- {result['fund_name']}", font=("Segoe UI", 12, "bold"),
                      bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 4))
                xirr_text = f"{result['xirr_pct']:.2f}%" if result["xirr_pct"] is not None else "Could not be computed"
                self._kv_line(card, "Total Amount Invested", format_inr(result["invested_total"]))
                self._kv_line(card, "Units Accumulated", f"{result['units']:.4f}")
                self._kv_line(card, "Current Value", format_inr(result["current_value"]))
                self._kv_line(card, "Absolute Return", format_pct(result["abs_return_pct"]))
                self._kv_line(card, "Annualised Return (XIRR)", xirr_text)
                Frame(card, bg=COLORS["card_bg"], height=8).pack()
                if result["used_extrapolation_assumption"]:
                    Label(card, text=(
                        "Assumption: part of this SIP schedule falls beyond the sample NAV history bundled "
                        f"with this prototype. NAVs beyond that point were extrapolated using an assumed "
                        f"{ASSUMPTIONS['sip_fallback_growth_pct']}% p.a. growth rate (MF X-Ray assumption, "
                        "editable in the source code)."
                    ), bg=COLORS["card_bg"], fg=COLORS["amber"], wraplength=1000, justify=LEFT,
                        font=("Segoe UI", 8, "italic")).pack(anchor=W, padx=14, pady=(0, 10))

                sched_df = pd.DataFrame(result["schedule"])
                card2 = self._card_wrap(result_holder)
                Label(card2, text="Instalment Schedule", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
                self._make_table(card2, sched_df, height=10, col_formats={
                    "NAV": lambda v: f"{v:.2f}", "Units": lambda v: f"{v:.4f}",
                    "Date": lambda v: v.strftime("%d-%b-%Y") if hasattr(v, "strftime") else str(v)})

            self.run_sip_calculation(fund_var.get(), amount_var.get(), start_var.get(), inst_var.get(), handle)

        ttk.Button(grid, text="Calculate", style="Accent.TButton", command=calculate).grid(row=1, column=4, padx=12)
        calculate()

        self._methodology_box(parent,
            "SIP units for each instalment = instalment amount / NAV on that date (sample NAV history). "
            "Current Value = total units x latest available NAV. XIRR is solved numerically (Newton-Raphson, "
            "with a bisection fallback) from the full instalment-by-instalment cash-flow schedule.")

    # ------------------------------------------------------------------ #
    # SECTION: AI Insights
    # ------------------------------------------------------------------ #
    def _build_ai_insights(self, parent, metrics):
        self._section_title(parent, "AI Insights",
                             "A rule-based explainability layer that turns the calculations elsewhere in this "
                             "application into plain-language observations. It never invents a number that "
                             "hasn't actually been calculated.")

        narrative_card = self._card(parent)
        Label(narrative_card, text="Portfolio Narrative", font=("Segoe UI", 12, "bold"),
              bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 4))
        Label(narrative_card, text=generate_ai_narrative(metrics), bg=COLORS["card_bg"], fg=COLORS["text_dark"],
              wraplength=1100, justify=LEFT, font=("Segoe UI", 10)).pack(anchor=W, padx=14, pady=(0, 14))

        ask_card = self._card(parent)
        Label(ask_card, text="Ask MF X-Ray", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 4))
        row = Frame(ask_card, bg=COLORS["card_bg"])
        row.pack(fill=X, padx=14)
        q_var = StringVar()
        Entry(row, textvariable=q_var, width=70).pack(side=LEFT, padx=(0, 8), pady=4)
        answer_label = Label(ask_card, text="", bg=COLORS["card_bg"], fg=COLORS["text_dark"],
                              wraplength=1100, justify=LEFT, font=("Segoe UI", 10, "italic"))

        def ask(*_):
            answer_label.configure(text="A: " + answer_question(q_var.get(), metrics))
            answer_label.pack(anchor=W, padx=14, pady=(8, 4))

        ttk.Button(row, text="Ask", style="Accent.TButton", command=ask).pack(side=LEFT)

        examples = [
            "Which companies have the highest exposure?", "Which two funds overlap the most?",
            "Which sector has the highest exposure?", "Why is my portfolio concentrated?",
            "Which fund contributes most to my risk?", "Explain my portfolio like a CA.",
        ]
        ex_frame = Frame(ask_card, bg=COLORS["card_bg"])
        ex_frame.pack(fill=X, padx=14, pady=(6, 14))
        Label(ex_frame, text="Try:", bg=COLORS["card_bg"], fg=COLORS["text_muted"],
              font=("Segoe UI", 8)).pack(side=LEFT)
        for ex in examples:
            def _set(e=ex):
                q_var.set(e)
                ask()
            ttk.Button(ex_frame, text=ex, command=_set).pack(side=LEFT, padx=3, pady=3)

        alerts_card = self._card(parent)
        Label(alerts_card, text="Alerts Feeding These Insights", font=("Segoe UI", 12, "bold"),
              bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
        alerts_df = alerts_to_df(metrics["alerts"])
        self._make_table(alerts_card, alerts_df, height=6)

    # ------------------------------------------------------------------ #
    # SECTION: Reports
    # ------------------------------------------------------------------ #
    def _build_reports(self, parent, metrics):
        self._section_title(parent, "Reports", "Export a full analysis of the current portfolio.")
        if not metrics["has_portfolio"]:
            self._empty_state(parent, "Build or load a portfolio before generating a report.")
            return

        card = self._card(parent)
        Label(card, text="Excel Report", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(12, 2))
        Label(card, text=("Portfolio Summary, Fund Allocation, Fund Analysis, Underlying Holdings, Stock Exposure, "
                           "Overlap Analysis, Sector Analysis, Risk Analysis, Alerts, AI Insights and Methodology "
                           "-- each on its own worksheet."),
              bg=COLORS["card_bg"], fg=COLORS["text_muted"], wraplength=1000, justify=LEFT,
              font=("Segoe UI", 9)).pack(anchor=W, padx=14)
        ttk.Button(card, text="Export to Excel", style="Accent.TButton",
                   command=lambda: self.export_report("excel")).pack(anchor=W, padx=14, pady=12)

        card2 = self._card(parent)
        Label(card2, text="Word Report", font=("Segoe UI", 12, "bold"), bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(12, 2))
        Label(card2, text=("A formatted document with a cover page, executive summary, portfolio overview, "
                            "fund-wise analysis, Portfolio X-Ray, overlap analysis, sector concentration, risk "
                            "analysis, Portfolio Health Score, key observations, alerts, methodology and disclaimer."),
              bg=COLORS["card_bg"], fg=COLORS["text_muted"], wraplength=1000, justify=LEFT,
              font=("Segoe UI", 9)).pack(anchor=W, padx=14)
        ttk.Button(card2, text="Export to Word", style="Accent.TButton",
                   command=lambda: self.export_report("word")).pack(anchor=W, padx=14, pady=12)

        if self.last_export_path:
            Label(parent, text=f"Last export: {self.last_export_path}", bg=COLORS["bg"],
                  fg=COLORS["text_muted"], font=("Segoe UI", 9, "italic")).pack(anchor=W, padx=24, pady=6)

    # ------------------------------------------------------------------ #
    # SECTION: Data Management
    # ------------------------------------------------------------------ #
    def _build_data_management(self, parent, metrics):
        self._section_title(parent, "Data Management",
                             f"View, add, edit, import or export the {DEMO_DATA_LABEL} used by this application.")

        actions = self._card(parent)
        row = Frame(actions, bg=COLORS["card_bg"])
        row.pack(fill=X, padx=14, pady=12)
        ttk.Button(row, text="Add / Edit Fund", command=self._open_fund_editor).pack(side=LEFT, padx=4)
        ttk.Button(row, text="Import Fund Data (CSV/Excel)", command=self._import_fund_data).pack(side=LEFT, padx=4)
        ttk.Button(row, text="Import Holdings (CSV/Excel)", command=self._import_holdings_data).pack(side=LEFT, padx=4)
        ttk.Button(row, text="Export Dataset (Excel)", command=self._export_dataset).pack(side=LEFT, padx=4)
        ttk.Checkbutton(row, text="Developer / Debug mode", variable=self.debug_mode).pack(side=LEFT, padx=20)

        table_card = self._card(parent)
        Label(table_card, text="Available Sample Funds", font=("Segoe UI", 12, "bold"),
              bg=COLORS["card_bg"]).pack(anchor=W, padx=14, pady=(10, 0))
        rows = [{
            "Fund": f.name, "Category": f.category, "NAV": f.nav, "AUM (Rs. Cr)": f.aum_cr,
            "Expense Ratio %": f.expense_ratio_pct, "Risk Level": f.risk_level,
            "Named Holdings": len(f.holdings), "Equity %": f.equity_pct,
        } for f in FUNDS.values()]
        self._make_table(table_card, pd.DataFrame(rows), height=8,
                          col_formats={"Expense Ratio %": format_pct, "Equity %": format_pct})

        Label(parent, text=(
            "Import templates -- Fund Data: Fund Name, Category, NAV, AUM_Cr, Expense_Ratio_Pct, Return_1Y_Pct, "
            "CAGR_3Y_Pct, CAGR_5Y_Pct, Risk_Level, Equity_Pct, Debt_Pct, Cash_Pct, Benchmark, Portfolio_Date.  "
            "Holdings: Fund Name, Company, Weight_Pct."
        ), bg=COLORS["bg"], fg=COLORS["text_muted"], wraplength=1100, justify=LEFT,
              font=("Segoe UI", 8, "italic")).pack(anchor=W, padx=24, pady=(4, 16))

    def _open_fund_editor(self):
        win = Toplevel(self.root)
        win.title("Add / Edit Fund")
        win.configure(bg=COLORS["bg"])
        win.geometry("560x640")

        fields = {}
        form = Frame(win, bg=COLORS["bg"])
        form.pack(fill=BOTH, expand=True, padx=16, pady=16)

        def add_field(label, default=""):
            Label(form, text=label, bg=COLORS["bg"], font=("Segoe UI", 9, "bold")).pack(anchor=W, pady=(6, 0))
            var = StringVar(value=default)
            Entry(form, textvariable=var, width=50).pack(anchor=W)
            fields[label] = var

        existing_names = list(FUNDS.keys())
        Label(form, text="Fund Name (existing funds can be edited)", bg=COLORS["bg"],
              font=("Segoe UI", 9, "bold")).pack(anchor=W, pady=(0, 0))
        name_var = StringVar(value="")
        ttk.Combobox(form, textvariable=name_var, values=existing_names, width=48).pack(anchor=W)
        fields["Fund Name"] = name_var

        for label in ["Category", "NAV", "AUM (Rs. Cr)", "Expense Ratio %", "1Y Return %", "3Y CAGR %",
                      "5Y CAGR %", "Risk Level (Low/Moderate/High/Very High)", "Equity %", "Debt %", "Cash %", "Benchmark"]:
            add_field(label)

        Label(form, text="Holdings -- one 'Company: Weight' per line", bg=COLORS["bg"],
              font=("Segoe UI", 9, "bold")).pack(anchor=W, pady=(6, 0))
        holdings_box = Text(form, height=8, width=50)
        holdings_box.pack(anchor=W)

        def load_existing(*_):
            name = name_var.get()
            if name in FUNDS:
                f = FUNDS[name]
                fields["Category"].set(f.category); fields["NAV"].set(str(f.nav))
                fields["AUM (Rs. Cr)"].set(str(f.aum_cr)); fields["Expense Ratio %"].set(str(f.expense_ratio_pct))
                fields["1Y Return %"].set(str(f.return_1y_pct)); fields["3Y CAGR %"].set(str(f.cagr_3y_pct))
                fields["5Y CAGR %"].set(str(f.cagr_5y_pct)); fields["Risk Level (Low/Moderate/High/Very High)"].set(f.risk_level)
                fields["Equity %"].set(str(f.equity_pct)); fields["Debt %"].set(str(f.debt_pct))
                fields["Cash %"].set(str(f.cash_pct)); fields["Benchmark"].set(f.benchmark)
                holdings_box.delete("1.0", END)
                holdings_box.insert("1.0", "\n".join(f"{c}: {w}" for c, w in f.holdings.items()))

        name_var.trace_add("write", lambda *a: load_existing()) if hasattr(name_var, "trace_add") else None

        def save():
            try:
                name = fields["Fund Name"].get().strip()
                if not name:
                    raise ValueError("Fund name is required.")
                if name in FUNDS and not messagebox.askyesno("Overwrite Fund", f"'{name}' already exists. Overwrite it?"):
                    return
                meta = {
                    "category": fields["Category"].get().strip() or "Uncategorised",
                    "nav": float(fields["NAV"].get()), "aum_cr": float(fields["AUM (Rs. Cr)"].get()),
                    "expense_ratio_pct": float(fields["Expense Ratio %"].get()),
                    "return_1y_pct": float(fields["1Y Return %"].get() or 0),
                    "cagr_3y_pct": float(fields["3Y CAGR %"].get() or 0),
                    "cagr_5y_pct": float(fields["5Y CAGR %"].get() or 0),
                    "risk_level": fields["Risk Level (Low/Moderate/High/Very High)"].get().strip() or "Moderate",
                    "equity_pct": float(fields["Equity %"].get() or 0), "debt_pct": float(fields["Debt %"].get() or 0),
                    "cash_pct": float(fields["Cash %"].get() or 0), "benchmark": fields["Benchmark"].get().strip() or "-",
                    "portfolio_date": PORTFOLIO_DATE,
                }
                holdings = {}
                for line in holdings_box.get("1.0", END).splitlines():
                    line = line.strip()
                    if not line or ":" not in line:
                        continue
                    company, weight = line.split(":", 1)
                    holdings[company.strip()] = float(weight.strip())
                FUND_META[name] = meta
                FUND_HOLDINGS[name] = holdings
                FUNDS[name] = Fund(name, meta, holdings)
                if name not in FUND_NAV_HISTORY:
                    FUND_NAV_HISTORY[name] = _generate_sample_nav_history()[name]
                messagebox.showinfo("Fund Saved", f"'{name}' has been saved.")
                win.destroy()
                self.refresh_current_section()
            except ValueError as exc:
                messagebox.showerror("Cannot Save Fund", f"Please check your entries.\n\n{exc}")

        ttk.Button(form, text="Save Fund", style="Accent.TButton", command=save).pack(anchor=W, pady=14)

    def _import_fund_data(self):
        path = filedialog.askopenfilename(title="Import Fund Data",
                                           filetypes=[("Spreadsheet files", "*.csv *.xlsx *.xls")])
        if not path:
            return
        try:
            df = pd.read_csv(path) if path.lower().endswith(".csv") else pd.read_excel(path)
            required = ["Fund Name", "Category", "NAV", "AUM_Cr", "Expense_Ratio_Pct", "Risk_Level",
                        "Equity_Pct", "Debt_Pct", "Cash_Pct", "Benchmark"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                raise ValueError(f"Missing required column(s): {', '.join(missing)}")
            existing_overlap = [n for n in df["Fund Name"] if n in FUNDS]
            if existing_overlap and not messagebox.askyesno(
                    "Overwrite Existing Funds?",
                    f"{len(existing_overlap)} fund(s) already exist ({', '.join(existing_overlap[:5])}...). Overwrite them?"):
                df = df[~df["Fund Name"].isin(existing_overlap)]
            for _, r in df.iterrows():
                name = str(r["Fund Name"]).strip()
                FUND_META[name] = {
                    "category": r["Category"], "nav": float(r["NAV"]), "aum_cr": float(r["AUM_Cr"]),
                    "expense_ratio_pct": float(r["Expense_Ratio_Pct"]),
                    "return_1y_pct": float(r.get("Return_1Y_Pct", 0) or 0),
                    "cagr_3y_pct": float(r.get("CAGR_3Y_Pct", 0) or 0), "cagr_5y_pct": float(r.get("CAGR_5Y_Pct", 0) or 0),
                    "risk_level": r["Risk_Level"], "equity_pct": float(r["Equity_Pct"]),
                    "debt_pct": float(r["Debt_Pct"]), "cash_pct": float(r["Cash_Pct"]),
                    "benchmark": r["Benchmark"], "portfolio_date": PORTFOLIO_DATE,
                }
                FUND_HOLDINGS.setdefault(name, {})
                FUNDS[name] = Fund(name, FUND_META[name], FUND_HOLDINGS[name])
            FUND_NAV_HISTORY.update(_generate_sample_nav_history())
            messagebox.showinfo("Import Complete", f"Imported {len(df)} fund(s).")
            self.refresh_current_section()
        except Exception as exc:
            messagebox.showerror("Import Failed", f"Could not import this file.\n\n{exc}")

    def _import_holdings_data(self):
        path = filedialog.askopenfilename(title="Import Holdings", filetypes=[("Spreadsheet files", "*.csv *.xlsx *.xls")])
        if not path:
            return
        try:
            df = pd.read_csv(path) if path.lower().endswith(".csv") else pd.read_excel(path)
            required = ["Fund Name", "Company", "Weight_Pct"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                raise ValueError(f"Missing required column(s): {', '.join(missing)}")
            unknown_funds = sorted(set(df["Fund Name"]) - set(FUNDS.keys()))
            if unknown_funds:
                raise ValueError(f"Unknown fund(s), add them first under 'Add / Edit Fund': {', '.join(unknown_funds)}")
            affected = sorted(set(df["Fund Name"]))
            if not messagebox.askyesno("Replace Holdings?",
                                        f"This will REPLACE all named holdings for: {', '.join(affected)}. Continue?"):
                return
            for fund_name in affected:
                sub = df[df["Fund Name"] == fund_name]
                FUND_HOLDINGS[fund_name] = {str(r["Company"]).strip(): float(r["Weight_Pct"]) for _, r in sub.iterrows()}
                FUNDS[fund_name] = Fund(fund_name, FUND_META[fund_name], FUND_HOLDINGS[fund_name])
                for company in FUND_HOLDINGS[fund_name]:
                    COMPANY_SECTOR_MAP.setdefault(company, "Others")
            messagebox.showinfo("Import Complete", f"Updated holdings for {len(affected)} fund(s).")
            self.refresh_current_section()
        except Exception as exc:
            messagebox.showerror("Import Failed", f"Could not import this file.\n\n{exc}")

    def _export_dataset(self):
        path = filedialog.asksaveasfilename(title="Export Dataset", defaultextension=".xlsx",
                                             initialfile="MF_XRay_Sample_Dataset",
                                             filetypes=[("Excel file", "*.xlsx")])
        if not path:
            return
        try:
            wb = openpyxl.Workbook()
            wb.remove(wb.active)
            ws1 = wb.create_sheet("Funds")
            fund_df = pd.DataFrame([f.to_dict() for f in FUNDS.values()]).drop(columns=["holdings"])
            _xl_write_df(ws1, fund_df, _xl_write_title(ws1, "Fund Data"))
            ws2 = wb.create_sheet("Holdings")
            rows = []
            for f in FUNDS.values():
                for c, w in f.holdings.items():
                    rows.append({"Fund Name": f.name, "Company": c, "Sector": COMPANY_SECTOR_MAP.get(c, "Others"), "Weight_Pct": w})
            _xl_write_df(ws2, pd.DataFrame(rows), _xl_write_title(ws2, "Underlying Holdings"))
            wb.save(path)
            messagebox.showinfo("Export Complete", f"Dataset exported to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", f"Could not export the dataset.\n\n{exc}")

    # ------------------------------------------------------------------ #
    # SECTION: About
    # ------------------------------------------------------------------ #
    def _build_about(self, parent, metrics):
        self._section_title(parent, "About MF X-Ray")
        card = self._card(parent)
        text = (
            f"{APP_FULL_TITLE}  |  {APP_SUBTITLE}\n"
            f"Version: {APP_VERSION}\n\n"
            f"Built as an ICAI AI Level 2 capstone project. MF X-Ray demonstrates how a mutual-fund "
            f"investor's true underlying exposure -- to individual companies and sectors -- can differ "
            f"from what fund-level allocation alone suggests, and applies a transparent, rule-based "
            f"explainability layer on top of standard portfolio analytics.\n\n"
            f"Deterministic Financial Analytics used: fund allocation, effective stock/sector exposure, "
            f"fund overlap, concentration, volatility, Sharpe Ratio, maximum drawdown and XIRR.\n\n"
            f"AI Layer used: rule-based natural-language insight generation, a keyword-matched portfolio "
            f"Q&A ('Ask MF X-Ray'), and threshold-driven alerting -- all built strictly on top of the "
            f"calculations above, never inventing a figure.\n\n"
            f"{DISCLAIMER_FULL}\n\n{DEMO_DATA_DISCLAIMER}\n\n"
            "Future Version Architecture (not implemented in this prototype):\n"
            "  Version 2 - real/official mutual-fund data, automated NAV updates, factsheet/PDF upload, "
            "portfolio-statement upload.\n"
            "  Version 3 - RAG-based AI, LLM-powered Q&A over a fund factsheet knowledge base, scheduled "
            "monitoring, email alerts, advanced anomaly detection.\n"
            "  Version 4 - multi-user login, cloud database, web and mobile interfaces, predictive "
            "analytics.\n\n"
            "This application works entirely offline and does not transmit portfolio data anywhere. It "
            "does not collect PAN, Aadhaar, bank details, passwords or brokerage credentials."
        )
        Label(card, text=text, bg=COLORS["card_bg"], fg=COLORS["text_dark"], wraplength=1100,
              justify=LEFT, font=("Segoe UI", 10)).pack(anchor=W, padx=18, pady=18)


# =============================================================================
# SECTION 15 : APPLICATION STARTUP
# =============================================================================
def main():
    try:
        root = Tk()
        app = MFXRayApp(root)  # noqa: F841 (kept alive by Tk's own reference graph)
        root.mainloop()
    except Exception:
        print("=" * 70)
        print("MF X-Ray encountered a fatal error while starting up:")
        traceback.print_exc()
        print("=" * 70)
        try:
            input("Press Enter to exit...")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
