"""
ingestion.py
============
Loads and validates applicant data from:

* a single Excel workbook (.xlsx) with the sheets produced by ``sample_data.build_excel_template``, or
* a set of CSV files whose file names contain a keyword identifying the statement
  (``balance``, ``pnl`` / ``profit``, ``cash``, ``debt``, ``proposed``, ``applicant``).

Everything is normalised into an ``ApplicantData`` object so the rest of the
engine never touches raw files.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd


class DataValidationError(Exception):
    """Raised when the uploaded data cannot be used (missing sheets, missing line items, bad values)."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


# --------------------------------------------------------------------------- #
# Schema definitions   (line item -> required?)   Values are in ₹ Crore.
# --------------------------------------------------------------------------- #
BS_ITEMS = {
    "Share Capital": True,
    "Reserves & Surplus": True,
    "Long Term Borrowings": True,          # excluding current maturities
    "Short Term Borrowings": True,         # CC / OD / WCDL
    "Current Maturities of LTD": True,
    "Trade Payables": True,
    "Other Current Liabilities": True,     # incl. provisions
    "Other Non-Current Liabilities": False,
    "Net Fixed Assets": True,
    "Capital Work in Progress": False,
    "Intangible Assets": True,
    "Non-Current Investments": False,
    "Other Non-Current Assets": False,
    "Inventories": True,
    "Trade Receivables": True,
    "Cash & Bank Balances": True,
    "Other Current Assets": False,
}
PNL_ITEMS = {
    "Revenue from Operations": True,
    "Other Income": False,
    "Cost of Goods Sold": True,            # materials consumed + purchases +/- inventory change
    "Employee Expenses": True,
    "Other Operating Expenses": True,
    "Depreciation & Amortization": True,
    "Finance Costs": True,
    "Tax Expense": True,
}
CF_ITEMS = {
    "Cash Flow from Operations": True,     # before interest paid (interest shown under financing)
    "Capital Expenditure": True,           # enter as a POSITIVE number (outflow)
    "Other Investing Cash Flows": False,
    "Debt Raised": True,
    "Debt Repaid": True,                   # principal repayments, POSITIVE number
    "Interest Paid": True,
    "Dividends Paid": False,
}
STATEMENTS = {"balance_sheet": BS_ITEMS, "pnl": PNL_ITEMS, "cashflow": CF_ITEMS}

APPLICANT_FIELDS = [
    ("name", "Company Name"),
    ("cin", "CIN"),
    ("industry", "Industry"),
    ("constitution", "Constitution"),
    ("inc_year", "Incorporation Year"),
    ("promoter_holding_pct", "Promoter Holding (%)"),
    ("rating", "External Rating"),
    ("bureau_score", "Credit Bureau Score (300-900)"),
]
PROPOSED_FIELDS = [
    ("facility_type", "Facility Type"),
    ("amount", "Requested Amount (Cr)"),
    ("tenure_years", "Tenure (Years)"),
    ("rate_pct", "Interest Rate (%)"),
    ("moratorium_months", "Moratorium (Months)"),
    ("refinance_amount", "Refinance of Existing Debt (Cr)"),
    ("collateral_value", "Collateral Value (Cr)"),
    ("purpose", "Purpose"),
]
DEBT_COLUMNS = [
    "Lender", "Facility Type", "Sanctioned Limit", "Outstanding",
    "Interest Rate (%)", "Annual Principal", "Annual Interest",
]
FACILITY_TYPES = ["Term Loan", "Working Capital CC/OD", "NCD"]


@dataclass
class ApplicantData:
    profile: dict
    years: list
    balance_sheet: pd.DataFrame   # index = line item, columns = fiscal years
    pnl: pd.DataFrame
    cashflow: pd.DataFrame
    existing_debt: pd.DataFrame
    proposed: dict
    warnings: list = field(default_factory=list)

    @property
    def latest_year(self) -> str:
        return self.years[-1]

    @property
    def vintage_years(self) -> float:
        """Years in operation as at the latest financial year (e.g. 'FY2025' -> 2025)."""
        m = re.search(r"(\d{4})", str(self.latest_year))
        ref_year = int(m.group(1)) if m else date.today().year
        inc = self.profile.get("inc_year")
        return float(max(ref_year - int(inc), 0)) if inc else np.nan


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _norm(text) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def _classify(name: str) -> str | None:
    n = _norm(name)
    rules = [
        ("balance_sheet", ("balance", "bs")),
        ("pnl", ("pnl", "profit", "loss", "income", "pl")),
        ("cashflow", ("cash", "cf")),
        ("existing_debt", ("existing", "debt", "lender", "exposure")),
        ("proposed", ("proposed", "facility", "proposal")),
        ("applicant", ("applicant", "profile", "company")),
    ]
    for key, kws in rules:
        # short tokens (bs, pl, cf) must match the whole name to avoid false positives
        if any((n == kw) if len(kw) <= 2 else (kw in n) for kw in kws):
            return key
    return None


