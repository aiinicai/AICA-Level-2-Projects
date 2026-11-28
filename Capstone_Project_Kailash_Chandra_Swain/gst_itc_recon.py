"""
GST ITC Reconciliation App  -  Purchase Register vs GSTR-2B
============================================================
Give it YOUR two files and it produces:
   1. Excel report (formula-driven: Summary, Exceptions, Vendor Risk, Method, full reconciliation, source data)
   2. Word report
   3. PowerPoint deck

Run:      python gst_itc_recon.py          (opens a window; browser page if tkinter is missing)
Command:  python gst_itc_recon.py --books purchase.xlsx --gstr2b gstr2b.xlsx --out results --taxpayer "ABC Ltd" --period "Oct 2026"
Install:  pip install pandas openpyxl python-docx python-pptx

Input files (.xlsx / .xls / .csv) need, in any column order and with common names:
   GSTIN, invoice number, invoice date, taxable value, IGST, CGST, SGST
Optional: supplier name, voucher no., expense category (for blocked-credit check), GSTR-2B portal "B2B" sheet works too.
"""
import argparse
import os
import re
import subprocess
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L


# =====================================================================================
#  ENGINE: matching, classification, ITC impact
# =====================================================================================

# =====================================================================================
#  INPUT: read any user file and convert it to the standard layout the engine needs
# =====================================================================================
ALIASES = {
    "supplier_gstin": ["gstin", "gstinofsupplier", "suppliergstin", "suppliergstno", "ctin", "gstno", "partygstin",
                       "gstinuin", "vendorgstin", "gstnumber", "partygstno", "gstinno"],
    "supplier_name": ["tradelegalname", "tradename", "legalname", "suppliername", "partyname", "party", "vendorname",
                      "vendor", "particulars", "name", "supplier", "ledgername"],
    "invoice_no": ["invoicenumber", "invoiceno", "invno", "invoice", "billno", "billnumber", "supplierinvoiceno",
                   "supplierinvoicenumber", "refno", "documentnumber", "docno", "inum", "partyinvoiceno",
                   "vendorinvoiceno", "invoiceref"],
    "invoice_date": ["invoicedate", "invdate", "date", "billdate", "documentdate", "dt", "supplierinvoicedate",
                     "partyinvoicedate", "vendorinvoicedate"],
    "taxable_value": ["taxablevalue", "taxable", "txval", "assessablevalue", "basicvalue", "taxableamount",
                      "taxableamt", "basicamount"],
    "igst": ["integratedtax", "igst", "igstamount", "iamt", "igstamt"],
    "cgst": ["centraltax", "cgst", "cgstamount", "camt", "cgstamt"],
    "sgst": ["stutaxstatetax", "statetax", "stateuttax", "sgst", "sgstutgst", "sgstamount", "samt", "utgst",
             "sgstamt", "stateutax"],
    "voucher_no": ["voucherno", "vouchernumber", "vchno", "voucher", "entryno", "pvno", "vchnumber"],
    "expense_category": ["expensecategory", "category", "expensehead", "nature", "accounthead", "expensetype",
                         "natureofexpense", "purchaseledger", "expenseledger"],
    "itc_available": ["itcavailable", "itcavailability", "eligibleitc", "itceligible"],
}
REQUIRED = ["supplier_gstin", "invoice_no", "invoice_date", "taxable_value"]


def _key(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _read_raw(path):
    p = Path(path)
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p, header=None, dtype=object)
    xl = pd.ExcelFile(p)
    sheet = next((s for s in xl.sheet_names if s.strip().lower() == "b2b"), xl.sheet_names[0])
    return xl.parse(sheet, header=None, dtype=object)


def read_any(path, label):
    """Read csv/excel, find the header row automatically (portal files have title rows) and rename columns."""
    raw = _read_raw(path)
    best, best_score = 0, -1
    for i in range(min(30, len(raw))):
        keys = {_key(v) for v in raw.iloc[i].dropna()}
        score = sum(any(a in keys for a in al) for al in ALIASES.values())
        if score > best_score:
            best, best_score = i, score
    df = raw.iloc[best + 1:].copy()
    df.columns = [str(v) for v in raw.iloc[best]]
    cmap, used = {}, set()
    for col in df.columns:
        n = _key(col)
        for std, al in ALIASES.items():
            if std not in used and n in al:
                cmap[col] = std
                used.add(std)
                break
    df = df.rename(columns=cmap)
    df = df.loc[:, ~df.columns.duplicated()]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(
            f"[{label}] these columns were not found: {missing}.\n"
            f"Columns in your file: {[str(c) for c in raw.iloc[best].dropna()]}\n"
            "Rename the headers in your file (e.g. 'GSTIN', 'Invoice No', 'Invoice Date', 'Taxable Value', "
            "'IGST', 'CGST', 'SGST') and try again.")
    if not any(c in df.columns for c in ("igst", "cgst", "sgst")):
        raise ValueError(f"[{label}] no IGST / CGST / SGST columns found. Columns: {list(df.columns)}")
    return df


