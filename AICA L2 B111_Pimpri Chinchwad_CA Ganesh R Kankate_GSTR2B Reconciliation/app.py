"""
Tally Purchase Register  ->  Standardisation  ->  Multi-tier GSTR-2B Reconciliation
================================================================================

Run with:   streamlit run app.py

Stage 1 : Clean & standardise the Tally Purchase Register (columnar export).
Stage 2 : Segregate unregistered / invalid-GSTIN entries (Non-2B).
Stage 3 : Multi-tier reconciliation against the GSTR-2B (B2B sheet)
          Tier 1 - Strict exact match      (GSTIN + exact Supplier Invoice No.)
          Tier 2 - Normalised exact match  (GSTIN + cleaned invoice no.)
          Tier 3 - GSTIN total match       (GSTIN-level totals within tolerance)
          Tier 4 - Unmatched Books vs 2B   (variance report)
Stage 4 : Formatted multi-tab Excel workbook, downloaded in one click.
"""

from __future__ import annotations

import io
import re
from datetime import date, datetime

import numpy as np
import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
LOOSE_GSTIN_REGEX = re.compile(r"^[0-9A-Z]{15}$")  # used to spot data rows in 2B

SHEET_CLEAN = "Cleaned_Purchase_Register"
SHEET_T1 = "1_Exact_Matched"
SHEET_T2 = "2_Normalized_Exact_Matched"
SHEET_T3 = "3_GSTIN_Total_Matched"
SHEET_UNREG = "5_Unregistered_Non_2B"
SHEET_UNMATCHED = "6_Unmatched_Books_vs_2B"
SHEET_SUMMARY = "0_Summary"
SHEET_2B = "GSTR2B_Cleaned"

STATUS_BOOKS_ONLY = "In Books, not in GSTR-2B"
STATUS_2B_ONLY = "In GSTR-2B, not in Books"


# ----------------------------------------------------------------------------
# Generic helpers
# ----------------------------------------------------------------------------
def canon(value) -> str:
    """Lower-case alphanumeric form of a header, for keyword matching."""
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def to_str(value) -> str:
    """Safe string conversion (handles NaN, 123.0 -> '123', dates)."""
    if value is None:
        return ""
    if isinstance(value, float):
        if np.isnan(value):
            return ""
        if value.is_integer():
            return str(int(value))
    if isinstance(value, (pd.Timestamp, datetime, date)):
        if pd.isna(value):
            return ""
        return value.strftime("%d-%m-%Y")
    if value is pd.NaT:
        return ""
    s = str(value).strip()
    return "" if s.lower() in ("nan", "none", "nat") else s


def to_number(value) -> float:
    """
    Convert Tally/Excel amounts to float.
    Handles commas, ₹, '(1,000)', '1,000.00 Cr' (negative) and '1,000 Dr'.
    Returns NaN for genuinely non-numeric text (used to detect text columns).
    """
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return 0.0 if pd.isna(value) else float(value)
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return np.nan
    s = str(value).strip()
    if s == "" or s.lower() in ("nan", "none", "-"):
        return 0.0
    negative = False
    low = s.lower()
    if low.endswith("cr"):
        negative, s = True, s[:-2]
    elif low.endswith("dr"):
        s = s[:-2]
    s = s.replace(",", "").replace("₹", "").replace("Rs.", "").strip()
    if s.startswith("(") and s.endswith(")"):
        negative, s = True, s[1:-1]
    try:
        n = float(s)
    except ValueError:
        return np.nan
    return -abs(n) if negative else n


def parse_date(value):
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value)
    if isinstance(value, (int, float)) and not pd.isna(value) and 20000 < value < 80000:
        return pd.Timestamp("1899-12-30") + pd.Timedelta(days=float(value))  # Excel serial
    s = to_str(value)
    if not s:
        return pd.NaT
    try:
        if re.match(r"^\d{4}-\d{1,2}-\d{1,2}", s):  # ISO yyyy-mm-dd: never day-first
            return pd.to_datetime(s[:10], format="%Y-%m-%d")
        return pd.to_datetime(s, dayfirst=True)
    except (ValueError, TypeError, OverflowError):
        return pd.NaT


def make_unique(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for n in names:
        if n in seen:
            seen[n] += 1
            out.append(f"{n}_{seen[n]}")
        else:
            seen[n] = 0
            out.append(n)
    return out


def find_col(columns, patterns, exclude=(), exact_first=True):
    """Return the first column whose canonical name equals / contains a pattern."""
    cmap = {c: canon(c) for c in columns}
    pats = [canon(p) for p in patterns]
    excl = [canon(e) for e in exclude]
    if exact_first:
        for p in pats:
            for c, cc in cmap.items():
                if cc == p and not any(e in cc for e in excl):
                    return c
    for p in pats:
        for c, cc in cmap.items():
            if p in cc and not any(e in cc for e in excl):
                return c
    return None


def clean_invoice_number(inv) -> str:
    """
    Normalise an invoice number for Tier-2 matching:
      * upper-case (case-insensitive)
      * strip leading zeros of every numeric block  (INV/001 == INV/1)
      * remove '/', '-', spaces and any other separators
      * strip any remaining leading zeros
    """
    s = to_str(inv).upper()
    if not s:
        return ""
    s = re.sub(r"(?<![0-9])0+(?=[0-9])", "", s)
    s = re.sub(r"[^0-9A-Z]", "", s)
    stripped = s.lstrip("0")
    return stripped if stripped else s


def strict_invoice(inv) -> str:
    """Tier-1 key: the invoice number exactly as typed (outer spaces trimmed)."""
    return to_str(inv)


def is_valid_gstin(g: str) -> bool:
    return bool(GSTIN_REGEX.match(g or ""))


def read_sheet(file_bytes: bytes, sheet) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet, header=None, dtype=object)


