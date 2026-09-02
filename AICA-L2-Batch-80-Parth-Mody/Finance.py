# ==============================================================================
#  PERSONAL FINANCE & DEBT IMPACT CALCULATOR  --  v2.6
#  Input Sheet | Calculation Engine | Output Sheet | Audit | Excel round-trip
#  Run:  python finance_planner.py          (Python 3.10+, built for 3.14)
#
#  v2.6 fixes
#    J. xl_sheet() was not idempotent: truncating a long name at 31 characters
#       could land on a space, which a second pass then stripped. The chart
#       series in the report therefore referenced a sheet name that did not
#       exist ("Unknown worksheet reference"), silently breaking the
#       amortisation chart for any loan with a long name - which every planned
#       goal loan has. Surfaced by the packaged build's self test.
#    K. Packaged as a standalone Windows application (see launcher.py and
#       FinancePlanner.spec). _ensure() no longer tries to pip-install when
#       frozen, and _launch() drives Streamlit's bootstrap in-process rather
#       than shelling out to sys.executable, which in a frozen build is the
#       application itself and would have relaunched it forever.
#
#  v2.5 fixes
#    H. Money columns added in v2.4 were never registered as money, so the goal
#       roadmap rendered raw floats (29714441.735167). The display formatter now
#       formats money with the same Indian grouping used everywhere else, adds a
#       compact option, and puts a % sign on percentages. Every new column is
#       registered, on screen and in the workbook.
#    I. "From other assets" was a black box. The engine now records every source
#       it draws on for each goal - which holding, its class, gross realised, the
#       tax and exit load paid on the way, and what actually reached the goal -
#       shown per goal on the roadmap, as a full table, and as a new
#       "24b Goal Funding Detail" sheet in the report.
#
#  v2.4 fixes
#    G. Replacement purchases were not modelled at all. A "house upgrade" kept the
#       old house on the books, kept servicing its loan alongside a second new
#       one (EMI 80,690 -> 198,602 on a single home), and wrote the entire
#       purchase price off to nowhere, so net worth fell by the full cost. Goals
#       now support selling the asset being replaced, settling the loan secured
#       on it from the proceeds, recovering that EMI as borrowing capacity before
#       the new loan is sized, and capitalising what was bought. Section 54
#       rollover is applied on a home-to-home upgrade.
#
#  v2.3 fixes
#    A. Excel dropdowns for Loan Type, Asset Class and Expense Category were
#       silently absent: Excel discards a list validation whose inline source
#       exceeds 255 characters, and those three were 301/295/346. Option lists
#       now live on a hidden sheet and are referenced as ranges, so the columns
#       genuinely constrain input. Unrecognised values are also flagged by the
#       validator rather than silently defaulting.
#    B. Deleting the grey notes row silently deleted the user's FIRST DATA ROW.
#       The row is now recognised by its content instead of assumed by position.
#    C. Workbooks used Western digit grouping (120,000,000) while the whole app
#       displays Indian grouping (12,00,00,000) - a 10x misread waiting to
#       happen. Both now use the Indian format.
#    D. A self-occupied home, a personal vehicle and personal valuables had no
#       home in the model, so they were missing from net worth. New asset
#       classes carry them: counted in net worth, shown as their own section,
#       never sold to plug a gap, and given no vote on the benchmark.
#    E. Goals were funded by unlimited imaginary borrowing, so everything read
#       ON TRACK. New borrowing is now capped by the EMI-to-income ceiling; what
#       will not fit is reported as refused borrowing and becomes a shortfall.
#    F. Verdict model corrected. Capital-gains tax was charged annually at the
#       full exit rate on assets that only pay it once, on sale; and one year of
#       volatility was charged against decisions running a decade or more. Each
#       loan is now judged over its own remaining life, against the marginal
#       vehicle your surplus actually flows into. A cheap long secured loan
#       reads as healthy leverage; a card balance is still condemned.
#
#  v2.2 fixes
#    1. Assumptions page crashed with IndexError (ASSUMPTION_FIELDS[22] on a
#       22-item list); eleven other help texts were off by one. Help is now
#       looked up by field name, not by position.
#    2. Cash-flow audit failed on the engine's own demo data. Goal payments,
#       the goal sinking fund drawn to make them and the proceeds of a planned
#       goal loan were missing from the identity, and an emergency-fund
#       drawdown was double-counted as an asset redemption.
#    3. Two goals falling in the same month overwrote each other's recorded
#       outflow instead of accumulating.
#    4. Residual surplus fell back to the emergency fund when no investable
#       holding existed, but was booked as a portfolio contribution, breaking
#       the portfolio identity.
#    5. Goals dated beyond the horizon were reported ON TRACK with zero
#       funding and broke the goal identity. Now labelled BEYOND HORIZON and
#       excluded from that test.
#    6. Let-out property interest was capped at the Section 24(b) limit. That
#       cap applies to a self-occupied property only.
#    7. Blank month-of-year / bonus month silently disabled the item.
#    8. Class defaults for return, volatility, days-to-cash and lock-in were
#       never applied, because the importer coerced blanks to zero.
#    9. Prepayment in 'emi' mode re-solved the tenure at the base rate,
#       ignoring the rate-shift scenario; prepayment headroom assumed a flat
#       5% penalty instead of the loan's own.
#   10. Two new audit tests (emergency fund and goal corpus continuity).
#
#  v2.2 performance: the monthly loop no longer touches pandas (~3x faster);
#       increment counting is O(1) rather than O(months); loan run-off totals
#       skip DataFrame construction; the demo template and the swap optimiser
#       are cached rather than rebuilt on every rerun.
#
#  v2.1 fixes: Excel sheet-name sanitiser (Excel forbids [ ] : * ? / \ and caps
#              names at 31 chars). Applied to the input template writer, the
#              template reader, the report writer and per-loan amortisation
#              tabs, so user-entered loan names containing slashes no longer
#              crash the export.
# ==============================================================================

# ------------------------------------------------------------------ BOOTSTRAP
import importlib, os, subprocess, sys

_REQUIRED = {
    "streamlit": "streamlit>=1.36", "pandas": "pandas>=2.2", "numpy": "numpy>=1.26",
    "plotly": "plotly>=5.20", "xlsxwriter": "xlsxwriter>=3.2", "openpyxl": "openpyxl>=3.1",
}


def _pip(a):
    return subprocess.call([sys.executable, "-m", "pip", *a])


def _frozen():
    """True inside a PyInstaller build, where every dependency is already
    bundled and there is no separate interpreter to shell out to."""
    return bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS")


def _ensure():
    if _frozen():
        return                      # dependencies are baked into the bundle
    miss = []
    for m, s in _REQUIRED.items():
        try:
            importlib.import_module(m)
        except Exception:
            miss.append(s)
    if not miss:
        return
    print("[setup] installing:", ", ".join(miss))
    _pip(["install", "--upgrade", "pip", "-q", "--disable-pip-version-check"])
    if _pip(["install", "-q", *miss]) != 0:
        if _pip(["install", "-q", "--pre", *miss]) != 0:
            _pip(["install", "--no-cache-dir", *miss])
    importlib.invalidate_caches()
    for m in _REQUIRED:
        try:
            importlib.import_module(m)
        except Exception as e:
            sys.exit(f"[setup] cannot import {m}: {e}\n  pip install "
                     + " ".join(_REQUIRED.values()))
    print("[setup] ready.")


_ensure()

import io, json, math

from xlsxwriter.utility import xl_col_to_name
from dataclasses import dataclass, field, fields
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

APP = "Personal Finance & Debt Impact Calculator"
VER = "2.6"
CCY = "\u20b9"


def _in_streamlit():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


def _launch():
    print(f"\n{APP} v{VER}\n[launch] opening browser app...\n")
    if _frozen():
        # sys.executable IS this exe, so a subprocess would relaunch the
        # launcher forever. Drive Streamlit's bootstrap in-process instead.
        from streamlit.web import bootstrap
        bootstrap.run(os.path.abspath(__file__), False, [], {})
        return
    raise SystemExit(subprocess.call(
        [sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__),
         "--server.headless=false", "--browser.gatherUsageStats=false"]))


# =============================================================== 1. CONSTANTS
TH = dict(bg="#0b1418", panel="#111f24", card="#152a30", accent="#00c9a7",
          amber="#ffb703", bad="#ef476f", good="#06d6a0", text="#e9f2f4",
          dim="#8fa6ab", grid="#1d353c")

ASSET_CLASSES = {
    "Equity MF / Direct Stocks":   dict(ret=12.0, vol=18.0, liq=3, tax="equity", lock=0),
    "Index Fund / ETF":            dict(ret=11.5, vol=17.0, liq=2, tax="equity", lock=0),
    "ELSS (Tax Saver)":            dict(ret=12.0, vol=18.0, liq=3, tax="equity", lock=36),
    "Debt MF / Liquid Fund":       dict(ret=7.0, vol=3.0, liq=2, tax="slab", lock=0),
    "Fixed Deposit / RD":          dict(ret=6.75, vol=0.5, liq=7, tax="slab", lock=0),
    "PPF":                         dict(ret=7.1, vol=0.0, liq=9999, tax="exempt", lock=180),
    "EPF / VPF":                   dict(ret=8.25, vol=0.0, liq=9999, tax="exempt", lock=240),
    "NPS":                         dict(ret=10.0, vol=12.0, liq=9999, tax="exempt", lock=360),
    "Sovereign Gold Bond / Gold":  dict(ret=8.5, vol=14.0, liq=7, tax="gold", lock=0),
    "Bonds / NCD":                 dict(ret=8.0, vol=5.0, liq=30, tax="slab", lock=0),
    "Real Estate (Investment)":    dict(ret=7.0, vol=12.0, liq=180, tax="property", lock=0),
    "Real Estate (Self-occupied)": dict(ret=6.0, vol=12.0, liq=210, tax="property", lock=0),
    "Vehicle (Personal Use)":      dict(ret=-12.0, vol=5.0, liq=45, tax="property", lock=0),
    "Jewellery / Personal Use":    dict(ret=6.0, vol=14.0, liq=30, tax="gold", lock=0),
    "ULIP / Traditional Policy":   dict(ret=5.0, vol=6.0, liq=60, tax="exempt", lock=60),
    "Crypto":                      dict(ret=18.0, vol=60.0, liq=1, tax="crypto", lock=0),
    "Cash / Savings A/c":          dict(ret=3.0, vol=0.0, liq=0, tax="slab", lock=0),
    "Business Equity / Unlisted":  dict(ret=18.0, vol=35.0, liq=365, tax="unlisted", lock=0),
    "Other":                       dict(ret=8.0, vol=10.0, liq=30, tax="slab", lock=0),
}

# Assets you live in, drive or wear. They belong in net worth — leaving the roof
# over your head and the car in the drive out of it understates you badly — but
# they fund nothing: never sold to plug a deficit or a goal, and they get no vote
# on the benchmark return that debt is judged against. A personal vehicle also
# depreciates, so its expected "return" is negative by default.
PERSONAL_CLASSES = {"Real Estate (Self-occupied)", "Vehicle (Personal Use)",
                    "Jewellery / Personal Use"}

# Selling one house to buy another rolls the gain over under Section 54, to the
# extent it is reinvested. Charging full capital-gains tax on an upgrade would
# invent a cost the law does not impose.
RESIDENTIAL_CLASSES = {"Real Estate (Self-occupied)", "Real Estate (Investment)"}

DEBT_TYPES = {
    "Home Loan (Self-occupied)":  dict(sec=True, shield="24b_self", rev=False, mkt=8.35),
    "Home Loan (Let-out)":        dict(sec=True, shield="24b_letout", rev=False, mkt=8.50),
    "Top-up Home Loan":           dict(sec=True, shield="none", rev=False, mkt=9.25),
    "Loan Against Property":      dict(sec=True, shield="none", rev=False, mkt=9.75),
    "Car / Vehicle Loan":         dict(sec=True, shield="none", rev=False, mkt=9.25),
    "Two-wheeler Loan":           dict(sec=True, shield="none", rev=False, mkt=11.0),
    "Personal Loan":              dict(sec=False, shield="none", rev=False, mkt=11.5),
    "Education Loan":             dict(sec=False, shield="80E", rev=False, mkt=9.5),
    "Gold Loan":                  dict(sec=True, shield="none", rev=False, mkt=9.5),
    "Loan Against Securities":    dict(sec=True, shield="none", rev=False, mkt=9.9),
    "Business / Working Capital": dict(sec=False, shield="business", rev=False, mkt=11.0),
    "Overdraft / Cash Credit":    dict(sec=True, shield="business", rev=True, mkt=10.5),
    "Credit Card Revolve":        dict(sec=False, shield="none", rev=True, mkt=36.0),
    "BNPL / Consumer Durable":    dict(sec=False, shield="none", rev=True, mkt=22.0),
    "Family / Informal Loan":     dict(sec=False, shield="none", rev=False, mkt=6.0),
}

EXP_CATS = ["Household - Groceries & Utilities", "Household - Help & Maintenance",
            "Rent", "Transport & Fuel", "Lifestyle - Dining & Entertainment",
            "Lifestyle - Shopping & Subscriptions", "Luxuries - Travel & Holidays",
            "Luxuries - Gadgets & Club", "Health & Medical", "Insurance Premiums",
            "Children - School & Tuition", "Dependents / Parents Support",
            "Professional / Business Overheads", "Other"]
GOAL_CATS = ["Education", "Marriage", "House Purchase", "Vehicle Purchase",
             "Business Capital", "Travel / Sabbatical", "Retirement Corpus",
             "Medical Buffer", "Other"]
PASSIVE_TYPES = ["Rental Income", "Dividends", "Interest (FD/Bonds)", "Annuity / Pension",
                 "Royalties", "Freelance / Consulting", "Digital / Content", "Other"]
FREQS = ["Monthly", "Quarterly", "Half-yearly", "Annual"]

BENCH_MODES = ["Marginal surplus vehicle", "Liquid portfolio blended", "Custom %"]

BAND_HI, BAND_LO = 1.5, -1.5
V_GOOD, V_NEUT, V_BAD = "HEALTHY LEVERAGE", "NEUTRAL", "LOSS-MAKING"


# =================================================================== 2. UTILS
def sf(v, d=0.0):
    try:
        f = float(v)
        return f if np.isfinite(f) else d
    except (TypeError, ValueError):
        return d


def si(v, d=0):
    return int(sf(v, d))


def sb(v, d=False):
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in ("true", "yes", "y", "1")
    try:
        return bool(int(v))
    except Exception:
        return d


def money(x, dp=0):
    x = sf(x, float("nan"))
    if not np.isfinite(x):
        return "-"
    sgn, x = ("-" if x < 0 else ""), abs(x)
    s = f"{x:,.{dp}f}"
    w, fr = (s.split(".") + [""])[:2]
    fr = ("." + fr) if fr else ""
    w = w.replace(",", "")
    if len(w) > 3:
        h, t = w[:-3], w[-3:]
        p = []
        while len(h) > 2:
            p.insert(0, h[-2:]); h = h[:-2]
        if h:
            p.insert(0, h)
        w = ",".join(p) + "," + t
    return f"{sgn}{CCY}{w}{fr}"


def compact(x):
    x = sf(x, float("nan"))
    if not np.isfinite(x):
        return "-"
    s, a = ("-" if x < 0 else ""), abs(x)
    if a >= 1e7:
        return f"{s}{CCY}{a/1e7:,.2f} Cr"
    if a >= 1e5:
        return f"{s}{CCY}{a/1e5:,.2f} L"
    if a >= 1e3:
        return f"{s}{CCY}{a/1e3:,.1f} K"
    return f"{s}{CCY}{a:,.0f}"


def mrate(annual_pct):
    """Effective monthly rate — investments compound at (1+i)^(1/12)-1."""
    return (1.0 + sf(annual_pct) / 100.0) ** (1.0 / 12.0) - 1.0


def lrate(annual_pct):
    """Lending convention — monthly rest = annual/12."""
    return sf(annual_pct) / 1200.0


def emi_of(P, apct, n):
    r, n = lrate(apct), max(si(n), 1)
    if r <= 0:
        return P / n
    f = (1 + r) ** n
    return P * r * f / (f - 1)


def tenure_of(P, apct, emi):
    r = lrate(apct)
    if emi <= 0:
        return None
    if r <= 0:
        return math.ceil(P / emi)
    if emi <= P * r + 1e-9:
        return None
    return math.ceil(-math.log(1 - P * r / emi) / math.log(1 + r))


def flat_to_reducing(P, flat_pct, n):
    tot = P * (flat_pct / 100.0) * (n / 12.0)
    emi = (P + tot) / n
    lo, hi = 1e-4, 200.0
    for _ in range(120):
        mid = (lo + hi) / 2
        if emi_of(P, mid, n) > emi:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2, emi


def liq_score(days):
    d = sf(days, 9999)
    return 5 if d <= 1 else 4 if d <= 7 else 3 if d <= 30 else 2 if d <= 180 else 1


def real_rate(nom, infl):
    """Fisher — not a naive subtraction."""
    return ((1 + nom / 100.0) / (1 + infl / 100.0) - 1) * 100.0


def cal_month(start_m, k):
    return ((si(start_m, 1) - 1 + k - 1) % 12) + 1


# Excel number format that groups the Indian way (12,00,00,000) instead of the
# Western 120,000,000. Reading "120,000,000" as twelve crore is exactly the kind
# of off-by-10x misread the app's own display convention avoids, so the workbooks
# must match the screen.
XL_INR = '[>=10000000]##\\,##\\,##\\,##0;[>=100000]##\\,##\\,##0;##,##0'

_XL_BAD = set('[]:*?/\\')


def xl_sheet(name, maxlen=31):
    """Excel forbids []:*?/\\ in sheet names, disallows leading/trailing
    apostrophes, and caps length at 31.

    Must be IDEMPOTENT. Truncating at 31 can land on a space, and a second
    pass would then strip it and return a different name — so the chart
    series in the report pointed at a sheet that did not exist ("Unknown
    worksheet reference"), silently breaking the amortisation charts for
    any loan with a long name."""
    s = "".join((" " if ch in _XL_BAD else ch) for ch in str(name))
    s = " ".join(s.split()).strip("'")
    return s[:maxlen].strip().strip("'") or "Sheet"


# ================================================= 3. INPUT SCHEMA (one truth)
def F(k, t, help, opts=None, **kw):
    return dict(k=k, t=t, help=help, opts=opts, **kw)


SCHEMA = {
    "debts": dict(
        label="Debts", icon="🏦",
        intro="One row per loan. Enter the CURRENT outstanding, not the original "
              "sanction. Leave EMI blank to derive it from remaining tenure, or leave "
              "tenure blank to derive it from EMI — the engine fills whichever is missing.",
        cols=[
            F("Loan / Lender", "text", "Your label for this loan, e.g. 'HDFC Home Loan'. "
                                       "Must be unique — it names the amortisation sheet."),
            F("Loan Type", "select", "Determines the tax shield, whether it is treated as "
                                     "revolving credit, and the market benchmark rate used "
                                     "for refinance suggestions.", list(DEBT_TYPES)),
            F("Secured?", "bool", "Tick if an asset is pledged. Secured debt is cheaper to "
                                  "refinance and is treated differently in consolidation advice."),
            F("Collateral / Security", "text", "What is pledged — 'Flat, Pune' / 'Car' / "
                                               "'MF units'. Free text, used in the report only."),
            F("Original Principal", "money", "Amount originally sanctioned. Used only for "
                                             "context; the engine runs off the outstanding."),
            F("Outstanding Principal", "money", "Principal still owed TODAY, from your latest "
                                                "statement. This drives everything."),
            F("Interest Rate % p.a.", "pct", "Current annual rate. For a floating loan use "
                                             "today's rate — stress tests shift it."),
            F("Fixed / Floating", "select", "Floating loans move with the rate-shift scenario; "
                                            "fixed loans do not.", ["Floating", "Fixed"]),
            F("Original Tenure (months)", "int", "Total months at sanction. Context only."),
            F("Remaining Tenure (months)", "int", "Months still to run. Leave 0 if you would "
                                                  "rather the engine derive it from your EMI."),
            F("EMI", "money", "Current monthly instalment. Leave 0 to have it derived from "
                              "the remaining tenure."),
            F("Flat / Add-on Rate?", "bool", "Tick ONLY if the rate quoted is flat/add-on "
                                             "(common on car, gold and some personal loans). "
                                             "The engine converts it to the true reducing-"
                                             "balance APR, which is roughly 1.8x the flat rate."),
            F("Prepayment Penalty %", "pct", "Charge on prepaid principal. Floating-rate home "
                                             "loans to individuals are typically nil; fixed-rate "
                                             "and personal loans often 2-5%."),
            F("Min Due % (revolving)", "pct", "Cards / overdrafts only: the minimum payment as "
                                              "a % of outstanding. Typically 5%. Ignored for "
                                              "term loans."),
            F("Linked Investment (collateral)", "text", "If this loan is secured against a "
                                                        "holding in your Investments sheet, name "
                                                        "it so the engine never sells that asset "
                                                        "while the loan is live."),
        ]),
    "investments": dict(
        label="Investments", icon="📈",
        intro="One row per holding. 'Invested Cost' drives the capital-gains calculation "
              "when the engine models a redemption — get it as close as you can.",
        cols=[
            F("Investment Name", "text", "Your label, e.g. 'Parag Parikh Flexi Cap'. Must be "
                                         "unique — goals and loans reference it by name."),
            F("Asset Class", "select", "Sets the tax treatment, and seeds the return, "
                                       "volatility and liquidity if you leave them blank.",
              list(ASSET_CLASSES)),
            F("Current Value", "money", "Today's market value of the holding."),
            F("Invested Cost", "money", "Total amount you put in (acquisition cost). The "
                                        "difference from current value is the embedded gain "
                                        "that gets taxed on exit."),
            F("Expected Return % p.a.", "pct", "YOUR nominal pre-tax expectation. This is an "
                                               "assumption, not a forecast — the engine will "
                                               "not question it, so be conservative."),
            F("Volatility % p.a.", "pct", "Annual standard deviation. Drives the risk haircut: "
                                          "risk-adjusted return = post-tax return − "
                                          "(risk-aversion x volatility). Equity ~18, debt ~3, "
                                          "FD ~0."),
            F("Days to Cash", "int", "Realistic days from decision to money in your account. "
                                     "Equity MF 3, FD 7, property 180. Use 9999 for locked."),
            F("Lock-in Remaining (months)", "int", "Months until you can legally redeem. ELSS, "
                                                   "PPF, NPS, tax-saver FDs. The optimiser "
                                                   "treats this as a hard constraint."),
            F("Exit Load %", "pct", "Charge on early redemption. Most equity funds 1% within "
                                    "a year; FDs often 0.5-1% penalty on premature closure."),
            F("Monthly SIP", "money", "Ongoing monthly contribution. Set 0 for lump-sum "
                                      "holdings with no recurring investment."),
            F("SIP Step-up % p.a.", "pct", "Annual increase in the SIP amount. 10% is a common "
                                           "target if your income rises at a similar rate."),
            F("Earmarked for Goal", "text", "If this holding is reserved for a specific goal, "
                                            "type the exact goal name. Earmarked assets are "
                                            "ring-fenced from debt prepayment."),
            F("Never Liquidate", "bool", "Hard constraint — the optimiser will never propose "
                                         "selling this, regardless of the arithmetic."),
        ]),
    "expenses": dict(
        label="Recurring Expenses", icon="🧾",
        intro="Monthly run-rate by category. EMIs are EXCLUDED here — the debt engine "
              "handles those, so including them would double-count.",
        cols=[
            F("Category", "select", "Pick the closest category. Grouping matters only for "
                                    "reporting and for applying different inflation rates.",
              EXP_CATS),
            F("Monthly Amount", "money", "Typical monthly spend today. Use a 3-month average "
                                         "rather than last month's figure."),
            F("Category Inflation %", "pct", "Annual escalation for THIS category. Medical and "
                                             "education typically run well above headline "
                                             "inflation; fuel and utilities near it."),
            F("Step-up Basis", "select", "'Inflation' uses the category rate above. 'Custom %' "
                                         "uses the next column instead — for planned lifestyle "
                                         "changes rather than price rises.", ["Inflation", "Custom %"]),
            F("Custom Step-up % p.a.", "pct", "Only used when Step-up Basis is 'Custom %'. Can "
                                              "be negative if you intend to cut this spend."),
        ]),
    "lumpy": dict(
        label="Annual & Lumpy Expenses", icon="📅",
        intro="Once-a-year outflows that create cashflow spikes — premiums, school fees, "
              "festivals, holidays. Keeping them separate is what makes the monthly "
              "cashflow realistic instead of a smooth average.",
        cols=[
            F("Item", "text", "What it is, e.g. 'Term + health insurance premium'."),
            F("Annual Amount", "money", "Total paid once per year."),
            F("Month of Year", "int", "Calendar month it falls due, 1 = January."),
            F("Inflation % p.a.", "pct", "Annual escalation for this specific item."),
        ]),
    "passive": dict(
        label="Passive Income", icon="💧",
        intro="Income not from your primary salary or business. Rental income "
              "automatically gets the 30% standard deduction before tax.",
        cols=[
            F("Source", "text", "Your label, e.g. 'Rental - Andheri flat'."),
            F("Type", "select", "Rental gets the 30% standard deduction. Other types are "
                                "taxed at your marginal rate if marked Gross.", PASSIVE_TYPES),
            F("Amount", "money", "Amount received per occurrence — see Frequency."),
            F("Frequency", "select", "How often it lands. Quarterly and annual receipts are "
                                     "placed in the correct month, not smoothed.", FREQS),
            F("Growth % p.a.", "pct", "Annual escalation. Rents typically 4-6%; dividends vary."),
            F("Taxable?", "bool", "Untick for genuinely tax-free receipts."),
            F("Entered As", "select", "'Gross' means the engine deducts tax. 'Net' means you "
                                      "have already deducted it and the figure passes through "
                                      "untouched.", ["Gross", "Net"]),
            F("Start Month", "int", "Simulation month it begins. 1 = now."),
            F("End Month", "int", "Simulation month it stops. 0 = runs for the whole horizon. "
                                  "Use this for a lease that expires or a pension that starts "
                                  "and later ends."),
        ]),
    "goals": dict(
        label="Goals", icon="🎯",
        intro="Costs in TODAY's money — the engine inflates each at its own rate. If "
              "'% From Own Corpus' is below 100, the balance is financed: give the rate "
              "and tenure and the engine creates that future loan, checks the EMI fits "
              "your income ceiling, and services it. For a REPLACEMENT purchase, name "
              "the asset you are selling and the class the new one becomes: the old "
              "asset is sold, the loan secured on it is settled from the proceeds, the "
              "freed EMI restores your borrowing capacity, and what you buy lands on "
              "your balance sheet.",
        cols=[
            F("Goal Name", "text", "Your label, e.g. 'Daughter UG education'. Investments "
                                   "reference this exact name when earmarked."),
            F("Category", "select", "Used for reporting and to decide the type of loan created "
                                    "if the goal is partly financed.", GOAL_CATS),
            F("Target Year (from now)", "int", "Years from today. 5 means 60 months away."),
            F("Cost in Today's Money", "money", "What it would cost if you paid for it TODAY. "
                                                "Do not pre-inflate it — that is the engine's job."),
            F("Goal Inflation % p.a.", "pct", "Escalation for THIS goal. Education and medical "
                                              "typically 8-11%, property 5-7%, general 6%. This "
                                              "single number often matters more than your "
                                              "return assumption."),
            F("Priority (1=highest)", "int", "1 to 5. When surplus is short, higher priority "
                                             "goals are funded first."),
            F("% From Own Corpus", "pct", "100 = fully self-funded. 20 on a house means a 20% "
                                          "down payment and an 80% loan."),
            F("If Loan: Rate %", "pct", "Rate on the financed portion. Ignored if own corpus "
                                        "is 100%."),
            F("If Loan: Tenure (yrs)", "int", "Tenure of the financed portion. Ignored if own "
                                              "corpus is 100%."),
            F("Earmarked Investment", "text", "Exact name of a holding reserved for this goal. "
                                              "It will be used for this goal and protected from "
                                              "everything else."),
            F("Sell to Fund (asset name)", "text",
              "For a REPLACEMENT purchase: the exact name of the holding you dispose of "
              "to pay for this one — the flat you move out of, the car you trade in. It "
              "is sold in full at the goal date, any loan secured against it is settled "
              "out of the proceeds, and the EMI that frees up restores your borrowing "
              "capacity for the new loan. Leave blank if nothing is being sold."),
            F("Becomes Asset (class)", "select",
              "If this goal BUYS something that you still own afterwards — a house, a "
              "car — pick its asset class and the purchase is capitalised onto your "
              "balance sheet at what you actually paid. Leave blank for consumption "
              "goals such as education, a wedding or a holiday, where the money is "
              "simply spent.", [""] + list(ASSET_CLASSES)),
        ]),
}

# Columns the asset-class defaults are allowed to seed. Blanks in these must
# survive the import as blanks; coercing them to zero silently turned an
# unfilled row into a 0% return / instantly liquid holding.
_SEEDABLE = {"investments": {"Expected Return % p.a.", "Volatility % p.a.",
                             "Days to Cash", "Lock-in Remaining (months)"}}