def standardise(df, kind):
    df = df.copy()
    df = df[df["supplier_gstin"].notna() & df["invoice_no"].notna()]
    for c in ("taxable_value", "igst", "cgst", "sgst"):
        df[c] = pd.to_numeric(df[c], errors="coerce") if c in df.columns else 0.0
    df = df[df["taxable_value"].notna()].copy()          # drops sub-header / total rows
    for c in ("igst", "cgst", "sgst"):
        df[c] = df[c].fillna(0.0)
    df["supplier_gstin"] = df["supplier_gstin"].astype(str).str.strip().str.upper().str.replace(r"\s", "", regex=True)
    df["invoice_no"] = df["invoice_no"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    d = pd.to_datetime(df["invoice_date"], errors="coerce", dayfirst=True)
    df["invoice_date"] = d
    if "supplier_name" not in df.columns:
        df["supplier_name"] = ""
    df["supplier_name"] = df["supplier_name"].fillna("").astype(str).str.strip()
    if kind == "books":
        if "voucher_no" not in df.columns:
            df["voucher_no"] = ""
        df["voucher_no"] = df["voucher_no"].fillna("").astype(str).str.strip()
        blank = df["voucher_no"] == ""
        df.loc[blank, "voucher_no"] = [f"ROW{i:05d}" for i in range(1, blank.sum() + 1)]
        if "expense_category" not in df.columns:
            df["expense_category"] = "Not provided"
        df["expense_category"] = df["expense_category"].fillna("Not provided").astype(str)
        cols = ["voucher_no", "supplier_gstin", "supplier_name", "invoice_no", "invoice_date",
                "taxable_value", "igst", "cgst", "sgst", "expense_category"]
    else:
        if "itc_available" not in df.columns:
            df["itc_available"] = "Yes"
        df["itc_available"] = df["itc_available"].fillna("Yes").astype(str)
        cols = ["supplier_gstin", "supplier_name", "invoice_no", "invoice_date",
                "taxable_value", "igst", "cgst", "sgst", "itc_available"]
    return df[cols].reset_index(drop=True)


TOLERANCE = 5.0          # Rs: tax differences up to this are treated as rounding
FUZZY_RATIO = 0.92       # invoice-number similarity for the low-confidence pass
FUZZY_AMT_PCT = 0.02     # taxable value must be within 2% for a fuzzy match
BLOCKED_CATEGORIES = {   # Sec 17(5) style blocked / restricted credits (illustrative)
    "Food & beverages": "Sec 17(5)(b) - food, beverages, outdoor catering",
    "Motor vehicle (passenger car)": "Sec 17(5)(a) - motor vehicles for passenger transport",
}

ISSUE_PRIORITY = ["AMOUNT_MISMATCH", "TAX_HEAD", "GSTIN_TYPO", "DATE_PERIOD",
                  "INV_FORMAT", "ROUNDING"]


# ---------------------------------------------------------------- normalisers
def norm_raw(s):
    return str(s).strip().upper()


def norm_inv(s):
    """Upper-case, drop punctuation/space, strip leading zeros inside digit runs."""
    s = re.sub(r"[^A-Z0-9]", " ", str(s).upper())
    s = re.sub(r"(?<![0-9])0+(?=[0-9])", "", s)      # leading zeros of every number
    return s.replace(" ", "")


def norm_inv_base(s):
    """As norm_inv, additionally ignoring trailing alphabetic suffixes (e.g. '-A')."""
    return re.sub(r"[A-Z]+$", "", norm_inv(s))


def hamming(a, b):
    if len(a) != len(b):
        return 99
    return sum(x != y for x, y in zip(a, b))


# ---------------------------------------------------------------- loading
def load(books_path, b2_path):
    b = standardise(read_any(books_path, "Purchase Register"), "books")
    g = standardise(read_any(b2_path, "GSTR-2B"), "gstr2b")
    for d in (b, g):
        d["tax"] = (d["igst"] + d["cgst"] + d["sgst"]).round(2)
    b["k_raw"] = b["invoice_no"].map(norm_raw)
    g["k_raw"] = g["invoice_no"].map(norm_raw)
    b["k_norm"] = b["invoice_no"].map(norm_inv)
    g["k_norm"] = g["invoice_no"].map(norm_inv)
    b["k_base"] = b["invoice_no"].map(norm_inv_base)
    g["k_base"] = g["invoice_no"].map(norm_inv_base)
    b["bid"] = range(len(b))
    g["gid"] = range(len(g))
    return b, g


# ---------------------------------------------------------------- matching
def match(b, g):
    """Return list of (bid, gid, method, confidence) pairs and set of duplicate bids."""
    # 0. duplicates inside books: same supplier + normalised invoice no. + same tax
    dup_ids = set()
    seen = {}
    for r in b.sort_values("voucher_no").itertuples():
        key = (r.supplier_gstin, r.k_norm, round(r.tax, 0))
        if key in seen:
            dup_ids.add(r.bid)
        else:
            seen[key] = r.bid

    un_b = set(b["bid"]) - dup_ids
    un_g = set(g["gid"])
    pairs = []

    bt = b.set_index("bid")
    gt = g.set_index("gid")

    def run_pass(keyfunc_b, keyfunc_g, method, conf, extra_ok=None):
        nonlocal un_b, un_g
        idx = defaultdict(list)
        for gid in sorted(un_g):
            idx[keyfunc_g(gt.loc[gid])].append(gid)
        for bid in sorted(un_b):
            k = keyfunc_b(bt.loc[bid])
            cands = idx.get(k, [])
            for gid in cands:
                if gid in un_g and (extra_ok is None or extra_ok(bt.loc[bid], gt.loc[gid])):
                    pairs.append((bid, gid, method, conf))
                    un_g.discard(gid)
                    un_b.discard(bid)
                    break

    # Pass 1: exact GSTIN + exact invoice number
    run_pass(lambda r: (r.supplier_gstin, r.k_raw), lambda r: (r.supplier_gstin, r.k_raw),
             "1-Exact", "High")
    # Pass 2: GSTIN + normalised invoice number (case/space/punctuation/leading zeros)
    run_pass(lambda r: (r.supplier_gstin, r.k_norm), lambda r: (r.supplier_gstin, r.k_norm),
             "2-Normalised invoice no.", "High")
    # Pass 3: GSTIN + invoice number ignoring trailing suffix
    run_pass(lambda r: (r.supplier_gstin, r.k_base), lambda r: (r.supplier_gstin, r.k_base),
             "3-Invoice suffix ignored", "Medium")
    # Pass 4: same invoice no., GSTIN differs by <=2 characters (typo) and same state code
    run_pass(lambda r: r.k_norm, lambda r: r.k_norm, "4-GSTIN typo tolerated", "Medium",
             extra_ok=lambda x, y: hamming(x.supplier_gstin, y.supplier_gstin) <= 2
             and x.supplier_gstin[:2] == y.supplier_gstin[:2]
             and abs(x.taxable_value - y.taxable_value) <= 0.02 * max(y.taxable_value, 1))

    # Pass 5: fuzzy invoice number inside same GSTIN, taxable value within 2%
    for bid in sorted(un_b):
        rb = bt.loc[bid]
        best, best_ratio = None, 0
        for gid in un_g:
            rg = gt.loc[gid]
            if rg.supplier_gstin != rb.supplier_gstin:
                continue
            if abs(rb.taxable_value - rg.taxable_value) > FUZZY_AMT_PCT * max(rg.taxable_value, 1):
                continue
            ratio = SequenceMatcher(None, rb.k_norm, rg.k_norm).ratio()
            if ratio >= FUZZY_RATIO and ratio > best_ratio:
                best, best_ratio = gid, ratio
        if best is not None:
            pairs.append((bid, best, "5-Fuzzy (review)", "Low"))
            un_g.discard(best)
            un_b.discard(bid)

    return pairs, dup_ids, un_b, un_g


# ---------------------------------------------------------------- classification
def explain(row):
    """Deterministic explanation text.  >>> Replace body with an LLM call to get free-text
    explanations; the structured fields passed in are all the model would need."""
    i = row["primary_issue"]
    m = row
    fmt = lambda x: f"Rs {x:,.2f}"
    if i == "NOT_IN_2B":
        return (f"Invoice {m['invoice_no_books']} of {m['supplier_name']} ({fmt(m['tax_books'])} tax) "
                "is booked but not reported by the supplier in GSTR-2B.")
    if i == "NOT_IN_BOOKS":
        return (f"Invoice {m['invoice_no_2b']} of {m['supplier_name']} ({fmt(m['tax_2b'])} tax) "
                "appears in GSTR-2B but has not been recorded in the purchase register.")
    if i == "DUPLICATE":
        return (f"Voucher {m['voucher_no']} repeats an invoice already booked "
                f"({m['invoice_no_books']}); ITC of {fmt(m['tax_books'])} is double counted.")
    if i == "AMOUNT_MISMATCH":
        return (f"Tax per books {fmt(m['tax_books'])} vs GSTR-2B {fmt(m['tax_2b'])} "
                f"(difference {fmt(m['tax_diff'])}).")
    if i == "TAX_HEAD":
        return (f"Total tax agrees ({fmt(m['tax_books'])}) but the heads differ - books show "
                f"IGST/CGST/SGST {m['heads_books']}, supplier reported {m['heads_2b']}.")
    if i == "GSTIN_TYPO":
        return (f"Matched on invoice no. and amount, but GSTIN in books ({m['gstin_books']}) "
                f"differs from GSTR-2B ({m['gstin_2b']}).")
    if i == "DATE_PERIOD":
        return (f"Invoice date in books {m['date_books']:%d-%b-%Y} vs {m['date_2b']:%d-%b-%Y} in "
                "GSTR-2B (supplier reported a different date/period).")
    if i == "INV_FORMAT":
        return (f"Same invoice recorded as '{m['invoice_no_books']}' in books and "
                f"'{m['invoice_no_2b']}' in GSTR-2B (format difference only).")
    if i == "ROUNDING":
        return f"Tax differs by {fmt(abs(m['tax_diff']))}, within the Rs {TOLERANCE:.0f} tolerance."
    return "Fully matched."


ACTIONS = {
    "NOT_IN_2B": "Follow up with supplier to file/amend GSTR-1; do not claim ITC until it reflects in GSTR-2B (Sec 16(2)(aa)).",
    "NOT_IN_BOOKS": "Verify receipt of goods/services; if genuine, book the invoice; otherwise ask supplier to correct.",
    "DUPLICATE": "Reverse the duplicate voucher; exclude from GSTR-3B ITC.",
    "AMOUNT_MISMATCH": "Check the invoice copy; correct books or request supplier amendment. Claim only the lower amount.",
    "TAX_HEAD": "Check place of supply; correct tax heads (IGST vs CGST+SGST) in the voucher.",
    "GSTIN_TYPO": "Correct the supplier GSTIN in the vendor master / voucher.",
    "DATE_PERIOD": "Verify invoice date and the period of claim (Sec 16(4) time limit).",
    "INV_FORMAT": "No ITC impact; standardise invoice-number entry.",
    "ROUNDING": "Within tolerance; pass a rounding adjustment if required.",
    "BLOCKED": "Credit blocked under Sec 17(5); ensure it is not claimed in GSTR-3B (review for exceptions).",
    "NONE": "No action.",
}


def heads(r, s=""):
    return f"{r['igst' + s]:,.0f}/{r['cgst' + s]:,.0f}/{r['sgst' + s]:,.0f}"


def reconcile(books_path, b2_path):
    b, g = load(books_path, b2_path)
    pairs, dup_ids, un_b, un_g = match(b, g)
    bt, gt = b.set_index("bid"), g.set_index("gid")
    out = []

    def blocked_reason(cat):
        if cat in BLOCKED_CATEGORIES:
            return BLOCKED_CATEGORIES[cat]
        c = str(cat).lower()
        if re.search(r"food|beverage|catering|canteen|restaurant", c):
            return BLOCKED_CATEGORIES["Food & beverages"]
        if re.search(r"passenger (car|vehicle)|motor car|staff car|company car", c):
            return BLOCKED_CATEGORIES["Motor vehicle (passenger car)"]
        return ""

    # ---- matched pairs
    for bid, gid, method, conf in pairs:
        rb, rg = bt.loc[bid], gt.loc[gid]
        issues = []
        diff = round(rb.tax - rg.tax, 2)
        heads_b = (rb.igst, rb.cgst, rb.sgst)
        heads_g = (rg.igst, rg.cgst, rg.sgst)
        if abs(diff) > TOLERANCE:
            issues.append("AMOUNT_MISMATCH")
        elif abs(diff) > 0.005:
            if abs(sum(heads_b) - sum(heads_g)) <= TOLERANCE and \
                    (rb.igst > 0) != (rg.igst > 0):
                issues.append("TAX_HEAD")
            else:
                issues.append("ROUNDING")
        elif (rb.igst > 0) != (rg.igst > 0):
            issues.append("TAX_HEAD")
        if rb.supplier_gstin != rg.supplier_gstin:
            issues.append("GSTIN_TYPO")
        if abs((rb.invoice_date - rg.invoice_date).days) > 31:
            issues.append("DATE_PERIOD")
        if rb.invoice_no.strip() != rg.invoice_no.strip():
            issues.append("INV_FORMAT")
        primary = next((i for i in ISSUE_PRIORITY if i in issues), "NONE")
        out.append(dict(
            voucher_no=rb.voucher_no, supplier_name=rb.supplier_name,
            gstin_books=rb.supplier_gstin, gstin_2b=rg.supplier_gstin,
            invoice_no_books=rb.invoice_no, invoice_no_2b=rg.invoice_no,
            date_books=rb.invoice_date, date_2b=rg.invoice_date,
            taxable_books=rb.taxable_value, taxable_2b=rg.taxable_value,
            tax_books=rb.tax, tax_2b=rg.tax, tax_diff=diff,
            heads_books=heads(rb), heads_2b=heads(rg),
            category=rb.expense_category, match_method=method, confidence=conf,
            primary_issue=primary, all_issues=", ".join(issues) if issues else "-"))

    # ---- books-only
    for bid in sorted(un_b):
        rb = bt.loc[bid]
        out.append(dict(
            voucher_no=rb.voucher_no, supplier_name=rb.supplier_name,
            gstin_books=rb.supplier_gstin, gstin_2b="", invoice_no_books=rb.invoice_no,
            invoice_no_2b="", date_books=rb.invoice_date, date_2b=pd.NaT,
            taxable_books=rb.taxable_value, taxable_2b=0.0, tax_books=rb.tax, tax_2b=0.0,
            tax_diff=rb.tax, heads_books=heads(rb), heads_2b="", category=rb.expense_category,
            match_method="Unmatched", confidence="-", primary_issue="NOT_IN_2B",
            all_issues="NOT_IN_2B"))
    # ---- duplicates
    for bid in sorted(dup_ids):
        rb = bt.loc[bid]
        out.append(dict(
            voucher_no=rb.voucher_no, supplier_name=rb.supplier_name,
            gstin_books=rb.supplier_gstin, gstin_2b="", invoice_no_books=rb.invoice_no,
            invoice_no_2b="", date_books=rb.invoice_date, date_2b=pd.NaT,
            taxable_books=rb.taxable_value, taxable_2b=0.0, tax_books=rb.tax, tax_2b=0.0,
            tax_diff=rb.tax, heads_books=heads(rb), heads_2b="", category=rb.expense_category,
            match_method="Duplicate in books", confidence="High", primary_issue="DUPLICATE",
            all_issues="DUPLICATE"))
    # ---- 2B only
    for gid in sorted(un_g):
        rg = gt.loc[gid]
        out.append(dict(
            voucher_no="", supplier_name=rg.supplier_name, gstin_books="",
            gstin_2b=rg.supplier_gstin, invoice_no_books="", invoice_no_2b=rg.invoice_no,
            date_books=pd.NaT, date_2b=rg.invoice_date, taxable_books=0.0,
            taxable_2b=rg.taxable_value, tax_books=0.0, tax_2b=rg.tax, tax_diff=-rg.tax,
            heads_books="", heads_2b=heads(rg), category="", match_method="Unmatched",
            confidence="-", primary_issue="NOT_IN_BOOKS", all_issues="NOT_IN_BOOKS"))

    df = pd.DataFrame(out)
    df["blocked_reason"] = df["category"].map(lambda c: blocked_reason(c))
    df["is_blocked"] = (df["blocked_reason"] != "") & (df["primary_issue"] != "NOT_IN_BOOKS") \
        & (df["primary_issue"] != "DUPLICATE")

    # ---- ITC impact (books side must foot: books = dup + blocked + not_in_2b + excess + claimable)
    def impact(r):
        tb, tg = r.tax_books, r.tax_2b
        z = dict(itc_books=tb, itc_2b=tg, itc_duplicate=0.0, itc_blocked=0.0,
                 itc_not_in_2b=0.0, itc_excess_over_2b=0.0, itc_claimable=0.0,
                 itc_unbooked_in_2b=0.0)
        if r.primary_issue == "NOT_IN_BOOKS":
            z["itc_unbooked_in_2b"] = tg
            return pd.Series(z)
        if r.primary_issue == "DUPLICATE":
            z["itc_duplicate"] = tb
            return pd.Series(z)
        if r.is_blocked:
            z["itc_blocked"] = tb
            return pd.Series(z)
        if r.primary_issue == "NOT_IN_2B":
            z["itc_not_in_2b"] = tb
            return pd.Series(z)
        z["itc_claimable"] = min(tb, tg)
        z["itc_excess_over_2b"] = max(tb - tg, 0.0)
        z["itc_unbooked_in_2b"] = max(tg - tb, 0.0)
        return pd.Series(z)

    df = pd.concat([df, df.apply(impact, axis=1)], axis=1)
    df["itc_at_risk"] = df["itc_not_in_2b"] + df["itc_excess_over_2b"]

    def risk(r):
        exposure = max(r.itc_at_risk, r.itc_duplicate, r.itc_unbooked_in_2b, r.itc_blocked)
        if r.primary_issue in ("NONE", "INV_FORMAT", "ROUNDING") and not r.is_blocked:
            return "Low"
        if exposure >= 50_000:
            return "High"
        if exposure >= 10_000:
            return "Medium"
        return "Low"

    df["risk"] = df.apply(risk, axis=1)
    df["final_issue"] = df.apply(lambda r: "BLOCKED" if r.is_blocked else r.primary_issue, axis=1)
    df["action"] = df["final_issue"].map(ACTIONS)
    df["explanation"] = df.apply(explain, axis=1)
    df.loc[df.is_blocked, "explanation"] = df.loc[df.is_blocked].apply(
        lambda r: f"Expense category '{r.category}' - {r.blocked_reason}. ITC of Rs {r.tax_books:,.2f} "
                  f"is ineligible.", axis=1)
    df["status"] = df["final_issue"].map(
        lambda i: {"NONE": "Matched", "INV_FORMAT": "Matched (format diff)",
                   "ROUNDING": "Matched (within tolerance)"}.get(i, "Exception"))
    df.insert(0, "ref", [f"R{i + 1:04d}" for i in range(len(df))])
    df = df.sort_values(["status", "risk", "itc_at_risk"], ascending=[True, True, False]) \
           .reset_index(drop=True)
    return df, b, g


# ---------------------------------------------------------------- summaries
def summary(df):
    s = dict(
        books_lines=int((df.tax_books > 0).sum()),
        gstr2b_lines=int((df.tax_2b > 0).sum()),
        itc_books=df.itc_books.sum(),
        itc_2b=df.itc_2b.sum(),
        itc_duplicate=df.itc_duplicate.sum(),
        itc_blocked=df.itc_blocked.sum(),
        itc_not_in_2b=df.itc_not_in_2b.sum(),
        itc_excess=df.itc_excess_over_2b.sum(),
        itc_claimable=df.itc_claimable.sum(),
        itc_unbooked=df.itc_unbooked_in_2b.sum(),
    )
    s["foot_check"] = round(s["itc_books"] - (s["itc_duplicate"] + s["itc_blocked"] +
                                              s["itc_not_in_2b"] + s["itc_excess"] +
                                              s["itc_claimable"]), 2)
    return s


def vendor_summary(df):
    d = df.copy()
    d["vendor"] = d["supplier_name"]
    g = d.groupby("vendor").agg(
        lines=("ref", "count"),
        exceptions=("status", lambda x: (x == "Exception").sum()),
        itc_books=("itc_books", "sum"), itc_claimable=("itc_claimable", "sum"),
        itc_at_risk=("itc_at_risk", "sum"), itc_blocked=("itc_blocked", "sum"),
        itc_duplicate=("itc_duplicate", "sum"), itc_unbooked=("itc_unbooked_in_2b", "sum")
    ).reset_index()
    g["exception_rate"] = g["exceptions"] / g["lines"]
    g["pct_books_at_risk"] = (g["itc_at_risk"] / g["itc_books"].replace(0, pd.NA)).fillna(0.0).astype(float)
    g["vendor_rating"] = g.apply(
        lambda r: "High" if r.pct_books_at_risk >= 0.25 or r.exception_rate >= 0.5
        else ("Medium" if r.pct_books_at_risk >= 0.10 or r.exception_rate >= 0.25 else "Low"), axis=1)
    return g.sort_values("itc_at_risk", ascending=False).reset_index(drop=True)




# =====================================================================================
#  EXCEL REPORT (formula-driven)
# =====================================================================================
FONT = "Arial"
NAVY = "1F3864"
f_norm = Font(name=FONT, size=10)
f_bold = Font(name=FONT, size=10, bold=True)
f_head = Font(name=FONT, size=10, bold=True, color="FFFFFF")
f_title = Font(name=FONT, size=16, bold=True, color=NAVY)
f_sub = Font(name=FONT, size=10, italic=True, color="595959")
f_input = Font(name=FONT, size=10, color="0000FF")
fill_head = PatternFill("solid", start_color=NAVY)
fill_sec = PatternFill("solid", start_color="D9E2F3")
fill_tot = PatternFill("solid", start_color="F2F2F2")
fill_hi = PatternFill("solid", start_color="F8CBAD")
fill_med = PatternFill("solid", start_color="FFE699")
fill_low = PatternFill("solid", start_color="C6E0B4")
thin = Side(style="thin", color="BFBFBF")
box = Border(left=thin, right=thin, top=thin, bottom=thin)
NUM = '#,##0.00;(#,##0.00);"-"'
INT = '#,##0;(#,##0);"-"'
PCT = '0.0%'
DATE = "dd-mmm-yyyy"

RECON_COLS = [  # (df column, header, width, format)
    ("ref", "Ref", 8, None), ("status", "Status", 24, None), ("final_issue", "Issue", 18, None),
    ("risk", "Risk", 8, None), ("voucher_no", "Voucher", 10, None),
    ("supplier_name", "Supplier", 30, None), ("gstin_books", "GSTIN (books)", 18, None),
    ("gstin_2b", "GSTIN (2B)", 18, None), ("invoice_no_books", "Invoice no. (books)", 18, None),
    ("invoice_no_2b", "Invoice no. (2B)", 18, None), ("date_books", "Date (books)", 12, DATE),
    ("date_2b", "Date (2B)", 12, DATE), ("taxable_books", "Taxable (books)", 15, NUM),
    ("taxable_2b", "Taxable (2B)", 15, NUM), ("tax_books", "Tax (books)", 14, NUM),
    ("tax_2b", "Tax (2B)", 14, NUM), ("tax_diff", "Tax diff", 12, NUM),
    ("match_method", "Match method", 24, None), ("confidence", "Confidence", 11, None),
    ("category", "Expense category", 24, None),
    ("itc_books", "ITC per books", 14, NUM), ("itc_2b", "ITC per 2B", 14, NUM),
    ("itc_duplicate", "Duplicate", 13, NUM), ("itc_blocked", "Blocked 17(5)", 13, NUM),
    ("itc_not_in_2b", "Not in 2B", 13, NUM), ("itc_excess_over_2b", "Excess over 2B", 13, NUM),
    ("itc_claimable", "Claimable ITC", 14, NUM), ("itc_unbooked_in_2b", "In 2B, not booked", 14, NUM),
    ("itc_at_risk", "ITC at risk", 13, NUM), ("itc_exposure", "Total exposure", 14, NUM),
    ("explanation", "Explanation", 70, None), ("action", "Recommended action", 70, None),
]
CI = {c[0]: i + 1 for i, c in enumerate(RECON_COLS)}   # 1-based col index
ISSUES = [("NOT_IN_2B", "Booked, not in GSTR-2B"), ("NOT_IN_BOOKS", "In GSTR-2B, not booked"),
          ("DUPLICATE", "Duplicate entry in books"), ("AMOUNT_MISMATCH", "Tax amount mismatch"),
          ("TAX_HEAD", "Tax head (IGST vs CGST/SGST)"), ("GSTIN_TYPO", "GSTIN error"),
          ("DATE_PERIOD", "Invoice date mismatch"), ("BLOCKED", "Blocked credit Sec 17(5)"),
          ("INV_FORMAT", "Invoice no. format only"), ("ROUNDING", "Rounding (<= tolerance)"),
          ("NONE", "Fully matched")]


def hdr(ws, row, headers, widths=None):
    for j, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=j, value=h)
        c.font, c.fill, c.border = f_head, fill_head, box
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 30
    if widths:
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[L(j)].width = w