def find_header_row(raw: pd.DataFrame, must: tuple[str, ...], scan: int = 80):
    """Find the first row containing every keyword in `must` (canonical match)."""
    for i in range(min(len(raw), scan)):
        cells = [canon(v) for v in raw.iloc[i].tolist() if to_str(v)]
        if all(any(c == m or c.startswith(m) for c in cells) for m in must):
            return i
    return None


# ----------------------------------------------------------------------------
# STAGE 1 : Tally Purchase Register standardisation
# ----------------------------------------------------------------------------
# Words that mark a ledger as a PURCHASE / EXPENSE (value) ledger. If any of these
# appear, the ledger goes to Taxable even if its name also says IGST/CGST/SGST,
# e.g. "Purchase IGST 18%", "IGST Purchases", "Puurchases IGST", "Labour Charges IGST".
PURCHASE_WORDS = re.compile(
    r"pu+r|labou?r|charge|expense|exps?\b|service|job\s*work|freight|cartage|"
    r"material|consumable|stores|spares|repair|maintenance|rent|hire|fees|"
    r"commission|goods|inward|interstate|inter\s*state|intrastate|intra\s*state|"
    r"local|import|stock|asset|machinery|equipment|packing|transport|contract",
    re.IGNORECASE,
)
# Words that mark a GST ledger as a TAX ledger even if a purchase word also appears.
TAX_LEDGER_WORDS = re.compile(
    r"\binput|\bitc\b|payable|receivable|\boutput|credit\s*ledger|\brcm\b|reverse\s*charge",
    re.IGNORECASE,
)


def classify_ledger(name: str) -> str:
    """
    Bucket a numeric ledger column of the Tally register.

    GST tax ledgers  -> only when the name has IGST/CGST/SGST *and* no purchase /
                        expense word, e.g. "Input IGST 18%", "IGST Input", "IGST @18%".
    Everything else  -> Taxable  (e.g. "Purchase IGST 18%", "Labour Charges IGST").
    """
    low = str(name).lower()
    c = canon(name)

    def word(token):
        return re.search(rf"(?<![a-z]){token}(?![a-z])", low) is not None

    if "grosstotal" in c:
        return "gross"
    if c in ("value", "quantity", "qty", "rate", "altunits", "billedqty", "actualqty"):
        return "info"
    if word("tds") or "taxdeducted" in c:
        return "tds"
    if word("tcs") or "taxcollected" in c:
        return "other"
    if "roundoff" in c or "roundedoff" in c or "rounding" in c:
        return "other"

    # "Input IGST on Purchases" is still a TAX ledger -> input-type words win.
    is_tax_named = TAX_LEDGER_WORDS.search(low) is not None
    is_purchase = PURCHASE_WORDS.search(low) is not None and not is_tax_named
    if not is_purchase:
        if "cess" in c:
            return "other"
        if word("igst") or "integratedtax" in c:
            return "igst"
        if word("cgst") or "centraltax" in c:
            return "cgst"
        if word("sgst") or word("utgst") or "statetax" in c or "uttax" in c:
            return "sgst"
    if word("sez"):
        return "sez"
    return "taxable"


GST_SLABS = (0.1, 0.25, 1.5, 3, 5, 6, 12, 18, 28, 40)


def gst_rate_check(taxable: float, igst: float, cgst: float, sgst: float, tol: float):
    """Effective GST rate = (IGST+CGST+SGST) / Taxable, checked against standard slabs."""
    tax = igst + cgst + sgst
    if abs(taxable) < 0.005:
        return (np.nan, "No Tax" if abs(tax) < 0.005 else "CHECK - Taxable is 0 but tax booked")
    rate = tax / taxable * 100
    if abs(tax) < 0.005:
        return (0.0, "No GST (0%)")
    if abs(igst) > 0.005 and (abs(cgst) > 0.005 or abs(sgst) > 0.005):
        return (round(rate, 2), "CHECK - both IGST and CGST/SGST booked")
    if abs(igst) < 0.005 and abs(cgst - sgst) > max(tol, 0.01):
        return (round(rate, 2), "CHECK - CGST and SGST differ")
    slab = min(GST_SLABS, key=lambda s: abs(s - rate))
    expected = taxable * slab / 100
    if abs(rate - slab) <= 0.1 or abs(tax - expected) <= tol:
        return (round(rate, 2), f"OK - {slab:g}%")
    return (round(rate, 2), "CHECK - not a standard GST rate (mixed rates / wrong ledger?)")