ASSUMPTION_FIELDS = [
    ("profile_name", "Profile name", "text", "Label for this plan; appears on the report cover."),
    ("horizon_years", "Projection horizon (years)", "int",
     "How far to project. 10 is the brief; the engine supports 3-30."),
    ("start_month", "Start calendar month (1-12)", "int",
     "The real month the plan starts. Aligns bonuses and annual expenses correctly."),
    ("inflation", "Headline inflation % p.a.", "pct",
     "General price inflation. Used where a category-specific rate is not given, and to "
     "compute real (inflation-adjusted) returns."),
    ("risk_aversion", "Risk-aversion coefficient", "num",
     "The haircut applied per unit of volatility. Risk-adjusted return = post-tax return − "
     "(coefficient x volatility). At 0.25, an 18%-volatility equity fund loses 4.5 points. "
     "Set 0 to compare on raw post-tax returns — but then a 12% equity assumption competes "
     "with a guaranteed 9% loan saving on unequal terms."),
    ("horizon_risk", "Scale risk haircut by the decision horizon", "bool",
     "ON (recommended). Volatility is quoted per year, but prepaying-or-investing is "
     "a decision that runs for the life of the loan, and the spread of the annualised "
     "outcome narrows with the square root of time. With this ON, a 16-year home loan "
     "is judged against equity's 16-year risk rather than a single year's. OFF charges "
     "a full year of volatility against every decision, which makes almost any loan — "
     "including a cheap secured one — look loss-making."),
    ("benchmark_mode", "Benchmark loans against", "text",
     "'Marginal surplus vehicle' (recommended) uses the risk-adjusted return of the "
     "holding your spare cash actually flows into. That is the true alternative to "
     "prepaying: if you do not repay the loan, this is where the rupee goes. "
     "'Liquid portfolio blended' instead averages every deployable holding by value — "
     "which drags the benchmark down with money you park for liquidity rather than "
     "return, and can make sound leverage look loss-making. Locked money never votes "
     "under either mode, because it cannot repay a loan."),
    ("benchmark_custom", "Custom benchmark % p.a.", "pct",
     "Used when benchmark mode is 'Custom %', or as a fallback when no deployable assets exist."),
    ("default_vehicle", "Residual surplus goes to", "text",
     "Exact name of the holding that receives leftover cash each month after every other "
     "priority is met."),
    ("goal_vehicle_return", "Goal sinking-fund return % p.a.", "pct",
     "Return on money set aside for goals. Keep this conservative — goal money is usually "
     "parked in lower-risk instruments as the date approaches."),
    ("ef_current", "Emergency fund today", "money", "Cash and near-cash held as a buffer."),
    ("ef_target_months", "EF target (months of expense)", "num",
     "Months of expenses to hold. 6 is standard for salaried, 9-12 for business income."),
    ("ef_return", "EF parking return % p.a.", "pct", "Return on the emergency fund."),
    ("ef_include_emi", "EF target includes EMIs", "bool",
     "Tick if the buffer should cover EMIs too, not just living costs. Recommended when "
     "you carry significant debt."),
    ("ef_max_share", "Max % of surplus to EF top-up", "pct",
     "Caps how aggressively the buffer is rebuilt, so it does not starve everything else."),
    ("liquid_deploy_cap", "Max % of liquid portfolio deployable to debt", "pct",
     "Ceiling on how much of your liquid portfolio the optimiser may propose selling."),
    ("deployable_max_days", "Max days-to-cash to count as deployable", "int",
     "Holdings slower than this are excluded from the benchmark and from swap proposals."),
    ("prepay_share_of_surplus", "Max % of monthly surplus to prepayment", "pct",
     "Caps monthly prepayment so some surplus still reaches investments."),
    ("prepay_mode", "Prepayment reduces", "text",
     "'tenure' keeps the EMI and shortens the loan (saves the most interest). 'emi' keeps "
     "the tenure and cuts the instalment (maximises monthly cashflow relief)."),
    ("emi_income_ceiling", "EMI-to-income ceiling %", "pct",
     "Comfort limit. Above 40% a single income shock forces asset sales at the worst time."),
    ("bt_threshold", "Flag refinance if rate exceeds market by (%)", "pct",
     "Sensitivity of the balance-transfer recommendation."),
    ("illiquid_warn_pct", "Warn if illiquid share exceeds %", "pct",
     "Portfolio concentration warning threshold."),
    ("allow_prepay_healthy", "Allow prepaying healthy-leverage loans", "bool",
     "Normally off — prepaying positive-carry debt destroys value. Turn on only if you "
     "value being debt-free above the arithmetic."),
]

AHELP = {k: h for k, _l, _t, h in ASSUMPTION_FIELDS}

TAX_FIELDS = [
    ("regime", "Tax regime (New / Old)", "text",
     "Regime-aware and material: Section 24b on a SELF-OCCUPIED home and Section 80E are "
     "recognised only under the old regime. Let-out property interest and business "
     "interest are recognised under both. Switching this can flip a loan's verdict."),
    ("marginal_rate", "Marginal tax rate %", "pct",
     "Your top slab rate, including surcharge if applicable."),
    ("cess", "Cess %", "pct", "Health and education cess applied on tax."),
    ("equity_ltcg", "Equity LTCG %", "pct", "Long-term capital gains rate on listed equity."),
    ("equity_ltcg_exempt", "Equity LTCG annual exemption", "money",
     "Annual exemption on long-term equity gains, applied per financial year and tracked "
     "across all redemptions the engine models."),
    ("equity_stcg", "Equity STCG %", "pct", "Short-term rate on listed equity."),
    ("other_ltcg", "Other-asset LTCG %", "pct", "Gold, property, unlisted shares."),
    ("crypto_rate", "Crypto / VDA rate %", "pct", "Flat rate on virtual digital assets."),
    ("apply_cg_on_redemption", "Apply capital-gains tax on redemptions", "bool",
     "Untick only to see the pre-tax picture. Leaving it on is what makes 'sell equity to "
     "kill a loan' an honest comparison."),
    ("sec54_rollover", "Roll gains over on a home-to-home upgrade (Sec 54)", "bool",
     "When a goal sells one residential property to buy another, the capital gain is "
     "exempt to the extent it is reinvested. Leave ON unless you want to see the "
     "gross-of-relief position."),
    ("apply_debt_shields", "Apply debt tax shields", "bool",
     "Applies 24b / 80E / business-interest deductibility to lower the effective cost of debt."),
    ("sec24b_cap", "Section 24b cap (self-occupied)", "money",
     "Cap on deductible interest for a self-occupied property. Let-out property has no cap."),
]

THELP = {k: h for k, _l, _t, h in TAX_FIELDS}

INCOME_FIELDS = [
    ("enabled", "Include this earner", "bool", "Untick to exclude entirely."),
    ("monthly_inhand", "Monthly in-hand (post-tax)", "money",
     "Take-home pay AFTER tax and deductions — the amount that actually reaches your bank."),
    ("annual_bonus", "Annual bonus (post-tax)", "money", "Post-tax bonus, paid once a year."),
    ("bonus_month", "Bonus calendar month (1-12)", "int", "1 = January."),
    ("increment_pct", "Annual increment %", "pct", "Expected annual raise."),
    ("increment_month", "Increment calendar month (1-12)", "int", "When the raise takes effect."),
    ("business_monthly", "Business income / month (post-tax)", "money",
     "Average monthly business drawings after tax. Leave 0 if salaried."),
    ("business_growth_pct", "Business growth % p.a.", "pct", "Can be negative."),
    ("stop_month", "Income stops after month # (0 = never)", "int",
     "For a planned retirement, sabbatical or contract end within the horizon."),
]


IHELP = {k: h for k, _l, _t, h in INCOME_FIELDS}


# ================================================================= 4. DEMO DATA
def demo():
    debts = pd.DataFrame([
        {"Loan / Lender": "HDFC Home Loan", "Loan Type": "Home Loan (Self-occupied)",
         "Secured?": True, "Collateral / Security": "Flat - Pune",
         "Original Principal": 5000000.0, "Outstanding Principal": 4200000.0,
         "Interest Rate % p.a.": 8.6, "Fixed / Floating": "Floating",
         "Original Tenure (months)": 240, "Remaining Tenure (months)": 198,
         "EMI": 43700.0, "Flat / Add-on Rate?": False, "Prepayment Penalty %": 0.0,
         "Min Due % (revolving)": 0.0,
         "Linked Investment (collateral)": "Flat - Pune (self-occupied)"},
        {"Loan / Lender": "ICICI Car Loan", "Loan Type": "Car / Vehicle Loan",
         "Secured?": True, "Collateral / Security": "Car", "Original Principal": 900000.0,
         "Outstanding Principal": 520000.0, "Interest Rate % p.a.": 9.4,
         "Fixed / Floating": "Fixed", "Original Tenure (months)": 60,
         "Remaining Tenure (months)": 34, "EMI": 18900.0, "Flat / Add-on Rate?": False,
         "Prepayment Penalty %": 3.0, "Min Due % (revolving)": 0.0,
         "Linked Investment (collateral)": "Car"},
        {"Loan / Lender": "Bajaj Personal Loan", "Loan Type": "Personal Loan",
         "Secured?": False, "Collateral / Security": "-", "Original Principal": 800000.0,
         "Outstanding Principal": 610000.0, "Interest Rate % p.a.": 15.5,
         "Fixed / Floating": "Fixed", "Original Tenure (months)": 48,
         "Remaining Tenure (months)": 39, "EMI": 20100.0, "Flat / Add-on Rate?": False,
         "Prepayment Penalty %": 4.0, "Min Due % (revolving)": 0.0,
         "Linked Investment (collateral)": ""},
        {"Loan / Lender": "Amex Card Revolve", "Loan Type": "Credit Card Revolve",
         "Secured?": False, "Collateral / Security": "-", "Original Principal": 180000.0,
         "Outstanding Principal": 180000.0, "Interest Rate % p.a.": 40.8,
         "Fixed / Floating": "Fixed", "Original Tenure (months)": 0,
         "Remaining Tenure (months)": 0, "EMI": 0.0, "Flat / Add-on Rate?": False,
         "Prepayment Penalty %": 0.0, "Min Due % (revolving)": 5.0,
         "Linked Investment (collateral)": ""},
    ])
    inv = pd.DataFrame([
        {"Investment Name": "Equity MF Core", "Asset Class": "Equity MF / Direct Stocks",
         "Current Value": 1850000.0, "Invested Cost": 1250000.0,
         "Expected Return % p.a.": 12.0, "Volatility % p.a.": 18.0, "Days to Cash": 3,
         "Lock-in Remaining (months)": 0, "Exit Load %": 0.0, "Monthly SIP": 35000.0,
         "SIP Step-up % p.a.": 10.0, "Earmarked for Goal": "", "Never Liquidate": False},
        {"Investment Name": "Nifty Index Fund", "Asset Class": "Index Fund / ETF",
         "Current Value": 620000.0, "Invested Cost": 500000.0,
         "Expected Return % p.a.": 11.5, "Volatility % p.a.": 17.0, "Days to Cash": 2,
         "Lock-in Remaining (months)": 0, "Exit Load %": 0.0, "Monthly SIP": 15000.0,
         "SIP Step-up % p.a.": 10.0, "Earmarked for Goal": "", "Never Liquidate": False},
        {"Investment Name": "Debt Fund Parking", "Asset Class": "Debt MF / Liquid Fund",
         "Current Value": 700000.0, "Invested Cost": 660000.0,
         "Expected Return % p.a.": 7.0, "Volatility % p.a.": 3.0, "Days to Cash": 2,
         "Lock-in Remaining (months)": 0, "Exit Load %": 0.0, "Monthly SIP": 0.0,
         "SIP Step-up % p.a.": 0.0, "Earmarked for Goal": "", "Never Liquidate": False},
        {"Investment Name": "Bank FD 3yr", "Asset Class": "Fixed Deposit / RD",
         "Current Value": 900000.0, "Invested Cost": 850000.0,
         "Expected Return % p.a.": 6.75, "Volatility % p.a.": 0.5, "Days to Cash": 7,
         "Lock-in Remaining (months)": 0, "Exit Load %": 1.0, "Monthly SIP": 0.0,
         "SIP Step-up % p.a.": 0.0, "Earmarked for Goal": "Sibling Marriage Support",
         "Never Liquidate": False},
        {"Investment Name": "PPF", "Asset Class": "PPF", "Current Value": 780000.0,
         "Invested Cost": 780000.0, "Expected Return % p.a.": 7.1, "Volatility % p.a.": 0.0,
         "Days to Cash": 9999, "Lock-in Remaining (months)": 84, "Exit Load %": 0.0,
         "Monthly SIP": 12500.0, "SIP Step-up % p.a.": 0.0, "Earmarked for Goal": "",
         "Never Liquidate": True},
        {"Investment Name": "EPF", "Asset Class": "EPF / VPF", "Current Value": 1450000.0,
         "Invested Cost": 1450000.0, "Expected Return % p.a.": 8.25, "Volatility % p.a.": 0.0,
         "Days to Cash": 9999, "Lock-in Remaining (months)": 240, "Exit Load %": 0.0,
         "Monthly SIP": 21000.0, "SIP Step-up % p.a.": 8.0, "Earmarked for Goal": "",
         "Never Liquidate": True},
        {"Investment Name": "SGB Tranche", "Asset Class": "Sovereign Gold Bond / Gold",
         "Current Value": 420000.0, "Invested Cost": 300000.0, "Expected Return % p.a.": 8.5,
         "Volatility % p.a.": 14.0, "Days to Cash": 7, "Lock-in Remaining (months)": 0,
         "Exit Load %": 0.0, "Monthly SIP": 0.0, "SIP Step-up % p.a.": 0.0,
         "Earmarked for Goal": "", "Never Liquidate": False},
        {"Investment Name": "Flat - Pune (self-occupied)",
         "Asset Class": "Real Estate (Self-occupied)", "Current Value": 8500000.0,
         "Invested Cost": 5000000.0, "Expected Return % p.a.": 6.0,
         "Volatility % p.a.": 12.0, "Days to Cash": 210,
         "Lock-in Remaining (months)": 0, "Exit Load %": 0.0, "Monthly SIP": 0.0,
         "SIP Step-up % p.a.": 0.0, "Earmarked for Goal": "", "Never Liquidate": True},
        {"Investment Name": "Car", "Asset Class": "Vehicle (Personal Use)",
         "Current Value": 700000.0, "Invested Cost": 900000.0,
         "Expected Return % p.a.": -12.0, "Volatility % p.a.": 5.0, "Days to Cash": 45,
         "Lock-in Remaining (months)": 0, "Exit Load %": 0.0, "Monthly SIP": 0.0,
         "SIP Step-up % p.a.": 0.0, "Earmarked for Goal": "", "Never Liquidate": True},
        {"Investment Name": "Rental Flat", "Asset Class": "Real Estate (Investment)",
         "Current Value": 6500000.0, "Invested Cost": 5200000.0,
         "Expected Return % p.a.": 5.0, "Volatility % p.a.": 12.0, "Days to Cash": 180,
         "Lock-in Remaining (months)": 0, "Exit Load %": 2.0, "Monthly SIP": 0.0,
         "SIP Step-up % p.a.": 0.0, "Earmarked for Goal": "", "Never Liquidate": False},
    ])
    exp = pd.DataFrame([
        {"Category": c, "Monthly Amount": v, "Category Inflation %": i,
         "Step-up Basis": "Inflation", "Custom Step-up % p.a.": 0.0}
        for c, v, i in [
            ("Household - Groceries & Utilities", 38000.0, 6.0),
            ("Household - Help & Maintenance", 12000.0, 7.0),
            ("Transport & Fuel", 11000.0, 6.0),
            ("Lifestyle - Dining & Entertainment", 16000.0, 7.0),
            ("Lifestyle - Shopping & Subscriptions", 12000.0, 6.0),
            ("Luxuries - Travel & Holidays", 10000.0, 8.0),
            ("Health & Medical", 6000.0, 10.0),
            ("Children - School & Tuition", 25000.0, 10.0),
            ("Dependents / Parents Support", 15000.0, 6.0)]])
    lumpy = pd.DataFrame([
        {"Item": "Term + health insurance premium", "Annual Amount": 78000.0,
         "Month of Year": 6, "Inflation % p.a.": 8.0},
        {"Item": "School annual fees & books", "Annual Amount": 120000.0,
         "Month of Year": 4, "Inflation % p.a.": 10.0},
        {"Item": "Festivals & gifting", "Annual Amount": 90000.0,
         "Month of Year": 10, "Inflation % p.a.": 6.0},
        {"Item": "Annual vacation", "Annual Amount": 200000.0,
         "Month of Year": 12, "Inflation % p.a.": 8.0}])
    passive = pd.DataFrame([
        {"Source": "Rental - Flat", "Type": "Rental Income", "Amount": 28000.0,
         "Frequency": "Monthly", "Growth % p.a.": 5.0, "Taxable?": True,
         "Entered As": "Gross", "Start Month": 1, "End Month": 0},
        {"Source": "Dividends", "Type": "Dividends", "Amount": 40000.0,
         "Frequency": "Annual", "Growth % p.a.": 8.0, "Taxable?": True,
         "Entered As": "Gross", "Start Month": 1, "End Month": 0},
        {"Source": "Consulting retainer", "Type": "Freelance / Consulting",
         "Amount": 35000.0, "Frequency": "Monthly", "Growth % p.a.": 6.0,
         "Taxable?": True, "Entered As": "Net", "Start Month": 1, "End Month": 0}])
    goals = pd.DataFrame([
        {"Goal Name": "Child UG Education", "Category": "Education",
         "Target Year (from now)": 5, "Cost in Today's Money": 2500000.0,
         "Goal Inflation % p.a.": 10.0, "Priority (1=highest)": 1,
         "% From Own Corpus": 70.0, "If Loan: Rate %": 9.5, "If Loan: Tenure (yrs)": 8,
         "Earmarked Investment": "", "Sell to Fund (asset name)": "",
         "Becomes Asset (class)": ""},
        {"Goal Name": "House Upgrade", "Category": "House Purchase",
         "Target Year (from now)": 7, "Cost in Today's Money": 12000000.0,
         "Goal Inflation % p.a.": 7.0, "Priority (1=highest)": 2,
         "% From Own Corpus": 30.0, "If Loan: Rate %": 8.6, "If Loan: Tenure (yrs)": 20,
         "Earmarked Investment": "",
         "Sell to Fund (asset name)": "Flat - Pune (self-occupied)",
         "Becomes Asset (class)": "Real Estate (Self-occupied)"},
        {"Goal Name": "Sibling Marriage Support", "Category": "Marriage",
         "Target Year (from now)": 3, "Cost in Today's Money": 1500000.0,
         "Goal Inflation % p.a.": 8.0, "Priority (1=highest)": 2,
         "% From Own Corpus": 100.0, "If Loan: Rate %": 0.0, "If Loan: Tenure (yrs)": 0,
         "Earmarked Investment": "Bank FD 3yr", "Sell to Fund (asset name)": "",
         "Becomes Asset (class)": ""},
        {"Goal Name": "Car Replacement", "Category": "Vehicle Purchase",
         "Target Year (from now)": 4, "Cost in Today's Money": 1800000.0,
         "Goal Inflation % p.a.": 6.0, "Priority (1=highest)": 4,
         "% From Own Corpus": 60.0, "If Loan: Rate %": 9.25, "If Loan: Tenure (yrs)": 5,
         "Earmarked Investment": "", "Sell to Fund (asset name)": "Car",
         "Becomes Asset (class)": "Vehicle (Personal Use)"}])
    income = dict(
        primary=dict(enabled=True, monthly_inhand=285000.0, annual_bonus=600000.0,
                     bonus_month=4, increment_pct=8.0, increment_month=4,
                     business_monthly=0.0, business_growth_pct=0.0, stop_month=0),
        secondary=dict(enabled=True, monthly_inhand=120000.0, annual_bonus=150000.0,
                       bonus_month=6, increment_pct=7.0, increment_month=6,
                       business_monthly=0.0, business_growth_pct=0.0, stop_month=0))
    assumptions = dict(
        profile_name="Demo Profile", horizon_years=10, start_month=date.today().month,
        inflation=6.0, risk_aversion=0.25, horizon_risk=True,
        benchmark_mode="Marginal surplus vehicle",
        benchmark_custom=10.0, default_vehicle="Equity MF Core", goal_vehicle_return=8.0,
        ef_current=450000.0, ef_target_months=6.0, ef_return=6.0, ef_include_emi=True,
        ef_max_share=40.0, liquid_deploy_cap=50.0, deployable_max_days=30,
        prepay_share_of_surplus=100.0, prepay_mode="tenure", emi_income_ceiling=40.0,
        bt_threshold=0.75, illiquid_warn_pct=60.0, allow_prepay_healthy=False)
    tax = dict(regime="New", marginal_rate=30.0, cess=4.0, equity_ltcg=12.5,
               equity_ltcg_exempt=125000.0, equity_stcg=20.0, other_ltcg=12.5,
               crypto_rate=30.0, apply_cg_on_redemption=True, sec54_rollover=True,
               apply_debt_shields=True, sec24b_cap=200000.0)
    return dict(assumptions=assumptions, tax=tax, income=income, passive=passive,
                expenses=exp, lumpy=lumpy, debts=debts, investments=inv, goals=goals)


def blank():
    P = demo()
    P["assumptions"]["profile_name"] = "My Plan"
    P["assumptions"]["ef_current"] = 0.0
    for k in ("passive", "expenses", "lumpy", "debts", "investments", "goals"):
        P[k] = P[k].iloc[0:0].copy()
    P["income"]["primary"].update(monthly_inhand=0.0, annual_bonus=0.0)
    P["income"]["secondary"].update(enabled=False, monthly_inhand=0.0, annual_bonus=0.0)
    return P


# =================================================================== 5. TAX
@dataclass
class TaxConfig:
    regime: str = "New"
    marginal_rate: float = 30.0
    cess: float = 4.0
    equity_ltcg: float = 12.5
    equity_ltcg_exempt: float = 125000.0
    equity_stcg: float = 20.0
    other_ltcg: float = 12.5
    crypto_rate: float = 30.0
    apply_cg_on_redemption: bool = True
    sec54_rollover: bool = True
    apply_debt_shields: bool = True
    sec24b_cap: float = 200000.0

    @classmethod
    def from_dict(cls, d):
        """Build from a profile dict, ignoring unknown keys and coercing types.
        An edited JSON or a stale template must not be able to crash the run."""
        base, out = cls(), {}
        for f_ in fields(cls):
            if not d or f_.name not in d:
                continue
            dv, v = getattr(base, f_.name), d[f_.name]
            out[f_.name] = sb(v, dv) if isinstance(dv, bool) else \
                sf(v, dv) if isinstance(dv, (int, float)) else str(v)
        return cls(**out)

    @property
    def mtr(self):
        return (self.marginal_rate / 100.0) * (1 + self.cess / 100.0)

    def gains_rate(self, kind):
        if not self.apply_cg_on_redemption:
            return 0.0
        c = 1 + self.cess / 100.0
        return {"equity": self.equity_ltcg / 100 * c, "slab": self.mtr, "exempt": 0.0,
                "gold": self.other_ltcg / 100 * c, "property": self.other_ltcg / 100 * c,
                "unlisted": self.other_ltcg / 100 * c,
                "crypto": self.crypto_rate / 100 * c}.get(kind, self.mtr)

    def drag(self, kind):
        if kind == "exempt":
            return 0.0
        if kind == "slab":
            return self.mtr
        return self.gains_rate(kind)

    def shield_frac(self, shield):
        if not self.apply_debt_shields:
            return 0.0
        old = str(self.regime).lower().startswith("old")
        if shield == "24b_self":
            return self.mtr if old else 0.0
        if shield == "24b_letout":
            return self.mtr
        if shield == "80E":
            return self.mtr if old else 0.0
        if shield == "business":
            return self.mtr
        return 0.0

    def eff_cost(self, rate, outstanding, shield):
        r = sf(rate)
        f = self.shield_frac(shield)
        if f <= 0 or outstanding <= 0:
            return r
        annual_int = outstanding * r / 100.0
        # The Section 24(b) ceiling applies to a SELF-OCCUPIED property only.
        # Interest on a let-out property is deductible in full, as is 80E
        # and business interest.
        ded = min(annual_int, self.sec24b_cap) if shield == "24b_self" else annual_int
        return r - (ded * f / outstanding * 100.0)


class TaxLedger:
    """Tracks the annual equity LTCG exemption across all modelled redemptions."""

    def __init__(self, tax: TaxConfig):
        self.tax = tax
        self.fy = -1
        self.left = tax.equity_ltcg_exempt
        self.paid = 0.0

    def roll(self, m):
        fy = (m - 1) // 12
        if fy != self.fy:
            self.fy = fy
            self.left = self.tax.equity_ltcg_exempt

    def tax_on_gain(self, gain, kind):
        if gain <= 0:
            return 0.0
        r = self.tax.gains_rate(kind)
        if kind == "equity" and self.left > 0:
            shielded = min(gain, self.left)
            self.left -= shielded
            gain -= shielded
        t = gain * r
        self.paid += t
        return t

    def peek_tax(self, gain, kind):
        """Non-mutating estimate, for the bisection solve."""
        if gain <= 0:
            return 0.0
        r = self.tax.gains_rate(kind)
        if kind == "equity":
            gain = max(0.0, gain - self.left)
        return gain * r


# ========================================================== 6. ENGINE OBJECTS
@dataclass
class Loan:
    name: str
    ltype: str
    secured: bool
    collateral: str
    balance: float
    rate: float
    emi: float
    penalty: float
    shield: str
    revolving: bool
    min_due: float
    fixed: bool
    linked: str = ""
    start_m: int = 1
    active: bool = True
    closed_m: int | None = None
    opening: float = 0.0
    int_paid: float = 0.0
    prin_paid: float = 0.0
    prepaid: float = 0.0
    eff_cost: float = 0.0
    verdict: str = V_NEUT
    led: list = field(default_factory=list)

    def r_now(self, bps):
        return self.rate + (0.0 if self.fixed else bps / 100.0)

    def service(self, m, bps):
        if not self.active or self.balance <= 0.5 or m < self.start_m:
            return 0.0, 0.0, 0.0
        r = lrate(self.r_now(bps))
        i = self.balance * r
        if self.revolving:
            md = max(self.min_due, 1.0)
            pay = min(max(self.balance * md / 100.0 + i, 100.0), self.balance + i)
        else:
            pay = min(self.emi, self.balance + i)
        p = max(pay - i, 0.0)
        if p <= 0:
            pay = i
        p = min(p, self.balance)
        op = self.balance
        self.balance -= p
        self.int_paid += i
        self.prin_paid += p
        self.led.append(dict(Month=m, Opening=op, EMI=pay, Interest=i, Principal=p,
                             Prepayment=0.0, Closing=self.balance))
        if self.balance <= 0.5:
            self.balance = 0.0
            self.active = False
            self.closed_m = m
        return i, p, pay

    def prepay(self, cash, m, mode="tenure", bps=0.0):
        if not self.active or cash <= 0 or self.balance <= 0:
            return 0.0
        pen = self.penalty / 100.0
        applied = min(cash / (1 + pen), self.balance)
        used = applied * (1 + pen)
        pre_bal = self.balance
        self.balance -= applied
        self.prepaid += applied
        if self.led and self.led[-1]["Month"] == m:
            self.led[-1]["Prepayment"] += applied
            self.led[-1]["Closing"] = self.balance
        else:
            self.led.append(dict(Month=m, Opening=pre_bal, EMI=0.0, Interest=0.0,
                                 Principal=0.0, Prepayment=applied, Closing=self.balance))
        if mode == "emi" and self.balance > 0 and not self.revolving:
            rem = tenure_of(pre_bal, self.r_now(bps), self.emi)
            if rem and rem > 1:
                self.emi = emi_of(self.balance, self.r_now(bps), rem)
        if self.balance <= 0.5:
            self.balance = 0.0
            self.active = False
            self.closed_m = m
        return used