def write_df_sheet(ws, df, cols, fmts=None):
    hdr(ws, 1, [c[1] for c in cols], [c[2] for c in cols])
    for i, r in enumerate(df.itertuples(index=False), 2):
        d = r._asdict() if hasattr(r, "_asdict") else {}
        for j, (k, _, _, fmt) in enumerate(cols, 1):
            v = d.get(k)
            if isinstance(v, float) and pd.isna(v):
                v = None
            if v is pd.NaT:
                v = None
            if isinstance(v, pd.Timestamp):
                v = v.to_pydatetime()
            c = ws.cell(row=i, column=j, value=v)
            c.font = f_norm
            if fmt:
                c.number_format = fmt
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{L(len(cols))}{len(df) + 1}"


def build(df, vendors, b_src, g_src, by_validation, tot_ok, tot_all, params, path):
    wb = Workbook()
    n = len(df)
    last = n + 1
    # ================= Reconciliation sheet =================
    wr = wb.active
    wr.title = "Reconciliation"
    d = df.copy()
    d["itc_at_risk"] = 0.0
    d["itc_exposure"] = 0.0
    write_df_sheet(wr, d, RECON_COLS)
    # live formulas for the two derived columns
    for i in range(2, last + 1):
        nb, ex = L(CI["itc_not_in_2b"]), L(CI["itc_excess_over_2b"])
        wr.cell(i, CI["itc_at_risk"], f"={nb}{i}+{ex}{i}").number_format = NUM
        parts = [L(CI[k]) + str(i) for k in ("itc_at_risk", "itc_duplicate", "itc_blocked", "itc_unbooked_in_2b")]
        wr.cell(i, CI["itc_exposure"], "=" + "+".join(parts)).number_format = NUM
        for k in ("itc_at_risk", "itc_exposure"):
            wr.cell(i, CI[k]).font = f_norm
    rk = L(CI["risk"])
    rng = f"{rk}2:{rk}{last}"
    wr.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"High"'], fill=fill_hi))
    wr.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Medium"'], fill=fill_med))
    wr.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Low"'], fill=fill_low))

    def R(key):  # absolute range on the Reconciliation sheet
        c = L(CI[key])
        return f"Reconciliation!${c}$2:${c}${last}"

    # ================= Summary sheet =================
    ws = wb.create_sheet("Summary", 0)
    ws.sheet_view.showGridLines = False
    for col, w in zip("ABCDEFG", (3, 44, 18, 18, 18, 3, 40)):
        ws.column_dimensions[col].width = w
    ws["B1"] = "GST ITC Reconciliation - Purchase Register vs GSTR-2B"
    ws["B1"].font = f_title
    ws["B2"] = "  |  ".join(x for x in ((f"Tax period: {params['period']}" if params.get("period") else ""),
                                      (f"Taxpayer: {params['taxpayer']}" if params.get("taxpayer") else "")) if x) or "Purchase Register vs GSTR-2B"
    ws["B2"].font = f_sub
    ws["B3"] = "All figures in Rs. Every number on this sheet is a live formula over the 'Reconciliation' sheet."
    ws["B3"].font = f_sub

    # parameters
    ws["B5"], ws["C5"] = "Parameters (inputs)", ""
    ws["B5"].font, ws["B5"].fill = f_bold, fill_sec
    ws["C5"].fill = fill_sec
    ws["B6"], ws["C6"] = "Rounding tolerance (Rs)", params["tol"]
    ws["B7"], ws["C7"] = "Fuzzy invoice-no. similarity threshold", params["fuzzy"]
    ws["B8"], ws["C8"] = "High-risk exposure threshold (Rs)", 50000
    ws["B9"], ws["C9"] = "Medium-risk exposure threshold (Rs)", 10000
    for r in range(6, 10):
        ws.cell(r, 2).font = f_norm
        ws.cell(r, 3).font = f_input
        ws.cell(r, 3).number_format = '#,##0.00' if r != 7 else '0.00'
        ws.cell(r, 3).fill = PatternFill("solid", start_color="FFFF99")
    ws["C6"].comment = Comment("Applied in the matching engine (recon.py, TOLERANCE). Changing it here "
                               "does not re-run the engine - documented for audit trail.", "Capstone")
    ws["C7"].comment = Comment("recon.py FUZZY_RATIO; documented here for the audit trail.", "Capstone")
    ws["C8"].comment = Comment("Risk thresholds are policy assumptions, not statutory limits.", "Capstone")

    # ITC waterfall
    r0 = 11
    ws.cell(r0, 2, "A. ITC waterfall (books -> claimable)").font = f_bold
    for c in (2, 3, 4):
        ws.cell(r0, c).fill = fill_sec
    ws.cell(r0, 3, "Amount (Rs)").font = f_bold
    ws.cell(r0, 4, "% of books ITC").font = f_bold
    rows = [("ITC per purchase register (books)", f"=SUM({R('itc_books')})"),
            ("Less: duplicate entries", f"=-SUM({R('itc_duplicate')})"),
            ("Less: blocked credits (Sec 17(5))", f"=-SUM({R('itc_blocked')})"),
            ("Less: invoices not in GSTR-2B", f"=-SUM({R('itc_not_in_2b')})"),
            ("Less: tax booked in excess of GSTR-2B", f"=-SUM({R('itc_excess_over_2b')})")]
    for k, (lab, fml) in enumerate(rows, r0 + 1):
        ws.cell(k, 2, lab).font = f_norm
        c = ws.cell(k, 3, fml)
        c.font, c.number_format = f_norm, NUM
        e = ws.cell(k, 4, f"=IF($C${r0 + 1}=0,0,C{k}/$C${r0 + 1})")
        e.font, e.number_format = f_norm, PCT
    kc = r0 + 1 + len(rows)       # claimable row
    ws.cell(kc, 2, "ITC claimable in GSTR-3B (eligible & matched)").font = f_bold
    c = ws.cell(kc, 3, f"=SUM(C{r0 + 1}:C{kc - 1})")
    c.font, c.number_format = f_bold, NUM
    e = ws.cell(kc, 4, f"=IF($C${r0 + 1}=0,0,C{kc}/$C${r0 + 1})")
    e.font, e.number_format = f_bold, PCT
    for col in (2, 3, 4):
        ws.cell(kc, col).fill = fill_tot
        ws.cell(kc, col).border = Border(top=Side(style="thin"), bottom=Side(style="double"))
    ws.cell(kc + 1, 2, "Check: equals sum of row-level claimable ITC").font = f_sub
    c = ws.cell(kc + 1, 3, f'=IF(ROUND(C{kc}-SUM({R("itc_claimable")}),2)=0,"OK","DIFFERENCE")')
    c.font = f_bold
    ws.cell(kc + 3, 2, "Memo: ITC per GSTR-2B (all invoices)").font = f_norm
    c = ws.cell(kc + 3, 3, f"=SUM({R('itc_2b')})")
    c.font, c.number_format = f_norm, NUM
    ws.cell(kc + 4, 2, "Memo: ITC in GSTR-2B but not booked / under-booked").font = f_norm
    c = ws.cell(kc + 4, 3, f"=SUM({R('itc_unbooked_in_2b')})")
    c.font, c.number_format = f_norm, NUM
    ws.cell(kc + 5, 2, "Total ITC at risk (not in 2B + excess over 2B)").font = f_bold
    c = ws.cell(kc + 5, 3, f"=SUM({R('itc_at_risk')})")
    c.font, c.number_format = f_bold, NUM

    # KPIs
    k0 = kc + 7
    ws.cell(k0, 2, "B. Match statistics").font = f_bold
    for c in (2, 3):
        ws.cell(k0, c).fill = fill_sec
    st = R("status")
    kp = [("Total reconciled lines", f"=COUNTA({R('ref')})", INT),
          ("Fully matched", f'=COUNTIF({st},"Matched")', INT),
          ("Matched with format / rounding difference",
           f'=COUNTIF({st},"Matched (format diff)")+COUNTIF({st},"Matched (within tolerance)")', INT),
          ("Exceptions needing action", f'=COUNTIF({st},"Exception")', INT),
          ("High-risk exceptions", f'=COUNTIF({R("risk")},"High")', INT),
          ("Exception rate", f"=IF(C{k0 + 1}=0,0,C{k0 + 4}/C{k0 + 1})", PCT),
          ("Auto-match rate (no manual work)", f"=IF(C{k0 + 1}=0,0,(C{k0 + 2}+C{k0 + 3})/C{k0 + 1})", PCT)]
    for k, (lab, fml, fm) in enumerate(kp, k0 + 1):
        ws.cell(k, 2, lab).font = f_norm
        c = ws.cell(k, 3, fml)
        c.font, c.number_format = f_norm, fm

    # Issue table
    t0 = k0 + len(kp) + 3
    ws.cell(t0 - 1, 2, "C. Issue-wise summary").font = f_bold
    for c in range(2, 5):
        ws.cell(t0 - 1, c).fill = fill_sec
    hdr_cells = ["Issue", "Lines", "ITC exposure (Rs)"]
    for j, h in enumerate(hdr_cells, 2):
        c = ws.cell(t0, j, h)
        c.font, c.fill, c.border = f_head, fill_head, box
        c.alignment = Alignment(horizontal="center")
    for k, (code, lab) in enumerate(ISSUES, t0 + 1):
        ws.cell(k, 2, lab).font = f_norm
        ws.cell(k, 7 if False else 2).value = lab
        crit = f'"{code}"'
        ws.cell(k, 3, f"=COUNTIF({R('final_issue')},{crit})").number_format = INT
        e = ws.cell(k, 4, f"=SUMIFS({R('itc_exposure')},{R('final_issue')},{crit})")
        e.number_format = NUM
        for c in (3, 4):
            ws.cell(k, c).font = f_norm
    tl = t0 + len(ISSUES)
    ws.cell(tl + 1, 2, "Total").font = f_bold
    ws.cell(tl + 1, 3, f"=SUM(C{t0 + 1}:C{tl})").number_format = INT
    ws.cell(tl + 1, 4, f"=SUM(D{t0 + 1}:D{tl})").number_format = NUM
    for c in (2, 3, 4):
        ws.cell(tl + 1, c).font = f_bold
        ws.cell(tl + 1, c).fill = fill_tot
    ws.cell(tl + 2, 2, "'Exposure' = ITC at risk + duplicate + blocked + in 2B but not booked (rounding rows show the small difference only).").font = f_sub

    # Chart (exclude 'fully matched' row = last)
    ch = BarChart()
    ch.type = "bar"
    ch.title = "ITC exposure by issue (Rs)"
    ch.style = 10
    data = Reference(ws, min_col=4, min_row=t0, max_row=tl - 1)
    cats = Reference(ws, min_col=2, min_row=t0 + 1, max_row=tl - 1)
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    ch.legend = None
    ch.roundedCorners = False
    ch.x_axis.delete = False
    ch.y_axis.delete = False
    ch.y_axis.number_format = '#,##0'
    ch.height, ch.width = 9, 17
    ch.x_axis.scaling.orientation = "maxMin"
    ws.add_chart(ch, "G11")

    # ================= Exceptions sheet =================
    we = wb.create_sheet("Exceptions", 1)
    ex = d[d["status"] == "Exception"].copy()
    ex["_r"] = ex["risk"].map({"High": 0, "Medium": 1, "Low": 2})
    ex["_e"] = ex["itc_not_in_2b"] + ex["itc_excess_over_2b"] + ex["itc_duplicate"] + \
        ex["itc_blocked"] + ex["itc_unbooked_in_2b"]
    ex = ex.sort_values(["_r", "_e"], ascending=[True, False])
    ecols = [c for c in RECON_COLS if c[0] in (
        "ref", "risk", "final_issue", "supplier_name", "voucher_no", "invoice_no_books", "invoice_no_2b",
        "tax_books", "tax_2b", "tax_diff", "explanation", "action")]
    ex["itc_exposure"] = ex["_e"]
    write_df_sheet(we, ex, ecols)
    erk = "B"
    we.conditional_formatting.add(f"B2:B{len(ex) + 1}", CellIsRule(operator="equal", formula=['"High"'], fill=fill_hi))
    we.conditional_formatting.add(f"B2:B{len(ex) + 1}", CellIsRule(operator="equal", formula=['"Medium"'], fill=fill_med))
    we.conditional_formatting.add(f"B2:B{len(ex) + 1}", CellIsRule(operator="equal", formula=['"Low"'], fill=fill_low))

    # ================= Vendor risk =================
    wv = wb.create_sheet("Vendor Risk", 2)
    hdr(wv, 1, ["Supplier", "Lines", "Exceptions", "Exception rate", "ITC per books", "Claimable ITC",
                "ITC at risk", "% of books ITC at risk", "Vendor rating"],
        [34, 8, 11, 12, 16, 16, 15, 14, 12])
    sup = R("supplier_name")
    for i, v in enumerate(vendors["vendor"], 2):
        wv.cell(i, 1, v).font = f_norm
        wv.cell(i, 2, f'=COUNTIF({sup},A{i})').number_format = INT
        wv.cell(i, 3, f'=COUNTIFS({sup},A{i},{R("status")},"Exception")').number_format = INT
        wv.cell(i, 4, f"=IF(B{i}=0,0,C{i}/B{i})").number_format = PCT
        wv.cell(i, 5, f'=SUMIFS({R("itc_books")},{sup},A{i})').number_format = NUM
        wv.cell(i, 6, f'=SUMIFS({R("itc_claimable")},{sup},A{i})').number_format = NUM
        wv.cell(i, 7, f'=SUMIFS({R("itc_at_risk")},{sup},A{i})').number_format = NUM
        wv.cell(i, 8, f"=IF(E{i}=0,0,G{i}/E{i})").number_format = PCT
        wv.cell(i, 9, f'=IF(OR(H{i}>=0.25,D{i}>=0.5),"High",IF(OR(H{i}>=0.1,D{i}>=0.25),"Medium","Low"))')
        for c in range(2, 10):
            wv.cell(i, c).font = f_norm
    nv = len(vendors) + 1
    wv.freeze_panes = "A2"
    wv.auto_filter.ref = f"A1:I{nv}"
    for lab, fill in (("High", fill_hi), ("Medium", fill_med), ("Low", fill_low)):
        wv.conditional_formatting.add(f"I2:I{nv}", CellIsRule(operator="equal", formula=[f'"{lab}"'], fill=fill))
    wv.cell(nv + 2, 1, "Rating rule: High if >=25% of books ITC at risk or >=50% of lines are exceptions; "
                       "Medium if >=10% / >=25%. Thresholds are illustrative policy assumptions.").font = f_sub

    # ================= source sheets =================
    wsrc = wb.create_sheet("Books (source)")
    bcols = [("voucher_no", "Voucher", 10, None), ("supplier_gstin", "Supplier GSTIN", 18, None),
             ("supplier_name", "Supplier", 30, None), ("invoice_no", "Invoice no.", 18, None),
             ("invoice_date", "Invoice date", 12, DATE), ("taxable_value", "Taxable value", 15, NUM),
             ("igst", "IGST", 12, NUM), ("cgst", "CGST", 12, NUM), ("sgst", "SGST", 12, NUM),
             ("expense_category", "Expense category", 26, None)]
    write_df_sheet(wsrc, b_src, bcols)
    w2 = wb.create_sheet("GSTR-2B (source)")
    gcols = [("supplier_gstin", "Supplier GSTIN", 18, None), ("supplier_name", "Supplier", 30, None),
             ("invoice_no", "Invoice no.", 18, None), ("invoice_date", "Invoice date", 12, DATE),
             ("taxable_value", "Taxable value", 15, NUM), ("igst", "IGST", 12, NUM),
             ("cgst", "CGST", 12, NUM), ("sgst", "SGST", 12, NUM), ("itc_available", "ITC available", 12, None)]
    write_df_sheet(w2, g_src, gcols)

    # ================= Method & validation =================
    wm = wb.create_sheet("Method", 3)
    wm.column_dimensions["A"].width = 34
    wm.column_dimensions["B"].width = 14
    wm.column_dimensions["C"].width = 14
    wm.column_dimensions["D"].width = 70
    wm["A1"] = "Matching method"
    wm["A1"].font = f_title
    steps = [
        "Pass 1  Exact: same supplier GSTIN + identical invoice number.",
        "Pass 2  Normalised: ignore case, spaces, punctuation and leading zeros in the invoice number.",
        "Pass 3  Suffix ignored: trailing letters such as '-A' dropped.",
        "Pass 4  GSTIN typo: same normalised invoice no. + same state code + GSTIN within 2 characters + taxable value within 2%.",
        "Pass 5  Fuzzy (low confidence, flagged for review): same GSTIN, similarity >= 0.92 (difflib), taxable value within 2%.",
        "Duplicates are detected first (same supplier + normalised invoice no. + tax) and excluded from matching.",
        "Matched pairs are then tested for: tax mismatch (> Rs 5), tax-head mismatch, GSTIN mismatch, date gap > 31 days, invoice-format difference.",
        "Sec 17(5) blocked credit is flagged by expense category (illustrative mapping - requires professional review).",
        "Explanations are deterministic templates; the explain() function is the hook where an LLM can be plugged in.",
    ]
    for i, s in enumerate(steps, 3):
        wm.cell(i, 1, s).font = f_norm
    wm.cell(len(steps) + 4, 1, "Every exception should be reviewed by a person before any return is filed. "
                               "Blocked-credit flags use expense-category keywords and are illustrative.").font = f_sub

    for sh in wb.worksheets:
        if sh.title != "Summary":
            sh.sheet_view.zoomScale = 90
    wb.save(path)