def standardize_tally(raw: pd.DataFrame, tol: float = 1.0):
    """Return (cleaned_df, info_dict)."""
    h = find_header_row(raw, ("date", "particulars"))
    if h is None:
        raise ValueError(
            "Could not find the header row in the Tally sheet "
            "(looked for a row containing both 'Date' and 'Particulars')."
        )

    headers = make_unique(
        [to_str(v) or f"Column_{j + 1}" for j, v in enumerate(raw.iloc[h].tolist())]
    )
    df = raw.iloc[h + 1 :].copy()
    df.columns = headers
    df = df.dropna(how="all")

    c_date = find_col(headers, ["Date"], exclude=["invoice", "supplier", "bill", "ref"])
    c_part = find_col(headers, ["Particulars"])
    c_vtype = find_col(headers, ["Voucher Type", "Vch Type"])
    c_vno = find_col(headers, ["Voucher No.", "Vch No.", "Voucher Number"])
    c_inv = find_col(
        headers,
        ["Supplier Invoice No.", "Supplier Inv No", "Supplier Invoice Number",
         "Bill No", "Reference No", "Ref No"],
        exclude=["date"],
    )
    c_inv_date = find_col(
        headers, ["Supplier Invoice Date", "Supplier Inv Date", "Bill Date", "Reference Date"]
    )
    c_gstin = find_col(headers, ["GSTIN/UIN", "GSTIN", "GST No"])
    c_gross = find_col(headers, ["Gross Total"])

    if c_gstin is None:
        raise ValueError(
            "No 'GSTIN/UIN' column found in the Tally register. In Tally, open the "
            "Purchase Register (columnar), press F12 / Alt+F5 and enable 'Show GSTIN/UIN', "
            "then export again."
        )
    if c_gross is None:
        raise ValueError("No 'Gross Total' column found in the Tally register.")

    # ---- Strip title rows, Grand Totals and blank / summary rows ----------
    part = df[c_part].map(to_str)
    is_total = part.str.fullmatch(r"(?i)\s*(grand\s+)?(sub\s*)?total\s*:?\s*")
    dates = df[c_date].map(parse_date) if c_date else pd.Series(pd.NaT, index=df.index)
    keep = dates.notna() & ~is_total & (part != "")
    if keep.sum() == 0 and c_vno:  # fallback: date column not parseable
        keep = (df[c_vno].map(to_str) != "") & ~is_total
    removed_rows = int(len(df) - keep.sum())
    df = df[keep].copy()
    dates = dates[keep]

    # ---- Classify remaining columns into text vs numeric ledgers ----------
    id_cols = [c for c in (c_date, c_part, c_vtype, c_vno, c_inv, c_inv_date, c_gstin) if c]
    other_text_cols, ledger_cols = [], []
    numeric_data = {}
    for col in headers:
        if col in id_cols or col == c_gross:
            continue
        series = df[col]
        non_empty = series.map(to_str) != ""
        if non_empty.sum() == 0:
            if not col.startswith("Column_"):
                numeric_data[col] = pd.Series(0.0, index=df.index)
                ledger_cols.append(col)
            continue
        nums = series.map(to_number)
        numeric_share = nums[non_empty].notna().mean()
        if numeric_share >= 0.8:
            numeric_data[col] = nums.fillna(0.0).astype(float)
            ledger_cols.append(col)
        else:
            other_text_cols.append(col)

    buckets = {col: classify_ledger(col) for col in ledger_cols}

    def bucket_sum(kind):
        cols = [c for c, k in buckets.items() if k == kind]
        if not cols:
            return pd.Series(0.0, index=df.index)
        return pd.concat([numeric_data[c] for c in cols], axis=1).sum(axis=1)

    gross = df[c_gross].map(to_number).fillna(0.0).astype(float)
    taxable = bucket_sum("taxable")
    igst, cgst, sgst = bucket_sum("igst"), bucket_sum("cgst"), bucket_sum("sgst")
    sez = bucket_sum("sez")
    # TDS reduces the amount payable to the party -> keep it as a negative figure
    tds = -bucket_sum("tds").abs() + 0.0  # "+ 0.0" turns -0.0 into 0.0
    other = bucket_sum("other")

    out = pd.DataFrame(index=df.index)
    out["Date"] = dates.dt.normalize() if c_date else pd.NaT
    out["Particulars"] = df[c_part].map(to_str)
    out["Voucher Type"] = df[c_vtype].map(to_str) if c_vtype else ""
    out["Voucher No."] = df[c_vno].map(to_str) if c_vno else ""
    out["Supplier Invoice No."] = df[c_inv].map(to_str) if c_inv else ""  # right after Voucher No.
    if c_inv_date:
        out["Supplier Invoice Date"] = df[c_inv_date].map(parse_date)
    out["GSTIN/UIN"] = df[c_gstin].map(to_str).str.upper().str.replace(r"\s+", "", regex=True)
    for col in other_text_cols:
        out[col] = df[col].map(to_str)

    out["Gross Total"] = gross
    out["Taxable"] = taxable
    out["IGST"] = igst
    out["CGST"] = cgst
    out["SGST"] = sgst
    out["SEZ SALES"] = sez
    out["TDS"] = tds
    out["Diff"] = (gross - (taxable + igst + cgst + sgst + sez + tds)).round(2)
    rate_check = [gst_rate_check(t, i, c, s, tol)
                  for t, i, c, s in zip(taxable, igst, cgst, sgst)]
    out["GST Rate %"] = [r for r, _ in rate_check]
    out["GST Rate Check"] = [s for _, s in rate_check]
    out["Cess / TCS / Round Off"] = other
    # Value comparable with GSTR-2B invoice value (TDS added back)
    out["Books Invoice Value"] = (gross - tds).round(2)

    # Ledger-wise detail (original columns) for audit trail
    reserved = set(out.columns)
    for col in ledger_cols:
        name = f"{col} [Ledger]" if col in reserved else col
        out[name] = numeric_data[col]

    out = out.reset_index(drop=True)
    info = {
        "header_row": h + 1,
        "removed_rows": removed_rows,
        "ledger_buckets": buckets,
        "missing_invoice_col": c_inv is None,
    }
    return out, info