@dataclass
class Asset:
    name: str
    klass: str
    balance: float
    cost: float
    ret: float
    vol: float
    liq: int
    kind: str
    lock_end: int
    sip: float
    stepup: float
    exit_load: float
    earmark: str
    protected: bool
    personal: bool = False
    growth: float = 0.0
    contrib: float = 0.0
    wdrawn: float = 0.0

    def mr(self):
        """Monthly effective rate, computed once — this runs for every holding
        in every month of the projection."""
        m = self.__dict__.get("_mr")
        if m is None:
            m = self.__dict__["_mr"] = mrate(self.ret)
        return m

    def grow(self):
        g = self.balance * self.mr()
        self.balance += g
        self.growth += g
        return g

    def add(self, amt):
        self.balance += amt
        self.cost += amt
        self.contrib += amt

    def sip_at(self, m):
        if self.sip <= 0:
            return 0.0
        return self.sip * (1 + self.stepup / 100.0) ** ((m - 1) // 12)

    def free(self, m):
        # Personal-use assets are never liquidated by the engine: it will not sell
        # the house you live in or the car you drive to plug a gap.
        return m >= self.lock_end and not self.protected and not self.personal

    def gain_frac(self):
        return max(0.0, (self.balance - self.cost) / self.balance) if self.balance > 0 else 0.0

    def liquidate(self, m, led: TaxLedger, force=False, exempt=False):
        """Sell the holding outright.

        `force` overrides the personal-use and never-liquidate guards — used when
        the plan explicitly trades an asset in, such as selling the house you are
        upgrading out of. A statutory lock-in always binds. `exempt` suppresses
        capital-gains tax for a Section 54 style rollover."""
        if self.balance <= 0 or m < self.lock_end:
            return 0.0, 0.0, 0.0, 0.0
        if not force and (self.protected or self.personal):
            return 0.0, 0.0, 0.0, 0.0
        gross = self.balance
        gain = max(0.0, gross - self.cost)
        tx = 0.0 if exempt else led.tax_on_gain(gain, self.kind)
        load = gross * self.exit_load / 100.0
        net = gross - tx - load
        self.cost = 0.0
        self.balance = 0.0
        self.wdrawn += gross
        return net, tx, load, gross

    def redeem(self, net_needed, m, led: TaxLedger):
        """Redeem to net `net_needed` after exit load and CGT. Bisection on gross."""
        if net_needed <= 0 or self.balance <= 0 or not self.free(m):
            return 0.0, 0.0, 0.0, 0.0
        gf, el = self.gain_frac(), self.exit_load / 100.0

        def net_of(g):
            return g - led.peek_tax(g * gf, self.kind) - g * el

        if net_of(self.balance) <= net_needed:
            gross = self.balance
        else:
            lo, hi = 0.0, self.balance
            for _ in range(60):
                mid = (lo + hi) / 2
                if net_of(mid) < net_needed:
                    lo = mid
                else:
                    hi = mid
            gross = hi
        gross = min(gross, self.balance)
        tx = led.tax_on_gain(gross * gf, self.kind)
        load = gross * el
        net = gross - tx - load
        self.cost *= (1 - gross / self.balance) if self.balance > 0 else 0.0
        self.balance -= gross
        self.wdrawn += gross
        return net, tx, load, gross


# ============================================================== 7. ANALYTICS
# Column schemas for the two diagnostic tables. An empty DataFrame built from an
# empty list of dicts carries no columns at all, which turned every downstream
# column access into a KeyError — advice() crashed for any profile with no debt.
_INV_COLS = ["Investment", "Class", "Personal", "Value", "Cost", "SIP", "StepUp",
             "Nominal", "Volatility", "TaxDrag", "PostTax", "TaxCostPts", "RiskCutPts",
             "Horizon", "RiskAdj", "DaysToCash", "LiquidityScore", "LockInMonths",
             "ExitLoad", "Earmark", "Protected", "TaxKind", "Deployable", "Weight %"]
_DEBT_COLS = ["Loan", "Type", "Security", "Collateral", "Outstanding", "Rate",
              "RateApplied", "EffectiveCost", "RealCost", "Shield", "EMI", "MonthsLeft",
              "InterestRemaining", "IntToPrin", "Benchmark", "Spread", "DecisionYears",
              "Verdict",
              "Revolving", "MinDue", "Penalty", "MarketRate", "Fixed", "LinkedAsset",
              "EngineNote"]
def after_tax_cagr(nom, kind, tax: TaxConfig, years):
    """Annualised return after tax, over a stated holding period.

    Interest-like income (slab-taxed) is taxed as it accrues, so the full rate
    bites every single year. A growth asset defers capital-gains tax to the day
    you actually sell, so charging the exit rate annually understates it — and
    the longer the hold, the larger the understatement."""
    if kind == "exempt":
        return nom
    if kind == "slab":
        return nom * (1 - tax.mtr)
    r, tr = nom / 100.0, tax.gains_rate(kind)
    n_ = max(float(years), 1.0)
    if r <= -1.0:
        return nom
    gross = (1.0 + r) ** n_
    if gross <= 1.0:
        return nom            # a loss attracts no capital-gains tax, and no credit
    net = gross - tr * (gross - 1.0)
    if net <= 0:
        return nom * (1 - tr)
    return (net ** (1.0 / n_) - 1.0) * 100.0


def risk_haircut(vol, coeff, years, scale=True):
    """Points knocked off an expected return to pay for its volatility.

    Volatility is quoted per year, but prepay-or-invest is a decision that runs
    for the life of the loan. The spread of the ANNUALISED outcome narrows with
    the square root of the horizon, so charging one full year of volatility
    against a sixteen-year decision overstates the risk several times over —
    which is what made cheap, long, secured loans read as loss-making."""
    if not scale:
        return coeff * vol
    return coeff * vol / math.sqrt(max(float(years), 1.0))


def inv_table(df, tax: TaxConfig, A, horizon=None):
    h = sf(horizon, 0.0) or sf(A.get("horizon_years"), 10.0)
    scale = sb(A.get("horizon_risk", True), True)
    coeff = sf(A["risk_aversion"])
    rows = []
    for _, r in df.iterrows():
        nm = str(r.get("Investment Name", "")).strip()
        if not nm:
            continue
        cls = str(r.get("Asset Class", "Other"))
        d = ASSET_CLASSES.get(cls, ASSET_CLASSES["Other"])
        val = sf(r.get("Current Value"))
        nom = sf(r.get("Expected Return % p.a."), d["ret"])
        vol = sf(r.get("Volatility % p.a."), d["vol"])
        kind = d["tax"]
        post = after_tax_cagr(nom, kind, tax, h)
        cut = risk_haircut(vol, coeff, h, scale)
        radj = post - cut
        liq = si(r.get("Days to Cash"), d["liq"])
        lock = si(r.get("Lock-in Remaining (months)"), d["lock"])
        prot = sb(r.get("Never Liquidate"))
        ear = str(r.get("Earmarked for Goal", "") or "").strip()
        personal = cls in PERSONAL_CLASSES
        rows.append(dict(
            Personal=personal,
            Investment=nm, Class=cls, Value=val, Cost=sf(r.get("Invested Cost"), val),
            SIP=sf(r.get("Monthly SIP")), StepUp=sf(r.get("SIP Step-up % p.a.")),
            Nominal=nom, Volatility=vol, PostTax=post,
            TaxDrag=((nom - post) / nom * 100 if nom else 0.0),
            TaxCostPts=(nom - post), RiskCutPts=cut, Horizon=h,
            RiskAdj=radj, DaysToCash=liq, LiquidityScore=liq_score(liq),
            LockInMonths=lock, ExitLoad=sf(r.get("Exit Load %")), Earmark=ear,
            Protected=prot, TaxKind=kind,
            Deployable=(lock == 0 and liq <= si(A["deployable_max_days"])
                        and not prot and not ear and not personal)))
    t = pd.DataFrame(rows, columns=_INV_COLS)
    if not t.empty:
        s = t["Value"].sum()
        t["Weight %"] = np.where(s > 0, t["Value"] / s * 100, 0.0)
    return t


def benchmark_of(t, A):
    """The return a rupee could earn instead of repaying debt.

    'Marginal surplus vehicle' is the default because it answers the actual
    question: if you DON'T prepay, the money goes to your chosen surplus vehicle
    — not proportionally into every liquid holding you own. Blending in a liquid
    fund you hold for liquidity, not for return, drags the benchmark down and
    makes sound leverage look loss-making."""
    mode = str(A.get("benchmark_mode", BENCH_MODES[0]))
    if mode == "Custom %":
        return sf(A["benchmark_custom"])
    if t is None or t.empty:
        return sf(A["benchmark_custom"])
    if mode.startswith("Marginal") or mode == "Default surplus vehicle":
        r = t[t["Investment"] == str(A.get("default_vehicle", "")).strip()]
        if not r.empty:
            return float(r.iloc[0]["RiskAdj"])
        # named vehicle missing: fall through to the blend rather than to a
        # constant that has nothing to do with the portfolio
    dep = t[t["Deployable"]]
    if dep.empty or dep["Value"].sum() <= 0:
        return sf(A["benchmark_custom"])
    return float(np.average(dep["RiskAdj"], weights=dep["Value"]))


def verdict_of(spread):
    return V_GOOD if spread > BAND_HI else V_BAD if spread < BAND_LO else V_NEUT


def schedule(P, rate, emi, revolving=False, min_due=5.0, cap=600,
             pre_m=None, pre_amt=0.0):
    rows, bal, m, r = [], float(P), 0, lrate(rate)
    md = max(sf(min_due), 1.0)
    while bal > 0.5 and m < cap:
        m += 1
        i = bal * r
        pay = max(bal * md / 100 + i, 100.0) if revolving else emi
        pay = min(pay, bal + i)
        p = min(max(pay - i, 0.0), bal)
        op = bal
        bal -= p
        pre = 0.0
        if pre_m and m == pre_m and pre_amt > 0:
            pre = min(pre_amt, bal)
            bal -= pre
        rows.append(dict(Month=m, Opening=op, EMI=pay, Interest=i, Principal=p,
                         Prepayment=pre, Closing=bal))
        if p <= 0 and pre <= 0:
            break
    return pd.DataFrame(rows)


def run_off(P, rate, emi, revolving=False, min_due=5.0, cap=600):
    """Months to closure and total interest, using the same recurrence as
    schedule() but without materialising a DataFrame. Used wherever only the
    totals are wanted — the diagnostics table and the swap optimiser."""
    bal, r = float(P), lrate(rate)
    md = max(sf(min_due), 1.0)
    ti, m = 0.0, 0
    while bal > 0.5 and m < cap:
        m += 1
        i = bal * r
        pay = max(bal * md / 100 + i, 100.0) if revolving else emi
        pay = min(pay, bal + i)
        p = min(max(pay - i, 0.0), bal)
        bal -= p
        ti += i
        if p <= 0:
            break
    return m, ti


def debt_table(df, tax: TaxConfig, bench_fn, infl, bps=0.0):
    # bench_fn(years) -> the return a rupee could earn over THAT loan's remaining
    # life. Judging a 16-year home loan and a 1-year card balance against the same
    # one-year benchmark was the core of the mis-verdict.
    bf = bench_fn if callable(bench_fn) else (lambda _y: float(bench_fn))
    rows = []
    for _, r in df.iterrows():
        nm = str(r.get("Loan / Lender", "")).strip()
        out = sf(r.get("Outstanding Principal"))
        if not nm or out <= 0:
            continue
        lt = str(r.get("Loan Type", "Personal Loan"))
        meta = DEBT_TYPES.get(lt, DEBT_TYPES["Personal Loan"])
        rate = sf(r.get("Interest Rate % p.a."))
        rem = si(r.get("Remaining Tenure (months)"))
        emi = sf(r.get("EMI"))
        flat = sb(r.get("Flat / Add-on Rate?"))
        note = ""
        if flat and rem > 0:
            rate, e2 = flat_to_reducing(out, rate, rem)
            emi = emi if emi > 0 else e2
            note = "flat rate converted"
        if not meta["rev"]:
            if emi <= 0 and rem > 0:
                emi = emi_of(out, rate, rem)
                note = (note + "; " if note else "") + "EMI derived from tenure"
            elif emi > 0:
                t = tenure_of(out, rate, emi)
                if t is None:
                    note = (note + "; " if note else "") + "EMI does not cover interest"
                    rem = rem or 600
                else:
                    if rem and abs(t - rem) > 2:
                        note = (note + "; " if note else "") + \
                            f"tenure recomputed {rem}->{t} from EMI"
                    rem = t
        fixed = str(r.get("Fixed / Floating", "Floating")).lower().startswith("fix")
        md = sf(r.get("Min Due % (revolving)"), 5.0)
        if meta["rev"] and md <= 0:
            md = 5.0
            note = (note + "; " if note else "") + "min-due defaulted to 5%"
        eff_r = rate + (0.0 if fixed else bps / 100.0)
        ec = tax.eff_cost(eff_r, out, meta["shield"])
        mleft_est, _ = run_off(out, eff_r, emi, meta["rev"], md)
        # Revolving credit can be cleared tomorrow, so the money's alternative use
        # is a short one. Term loans get the horizon they actually run for.
        yrs = 1.0 if meta["rev"] else max((mleft_est or rem or 12) / 12.0, 1.0)
        bench = bf(yrs)
        sp = bench - ec
        v = verdict_of(sp)
        if meta["rev"] and ec > 18:
            v = V_BAD
        mleft, ti = run_off(out, eff_r, emi, meta["rev"], md)
        rows.append(dict(
            Loan=nm, Type=lt, Security=("Secured" if sb(r.get("Secured?"), meta["sec"])
                                        else "Unsecured"),
            Collateral=str(r.get("Collateral / Security", "") or "-"),
            Outstanding=out, Rate=rate, RateApplied=eff_r, EffectiveCost=ec,
            RealCost=real_rate(ec, infl), Shield=meta["shield"],
            EMI=emi, MonthsLeft=(mleft or rem), InterestRemaining=ti,
            IntToPrin=(ti / out * 100 if out else 0.0), Benchmark=bench, Spread=sp,
            DecisionYears=yrs,
            Verdict=v, Revolving=meta["rev"], MinDue=md, Penalty=sf(r.get("Prepayment Penalty %")),
            MarketRate=meta["mkt"], Fixed=fixed,
            LinkedAsset=str(r.get("Linked Investment (collateral)", "") or ""),
            EngineNote=note or "-"))
    return pd.DataFrame(rows, columns=_DEBT_COLS)


# ============================================================= 8. SIMULATION
@dataclass
class Sim:
    monthly: pd.DataFrame
    annual: pd.DataFrame
    ledgers: dict
    goals: list
    warnings: list
    debt: pd.DataFrame
    inv: pd.DataFrame
    bench: float
    wlog: pd.DataFrame
    nw0: float
    nw1: float
    audit: pd.DataFrame
    loans: list
    assets: list
    goal_src: pd.DataFrame


def _month_of_year(v, fallback):
    """A blank or out-of-range calendar month never matches, which silently
    disables the item for the whole projection. Fall back instead."""
    x = si(v, fallback)
    return x if 1 <= x <= 12 else fallback


def build_plan(P):
    """Flatten the input frames into plain Python structures ONCE.

    The monthly loop used to call DataFrame.iterrows() for expenses, lumpy items
    and passive income in every one of up to 360 months — over half the whole
    projection's runtime. None of it depends on the month, so it is hoisted."""
    A = P["assumptions"]
    infl = sf(A["inflation"])
    earners = []
    for who in ("primary", "secondary"):
        b = P["income"].get(who, {})
        if not sb(b.get("enabled")):
            continue
        earners.append(dict(
            stop=si(b.get("stop_month")), sal=sf(b.get("monthly_inhand")),
            bonus=sf(b.get("annual_bonus")), bm=_month_of_year(b.get("bonus_month"), 4),
            im=_month_of_year(b.get("increment_month"), 4),
            inc=sf(b.get("increment_pct")) / 100.0,
            biz=sf(b.get("business_monthly")),
            bizg=sf(b.get("business_growth_pct")) / 100.0))
    passive = []
    for _, r in P["passive"].iterrows():
        if not str(r.get("Source", "")).strip():
            continue
        amt = sf(r.get("Amount"))
        if amt <= 0:
            continue
        e0 = si(r.get("End Month"))
        passive.append(dict(
            amt=amt, s0=max(si(r.get("Start Month"), 1), 1),
            e0=(e0 if e0 > 0 else 10 ** 9),
            g=sf(r.get("Growth % p.a.")) / 100.0,
            step={"Monthly": 1, "Quarterly": 3, "Half-yearly": 6,
                  "Annual": 12}.get(str(r.get("Frequency", "Monthly")), 1),
            taxed=(sb(r.get("Taxable?"), True)
                   and str(r.get("Entered As", "Gross")) == "Gross"),
            rental=(str(r.get("Type")) == "Rental Income")))
    exps = []
    for _, r in P["expenses"].iterrows():
        if not str(r.get("Category", "")).strip():
            continue
        amt = sf(r.get("Monthly Amount"))
        if amt <= 0:
            continue
        rt = sf(r.get("Custom Step-up % p.a.")) if \
            str(r.get("Step-up Basis", "Inflation")) == "Custom %" else \
            sf(r.get("Category Inflation %"), infl)
        exps.append((amt, rt))
    lumps = []
    for _, r in P["lumpy"].iterrows():
        if not str(r.get("Item", "")).strip():
            continue
        amt = sf(r.get("Annual Amount"))
        if amt <= 0:
            continue
        lumps.append((amt, _month_of_year(r.get("Month of Year"), 1),
                      sf(r.get("Inflation % p.a."), infl) / 100.0))
    return dict(sm=si(A["start_month"], 1), earners=earners, passive=passive,
                exps=exps, lumps=lumps, _expc={})


def _hikes(sm, im, m):
    """How many increment anniversaries have landed strictly after month 1.

    cal_month(sm, k) == im  <=>  k = d (mod 12), with d as below. Counting the
    matching k in [2, m] in closed form replaces an O(m) scan that ran per
    earner per month, i.e. O(months^2) over the projection."""
    d = (im - sm + 1) % 12
    k0 = d if d >= 2 else d + 12
    return 0 if m < k0 else (m - k0) // 12 + 1


def income_at(plan, m, sc, tax):
    sm = plan["sm"]
    cm = cal_month(sm, m)
    yr = (m - 1) // 12
    o = dict(salary=0.0, bonus=0.0, business=0.0, passive=0.0)
    shock = (1 - sc["income_loss_pct"] / 100.0) \
        if (sc["income_loss_months"] and m <= sc["income_loss_months"]) else 1.0
    for b in plan["earners"]:
        if b["stop"] and m > b["stop"]:
            continue
        g = (1 + b["inc"]) ** _hikes(sm, b["im"], m)
        o["salary"] += b["sal"] * g * shock
        if cm == b["bm"]:
            o["bonus"] += b["bonus"] * g
        o["business"] += b["biz"] * (1 + b["bizg"]) ** yr
    for p in plan["passive"]:
        if m < p["s0"] or m > p["e0"] or (m - p["s0"]) % p["step"]:
            continue
        amt = p["amt"] * (1 + p["g"]) ** yr
        if p["taxed"]:
            # Rental income carries the 30% standard deduction before tax.
            base = amt * 0.70 if p["rental"] else amt
            amt -= base * tax.mtr
        o["passive"] += amt
    return o


def expense_at(plan, m, sc):
    yr = (m - 1) // 12
    cm = cal_month(plan["sm"], m)
    shift = sc["expense_shift"]
    tot = plan["_expc"].get(yr)
    if tot is None:
        tot = plan["_expc"][yr] = sum(
            amt * (1 + (rt + shift) / 100.0) ** yr for amt, rt in plan["exps"])
    lump = sum(amt * (1 + g) ** yr for amt, mo, g in plan["lumps"] if mo == cm)
    return tot, lump


def simulate(P, sc):
    tax: TaxConfig = P["_tax"]
    led = TaxLedger(tax)
    A = P["assumptions"]
    H = si(A["horizon_years"], 10) * 12
    infl = sf(A["inflation"])
    warn = []

    itbl = inv_table(P["investments"], tax, A)
    bench = benchmark_of(itbl, A)
    _bcache = {}

    def bench_fn(years):
        """Benchmark return over a given holding period, memoised."""
        k = round(max(float(years), 1.0), 1)
        if k not in _bcache:
            _bcache[k] = benchmark_of(inv_table(P["investments"], tax, A, k), A)
        return _bcache[k]

    dtbl = debt_table(P["debts"], tax, bench_fn, infl, sc["rate_bps"])
    plan = build_plan(P)

    assets = []
    for _, r in itbl.iterrows():
        shock = (1 - sc["market_shock"] / 100.0) if r["Volatility"] > 8 else 1.0
        assets.append(Asset(
            name=r["Investment"], klass=r["Class"], balance=r["Value"] * shock,
            cost=r["Cost"], ret=r["Nominal"] + sc["return_shift"], vol=r["Volatility"],
            liq=si(r["DaysToCash"]), kind=r["TaxKind"], lock_end=si(r["LockInMonths"]) + 1,
            sip=r["SIP"], stepup=r["StepUp"], exit_load=r["ExitLoad"],
            earmark=r["Earmark"], protected=bool(r["Protected"]),
            personal=bool(r["Personal"])))

    loans = []
    for _, r in dtbl.iterrows():
        L = Loan(name=r["Loan"], ltype=r["Type"], secured=(r["Security"] == "Secured"),
                 collateral=r["Collateral"], balance=r["Outstanding"], rate=r["Rate"],
                 emi=r["EMI"], penalty=r["Penalty"], shield=r["Shield"],
                 revolving=bool(r["Revolving"]), min_due=r["MinDue"], fixed=bool(r["Fixed"]),
                 linked=r["LinkedAsset"], opening=r["Outstanding"],
                 eff_cost=r["EffectiveCost"], verdict=r["Verdict"])
        loans.append(L)

    def collateral_now():
        """Holdings pledged against a loan that is still live. Recomputed because a
        trade-in can settle the loan and release the security mid-projection."""
        return {L.linked for L in loans if L.linked and L.balance > 0.5}

    ef = sf(A["ef_current"])
    ef_r = mrate(A["ef_return"])
    goal_r = mrate(A["goal_vehicle_return"])

    goals = []
    for _, r in P["goals"].iterrows():
        nm = str(r.get("Goal Name", "")).strip()
        if not nm:
            continue
        ty = max(si(r.get("Target Year (from now)"), 1), 1)
        c0 = sf(r.get("Cost in Today's Money"))
        gi = sf(r.get("Goal Inflation % p.a."), infl)
        goals.append(dict(name=nm, cat=str(r.get("Category", "Other")), month=ty * 12,
                          years=ty, c0=c0, gi=gi, fv=c0 * (1 + gi / 100.0) ** ty,
                          pri=min(max(si(r.get("Priority (1=highest)"), 3), 1), 5),
                          own=sf(r.get("% From Own Corpus"), 100.0),
                          lrate_=sf(r.get("If Loan: Rate %")),
                          ltenure=si(r.get("If Loan: Tenure (yrs)")),
                          ear=str(r.get("Earmarked Investment", "") or "").strip(),
                          sell=str(r.get("Sell to Fund (asset name)", "") or "").strip(),
                          becomes=str(r.get("Becomes Asset (class)", "") or "").strip(),
                          inh=(ty * 12 <= H),
                          bucket=0.0, growth=0.0, sunk=0.0, f_bucket=0.0, f_ear=0.0,
                          f_liq=0.0, f_loan=0.0, short=0.0, capped=0.0,
                          f_sale=0.0, settled=0.0, freed=0.0, cap=0.0, srcs=[]))
    goals.sort(key=lambda g: (g["month"], g["pri"]))

    sipset = itbl[itbl["SIP"] > 0] if not itbl.empty else pd.DataFrame()
    sip_blend = float(np.average(sipset["RiskAdj"], weights=sipset["SIP"])) \
        if not sipset.empty and sipset["SIP"].sum() > 0 else bench

    rows, wlog = [], []
    mode = A["prepay_mode"]

    for m in range(1, H + 1):
        led.roll(m)
        yr = (m - 1) // 12 + 1
        a_open = sum(x.balance for x in assets)
        ef_open, gb_open = ef, sum(g["bucket"] for g in goals)

        inc = income_at(plan, m, sc, tax)
        tinc = sum(inc.values())
        exp, lump = expense_at(plan, m, sc)
        living = exp + lump

        a_growth = sum(x.grow() for x in assets)
        ef_int = ef * ef_r
        ef += ef_int
        g_growth = 0.0
        for g in goals:
            gg = g["bucket"] * goal_r
            g["bucket"] += gg
            g["growth"] += gg
            g_growth += gg

        for L in loans:
            if L.start_m == m and L.balance > 0:
                L.active = True

        emi_tot = i_tot = p_tot = 0.0
        for L in loans:
            i, p, cash = L.service(m, sc["rate_bps"])
            emi_tot += cash
            i_tot += i
            p_tot += p

        collateral_locked = collateral_now()
        surplus = tinc - living - emi_tot
        avail = max(surplus, 0.0)
        w_net = w_gross = w_tax = gap = ef_used = 0.0
        bucket_used = loan_drawn = capitalised = 0.0

        if surplus < 0:
            need = -surplus
            u = min(ef, need)
            ef -= u
            ef_used += u
            need -= u
            # NB: the EF drawdown is its own cash source (EF_Used). Folding it
            # into Withdraw_Net as well double-counted it in the cash identity.
            if need > 0:
                for x in sorted(assets, key=lambda z: (z.liq, -z.ret)):
                    if need <= 0.5:
                        break
                    if x.earmark or x.name in collateral_locked or not x.free(m):
                        continue
                    n, t, l, gr = x.redeem(need, m, led)
                    need -= n
                    w_net += n
                    w_tax += t
                    w_gross += gr
            if need > 1:
                gap = need
                warn.append(f"M{m} (Yr{yr}): financing gap {compact(need)} — income plus "
                            f"accessible assets did not cover outgo.")
            avail = 0.0

        al = dict(ef=0.0, rev=0.0, sip=0.0, goal=0.0, pre=0.0, res=0.0)
        ef_tgt = sf(A["ef_target_months"]) * (exp + (emi_tot if sb(A["ef_include_emi"]) else 0))
        if ef < ef_tgt and avail > 0:
            t = min(ef_tgt - ef, avail * sf(A["ef_max_share"]) / 100.0)
            ef += t
            avail -= t
            al["ef"] = t

        for L in sorted([l for l in loans if l.revolving and l.active],
                        key=lambda z: -z.eff_cost):
            if avail <= 0:
                break
            used = L.prepay(min(avail, L.balance * (1 + L.penalty / 100)), m, mode,
                            sc["rate_bps"])
            avail -= used
            al["rev"] += used

        lossy = [l for l in loans if l.active and not l.revolving and l.verdict == V_BAD]
        worst = max([l.eff_cost for l in lossy], default=None)
        flip = bool(lossy) and (sip_blend < worst)

        def do_sip():
            nonlocal avail
            for x in assets:
                if avail <= 0:
                    break
                amt = min(x.sip_at(m), avail)
                if amt <= 0:
                    continue
                x.add(amt)
                avail -= amt
                al["sip"] += amt

        def do_pre():
            nonlocal avail
            if avail <= 0:
                return
            budget = avail * sf(A["prepay_share_of_surplus"]) / 100.0
            for L in sorted(lossy, key=lambda z: -z.eff_cost):
                if budget <= 0:
                    break
                used = L.prepay(min(budget, L.balance * (1 + L.penalty / 100.0)), m,
                                mode, sc["rate_bps"])
                budget -= used
                avail -= used
                al["pre"] += used

        def do_goal():
            nonlocal avail
            if avail <= 0:
                return
            live = [g for g in goals if g["month"] >= m]
            reqs = []
            for g in live:
                n = max(g["month"] - m + 1, 1)
                need = g["fv"] * g["own"] / 100.0
                have = g["bucket"] * (1 + goal_r) ** n
                if g["ear"]:
                    for x in assets:
                        if x.name == g["ear"]:
                            have += x.balance * (1 + x.mr()) ** n
                shortfall = max(need - have, 0.0)
                if shortfall <= 0:
                    continue
                pmt = shortfall * goal_r / ((1 + goal_r) ** n - 1) if goal_r > 0 \
                    else shortfall / n
                reqs.append((g, pmt))
            if not reqs:
                return
            treq = sum(p for _, p in reqs)
            pot = min(avail, treq)
            if pot >= treq - 1e-9:
                for g, p in reqs:
                    g["bucket"] += p
                    g["sunk"] += p
            else:
                w = [(6 - g["pri"]) * p for g, p in reqs]
                ws = sum(w) or 1.0
                for (g, p), wi in zip(reqs, w):
                    s = pot * wi / ws
                    g["bucket"] += s
                    g["sunk"] += s
            al["goal"] += pot
            avail -= pot

        if flip:
            do_pre(); do_sip(); do_goal()
        else:
            do_sip(); do_goal(); do_pre()

        if avail > 0.01:
            tgt = next((x for x in assets if x.name == A["default_vehicle"]), None)
            if tgt is None:
                cands = [x for x in assets if not x.protected and not x.personal]
                tgt = max(cands, key=lambda z: z.ret) if cands else None
            if tgt is not None:
                tgt.add(avail)
                al["res"] += avail
            else:
                # Nothing investable exists: park it in the emergency fund and
                # book it as an EF top-up. Booking it as a portfolio contribution
                # credited the portfolio with money it never received.
                ef += avail
                al["ef"] += avail
            avail = 0.0

        g_out = 0.0
        for g in goals:
            if g["month"] != m:
                continue
            need = g["fv"]

            # ---- 1. TRADE-IN. Sell what is being replaced, settle any loan
            # secured on it out of the proceeds, and recover that EMI.
            sale_net, freed = 0.0, 0.0
            if g["sell"]:
                tgt_a = next((x for x in assets
                              if x.name == g["sell"] and x.balance > 0), None)
                if tgt_a is None:
                    warn.append(f"Goal '{g['name']}': '{g['sell']}' was named as the "
                                f"asset to sell but no such holding was left to sell.")
                else:
                    roll = (sb(tax.sec54_rollover, True)
                            and tgt_a.klass in RESIDENTIAL_CLASSES
                            and g["becomes"] in RESIDENTIAL_CLASSES)
                    nt, tx_, ld_, gr_ = tgt_a.liquidate(m, led, force=True, exempt=roll)
                    sale_net += nt
                    w_net += nt
                    w_tax += tx_
                    w_gross += gr_
                    g["srcs"].append(dict(
                        Source=tgt_a.name, Kind="Asset sold (trade-in)",
                        Asset_Class=tgt_a.klass, Gross=gr_, Tax=tx_, Exit_Cost=ld_,
                        Net_Applied=nt,
                        Note=("Section 54 rollover — no capital-gains tax" if roll
                              else "sold in full at its projected value")))
                    warn.append(
                        f"Goal '{g['name']}' (Yr{g['years']}): sold '{tgt_a.name}' for "
                        f"{compact(gr_)} gross, {compact(nt)} net"
                        + (" (Section 54 rollover applied, no capital-gains tax)"
                           if roll else f" after {compact(tx_ + ld_)} of tax and costs")
                        + ".")
                    for L in loans:
                        if not (L.active and L.balance > 0.5 and L.linked == tgt_a.name):
                            continue
                        emi_was = L.emi
                        used = L.prepay(min(sale_net, L.balance * (1 + L.penalty / 100)),
                                        m, mode, sc["rate_bps"])
                        sale_net -= used
                        al["pre"] += used
                        g["settled"] += used
                        if not L.active:
                            freed += emi_was
                            warn.append(
                                f"Goal '{g['name']}': settled '{L.name}' with "
                                f"{compact(used)} of the sale proceeds, freeing "
                                f"{money(emi_was)} a month of EMI capacity.")
                        else:
                            warn.append(
                                f"Goal '{g['name']}': the sale of '{tgt_a.name}' did not "
                                f"fully clear '{L.name}' — {compact(L.balance)} of "
                                f"secured debt remains against an asset you no longer own.")
                    g["freed"] = freed

            # ---- 2. Proceeds meet the cost first; the down-payment ratio then
            # applies to whatever is still left to find.
            take_sale = min(max(sale_net, 0.0), need)
            g["f_sale"] = take_sale
            sale_net -= take_sale
            after = max(need - take_sale, 0.0)
            own = after * g["own"] / 100.0
            fin = after - own
            if fin > 1:
                if g["ltenure"] > 0 and g["lrate_"] > 0:
                    lt = ("Home Loan (Self-occupied)" if "House" in g["cat"]
                          else "Education Loan" if "Education" in g["cat"]
                          else "Car / Vehicle Loan" if "Vehicle" in g["cat"]
                          else "Personal Loan")
                    meta = DEBT_TYPES[lt]
                    # AFFORDABILITY GATE. A goal is not "funded" merely because a
                    # loan can be imagined for it. The new EMI, on top of everything
                    # already being serviced, must stay inside the EMI-to-income
                    # ceiling. EMI is linear in principal, so the borrowable amount
                    # scales directly with the headroom that is left.
                    # The EMI released by settling the old loan is capacity again.
                    room = max(tinc * sf(A["emi_income_ceiling"]) / 100.0
                               - max(emi_tot - freed, 0.0), 0.0)
                    want = emi_of(fin, g["lrate_"], g["ltenure"] * 12)
                    take = fin if want <= room else (fin * room / want if want > 0 else 0.0)
                    if take > 1:
                        nl = Loan(name=f"{g['name']} — planned loan", ltype=lt,
                                  secured=meta["sec"], collateral=g["cat"], balance=take,
                                  rate=g["lrate_"],
                                  emi=emi_of(take, g["lrate_"], g["ltenure"] * 12),
                                  penalty=0.0, shield=meta["shield"], revolving=False,
                                  min_due=5.0, fixed=False, start_m=m + 1, active=False,
                                  opening=take)
                        nl.linked = g["name"] if g["becomes"] else ""
                        nl.eff_cost = tax.eff_cost(nl.rate, take, nl.shield)
                        nl.verdict = verdict_of(bench_fn(g["ltenure"]) - nl.eff_cost)
                        loans.append(nl)
                        g["f_loan"] = take
                        loan_drawn += take
                        g["srcs"].append(dict(
                            Source=nl.name, Kind="New borrowing",
                            Asset_Class="-", Gross=take, Tax=0.0, Exit_Cost=0.0,
                            Net_Applied=take,
                            Note=f"{lt} at {g['lrate_']:.2f}% over "
                                 f"{g['ltenure']} years, EMI {money(nl.emi)}"))
                    if fin - take > 1:
                        g["capped"] = fin - take
                        warn.append(
                            f"Goal '{g['name']}' (Yr{g['years']}): the plan assumed "
                            f"{compact(fin)} of new borrowing, but servicing it needs "
                            f"{money(want)} a month and only {money(room)} fits inside "
                            f"your {sf(A['emi_income_ceiling']):.0f}% EMI-to-income "
                            f"ceiling. Borrowing was capped at {compact(take)}; the "
                            f"rest must come from your own corpus or the goal is short.")
                    own += fin - take
                else:
                    own = need
                    warn.append(f"Goal '{g['name']}': financed portion had no rate/tenure, "
                                f"so it was treated as fully self-funded.")
            u = min(g["bucket"], own)
            g["bucket"] -= u
            own -= u
            g["f_bucket"] = u
            bucket_used += u
            if u > 0.5:
                g["srcs"].append(dict(
                    Source="Goal sinking fund", Kind="Sinking fund",
                    Asset_Class="-", Gross=u, Tax=0.0, Exit_Cost=0.0, Net_Applied=u,
                    Note="monthly set-asides made for this goal, plus growth"))
            if own > 0 and g["ear"]:
                for x in assets:
                    if x.name == g["ear"]:
                        n, t, l, gr = x.redeem(own, m, led)
                        own -= n
                        g["f_ear"] += n
                        w_tax += t
                        w_gross += gr
                        w_net += n
                        if n > 0.5:
                            g["srcs"].append(dict(
                                Source=x.name, Kind="Earmarked investment",
                                Asset_Class=x.klass, Gross=gr, Tax=t, Exit_Cost=l,
                                Net_Applied=n,
                                Note="ring-fenced for this goal from the start"))
            if own > 0:
                for x in sorted(assets, key=lambda z: (z.liq, z.ret)):
                    if own <= 0.5:
                        break
                    if x.earmark or x.name in collateral_locked or not x.free(m):
                        continue
                    n, t, l, gr = x.redeem(own, m, led)
                    own -= n
                    g["f_liq"] += n
                    w_tax += t
                    w_gross += gr
                    w_net += n
                    if n > 0.5:
                        g["srcs"].append(dict(
                            Source=x.name, Kind="Other investment redeemed",
                            Asset_Class=x.klass, Gross=gr, Tax=t, Exit_Cost=l,
                            Net_Applied=n,
                            Note=f"redeemed in liquidity order ({x.liq} days to cash)"))
            if own > 1:
                g["short"] = own
                g["srcs"].append(dict(
                    Source="UNFUNDED", Kind="Shortfall", Asset_Class="-", Gross=own,
                    Tax=0.0, Exit_Cost=0.0, Net_Applied=own,
                    Note="nothing left to draw on — this part of the goal is not met"))
                warn.append(f"Goal '{g['name']}' (Yr{g['years']}): shortfall {compact(own)} "
                            f"against a need of {compact(need)}.")
            # Only money that actually moved is an outflow. Booking the full cost
            # when part of it was never funded invented cash equal to the
            # shortfall. The unfunded remainder is reported as a shortfall on the
            # goal roadmap instead. `+=` because two goals can share a month.
            paid = (g["f_sale"] + g["f_bucket"] + g["f_ear"] + g["f_liq"]
                    + g["f_loan"])
            g_out += paid

            # ---- 3. If the goal BUYS something you still own, put it on the
            # balance sheet at what was actually paid. Without this an upgrade
            # looked like pure destruction of net worth.
            if g["becomes"] and paid > 1:
                dd = ASSET_CLASSES.get(g["becomes"], ASSET_CLASSES["Other"])
                assets.append(Asset(
                    name=g["name"], klass=g["becomes"], balance=paid, cost=paid,
                    ret=dd["ret"] + sc["return_shift"], vol=dd["vol"], liq=dd["liq"],
                    kind=dd["tax"], lock_end=m + si(dd["lock"]), sip=0.0, stepup=0.0,
                    exit_load=0.0, earmark="", protected=False,
                    personal=(g["becomes"] in PERSONAL_CLASSES)))
                g["cap"] = paid
                capitalised += paid

            # ---- 4. Sold for more than the replacement cost? Bank the difference.
            if sale_net > 1:
                tt = next((x for x in assets
                           if x.name == A["default_vehicle"] and not x.personal), None)
                if tt is None:
                    cc = [x for x in assets if not x.protected and not x.personal]
                    tt = max(cc, key=lambda z: z.ret) if cc else None
                if tt is not None:
                    tt.add(sale_net)
                    al["res"] += sale_net
                else:
                    ef += sale_net
                    al["ef"] += sale_net
                sale_net = 0.0

        a_close = sum(x.balance for x in assets)
        gb = sum(g["bucket"] for g in goals)
        debt = sum(l.balance for l in loans)
        nw = a_close + ef + gb - debt
        defl = (1 + infl / 100.0) ** ((m - 1) / 12.0)

        # `capitalised` is not a cash flow — the cash already left as Goal_Outflow.
        # It is the asset arriving in exchange, so the portfolio identity needs it.
        contrib = al["sip"] + al["res"] + capitalised
        rows.append(dict(
            Month=m, Year=yr, Salary=inc["salary"], Bonus=inc["bonus"],
            Business=inc["business"], Passive=inc["passive"], Total_Income=tinc,
            Living_Expenses=exp, Lumpy_Expenses=lump, EMI_Paid=emi_tot, Interest=i_tot,
            Principal=p_tot, Prepayment=al["pre"] + al["rev"], SIP=al["sip"],
            Goal_Funding=al["goal"], EF_Topup=al["ef"], Surplus_Invested=al["res"],
            Goal_Outflow=g_out, Withdraw_Net=w_net, Withdraw_Gross=w_gross,
            Redemption_Tax=w_tax, EF_Used=ef_used, Financing_Gap=gap,
            Goal_Corpus_Used=bucket_used, Loan_Drawn=loan_drawn,
            Net_Surplus=surplus, Portfolio_Growth=a_growth, Contributions=contrib,
            Assets_Open=a_open, EF_Interest=ef_int, Goal_Growth=g_growth,
            EF_Balance=ef, Investments=a_close, Goal_Corpus=gb,
            Total_Assets=a_close + ef + gb, Total_Debt=debt, Net_Worth=nw,
            Net_Worth_Real=nw / defl,
            EMI_to_Income=(emi_tot / tinc * 100 if tinc > 0 else 0.0),
            Savings_Rate=((tinc - living - emi_tot) / tinc * 100 if tinc > 0 else 0.0)))
        wlog.append(dict(Month=m, Order=("prepay-before-SIP" if flip else "standard"),
                         SIP_Blend_RiskAdj=sip_blend,
                         Worst_LossMaking_Cost=(worst if worst else np.nan),
                         EF=al["ef"], Revolving=al["rev"], SIP=al["sip"], Goals=al["goal"],
                         Prepay=al["pre"], Residual=al["res"]))

    mon = pd.DataFrame(rows)
    ann = mon.groupby("Year").agg(
        Income=("Total_Income", "sum"), Expenses=("Living_Expenses", "sum"),
        Lumpy=("Lumpy_Expenses", "sum"), EMI=("EMI_Paid", "sum"),
        Interest=("Interest", "sum"), Principal=("Principal", "sum"),
        Prepayment=("Prepayment", "sum"), SIP=("SIP", "sum"),
        Goal_Funding=("Goal_Funding", "sum"), Goal_Outflow=("Goal_Outflow", "sum"),
        Withdrawals=("Withdraw_Net", "sum"), Redemption_Tax=("Redemption_Tax", "sum"),
        Gap=("Financing_Gap", "sum"), Investments=("Investments", "last"),
        EF=("EF_Balance", "last"), Goal_Corpus=("Goal_Corpus", "last"),
        Debt=("Total_Debt", "last"), Net_Worth=("Net_Worth", "last"),
        Net_Worth_Real=("Net_Worth_Real", "last"),
        EMI_to_Income=("EMI_to_Income", "mean"),
        Savings_Rate=("Savings_Rate", "mean")).reset_index()

    ledgers = {}
    for L in loans:
        if L.led:
            d = pd.DataFrame(L.led)
            d["Cum Interest"] = d["Interest"].cumsum()
            d["Cum Principal"] = (d["Principal"] + d["Prepayment"]).cumsum()
            ledgers[L.name] = d

    gsrc = []
    for g in goals:
        for r_ in g["srcs"]:
            gsrc.append(dict(Goal=g["name"], Year=g["years"], **r_))
    gsrc = pd.DataFrame(gsrc, columns=["Goal", "Year", "Source", "Kind", "Asset_Class",
                                       "Gross", "Tax", "Exit_Cost", "Net_Applied",
                                       "Note"])

    gout = []
    for g in goals:
        tf = (g["f_sale"] + g["f_bucket"] + g["f_ear"] + g["f_liq"] + g["f_loan"])
        # A goal dated past the horizon is never paid out, so "funded 0,
        # shortfall 0" would read as ON TRACK. Say what actually happened.
        status = ("BEYOND HORIZON" if not g["inh"]
                  else "ON TRACK" if g["short"] <= 1 else "SHORTFALL")
        gout.append(dict(Goal=g["name"], Category=g["cat"], Year=g["years"],
                         Cost_Today=g["c0"], Goal_Inflation=g["gi"], Future_Cost=g["fv"],
                         Priority=g["pri"], From_Sinking_Fund=g["f_bucket"],
                         From_Earmarked=g["f_ear"], From_Other_Assets=g["f_liq"],
                         From_Loan=g["f_loan"], From_Sale=g["f_sale"],
                         Loan_Settled_On_Sale=g["settled"], EMI_Freed=g["freed"],
                         Capitalised=g["cap"], Total_Funded=tf, Shortfall=g["short"],
                         Funded_Pct=(tf / g["fv"] * 100 if g["fv"] else 0.0),
                         In_Horizon=g["inh"], Corpus_So_Far=g["bucket"],
                         Borrowing_Refused=g["capped"], Status=status,
                         Avg_Monthly_Set_Aside=g["sunk"] / max(g["month"], 1)))

    if not dtbl.empty:
        by = {L.name: L for L in loans}
        for col, fn in (("Closes_In_Month", lambda L: L.closed_m or np.nan),
                        ("Interest_Paid_In_Plan", lambda L: L.int_paid),
                        ("Prepaid_In_Plan", lambda L: L.prepaid)):
            dtbl[col] = [fn(by[nm]) if nm in by else np.nan for nm in dtbl["Loan"]]

    nw0 = (itbl["Value"].sum() if not itbl.empty else 0.0) + sf(A["ef_current"]) \
        - (dtbl["Outstanding"].sum() if not dtbl.empty else 0.0)

    return Sim(monthly=mon, annual=ann, ledgers=ledgers, goals=gout,
               warnings=sorted(set(warn))[:60], debt=dtbl, inv=itbl, bench=bench,
               wlog=pd.DataFrame(wlog), nw0=nw0,
               nw1=(mon["Net_Worth"].iloc[-1] if not mon.empty else 0.0),
               audit=pd.DataFrame(), loans=loans, assets=assets, goal_src=gsrc)


# ================================================================== 9. AUDIT
def audit(sim: Sim, P):
    """Independent identity tests. Any deviation above Rs 1 means the engine is wrong."""
    out = []

    def add(name, dev, detail, n=None):
        out.append(dict(Test=name, Max_Deviation=dev,
                        Result=("PASS" if abs(dev) < 1.0 else "FAIL"),
                        Rows_Checked=(n if n is not None else "-"), Detail=detail))

    worst, rows = 0.0, 0
    for nm, d in sim.ledgers.items():
        e = (d["Opening"] - d["Principal"] - d["Prepayment"] - d["Closing"]).abs().max()
        worst = max(worst, float(e))
        rows += len(d)
    add("Loan ledger: Opening − Principal − Prepayment = Closing", worst,
        "Verifies every amortisation row internally balances.", rows)

    worst = 0.0
    for L in sim.loans:
        e = abs((L.opening - L.balance) - (L.prin_paid + L.prepaid))
        worst = max(worst, e)
    add("Loan totals: Opening − Closing = Principal + Prepayments", worst,
        "Verifies no principal is created or destroyed over the life of each loan.",
        len(sim.loans))

    m = sim.monthly
    if not m.empty:
        lhs = (m["Total_Income"] + m["Withdraw_Net"] + m["EF_Used"] +
               m["Goal_Corpus_Used"] + m["Loan_Drawn"] + m["Financing_Gap"])
        rhs = (m["Living_Expenses"] + m["Lumpy_Expenses"] + m["EMI_Paid"] +
               m["Prepayment"] + m["SIP"] + m["Goal_Funding"] + m["EF_Topup"] +
               m["Surplus_Invested"] + m["Goal_Outflow"])
        dev = float((lhs - rhs).abs().max())
        add("Monthly cash: inflows = outflows", dev,
            "Income + net redemptions + EF drawdown + goal corpus drawn + proceeds "
            "of any planned goal loan + unmet gap must equal every outflow, the "
            "goal payment itself included.", len(m))

        ef_open = m["EF_Balance"].shift(1)
        ef_open.iloc[0] = sf(P["assumptions"]["ef_current"])
        dev = float((ef_open + m["EF_Interest"] + m["EF_Topup"] - m["EF_Used"]
                     - m["EF_Balance"]).abs().max())
        add("Emergency fund: Open + Interest + Top-up - Drawdown = Close", dev,
            "Verifies the buffer is never credited or debited off the books.", len(m))

        gb_open = m["Goal_Corpus"].shift(1)
        gb_open.iloc[0] = 0.0
        dev = float((gb_open + m["Goal_Growth"] + m["Goal_Funding"]
                     - m["Goal_Corpus_Used"] - m["Goal_Corpus"]).abs().max())
        add("Goal corpus: Open + Growth + Funding - Drawn = Close", dev,
            "Verifies money set aside for goals is spent on those goals and "
            "nothing else.", len(m))

        exp_close = (m["Assets_Open"] + m["Portfolio_Growth"] + m["Contributions"]
                     - m["Withdraw_Gross"])
        dev = float((exp_close - m["Investments"]).abs().max())
        add("Portfolio: Open + Growth + Contributions − Redemptions = Close", dev,
            "Verifies no value leaks in or out of the investment pool.", len(m))

        dev = float((m["Investments"] + m["EF_Balance"] + m["Goal_Corpus"]
                     - m["Total_Debt"] - m["Net_Worth"]).abs().max())
        add("Net worth = Assets + EF + Goal corpus − Debt", dev,
            "Verifies the headline number is the sum of its parts.", len(m))

    worst, ng = 0.0, 0
    for g in sim.goals:
        if not g.get("In_Horizon", True):
            continue          # never falls due inside the projection
        ng += 1
        e = abs(g["Total_Funded"] + g["Shortfall"] - g["Future_Cost"])
        worst = max(worst, e)
    add("Goals: Funded + Shortfall = Inflated cost", worst,
        "Verifies every rupee of each goal falling due inside the horizon is "
        "accounted for. Goals dated beyond it are excluded - they are never paid "
        "out, and are flagged BEYOND HORIZON on the roadmap instead.", ng)

    return pd.DataFrame(out)


# ============================================ 10. OPTIMISER / ADVICE / LEVERS
def eval_swap(a_row, l_row, amount, tax: TaxConfig):
    out, rate, emi = sf(l_row["Outstanding"]), sf(l_row["RateApplied"]), sf(l_row["EMI"])
    if out <= 0 or emi <= 0:
        return None
    T = tenure_of(out, rate, emi)
    if not T:
        return None
    gf = max(0.0, (a_row["Value"] - a_row["Cost"]) / a_row["Value"]) if a_row["Value"] > 0 else 0
    tr, el = tax.gains_rate(a_row["TaxKind"]), sf(a_row["ExitLoad"]) / 100
    pen = sf(l_row["Penalty"]) / 100
    fr = min(gf * tr + el, 0.85)
    gross = min(amount / (1 - fr), a_row["Value"])
    net = gross * (1 - fr)
    killed = net / (1 + pen)
    ra = mrate(a_row["RiskAdj"])
    base = a_row["Value"] * (1 + ra) ** T
    rem = out - killed
    if rem <= 0:
        T2, i_new = 0, 0.0
    else:
        T2, i_new = run_off(rem, rate, emi)
    _, i_old = run_off(out, rate, emi)
    freed = sum(emi * (1 + ra) ** (T - k) for k in range(T2 + 1, T + 1))
    after = (a_row["Value"] - gross) * (1 + ra) ** T + freed
    return dict(Asset=a_row["Investment"], Loan=l_row["Loan"], Redeem_Gross=gross,
                Net_To_Loan=net, Tax_And_Load=gross * fr, Penalty=net - killed,
                Principal_Killed=killed, Interest_Saved=i_old - i_new,
                Months_Saved=T - T2, Tenure_Before=T, Tenure_After=T2,
                Wealth_Delta=after - base, Loan_Cost=l_row["EffectiveCost"],
                Asset_Return=a_row["RiskAdj"],
                Verdict=("DO IT" if after > base else "DON'T"))


def optimise(sim: Sim, P):
    tax, A = P["_tax"], P["assumptions"]
    iv, dt = sim.inv, sim.debt
    if iv.empty or dt.empty:
        return pd.DataFrame()
    mexp = float(sim.monthly["Living_Expenses"].iloc[0]) if not sim.monthly.empty else 0.0
    ef_need = max(sf(A["ef_target_months"]) * mexp - sf(A["ef_current"]), 0.0)
    pool = iv[iv["Deployable"]].copy()
    if pool.empty:
        return pd.DataFrame()
    locked = {L.linked for L in sim.loans if L.linked}
    pool = pool[~pool["Investment"].isin(locked)]
    if pool.empty:
        return pd.DataFrame()
    budget = max(pool["Value"].sum() * sf(A["liquid_deploy_cap"]) / 100 - ef_need, 0.0)
    # A holding can only be sold once. Without this the same asset was offered
    # against several loans and the table double-counted it.
    remain = {r["Investment"]: float(r["Value"]) for _, r in pool.iterrows()}
    res = []
    for _, L in dt.sort_values("EffectiveCost", ascending=False).iterrows():
        if budget <= 0:
            break
        if L["Verdict"] == V_GOOD and not sb(A["allow_prepay_healthy"]):
            continue
        for _, Aq in pool.sort_values("RiskAdj").iterrows():
            if budget <= 0:
                break
            amt = min(budget, remain.get(Aq["Investment"], 0.0),
                      L["Outstanding"] * 1.02)
            if amt < 5000:
                continue
            e = eval_swap(Aq, L, amt, tax)
            if e:
                e["Spread_vs_Loan"] = Aq["RiskAdj"] - L["EffectiveCost"]
                e["Liquidity"] = Aq["LiquidityScore"]
                res.append(e)
                if e["Wealth_Delta"] > 0:
                    budget -= amt
                    remain[Aq["Investment"]] = max(
                        remain[Aq["Investment"]] - e["Redeem_Gross"], 0.0)
    d = pd.DataFrame(res)
    return d.sort_values("Wealth_Delta", ascending=False) if not d.empty else d


def advice(sim: Sim, P, swaps):
    A = P["assumptions"]
    R, dt, iv, mon, b = [], sim.debt, sim.inv, sim.monthly, sim.bench

    def add(p, area, title, detail, q="-"):
        R.append(dict(Priority=p, Area=area, Title=title, Detail=detail, Quantified=q))

    if dt.empty:
        add(1, "Debt", "No debt on record",
            "Nothing to restructure. Direct attention to goal funding and keeping the "
            "emergency fund at target.")
    for _, r in dt[dt["Verdict"] == V_BAD].iterrows() if not dt.empty else ():
        add(1, "Loss-making debt", f"Retire '{r['Loan']}' ahead of schedule",
            f"Effective post-tax cost is {r['EffectiveCost']:.2f}% against a marginal "
            f"risk-adjusted return of {r['Benchmark']:.2f}% over this loan's remaining "
            f"{r['DecisionYears']:.0f} years — a negative spread of {r['Spread']:.2f}%. "
            f"Every rupee left outstanding destroys roughly {abs(r['Spread']):.2f}% of "
            f"value a year. Real cost after {A['inflation']:.1f}% inflation is "
            f"{r['RealCost']:.2f}%.",
            f"Interest still payable {compact(r['InterestRemaining'])} "
            f"({r['IntToPrin']:.0f}% of the outstanding)")
    for _, r in (dt.iterrows() if not dt.empty else ()):
        if r["Rate"] - r["MarketRate"] >= sf(A["bt_threshold"]):
            n = max(si(r["MonthsLeft"]), 1)
            save = (r["EMI"] - emi_of(r["Outstanding"], r["MarketRate"], n)) * n
            add(2, "Repricing", f"Reprice or transfer '{r['Loan']}'",
                f"You pay {r['Rate']:.2f}% where the prevailing benchmark for this product "
                f"is about {r['MarketRate']:.2f}%. Ask your existing lender for a rate reset "
                f"first — it costs a small fee and no paperwork. Move only if refused.",
                f"Indicative lifetime saving {compact(save)}")
    uns = dt[(dt["Security"] == "Unsecured") & (dt["EffectiveCost"] > b)] \
        if not dt.empty else dt
    if len(uns) >= 2:
        w = float(np.average(uns["EffectiveCost"], weights=uns["Outstanding"]))
        sec = min(DEBT_TYPES[k]["mkt"] for k in
                  ("Loan Against Property", "Loan Against Securities", "Gold Loan"))
        add(2, "Consolidation",
            f"Consolidate {len(uns)} unsecured loans into one secured facility",
            f"Weighted effective cost of the unsecured stack is {w:.2f}%; a secured "
            f"facility runs near {sec:.2f}%. It also collapses several EMI dates into one, "
            f"cutting the risk of a missed payment. The trade-off is real: you convert "
            f"unsecured exposure into a charge on an asset, so only do this if your income "
            f"is stable.",
            f"On {compact(uns['Outstanding'].sum())}, annual interest saving around "
            f"{compact(uns['Outstanding'].sum() * (w - sec) / 100)}")
    rev = dt[dt["Revolving"].astype(bool)] if not dt.empty else dt
    if not rev.empty:
        add(1, "Revolving credit", "Clear revolving balances before anything else",
            "Card and BNPL balances compound monthly at rates no portfolio beats after "
            "tax. The engine already forces these to the front of the waterfall. As an "
            "interim step, converting the balance to a fixed-tenure EMI or a personal loan "
            "typically halves the rate.",
            f"Balance {compact(rev['Outstanding'].sum())} at up to "
            f"{rev['EffectiveCost'].max():.1f}% effective")
    for _, r in (dt[dt["Verdict"] == V_GOOD].iterrows() if not dt.empty else ()):
        add(4, "Healthy leverage", f"Do NOT prepay '{r['Loan']}'",
            f"Effective cost {r['EffectiveCost']:.2f}% sits below the "
            f"{r['Benchmark']:.2f}% your money can earn over this loan's remaining "
            f"{r['DecisionYears']:.0f} years, a spread of +{r['Spread']:.2f}%. Prepaying "
            f"converts positive carry into a zero return. Keep the tenure and invest the "
            f"difference.",
            f"Value of retaining roughly "
            f"{compact(r['Outstanding'] * r['Spread'] / 100)} a year")
    if swaps is not None and not swaps.empty:
        for _, s in swaps[swaps["Wealth_Delta"] > 0].head(5).iterrows():
            add(2, "Asset to debt swap",
                f"Redeem '{s['Asset']}' to part-prepay '{s['Loan']}'",
                f"The loan costs {s['Loan_Cost']:.2f}% post-tax while the asset is expected "
                f"to earn only {s['Asset_Return']:.2f}% risk-adjusted post-tax. Redeeming "
                f"{compact(s['Redeem_Gross'])} gross loses {compact(s['Tax_And_Load'])} to "
                f"tax and exit load, leaving {compact(s['Net_To_Loan'])} for the loan.",
                f"Interest saved {compact(s['Interest_Saved'])}; tenure cut "
                f"{si(s['Months_Saved'])} months; terminal wealth "
                f"+{compact(s['Wealth_Delta'])}")
    if not mon.empty:
        pk = mon["EMI_to_Income"].max()
        if pk > sf(A["emi_income_ceiling"]):
            add(1, "Debt capacity",
                f"EMI-to-income peaks at {pk:.0f}%, above your {sf(A['emi_income_ceiling']):.0f}% ceiling",
                "At this level one income shock forces asset sales at the worst possible "
                "moment. Lengthen tenure on the cheapest secured loan to buy cashflow room, "
                "or defer the discretionary goal that triggers the borrowing.",
                f"Peak occurs in month {si(mon['EMI_to_Income'].idxmax()) + 1}")
        if mon["Financing_Gap"].sum() > 0:
            add(1, "Liquidity", "The plan runs into a financing gap",
                "In at least one month, income plus accessible assets cannot meet outgo. "
                "Fix the sequencing rather than the total: defer or downsize the nearest "
                "goal, raise the emergency fund, or arrange a standby credit line before "
                "you need it.",
                f"Total gap {compact(mon['Financing_Gap'].sum())}")
        need = sf(A["ef_target_months"]) * mon["Living_Expenses"].iloc[0]
        if mon["EF_Balance"].iloc[-1] < need:
            add(2, "Emergency fund", "Emergency fund finishes below target",
                f"Target is {sf(A['ef_target_months']):.0f} months of expenses "
                f"({compact(need)}). This is the cheapest insurance you can buy against "
                f"being forced to liquidate growth assets or revolve on a card.",
                f"Shortfall {compact(need - mon['EF_Balance'].iloc[-1])}")
        rt = mon["Redemption_Tax"].sum()
        if rt > 0:
            add(3, "Tax", "Redemption tax is a real cost in this plan",
                "Capital gains tax and exit loads on the redemptions the plan requires are "
                "shown below. Staggering redemptions across financial years to use the "
                "annual equity exemption more than once can reduce this materially.",
                f"Total modelled redemption tax {compact(rt)}")
    iv = iv[~iv["Personal"].astype(bool)] if not iv.empty else iv
    if not iv.empty:
        il = iv[iv["LiquidityScore"] <= 2]["Value"].sum()
        tt = iv["Value"].sum()
        if tt > 0 and il / tt > sf(A["illiquid_warn_pct"]) / 100:
            add(3, "Portfolio liquidity", f"{il/tt*100:.0f}% of the portfolio is illiquid",
                "Illiquid assets cannot defend you in a cash crunch and cannot retire "
                "expensive debt. Build the liquid sleeve before adding further to locked "
                "or physical assets.",
                f"Illiquid {compact(il)} of {compact(tt)}")
    d = pd.DataFrame(R)
    return d.sort_values("Priority") if not d.empty else d


def levers(sim: Sim, P):
    A = P["assumptions"]
    r = mrate(A["goal_vehicle_return"])
    out = []
    for g in sim.goals:
        if g["Status"] != "SHORTFALL":
            out.append(dict(Goal=g["Goal"], Status=g["Status"], Extra_SIP=0.0,
                            Delay_Years=0.0, Cost_Cut_Pct=0.0, Freed_EMI_Cover="-"))
            continue
        n = max(si(g["Year"]) * 12, 1)
        sh = g["Shortfall"]
        extra = sh * r / ((1 + r) ** n - 1) if r > 0 else sh / n
        have = g["Total_Funded"]
        # Deferring only closes the gap if the corpus compounds FASTER than the
        # goal inflates. Measuring growth against a frozen cost understated the
        # delay, and reported a cure for goals where deferral never catches up.
        gi = sf(g["Goal_Inflation"]) / 100.0
        den = 12.0 * math.log(1 + r) - math.log(1 + gi) if r > 0 else 0.0
        delay = (math.log(g["Future_Cost"] / have) / den
                 if have > 0 and den > 0 else float("nan"))
        freed = 0.0
        if not sim.debt.empty:
            for _, L in sim.debt.iterrows():
                cm = L.get("Closes_In_Month")
                if pd.notna(cm) and cm < g["Year"] * 12:
                    k = g["Year"] * 12 - si(cm)
                    freed += L["EMI"] * (((1 + r) ** k - 1) / r if r > 0 else k)
        out.append(dict(Goal=g["Goal"], Status="SHORTFALL", Extra_SIP=extra,
                        Delay_Years=(round(max(delay, 0.0), 2) if np.isfinite(delay) else np.nan),
                        Cost_Cut_Pct=round(sh / g["Future_Cost"] * 100, 1),
                        Freed_EMI_Cover=(f"{min(freed/sh*100, 999):.0f}% of the gap"
                                         if freed > 0 else "nil")))
    return pd.DataFrame(out)


# ================================================= 11. EXCEL TEMPLATE / PARSE
def template_bytes(P=None):
    P = P or demo()
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        wb = xw.book
        f_t = wb.add_format(dict(bold=True, font_size=15, font_color="#0b3c49"))
        f_h = wb.add_format(dict(bold=True, bg_color="#0b3c49", font_color="white",
                                 border=1, text_wrap=True, valign="vcenter"))
        f_n = wb.add_format(dict(italic=True, font_size=9, font_color="#4a6a72",
                                 text_wrap=True, valign="top", border=1,
                                 bg_color="#eef6f7"))
        f_c = wb.add_format(dict(border=1))
        f_m = wb.add_format(dict(border=1, num_format=XL_INR))
        f_p = wb.add_format(dict(border=1, num_format="0.00"))
        f_w = wb.add_format(dict(text_wrap=True, valign="top"))

        ws = wb.add_worksheet("READ ME")
        ws.set_column(0, 0, 110)
        ws.write(0, 0, "Personal Finance & Debt Impact Calculator — input template", f_t)
        for i, line in enumerate([
            "",
            "HOW TO USE",
            "1. Every sheet below is pre-filled with a worked demo so you can see the shape "
            "of the data.",
            "2. Overwrite the demo rows with your own. Delete any rows you do not need. Add "
            "as many as you like.",
            "3. Row 3 of each sheet is a grey NOTES row explaining every column. You may "
            "leave it or delete it — the app recognises it by its content and will "
            "not mistake one of your rows for it.",
            "4. Do not rename sheets or column headers. The app matches on them exactly.",
            "5. Columns with a dropdown (Loan Type, Asset Class, Category, and so on) "
            "only accept the listed options. Typed-in text is not recognised.",
            "6. Save, then upload the file in the app under Start & Data Entry.",
            "",
            "RULES THAT MATTER",
            "• Enter POST-TAX, in-hand figures for salary and business income.",
            "• Do NOT include EMIs in the Expenses sheet — the debt engine handles them, and "
            "including them double-counts.",
            "• Goal costs go in TODAY's money. The engine inflates them at the rate you give.",
            "• Loan outstanding is what you owe today, not the original sanction.",
            "• Names must be unique. Goals and loans reference investments by their exact name.",
            "",
            "The Field Guide sheet lists every column with its full explanation.",
        ]):
            ws.write(i + 1, 0, line, f_w)

        guide = []
        for key, spec in SCHEMA.items():
            for c in spec["cols"]:
                guide.append(dict(Sheet=spec["label"], Column=c["k"],
                                  Type=c["t"], Explanation=c["help"]))
        for k, lbl, t, h in ASSUMPTION_FIELDS:
            guide.append(dict(Sheet="Assumptions", Column=lbl, Type=t, Explanation=h))
        for k, lbl, t, h in TAX_FIELDS:
            guide.append(dict(Sheet="Tax", Column=lbl, Type=t, Explanation=h))
        for k, lbl, t, h in INCOME_FIELDS:
            guide.append(dict(Sheet="Income", Column=lbl, Type=t, Explanation=h))
        g = pd.DataFrame(guide)
        g.to_excel(xw, sheet_name="Field Guide", index=False, startrow=1)
        wsg = xw.sheets["Field Guide"]
        wsg.write(0, 0, "Field guide — what every input means", f_t)
        for j, c in enumerate(g.columns):
            wsg.write(1, j, c, f_h)
        wsg.set_column(0, 0, 22)
        wsg.set_column(1, 1, 32)
        wsg.set_column(2, 2, 10)
        wsg.set_column(3, 3, 105, f_w)
        wsg.freeze_panes(2, 0)

        wsl = wb.add_worksheet("Lists")
        wsl.hide()
        _ranges, _col = {}, 0
        for _opts in [c["opts"] for spec in SCHEMA.values() for c in spec["cols"]
                      if c["t"] == "select" and c["opts"]] + [["TRUE", "FALSE"]]:
            _key = tuple(_opts)
            if _key in _ranges:
                continue
            wsl.write(0, _col, "options")
            for _i, _o in enumerate(_opts):
                wsl.write(_i + 1, _col, _o)
            _a = xl_col_to_name(_col)
            _ranges[_key] = f"=Lists!${_a}$2:${_a}${len(_opts) + 1}"
            _col += 1

        for key, spec in SCHEMA.items():
            df = P[key]
            cols = [c["k"] for c in spec["cols"]]
            df = df.reindex(columns=cols) if not df.empty else pd.DataFrame(columns=cols)
            sh = xl_sheet(spec["label"])
            wsx = wb.add_worksheet(sh)
            wsx.write(0, 0, f"{spec['label']} — {spec['intro']}", f_w)
            wsx.set_row(0, 34)
            for j, c in enumerate(spec["cols"]):
                wsx.write(1, j, c["k"], f_h)
                wsx.write(2, j, c["help"], f_n)
                fmt = f_m if c["t"] == "money" else f_p if c["t"] == "pct" else f_c
                wsx.set_column(j, j, max(15, min(len(c["k"]) + 6, 30)), fmt)
                if c["t"] == "select" and c["opts"]:
                    wsx.data_validation(3, j, 400, j, dict(
                        validate="list", source=_ranges[tuple(c["opts"])],
                        error_title="Pick from the list",
                        error_message="This column only accepts one of the listed "
                                      "options. Anything else is not recognised by "
                                      "the engine."))
                if c["t"] == "bool":
                    wsx.data_validation(3, j, 400, j, dict(
                        validate="list", source=_ranges[("TRUE", "FALSE")]))
            wsx.set_row(2, 46)
            for i, (_, r) in enumerate(df.iterrows()):
                for j, c in enumerate(spec["cols"]):
                    v = r.get(c["k"])
                    if pd.isna(v):
                        v = "" if c["t"] == "text" else 0
                    if c["t"] == "bool":
                        v = "TRUE" if sb(v) else "FALSE"
                    wsx.write(3 + i, j, v)
            wsx.freeze_panes(3, 1)

        def kv(sheet, fields, src, title):
            rows = [dict(Parameter=lbl, Value=src.get(k, ""), Guidance=h)
                    for k, lbl, t, h in fields]
            d = pd.DataFrame(rows)
            d.to_excel(xw, sheet_name=sheet, index=False, startrow=1)
            w = xw.sheets[sheet]
            w.write(0, 0, title, f_t)
            for j, c in enumerate(d.columns):
                w.write(1, j, c, f_h)
            w.set_column(0, 0, 38)
            w.set_column(1, 1, 18, f_c)
            w.set_column(2, 2, 100, f_w)
            w.freeze_panes(2, 0)

        kv("Assumptions", ASSUMPTION_FIELDS, P["assumptions"],
           "Assumptions — edit the Value column only")
        kv("Tax", TAX_FIELDS, P["tax"], "Tax settings — edit the Value column only")
        inc_rows = []
        for who, lbl in (("primary", "Earner 1"), ("secondary", "Earner 2 / Spouse")):
            for k, l, t, h in INCOME_FIELDS:
                inc_rows.append(dict(Parameter=f"{lbl} — {l}",
                                     Value=P["income"][who].get(k, ""), Guidance=h))
        d = pd.DataFrame(inc_rows)
        d.to_excel(xw, sheet_name="Income", index=False, startrow=1)
        w = xw.sheets["Income"]
        w.write(0, 0, "Income — POST-TAX figures only", f_t)
        for j, c in enumerate(d.columns):
            w.write(1, j, c, f_h)
        w.set_column(0, 0, 42)
        w.set_column(1, 1, 18, f_c)
        w.set_column(2, 2, 95, f_w)
        w.freeze_panes(2, 0)
    return buf.getvalue()


@st.cache_data(show_spinner=False)
def demo_template_bytes():
    """The blank demo template never changes within a session. Rebuilding a
    full workbook on every rerun of the Start page was pure waste."""
    return template_bytes(demo())


def _is_notes_row(row, spec):
    """True when this row is the template's grey guidance row rather than data.
    It is identified by its cells matching the column help text."""
    hits = 0
    for c in spec["cols"]:
        v = row.get(c["k"])
        if isinstance(v, str) and v.strip() and v.strip()[:40] == c["help"][:40]:
            hits += 1
    return hits >= 2


def parse_workbook(data):
    """Read an uploaded template back into a profile. Returns (profile, messages)."""
    msg = []
    P = blank()
    xl = pd.ExcelFile(io.BytesIO(data))
    for key, spec in SCHEMA.items():
        sh = xl_sheet(spec["label"])
        if sh not in xl.sheet_names:
            msg.append(f"Sheet '{sh}' not found — left empty.")
            continue
        df = pd.read_excel(xl, sheet_name=sh, header=1)
        # The template puts a grey NOTES row directly under the header. Dropping
        # row 1 unconditionally silently ate the user's FIRST DATA ROW whenever
        # they had deleted those notes. Recognise the row by its content instead.
        dropped = not df.empty and _is_notes_row(df.iloc[0], spec)
        if dropped:
            df = df.iloc[1:]
        cols = [c["k"] for c in spec["cols"]]
        missing = [c for c in cols if c not in df.columns]
        if missing:
            msg.append(f"'{sh}': missing columns {missing} — filled with defaults.")
        df = df.reindex(columns=cols)
        df = df.dropna(how="all")
        seedable = _SEEDABLE.get(key, ())
        for c in spec["cols"]:
            if c["k"] not in df.columns:
                continue
            if c["k"] in seedable:
                # Leave blanks as NaN so the asset-class default can seed them,
                # which is what the field guide promises.
                df[c["k"]] = pd.to_numeric(df[c["k"]], errors="coerce")
            elif c["t"] in ("money", "pct", "num"):
                df[c["k"]] = pd.to_numeric(df[c["k"]], errors="coerce").fillna(0.0)
            elif c["t"] == "int":
                df[c["k"]] = pd.to_numeric(df[c["k"]], errors="coerce").fillna(0).astype(int)
            elif c["t"] == "bool":
                df[c["k"]] = df[c["k"]].map(sb)
            else:
                df[c["k"]] = df[c["k"]].fillna("").astype(str).str.strip()
        keycol = spec["cols"][0]["k"]
        df = df[df[keycol].astype(str).str.strip() != ""]
        P[key] = df.reset_index(drop=True)
        msg.append(f"'{sh}': {len(df)} rows loaded.")
        if dropped:
            msg.append(f"   ('{sh}': the grey notes row was recognised and skipped.)")

    def read_kv(sheet, fields, target, prefix_map=None):
        if sheet not in xl.sheet_names:
            msg.append(f"Sheet '{sheet}' not found — defaults kept.")
            return
        d = pd.read_excel(xl, sheet_name=sheet, header=1)
        if "Parameter" not in d.columns or "Value" not in d.columns:
            msg.append(f"'{sheet}': Parameter/Value columns not found.")
            return
        look = {str(a).strip(): b for a, b in zip(d["Parameter"], d["Value"])}
        if prefix_map:
            for who, lbl in prefix_map:
                for k, l, t, h in fields:
                    v = look.get(f"{lbl} — {l}")
                    if v is None or (isinstance(v, float) and pd.isna(v)):
                        continue
                    target[who][k] = sb(v) if t == "bool" else \
                        si(v) if t == "int" else sf(v) if t in ("money", "pct", "num") else str(v)
        else:
            for k, l, t, h in fields:
                v = look.get(l)
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    continue
                target[k] = sb(v) if t == "bool" else si(v) if t == "int" else \
                    sf(v) if t in ("money", "pct", "num") else str(v).strip()

    read_kv("Assumptions", ASSUMPTION_FIELDS, P["assumptions"])
    read_kv("Tax", TAX_FIELDS, P["tax"])
    read_kv("Income", INCOME_FIELDS, P["income"],
            prefix_map=[("primary", "Earner 1"), ("secondary", "Earner 2 / Spouse")])
    return P, msg


# ============================================================ 12. VALIDATION
def validate(P):
    out = []

    def add(sev, where, m):
        out.append(dict(Severity=sev, Where=where, Message=m))

    A = P["assumptions"]
    inc = P["income"]
    tot_inc = sum(sf(inc[w].get("monthly_inhand")) + sf(inc[w].get("business_monthly"))
                  for w in ("primary", "secondary") if sb(inc[w].get("enabled")))
    if tot_inc <= 0:
        add("BLOCKER", "Income", "No monthly income entered — the projection cannot run.")
    exp = P["expenses"]
    if exp.empty or pd.to_numeric(exp.get("Monthly Amount"), errors="coerce").fillna(0).sum() <= 0:
        add("WARNING", "Expenses", "No expenses entered. A plan with zero expenses will "
                                   "overstate your surplus dramatically.")
    for _, r in P["lumpy"].iterrows():
        mo = si(r.get("Month of Year"))
        if not (1 <= mo <= 12):
            add("WARNING", "Annual & Lumpy Expenses",
                f"'{str(r.get('Item', '')).strip()}': month of year is {mo}, outside "
                f"1-12. The engine will treat it as January, so the cashflow spike "
                f"lands in the wrong month.")
    for who, lbl in (("primary", "Earner 1"), ("secondary", "Earner 2 / Spouse")):
        b = inc.get(who, {})
        if not sb(b.get("enabled")):
            continue
        for k, nm in (("bonus_month", "bonus month"),
                      ("increment_month", "increment month")):
            v = si(b.get(k))
            if not (1 <= v <= 12):
                add("WARNING", "Income",
                    f"{lbl}: {nm} is {v}, outside 1-12. The engine will use April.")
    inv = P["investments"]
    if not inv.empty:
        names = inv["Investment Name"].astype(str).str.strip()
        dup = names[names.duplicated()].unique().tolist()
        if dup:
            add("BLOCKER", "Investments", f"Duplicate investment names: {dup}. Names must "
                                          f"be unique — goals reference them.")
        bad = inv[pd.to_numeric(inv["Invested Cost"], errors="coerce").fillna(0) >
                  pd.to_numeric(inv["Current Value"], errors="coerce").fillna(0) * 3]
        for _, r in bad.iterrows():
            add("WARNING", "Investments",
                f"'{r['Investment Name']}': invested cost is far above current value. "
                f"Check the figures — this suppresses capital-gains tax in the model.")
        for _, r in inv.iterrows():
            if sf(r["Expected Return % p.a."]) > 20:
                add("WARNING", "Investments",
                    f"'{r['Investment Name']}': {sf(r['Expected Return % p.a.']):.1f}% "
                    f"expected return is aggressive. Everything downstream inherits this.")
    debts = P["debts"]
    if not debts.empty:
        dn = debts["Loan / Lender"].astype(str).str.strip()
        dup = dn[dn.duplicated()].unique().tolist()
        if dup:
            add("BLOCKER", "Debts", f"Duplicate loan names: {dup}.")
        for _, r in debts.iterrows():
            lt = str(r.get("Loan Type", ""))
            meta = DEBT_TYPES.get(lt)
            out_p, emi = sf(r["Outstanding Principal"]), sf(r["EMI"])
            rate = sf(r["Interest Rate % p.a."])
            rem = si(r["Remaining Tenure (months)"])
            if meta and not meta["rev"]:
                if emi <= 0 and rem <= 0:
                    add("BLOCKER", "Debts", f"'{r['Loan / Lender']}': needs either an EMI "
                                            f"or a remaining tenure.")
                if emi > 0 and out_p > 0 and emi <= out_p * lrate(rate):
                    add("BLOCKER", "Debts",
                        f"'{r['Loan / Lender']}': the EMI of {money(emi)} does not even "
                        f"cover monthly interest of {money(out_p * lrate(rate))}. The "
                        f"balance would grow forever.")
            if rate <= 0:
                add("WARNING", "Debts", f"'{r['Loan / Lender']}': zero interest rate.")
            li = str(r.get("Linked Investment (collateral)", "") or "").strip()
            if li and (inv.empty or li not in set(inv["Investment Name"].astype(str))):
                add("WARNING", "Debts", f"'{r['Loan / Lender']}': linked investment '{li}' "
                                        f"does not match any investment name.")
    for key, col, allowed in (("debts", "Loan Type", DEBT_TYPES),
                              ("investments", "Asset Class", ASSET_CLASSES),
                              ("expenses", "Category", EXP_CATS),
                              ("goals", "Category", GOAL_CATS)):
        d = P[key]
        if d.empty or col not in d.columns:
            continue
        for v in sorted({str(x).strip() for x in d[col] if str(x).strip()}):
            if v not in allowed:
                add("BLOCKER" if key in ("debts", "investments") else "WARNING",
                    SCHEMA[key]["label"],
                    f"'{col}' contains '{v}', which is not one of the recognised "
                    f"options. Pick from the dropdown — free text is not understood "
                    f"and the engine would silently fall back to a default.")

    goals = P["goals"]
    if not goals.empty:
        gn = set(goals["Goal Name"].astype(str).str.strip())
        for _, r in goals.iterrows():
            if si(r["Target Year (from now)"]) > si(A["horizon_years"]):
                add("WARNING", "Goals", f"'{r['Goal Name']}' falls in year "
                                        f"{si(r['Target Year (from now)'])}, beyond the "
                                        f"{si(A['horizon_years'])}-year horizon. It will not "
                                        f"be funded in this run.")
            e = str(r.get("Earmarked Investment", "") or "").strip()
            if e and (inv.empty or e not in set(inv["Investment Name"].astype(str))):
                add("BLOCKER", "Goals", f"'{r['Goal Name']}': earmarked investment '{e}' "
                                        f"does not exist.")
            sl = str(r.get("Sell to Fund (asset name)", "") or "").strip()
            if sl:
                if inv.empty or sl not in set(inv["Investment Name"].astype(str)):
                    add("BLOCKER", "Goals",
                        f"'{r['Goal Name']}': 'Sell to Fund' names '{sl}', which is not "
                        f"one of your investments. Add it as a holding first — that is "
                        f"how the engine knows what it is worth and what loan sits "
                        f"against it.")
                elif not P["debts"].empty:
                    linked = P["debts"][P["debts"]["Linked Investment (collateral)"]
                                        .astype(str).str.strip() == sl]
                    if linked.empty:
                        secured = P["debts"][P["debts"]["Secured?"].map(sb)]
                        if not secured.empty:
                            add("NOTE", "Goals",
                                f"'{r['Goal Name']}': '{sl}' will be sold, but no loan "
                                f"lists it under 'Linked Investment (collateral)'. If a "
                                f"loan is secured on it, set that link or the loan will "
                                f"keep running after the asset is gone.")
            bc = str(r.get("Becomes Asset (class)", "") or "").strip()
            if bc and bc not in ASSET_CLASSES:
                add("BLOCKER", "Goals",
                    f"'{r['Goal Name']}': 'Becomes Asset (class)' is '{bc}', which is "
                    f"not a recognised asset class.")
            if not bc and str(r.get("Category", "")) in ("House Purchase",
                                                         "Vehicle Purchase"):
                add("WARNING", "Goals",
                    f"'{r['Goal Name']}' buys an asset but 'Becomes Asset (class)' is "
                    f"blank, so the money spent will vanish from your balance sheet "
                    f"instead of becoming something you own.")
            if sf(r["% From Own Corpus"]) < 100 and (sf(r["If Loan: Rate %"]) <= 0 or
                                                     si(r["If Loan: Tenure (yrs)"]) <= 0):
                add("WARNING", "Goals", f"'{r['Goal Name']}' is partly financed but has no "
                                        f"loan rate/tenure. It will be treated as fully "
                                        f"self-funded.")
        if not inv.empty:
            for _, r in inv.iterrows():
                e = str(r.get("Earmarked for Goal", "") or "").strip()
                if e and e not in gn:
                    add("WARNING", "Investments",
                        f"'{r['Investment Name']}' is earmarked for '{e}', which is not a "
                        f"goal name. It will be ring-fenced but never used.")
    dv = str(A.get("default_vehicle", "")).strip()
    if not inv.empty and dv and dv not in set(inv["Investment Name"].astype(str)):
        add("WARNING", "Assumptions", f"Residual surplus vehicle '{dv}' is not an investment "
                                      f"name. The highest-return unprotected holding will be "
                                      f"used instead.")
    if sf(A["risk_aversion"]) == 0:
        add("NOTE", "Assumptions", "Risk aversion is 0, so volatile equity competes with "
                                   "guaranteed loan savings on equal terms. This biases the "
                                   "engine towards keeping debt.")
    if str(P["tax"]["regime"]).lower().startswith("new"):
        add("NOTE", "Tax", "Under the new regime the engine applies no Section 24b shield to "
                           "a self-occupied home loan and no 80E on education loans, so their "
                           "effective cost equals the headline rate.")
    return pd.DataFrame(out)


# ================================================================== 13. EXCEL REPORT
def report_bytes(P, sim: Sim, swaps, recs, lev, aud):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        wb = xw.book
        F = dict(
            t=wb.add_format(dict(bold=True, font_size=15, font_color="#0b3c49")),
            h=wb.add_format(dict(bold=True, bg_color="#0b3c49", font_color="white",
                                 border=1, text_wrap=True, valign="vcenter")),
            m=wb.add_format(dict(num_format=XL_INR, border=1)),
            p=wb.add_format(dict(num_format='0.00"%"', border=1)),
            w=wb.add_format(dict(border=1, text_wrap=True, valign="top")),
            good=wb.add_format(dict(bg_color="#c6efce", font_color="#006100", border=1)),
            bad=wb.add_format(dict(bg_color="#ffc7ce", font_color="#9c0006", border=1)),
            warn=wb.add_format(dict(bg_color="#ffeb9c", font_color="#9c6500", border=1)))

        def put(df, sheet, mcols=(), pcols=(), width=16, wrap=()):
            sheet = xl_sheet(sheet)
            if df is None or df.empty:
                df = pd.DataFrame({"(no data)": []})
            df.to_excel(xw, sheet_name=sheet, index=False, startrow=1)
            ws = xw.sheets[sheet]
            ws.write(0, 0, sheet, F["t"])
            for j, c in enumerate(df.columns):
                ws.write(1, j, str(c), F["h"])
                fmt = F["m"] if c in mcols else F["p"] if c in pcols else \
                    F["w"] if c in wrap else None
                w = 60 if c in wrap else max(width, min(len(str(c)) + 4, 40))
                ws.set_column(j, j, w, fmt)
            ws.freeze_panes(2, 1)
            if len(df):
                ws.autofilter(1, 0, 1 + len(df), max(len(df.columns) - 1, 0))
            return ws

        A, tx = P["assumptions"], P["_tax"]
        cover = pd.DataFrame([
            ("Report", APP), ("Version", VER), ("Generated", date.today().isoformat()),
            ("Profile", A.get("profile_name", "-")),
            ("Horizon (years)", A["horizon_years"]),
            ("Headline inflation %", A["inflation"]),
            ("Tax regime", tx.regime), ("Marginal rate %", tx.marginal_rate),
            ("Equity LTCG % / annual exemption",
             f"{tx.equity_ltcg} / {money(tx.equity_ltcg_exempt)}"),
            ("Debt shields applied", tx.apply_debt_shields),
            ("Risk-aversion coefficient", A["risk_aversion"]),
            ("Marginal benchmark return %", round(sim.bench, 2)),
            ("Healthy band", f"spread above +{BAND_HI}%"),
            ("Loss-making band", f"spread below {BAND_LO}%"),
            ("EF target (months)", A["ef_target_months"]),
            ("Liquid deploy cap %", A["liquid_deploy_cap"]),
            ("EMI-to-income ceiling %", A["emi_income_ceiling"]),
            ("Prepayment mode", A["prepay_mode"]),
            ("Waterfall rule", "Loss-making debt is prepaid BEFORE SIPs in any month where "
                               "the blended SIP risk-adjusted return is below the worst "
                               "loss-making loan's effective cost"),
            ("Opening net worth", round(sim.nw0)),
            ("Closing net worth (nominal)", round(sim.nw1)),
            ("Closing net worth (today's money)",
             round(sim.monthly["Net_Worth_Real"].iloc[-1]) if not sim.monthly.empty else 0),
            ("Audit tests passed",
             f"{(aud['Result'] == 'PASS').sum()} of {len(aud)}" if not aud.empty else "-"),
        ], columns=["Parameter", "Value"])
        put(cover, "01 Cover", width=36, wrap=("Value",))

        put(aud, "02 Audit", width=18, wrap=("Detail",))

        r0 = 1
        ws = wb.add_worksheet("03 Inputs")
        ws.write(0, 0, "INPUT SHEET", F["t"])
        for key, spec in SCHEMA.items():
            ws.write(r0, 0, spec["label"], F["h"])
            r0 += 1
            d = P[key]
            if d.empty:
                ws.write(r0, 0, "(none)")
                r0 += 2
                continue
            d.to_excel(xw, sheet_name="03 Inputs", index=False, startrow=r0)
            r0 += len(d) + 3
        ws.set_column(0, 30, 20)

        if not sim.debt.empty:
            d = sim.debt.copy()
            ws = put(d, "04 Debt Diagnostics",
                     mcols=("Outstanding", "EMI", "InterestRemaining",
                            "Interest_Paid_In_Plan", "Prepaid_In_Plan"),
                     pcols=("Rate", "RateApplied", "EffectiveCost", "RealCost", "Spread",
                            "Benchmark", "MarketRate", "IntToPrin", "Penalty", "MinDue",
                            "DecisionYears"),
                     wrap=("EngineNote",))
            vc, n = list(d.columns).index("Verdict"), len(d)
            for val, fmt in ((V_BAD, F["bad"]), (V_GOOD, F["good"]), (V_NEUT, F["warn"])):
                ws.conditional_format(2, vc, 1 + n, vc, dict(
                    type="text", criteria="containing", value=val, format=fmt))
            sc = list(d.columns).index("Spread")
            ws.conditional_format(2, sc, 1 + n, sc, dict(
                type="3_color_scale", min_color="#ffc7ce", mid_color="#ffeb9c",
                max_color="#c6efce"))

        for i, (nm, led) in enumerate(sim.ledgers.items(), 1):
            sh = xl_sheet(f"AM{i:02d} {nm}")
            ws = put(led, sh, mcols=[c for c in led.columns if c != "Month"])
            n = len(led)
            ch = wb.add_chart(dict(type="line"))
            ch.add_series(dict(name="Outstanding", categories=[sh, 2, 0, 1 + n, 0],
                               values=[sh, 2, list(led.columns).index("Closing"),
                                       1 + n, list(led.columns).index("Closing")],
                               line=dict(color="#0b3c49", width=2)))
            ch.add_series(dict(name="Interest", categories=[sh, 2, 0, 1 + n, 0],
                               values=[sh, 2, list(led.columns).index("Interest"),
                                       1 + n, list(led.columns).index("Interest")],
                               y2_axis=True, line=dict(color="#ef476f", width=1.5)))
            ch.set_title(dict(name=f"{nm} — run-off and interest"))
            ch.set_size(dict(width=780, height=340))
            ws.insert_chart(2, len(led.columns) + 1, ch)

        put(sim.inv, "20 Investments", mcols=("Value", "Cost", "SIP"),
            pcols=("Nominal", "PostTax", "RiskAdj", "Volatility", "TaxDrag",
                   "Weight %", "ExitLoad", "StepUp", "TaxCostPts", "RiskCutPts",
                   "Horizon"))
        mc = sim.monthly
        ws = put(mc, "21 Monthly Cashflow",
                 mcols=[c for c in mc.columns if c not in
                        ("Month", "Year", "EMI_to_Income", "Savings_Rate")],
                 pcols=("EMI_to_Income", "Savings_Rate"), width=15)
        gc = list(mc.columns).index("Financing_Gap")
        ws.conditional_format(2, gc, 1 + len(mc), gc,
                              dict(type="cell", criteria=">", value=0, format=F["bad"]))

        an = sim.annual
        ws = put(an, "22 Annual Summary",
                 mcols=[c for c in an.columns if c not in
                        ("Year", "EMI_to_Income", "Savings_Rate")],
                 pcols=("EMI_to_Income", "Savings_Rate"))
        n, sh = len(an), "22 Annual Summary"
        c1 = wb.add_chart(dict(type="line"))
        for col, colr in (("Net_Worth", "#00c9a7"), ("Net_Worth_Real", "#8ecae6")):
            c1.add_series(dict(name=col, categories=[sh, 2, 0, 1 + n, 0],
                               values=[sh, 2, list(an.columns).index(col), 1 + n,
                                       list(an.columns).index(col)],
                               line=dict(color=colr, width=3)))
        c1.set_title(dict(name="Net worth — nominal vs today's money"))
        c1.set_size(dict(width=760, height=340))
        ws.insert_chart(2, len(an.columns) + 1, c1)
        c2 = wb.add_chart(dict(type="column", subtype="stacked"))
        for col, colr in (("Investments", "#00c9a7"), ("EF", "#8ecae6"),
                          ("Goal_Corpus", "#ffb703"), ("Debt", "#ef476f")):
            c2.add_series(dict(name=col, categories=[sh, 2, 0, 1 + n, 0],
                               values=[sh, 2, list(an.columns).index(col), 1 + n,
                                       list(an.columns).index(col)],
                               fill=dict(color=colr)))
        c2.set_title(dict(name="Assets vs liabilities"))
        c2.set_size(dict(width=760, height=340))
        ws.insert_chart(20, len(an.columns) + 1, c2)
        c3 = wb.add_chart(dict(type="column", subtype="stacked"))
        for col, colr in (("Interest", "#ef476f"), ("Principal", "#06d6a0"),
                          ("Prepayment", "#ffb703")):
            c3.add_series(dict(name=col, categories=[sh, 2, 0, 1 + n, 0],
                               values=[sh, 2, list(an.columns).index(col), 1 + n,
                                       list(an.columns).index(col)],
                               fill=dict(color=colr)))
        c3.set_title(dict(name="Interest vs principal vs prepayment"))
        c3.set_size(dict(width=760, height=340))
        ws.insert_chart(38, len(an.columns) + 1, c3)

        nw = nw_statement(sim, P)
        put(nw, "23 Net Worth Statement", mcols=("Amount",), width=32)
        gdf = pd.DataFrame(sim.goals)
        if not gdf.empty:
            ws = put(gdf, "24 Goal Roadmap",
                     mcols=("Cost_Today", "Future_Cost", "From_Sale",
                            "From_Sinking_Fund", "From_Earmarked", "From_Other_Assets",
                            "From_Loan", "Total_Funded", "Shortfall",
                            "Borrowing_Refused", "Loan_Settled_On_Sale", "EMI_Freed",
                            "Capitalised", "Corpus_So_Far", "Avg_Monthly_Set_Aside"),
                     pcols=("Goal_Inflation", "Funded_Pct"))
            sc = list(gdf.columns).index("Status")
            ws.conditional_format(2, sc, 1 + len(gdf), sc, dict(
                type="text", criteria="containing", value="SHORTFALL", format=F["bad"]))
            ws.conditional_format(2, sc, 1 + len(gdf), sc, dict(
                type="text", criteria="containing", value="ON TRACK", format=F["good"]))
            ws.conditional_format(2, sc, 1 + len(gdf), sc, dict(
                type="text", criteria="containing", value="BEYOND", format=F["warn"]))
        put(sim.goal_src, "24b Goal Funding Detail",
            mcols=("Gross", "Tax", "Exit_Cost", "Net_Applied"), width=20,
            wrap=("Note",))
        put(lev, "25 Goal Levers", mcols=("Extra_SIP",), width=22)
        put(swaps, "26 Asset-Debt Swaps",
            mcols=("Redeem_Gross", "Net_To_Loan", "Tax_And_Load", "Penalty",
                   "Principal_Killed", "Interest_Saved", "Wealth_Delta"),
            pcols=("Loan_Cost", "Asset_Return", "Spread_vs_Loan"), width=18)
        put(recs, "27 Recommendations", width=20, wrap=("Detail", "Quantified"))
        put(sim.wlog, "28 Waterfall Log",
            mcols=("EF", "Revolving", "SIP", "Goals", "Prepay", "Residual"),
            pcols=("SIP_Blend_RiskAdj", "Worst_LossMaking_Cost"), width=17)
        put(pd.DataFrame({"Flag": sim.warnings or ["None"]}), "29 Warnings",
            width=20, wrap=("Flag",))
    return buf.getvalue()


def nw_statement(sim: Sim, P):
    A = P["assumptions"]
    rows, iv = [], sim.inv
    per = iv[iv["Personal"].astype(bool)] if not iv.empty else iv
    fin = iv[~iv["Personal"].astype(bool)] if not iv.empty else iv
    if not fin.empty:
        for cls, g in fin.groupby("Class"):
            rows.append(dict(Section="INVESTED ASSETS", Item=cls,
                             Amount=g["Value"].sum()))
    rows.append(dict(Section="INVESTED ASSETS", Item="Emergency fund / cash",
                     Amount=sf(A["ef_current"])))
    t_fin = sum(r["Amount"] for r in rows)
    rows.append(dict(Section="INVESTED ASSETS", Item="Total invested assets",
                     Amount=t_fin))
    t_per = 0.0
    if not per.empty:
        # The home you live in, the car, personal valuables. Counted in net worth,
        # never counted as something that could repay a loan or fund a goal.
        for cls, g in per.groupby("Class"):
            v = g["Value"].sum()
            t_per += v
            rows.append(dict(Section="PERSONAL / USE ASSETS", Item=cls, Amount=v))
        rows.append(dict(Section="PERSONAL / USE ASSETS",
                         Item="Total personal assets", Amount=t_per))
    ta = t_fin + t_per
    rows.append(dict(Section="ASSETS", Item="TOTAL ASSETS", Amount=ta))
    tl = 0.0
    if not sim.debt.empty:
        for t, g in sim.debt.groupby("Type"):
            v = g["Outstanding"].sum()
            tl += v
            rows.append(dict(Section="LIABILITIES", Item=t, Amount=-v))
    rows.append(dict(Section="LIABILITIES", Item="TOTAL LIABILITIES", Amount=-tl))
    rows.append(dict(Section="NET", Item="NET WORTH TODAY", Amount=ta - tl))
    if not sim.monthly.empty:
        e = sim.monthly.iloc[-1]
        rows.append(dict(Section="NET",
                         Item=f"NET WORTH YEAR {si(A['horizon_years'])} (nominal)",
                         Amount=e["Net_Worth"]))
        rows.append(dict(Section="NET",
                         Item=f"NET WORTH YEAR {si(A['horizon_years'])} (today's money)",
                         Amount=e["Net_Worth_Real"]))
    return pd.DataFrame(rows)


# ==================================================================== 14. UI
CSS = f"""
<style>
.stApp {{ background:{TH['bg']}; color:{TH['text']}; }}
.block-container {{ padding: 1.4rem 2.6rem 5rem; max-width: 1500px; }}
section[data-testid="stSidebar"] {{ background:{TH['panel']};
  border-right:1px solid {TH['grid']}; }}
section[data-testid="stSidebar"] .block-container {{ padding-top:1rem; }}
h1,h2,h3,h4,h5 {{ color:{TH['text']}; letter-spacing:.2px; line-height:1.4; }}
h2 {{ font-size:22px; margin:.3rem 0 .2rem; }}
h3 {{ font-size:17px; margin:.2rem 0; }}
p, li, label, .stMarkdown {{ line-height:1.65; }}
hr {{ margin:1.5rem 0; border-color:{TH['grid']}; }}

.hero {{ background:linear-gradient(100deg,{TH['panel']} 0%,#0a2026 100%);
  border:1px solid {TH['grid']}; border-left:5px solid {TH['accent']};
  border-radius:14px; padding:20px 26px; margin-bottom:22px; }}
.hero h1 {{ margin:0; font-size:25px; line-height:1.3; }}
.hero p {{ margin:8px 0 0; color:{TH['dim']}; font-size:13.5px; }}

.sec {{ border-left:3px solid {TH['accent']}; padding:2px 0 2px 14px;
  margin:26px 0 14px; }}
.sec h3 {{ margin:0; font-size:18px; }}
.sec p {{ margin:5px 0 0; color:{TH['dim']}; font-size:13px; max-width:900px; }}

.kpi {{ background:{TH['card']}; border:1px solid {TH['grid']};
  border-top:3px solid {TH['accent']}; border-radius:12px;
  padding:16px 18px 18px; min-height:118px; margin-bottom:14px; }}
.kpi .l {{ font-size:11px; letter-spacing:1.3px; text-transform:uppercase;
  color:{TH['dim']}; line-height:1.5; min-height:32px; display:block; }}
.kpi .v {{ font-size:24px; font-weight:700; line-height:1.3; margin-top:6px;
  word-break:break-word; }}
.kpi .s {{ font-size:11.5px; color:{TH['dim']}; margin-top:6px; line-height:1.5;
  display:block; }}

.pill {{ display:inline-block; padding:4px 13px; border-radius:20px; font-size:11px;
  font-weight:700; letter-spacing:.7px; white-space:nowrap; }}
.pg {{ background:rgba(6,214,160,.15); color:{TH['good']};
  border:1px solid rgba(6,214,160,.45); }}
.pw {{ background:rgba(255,183,3,.15); color:{TH['amber']};
  border:1px solid rgba(255,183,3,.45); }}
.pb {{ background:rgba(239,71,111,.15); color:{TH['bad']};
  border:1px solid rgba(239,71,111,.45); }}

.rec {{ background:{TH['card']}; border:1px solid {TH['grid']};
  border-left:4px solid {TH['amber']}; border-radius:10px; padding:16px 20px;
  margin-bottom:14px; }}
.rec .t {{ font-weight:700; font-size:15px; color:{TH['accent']};
  margin-bottom:8px; line-height:1.45; }}
.rec .d {{ font-size:13.5px; line-height:1.75; color:{TH['text']}; }}
.rec .q {{ font-size:12.5px; color:{TH['amber']}; margin-top:10px;
  padding-top:9px; border-top:1px solid {TH['grid']}; }}

.loan {{ background:{TH['card']}; border:1px solid {TH['grid']}; border-radius:11px;
  padding:16px 20px; margin-bottom:13px; }}
.loan .n {{ font-size:15.5px; font-weight:700; line-height:1.4; }}
.loan .m {{ font-size:12px; color:{TH['dim']}; margin-top:4px; }}
.num {{ font-size:19px; font-weight:700; line-height:1.35; }}
.cap {{ font-size:10.5px; text-transform:uppercase; letter-spacing:1.1px;
  color:{TH['dim']}; line-height:1.5; }}

div.stButton>button {{ background:{TH['accent']}; color:#04191c; font-weight:700;
  border:none; border-radius:9px; padding:10px 20px; width:100%; }}
div.stButton>button:hover {{ filter:brightness(1.12); }}
div.stDownloadButton>button {{ background:{TH['amber']}; color:#241a00;
  font-weight:700; border:none; border-radius:9px; padding:10px 20px; width:100%; }}

[data-testid="stMetricLabel"] p {{ font-size:12px !important; white-space:normal;
  line-height:1.45; color:{TH['dim']}; }}
[data-testid="stMetricValue"] {{ font-size:20px !important; line-height:1.35; }}
.stTabs [data-baseweb="tab-list"] {{ gap:6px; flex-wrap:wrap; }}
.stTabs [data-baseweb="tab"] {{ background:{TH['panel']}; border-radius:9px 9px 0 0;
  padding:10px 18px; border:1px solid {TH['grid']}; border-bottom:none;
  font-size:13.5px; }}
.stTabs [aria-selected="true"] {{ background:{TH['card']};
  border-top:2px solid {TH['accent']}; color:{TH['accent']}; }}
.stDataFrame, [data-testid="stDataFrameResizable"] {{ font-size:12.5px; }}
.note {{ background:{TH['card']}; border:1px solid {TH['grid']}; border-radius:10px;
  padding:14px 18px; font-size:13px; line-height:1.7; color:{TH['dim']};
  margin-bottom:16px; }}
.note b {{ color:{TH['text']}; }}
</style>
"""


def kpi(label, value, sub="", tone=""):
    c = {"good": TH["good"], "bad": TH["bad"], "warn": TH["amber"]}.get(tone, TH["text"])
    st.markdown(f"<div class='kpi'><span class='l'>{label}</span>"
                f"<div class='v' style='color:{c}'>{value}</div>"
                f"<span class='s'>{sub}</span></div>", unsafe_allow_html=True)


def section(title, desc=""):
    st.markdown(f"<div class='sec'><h3>{title}</h3>"
                f"{f'<p>{desc}</p>' if desc else ''}</div>", unsafe_allow_html=True)


def note(html):
    st.markdown(f"<div class='note'>{html}</div>", unsafe_allow_html=True)


def pill(t, tone):
    return f"<span class='pill {'pg' if tone=='good' else 'pb' if tone=='bad' else 'pw'}'>{t}</span>"


def show(df, **kw):
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kw)
    except TypeError:
        st.dataframe(df, use_container_width=True, **kw)


