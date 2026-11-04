"""Smart import: read vendor statements and software exports (xlsx / xls / csv / text-based PDF),
detect the layout and classify every row as a Bill or a Payment.

Pipeline (each step is exposed so the app can show it and let the user correct it):
    read_raw()    -> candidate sheets / tables as header-less DataFrames
    analyse()     -> header row + column mapping (+ vendor guess from the preamble)
    build_rows()  -> canonical rows: Date, Vendor, Ref, Description, Type, Debit, Credit, Amount, Balance
    classify()    -> adds Kind (Bill / Payment / Skip / Review), Basis, Check
    to_inputs()   -> standard Bills / Payments tables (then engine.standardise)

Scanned (image-only) PDFs are not supported – they need OCR.
"""
from __future__ import annotations

import csv
import difflib
import io
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

from engine import bill_key, vendor_key

# --------------------------------------------------------------------------- #
# Column detection
# --------------------------------------------------------------------------- #
FIELDS = ["Date", "Vendor", "Ref", "Description", "Type", "Debit", "Credit", "Amount", "Balance", "Payment Mode"]

SYNONYMS = {
    "Date": ["date", "txndate", "transactiondate", "voucherdate", "postingdate", "invoicedate", "billdate", "docdate",
             "documentdate", "paymentdate", "valuedate", "entrydate", "vchdate"],
    "Vendor": ["vendor", "vendorname", "supplier", "suppliername", "party", "partyname", "accountname", "ledgername",
               "customername", "nameofsupplier", "payee"],
    "Ref": ["ref", "refno", "reference", "referenceno", "invoiceno", "invoicenumber", "billno", "billnumber", "voucherno",
            "vchno", "vouchernumber", "documentno", "docno", "invno", "number", "transactionno", "txnno", "chequeno",
            "utr", "supplierinvoiceno", "partyinvoiceno", "invoice", "bill"],
    "Description": ["description", "particulars", "particular", "narration", "details", "remarks", "memo",
                    "transactiondetails", "text", "item"],
    "Type": ["type", "vouchertype", "vchtype", "transactiontype", "documenttype", "doctype", "txntype", "entrytype", "category"],
    "Debit": ["debit", "dr", "debitamount", "withdrawal", "debitrs", "debitamt"],
    "Credit": ["credit", "cr", "creditamount", "deposit", "creditrs", "creditamt"],
    "Amount": ["amount", "amt", "value", "netamount", "totalamount", "invoiceamount", "billamount", "amountpaid",
               "paidamount", "grossamount", "amountrs", "transactionamount", "invoicevalue", "billvalue"],
    "Balance": ["balance", "closingbalance", "runningbalance", "bal", "balanceamount"],
    "Payment Mode": ["paymentmode", "mode", "modeofpayment"],
}
_SYN_REV = {s: f for f, ss in SYNONYMS.items() for s in ss}


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _match_field(cell) -> str | None:
    n = _norm(cell)
    if not n or n == "nan":
        return None
    if n in _SYN_REV:
        return _SYN_REV[n]
    return None


@dataclass
class Detected:
    header_idx: int | None
    mapping: dict          # field -> column position
    score: int
    preamble: str          # text above the header (vendor name often lives here)
    layout: str


def map_header_row(raw: pd.DataFrame, i: int) -> dict:
    """Column mapping for the given header row (0-based)."""
    mapping: dict[str, int] = {}
    for j, cell in enumerate(raw.iloc[i].tolist()):
        f = _match_field(cell)
        if f and f not in mapping:
            mapping[f] = j
    return mapping


def analyse(raw: pd.DataFrame) -> Detected:
    """Find the header row and map columns to canonical fields."""
    best = (0, None, {})
    for i in range(min(len(raw), 40)):
        mapping = map_header_row(raw, i)
        score = len(mapping)
        has_core = "Date" in mapping or "Amount" in mapping or "Debit" in mapping
        if has_core and score > best[0]:
            best = (score, i, mapping)
    score, idx, mapping = best
    if idx is None or score < 2:
        return Detected(None, {}, 0, "", "Not recognised")
    pre = " ".join(str(v) for row in raw.iloc[:idx].values.tolist() for v in row if str(v) not in ("nan", "None", ""))
    return Detected(idx, mapping, score, pre, layout_label(mapping))