# ----------------------------------------------------------------------------
# GSTR-2B parsing
# ----------------------------------------------------------------------------
def detect_2b_sheet(file_bytes: bytes) -> tuple[list[str], int]:
    sheets = pd.ExcelFile(io.BytesIO(file_bytes)).sheet_names
    for i, s in enumerate(sheets):
        if canon(s) == "b2b":
            return sheets, i
    return sheets, 0


def parse_gstr2b(raw: pd.DataFrame) -> pd.DataFrame:
    """Parse the GSTR-2B B2B sheet (portal format with 2-row headers, or a flat table)."""
    h = None
    for i in range(min(len(raw), 80)):
        cells = [canon(v) for v in raw.iloc[i].tolist() if to_str(v)]
        if any("gstin" in c for c in cells) and len(cells) >= 3:
            h = i
            break
    if h is None:
        raise ValueError("Could not find a header row containing 'GSTIN' in the GSTR-2B sheet.")

    top = [to_str(v) for v in raw.iloc[h].tolist()]
    sub = [to_str(v) for v in raw.iloc[h + 1].tolist()] if h + 1 < len(raw) else [""] * len(top)
    sub_keys = ("invoicenumber", "invoicedate", "invoicevalue", "integratedtax",
                "centraltax", "taxablevalue", "notenumber", "documentnumber")
    two_level = any(any(k in canon(s) for k in sub_keys) for s in sub if s)

    names, last_top = [], ""
    for j, t in enumerate(top):
        if t:
            last_top = t
        s = sub[j] if two_level else ""
        names.append(s or t or (last_top if two_level else "") or f"Column_{j + 1}")
    names = make_unique(names)

    df = raw.iloc[h + (2 if two_level else 1) :].copy()
    df.columns = names

    c_gstin = find_col(names, ["GSTIN of supplier", "GSTIN"])
    c_name = find_col(names, ["Trade/Legal name", "Trade Name", "Legal Name", "Supplier Name", "Name"])
    c_inv = find_col(names, ["Invoice number", "Invoice No", "Document Number", "Note Number", "Bill No"])
    c_date = find_col(names, ["Invoice Date", "Document Date", "Note Date", "Date"],
                      exclude=["filing", "irn"])
    c_val = find_col(names, ["Invoice Value", "Document Value", "Note Value", "Total Value"])
    c_taxable = find_col(names, ["Taxable Value", "Taxable"])
    c_igst = find_col(names, ["Integrated Tax", "IGST"])
    c_cgst = find_col(names, ["Central Tax", "CGST"])
    c_sgst = find_col(names, ["State/UT Tax", "State Tax", "SGST", "UTGST"])
    c_cess = find_col(names, ["Cess"])
    c_itc = find_col(names, ["ITC Availability", "ITC Available"])
    c_rc = find_col(names, ["Reverse Charge"])
    c_period = find_col(names, ["GSTR-1/IFF/GSTR-5 Period", "Period"], exclude=["date"])

    if c_gstin is None:
        raise ValueError("Could not find a 'GSTIN of supplier' column in the GSTR-2B sheet.")
    if c_inv is None:
        raise ValueError("Could not find an 'Invoice number' column in the GSTR-2B sheet.")

    g = pd.DataFrame(index=df.index)
    g["2B GSTIN"] = df[c_gstin].map(to_str).str.upper().str.replace(r"\s+", "", regex=True)
    df = df[g["2B GSTIN"].str.match(LOOSE_GSTIN_REGEX)]  # drops totals / blanks / notes
    g = g.loc[df.index]

    def num(col):
        return df[col].map(to_number).fillna(0.0).astype(float) if col else 0.0

    g["2B Supplier Name"] = df[c_name].map(to_str) if c_name else ""
    g["2B Invoice No."] = df[c_inv].map(to_str)
    g["2B Invoice Date"] = df[c_date].map(parse_date) if c_date else pd.NaT
    g["2B Taxable"] = num(c_taxable)
    g["2B IGST"] = num(c_igst)
    g["2B CGST"] = num(c_cgst)
    g["2B SGST"] = num(c_sgst)
    g["2B Cess"] = num(c_cess)
    g["2B Invoice Value"] = (
        num(c_val) if c_val else g["2B Taxable"] + g["2B IGST"] + g["2B CGST"] + g["2B SGST"] + g["2B Cess"]
    )
    g["2B ITC Availability"] = df[c_itc].map(to_str) if c_itc else ""
    g["2B Reverse Charge"] = df[c_rc].map(to_str) if c_rc else ""
    g["2B Period"] = df[c_period].map(to_str) if c_period else ""

    # The portal lists one row per invoice per tax rate -> consolidate per invoice
    g = (
        g.groupby(["2B GSTIN", "2B Invoice No."], as_index=False, sort=False)
        .agg(
            {
                "2B Supplier Name": "first",
                "2B Invoice Date": "first",
                "2B Invoice Value": "max",  # repeated on every rate row
                "2B Taxable": "sum",
                "2B IGST": "sum",
                "2B CGST": "sum",
                "2B SGST": "sum",
                "2B Cess": "sum",
                "2B ITC Availability": "first",
                "2B Reverse Charge": "first",
                "2B Period": "first",
            }
        )
    )
    num_cols = ["2B Invoice Value", "2B Taxable", "2B IGST", "2B CGST", "2B SGST", "2B Cess"]
    g[num_cols] = g[num_cols].round(2)
    return g