def plot(fig, h=420):
    fig.update_layout(paper_bgcolor=TH["card"], plot_bgcolor=TH["card"], height=h,
                      font=dict(color=TH["text"], size=12.5,
                                family="Inter, Segoe UI, sans-serif"),
                      margin=dict(l=15, r=15, t=60, b=45), hovermode="x unified",
                      title=dict(font=dict(size=15), x=0.01, y=0.96),
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0,
                                  font=dict(size=11.5)))
    fig.update_xaxes(gridcolor=TH["grid"], zerolinecolor=TH["grid"],
                     title_font=dict(size=12), tickfont=dict(size=11))
    fig.update_yaxes(gridcolor=TH["grid"], zerolinecolor=TH["grid"],
                     title_font=dict(size=12), tickfont=dict(size=11))
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True)


def fmt(df, m=(), p=(), d=(), c=()):
    """Format a frame for display.

    m = money (Indian grouping, matching the rest of the app), c = compact money
    (2.97 Cr), p = percent, d = plain decimal. Anything not listed renders raw —
    which is how columns like 29714441.735167 used to reach the screen."""
    if df is None or df.empty:
        return df
    spec = {}
    num = lambda col: col in df.columns and pd.api.types.is_numeric_dtype(df[col])
    for col in m:
        if num(col):
            spec[col] = money
    for col in c:
        if num(col):
            spec[col] = compact
    for col in p:
        if num(col):
            spec[col] = lambda v: "-" if pd.isna(v) else f"{v:,.2f}%"
    for col in d:
        if num(col):
            spec[col] = lambda v: "-" if pd.isna(v) else f"{v:,.1f}"
    return df.style.format(spec)