def layout_label(m: dict) -> str:
    if "Debit" in m or "Credit" in m:
        return "Ledger / statement with Debit–Credit columns"
    if "Type" in m and "Amount" in m:
        return "Transaction list with a type column"
    if "Balance" in m and "Amount" in m:
        return "Ledger with running balance"
    if "Amount" in m:
        return "Single-type list (all bills or all payments)"
    return "Not recognised"


# --------------------------------------------------------------------------- #
# Reading files
# --------------------------------------------------------------------------- #
@dataclass
class RawSheet:
    name: str
    df: pd.DataFrame


def read_raw(data: bytes, filename: str) -> list[RawSheet]:
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "csv":
        text = None
        for enc in ("utf-8-sig", "latin-1"):
            try:
                text = data.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        rows = list(csv.reader(io.StringIO(text)))
        width = max((len(r) for r in rows), default=0)
        df = pd.DataFrame([r + [None] * (width - len(r)) for r in rows], dtype=object)
        return [RawSheet("CSV", df)]
    if ext in ("xlsx", "xlsm", "xls"):
        xf = pd.ExcelFile(io.BytesIO(data), engine="xlrd" if ext == "xls" else "openpyxl")
        return [RawSheet(s, xf.parse(s, header=None, dtype=object)) for s in xf.sheet_names]
    if ext == "pdf":
        return _read_pdf(data)
    raise ValueError(f"Unsupported file type '.{ext}'. Use .xlsx, .xls, .csv or a text-based .pdf.")


_DATE_RE = r"(?:\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{1,2}[- ][A-Za-z]{3,9}[- ,]+\d{2,4}|\d{4}-\d{2}-\d{2})"
_NUM_RE = r"\(?-?\d[\d,]*\.\d{1,2}\)?(?:\s?(?:Dr|Cr|DR|CR)\b\.?)?"


def _read_pdf(data: bytes) -> list[RawSheet]:
    import pdfplumber

    sheets: list[RawSheet] = []
    lines: list[str] = []
    tables_rows: list[list] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            for t in page.extract_tables() or []:
                for r in t:
                    if r and any(c not in (None, "") for c in r):
                        tables_rows.append([None if c is None else re.sub(r"\s*\n\s*", " ", str(c)).strip() for c in r])
            lines += (page.extract_text() or "").splitlines()
    if not lines and not tables_rows:
        raise ValueError("No text found in this PDF – it looks scanned. Please export from your software as Excel/CSV, or run OCR first.")
    if tables_rows:
        width = max(len(r) for r in tables_rows)
        df = pd.DataFrame([r + [None] * (width - len(r)) for r in tables_rows], dtype=object)
        if analyse(df).score >= 3:
            sheets.append(RawSheet("PDF tables", df))
    parsed = _parse_text_lines(lines)
    if parsed is not None:
        sheets.append(RawSheet("PDF text", parsed))
    if not sheets:
        raise ValueError("Could not find a transaction table in this PDF. Try exporting the report as Excel/CSV.")
    return sheets


def _parse_text_lines(lines: list[str]) -> pd.DataFrame | None:
    """Fallback for PDFs without ruled tables: date-led lines -> Date, Particulars, amounts."""
    rows = []
    for ln in lines:
        m = re.match(rf"^\s*({_DATE_RE})\s+(.*)$", ln)
        if not m:
            continue
        rest = m.group(2)
        nums = list(re.finditer(_NUM_RE, rest))
        if not nums:
            continue
        first = nums[0].start()
        desc = rest[:first].strip()
        vals = [n.group(0).strip() for n in nums]
        if len(vals) >= 3:
            vals = vals[-3:]
            rec = [m.group(1), desc, vals[0], vals[1], None, vals[2]]
        elif len(vals) == 2:
            rec = [m.group(1), desc, None, None, vals[0], vals[1]]
        else:
            rec = [m.group(1), desc, None, None, vals[0], None]
        rows.append(rec)
    if len(rows) < 2:
        return None
    hdr = ["Date", "Particulars", "Debit", "Credit", "Amount", "Balance"]
    df = pd.DataFrame([hdr] + rows, dtype=object)
    # drop all-empty columns so mapping isn't polluted
    keep = [j for j in df.columns if df.iloc[1:, j].notna().any() or j < 2]
    return df[keep].reset_index(drop=True)