def _read_statement(df: pd.DataFrame, items: dict, label: str, errors: list, warnings: list):
    """Convert a sheet laid out as [Line Item | FY1 | FY2 | FY3] into a canonical DataFrame."""
    df = df.dropna(how="all").copy()
    if df.shape[1] < 3:
        errors.append(f"{label}: expected a 'Line Item' column plus at least two fiscal-year columns.")
        return None
    df = df.set_index(df.columns[0])
    df.columns = [str(c).strip() for c in df.columns]
    df = df.apply(pd.to_numeric, errors="coerce")
    lookup = {_norm(i): i for i in df.index}

    rows, missing = {}, []
    for item, required in items.items():
        src = lookup.get(_norm(item))
        if src is None:
            if required:
                missing.append(item)
            else:
                rows[item] = pd.Series(0.0, index=df.columns)
                warnings.append(f"{label}: optional line '{item}' not supplied - assumed 0.")
        else:
            row = df.loc[src]
            if isinstance(row, pd.DataFrame):  # duplicate line item names
                row = row.iloc[0]
            rows[item] = row
    if missing:
        errors.append(f"{label}: missing required line items -> {', '.join(missing)}")
        return None
    out = pd.DataFrame(rows).T
    if out.isna().any().any():
        bad = out.index[out.isna().any(axis=1)].tolist()
        errors.append(f"{label}: non-numeric / blank values in -> {', '.join(bad)}")
        return None
    return out


def _read_key_value(df: pd.DataFrame, fields: list) -> dict:
    df = df.dropna(how="all")
    kv = {_norm(k): v for k, v in zip(df.iloc[:, 0], df.iloc[:, 1])}
    out = {}
    for key, label in fields:
        out[key] = kv.get(_norm(label))
    return out


def _normalise_facility_type(text) -> str:
    t = str(text).lower()
    if any(w in t for w in ("cc", "od", "working", "overdraft", "cash credit", "wcdl")):
        return "Working Capital CC/OD"
    if "ncd" in t or "debenture" in t:
        return "NCD"
    return "Term Loan"