def editor(key, P):
    spec = SCHEMA[key]
    cfg = {}
    for c in spec["cols"]:
        t, h, o = c["t"], c["help"], c["opts"]
        if t == "select":
            cfg[c["k"]] = st.column_config.SelectboxColumn(c["k"], options=o, help=h,
                                                           width="medium")
        elif t == "bool":
            cfg[c["k"]] = st.column_config.CheckboxColumn(c["k"], help=h)
        elif t == "money":
            cfg[c["k"]] = st.column_config.NumberColumn(c["k"], help=h, format="%.0f",
                                                        step=1000.0, width="small")
        elif t == "pct":
            cfg[c["k"]] = st.column_config.NumberColumn(c["k"], help=h, format="%.2f",
                                                        step=0.25, width="small")
        elif t == "int":
            cfg[c["k"]] = st.column_config.NumberColumn(c["k"], help=h, format="%d",
                                                        step=1, width="small")
        else:
            cfg[c["k"]] = st.column_config.TextColumn(c["k"], help=h, width="medium")
    df = P[key]
    cols = [c["k"] for c in spec["cols"]]
    if df.empty:
        df = pd.DataFrame(columns=cols)
    else:
        df = df.reindex(columns=cols)
    try:
        return st.data_editor(df, column_config=cfg, num_rows="dynamic",
                              key=f"ed_{key}", hide_index=True, width="stretch")
    except TypeError:
        return st.data_editor(df, column_config=cfg, num_rows="dynamic",
                              key=f"ed_{key}", hide_index=True, use_container_width=True)