def best_sheet(sheets: list[RawSheet]) -> tuple[RawSheet, Detected]:
    scored = [(s, analyse(s.df)) for s in sheets]
    scored.sort(key=lambda t: (t[1].score, len(t[0].df)), reverse=True)
    return scored[0]


# --------------------------------------------------------------------------- #
# Canonical rows
# --------------------------------------------------------------------------- #
def parse_amount(v) -> tuple[float, str | None]:
    """'1,23,456.50' -> 123456.5 ; '(500)' -> -500 ; '500 Cr' -> (500,'Cr'). NaN if not numeric."""
    if v is None:
        return np.nan, None
    if isinstance(v, (int, float, np.integer, np.floating)):
        return (np.nan, None) if pd.isna(v) else (float(v), None)
    s = str(v).strip()
    if s in ("", "nan", "None", "-", "–"):
        return np.nan, None
    side = None
    m = re.search(r"\b(dr|cr)\b\.?\s*$", s, re.I)
    if m:
        side = m.group(1).capitalize()
        s = s[: m.start()].strip()
    neg = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[^\d.\-]", "", s)
    if s in ("", "-", ".", "-."):
        return np.nan, None
    try:
        x = float(s)
    except ValueError:
        return np.nan, None
    return (-abs(x) if neg else x), side