# =====================================================================================
#  WORD + POWERPOINT (generated from the user's own results)
# =====================================================================================
def inr(x):
    x = round(float(x))
    s = str(abs(x))
    if len(s) > 3:
        head, last3 = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [last3])
    return ("-" if x < 0 else "") + "Rs " + s


def _facts(df, vend):
    S = summary(df)
    d = df.assign(expo=df.itc_at_risk + df.itc_duplicate + df.itc_blocked + df.itc_unbooked_in_2b)
    labels = dict(ISSUES)
    by = (d[d.final_issue != "NONE"].groupby("final_issue")
          .agg(count=("ref", "count"), exposure=("expo", "sum")).reset_index())
    by["label"] = by["final_issue"].map(labels)
    by["action"] = by["final_issue"].map(ACTIONS)
    by = by.sort_values("exposure", ascending=False).reset_index(drop=True)
    exc = d[d.status == "Exception"].sort_values("expo", ascending=False)
    return S, d, by, exc


def make_word(df, vend, path, taxpayer, period):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    S, d, by, exc = _facts(df, vend)
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2)
    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = Pt(10)

    def shade(cell, color):
        tcPr = cell._tc.get_or_add_tcPr()
        sh = OxmlElement("w:shd")
        sh.set(qn("w:val"), "clear")
        sh.set(qn("w:fill"), color)
        tcPr.append(sh)

    def table(rows, header, right=()):
        t = doc.add_table(rows=1, cols=len(header))
        t.style = "Table Grid"
        for j, h in enumerate(header):
            c = t.rows[0].cells[j]
            c.text = ""
            r = c.paragraphs[0].add_run(str(h))
            r.bold, r.font.size, r.font.color.rgb = True, Pt(9), RGBColor(255, 255, 255)
            shade(c, "1F3864")
        for row in rows:
            cells = t.add_row().cells
            for j, v in enumerate(row):
                cells[j].text = ""
                p = cells[j].paragraphs[0]
                p.add_run(str(v)).font.size = Pt(9)
                if j in right:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        doc.add_paragraph()

    h = doc.add_heading("GST ITC Reconciliation Report", 0)
    sub = " | ".join(x for x in (taxpayer, f"Tax period: {period}" if period else "",
                                  "Purchase Register vs GSTR-2B") if x)
    doc.add_paragraph(sub)

    n_exc = int((df.status == "Exception").sum())
    doc.add_heading("1. Summary", 1)
    doc.add_paragraph(
        f"{S['books_lines']} purchase-register lines and {S['gstr2b_lines']} GSTR-2B lines were reconciled. "
        f"ITC per books is {inr(S['itc_books'])} against {inr(S['itc_2b'])} per GSTR-2B. "
        f"After removing duplicates, blocked credits, invoices not in GSTR-2B and excess over GSTR-2B, "
        f"ITC that can be claimed is {inr(S['itc_claimable'])}. "
        f"{n_exc} lines need attention. ITC in GSTR-2B that is not yet booked: {inr(S['itc_unbooked'])}.")

    doc.add_heading("2. ITC waterfall", 1)
    table([("ITC as per books", inr(S["itc_books"])),
           ("Less: duplicate entries", inr(-S["itc_duplicate"])),
           ("Less: blocked credit (Sec 17(5))", inr(-S["itc_blocked"])),
           ("Less: booked but not in GSTR-2B", inr(-S["itc_not_in_2b"])),
           ("Less: excess over GSTR-2B", inr(-S["itc_excess"])),
           ("ITC claimable", inr(S["itc_claimable"])),
           ("Memo: in GSTR-2B, not booked", inr(S["itc_unbooked"]))],
          ["Item", "Amount"], right=(1,))

    doc.add_heading("3. Exceptions by type and recommended action", 1)
    table([(r.label, r["count"], inr(r.exposure), r.action) for _, r in by.iterrows()],
          ["Issue", "Lines", "ITC exposure", "Recommended action"], right=(1, 2))

    doc.add_heading("4. Vendor risk (top 15 by ITC at risk)", 1)
    table([(v.vendor or "(blank)", v.lines, v.exceptions, inr(v.itc_at_risk), v.vendor_rating)
           for v in vend.head(15).itertuples()],
          ["Vendor", "Lines", "Exceptions", "ITC at risk", "Rating"], right=(1, 2, 3))

    doc.add_heading("5. Exception list", 1)
    table([(e.voucher_no, (e.supplier_name or "")[:28], e.invoice_no_books or e.invoice_no_2b,
            dict(ISSUES).get(e.final_issue, e.final_issue), f"{e.tax_books:,.2f}", f"{e.tax_2b:,.2f}",
            f"{e.expo:,.2f}") for e in exc.itertuples()],
          ["Voucher", "Supplier", "Invoice", "Issue", "Tax (books)", "Tax (2B)", "Exposure"], right=(4, 5, 6))

    doc.add_heading("6. Method and limitations", 1)
    for t in ["Matching in five passes: exact GSTIN + invoice no.; normalised invoice no.; suffix ignored; "
              "GSTIN typo; fuzzy match (low confidence).",
              "Matched invoices are tested for tax difference above Rs 5, tax-head mismatch, GSTIN mismatch, "
              "date gap over 31 days and invoice-format difference.",
              "Blocked credit under Sec 17(5) is flagged from the expense category text (illustrative keywords) "
              "and needs professional review.",
              "This is a decision-support tool. Every exception should be reviewed by a person before any "
              "return is filed."]:
        doc.add_paragraph(t, style="List Bullet")
    doc.save(path)