# ------------------------------------------------------------- INPUT PAGES
def page_start(P):
    section("Start here", "Three ways to get your data in. Pick whichever suits you.")
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        with st.container(border=True):
            st.markdown("#### 1 · Excel round-trip")
            st.caption("Recommended for a full plan. Download the template — it comes "
                       "pre-filled with a worked demo and a notes row under every column "
                       "explaining what to enter. Replace the demo rows with yours, save, "
                       "and upload it back.")
            st.download_button("⬇️ Download input template",
                               demo_template_bytes(),
                               file_name="finance_input_template.xlsx",
                               mime="application/vnd.openxmlformats-officedocument."
                                    "spreadsheetml.sheet")
            st.markdown("")
            st.download_button("⬇️ Download template with MY current data",
                               template_bytes(P), file_name="my_finance_inputs.xlsx",
                               mime="application/vnd.openxmlformats-officedocument."
                                    "spreadsheetml.sheet")
            up = st.file_uploader("Upload a filled template", type=["xlsx"],
                                  key="up_xl",
                                  help="Must be the template from above — sheet and "
                                       "column names are matched exactly.")
            if up is not None and st.button("📥 Import this workbook"):
                try:
                    newP, msgs = parse_workbook(up.read())
                    st.session_state.P = newP
                    st.session_state.result = None
                    st.session_state.import_log = msgs
                    st.success("Imported. Review the pages, then run the engine.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not read that workbook: {e}")
    with c2:
        with st.container(border=True):
            st.markdown("#### 2 · Type it in the app")
            st.caption("Work through the pages in the sidebar in order. Every field has a "
                       "hover note — the ⓘ icon on widgets, and the column header tooltip "
                       "in each table. Rows are added with the + at the bottom of a table.")
            if st.button("🧪 Load the demo profile"):
                st.session_state.P = demo()
                st.session_state.result = None
                st.rerun()
            st.markdown("")
            if st.button("🧹 Clear everything and start blank"):
                st.session_state.P = blank()
                st.session_state.result = None
                st.rerun()
    with c3:
        with st.container(border=True):
            st.markdown("#### 3 · Saved profile")
            st.caption("A JSON snapshot of every input. Smaller and faster than Excel — "
                       "use it to come back to a plan later or to keep several scenarios "
                       "side by side.")
            st.download_button("⬇️ Save profile (.json)", to_json(P),
                               file_name="finance_profile.json", mime="application/json")
            uj = st.file_uploader("Load profile (.json)", type=["json"], key="up_js")
            if uj is not None:
                try:
                    st.session_state.P = from_json(uj.read().decode("utf-8"))
                    st.session_state.result = None
                    st.success("Profile loaded.")
                except Exception as e:
                    st.error(f"Could not read that file: {e}")

    if st.session_state.get("import_log"):
        with st.expander("Import log", expanded=False):
            for m in st.session_state.import_log:
                st.write("• " + m)

    section("What the engine will do with this",
            "So you know what each input actually drives.")
    note("<b>Debt</b> — a full monthly amortisation schedule per loan, an effective "
         "post-tax cost after any tax shield, and a verdict against your marginal "
         "investment return.<br>"
         "<b>Investments</b> — post-tax and risk-adjusted returns, a liquidity tier, and "
         "a check on whether any holding would be better used to retire a loan.<br>"
         "<b>Cashflow</b> — every month of the horizon, with EMIs, lumpy expenses and goal "
         "outflows landing in the correct month rather than smoothed.<br>"
         "<b>Goals</b> — inflated to their future cost, funded from a sinking fund, and "
         "reported with the exact monthly top-up needed to close any gap.<br>"
         "<b>Audit</b> — eight arithmetic identity tests you can inspect, so you do not "
         "have to take the output on trust.")


def page_assumptions(P):
    A = P["assumptions"]
    section("Plan basics", "The horizon and the inflation rate that everything else "
                           "is measured against.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        A["profile_name"] = st.text_input("Profile name", A["profile_name"],
                                          help=AHELP["profile_name"])
        A["horizon_years"] = st.slider("Projection horizon (years)", 3, 30,
                                       si(A["horizon_years"], 10),
                                       help=AHELP["horizon_years"])
    with c2:
        A["start_month"] = st.selectbox(
            "Start calendar month", list(range(1, 13)),
            index=si(A["start_month"], 1) - 1,
            format_func=lambda x: ["January", "February", "March", "April", "May",
                                   "June", "July", "August", "September", "October",
                                   "November", "December"][x - 1],
            help=AHELP["start_month"])
        A["inflation"] = st.number_input("Headline inflation % p.a.", 0.0, 25.0,
                                         sf(A["inflation"], 6.0), 0.25,
                                         help=AHELP["inflation"])

    section("How returns are compared with debt",
            "This is the single most consequential setting in the app. It decides which "
            "loans get labelled loss-making.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        A["risk_aversion"] = st.slider("Risk-aversion coefficient", 0.0, 1.0,
                                       sf(A["risk_aversion"], 0.25), 0.05,
                                       help=AHELP["risk_aversion"])
        A["horizon_risk"] = st.toggle("Scale risk haircut by the decision horizon",
                                      sb(A.get("horizon_risk", True), True),
                                      help=AHELP["horizon_risk"])
        _bm = str(A.get("benchmark_mode", BENCH_MODES[0]))
        if _bm == "Default surplus vehicle":       # pre-2.3 name
            _bm = BENCH_MODES[0]
        A["benchmark_mode"] = st.selectbox(
            "Benchmark loans against", BENCH_MODES,
            index=BENCH_MODES.index(_bm) if _bm in BENCH_MODES else 0,
            help=AHELP["benchmark_mode"])
    with c2:
        A["benchmark_custom"] = st.number_input("Custom benchmark % p.a.", 0.0, 40.0,
                                                sf(A["benchmark_custom"], 10.0), 0.25,
                                                help=AHELP["benchmark_custom"])
        names = [str(x) for x in P["investments"].get(
            "Investment Name", pd.Series(dtype=str)).tolist()] or ["(none)"]
        dv = A["default_vehicle"] if A["default_vehicle"] in names else names[0]
        A["default_vehicle"] = st.selectbox("Residual surplus goes to", names,
                                            index=names.index(dv),
                                            help=AHELP["default_vehicle"])
    ra = sf(A["risk_aversion"])
    _tx = TaxConfig.from_dict(P["tax"])
    _sc = sb(A.get("horizon_risk", True), True)
    _rows = []
    for _y in (1, 5, 10, 20):
        _pt = after_tax_cagr(12.0, "equity", _tx, _y)
        _cut = risk_haircut(18.0, ra, _y, _sc)
        _rows.append(f"<tr><td>{_y} yr</td><td>{_pt:.2f}%</td>"
                     f"<td>-{_cut:.2f}</td><td><b>{_pt - _cut:.2f}%</b></td></tr>")
    note("<b>Worked example at your current settings.</b> An equity fund you expect to "
         "return 12% nominal, with 18% volatility, taxed on exit at the equity LTCG "
         "rate. What it actually competes with depends on how long the decision runs:"
         "<table style='margin-top:8px;font-size:12.5px'>"
         "<tr><td><b>Decision horizon</b></td><td><b>After tax</b></td>"
         "<td><b>Risk haircut</b></td><td><b>Competes at</b></td></tr>"
         + "".join(_rows) + "</table>"
         "<br>A loan is loss-making only if its post-tax cost exceeds the figure in "
         "the last column <i>for that loan's own remaining life</i>. This is why a "
         "long, cheap, secured loan can be healthy leverage while a credit card at "
         "the same nominal spread is not."
         + ("" if _sc else "<br><br><b>Horizon scaling is OFF</b>, so every row above "
                           "would use the 1-year haircut of "
                           f"{ra * 18:.2f} points regardless of the loan's life."))

    section("Emergency fund", "Ring-fenced. The optimiser will never spend it on debt.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        A["ef_current"] = st.number_input(f"Emergency fund today ({CCY})", 0.0, 1e10,
                                          sf(A["ef_current"]), 10000.0,
                                          help=AHELP["ef_current"])
        A["ef_target_months"] = st.number_input("Target — months of expenses", 0.0, 36.0,
                                                sf(A["ef_target_months"], 6.0), 0.5,
                                                help=AHELP["ef_target_months"])
        A["ef_return"] = st.number_input("Parking return % p.a.", 0.0, 15.0,
                                         sf(A["ef_return"], 6.0), 0.25,
                                         help=AHELP["ef_return"])
    with c2:
        A["ef_include_emi"] = st.toggle("Target should also cover EMIs",
                                        sb(A["ef_include_emi"]),
                                        help=AHELP["ef_include_emi"])
        A["ef_max_share"] = st.number_input("Max % of monthly surplus used to top it up",
                                            0.0, 100.0, sf(A["ef_max_share"], 40.0), 5.0,
                                            help=AHELP["ef_max_share"])

    section("Prepayment policy", "Constraints the optimiser must respect.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        A["liquid_deploy_cap"] = st.number_input(
            "Max % of liquid portfolio deployable to debt", 0.0, 100.0,
            sf(A["liquid_deploy_cap"], 50.0), 5.0, help=AHELP["liquid_deploy_cap"])
        A["deployable_max_days"] = st.number_input(
            "Max days-to-cash to count as deployable", 0, 400,
            si(A["deployable_max_days"], 30), 1, help=AHELP["deployable_max_days"])
        A["prepay_share_of_surplus"] = st.number_input(
            "Max % of monthly surplus to prepayment", 0.0, 100.0,
            sf(A["prepay_share_of_surplus"], 100.0), 5.0, help=AHELP["prepay_share_of_surplus"])
    with c2:
        A["prepay_mode"] = st.radio("Prepayment reduces", ["tenure", "emi"],
                                    index=0 if A["prepay_mode"] == "tenure" else 1,
                                    horizontal=True, help=AHELP["prepay_mode"])
        A["emi_income_ceiling"] = st.number_input("EMI-to-income ceiling %", 0.0, 100.0,
                                                  sf(A["emi_income_ceiling"], 40.0), 1.0,
                                                  help=AHELP["emi_income_ceiling"])
        A["allow_prepay_healthy"] = st.toggle("Allow prepaying healthy-leverage loans",
                                              sb(A["allow_prepay_healthy"]),
                                              help=AHELP["allow_prepay_healthy"])

    section("Goal funding & alerts")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        A["goal_vehicle_return"] = st.number_input("Goal sinking-fund return % p.a.",
                                                   0.0, 30.0,
                                                   sf(A["goal_vehicle_return"], 8.0), 0.25,
                                                   help=AHELP["goal_vehicle_return"])
        A["bt_threshold"] = st.number_input("Flag refinance if rate exceeds market by (%)",
                                            0.0, 10.0, sf(A["bt_threshold"], 0.75), 0.25,
                                            help=AHELP["bt_threshold"])
    with c2:
        A["illiquid_warn_pct"] = st.number_input("Warn if illiquid share exceeds %", 0.0,
                                                 100.0, sf(A["illiquid_warn_pct"], 60.0),
                                                 5.0, help=AHELP["illiquid_warn_pct"])
    note(f"<b>Verdict bands in force.</b> Spread above <b>+{BAND_HI}%</b> is "
         f"{V_GOOD.lower()} · between <b>{BAND_LO}%</b> and <b>+{BAND_HI}%</b> is neutral · "
         f"below <b>{BAND_LO}%</b> is loss-making. Spread = benchmark risk-adjusted "
         f"post-tax return minus the loan's effective post-tax cost.")


def page_tax(P):
    T = P["tax"]
    section("Regime", "Regime choice changes which loans get a tax shield, which can flip "
                      "a verdict on its own.")
    c1, c2 = st.columns([1, 2], gap="large")
    with c1:
        T["regime"] = st.radio("Tax regime", ["New", "Old"],
                               index=0 if str(T["regime"]).startswith("New") else 1,
                               horizontal=True, help=THELP["regime"])
        T["marginal_rate"] = st.number_input("Marginal tax rate %", 0.0, 45.0,
                                             sf(T["marginal_rate"], 30.0), 0.5,
                                             help=THELP["marginal_rate"])
        T["cess"] = st.number_input("Cess %", 0.0, 10.0, sf(T["cess"], 4.0), 0.5,
                                    help=THELP["cess"])
    with c2:
        old = str(T["regime"]).lower().startswith("old")
        note(f"<b>Shields under the {'old' if old else 'new'} regime.</b><br>"
             f"Self-occupied home loan (Sec 24b): <b>{'applied, capped' if old else 'NOT applied'}</b><br>"
             f"Let-out property interest: <b>applied, uncapped</b><br>"
             f"Education loan (Sec 80E): <b>{'applied, uncapped' if old else 'NOT applied'}</b><br>"
             f"Business / working-capital interest: <b>applied, uncapped</b><br><br>"
             f"This is why a home loan can read 8.60% here and 7.20% under the other "
             f"regime — and why the prepayment recommendation can reverse.")

    section("Capital gains", "Applied whenever the engine models a redemption, so that "
                             "'sell an asset to kill a loan' is an honest comparison.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        T["equity_ltcg"] = st.number_input("Equity LTCG %", 0.0, 40.0,
                                           sf(T["equity_ltcg"], 12.5), 0.5,
                                           help=THELP["equity_ltcg"])
        T["equity_ltcg_exempt"] = st.number_input(f"Equity LTCG annual exemption ({CCY})",
                                                  0.0, 1e7, sf(T["equity_ltcg_exempt"],
                                                               125000.0), 25000.0,
                                                  help=THELP["equity_ltcg_exempt"])
        T["equity_stcg"] = st.number_input("Equity STCG %", 0.0, 40.0,
                                           sf(T["equity_stcg"], 20.0), 0.5,
                                           help=THELP["equity_stcg"])
    with c2:
        T["other_ltcg"] = st.number_input("Other-asset LTCG % (gold, property, unlisted)",
                                          0.0, 40.0, sf(T["other_ltcg"], 12.5), 0.5,
                                          help=THELP["other_ltcg"])
        T["crypto_rate"] = st.number_input("Crypto / VDA rate %", 0.0, 50.0,
                                           sf(T["crypto_rate"], 30.0), 1.0,
                                           help=THELP["crypto_rate"])
        T["sec24b_cap"] = st.number_input(f"Section 24b cap, self-occupied ({CCY})", 0.0,
                                          1e7, sf(T["sec24b_cap"], 200000.0), 50000.0,
                                          help=THELP["sec24b_cap"])

    section("Switches")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        T["apply_cg_on_redemption"] = st.toggle("Apply capital-gains tax on redemptions",
                                                sb(T["apply_cg_on_redemption"]),
                                                help=THELP["apply_cg_on_redemption"])
        T["sec54_rollover"] = st.toggle("Section 54 rollover on a home-to-home upgrade",
                                        sb(T.get("sec54_rollover", True), True),
                                        help=THELP["sec54_rollover"])
    with c2:
        T["apply_debt_shields"] = st.toggle("Apply debt tax shields",
                                            sb(T["apply_debt_shields"]),
                                            help=THELP["apply_debt_shields"])
    note("The annual equity exemption is tracked per financial year across every "
         "redemption the engine models, not applied once. Debt mutual funds bought after "
         "1 April 2023 are treated at your slab rate with no indexation, in line with "
         "current law.")