# ----------------------------------------------------------------------------
# STAGE 2 : Multi-tier reconciliation engine
# ----------------------------------------------------------------------------
COMPARE_PAIRS = [
    ("Books Invoice Value", "2B Invoice Value", "Diff Invoice Value"),
    ("Taxable", "2B Taxable", "Diff Taxable"),
    ("IGST", "2B IGST", "Diff IGST"),
    ("CGST", "2B CGST", "Diff CGST"),
    ("SGST", "2B SGST", "Diff SGST"),
]


def key_match(books: pd.DataFrame, twob: pd.DataFrame, bkey: str, gkey: str) -> pd.DataFrame:
    """One-to-one match on GSTIN + key (duplicates are paired in order, extras fall through)."""
    b = books[books[bkey] != ""].copy()
    g = twob[twob[gkey] != ""].copy()
    b["_seq"] = b.groupby(["GSTIN/UIN", bkey]).cumcount()
    g["_seq"] = g.groupby(["2B GSTIN", gkey]).cumcount()
    return b.merge(
        g,
        left_on=["GSTIN/UIN", bkey, "_seq"],
        right_on=["2B GSTIN", gkey, "_seq"],
        how="inner",
        suffixes=("", "_2b"),
    )


def format_matched(m: pd.DataFrame, tier_label: str, tol: float) -> pd.DataFrame:
    cols = [
        "Date", "Particulars", "Voucher Type", "Voucher No.", "Supplier Invoice No.",
        "Supplier Invoice Date", "GSTIN/UIN", "2B Supplier Name", "2B Invoice No.",
        "2B Invoice Date",
    ]
    out = pd.DataFrame({"Match Tier": tier_label}, index=m.index)
    for c in cols:
        if c in m.columns:
            out[c] = m[c]
    out["Gross Total"] = m["Gross Total"]
    out["TDS"] = m["TDS"]
    within = pd.Series(True, index=m.index)
    for bcol, gcol, dcol in COMPARE_PAIRS:
        out[f"Books {bcol}" if not bcol.startswith("Books") else bcol] = m[bcol]
        out[gcol] = m[gcol]
        out[dcol] = (m[bcol] - m[gcol]).round(2)
        within &= out[dcol].abs() <= tol
    out["2B ITC Availability"] = m["2B ITC Availability"]
    out["2B Period"] = m["2B Period"]
    out["Value Status"] = np.where(within, "Matched", "Matched - Amount Mismatch")
    return out.reset_index(drop=True)