def make_ppt(df, vend, path, taxpayer, period):
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches, Pt

    S, d, by, exc = _facts(df, vend)
    NAVY, GREY, LIGHT = RGBColor(0x1F, 0x38, 0x64), RGBColor(0x59, 0x59, 0x59), RGBColor(0xD9, 0xE2, 0xF3)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.33), Inches(7.5)
    blank = prs.slide_layouts[6]
    state = {"n": 0}

    def text(sl, x, y, w, h, lines, size=16, bold=False, color=GREY):
        tf = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
        tf.word_wrap = True
        for i, ln in enumerate(lines if isinstance(lines, list) else [lines]):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text, p.font.size, p.font.bold, p.font.color.rgb = ln, Pt(size), bold, color
            p.space_after = Pt(6)

    def slide(title):
        sl = prs.slides.add_slide(blank)
        bar = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.1))
        bar.fill.solid()
        bar.fill.fore_color.rgb = NAVY
        bar.line.fill.background()
        text(sl, 0.5, 0.2, 12, 0.8, title, 28, True, RGBColor(255, 255, 255))
        state["n"] += 1
        sub = " | ".join(x for x in (taxpayer, period) if x)
        text(sl, 0.5, 7.0, 10, 0.3, f"GST ITC Reconciliation  |  {sub}", 10)
        return sl

    def table(sl, rows, header, widths, top=1.4, size=11, right=()):
        n = len(rows) + 1
        shp = sl.shapes.add_table(n, len(header), Inches(0.5), Inches(top), Inches(sum(widths)), Inches(0.38 * n))
        t = shp.table
        for j, w in enumerate(widths):
            t.columns[j].width = Inches(w)
        for j, h in enumerate(header):
            t.cell(0, j).text = h
        for i, r in enumerate(rows, 1):
            for j, v in enumerate(r):
                t.cell(i, j).text = str(v)
        for i, row in enumerate(t.rows):
            for j, c in enumerate(row.cells):
                for p in c.text_frame.paragraphs:
                    p.font.size = Pt(size)
                    if j in right:
                        p.alignment = 3  # right

    def chart(sl, cats, vals, x, y, w, h, name):
        cd = CategoryChartData()
        cd.categories = cats
        cd.add_series(name, vals)
        ch = sl.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd).chart
        ch.has_legend = False
        ch.has_title = False
        ch.plots[0].has_data_labels = True
        ch.plots[0].data_labels.font.size = Pt(10)
        ch.plots[0].data_labels.number_format = '#,##0'
        ch.plots[0].data_labels.number_format_is_linked = False
        ch.category_axis.tick_labels.font.size = Pt(10)
        ch.value_axis.tick_labels.font.size = Pt(10)

    # 1 title
    sl = prs.slides.add_slide(blank)
    bg = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()
    text(sl, 0.9, 2.3, 11.5, 1.2, "GST ITC Reconciliation", 44, True, RGBColor(255, 255, 255))
    text(sl, 0.9, 3.6, 11.5, 1, "Purchase Register vs GSTR-2B", 22, False, RGBColor(255, 255, 255))
    text(sl, 0.9, 4.5, 11.5, 1, " | ".join(x for x in (taxpayer, period) if x), 18, False, RGBColor(217, 226, 243))

    # 2 headline
    n_exc = int((df.status == "Exception").sum())
    sl = slide("Headline numbers")
    kp = [("ITC per books", inr(S["itc_books"])), ("ITC per GSTR-2B", inr(S["itc_2b"])),
          ("ITC claimable", inr(S["itc_claimable"])), ("In 2B, not booked", inr(S["itc_unbooked"]))]
    for i, (k, v) in enumerate(kp):
        x = 0.5 + i * 3.13
        b = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(1.6), Inches(2.9), Inches(1.7))
        b.fill.solid()
        b.fill.fore_color.rgb = LIGHT
        b.line.fill.background()
        text(sl, x + 0.1, 1.8, 2.7, 0.5, k, 14)
        text(sl, x + 0.1, 2.4, 2.7, 0.8, v, 22, True, NAVY)
    text(sl, 0.5, 3.8, 12, 3, [
        f"{S['books_lines']} books lines and {S['gstr2b_lines']} GSTR-2B lines reconciled.",
        f"{n_exc} lines need attention ({n_exc / max(len(df), 1):.0%} of all lines).",
        f"ITC removed from the claim: duplicates {inr(S['itc_duplicate'])}, blocked {inr(S['itc_blocked'])}, "
        f"not in 2B {inr(S['itc_not_in_2b'])}, excess over 2B {inr(S['itc_excess'])}."], 18)

    # 3 waterfall
    sl = slide("From ITC per books to ITC claimable")
    chart(sl, ["Books", "Duplicate", "Blocked", "Not in 2B", "Excess", "Claimable"],
          [round(S[k]) for k in ("itc_books", "itc_duplicate", "itc_blocked", "itc_not_in_2b", "itc_excess",
                                 "itc_claimable")], 0.7, 1.4, 12, 5.4, "Rs")

    # 4 exceptions
    sl = slide("Exceptions by type")
    if len(by):
        chart(sl, list(by.label.str.slice(0, 22)), [int(x) for x in by["count"]], 0.4, 1.4, 6.3, 5.4, "Lines")
        table(sl, [(r.label[:30], r["count"], inr(r.exposure)) for _, r in by.head(10).iterrows()],
              ["Issue", "Lines", "ITC exposure"], [3.0, 0.8, 1.9], top=1.5, size=10, right=(1, 2))
        sl.shapes[-1].left = Inches(6.9)
    else:
        text(sl, 0.8, 2, 11, 1, "No exceptions found - all lines matched.", 22)

    # 5 vendors
    sl = slide("Vendors with most ITC at risk")
    v = vend.head(10)
    table(sl, [((x.vendor or "(blank)")[:34], x.lines, x.exceptions, inr(x.itc_at_risk), x.vendor_rating)
               for x in v.itertuples()],
          ["Vendor", "Lines", "Exceptions", "ITC at risk", "Rating"], [5.2, 1.2, 1.5, 2.5, 1.5], right=(1, 2, 3))

    # 6 top exceptions
    sl = slide("Largest individual exceptions")
    table(sl, [((e.supplier_name or "")[:26], (e.invoice_no_books or e.invoice_no_2b)[:18],
                dict(ISSUES).get(e.final_issue, e.final_issue)[:28], inr(e.expo))
               for e in exc.head(10).itertuples()],
          ["Supplier", "Invoice", "Issue", "ITC exposure"], [4.0, 2.6, 3.7, 2.0], right=(3,))

    # 7 actions
    sl = slide("Recommended actions")
    table(sl, [(r.label[:28], r["count"], r.action) for _, r in by.head(8).iterrows()],
          ["Issue", "Lines", "Action"], [3.2, 0.9, 8.2], size=10, right=(1,))

    # 8 method
    sl = slide("Method and limitations")
    text(sl, 0.6, 1.5, 12, 5, [
        "5-pass matching: exact, normalised invoice no., suffix ignored, GSTIN typo, fuzzy (flagged low confidence).",
        "Tests on matched pairs: tax difference > Rs 5, IGST vs CGST/SGST heads, GSTIN, date gap > 31 days.",
        "Blocked credit (Sec 17(5)) flagged from expense-category keywords - illustrative, needs review.",
        "Decision support only: a person must review every exception before filing GSTR-3B."], 18)
    prs.save(path)