def page_income(P):
    section("Earners", "Enter POST-TAX, in-hand amounts. The engine does not compute "
                       "income tax — that was the agreed basis.")
    for who, title in (("primary", "Earner 1"), ("secondary", "Earner 2 / Spouse")):
        b = P["income"][who]
        with st.container(border=True):
            st.markdown(f"#### {title}")
            b["enabled"] = st.toggle("Include this earner", sb(b.get("enabled")),
                                     key=f"en_{who}", help=IHELP["enabled"])
            if not b["enabled"]:
                st.caption("Excluded from the projection.")
                continue
            c1, c2, c3 = st.columns(3, gap="large")
            with c1:
                b["monthly_inhand"] = st.number_input(
                    f"Monthly in-hand ({CCY})", 0.0, 1e9, sf(b["monthly_inhand"]), 5000.0,
                    key=f"mi_{who}", help=IHELP["monthly_inhand"])
                b["business_monthly"] = st.number_input(
                    f"Business income / month ({CCY})", 0.0, 1e9, sf(b["business_monthly"]),
                    5000.0, key=f"bz_{who}", help=IHELP["business_monthly"])
            with c2:
                b["annual_bonus"] = st.number_input(
                    f"Annual bonus ({CCY})", 0.0, 1e9, sf(b["annual_bonus"]), 10000.0,
                    key=f"ab_{who}", help=IHELP["annual_bonus"])
                b["bonus_month"] = st.number_input("Bonus calendar month", 1, 12,
                                                   si(b["bonus_month"], 4), key=f"bm_{who}",
                                                   help=IHELP["bonus_month"])
            with c3:
                b["increment_pct"] = st.number_input("Annual increment %", 0.0, 60.0,
                                                     sf(b["increment_pct"]), 0.5,
                                                     key=f"ip_{who}",
                                                     help=IHELP["increment_pct"])
                b["increment_month"] = st.number_input("Increment calendar month", 1, 12,
                                                       si(b["increment_month"], 4),
                                                       key=f"im_{who}",
                                                       help=IHELP["increment_month"])
            c1, c2 = st.columns(2, gap="large")
            with c1:
                b["business_growth_pct"] = st.number_input(
                    "Business growth % p.a.", -50.0, 100.0, sf(b["business_growth_pct"]),
                    0.5, key=f"bg_{who}", help=IHELP["business_growth_pct"])
            with c2:
                b["stop_month"] = st.number_input("Income stops after month # (0 = never)",
                                                  0, 600, si(b["stop_month"]),
                                                  key=f"sm_{who}", help=IHELP["stop_month"])

    section(SCHEMA["passive"]["label"], SCHEMA["passive"]["intro"])
    P["passive"] = editor("passive", P)
    if not P["passive"].empty:
        mth = 0.0
        for _, r in P["passive"].iterrows():
            a = sf(r.get("Amount"))
            f = str(r.get("Frequency", "Monthly"))
            mth += a / {"Monthly": 1, "Quarterly": 3, "Half-yearly": 6, "Annual": 12}.get(f, 1)
        c1, c2, c3 = st.columns(3, gap="large")
        with c1:
            kpi("Passive income, monthly equivalent", compact(mth),
                "before tax adjustment")
        with c2:
            sal = sum(sf(P["income"][w]["monthly_inhand"]) +
                      sf(P["income"][w]["business_monthly"])
                      for w in ("primary", "secondary") if sb(P["income"][w]["enabled"]))
            kpi("Active income, monthly", compact(sal), "salary and business, in-hand")
        with c3:
            tot = sal + mth
            kpi("Passive share of income", f"{mth/tot*100:.1f}%" if tot else "-",
                "the higher this is, the more resilient the plan",
                "good" if tot and mth / tot > 0.25 else "")


def page_expenses(P):
    section(SCHEMA["expenses"]["label"], SCHEMA["expenses"]["intro"])
    P["expenses"] = editor("expenses", P)
    st.markdown("")
    section(SCHEMA["lumpy"]["label"], SCHEMA["lumpy"]["intro"])
    P["lumpy"] = editor("lumpy", P)
    if not P["expenses"].empty or not P["lumpy"].empty:
        m = pd.to_numeric(P["expenses"]["Monthly Amount"], errors="coerce"
                          ).fillna(0).sum() if not P["expenses"].empty else 0.0
        l = pd.to_numeric(P["lumpy"]["Annual Amount"],
                          errors="coerce").fillna(0).sum() if not P["lumpy"].empty else 0.0
        st.markdown("")
        c1, c2, c3, c4 = st.columns(4, gap="large")
        with c1:
            kpi("Monthly run-rate", compact(m), "recurring only, EMIs excluded")
        with c2:
            kpi("Annual, including lumpy", compact(m * 12 + l))
        with c3:
            kpi("Lumpy share of the year",
                f"{l / (m * 12 + l) * 100:.1f}%" if (m * 12 + l) > 0 else "-",
                "these create the cashflow spikes")
        with c4:
            infl = sf(P["assumptions"]["inflation"], 6.0)
            y10 = m * 12 * (1 + infl / 100) ** 10
            kpi("Annual spend in year 10", compact(y10),
                f"at {infl:.1f}% inflation — this is what the plan must fund", "warn")


def page_debts(P):
    section(SCHEMA["debts"]["label"], SCHEMA["debts"]["intro"])
    P["debts"] = editor("debts", P)
    if not P["debts"].empty:
        o = pd.to_numeric(P["debts"]["Outstanding Principal"], errors="coerce").fillna(0)
        e = pd.to_numeric(P["debts"]["EMI"], errors="coerce").fillna(0)
        r = pd.to_numeric(P["debts"]["Interest Rate % p.a."], errors="coerce").fillna(0)
        st.markdown("")
        c1, c2, c3, c4 = st.columns(4, gap="large")
        with c1:
            kpi("Total outstanding", compact(o.sum()))
        with c2:
            kpi("Total monthly EMI", compact(e.sum()))
        with c3:
            kpi("Weighted average rate",
                f"{np.average(r, weights=o):.2f}%" if o.sum() else "-",
                "before any tax shield")
        with c4:
            kpi("Highest rate on the book", f"{r.max():.2f}%" if len(r) else "-",
                "this is where the damage is", "bad" if len(r) and r.max() > 15 else "")
        note("<b>A note on flat rates.</b> If a lender quoted you '9% flat' on a car or "
             "personal loan, tick the Flat / Add-on box. A 9% flat rate over 5 years is "
             "roughly a 16.5% reducing-balance rate — nearly double. Getting this wrong is "
             "the most common reason a debt plan understates its own cost.")


def page_investments(P):
    section("Asset-class defaults",
            "These seed any row where you leave return, volatility, liquidity or lock-in "
            "blank. Set them once to your own house view; per-holding entries always win.")
    with st.expander("Edit class defaults", expanded=False):
        seed = pd.DataFrame([
            {"Asset Class": k, "Expected Return % p.a.": v["ret"],
             "Volatility % p.a.": v["vol"], "Days to Cash": v["liq"],
             "Tax Treatment": v["tax"], "Statutory Lock-in (months)": v["lock"]}
            for k, v in ASSET_CLASSES.items()])
        try:
            ed = st.data_editor(seed, key="ed_seed", hide_index=True, width="stretch",
                                disabled=["Asset Class", "Tax Treatment"])
        except TypeError:
            ed = st.data_editor(seed, key="ed_seed", hide_index=True,
                                use_container_width=True,
                                disabled=["Asset Class", "Tax Treatment"])
        for _, r in ed.iterrows():
            if r["Asset Class"] in ASSET_CLASSES:
                ASSET_CLASSES[r["Asset Class"]].update(
                    ret=sf(r["Expected Return % p.a."]), vol=sf(r["Volatility % p.a."]),
                    liq=si(r["Days to Cash"]), lock=si(r["Statutory Lock-in (months)"]))

    section(SCHEMA["investments"]["label"], SCHEMA["investments"]["intro"])
    P["investments"] = editor("investments", P)
    if not P["investments"].empty:
        v = pd.to_numeric(P["investments"]["Current Value"], errors="coerce").fillna(0)
        s = pd.to_numeric(P["investments"]["Monthly SIP"], errors="coerce").fillna(0)
        rr = pd.to_numeric(P["investments"]["Expected Return % p.a."], errors="coerce")
        st.markdown("")
        c1, c2, c3, c4 = st.columns(4, gap="large")
        with c1:
            kpi("Portfolio value", compact(v.sum()))
        with c2:
            kpi("Monthly SIP commitment", compact(s.sum()))
        with c3:
            ok = rr.notna() & (v > 0)
            kpi("Weighted expected return",
                f"{np.average(rr[ok], weights=v[ok]):.2f}%" if ok.any() else "-",
                "nominal, pre-tax, before any risk haircut; blanks take the "
                "asset-class default")
        with c4:
            kpi("Holdings", f"{len(P['investments'])}")


def page_goals(P):
    section(SCHEMA["goals"]["label"], SCHEMA["goals"]["intro"])
    P["goals"] = editor("goals", P)
    if not P["goals"].empty:
        g = P["goals"].copy()
        g["_fv"] = [sf(r["Cost in Today's Money"]) *
                    (1 + sf(r["Goal Inflation % p.a."]) / 100) ** sf(r["Target Year (from now)"])
                    for _, r in g.iterrows()]
        c0 = pd.to_numeric(g["Cost in Today's Money"], errors="coerce").fillna(0).sum()
        st.markdown("")
        c1, c2, c3, c4 = st.columns(4, gap="large")
        with c1:
            kpi("Number of goals", f"{len(g)}")
        with c2:
            kpi("Total cost in today's money", compact(c0))
        with c3:
            kpi("Total cost when actually due", compact(g["_fv"].sum()),
                "after goal-specific inflation", "warn")
        with c4:
            kpi("Inflation adds", compact(g["_fv"].sum() - c0),
                f"{(g['_fv'].sum()/c0-1)*100:.0f}% more than today's price"
                if c0 else "", "bad")
        note("<b>Why this gap matters.</b> The difference above is not a modelling "
             "artefact — it is the amount your plan must generate purely to stand still. "
             "Education at 10% doubles roughly every seven years. If any of these "
             "inflation rates look generous, lower them here rather than discovering the "
             "gap later.")


def page_check(P):
    section("Data check", "Run this before the engine. Blockers will produce nonsense "
                          "output; warnings are worth a second look.")
    v = validate(P)
    if v.empty:
        st.success("No issues found. Run the engine from the sidebar.")
        return
    nb = (v["Severity"] == "BLOCKER").sum()
    nw = (v["Severity"] == "WARNING").sum()
    nn = (v["Severity"] == "NOTE").sum()
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        kpi("Blockers", f"{nb}", "must be fixed", "bad" if nb else "good")
    with c2:
        kpi("Warnings", f"{nw}", "worth reviewing", "warn" if nw else "good")
    with c3:
        kpi("Notes", f"{nn}", "for your awareness")
    st.markdown("")
    for sev in ("BLOCKER", "WARNING", "NOTE"):
        sub = v[v["Severity"] == sev]
        if sub.empty:
            continue
        st.markdown(f"#### {sev.title()}s")
        for _, r in sub.iterrows():
            st.markdown(f"<div class='rec' style='border-left-color:"
                        f"{TH['bad'] if sev=='BLOCKER' else TH['amber'] if sev=='WARNING' else TH['accent']}'>"
                        f"<div class='t'>{r['Where']}</div>"
                        f"<div class='d'>{r['Message']}</div></div>", unsafe_allow_html=True)


# ------------------------------------------------------------ OUTPUT PAGES
def out_dashboard(sim, P):
    A = P["assumptions"]
    m, an = sim.monthly, sim.annual
    section("Where you stand and where this plan takes you")
    c = st.columns(3, gap="large")
    with c[0]:
        kpi("Net worth today", compact(sim.nw0))
    with c[1]:
        cagr = ((sim.nw1 / sim.nw0) ** (1 / si(A["horizon_years"])) - 1) * 100 \
            if sim.nw0 > 0 and sim.nw1 > 0 else float("nan")
        kpi(f"Net worth in year {si(A['horizon_years'])}", compact(sim.nw1),
            f"{cagr:.1f}% a year" if np.isfinite(cagr) else "",
            "good" if sim.nw1 > sim.nw0 else "bad")
    with c[2]:
        rw = m["Net_Worth_Real"].iloc[-1] if not m.empty else 0
        kpi("Same figure in today's money", compact(rw),
            f"after {sf(A['inflation']):.1f}% inflation — this is the honest number", "warn")
    c = st.columns(3, gap="large")
    with c[0]:
        d0 = sim.debt["Outstanding"].sum() if not sim.debt.empty else 0
        kpi("Debt outstanding today", compact(d0))
    with c[1]:
        kpi("Marginal benchmark return", f"{sim.bench:.2f}%",
            "risk-adjusted and post-tax — every loan is judged against this", "good")
    with c[2]:
        nb = (sim.debt["Verdict"] == V_BAD).sum() if not sim.debt.empty else 0
        kpi("Loss-making loans", f"{nb}", "costing more than your money earns",
            "bad" if nb else "good")
    c = st.columns(3, gap="large")
    with c[0]:
        kpi("Total interest over the plan", compact(m["Interest"].sum()),
            "the price of the debt you carry", "bad")
    with c[1]:
        kpi("Peak EMI to income", f"{m['EMI_to_Income'].max():.0f}%",
            f"your ceiling is {sf(A['emi_income_ceiling']):.0f}%",
            "bad" if m["EMI_to_Income"].max() > sf(A["emi_income_ceiling"]) else "good")
    with c[2]:
        g = m["Financing_Gap"].sum()
        kpi("Financing gaps", compact(g) if g else "None",
            "months where cash ran out", "bad" if g else "good")

    section("Net worth trajectory")
    f = go.Figure()
    f.add_trace(go.Scatter(x=an["Year"], y=an["Net_Worth"], name="Net worth (nominal)",
                           mode="lines+markers", line=dict(color=TH["accent"], width=3),
                           fill="tozeroy", fillcolor="rgba(0,201,167,.10)"))
    f.add_trace(go.Scatter(x=an["Year"], y=an["Net_Worth_Real"],
                           name="Net worth (today's money)", mode="lines",
                           line=dict(color="#8ecae6", width=2, dash="dash")))
    f.add_trace(go.Scatter(x=an["Year"], y=-an["Debt"], name="Debt",
                           line=dict(color=TH["bad"], dash="dot")))
    f.update_layout(title="Nominal vs real net worth, and the debt behind it",
                    xaxis_title="Year", yaxis_title=f"{CCY}")
    plot(f, 450)

    if not sim.debt.empty:
        section("Which loans help you and which hurt",
                "Bars to the right of zero are cheaper than your money earns. Bars to the "
                "left are destroying value every month they stay outstanding.")
        d = sim.debt.sort_values("Spread")
        col = [TH["bad"] if v == V_BAD else TH["good"] if v == V_GOOD else TH["amber"]
               for v in d["Verdict"]]
        f = go.Figure(go.Bar(x=d["Spread"], y=d["Loan"], orientation="h",
                             marker_color=col,
                             text=[f"{s:+.2f}%" for s in d["Spread"]],
                             textposition="outside", cliponaxis=False))
        f.add_vline(x=0, line_color=TH["text"], line_width=1)
        f.add_vline(x=BAND_HI, line_color=TH["good"], line_dash="dot")
        f.add_vline(x=BAND_LO, line_color=TH["bad"], line_dash="dot")
        f.update_layout(title="Leverage spread — benchmark minus effective cost",
                        xaxis_title="Percentage points")
        plot(f, max(300, 90 + 52 * len(d)))

    section("Annual cashflow composition")
    f = go.Figure()
    f.add_trace(go.Bar(x=an["Year"], y=an["Income"], name="Income",
                       marker_color=TH["accent"]))
    f.add_trace(go.Bar(x=an["Year"], y=-(an["Expenses"] + an["Lumpy"]), name="Living costs",
                       marker_color="#8ecae6"))
    f.add_trace(go.Bar(x=an["Year"], y=-an["EMI"], name="EMI", marker_color=TH["bad"]))
    f.add_trace(go.Bar(x=an["Year"], y=-(an["SIP"] + an["Goal_Funding"]), name="Invested",
                       marker_color=TH["amber"]))
    f.update_layout(barmode="relative", title="Where the money goes each year",
                    xaxis_title="Year")
    plot(f, 440)

    if sim.warnings:
        section("Engine flags")
        with st.expander(f"{len(sim.warnings)} flags raised during the projection"):
            for w in sim.warnings:
                st.write("• " + w)


def out_debt(sim, P):
    if sim.debt.empty:
        st.info("No debt entered.")
        return
    d = sim.debt
    section("Loan-by-loan verdict",
            f"Each loan's effective post-tax cost against your marginal benchmark of "
            f"{sim.bench:.2f}%.")
    for _, r in d.sort_values("EffectiveCost", ascending=False).iterrows():
        tone = "bad" if r["Verdict"] == V_BAD else "good" if r["Verdict"] == V_GOOD else "warn"
        with st.container(border=True):
            c = st.columns([3, 2], gap="large")
            with c[0]:
                st.markdown(f"<div class='loan' style='background:transparent;border:none;"
                            f"padding:0'><div class='n'>{r['Loan']}</div>"
                            f"<div class='m'>{r['Type']} · {r['Security']} · "
                            f"{r['Collateral']}</div></div>", unsafe_allow_html=True)
            with c[1]:
                st.markdown(f"<div style='text-align:right'>{pill(r['Verdict'], tone)}</div>",
                            unsafe_allow_html=True)
            c = st.columns(5, gap="medium")
            for col, cap, val, sub in (
                (c[0], "Outstanding", compact(r["Outstanding"]), f"EMI {compact(r['EMI'])}"),
                (c[1], "Headline rate", f"{r['Rate']:.2f}%",
                 "fixed" if r["Fixed"] else "floating"),
                (c[2], "Effective post-tax cost", f"{r['EffectiveCost']:.2f}%",
                 f"{r['EffectiveCost'] - r['Rate']:+.2f} pts from tax shield"),
                (c[3], "Spread vs benchmark", f"{r['Spread']:+.2f}%",
                 f"real cost {r['RealCost']:+.2f}%"),
                (c[4], "Interest still to pay", compact(r["InterestRemaining"]),
                 f"{r['IntToPrin']:.0f}% of outstanding · {si(r['MonthsLeft'])} months")):
                with col:
                    st.markdown(f"<div class='cap'>{cap}</div>"
                                f"<div class='num'>{val}</div>"
                                f"<div class='cap' style='text-transform:none'>{sub}</div>",
                                unsafe_allow_html=True)
            if r["EngineNote"] != "-":
                st.caption(f"Engine note — {r['EngineNote']}")
            with st.expander("Why this verdict"):
                shield = r["Rate"] - r["EffectiveCost"]
                st.markdown(
                    f"**The loan costs**\n\n"
                    f"- Headline rate **{r['Rate']:.2f}%**\n"
                    f"- Tax shield ({r['Shield']}) "
                    f"{'−' if shield > 0 else ''}{abs(shield):.2f} pts\n"
                    f"- **Effective post-tax cost {r['EffectiveCost']:.2f}%** — this is "
                    f"a certain, guaranteed cost\n\n"
                    f"**The money could instead earn**\n\n"
                    f"- This loan runs about **{r['DecisionYears']:.1f} more years**, so "
                    f"that is the horizon the comparison uses\n"
                    f"- Over that horizon your benchmark investment competes at "
                    f"**{r['Benchmark']:.2f}%** after tax and after the risk haircut\n\n"
                    f"**Verdict**\n\n"
                    f"- Spread = {r['Benchmark']:.2f}% − {r['EffectiveCost']:.2f}% = "
                    f"**{r['Spread']:+.2f} points**\n"
                    f"- Above +{BAND_HI} is {V_GOOD.lower()}, below {BAND_LO} is "
                    f"{V_BAD.lower()}, in between is neutral\n\n"
                    + ("Keeping this loan and investing the difference is expected to "
                       "leave you better off." if r["Verdict"] == V_GOOD else
                       "Every rupee left outstanding is expected to destroy value."
                       if r["Verdict"] == V_BAD else
                       "The edge either way is inside the noise. Either choice is "
                       "defensible; pick on cashflow comfort, not arithmetic."))

    section("Full table")
    cols = ["Loan", "Type", "Security", "Outstanding", "Rate", "EffectiveCost", "RealCost",
            "EMI", "MonthsLeft", "InterestRemaining", "IntToPrin", "DecisionYears",
            "Benchmark", "Spread", "Verdict",
            "Penalty", "MarketRate", "Closes_In_Month", "Interest_Paid_In_Plan",
            "Prepaid_In_Plan"]
    show(fmt(d[[c for c in cols if c in d.columns]],
             m=("Outstanding", "EMI", "InterestRemaining", "Interest_Paid_In_Plan",
                "Prepaid_In_Plan"),
             p=("Rate", "EffectiveCost", "RealCost", "Spread", "MarketRate",
                "Benchmark"),
             d=("IntToPrin", "Penalty", "DecisionYears")))

    section("Floating-rate stress test",
            "What happens to your total EMI if rates move. Fixed-rate loans are excluded.")
    base = sum(r["EMI"] for _, r in d.iterrows() if not r["Revolving"])
    rows = []
    for bps in (-100, 0, 50, 100, 200, 300):
        t = 0.0
        for _, r in d.iterrows():
            if r["Revolving"]:
                continue
            rr = r["Rate"] + (0 if r["Fixed"] else bps / 100)
            t += emi_of(r["Outstanding"], rr, max(si(r["MonthsLeft"]), 1))
        rows.append(dict(Scenario=f"{bps:+d} bps", Total_EMI=t, Change=t - base,
                         Change_Pct=(t / base - 1) * 100 if base else 0))
    show(fmt(pd.DataFrame(rows), m=("Total_EMI", "Change"), p=("Change_Pct",)))


def out_amort(sim, P):
    if not sim.ledgers:
        st.info("No loan schedules to show.")
        return
    section("Amortisation schedule", "Month by month, for the loan you select.")
    pick = st.selectbox("Loan", list(sim.ledgers.keys()))
    led = sim.ledgers[pick]
    c = st.columns(4, gap="large")
    with c[0]:
        kpi("Months in the plan", f"{len(led)}",
            "until closure or the end of the horizon")
    with c[1]:
        kpi("Interest paid", compact(led["Interest"].sum()), "", "bad")
    with c[2]:
        kpi("Principal repaid", compact(led["Principal"].sum()), "", "good")
    with c[3]:
        kpi("Prepaid", compact(led["Prepayment"].sum()),
            "over and above the EMI", "good")
    f = go.Figure()
    f.add_trace(go.Bar(x=led["Month"], y=led["Interest"], name="Interest",
                       marker_color=TH["bad"]))
    f.add_trace(go.Bar(x=led["Month"], y=led["Principal"], name="Principal",
                       marker_color=TH["good"]))
    f.add_trace(go.Bar(x=led["Month"], y=led["Prepayment"], name="Prepayment",
                       marker_color=TH["amber"]))
    f.add_trace(go.Scatter(x=led["Month"], y=led["Closing"], name="Outstanding",
                           yaxis="y2", line=dict(color=TH["accent"], width=3)))
    f.update_layout(barmode="stack", title=f"{pick} — interest, principal and run-off",
                    xaxis_title="Month",
                    yaxis2=dict(overlaying="y", side="right", showgrid=False,
                                title="Outstanding"))
    plot(f, 470)
    section("What-if: a one-off prepayment")
    row = sim.debt[sim.debt["Loan"] == pick]
    if not row.empty:
        r = row.iloc[0]
        c1, c2 = st.columns(2, gap="large")
        amt = c1.number_input(f"Prepay amount ({CCY})", 0.0, float(r["Outstanding"]),
                              float(min(500000, r["Outstanding"])), 25000.0,
                              help="A lump sum applied on top of the EMI.")
        mth = c2.number_input("In which month", 1, 360, 1,
                              help="Month 1 is now. Prepaying early saves far more "
                                   "interest than prepaying late.")
        b = schedule(r["Outstanding"], r["RateApplied"], r["EMI"], bool(r["Revolving"]),
                     r["MinDue"])
        n = schedule(r["Outstanding"], r["RateApplied"], r["EMI"], bool(r["Revolving"]),
                     r["MinDue"], pre_m=si(mth), pre_amt=amt)
        pen = amt * r["Penalty"] / 100
        c = st.columns(4, gap="large")
        with c[0]:
            kpi("Interest saved", compact(b["Interest"].sum() - n["Interest"].sum()),
                "", "good")
        with c[1]:
            kpi("Tenure shortened", f"{len(b) - len(n)} months", "", "good")
        with c[2]:
            kpi("Prepayment penalty", compact(pen), f"at {r['Penalty']:.1f}%",
                "bad" if pen else "")
        with c[3]:
            net = b["Interest"].sum() - n["Interest"].sum() - pen
            kpi("Net benefit", compact(net), "after the penalty",
                "good" if net > 0 else "bad")
    section("Schedule")
    show(fmt(led, m=[c for c in led.columns if c != "Month"]))


def out_inv(sim, P):
    if sim.inv.empty:
        st.info("No investments entered.")
        return
    iv = sim.inv
    per = iv[iv["Personal"].astype(bool)]
    iv = iv[~iv["Personal"].astype(bool)]          # returns/benchmark: invested only
    if iv.empty:
        st.info("Only personal-use assets are recorded. Nothing here is investable, "
                "so there is no portfolio return to analyse.")
        show(fmt(per, m=("Value", "Cost"), p=("Nominal",)))
        return
    tv = float(iv["Value"].sum())

    def wavg(col):
        """Value-weighted, falling back to a plain mean when every holding is
        zero — np.average raises on zero weights."""
        return float(np.average(iv[col], weights=iv["Value"])) if tv > 0 \
            else float(iv[col].mean())

    section("Portfolio at a glance")
    c = st.columns(4, gap="large")
    with c[0]:
        kpi("Invested portfolio", compact(tv),
            (f"plus {compact(per['Value'].sum())} of personal-use assets, excluded "
             f"from these returns" if not per.empty else ""))
    with c[1]:
        kpi("Blended post-tax return", f"{wavg('PostTax'):.2f}%",
            "after tax drag, before risk")
    with c[2]:
        kpi("Blended risk-adjusted return", f"{wavg('RiskAdj'):.2f}%",
            "the number that competes with your debt")
    with c[3]:
        lq = float(iv[iv["LiquidityScore"] >= 4]["Value"].sum())
        kpi("Accessible within 7 days", compact(lq),
            f"{lq / tv * 100:.0f}% of the portfolio" if tv > 0 else "-")
    section("Return against liquidity",
            "Top-right is where you want size: good risk-adjusted return and quick access. "
            "Anything below the dashed line earns less than the marginal benchmark and is "
            "a candidate for retiring debt instead.")
    f = go.Figure(go.Scatter(
        x=iv["LiquidityScore"], y=iv["RiskAdj"], mode="markers+text",
        text=iv["Investment"], textposition="top center", textfont=dict(size=10.5),
        marker=dict(size=np.clip(iv["Value"] / max(iv["Value"].max(), 1) * 70, 14, 70),
                    color=iv["Volatility"], colorscale="Teal", showscale=True,
                    colorbar=dict(title="Volatility %", thickness=12),
                    line=dict(color=TH["grid"], width=1))))
    f.add_hline(y=sim.bench, line_dash="dash", line_color=TH["amber"],
                annotation_text=f"benchmark {sim.bench:.2f}%")
    f.update_layout(title="Bubble size is the amount invested",
                    xaxis_title="Liquidity score  (1 illiquid · 5 instant)",
                    yaxis_title="Risk-adjusted post-tax return %")
    plot(f, 480)
    section("Allocation")
    g = iv.groupby("Class")["Value"].sum().sort_values()
    f = go.Figure(go.Bar(x=g.values, y=g.index, orientation="h",
                         marker_color=TH["accent"],
                         text=[compact(v) for v in g.values], textposition="outside",
                         cliponaxis=False))
    f.update_layout(title="Value by asset class", xaxis_title=CCY)
    plot(f, max(300, 90 + 40 * len(g)))
    section("Holdings detail")
    show(fmt(iv, m=("Value", "Cost", "SIP"),
             p=("Nominal", "PostTax", "RiskAdj", "TaxCostPts", "RiskCutPts"),
             d=("Volatility", "TaxDrag", "Weight %", "ExitLoad", "StepUp", "Horizon")))
    note("<b>Risk-adjusted return</b> = after-tax CAGR over the decision horizon, "
         "less risk-aversion × volatility ⁄ √horizon. Capital-gains tax on a growth "
         "asset is charged once at exit, not every year, and a longer horizon narrows "
         "the spread of the annualised outcome — which is why the same fund competes "
         "harder against a 16-year home loan than against a 1-year card balance. "
         "<b>Deployable</b> means unlocked, liquid enough under your setting, "
         "not earmarked for a goal, not pledged as collateral, and not marked never-"
         "liquidate. Only deployable assets set the benchmark, because only they could "
         "actually repay a loan.")