def reconcile(registered: pd.DataFrame, twob: pd.DataFrame, tol: float) -> dict:
    books = registered.copy()
    books["_bid"] = np.arange(len(books))
    books["_inv_raw"] = books["Supplier Invoice No."].map(strict_invoice)
    books["_inv_norm"] = books["Supplier Invoice No."].map(clean_invoice_number)

    g = twob.copy()
    g["_gid"] = np.arange(len(g))
    g["_inv_raw"] = g["2B Invoice No."].map(strict_invoice)
    g["_inv_norm"] = g["2B Invoice No."].map(clean_invoice_number)

    # Tier 1 - strict exact
    t1 = key_match(books, g, "_inv_raw", "_inv_raw")
    rem_b = books[~books["_bid"].isin(t1["_bid"])]
    rem_g = g[~g["_gid"].isin(t1["_gid"])]

    # Tier 2 - normalised exact
    t2 = key_match(rem_b, rem_g, "_inv_norm", "_inv_norm")
    rem_b = rem_b[~rem_b["_bid"].isin(t2["_bid"])]
    rem_g = rem_g[~rem_g["_gid"].isin(t2["_gid"])]

    # Tier 3 - GSTIN-level totals within tolerance
    b_tot = rem_b.groupby("GSTIN/UIN")["Books Invoice Value"].sum()
    g_tot = rem_g.groupby("2B GSTIN")["2B Invoice Value"].sum()
    both = b_tot.to_frame("Books Total").join(g_tot.rename("2B Total"), how="inner")
    both["GSTIN Diff"] = (both["Books Total"] - both["2B Total"]).round(2)
    t3_gstins = both[both["GSTIN Diff"].abs() <= tol].index

    t3_b = rem_b[rem_b["GSTIN/UIN"].isin(t3_gstins)]
    t3_g = rem_g[rem_g["2B GSTIN"].isin(t3_gstins)]
    rem_b = rem_b[~rem_b["GSTIN/UIN"].isin(t3_gstins)]
    rem_g = rem_g[~rem_g["2B GSTIN"].isin(t3_gstins)]

    t3 = stack_sides(t3_b, t3_g, "Matched on GSTIN total")
    if not t3.empty:
        t3 = t3.merge(both[["Books Total", "2B Total", "GSTIN Diff"]],
                      left_on="GSTIN", right_index=True, how="left")
        t3 = t3.rename(columns={"Books Total": "GSTIN Books Total",
                                "2B Total": "GSTIN 2B Total"})
    t3 = t3.drop(columns=[c for c in t3.columns if c.startswith("_")], errors="ignore")

    # Tier 4 - unmatched variance report
    dup_keys = books.groupby(["GSTIN/UIN", "_inv_norm"])["_bid"].transform("count")
    dup_bids = set(books.loc[(dup_keys > 1) & (books["_inv_norm"] != ""), "_bid"])
    unmatched = build_unmatched(rem_b, rem_g, dup_bids, tol)

    return {
        "t1": format_matched(t1, "Tier 1 - Exact", tol),
        "t2": format_matched(t2, "Tier 2 - Normalised", tol),
        "t3": t3,
        "unmatched": unmatched,
        "counts": {
            "t1": (len(t1), t1["Books Invoice Value"].sum(), t1["2B Invoice Value"].sum()),
            "t2": (len(t2), t2["Books Invoice Value"].sum(), t2["2B Invoice Value"].sum()),
            "t3": (len(t3_b), len(t3_g), t3_b["Books Invoice Value"].sum(),
                   t3_g["2B Invoice Value"].sum(), len(t3_gstins)),
            "t4": (len(rem_b), len(rem_g), rem_b["Books Invoice Value"].sum(),
                   rem_g["2B Invoice Value"].sum()),
        },
    }


def stack_sides(b: pd.DataFrame, g: pd.DataFrame, status_b: str, status_g: str | None = None):
    """Put Books rows and 2B rows into one common layout."""
    status_g = status_g or status_b
    rows_b = pd.DataFrame(
        {
            "Status": status_b,
            "Source": "Books",
            "GSTIN": b["GSTIN/UIN"],
            "Party / Supplier Name": b["Particulars"],
            "Voucher No.": b["Voucher No."],
            "Voucher Date": b["Date"],
            "Invoice No.": b["Supplier Invoice No."],
            "Invoice Date": b["Supplier Invoice Date"] if "Supplier Invoice Date" in b else pd.NaT,
            "Invoice Value": b["Books Invoice Value"],
            "Taxable": b["Taxable"],
            "IGST": b["IGST"],
            "CGST": b["CGST"],
            "SGST": b["SGST"],
            "_bid": b["_bid"],
        }
    )
    rows_g = pd.DataFrame(
        {
            "Status": status_g,
            "Source": "GSTR-2B",
            "GSTIN": g["2B GSTIN"],
            "Party / Supplier Name": g["2B Supplier Name"],
            "Voucher No.": "",
            "Voucher Date": pd.NaT,
            "Invoice No.": g["2B Invoice No."],
            "Invoice Date": g["2B Invoice Date"],
            "Invoice Value": g["2B Invoice Value"],
            "Taxable": g["2B Taxable"],
            "IGST": g["2B IGST"],
            "CGST": g["2B CGST"],
            "SGST": g["2B SGST"],
            "_gid": g["_gid"],
            "_inv_norm": g["_inv_norm"],
        }
    )
    frames = [f for f in (rows_b, rows_g) if not f.empty]
    if not frames:
        return pd.DataFrame(columns=list(rows_b.columns))
    out = pd.concat(frames, ignore_index=True)
    return out.sort_values(["GSTIN", "Source"], kind="stable").reset_index(drop=True)


def build_unmatched(rem_b, rem_g, dup_bids, tol) -> pd.DataFrame:
    out = stack_sides(rem_b, rem_g, STATUS_BOOKS_ONLY, STATUS_2B_ONLY)
    if out.empty:
        return out.drop(columns=[c for c in out.columns if c.startswith("_")], errors="ignore")

    b_tot = rem_b.groupby("GSTIN/UIN")["Books Invoice Value"].sum()
    g_tot = rem_g.groupby("2B GSTIN")["2B Invoice Value"].sum()
    out["GSTIN Books Total"] = out["GSTIN"].map(b_tot).fillna(0.0)
    out["GSTIN 2B Total"] = out["GSTIN"].map(g_tot).fillna(0.0)
    out["GSTIN Net Variance"] = (out["GSTIN Books Total"] - out["GSTIN 2B Total"]).round(2)

    gstins_b, gstins_g = set(b_tot.index), set(g_tot.index)
    remarks = []
    for _, r in out.iterrows():
        notes = []
        if r["Source"] == "Books":
            if r.get("_bid") in dup_bids:
                notes.append("Possible duplicate booking (same GSTIN + invoice no. in books)")
            if not to_str(r["Invoice No."]):
                notes.append("Supplier Invoice No. blank in books")
            if r["GSTIN"] in gstins_g:
                cand = rem_g[(rem_g["2B GSTIN"] == r["GSTIN"])
                             & ((rem_g["2B Invoice Value"] - r["Invoice Value"]).abs() <= tol)]
                if not cand.empty:
                    notes.append("Probable match - same value in 2B as Inv "
                                 + ", ".join(cand["2B Invoice No."].astype(str).head(3)))
                else:
                    notes.append("GSTIN present in 2B - check invoice no. / amount")
            else:
                notes.append("Supplier invoice not reflected in 2B - follow up / ITC at risk")
        else:
            if r["GSTIN"] in gstins_b:
                notes.append("GSTIN present in books - check invoice no. / amount")
            else:
                notes.append("Not booked in Tally - verify & account / claim ITC")
        remarks.append("; ".join(notes))
    out["Remarks"] = remarks
    return out.drop(columns=[c for c in out.columns if c.startswith("_")], errors="ignore")