def _read_existing_debt(df: pd.DataFrame, errors: list, warnings: list):
    df = df.dropna(how="all").copy()
    df.columns = [str(c).strip() for c in df.columns]
    lookup = {_norm(c): c for c in df.columns}
    needed = ["Lender", "Facility Type", "Outstanding"]
    missing = [c for c in needed if _norm(c) not in lookup]
    if missing:
        errors.append(f"Existing debt: missing columns -> {', '.join(missing)}")
        return None
    out = pd.DataFrame()
    for col in DEBT_COLUMNS:
        out[col] = df[lookup[_norm(col)]] if _norm(col) in lookup else np.nan
    for col in DEBT_COLUMNS[2:]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["Facility Type"] = out["Facility Type"].map(_normalise_facility_type)
    out["Lender"] = out["Lender"].astype(str).str.strip()
    out["Sanctioned Limit"] = out["Sanctioned Limit"].fillna(out["Outstanding"])
    if out["Annual Interest"].isna().any():
        out["Annual Interest"] = out["Annual Interest"].fillna(out["Outstanding"] * out["Interest Rate (%)"] / 100)
        warnings.append("Existing debt: blank 'Annual Interest' derived as Outstanding x Interest Rate.")
    out["Annual Principal"] = out["Annual Principal"].fillna(0.0)
    if out[["Outstanding", "Annual Interest"]].isna().any().any():
        errors.append("Existing debt: 'Outstanding' and 'Annual Interest' (or 'Interest Rate (%)') must be numeric.")
        return None
    return out.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def load_from_files(files: dict[str, bytes]) -> ApplicantData:
    """
    ``files`` maps file name -> raw bytes. Accepts either one .xlsx workbook or several .csv files.
    Raises ``DataValidationError`` listing every problem found.
    """
    errors: list[str] = []
    warnings: list[str] = []
    frames: dict[str, pd.DataFrame] = {}

    for fname, raw in files.items():
        lower = fname.lower()
        if lower.endswith((".xlsx", ".xlsm", ".xls")):
            book = pd.read_excel(io.BytesIO(raw), sheet_name=None)
            for sheet, df in book.items():
                key = _classify(sheet)
                if key:
                    frames[key] = df
        elif lower.endswith(".csv"):
            key = _classify(fname.rsplit(".", 1)[0])
            if key:
                frames[key] = pd.read_csv(io.BytesIO(raw))
            else:
                warnings.append(f"File '{fname}' ignored - could not tell which statement it contains.")

    for key in ("balance_sheet", "pnl", "cashflow", "existing_debt", "proposed", "applicant"):
        if key not in frames:
            errors.append(f"Missing input: {key.replace('_', ' ')} (sheet or CSV).")
    if errors:
        raise DataValidationError(errors)

    bs = _read_statement(frames["balance_sheet"], BS_ITEMS, "Balance sheet", errors, warnings)
    pl = _read_statement(frames["pnl"], PNL_ITEMS, "P&L", errors, warnings)
    cf = _read_statement(frames["cashflow"], CF_ITEMS, "Cash flow", errors, warnings)
    debt = _read_existing_debt(frames["existing_debt"], errors, warnings)
    profile = _read_key_value(frames["applicant"], APPLICANT_FIELDS)
    proposed = _read_key_value(frames["proposed"], PROPOSED_FIELDS)

    if errors:
        raise DataValidationError(errors)

    # ---- year alignment -------------------------------------------------- #
    year_sets = [list(bs.columns), list(pl.columns), list(cf.columns)]
    if not (year_sets[0] == year_sets[1] == year_sets[2]):
        raise DataValidationError(["Fiscal-year columns differ across Balance Sheet / P&L / Cash Flow sheets."])
    years = year_sets[0]
    if len(years) != 3:
        warnings.append(f"Expected 3 years of audited financials, received {len(years)}; trends may be less reliable.")

    # ---- profile & proposal typing -------------------------------------- #
    profile["name"] = str(profile.get("name") or "Unnamed applicant")
    for k in ("cin", "industry", "constitution", "rating"):
        profile[k] = "" if profile.get(k) is None or (isinstance(profile[k], float) and np.isnan(profile[k])) else str(profile[k])
    for k in ("inc_year", "promoter_holding_pct", "bureau_score"):
        profile[k] = pd.to_numeric(profile.get(k), errors="coerce")
    for k in ("amount", "tenure_years", "rate_pct"):
        proposed[k] = pd.to_numeric(proposed.get(k), errors="coerce")
        if pd.isna(proposed[k]):
            errors.append(f"Proposed facility: '{k}' is missing or not numeric.")
    for k in ("moratorium_months", "refinance_amount", "collateral_value"):
        v = pd.to_numeric(proposed.get(k), errors="coerce")
        proposed[k] = 0.0 if pd.isna(v) else float(v)
    proposed["facility_type"] = str(proposed.get("facility_type") or "Term Loan")
    proposed["purpose"] = str(proposed.get("purpose") or "")
    if errors:
        raise DataValidationError(errors)

    # ---- sanity checks (warnings only) ---------------------------------- #
    assets = bs.loc[["Net Fixed Assets", "Capital Work in Progress", "Intangible Assets", "Non-Current Investments",
                     "Other Non-Current Assets", "Inventories", "Trade Receivables", "Cash & Bank Balances",
                     "Other Current Assets"]].sum()
    liabs = bs.loc[["Share Capital", "Reserves & Surplus", "Long Term Borrowings", "Short Term Borrowings",
                    "Current Maturities of LTD", "Trade Payables", "Other Current Liabilities",
                    "Other Non-Current Liabilities"]].sum()
    gap = (assets - liabs).abs()
    for y in years:
        if gap[y] > max(0.5, 0.005 * assets[y]):
            warnings.append(f"Balance sheet {y} does not balance (assets - liabilities = {assets[y] - liabs[y]:,.2f} Cr).")
    bs_score = profile["bureau_score"]
    if pd.isna(bs_score):
        warnings.append("No credit bureau score supplied - bureau metric excluded from scorecard and policy checks.")
    elif not (300 <= bs_score <= 900):
        warnings.append(f"Credit bureau score {bs_score:g} is outside the 300-900 range - please verify.")
    if not (10 <= proposed["amount"] <= 50):
        warnings.append(f"Requested amount ₹{proposed['amount']:,.1f} Cr is outside the 10-50 Cr target ticket size.")

    return ApplicantData(profile, years, bs, pl, cf, debt, proposed, warnings)