def out_cash(sim, P):
    A = P["assumptions"]
    m, an = sim.monthly, sim.annual
    section("Cashflow")
    view = st.radio("Granularity", ["Annual", "Monthly"], horizontal=True)
    if view == "Annual":
        show(fmt(an, m=[c for c in an.columns if c not in
                        ("Year", "EMI_to_Income", "Savings_Rate")],
                 d=("EMI_to_Income", "Savings_Rate")))
    else:
        yr = st.slider("Year", 1, si(A["horizon_years"], 10), 1)
        sub = m[m["Year"] == yr]
        show(fmt(sub, m=[c for c in sub.columns if c not in
                         ("Month", "Year", "EMI_to_Income", "Savings_Rate")],
                 d=("EMI_to_Income", "Savings_Rate")))
    section("Surplus, EMI and the lumps")
    f = go.Figure()
    f.add_trace(go.Scatter(x=m["Month"], y=m["Net_Surplus"], name="Net surplus",
                           line=dict(color=TH["accent"], width=2)))
    f.add_trace(go.Scatter(x=m["Month"], y=m["EMI_Paid"], name="EMI",
                           line=dict(color=TH["bad"], width=2)))
    f.add_trace(go.Bar(x=m["Month"], y=m["Goal_Outflow"], name="Goal outflow",
                       marker_color=TH["amber"]))
    f.add_hline(y=0, line_color=TH["dim"], line_width=1)
    f.update_layout(title="Monthly cash — the dips are lumpy expenses and goal payments",
                    xaxis_title="Month")
    plot(f, 440)
    section("Health ratios")
    f = go.Figure()
    f.add_trace(go.Scatter(x=m["Month"], y=m["EMI_to_Income"], name="EMI to income %",
                           line=dict(color=TH["bad"], width=2)))
    f.add_trace(go.Scatter(x=m["Month"], y=m["Savings_Rate"], name="Savings rate %",
                           line=dict(color=TH["good"], width=2)))
    f.add_hline(y=sf(A["emi_income_ceiling"]), line_dash="dot", line_color=TH["amber"],
                annotation_text="your EMI ceiling")
    f.update_layout(title="Debt burden and savings rate over time", xaxis_title="Month",
                    yaxis_title="%")
    plot(f, 420)
    section("Waterfall log", "Your rule in action: prepayment jumps ahead of SIPs in any "
                             "month where the blended SIP risk-adjusted return is below "
                             "the worst loss-making loan's effective cost.")
    wl = sim.wlog
    flips = (wl["Order"] == "prepay-before-SIP").sum()
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        kpi("Months prepayment came first", f"{flips}", f"out of {len(wl)}",
            "warn" if flips else "good")
    with c2:
        kpi("Blended SIP risk-adjusted return", f"{wl['SIP_Blend_RiskAdj'].iloc[0]:.2f}%")
    with c3:
        w = wl["Worst_LossMaking_Cost"].max()
        kpi("Worst loss-making cost seen", f"{w:.2f}%" if np.isfinite(w) else "none",
            "", "bad" if np.isfinite(w) else "good")
    with st.expander("Month-by-month allocation"):
        show(fmt(wl, m=("EF", "Revolving", "SIP", "Goals", "Prepay", "Residual"),
                 p=("SIP_Blend_RiskAdj", "Worst_LossMaking_Cost")))


def out_nw(sim, P):
    A = P["assumptions"]
    an = sim.annual
    d0 = sim.debt["Outstanding"].sum() if not sim.debt.empty else 0
    a0 = (sim.inv["Value"].sum() if not sim.inv.empty else 0) + sf(A["ef_current"])
    section("Net worth statement")
    c = st.columns(4, gap="large")
    with c[0]:
        kpi("Gross assets", compact(a0))
    with c[1]:
        kpi("Total liabilities", compact(d0), "", "bad")
    with c[2]:
        kpi("Net worth today", compact(a0 - d0), "", "good" if a0 > d0 else "bad")
    with c[3]:
        kpi("Debt to assets", f"{d0/a0*100:.1f}%" if a0 else "-",
            "below 40% is comfortable", "bad" if a0 and d0 / a0 > 0.4 else "good")
    show(fmt(nw_statement(sim, P), m=("Amount",)))
    section("How it builds")
    f = go.Figure()
    for col, nm, colr in (("Investments", "Investments", TH["accent"]),
                          ("EF", "Emergency fund", "#8ecae6"),
                          ("Goal_Corpus", "Goal corpus", TH["amber"])):
        f.add_trace(go.Bar(x=an["Year"], y=an[col], name=nm, marker_color=colr))
    f.add_trace(go.Bar(x=an["Year"], y=-an["Debt"], name="Debt", marker_color=TH["bad"]))
    f.add_trace(go.Scatter(x=an["Year"], y=an["Net_Worth"], name="Net worth",
                           line=dict(color="white", width=3)))
    f.update_layout(barmode="relative", title="Assets, liabilities and net worth by year",
                    xaxis_title="Year")
    plot(f, 470)


def out_goals(sim, P):
    g = pd.DataFrame(sim.goals)
    if g.empty:
        st.info("No goals entered.")
        return
    lv = levers(sim, P)
    section("Goal roadmap")
    for _, r in g.iterrows():
        short = r["Status"] == "SHORTFALL"
        beyond = r["Status"] == "BEYOND HORIZON"
        ok = not short
        L = lv[lv["Goal"] == r["Goal"]]
        with st.container(border=True):
            c = st.columns([3, 1.2], gap="large")
            with c[0]:
                st.markdown(f"<div class='n' style='font-size:16px;font-weight:700'>"
                            f"{r['Goal']}</div><div class='m' style='color:{TH['dim']};"
                            f"font-size:12px;margin-top:4px'>{r['Category']} · due in year "
                            f"{si(r['Year'])} · priority {si(r['Priority'])}</div>",
                            unsafe_allow_html=True)
            with c[1]:
                tone = "warn" if beyond else "good" if ok else "bad"
                st.markdown(f"<div style='text-align:right'>"
                            f"{pill(r['Status'], tone)}</div>",
                            unsafe_allow_html=True)
            c = st.columns(4, gap="medium")
            for col, cap, val, sub in (
                (c[0], "Cost today", compact(r["Cost_Today"]), ""),
                (c[1], "Cost when due", compact(r["Future_Cost"]),
                 f"at {r['Goal_Inflation']:.1f}% goal inflation"),
                (c[2], "Set aside so far" if beyond else "Funded",
                 compact(r["Corpus_So_Far"]) if beyond else f"{r['Funded_Pct']:.0f}%",
                 "by the end of the projection" if beyond else compact(r["Total_Funded"])),
                (c[3], "Shortfall",
                 "not yet due" if beyond
                 else compact(r["Shortfall"]) if r["Shortfall"] > 1 else "—",
                 "" if ok else "needs action")):
                with col:
                    st.markdown(f"<div class='cap'>{cap}</div><div class='num'>{val}</div>"
                                f"<div class='cap' style='text-transform:none'>{sub}</div>",
                                unsafe_allow_html=True)
            prog = (r["Corpus_So_Far"] / r["Future_Cost"] if beyond and r["Future_Cost"]
                    else float(r["Funded_Pct"]) / 100)
            st.progress(min(max(float(prog), 0.0), 1.0))
            if beyond:
                st.caption(
                    f"This goal falls in year {si(r['Year'])}, beyond the "
                    f"{si(P['assumptions']['horizon_years'])}-year horizon, so the "
                    f"projection never pays it out. The engine still sets money aside "
                    f"for it — {compact(r['Corpus_So_Far'])} by the end of the run "
                    f"against a future cost of {compact(r['Future_Cost'])}. Extend the "
                    f"horizon to test whether it is genuinely funded.")
            src = sim.goal_src[sim.goal_src["Goal"] == r["Goal"]] \
                if not sim.goal_src.empty else sim.goal_src
            if not src.empty:
                with st.expander(f"Where the {compact(r['Future_Cost'])} came from"):
                    t = src[["Source", "Kind", "Asset_Class", "Gross", "Tax",
                             "Exit_Cost", "Net_Applied", "Note"]].copy()
                    t = t.rename(columns={
                        "Asset_Class": "Asset class", "Gross": "Gross realised",
                        "Exit_Cost": "Exit load", "Net_Applied": "Applied to goal"})
                    show(fmt(t, m=("Gross realised", "Tax", "Exit load",
                                   "Applied to goal")))
                    tot = float(src["Net_Applied"].sum())
                    cost = float(src.loc[src["Kind"] != "Shortfall",
                                         "Net_Applied"].sum())
                    frict = float(src["Tax"].sum() + src["Exit_Cost"].sum())
                    st.caption(
                        f"Applied to the goal: {money(cost)}"
                        + (f" · unfunded: {money(tot - cost)}" if tot - cost > 1 else "")
                        + (f" · lost to tax and exit costs on the way: {money(frict)}"
                           if frict > 1 else "")
                        + ". 'Other investment redeemed' rows are sold in liquidity "
                          "order — quickest to cash first — skipping anything locked, "
                          "pledged, earmarked elsewhere or in personal use.")
            if short and not L.empty:
                x = L.iloc[0]
                dly = f"{x['Delay_Years']} years" if np.isfinite(sf(x["Delay_Years"], np.nan)) \
                    else "not achievable by delay alone"
                st.markdown(
                    f"<div class='rec' style='margin-top:12px'>"
                    f"<div class='t'>Closing a {compact(r['Shortfall'])} gap</div>"
                    f"<div class='d'>Any one of these works:<br>"
                    f"<b>a.</b> Start an additional SIP of <b>{money(x['Extra_SIP'])} a "
                    f"month</b> from now.<br>"
                    f"<b>b.</b> Defer the goal by <b>{dly}</b>.<br>"
                    f"<b>c.</b> Reduce the target by <b>{x['Cost_Cut_Pct']}%</b>.<br>"
                    f"<b>d.</b> Redirect the EMIs freed as loans close before this date — "
                    f"that alone covers <b>{x['Freed_EMI_Cover']}</b>."
                    f"</div></div>", unsafe_allow_html=True)
    section("Funding sources")
    f = go.Figure()
    for col, nm, colr in (("From_Sinking_Fund", "Sinking fund", TH["accent"]),
                          ("From_Earmarked", "Earmarked asset", "#8ecae6"),
                          ("From_Other_Assets", "Other assets", TH["amber"]),
                          ("From_Loan", "Loan", TH["bad"]),
                          ("Shortfall", "Unfunded", "#5a2634")):
        f.add_trace(go.Bar(x=g["Goal"], y=g[col], name=nm, marker_color=colr))
    f.update_layout(barmode="stack", title="How each goal gets paid for")
    plot(f, 450)
    section("Detail")
    order = ["Goal", "Category", "Year", "Priority", "Status", "Cost_Today",
             "Goal_Inflation", "Future_Cost", "From_Sale", "From_Sinking_Fund",
             "From_Earmarked", "From_Other_Assets", "From_Loan", "Total_Funded",
             "Funded_Pct", "Shortfall", "Borrowing_Refused", "Loan_Settled_On_Sale",
             "EMI_Freed", "Capitalised", "Corpus_So_Far", "Avg_Monthly_Set_Aside"]
    gt = g[[c for c in order if c in g.columns]].rename(columns={
        "Cost_Today": "Cost today", "Future_Cost": "Cost when due",
        "Goal_Inflation": "Goal inflation", "From_Sale": "From sale of asset",
        "From_Sinking_Fund": "From sinking fund", "From_Earmarked": "From earmarked",
        "From_Other_Assets": "From other assets", "From_Loan": "From new loan",
        "Total_Funded": "Total funded", "Funded_Pct": "Funded",
        "Borrowing_Refused": "Borrowing refused", "Loan_Settled_On_Sale":
        "Old loan settled", "EMI_Freed": "EMI freed", "Capitalised": "Asset acquired",
        "Corpus_So_Far": "Corpus so far", "Avg_Monthly_Set_Aside": "Avg monthly set-aside"})
    show(fmt(gt,
             m=("Cost today", "Cost when due", "From sale of asset",
                "From sinking fund", "From earmarked", "From other assets",
                "From new loan", "Total funded", "Shortfall", "Borrowing refused",
                "Old loan settled", "EMI freed", "Asset acquired", "Corpus so far",
                "Avg monthly set-aside"),
             p=("Goal inflation", "Funded")))
    if not sim.goal_src.empty:
        section("Every rupee, by source",
                "One row per source per goal, so 'from other assets' is never a "
                "black box. Gross is what was realised, and the gap to what reached "
                "the goal is the tax and exit cost of getting there.")
        gs = sim.goal_src.rename(columns={
            "Asset_Class": "Asset class", "Gross": "Gross realised",
            "Exit_Cost": "Exit load", "Net_Applied": "Applied to goal"})
        show(fmt(gs, m=("Gross realised", "Tax", "Exit load", "Applied to goal")))


def out_advice(sim, P, swaps, recs):
    section("Action plan", "Ordered by what will cost you most if ignored.")
    if recs.empty:
        st.info("No recommendations generated.")
    else:
        for pr in sorted(recs["Priority"].unique()):
            lbl = {1: "Do first", 2: "Do next", 3: "Monitor",
                   4: "Leave alone"}.get(pr, "Other")
            colr = {1: TH["bad"], 2: TH["amber"], 3: "#8ecae6",
                    4: TH["good"]}.get(pr, TH["accent"])
            st.markdown(f"<h3 style='color:{colr};margin-top:26px'>{lbl}</h3>",
                        unsafe_allow_html=True)
            for _, r in recs[recs["Priority"] == pr].iterrows():
                st.markdown(f"<div class='rec' style='border-left-color:{colr}'>"
                            f"<div class='t'>{r['Title']}</div>"
                            f"<div class='d'>{r['Detail']}</div>"
                            f"<div class='q'>{r['Quantified']}</div></div>",
                            unsafe_allow_html=True)
    section("Asset to debt swaps",
            "Would selling something to kill a loan actually leave you richer? Judged on "
            "terminal wealth after capital-gains tax, exit load and prepayment penalty — "
            "not on a naive rate comparison.")
    if swaps.empty:
        st.info("No feasible swap after applying your constraints — emergency fund intact, "
                "no lock-ins broken, deployable cap respected, earmarked and pledged assets "
                "left alone.")
    else:
        show(fmt(swaps, m=("Redeem_Gross", "Net_To_Loan", "Tax_And_Load", "Penalty",
                           "Principal_Killed", "Interest_Saved", "Wealth_Delta"),
                 p=("Loan_Cost", "Asset_Return", "Spread_vs_Loan")))
        note("<b>Wealth_Delta</b> compares your wealth at the loan's original maturity under "
             "two paths: keep investing and let the loan run, versus redeem, prepay, and "
             "invest the freed EMI from the day the loan closes. Positive means the swap "
             "makes you richer after every friction.")


def out_audit(sim, P, aud):
    section("Audit and reconciliation",
            "Independent arithmetic checks on the engine's own output. Each test "
            "recomputes an identity from the results rather than trusting the code path "
            "that produced them. Any deviation above one rupee is a genuine defect.")
    npass = (aud["Result"] == "PASS").sum() if not aud.empty else 0
    c = st.columns(3, gap="large")
    with c[0]:
        kpi("Tests passed", f"{npass} of {len(aud)}", "",
            "good" if npass == len(aud) else "bad")
    with c[1]:
        kpi("Largest deviation found",
            money(aud["Max_Deviation"].max(), 4) if not aud.empty else "-",
            "across every row of every schedule")
    with c[2]:
        kpi("Months simulated", f"{len(sim.monthly)}",
            f"{len(sim.ledgers)} loan schedules")
    st.markdown("")
    for _, r in aud.iterrows():
        ok = r["Result"] == "PASS"
        st.markdown(
            f"<div class='rec' style='border-left-color:{TH['good'] if ok else TH['bad']}'>"
            f"<div class='t'>{'✓' if ok else '✗'} {r['Test']}</div>"
            f"<div class='d'>{r['Detail']}<br>Rows checked: <b>{r['Rows_Checked']}</b> · "
            f"maximum deviation: <b>{money(r['Max_Deviation'], 6)}</b></div></div>",
            unsafe_allow_html=True)

    section("Methodology", "Every formula the engine uses, so you can check it by hand.")
    with st.expander("Debt", expanded=True):
        st.markdown(f"""
- **EMI** = P·r·(1+r)ⁿ ⁄ ((1+r)ⁿ − 1), with r = annual rate ⁄ 1200 — the monthly-rest
  convention Indian lenders use.
- **Monthly interest** = opening balance × r. Principal = EMI − interest. Closing =
  opening − principal.
- **Flat-rate conversion**: total interest = P × flat% × years; EMI = (P + interest) ⁄ n;
  the true reducing-balance APR is then solved by bisection. A 9% flat quote comes out
  near 16.5% reducing.
- **Effective post-tax cost** = rate − (deductible interest × marginal rate) ⁄ outstanding.
  For a self-occupied home loan the deduction is capped, so the shield dilutes as the
  loan grows. Let-out property interest, 80E and business interest are uncapped.
- **Real cost** uses Fisher: (1 + nominal) ⁄ (1 + inflation) − 1. Not a subtraction.
- **Revolving credit** pays max(min-due% × balance + interest, {CCY}100) each month.
""")
    with st.expander("Investments and the comparison"):
        st.markdown("""
- **Monthly growth** = (1 + annual)^(1/12) − 1, the effective rate. Note this differs
  deliberately from the loan convention of annual ⁄ 12, because lenders quote nominal
  rates and investment returns are quoted as effective.
- **Post-tax return** = nominal × (1 − tax drag). Slab-taxed instruments are dragged
  annually as they accrue; growth assets are dragged at the exit rate on the embedded gain.
- **Risk-adjusted return** = post-tax − (risk-aversion × volatility).
- **Benchmark** = value-weighted risk-adjusted return of deployable assets only.
- **Spread** = benchmark − effective cost of debt. This single number drives every verdict.
- **Redemptions** solve by bisection for the gross amount that nets the cash needed, after
  exit load and capital-gains tax, with the annual equity exemption tracked per financial
  year across all redemptions.
""")
    with st.expander("Cashflow and goals"):
        st.markdown("""
- Income and expenses step **annually**, on the anniversary month you specify, not smoothly.
- Bonuses and annual expenses land in their **calendar month**, aligned to your start month.
- Rental income receives the **30% standard deduction** before tax is applied.
- **Surplus waterfall**: emergency fund top-up → revolving credit → then either
  (prepay, SIP, goals) or (SIP, goals, prepay), decided monthly by your rule → residual to
  the default vehicle.
- **Deficits** draw first on the emergency fund, then on liquid assets in liquidity order,
  skipping anything earmarked, pledged or locked. Anything still unmet is reported as a
  financing gap rather than silently ignored.
- **Goal future cost** = today's cost × (1 + goal inflation)^years. A goal dated
  beyond the horizon is never paid out; it is reported as BEYOND HORIZON with the
  corpus accumulated against it, and excluded from the goal identity test.
- **Borrowing for a goal is capped by affordability.** The engine will not assume a
  loan it cannot service: the new EMI, on top of everything already being paid, must
  fit inside your EMI-to-income ceiling. Because the instalment is linear in the
  principal, the borrowable amount scales with the headroom left. Anything that will
  not fit is reported as refused borrowing and falls through to your own corpus, or
  becomes a shortfall. A goal is never marked ON TRACK on the strength of debt you
  could not repay.
- **Replacement purchases** — upgrading a house, changing the car — run in this
  order at the goal date:
  1. the asset named in *Sell to Fund* is sold in full, at its projected value;
  2. any loan whose *Linked Investment (collateral)* is that asset is settled out of
     the proceeds, with its prepayment penalty;
  3. the EMI thereby released is added back to your borrowing capacity **before** the
     new loan is sized, so the upgrade is judged on what you will actually be paying,
     not on carrying both loans at once;
  4. the remaining proceeds meet the new cost first, and the *% From Own Corpus*
     ratio then applies only to what is still left to find;
  5. what you buy is capitalised onto the balance sheet at what was actually paid,
     via *Becomes Asset (class)*, so an upgrade is a change in the composition of
     your wealth rather than its destruction;
  6. if the old asset sold for more than the new one cost, the difference is invested.

  Where a residential property is sold to buy another, the capital gain is rolled
  over under Section 54 to the extent it is reinvested. If the sale does not clear
  the loan secured on it, the engine says so explicitly rather than quietly leaving
  secured debt against an asset you no longer own.
- **Required monthly set-aside** = gap × r ⁄ ((1+r)ⁿ − 1), recomputed every month against
  the actual balance, so it self-corrects.
""")
    with st.expander("What this engine does not do"):
        st.markdown("""
- It does not forecast markets. Returns are **your** inputs compounded deterministically.
  A 12% equity assumption held for ten years is an assumption, not a fact — the
  risk-aversion haircut exists to keep it honest.
- It does not compute income tax. You enter post-tax figures, as agreed.
- It applies no statutory contribution caps (PPF ₹1.5 lakh a year, for instance).
- Section 54 relief is applied as a simple full rollover to the extent reinvested. The
  real provision has holding-period, timing and one-house conditions, and Section 54F
  is different again. Confirm with your CA before relying on it for a large disposal.
- A replacement purchase is assumed to complete in a single month: sale, settlement
  and purchase all land together, with no bridging finance and no rent in between.
- It assumes you never miss a payment and never change your mind.
- The tax layer is a **planning simplification**. Before executing any large redemption,
  have the actual gain and holding period computed by your CA — the difference between
  short and long-term treatment alone can move the answer materially.
""")


def out_export(sim, P, swaps, recs, lev, aud):
    section("Excel report", "A formatted workbook with native charts and conditional "
                            "formatting, one sheet per loan schedule.")
    st.markdown("""
Sheets included: Cover and assumptions · **Audit results** · Inputs · Debt diagnostics ·
one amortisation schedule per loan with an embedded chart · Investment analysis ·
Monthly cashflow (every month) · Annual summary with three charts · Net worth statement ·
Goal roadmap · Goal levers · Asset-to-debt swaps · Recommendations · Waterfall log · Warnings.
""")
    if st.button("🧾 Generate the workbook"):
        with st.spinner("Building..."):
            st.session_state.xlsx = report_bytes(P, sim, swaps, recs, lev, aud)
        st.success(f"Ready — {len(st.session_state.xlsx)/1024:.0f} KB")
    if "xlsx" in st.session_state:
        st.download_button("⬇️ Download the report",
                           st.session_state.xlsx,
                           file_name=f"Finance_Plan_{date.today().isoformat()}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet")
    section("Other exports")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.download_button("⬇️ Inputs as an editable template",
                           template_bytes(P), file_name="my_finance_inputs.xlsx",
                           mime="application/vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet")
        st.caption("Your current data in the upload template format — edit offline and "
                   "bring it back.")
    with c2:
        st.download_button("⬇️ Profile as JSON", to_json(P),
                           file_name="finance_profile.json", mime="application/json")
        st.caption("Compact snapshot for versioning scenarios.")


# ------------------------------------------------------------ SAVE / LOAD
def to_json(P):
    o = dict(assumptions=P["assumptions"], tax=P["tax"], income=P["income"])
    for k in SCHEMA:
        o[k] = P[k].to_dict(orient="records")
    return json.dumps(o, indent=2, default=str)


def from_json(raw):
    d = json.loads(raw)
    P = demo()
    P["assumptions"].update(d.get("assumptions", {}))
    P["tax"].update(d.get("tax", {}))
    for w in ("primary", "secondary"):
        if w in d.get("income", {}):
            P["income"][w].update(d["income"][w])
    for k in SCHEMA:
        if k in d:
            P[k] = pd.DataFrame(d[k])
    return P


# ------------------------------------------------------------------ SHELL
IN_PAGES = ["① Start & data entry", "② Assumptions", "③ Tax", "④ Income",
            "⑤ Expenses", "⑥ Debts", "⑦ Investments", "⑧ Goals", "⑨ Data check"]
OUT_PAGES = ["Dashboard", "Debt diagnostics", "Amortisation", "Investments",
             "Cashflow", "Net worth", "Goal roadmap", "Advisory",
             "Audit & methodology", "Export"]


def sidebar():
    with st.sidebar:
        st.markdown(f"### {APP.split('&')[0].strip()}")
        st.caption(f"v{VER} · deterministic engine")
        st.divider()
        mode = st.radio("Section", ["📥 Inputs", "📊 Results"], label_visibility="collapsed")
        st.divider()
        if mode.startswith("📥"):
            page = st.radio("Page", IN_PAGES, label_visibility="collapsed")
        else:
            page = st.radio("Page", OUT_PAGES, label_visibility="collapsed")
        st.divider()
        st.markdown("**Scenario**")
        preset = st.selectbox("Preset", ["Base", "Optimistic", "Pessimistic", "Custom"],
                              help="Base uses your inputs as entered. The others shift "
                                   "returns, inflation and rates together.")
        base = dict(return_shift=0.0, expense_shift=0.0, rate_bps=0.0,
                    market_shock=0.0, income_loss_pct=0.0, income_loss_months=0)
        sc = {"Base": base,
              "Optimistic": dict(base, return_shift=2.0, expense_shift=-1.0, rate_bps=-50.0),
              "Pessimistic": dict(base, return_shift=-3.0, expense_shift=1.5,
                                  rate_bps=150.0)}.get(preset, dict(base))
        if preset == "Custom":
            sc["return_shift"] = st.slider("Return shift (pts)", -8.0, 8.0, 0.0, 0.5)
            sc["expense_shift"] = st.slider("Inflation shift (pts)", -3.0, 6.0, 0.0, 0.5)
            sc["rate_bps"] = st.slider("Floating rate shift (bps)", -300, 400, 0, 25)
        with st.expander("Stress tests"):
            sc["market_shock"] = st.number_input("Market crash in month 1 (%)", 0, 70,
                                                 si(sc["market_shock"]), 5,
                                                 help="Applied to volatile assets only.")
            sc["income_loss_pct"] = st.number_input("Income loss (%)", 0, 100,
                                                    si(sc["income_loss_pct"]), 5)
            sc["income_loss_months"] = st.number_input("Lasting how many months", 0, 60,
                                                       si(sc["income_loss_months"]), 1)
        st.session_state.scen = sc
        st.divider()
        if st.button("▶️  Run the engine"):
            P = st.session_state.P
            v = validate(P)
            if not v.empty and (v["Severity"] == "BLOCKER").any():
                st.error("Blockers found — see the Data check page.")
            else:
                P["_tax"] = TaxConfig.from_dict(P["tax"])
                with st.spinner("Amortising, projecting, auditing..."):
                    sim = simulate(P, sc)
                    sim.audit = audit(sim, P)
                    st.session_state.result = sim
                st.session_state.pop("xlsx", None)
                fails = (sim.audit["Result"] == "FAIL").sum()
                if fails:
                    st.error(f"{fails} audit test(s) FAILED — see Audit page.")
                else:
                    st.success("Done. All audit tests passed.")
        return mode, page


def main():
    st.set_page_config(page_title=APP, page_icon="🧮", layout="wide",
                       initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)
    if "P" not in st.session_state:
        st.session_state.P = demo()
    if "result" not in st.session_state:
        st.session_state.result = None
    P = st.session_state.P
    mode, page = sidebar()
    st.markdown(f"<div class='hero'><h1>🧮 {APP}</h1><p>{page}</p></div>",
                unsafe_allow_html=True)

    if mode.startswith("📥"):
        {IN_PAGES[0]: page_start, IN_PAGES[1]: page_assumptions, IN_PAGES[2]: page_tax,
         IN_PAGES[3]: page_income, IN_PAGES[4]: page_expenses, IN_PAGES[5]: page_debts,
         IN_PAGES[6]: page_investments, IN_PAGES[7]: page_goals,
         IN_PAGES[8]: page_check}[page](P)
        return

    sim = st.session_state.result
    if sim is None:
        st.info("Nothing to show yet. Complete the input pages, then press "
                "**Run the engine** in the sidebar.")
        return
    # The swap optimiser is the expensive part of the output side; only the pages
    # that actually display it should pay for it on every rerun.
    if page in ("Advisory", "Export"):
        swaps = optimise(sim, P)
        recs = advice(sim, P, swaps)
    else:
        swaps = recs = pd.DataFrame()
    lev = levers(sim, P) if page == "Export" else pd.DataFrame()
    if page == "Dashboard":
        out_dashboard(sim, P)
    elif page == "Debt diagnostics":
        out_debt(sim, P)
    elif page == "Amortisation":
        out_amort(sim, P)
    elif page == "Investments":
        out_inv(sim, P)
    elif page == "Cashflow":
        out_cash(sim, P)
    elif page == "Net worth":
        out_nw(sim, P)
    elif page == "Goal roadmap":
        out_goals(sim, P)
    elif page == "Advisory":
        out_advice(sim, P, swaps, recs)
    elif page == "Audit & methodology":
        out_audit(sim, P, sim.audit)
    else:
        out_export(sim, P, swaps, recs, lev, sim.audit)


if _in_streamlit():
    main()
elif __name__ == "__main__":
    _launch()