def _to_dates(col: pd.Series) -> pd.Series:
    def one(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return pd.NaT
        if isinstance(v, (int, float, np.integer, np.floating)) and 20000 < float(v) < 80000:
            return pd.Timestamp("1899-12-30") + pd.Timedelta(days=float(v))
        try:
            iso = isinstance(v, str) and re.match(r"^\s*\d{4}-\d{2}-\d{2}", v) is not None
            return pd.to_datetime(v, dayfirst=not iso)
        except Exception:  # noqa: BLE001
            return pd.NaT
    return col.map(one).dt.normalize()


def build_rows(raw: pd.DataFrame, header_idx: int, mapping: dict) -> pd.DataFrame:
    body = raw.iloc[header_idx + 1:].reset_index(drop=True)
    out = pd.DataFrame(index=body.index)
    for f in FIELDS:
        out[f] = body.iloc[:, mapping[f]] if f in mapping and mapping[f] < body.shape[1] else None
    out["Date"] = _to_dates(out["Date"])
    for f in ("Ref", "Description", "Type", "Vendor", "Payment Mode"):
        out[f] = out[f].map(lambda v: None if v is None or str(v).strip() in ("", "nan", "None") else re.sub(r"\s+", " ", str(v)).strip())
    for f in ("Debit", "Credit", "Amount", "Balance"):
        parsed = out[f].map(parse_amount)
        out[f] = parsed.map(lambda t: t[0])
        out[f + "_side"] = parsed.map(lambda t: t[1])
    out["_src_row"] = body.index + header_idx + 2
    return _clean_text_cols(out)


_TEXT_COLS = ("Ref", "Description", "Type", "Vendor", "Payment Mode")


def _clean_text_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Missing text -> None (pandas may store NaN)."""
    df = df.copy()
    for c in _TEXT_COLS:
        if c in df:
            df[c] = pd.Series([v if isinstance(v, str) and v.strip() else None for v in df[c]], index=df.index, dtype=object)
    return df


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #
SKIP_RE = re.compile(r"\b(opening\s*balance|closing\s*balance|balance\s*(b/?f|c/?f)|brought\s*forward|carried\s*forward|"
                     r"b/f|c/f|grand\s*total|sub\s*total|total|net\s*balance|balance\s*due)\b", re.I)
BILL_RE = re.compile(r"\b(invoice|inv|bill|purchase|tax\s*inv\w*|debit\s*note|sales|sale|dn)\b", re.I)
PAY_RE = re.compile(r"\b(payment|paid|receipt|rcpt|neft|rtgs|imps|upi|cheque|chq|cash|bank|utr|tds|credit\s*note|"
                    r"cn|adjust\w*|journal|jv|contra|settle\w*|remittance|treds|advance|pmt)\b", re.I)


def _kw_kind(text: str | None) -> str | None:
    if not text:
        return None
    b, p = bool(BILL_RE.search(text)), bool(PAY_RE.search(text))
    if b and not p:
        return "Bill"
    if p and not b:
        return "Payment"
    return None


def _text_kind(r) -> str | None:
    return _kw_kind(r["Type"]) or _kw_kind(" ".join(x for x in (r["Description"], r["Ref"]) if x))


def infer_perspective(rows: pd.DataFrame) -> str | None:
    """'vendor' if invoice-like rows sit in Debit (vendor's own statement), 'ours' if in Credit; None if unclear."""
    if "Debit" not in rows or not (rows["Debit"].notna().any() or rows["Credit"].notna().any()):
        return None
    vend = ours = 0
    for _, r in rows.iterrows():
        k = _text_kind(r)
        if k is None:
            continue
        dr, cr = (r["Debit"] or 0) > 0, (r["Credit"] or 0) > 0
        if dr == cr:
            continue
        if (k == "Bill" and dr) or (k == "Payment" and cr):
            vend += 1
        else:
            ours += 1
    if vend + ours < 2 or max(vend, ours) < 2 * min(vend, ours) + 1:
        return None
    return "vendor" if vend > ours else "ours"


def classify(rows: pd.DataFrame, perspective: str = "vendor", default_kind: str | None = None) -> pd.DataFrame:
    """Add Kind (Bill/Payment/Skip/Review), Basis and Check columns.

    perspective: 'vendor' = vendor's own statement (Debit = invoices raised, Credit = receipts);
                 'ours'   = our ledger of the vendor (Credit = bills booked, Debit = payments made).
    default_kind: 'Bill' / 'Payment' for single-type lists without any other signal.
    """
    sign_for_dr = 1 if perspective == "vendor" else -1   # effect of a Dr on 'amount payable' in this perspective
    out = _clean_text_cols(rows)
    kinds, basis, check, amts = [], [], [], []
    prev_bal = None
    has_bal = out["Balance"].notna().any()
    has_neg_amount = (out["Amount"] < 0).any() and (out["Amount"] > 0).any()

    def signed_bal(r):
        if pd.isna(r["Balance"]):
            return None
        s = r["Balance_side"]
        v = abs(r["Balance"]) if s else r["Balance"]
        if s == "Dr":
            return v * sign_for_dr
        if s == "Cr":
            return -v * sign_for_dr
        return v

    for _, r in out.iterrows():
        text = " ".join(x for x in (r["Description"], r["Ref"], r["Type"]) if x)
        bal = signed_bal(r)
        skip = bool(SKIP_RE.search(text)) and not (r["Ref"] and BILL_RE.search(r["Ref"] or ""))
        amt_cols = [x for x in (r["Debit"], r["Credit"], r["Amount"]) if not pd.isna(x) and x != 0]
        if skip or pd.isna(r["Date"]) and not amt_cols:
            if skip and prev_bal is None:
                prev_bal = bal if bal is not None else (
                    _opening_from_amount(r, sign_for_dr))
            elif bal is not None:
                prev_bal = bal
            kinds.append("Skip"); basis.append("Opening/closing/total row" if skip else "No date/amount"); check.append(""); amts.append(np.nan)
            continue
        tk = _text_kind(r)
        k = b = c = None
        amount = np.nan
        dr = r["Debit"] if not pd.isna(r["Debit"]) and r["Debit"] != 0 else None
        cr = r["Credit"] if not pd.isna(r["Credit"]) and r["Credit"] != 0 else None
        if dr is not None or cr is not None:
            side = "Dr" if dr is not None else "Cr"
            amount = abs(dr if dr is not None else cr)
            k = ("Bill" if side == "Dr" else "Payment") if perspective == "vendor" else ("Bill" if side == "Cr" else "Payment")
            b = f"{side} column ({'vendor statement' if perspective == 'vendor' else 'our ledger'})"
            if tk and tk != k:
                c = f"Text looks like a {tk.lower()}"
        elif not pd.isna(r["Amount"]) and r["Amount"] != 0:
            amount = abs(r["Amount"])
            side = r["Amount_side"]
            if side in ("Dr", "Cr"):
                k = ("Bill" if side == "Dr" else "Payment") if perspective == "vendor" else ("Bill" if side == "Cr" else "Payment")
                b = f"{side} suffix on amount"
            elif r["Type"] and _kw_kind(r["Type"]):
                k, b = _kw_kind(r["Type"]), "Type column"
            elif tk:
                k, b = tk, "Keywords in description"
            elif has_bal and bal is not None and prev_bal is not None and abs(abs(bal - prev_bal) - amount) < 0.01:
                k = "Bill" if bal > prev_bal else "Payment"
                b = "Running balance moved " + ("up" if k == "Bill" else "down")
            elif has_neg_amount:
                k, b = ("Payment", "Negative amount") if r["Amount"] < 0 else ("Bill", "Positive amount")
            elif default_kind:
                k, b = default_kind, "File-level choice"
            else:
                k, b = "Review", "Could not tell – please choose"
        else:
            k, b, amount = "Skip", "No amount", np.nan
        if bal is not None:
            prev_bal = bal
        kinds.append(k); basis.append(b); check.append(c or ""); amts.append(amount)
    out["Kind"], out["Basis"], out["Check"], out["Amt"] = kinds, basis, check, amts
    # TReDS mode
    out["Mode"] = [
        "TReDS" if re.search(r"treds", " ".join(x for x in (m, t, d, rf) if x), re.I) else "Other"
        for m, t, d, rf in zip(out["Payment Mode"], out["Type"], out["Description"], out["Ref"])
    ]
    return out


def _opening_from_amount(r, sign_for_dr):
    for col in ("Debit", "Credit", "Amount"):
        v = r[col]
        if not pd.isna(v) and v != 0:
            side = "Dr" if col == "Debit" else ("Cr" if col == "Credit" else r["Amount_side"])
            if side == "Dr":
                return abs(v) * sign_for_dr
            if side == "Cr":
                return -abs(v) * sign_for_dr
            return abs(v)
    return None


# --------------------------------------------------------------------------- #
# Vendors + conversion to standard inputs
# --------------------------------------------------------------------------- #
def match_vendor(name: str | None, master_names: list[str]) -> tuple[str | None, str]:
    """Match a name to the vendor master. Returns (name, how) where how in exact/fuzzy/none."""
    if not name:
        return None, "none"
    keys = {vendor_key(n): n for n in master_names}
    k = vendor_key(name)
    if k in keys:
        return keys[k], "exact"
    close = difflib.get_close_matches(k, list(keys), n=1, cutoff=0.86)
    if close:
        return keys[close[0]], "fuzzy"
    return name, "none"


def guess_vendor(text: str, master_names: list[str]) -> str | None:
    """Find a master vendor name mentioned in the text above the table (e.g. 'Statement of account – XYZ')."""
    t = vendor_key(text)
    hits = [n for n in master_names if vendor_key(n) and vendor_key(n) in t]
    return max(hits, key=len) if hits else None


_REF_AFTER_KW = re.compile(r"\b(?:tax\s*invoice|invoice|inv|bill)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Za-z0-9][\w/\-.]*\d[\w/\-.]*)", re.I)
_REF_TOKEN = re.compile(r"(?<![\w/\-.])([A-Za-z]{1,6}[/\-]?\d[\w/\-.]*|\d+[/\-][\w/\-.]+)(?![\w/\-.])")


def extract_ref(text: str | None) -> str | None:
    """Pull an invoice number out of a narration such as 'Sales Invoice SL/001'."""
    if not text:
        return None
    m = _REF_AFTER_KW.search(text)
    if m:
        return m.group(1).rstrip(".-/")
    m = _REF_TOKEN.search(text)
    return m.group(1).rstrip(".-/") if m else None


def _ref_pattern(ref: str) -> re.Pattern | None:
    chunks = re.findall(r"[A-Za-z0-9]+", str(ref))
    if not chunks or (len(chunks) == 1 and chunks[0].isdigit() and len(chunks[0]) < 3) or sum(map(len, chunks)) < 2:
        return None
    return re.compile(r"(?<![A-Za-z0-9])" + r"[\W_]*".join(re.escape(c) for c in chunks) + r"(?![A-Za-z0-9])", re.I)


def to_inputs(cl: pd.DataFrame, default_vendor: str | None, master_names: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Turn classified rows (Kind edited by the user if needed) into raw Bills / Payments tables."""
    notes: list[str] = []
    use = cl[cl["Kind"].isin(["Bill", "Payment"]) & cl["Date"].notna() & cl["Amt"].notna()].copy()
    dropped = int(cl["Kind"].isin(["Bill", "Payment"]).sum() - len(use))
    if dropped:
        notes.append(f"{dropped} row(s) skipped – missing date or amount.")
    fuzzy = []

    def vend(v):
        name = v if v else default_vendor
        m, how = match_vendor(name, master_names)
        if how == "fuzzy":
            fuzzy.append(f"{name} → {m}")
        return m

    use["VendorFinal"] = use["Vendor"].map(vend)
    if use["VendorFinal"].isna().any():
        notes.append(f"{int(use['VendorFinal'].isna().sum())} row(s) have no vendor – choose the vendor for this file.")
        use = use[use["VendorFinal"].notna()]
    if fuzzy:
        notes.append("Vendor names matched approximately: " + "; ".join(sorted(set(fuzzy))[:8]))

    bills = use[use["Kind"] == "Bill"].copy()
    pays = use[use["Kind"] == "Payment"].copy()

    # Bill numbers
    got = bills["Ref"].isna()
    if got.any():
        bills.loc[got, "Ref"] = bills.loc[got, "Description"].map(extract_ref)
        if (~bills.loc[got, "Ref"].isna()).any():
            notes.append(f"{int((~bills.loc[got, 'Ref'].isna()).sum())} invoice number(s) were read from the narration.")
    missing = bills["Ref"].isna()
    if missing.any():
        bills.loc[missing, "Ref"] = [f"AUTO-{i}" for i in bills.loc[missing, "_src_row"]]
        notes.append(f"{int(missing.sum())} bill(s) had no invoice number – AUTO-<row> numbers were generated.")
    bills_out = pd.DataFrame({"Bill No": bills["Ref"], "Vendor Name": bills["VendorFinal"], "Bill Date": bills["Date"],
                              "Bill Amount": bills["Amt"], "Description": bills["Description"]})

    # Link payments to bills mentioned in their narration (whole-token match, separators ignored)
    index: dict[str, list[tuple[re.Pattern, str]]] = {}
    for _, b in bills.iterrows():
        pat = _ref_pattern(b["Ref"])
        if pat is not None:
            index.setdefault(vendor_key(b["VendorFinal"]), []).append((pat, b["Ref"]))
    linked = 0

    def link(r):
        nonlocal linked
        text = " ".join(x for x in (r["Description"], r["Ref"]) if x)
        hits = {orig for pat, orig in index.get(vendor_key(r["VendorFinal"]), []) if pat.search(text)}
        if len(hits) == 1:
            linked += 1
            return next(iter(hits))
        return None

    pays["LinkedBill"] = pays.apply(link, axis=1) if len(pays) else None
    if len(pays):
        notes.append(f"{linked} of {len(pays)} payment(s) linked to a specific bill from their narration; the rest are applied oldest-bill-first.")
    pays_out = pd.DataFrame({"Vendor Name": pays["VendorFinal"], "Payment Date": pays["Date"], "Amount Paid": pays["Amt"],
                             "Bill No": pays["LinkedBill"], "Reference": pays["Ref"], "Payment Mode": pays["Mode"]})
    return bills_out.reset_index(drop=True), pays_out.reset_index(drop=True), notes