# ----------------------------------------------------------------------------
# Excel export
# ----------------------------------------------------------------------------
def build_workbook(sheets: dict[str, pd.DataFrame]) -> bytes:
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df = df.drop(columns=[c for c in df.columns if str(c).startswith("_")], errors="ignore")
            if df.columns.empty:
                df = pd.DataFrame({"Info": ["No records in this category"]})
            df.to_excel(writer, sheet_name=name[:31], index=False)
            ws = writer.sheets[name[:31]]
            ws.freeze_panes = "A2"
            if len(df):
                ws.auto_filter.ref = ws.dimensions
            for j, col in enumerate(df.columns, start=1):
                cell = ws.cell(row=1, column=j)
                cell.fill, cell.font = header_fill, header_font
                cell.alignment = Alignment(wrap_text=True, vertical="center")
                letter = get_column_letter(j)
                sample = df[col].head(300)
                width = max([len(str(col))] + [len(to_str(v)) for v in sample]) + 2
                ws.column_dimensions[letter].width = min(max(width, 10), 45)
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    fmt = "dd-mm-yyyy"
                elif pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col]):
                    fmt = "#,##0.00"
                else:
                    continue
                for row in range(2, len(df) + 2):
                    ws.cell(row=row, column=j).number_format = fmt
            ws.row_dimensions[1].height = 32
    return buf.getvalue()


def build_summary(clean, unreg, twob, rec, tol) -> pd.DataFrame:
    c = rec["counts"]
    rows = [
        ("Purchase Register (cleaned)", len(clean), clean["Books Invoice Value"].sum(), None, None),
        ("GSTR-2B invoices (B2B, consolidated)", None, None, len(twob), twob["2B Invoice Value"].sum()),
        ("Tier 1 - Strict Exact Match", c["t1"][0], c["t1"][1], c["t1"][0], c["t1"][2]),
        ("Tier 2 - Normalised Exact Match", c["t2"][0], c["t2"][1], c["t2"][0], c["t2"][2]),
        (f"Tier 3 - GSTIN Total Match ({c['t3'][4]} GSTINs)", c["t3"][0], c["t3"][2], c["t3"][1], c["t3"][3]),
        ("Tier 4 - Unmatched (variance)", c["t4"][0], c["t4"][2], c["t4"][1], c["t4"][3]),
        ("Unregistered / invalid GSTIN (Non-2B)", len(unreg), unreg["Books Invoice Value"].sum(), None, None),
    ]
    df = pd.DataFrame(rows, columns=["Category", "Books Count", "Books Value",
                                     "2B Count", "2B Value"])
    df.loc[len(df)] = [f"Rounding tolerance used: ₹{tol:,.2f}", None, None, None, None]
    return df