# =====================================================================================
#  APP
# =====================================================================================
def run_all(books, gstr2b, out_dir, taxpayer="", period=""):
    """Reads the two user files and writes Excel + Word + PowerPoint into out_dir."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df, b, g = reconcile(books, gstr2b)
    if df.empty:
        raise ValueError("No invoices were found in the two files.")
    vend = vendor_summary(df)
    tag = re.sub(r"[^A-Za-z0-9]+", "_", period).strip("_") or "report"
    xl = out_dir / f"GST_ITC_Reconciliation_{tag}.xlsx"
    wd = out_dir / f"GST_ITC_Report_{tag}.docx"
    pp = out_dir / f"GST_ITC_Presentation_{tag}.pptx"
    build(df, vend, b, g, None, 0, 0,
          dict(tol=TOLERANCE, fuzzy=FUZZY_RATIO, taxpayer=taxpayer, period=period), str(xl))
    make_word(df, vend, str(wd), taxpayer, period)
    make_ppt(df, vend, str(pp), taxpayer, period)
    return summary(df), dict(excel=str(xl), word=str(wd), ppt=str(pp), folder=str(out_dir))


def summary_text(S, files):
    lines = [f"ITC per books      : {inr(S['itc_books'])}",
             f"ITC per GSTR-2B    : {inr(S['itc_2b'])}",
             f"  duplicates       : {inr(S['itc_duplicate'])}",
             f"  blocked 17(5)    : {inr(S['itc_blocked'])}",
             f"  not in 2B        : {inr(S['itc_not_in_2b'])}",
             f"  excess over 2B   : {inr(S['itc_excess'])}",
             f"ITC claimable      : {inr(S['itc_claimable'])}",
             f"In 2B, not booked  : {inr(S['itc_unbooked'])}", "",
             "Saved in: " + files["folder"],
             "  " + Path(files["excel"]).name, "  " + Path(files["word"]).name, "  " + Path(files["ppt"]).name]
    return "\n".join(lines)


def open_path(p):
    if sys.platform.startswith("win"):
        os.startfile(p)
    else:
        subprocess.call(["open" if sys.platform == "darwin" else "xdg-open", p])


def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("GST ITC Reconciliation - Purchase Register vs GSTR-2B")
    root.geometry("760x560")
    v = {k: tk.StringVar() for k in ("books", "g2b", "out", "tax", "per")}
    ft = [("Excel / CSV", "*.xlsx *.xls *.csv")]
    files = {}

    def pick_file(var):
        var.set(filedialog.askopenfilename(filetypes=ft) or var.get())
        if var is v["books"] and not v["out"].get() and var.get():
            v["out"].set(str(Path(var.get()).parent / "ITC_Reconciliation_Output"))

    def pick_dir(var):
        var.set(filedialog.askdirectory() or var.get())

    def row(r, label, var, cmd=None):
        ttk.Label(root, text=label).grid(row=r, column=0, padx=10, pady=8, sticky="w")
        ttk.Entry(root, textvariable=var, width=62).grid(row=r, column=1)
        if cmd:
            ttk.Button(root, text="Browse", command=cmd).grid(row=r, column=2, padx=8)

    row(0, "Purchase Register", v["books"], lambda: pick_file(v["books"]))
    row(1, "GSTR-2B file", v["g2b"], lambda: pick_file(v["g2b"]))
    row(2, "Save reports in", v["out"], lambda: pick_dir(v["out"]))
    row(3, "Taxpayer name (optional)", v["tax"])
    row(4, "Tax period e.g. Oct 2026", v["per"])
    box = tk.Text(root, height=16, width=90, state="disabled", font=("Consolas", 9))
    box.grid(row=7, column=0, columnspan=3, padx=10, pady=8)

    def show(t):
        box.config(state="normal")
        box.delete("1.0", "end")
        box.insert("end", t)
        box.config(state="disabled")

    def go():
        if not v["books"].get() or not v["g2b"].get():
            return messagebox.showwarning("Missing", "Please choose both files.")
        out = v["out"].get() or str(Path(v["books"].get()).parent / "ITC_Reconciliation_Output")
        v["out"].set(out)
        show("Working ...")
        root.update()
        try:
            S, f = run_all(v["books"].get(), v["g2b"].get(), out, v["tax"].get(), v["per"].get())
        except Exception as e:
            show(f"ERROR\n{e}")
            return messagebox.showerror("Error", f"{type(e).__name__}: {e}")
        files.update(f)
        show(summary_text(S, f))

    def opn(k):
        if not files:
            return messagebox.showinfo("Info", "Click 'Generate reports' first.")
        open_path(files[k])

    ttk.Button(root, text="Generate reports", command=go).grid(row=5, column=1, pady=6)
    bf = ttk.Frame(root)
    bf.grid(row=6, column=0, columnspan=3)
    for i, (t, k) in enumerate([("Open Excel", "excel"), ("Open Word", "word"), ("Open PPT", "ppt"),
                                ("Open folder", "folder")]):
        ttk.Button(bf, text=t, command=lambda k=k: opn(k)).grid(row=0, column=i, padx=6)
    root.mainloop()


def web():
    """Browser version (used automatically when tkinter is not available)."""
    import tempfile
    import threading
    import webbrowser
    from email import message_from_bytes
    from email.policy import HTTP
    from http.server import BaseHTTPRequestHandler, HTTPServer

    tmp = Path(tempfile.mkdtemp())
    state = {}
    PAGE = ("<html><body style='font-family:Arial;max-width:820px;margin:30px auto'>"
            "<h2>GST ITC Reconciliation - Purchase Register vs GSTR-2B</h2>{body}"
            "<form method=post enctype=multipart/form-data>"
            "<p>Purchase Register: <input type=file name=books required></p>"
            "<p>GSTR-2B file: <input type=file name=g2b required></p>"
            "<p>Taxpayer name: <input name=tax size=40></p><p>Tax period: <input name=per size=20></p>"
            "<button style='padding:8px 20px'>Generate reports</button></form></body></html>")
    MIME = {"excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "ppt": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}

    class H(BaseHTTPRequestHandler):
        def _send(self, body, ctype="text/html", extra=None):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            for k, val in (extra or {}).items():
                self.send_header(k, val)
            self.end_headers()
            self.wfile.write(body if isinstance(body, bytes) else body.encode("utf-8"))

        def do_GET(self):
            k = self.path.strip("/")
            if k in MIME and k in state:
                p = Path(state[k])
                return self._send(p.read_bytes(), MIME[k],
                                  {"Content-Disposition": f"attachment; filename={p.name}"})
            self._send(PAGE.format(body=""))

        def do_POST(self):
            n = int(self.headers["Content-Length"])
            raw = b"Content-Type: " + self.headers["Content-Type"].encode() + b"\r\n\r\n" + self.rfile.read(n)
            msg = message_from_bytes(raw, policy=HTTP)
            f, form = {}, {}
            for part in msg.iter_parts():
                name = part.get_param("name", header="content-disposition")
                fn = part.get_filename()
                data = part.get_payload(decode=True)
                if fn:
                    p = tmp / (name + Path(fn).suffix)
                    p.write_bytes(data)
                    f[name] = p
                else:
                    form[name] = data.decode("utf-8", "ignore")
            try:
                S, files = run_all(f["books"], f["g2b"], tmp / "out", form.get("tax", ""), form.get("per", ""))
                state.update(excel=files["excel"], word=files["word"], ppt=files["ppt"])
                body = ("<pre>" + summary_text(S, files) + "</pre><p><a href=/excel><b>Download Excel</b></a> | "
                        "<a href=/word><b>Download Word</b></a> | <a href=/ppt><b>Download PowerPoint</b></a></p><hr>")
            except Exception as e:
                body = f"<pre style=color:red>Error: {e}</pre>"
            self._send(PAGE.format(body=body))

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 8000), H)
    print("Open http://127.0.0.1:8000  (Ctrl+C to stop)")
    threading.Timer(1, lambda: webbrowser.open("http://127.0.0.1:8000")).start()
    srv.serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--books", help="purchase register file")
    ap.add_argument("--gstr2b", help="GSTR-2B file")
    ap.add_argument("--out", default="ITC_Reconciliation_Output")
    ap.add_argument("--taxpayer", default="")
    ap.add_argument("--period", default="")
    a = ap.parse_args()
    if a.books and a.gstr2b:
        S, f = run_all(a.books, a.gstr2b, a.out, a.taxpayer, a.period)
        print(summary_text(S, f))
    else:
        try:
            import tkinter
            tkinter.Tk().destroy()
            gui()
        except Exception:
            web()