# ----------------------------------------------------------------------------
# STREAMLIT UI
# ----------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Tally vs GSTR-2B Reconciliation", page_icon="📊", layout="wide")
    st.title("📊 Tally Purchase Register & GSTR-2B Reconciliation")
    st.caption(
        "Stage 1: clean the Tally register · Stage 2: multi-tier reconciliation "
        "(Exact → Normalised → GSTIN Total → Unmatched) · one-click Excel export"
    )

    c1, c2 = st.columns(2)
    with c1:
        tally_file = st.file_uploader("Tally Purchase Register (.xlsx)", type=["xlsx"], key="tally")
    with c2:
        gstr_file = st.file_uploader("GSTR-2B Excel Sheet (.xlsx)", type=["xlsx"], key="gstr2b")

    s1, s2, s3 = st.columns(3)
    tally_sheet = gstr_sheet = None
    if tally_file:
        t_bytes = tally_file.getvalue()
        t_sheets = pd.ExcelFile(io.BytesIO(t_bytes)).sheet_names
        with s1:
            tally_sheet = st.selectbox("Tally sheet", t_sheets, index=0)
    if gstr_file:
        g_bytes = gstr_file.getvalue()
        g_sheets, g_idx = detect_2b_sheet(g_bytes)
        with s2:
            gstr_sheet = st.selectbox("GSTR-2B sheet (B2B)", g_sheets, index=g_idx)
    with s3:
        tolerance = st.number_input("Rounding Tolerance Threshold (₹)", min_value=0.0,
                                    value=1.00, step=0.50, format="%.2f")

    run = st.button("▶ Run Reconciliation", type="primary",
                    disabled=not (tally_file and gstr_file))

    if run:
        try:
            with st.spinner("Stage 1 - standardising Tally Purchase Register..."):
                clean, info = standardize_tally(read_sheet(t_bytes, tally_sheet), tolerance)
                valid = clean["GSTIN/UIN"].map(is_valid_gstin)
                unreg = clean[~valid].reset_index(drop=True)
                registered = clean[valid].reset_index(drop=True)
            with st.spinner("Reading GSTR-2B..."):
                twob = parse_gstr2b(read_sheet(g_bytes, gstr_sheet))
            with st.spinner("Stage 2 - multi-tier reconciliation..."):
                rec = reconcile(registered, twob, tolerance)
                summary = build_summary(clean, unreg, twob, rec, tolerance)
                workbook = build_workbook(
                    {
                        SHEET_SUMMARY: summary,
                        SHEET_CLEAN: clean,
                        SHEET_T1: rec["t1"],
                        SHEET_T2: rec["t2"],
                        SHEET_T3: rec["t3"],
                        SHEET_UNREG: unreg,
                        SHEET_UNMATCHED: rec["unmatched"],
                        SHEET_2B: twob,
                    }
                )
            st.session_state["result"] = {
                "info": info, "clean": clean, "unreg": unreg, "twob": twob,
                "rec": rec, "summary": summary, "workbook": workbook,
            }
        except Exception as exc:  # surface any parsing issue to the user
            st.session_state.pop("result", None)
            st.error(f"Processing failed: {exc}")

    res = st.session_state.get("result")
    if not res:
        st.info("Upload both files and click **Run Reconciliation**.")
        return

    info, rec = res["info"], res["rec"]
    st.success(
        f"Done. Header found on row {info['header_row']}; "
        f"{info['removed_rows']} title/total/blank rows removed."
    )
    if info["missing_invoice_col"]:
        st.warning("No 'Supplier Invoice No.' column found in Tally - Tiers 1 & 2 cannot match.")
    diff_rows = int((res["clean"]["Diff"].abs() > tolerance).sum())
    if diff_rows:
        st.warning(f"{diff_rows} voucher(s) have a non-zero 'Diff' (see Cleaned_Purchase_Register).")
    rate_flags = int(res["clean"]["GST Rate Check"].str.startswith("CHECK").sum())
    if rate_flags:
        st.warning(f"{rate_flags} voucher(s) failed the GST rate check - filter "
                   "'GST Rate Check' = CHECK in Cleaned_Purchase_Register and review "
                   "the 'Ledger mapping' tab.")

    m = st.columns(6)
    m[0].metric("Register rows", len(res["clean"]))
    m[1].metric("Tier 1 exact", len(rec["t1"]))
    m[2].metric("Tier 2 normalised", len(rec["t2"]))
    m[3].metric("Tier 3 GSTIN rows", rec["counts"]["t3"][0])
    m[4].metric("Unmatched (Books / 2B)", f"{rec['counts']['t4'][0]} / {rec['counts']['t4'][1]}")
    m[5].metric("Unregistered", len(res["unreg"]))

    st.download_button(
        "📥 Download Reconciliation Workbook (.xlsx)",
        data=res["workbook"],
        file_name=f"GSTR2B_Reconciliation_{datetime.now():%Y%m%d_%H%M}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

    tabs = st.tabs(["Summary", SHEET_CLEAN, SHEET_T1, SHEET_T2, SHEET_T3, SHEET_UNREG,
                    SHEET_UNMATCHED, "Ledger mapping"])
    frames = [res["summary"], res["clean"], rec["t1"], rec["t2"], rec["t3"], res["unreg"],
              rec["unmatched"]]
    for tab, frame in zip(tabs[:-1], frames):
        with tab:
            st.dataframe(frame, use_container_width=True, hide_index=True)
    with tabs[-1]:
        st.caption("How each Tally ledger column was classified when computing the standard columns.")
        st.dataframe(
            pd.DataFrame(list(info["ledger_buckets"].items()), columns=["Ledger column", "Bucket"]),
            use_container_width=True, hide_index=True,
        )


def _launch_streamlit_server():
    """
    Started with plain `python app.py` or IDLE (F5)? Streamlit apps must run via
    `streamlit run`, so start that in its own console window and open the browser.
    """
    import os
    import subprocess
    import sys

    exe = sys.executable
    if os.path.basename(exe).lower() == "pythonw.exe":  # IDLE uses pythonw.exe
        candidate = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.exists(candidate):
            exe = candidate
    script = os.path.abspath(__file__)
    flags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
    subprocess.Popen([exe, "-m", "streamlit", "run", script],
                     cwd=os.path.dirname(script), creationflags=flags)
    print("Starting the app in a new window - your browser will open at http://localhost:8501")
    print("To stop the app, close that new black window.")


if __name__ == "__main__":
    from streamlit import runtime

    if runtime.exists():  # launched with `streamlit run app.py`
        main()
    else:  # launched with `python app.py` / IDLE F5
        _launch_streamlit_server()
