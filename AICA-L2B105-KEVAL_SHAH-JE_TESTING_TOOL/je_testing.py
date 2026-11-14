"""
============================================================================
 JOURNAL ENTRY TESTING  (JE Testing)  --  Simplified Audit Analytics Tool
----------------------------------------------------------------------------
 Risk-based journal-entry testing for the risk of management override of
 controls (ICAI SA 240). Reads SAP and other ERP GL extracts.

 PIPELINE
   GL extract (Excel / CSV)  [+ optional Trial Balance]
   ->  column mapping  ->  data-quality checks  ->  GL-to-TB reconciliation
   ->  12 simple risk rules  ->  weighted risk score per journal entry
   ->  Low / Medium / High / Critical  ->  sample selection
   ->  audit-ready Excel workpaper

 This module is the ENGINE + command line.  je_testing_app.py is the
 desktop window.

 USAGE
     python je_testing.py "GL dump.xlsx"              # analyse a GL only
     python je_testing.py "GL dump.xlsx" "TB.xlsx"    # analyse GL linked to a TB
     python je_testing.py                             # use the files in input\\

 Thresholds, risk weights, user lists, keywords and holidays live in
 je_config.json (auto-created next to the program on first run).
============================================================================
"""

import sys
import re
import json
import secrets
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter


# ---------------------------------------------------------------------------
# LOCATIONS
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR   = BASE_DIR / "input"
OUTPUT_DIR  = BASE_DIR / "OUTPUT_WORKPAPERS"
CONFIG_PATH = BASE_DIR / "je_config.json"


# ---------------------------------------------------------------------------
# CANONICAL FIELDS  &  SAP / ERP COLUMN ALIASES
# ---------------------------------------------------------------------------
# The engine works with these internal field names; COLUMN_ALIASES maps the
# common SAP (and generic ERP) headings onto them.  Matching ignores case,
# spaces and punctuation, so "Amount in local currency" == "amountinlocalcurrency".
COLUMN_ALIASES = {
    "je_id":        ["documentnumber", "documentno", "docno", "belnr",
                     "journalentry", "jeid", "voucherno", "vouchernumber",
                     "entryno"],
    "company":      ["companycode", "bukrs", "company", "cocode"],
    "account":      ["account", "glaccount", "glaccountno", "accountno",
                     "accountnumber", "hkont", "glcode", "ledgercode"],
    "account_name": ["accountname", "glaccountname", "accountdescription",
                     "gldescription", "ledgername"],
    "user":         ["username", "user", "createdby", "enteredby", "userid",
                     "usnam", "postedby"],
    "doc_type":     ["documenttype", "doctype", "blart", "vouchertype"],
    "entry_date":   ["entrydate", "cpudate", "createdon", "enteredon",
                     "systemdate"],
    "posting_date": ["postingdate", "postdate", "budat", "gldate"],
    "doc_date":     ["documentdate", "docdate", "bldat"],
    "period":       ["yearmonth", "period", "fiscalperiod", "postingperiod",
                     "fiscalyearperiod"],
    "amount":       ["amountinlocalcurrency", "amountincompanycodecurrency",
                     "localamount", "amountlc", "dmbtr", "amount", "amountinr"],
    "narration":    ["text", "description", "narration", "linetext",
                     "itemtext", "sgtxt", "remarks", "headertext"],
    # SAP 'offsetting account' (GKONT): the other side of the entry.  Lets the
    # tool show both legs even when the extract holds only some accounts.
    "offset_acct":  ["offsettingaccount", "offsettingacctno", "offsettingaccountno",
                     "offsetaccount", "offsettingacct", "gkont"],
    "offset_name":  ["offsettingaccountname", "nameofoffsettingaccount",
                     "offsetaccountname"],
}

# Trial Balance headings.  Movement for the year = closing - opening.
TB_ALIASES = {
    "account":      ["glaccount", "glacct", "account", "glaccountno", "accountno",
                     "accountnumber", "ledgercode", "glcode", "hkont"],
    "account_name": ["accountname", "glaccountname", "glaccountdescription",
                     "accountdescription", "ledgername", "gldescription",
                     "description", "particulars"],
    "opening":      ["openingbalance", "opening", "ob", "balancecarriedforward",
                     "balancebroughtforward", "openingbal"],
    "closing":      ["closingbalance", "closing", "cb", "endingbalance",
                     "balance", "closingbal", "finalbalance"],
}

# Fields we cannot run without.
ESSENTIAL_FIELDS = ["je_id", "account", "amount"]
TB_ESSENTIAL_FIELDS = ["account", "closing"]

# Largest file the tool will read (protects against a hang on a wrong/huge file).
MAX_FILE_MB = 300

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                 "Saturday", "Sunday"]


# ---------------------------------------------------------------------------
# DEFAULT CONFIGURATION  (written to je_config.json on first run)
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "_comment": "JE Testing configuration. Edit values to tune the tool to a "
                "client. Delete this file to regenerate defaults.",

    # ---- manual journals ----
    "manual_doc_types":   ["SA"],          # SAP 'SA' = manual G/L journal

    # ---- people (replace the demo IDs with the client's access list) ----
    "privileged_users":   [],              # IT / admin IDs with elevated access
    "super_users":        [],              # senior users (e.g. CFO) who can post anywhere

    # ---- timing ----
    "non_working_days":   ["Sunday"],      # add "Saturday" for a 5-day week
    "period_end_days":    3,               # last N days of each month
    "back_dated_lag_days": 5,              # entry date later than posting date by > N days
    "public_holidays": [                   # YYYY-MM-DD, edit for the year under audit
        "2025-04-14", "2025-05-01", "2025-08-15", "2025-08-27", "2025-10-02",
        "2025-10-21", "2025-10-22", "2025-11-05", "2025-12-25",
        "2026-01-01", "2026-01-26", "2026-03-04"
    ],

    # ---- amounts (in local currency) ----
    "round_base":         100000.0,        # "round" = exact multiple of Rs. 1,00,000
    "large_amount":       10000000.0,      # >= Rs. 1 crore = large

    # ---- narration ----
    "narration_min_len":  4,
    "generic_descriptions": ["adjustment", "adjustments", "correction", "entry",
                             "journal", "misc", "miscellaneous", "reclass",
                             "transfer", "rectification", "jv", "test", "being"],
    "fraud_keywords": ["kickback", "bribe", "fake", "fictitious", "plug",
                       "balancing figure", "cover up", "off the book", "off book",
                       "fabricate", "do not record", "as instructed",
                       "as discussed", "personal use", "siphon", "override",
                       "topside", "top side"],

    # ---- risk weights: points each rule adds to a journal's score ----
    "risk_weights": {
        "non_working_day": 10, "holiday": 10, "period_end": 10, "back_dated": 15,
        "privileged_user": 20, "manual_super_user": 25, "manual_journal": 15,
        "round_amount": 10, "large_amount": 15,
        "missing_desc": 10, "generic_desc": 5, "fraud_keyword": 25
    },

    # ---- risk bands (on the total journal score) ----
    "category_bands": {"critical": 60, "high": 40, "medium": 20},

    # ---- sampling ----
    "risk_sample_size":   25,              # top-N by risk score
    "random_sample_size": 15,              # random picks from the rest
    "random_seed":        "",              # blank = new unpredictable seed each run
                                           # (the seed used is recorded in the workpaper)

    # ---- GL-to-TB reconciliation ----
    "tb_tolerance":       1.0              # differences up to Rs. 1 treated as agreed
}

# Settings that must be numbers (checked when je_config.json is loaded).
NUMERIC_KEYS = ["period_end_days", "back_dated_lag_days", "round_base",
                "large_amount", "narration_min_len", "risk_sample_size",
                "random_sample_size", "tb_tolerance"]


# ---------------------------------------------------------------------------
# CONFIG LOADING
# ---------------------------------------------------------------------------
def load_config(path=CONFIG_PATH, create=True):
    """Load je_config.json, filling any missing keys from DEFAULT_CONFIG."""
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))   # deep copy
    path = Path(path)
    if path.exists():
        try:
            cfg = _deep_merge(cfg, json.loads(path.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"  (Could not read {path.name}: {e}; using defaults.)")
    elif create:
        try:
            path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        except OSError as e:
            print(f"  (Could not create {path.name}: {e}; using defaults.)")
    return _validate_config(cfg)


def _validate_config(cfg):
    """Reject a hand-edited setting that is not a number, instead of failing
    half-way through a run with a confusing error."""
    for key in NUMERIC_KEYS:
        try:
            cfg[key] = float(cfg[key])
        except (TypeError, ValueError):
            print(f"  (Setting '{key}' is not a number; using default.)")
            cfg[key] = float(DEFAULT_CONFIG[key])
    for key, default in DEFAULT_CONFIG["risk_weights"].items():
        try:
            cfg["risk_weights"][key] = int(float(cfg["risk_weights"].get(key, default)))
        except (TypeError, ValueError):
            cfg["risk_weights"][key] = default
    return cfg


def save_config(cfg, path=CONFIG_PATH):
    Path(path).write_text(json.dumps(cfg, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    return path


def _deep_merge(base, override):
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def _norm(text):
    return re.sub(r"[^a-z0-9]", "", str(text).strip().lower())


def to_number(series):
    """Robust numeric conversion: handles '1,20,000.00', '(500)', blanks."""
    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0.0)
    s = (series.astype(str)
               .str.replace(",", "", regex=False)
               .str.replace("₹", "", regex=False)
               .str.strip())
    s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def _parse_dates(series):
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    out = pd.to_datetime(series, errors="coerce", format="%Y-%m-%d")
    if out.isna().mean() > 0.5:
        out = pd.to_datetime(series, errors="coerce", dayfirst=True, format="mixed")
    return out


# ---------------------------------------------------------------------------
# DATA IMPORT  &  FIELD MAPPING
# ---------------------------------------------------------------------------
def load_raw(path, aliases=COLUMN_ALIASES):
    """Read a GL or TB file (Excel / CSV).  Finds the header row even if the
    file has title rows on top, and in a multi-sheet workbook picks the sheet
    whose headings best match the expected columns."""
    path = Path(path)
    if path.suffix.lower() not in (".xlsx", ".xlsm", ".xls", ".csv"):
        raise ValueError(f"'{path.name}' is not a spreadsheet. "
                         "Please choose an Excel (.xlsx, .xls) or CSV (.csv) file.")
    size_mb = path.stat().st_size / 1_048_576
    if size_mb == 0:
        raise ValueError(f"'{path.name}' is empty (0 bytes).")
    if size_mb > MAX_FILE_MB:
        raise ValueError(f"{path.name} is {size_mb:,.0f} MB; the limit is {MAX_FILE_MB} MB. "
                         "Split the extract (e.g. by quarter) and run each part.")

    if path.suffix.lower() == ".csv":
        try:
            raw = pd.read_csv(path, header=None, dtype=str, keep_default_na=False,
                              encoding="utf-8-sig")
        except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as e:
            raise ValueError(f"'{path.name}' could not be read as a CSV file ({e}).") from None
        if raw.empty:
            raise ValueError(f"'{path.name}' has no data.")
        return _promote_header(raw, aliases)

    try:
        xl = pd.ExcelFile(path)
    except Exception as e:   # zip/xml/format errors from a damaged or fake .xlsx
        raise ValueError(f"'{path.name}' is not a valid Excel file - it may be damaged "
                         f"or saved in another format ({type(e).__name__}).") from None
    best_raw, best_score = None, -1
    for sheet in xl.sheet_names:
        try:
            candidate = xl.parse(sheet, header=None)
        except (ValueError, KeyError) as e:          # unreadable sheet: skip it
            print(f"  (Skipped sheet '{sheet}': {e})")
            continue
        if candidate.empty:
            continue
        score = max((_header_score(candidate.iloc[i], aliases)
                     for i in range(min(20, len(candidate)))), default=0)
        if score > best_score:
            best_score, best_raw = score, candidate
    if best_raw is None or best_raw.empty:
        raise ValueError(f"'{path.name}' has no data.")
    return _promote_header(best_raw, aliases)


def _header_score(row, aliases=COLUMN_ALIASES):
    norms = {_norm(v) for v in row.tolist() if pd.notna(v)}
    return sum(1 for names in aliases.values()
               if any(_norm(a) in norms for a in names))


def _promote_header(raw, aliases=COLUMN_ALIASES):
    best_row = max(range(min(20, len(raw))),
                   key=lambda i: _header_score(raw.iloc[i], aliases))
    head = raw.iloc[best_row]
    cols = [str(head[j]).strip() if pd.notna(head[j]) else f"col{j}"
            for j in range(raw.shape[1])]
    data = raw.iloc[best_row + 1:].copy()
    data.columns = cols
    data = _dedupe_columns(data)
    return data.dropna(how="all").reset_index(drop=True)


def _dedupe_columns(data):
    """SAP extracts sometimes repeat a heading; keep the copy with most data."""
    if not data.columns.duplicated().any():
        return data
    keep = []
    for name in pd.unique(data.columns):
        positions = [i for i, c in enumerate(data.columns) if c == name]
        keep.append(max(positions, key=lambda p: data.iloc[:, p]
                        .replace("", np.nan).notna().sum()))
    return data.iloc[:, sorted(keep)].copy()


def build_mapping(df, aliases=COLUMN_ALIASES):
    """Return {canonical_field: actual_column} auto-detected from headers."""
    lookup = {}
    for actual in df.columns:
        lookup.setdefault(_norm(actual), actual)
    mapping = {}
    for field, names in aliases.items():
        for alias in names:
            if _norm(alias) in lookup:
                mapping[field] = lookup[_norm(alias)]
                break
    return mapping


FIELD_HINTS = {
    "je_id":   "Document Number (SAP: BELNR)",
    "account": "G/L Account (SAP: HKONT)",
    "amount":  "Amount in Local Currency (SAP: DMBTR)",
    "closing": "Closing Balance (or 'TB - <company code>')",
}


def validate_mapping(mapping, essential=ESSENTIAL_FIELDS, what="GL"):
    missing = [f for f in essential if f not in mapping]
    if missing:
        need = "\n".join(f"   - {FIELD_HINTS.get(f, f)}" for f in missing)
        raise ValueError(
            f"This does not look like a {what} file - required column(s) not found:\n"
            f"{need}\n\nCheck that you selected the right file, or rename the column "
            "heading and run again.")


def apply_mapping(df, mapping):
    """Build the clean working table from the raw extract + mapping."""
    out = pd.DataFrame(index=df.index)
    for field, actual in mapping.items():
        if actual in df.columns:
            out[field] = df[actual]

    # exact duplicate lines (every mapped column identical) - before any cleaning
    out["dup_line"] = out.astype(str).duplicated(keep="first")

    # amounts typed as text (e.g. "1,2O,000" with a letter O) would silently
    # become 0, so remember which non-blank values could not be read
    raw_amt = out["amount"].fillna("").astype(str).str.strip().replace({"nan": "", "None": ""})
    out["amount"] = to_number(out["amount"])
    num_check = pd.to_numeric(raw_amt.str.replace(",", "", regex=False)
                              .str.replace("₹", "", regex=False)
                              .str.replace(r"^\((.*)\)$", r"-\1", regex=True),
                              errors="coerce")
    out["amount_invalid"] = (raw_amt != "") & num_check.isna()

    date_col = next((d for d in ("posting_date", "doc_date", "entry_date") if d in out), None)
    raw_date = (out[date_col].fillna("").astype(str).str.strip().replace({"nan": "", "NaT": "", "None": ""})
                if date_col else pd.Series("", index=out.index))
    for d in ("posting_date", "entry_date", "doc_date"):
        if d in out:
            out[d] = _parse_dates(out[d])
    out["date_invalid"] = (raw_date != "") & (out[date_col].isna() if date_col else False)
    # one canonical date for the timing rules
    if "posting_date" in out:
        out["date"] = out["posting_date"]
    elif "doc_date" in out:
        out["date"] = out["doc_date"]
    elif "entry_date" in out:
        out["date"] = out["entry_date"]
    else:
        out["date"] = pd.NaT

    for t in ("je_id", "company", "account", "account_name", "user", "doc_type",
              "period", "narration", "offset_acct", "offset_name"):
        if t in out:
            out[t] = (out[t].fillna("").astype(str).str.strip()
                            .replace({"nan": "", "NaT": "", "None": ""}))
        else:
            out[t] = ""

    out["abs_amount"] = out["amount"].abs()
    # document + company + period guards against document-number reuse
    out["je_key"] = out["company"] + "|" + out["je_id"] + "|" + out["period"]
    out = out.reset_index(drop=True)
    out["row_id"] = out.index + 1
    return out


def financial_year(df, start_month=4):
    """The financial year most of the GL falls in (Indian FY: April - March)."""
    valid = df["date"].dropna()
    if valid.empty:
        return None, None
    fy = np.where(valid.dt.month >= start_month, valid.dt.year, valid.dt.year - 1)
    y = int(pd.Series(fy).mode()[0])
    start = pd.Timestamp(year=y, month=start_month, day=1)
    return start, start + pd.DateOffset(years=1) - pd.Timedelta(days=1)


def data_quality(df):
    """Completeness and accuracy checks shown to the auditor before relying on
    the data (SA 500).  Status: ok / ERROR (must be resolved) / review."""
    checks = []
    checks.append(["Total line items", len(df), ""])
    checks.append(["Distinct journal entries", df["je_key"].nunique(), ""])
    checks.append(["Distinct accounts", df["account"].nunique(), ""])
    checks.append(["Distinct users", df["user"].replace("", np.nan).nunique(), ""])

    fy_start, fy_end = financial_year(df)
    outside = (int((df["date"].notna() & ((df["date"] < fy_start) | (df["date"] > fy_end))).sum())
               if fy_start is not None else 0)
    for label, n, sev in (
            ("Lines with an amount that is not a number", int(df["amount_invalid"].sum()), "ERROR"),
            ("Lines with an invalid date (e.g. 31-02-2026)", int(df["date_invalid"].sum()), "ERROR"),
            ("Lines with no posting date", int((df["date"].isna() & ~df["date_invalid"]).sum()), "ERROR"),
            ("Lines dated outside the financial year", outside, "ERROR"),
            ("Exact duplicate lines", int(df["dup_line"].sum()), "ERROR"),
            ("Lines with no account", int((df["account"] == "").sum()), "ERROR"),
            ("Lines with no user", int((df["user"] == "").sum()), "review"),
            ("Lines with zero amount", int(((df["abs_amount"] == 0) & ~df["amount_invalid"]).sum()), "review")):
        checks.append([label, n, sev if n else "ok"])

    unbal = int((df.groupby("je_key")["amount"].sum().abs() > 1.0).sum())
    checks.append(["Journal entries that do not net to 0", unbal, "ERROR" if unbal else "ok"])

    total_dr = float(df.loc[df["amount"] > 0, "amount"].sum())
    total_cr = float(-df.loc[df["amount"] < 0, "amount"].sum())
    checks.append(["Total debits", round(total_dr, 2), ""])
    checks.append(["Total credits", round(total_cr, 2), ""])
    checks.append(["Debit - Credit difference", round(total_dr - total_cr, 2),
                   "ok" if abs(total_dr - total_cr) <= 1 else "ERROR"])

    valid = df["date"].dropna()
    rng = f"{valid.min():%d-%m-%Y} to {valid.max():%d-%m-%Y}" if not valid.empty else ""
    checks.append(["Posting date range", rng, ""])
    fy_txt = f"{fy_start:%d-%m-%Y} to {fy_end:%d-%m-%Y}" if fy_start is not None else ""
    checks.append(["Financial year (detected)", fy_txt, ""])
    return {"checks": checks, "total_debit": total_dr, "total_credit": total_cr,
            "fy": fy_txt}


def count_issues(checks):
    return sum(1 for c in checks if c[2] in ("ERROR", "review"))


# ---------------------------------------------------------------------------
# TRIAL BALANCE  --  link the GL to the TB (completeness of the population)
# ---------------------------------------------------------------------------
def load_tb(path):
    """Read a Trial Balance: one row per account with closing (and ideally
    opening) balance.  Debit balances positive, credit balances negative."""
    raw = load_raw(path, TB_ALIASES)
    mapping = build_mapping(raw, TB_ALIASES)
    if "closing" not in mapping:
        # SAP-style TB headings such as "TB - 1610" (ledger balance for company
        # code 1610).  Prefer the ledger balance over a "Derived"/reclassified
        # one, because reclassifications never pass through the GL.
        for pattern in (r"^tb\d*$", r"^derivedtb\d*$"):
            hit = [c for c in raw.columns if re.match(pattern, _norm(c))]
            if hit:
                mapping["closing"] = hit[0]
                break
    validate_mapping(mapping, TB_ESSENTIAL_FIELDS, "Trial Balance")
    tb = pd.DataFrame({
        "account": raw[mapping["account"]].fillna("").astype(str).str.strip(),
        "tb_name": (raw[mapping["account_name"]].fillna("").astype(str).str.strip()
                    if "account_name" in mapping else ""),
        "opening": to_number(raw[mapping["opening"]]) if "opening" in mapping else 0.0,
        "closing": to_number(raw[mapping["closing"]]),
    })
    tb = tb[tb["account"] != ""]
    if tb.empty:
        raise ValueError("The Trial Balance has no account rows.")
    dup_accounts = int(tb["account"].duplicated().sum())
    tb = (tb.groupby("account", as_index=False)
            .agg(tb_name=("tb_name", "first"), opening=("opening", "sum"),
                 closing=("closing", "sum")))
    tb["tb_movement"] = tb["closing"] - tb["opening"]
    tb.attrs.update(has_opening="opening" in mapping, dup_accounts=dup_accounts,
                    closing_total=round(float(tb["closing"].sum()), 2),
                    opening_total=round(float(tb["opening"].sum()), 2))
    return tb, mapping


def tb_checks(tb, tb_summary, cfg):
    """Data-quality rows about the Trial Balance itself."""
    tol = float(cfg.get("tb_tolerance", 1.0))
    ct, ot = tb.attrs.get("closing_total", 0.0), tb.attrs.get("opening_total", 0.0)
    return [
        ["TB closing balances total (must be 0)", ct, "ok" if abs(ct) <= tol else "ERROR"],
        ["TB opening balances total (must be 0)", ot, "ok" if abs(ot) <= tol else "ERROR"],
        ["Account appearing more than once in TB", tb.attrs.get("dup_accounts", 0),
         "ERROR" if tb.attrs.get("dup_accounts", 0) else "ok"],
        ["Accounts posted in GL but missing from TB", tb_summary["gl_only"],
         "ERROR" if tb_summary["gl_only"] else "ok"],
        ["Accounts where GL does not agree to TB", tb_summary["differences"],
         "ERROR" if tb_summary["differences"] else "ok"],
    ]


def reconcile_tb(df, tb, cfg):
    """For every account: GL net movement (sum of the GL dump) vs TB movement
    (closing - opening).  Differences mean the GL extract may be incomplete."""
    tol = float(cfg.get("tb_tolerance", 1.0))
    gl = (df.groupby("account", as_index=False)
            .agg(gl_movement=("amount", "sum"), gl_lines=("row_id", "count")))
    rec = tb.merge(gl, on="account", how="outer")
    rec["tb_name"] = rec["tb_name"].fillna("")
    for c in ("opening", "closing", "tb_movement", "gl_movement", "gl_lines"):
        rec[c] = rec[c].fillna(0.0)
    rec["difference"] = (rec["tb_movement"] - rec["gl_movement"]).round(2)
    in_tb = rec["account"].isin(tb["account"])
    in_gl = rec["account"].isin(df["account"])
    rec["status"] = np.select(
        [~in_tb, rec["difference"].abs() <= tol],
        ["In GL but not in TB", "Agrees"],
        default="DIFFERENCE")
    rec.loc[in_tb & ~in_gl & (rec["difference"].abs() <= tol), "status"] = "Agrees (no GL movement)"
    order = {"DIFFERENCE": 0, "In GL but not in TB": 1}
    rec = rec.sort_values(by=["status", "account"],
                          key=lambda s: s.map(order).fillna(2) if s.name == "status" else s)
    view = rec.rename(columns={
        "account": "Account", "tb_name": "Account Name (TB)",
        "opening": "TB Opening", "closing": "TB Closing",
        "tb_movement": "TB Movement (Closing - Opening)",
        "gl_movement": "GL Net Movement", "gl_lines": "GL Lines",
        "difference": "Difference (TB - GL)", "status": "Status"})
    cols = ["Account", "Account Name (TB)", "TB Opening", "TB Closing",
            "TB Movement (Closing - Opening)", "GL Net Movement", "GL Lines",
            "Difference (TB - GL)", "Status"]
    view = view[cols].reset_index(drop=True)
    summary = {
        "accounts_tb": int(in_tb.sum()),
        "agreed": int(view["Status"].str.startswith("Agrees").sum()),
        "differences": int((view["Status"] == "DIFFERENCE").sum()),
        "gl_only": int((view["Status"] == "In GL but not in TB").sum()),
        "net_difference": round(float(rec["difference"].abs().sum()), 2),
        "tb_balanced": abs(float(tb["closing"].sum())) <= tol,
        "has_opening": bool(tb.attrs.get("has_opening", True)),
    }
    return view, summary


def add_tb_names(df, tb):
    """Fill blank account and offsetting-account names in the GL from the TB."""
    names = dict(zip(tb["account"], tb["tb_name"]))
    for acc_col, name_col in (("account", "account_name"), ("offset_acct", "offset_name")):
        blank = df[name_col] == ""
        df.loc[blank, name_col] = df.loc[blank, acc_col].map(names).fillna("")
    return df


# ---------------------------------------------------------------------------
# THE 12 RISK RULES  --  label, assertion, suggested procedure, SA reference
# ---------------------------------------------------------------------------
RULES = {
    # ---- WHEN was it posted? ----
    "non_working_day":   ("Posted on a Sunday / non-working day", "Occurrence",
                          "Inspect support and confirm the business reason for a non-working-day posting.",
                          "SA 240.A43"),
    "holiday":           ("Posted on a public holiday", "Occurrence",
                          "Corroborate with source documents; confirm who authorised a holiday posting.",
                          "SA 240.A43"),
    "period_end":        ("Posted near month-end", "Cut-off",
                          "Vouch to evidence; test that the entry belongs in the period.",
                          "SA 240.A43"),
    "back_dated":        ("Back-dated (entered well after posting date)", "Cut-off / Occurrence",
                          "Investigate the delay between entry and posting date; confirm the period was open.",
                          "SA 240.A43"),
    # ---- WHO posted it? ----
    "privileged_user":   ("Posted by a privileged / IT user", "Authorisation",
                          "Confirm segregation of duties; verify independent review of the entry.",
                          "SA 240.A43, SA 315"),
    "manual_super_user": ("Manual entry by a super-user", "Management override",
                          "Inspect authorisation and supporting evidence for the manual entry.",
                          "SA 240.32-33"),
    "manual_journal":    ("Manual journal entry", "Management override",
                          "Manual JEs are the core SA 240 population; vouch approval and support.",
                          "SA 240.A43"),
    # ---- HOW MUCH? ----
    "round_amount":      ("Round-sum amount", "Accuracy / Valuation",
                          "Round figures often indicate estimates; vouch to the basis of calculation.",
                          "SA 240.A43"),
    "large_amount":      ("Large amount", "Accuracy / Valuation",
                          "Obtain and inspect full supporting documentation.",
                          "SA 240.A43"),
    # ---- WHAT does the narration say? ----
    "missing_desc":      ("Missing narration", "Occurrence",
                          "Obtain an explanation; an unexplained entry weakens the audit trail.",
                          "SA 240.A43, SA 230"),
    "generic_desc":      ("Generic / vague narration", "Occurrence",
                          "Seek specific support; vague text can hide the entry's real nature.",
                          "SA 240.A43, SA 230"),
    "fraud_keyword":     ("Narration contains a red-flag keyword", "Occurrence (fraud)",
                          "Investigate the wording; escalate under the fraud-response protocol.",
                          "SA 240.32-33"),
}
RULE_KEYS = list(RULES.keys())


def run_rules(df, cfg):
    """Add one True/False column per rule (named as in RULES) to every GL line."""
    df = df.copy()
    dt = df["date"]
    has_date = dt.notna()

    # ---------- WHEN ----------
    off_days = {WEEKDAY_NAMES.index(d.strip().title())
                for d in cfg.get("non_working_days", []) if d.strip().title() in WEEKDAY_NAMES}
    df["non_working_day"] = has_date & dt.dt.weekday.isin(off_days)
    holidays = set(pd.to_datetime(cfg.get("public_holidays", []), errors="coerce").date)
    df["holiday"] = has_date & dt.dt.date.isin(holidays)
    days_to_month_end = ((dt + pd.offsets.MonthEnd(0)) - dt).dt.days
    df["period_end"] = has_date & (days_to_month_end < cfg["period_end_days"])
    if "entry_date" in df.columns and "posting_date" in df.columns:
        lag = (df["entry_date"] - df["posting_date"]).dt.days
        df["back_dated"] = lag.fillna(0) > cfg["back_dated_lag_days"]
    else:
        df["back_dated"] = False

    # ---------- WHO ----------
    manual_types = {t.upper() for t in cfg.get("manual_doc_types", [])}
    df["manual_journal"] = df["doc_type"].str.upper().isin(manual_types)
    df["privileged_user"] = df["user"].isin(set(cfg.get("privileged_users", [])))
    df["manual_super_user"] = (df["manual_journal"]
                               & df["user"].isin(set(cfg.get("super_users", []))))

    # ---------- HOW MUCH ----------
    base = float(cfg["round_base"])
    if base > 0:
        df["round_amount"] = (df["abs_amount"] >= base) & (np.mod(df["abs_amount"], base) == 0)
    else:
        df["round_amount"] = False
    df["large_amount"] = df["abs_amount"] >= cfg["large_amount"]

    # ---------- WHAT (narration) ----------
    text = df["narration"].str.strip()
    df["missing_desc"] = text == ""
    generic = {_norm(g) for g in cfg.get("generic_descriptions", [])}
    df["generic_desc"] = (text != "") & (
        (text.str.len() < cfg["narration_min_len"]) | text.map(_norm).isin(generic))
    df["fraud_keyword"] = _contains_any(text.str.lower(), cfg.get("fraud_keywords", []))

    for k in RULE_KEYS:
        df[k] = df[k].fillna(False).astype(bool)
    return df


def _contains_any(text_lower, keywords):
    kws = [k.lower().strip() for k in keywords if k.strip()]
    if not kws:
        return pd.Series(False, index=text_lower.index)
    return text_lower.str.contains("|".join(re.escape(k) for k in kws),
                                   regex=True, na=False)


# ---------------------------------------------------------------------------
# WEIGHTED RISK SCORING  ->  one row per journal entry
# ---------------------------------------------------------------------------
def _journal_sides(df):
    """Debit and credit accounts of every journal, as 'account name' labels.
    Each line contributes its own account to its side and, if the extract
    carries the SAP offsetting account, that account to the opposite side -
    so both legs show even when the extract holds only one side."""
    names = {}
    for acc, nm in zip(df["offset_acct"], df["offset_name"]):
        if acc and nm:
            names[acc] = nm
    for acc, nm in zip(df["account"], df["account_name"]):
        if acc and nm:
            names[acc] = nm
    own = pd.DataFrame({"je_key": df["je_key"], "acc": df["account"],
                        "side": np.where(df["amount"] > 0, "Dr", "Cr")})
    off = pd.DataFrame({"je_key": df["je_key"], "acc": df["offset_acct"],
                        "side": np.where(df["amount"] > 0, "Cr", "Dr")})
    legs = pd.concat([own[df["amount"] != 0], off[(df["offset_acct"] != "") & (df["amount"] != 0)]])
    legs = legs[legs["acc"] != ""].drop_duplicates()
    legs["label"] = [f"{a} {names[a]}" if names.get(a) else a for a in legs["acc"]]
    joined = (legs.groupby(["je_key", "side"])["label"]
                  .agg(lambda s: "; ".join(sorted(s))[:120]).unstack())
    empty = pd.Series(dtype=str)
    return joined.get("Dr", empty), joined.get("Cr", empty)


def score_journals(df, cfg):
    """Roll line-level flags up to the journal entry.  A journal triggers a rule
    if ANY of its lines does; its score is the sum of the triggered weights."""
    weights = cfg["risk_weights"]
    bands = cfg["category_bands"]

    g = df.groupby("je_key")
    je = pd.DataFrame(index=g.size().index)
    je["je_id"]    = g["je_id"].first()
    je["company"]  = g["company"].first()
    je["date"]     = g["date"].min()
    je["doc_type"] = g["doc_type"].agg(lambda s: ",".join(sorted(set(s)))[:30])
    je["user"]     = g["user"].agg(lambda s: ",".join(sorted(set(x for x in s if x)))[:40])
    je["n_lines"]  = g.size()
    je["amount"]   = g["amount"].apply(lambda s: float(s[s > 0].sum()))   # debit total
    je["narration"] = g["narration"].agg(
        lambda s: "; ".join(sorted(set(x for x in s if x)))[:80])
    dr, cr = _journal_sides(df)
    je["dr_accounts"] = dr.reindex(je.index).fillna("")
    je["cr_accounts"] = cr.reindex(je.index).fillna("")

    flags = g[RULE_KEYS].any()
    je = je.join(flags)
    w = np.array([weights.get(k, 0) for k in RULE_KEYS], dtype=float)
    je["risk_score"] = (flags.values * w).sum(axis=1).astype(int)
    je["n_flags"] = flags.sum(axis=1).astype(int)
    je["triggered"] = flags.apply(
        lambda r: "; ".join(RULES[k][0] for k in RULE_KEYS if r[k]), axis=1)

    def _band(s):
        if s >= bands["critical"]: return "Critical"
        if s >= bands["high"]:     return "High"
        if s >= bands["medium"]:   return "Medium"
        return "Low"
    je["risk_category"] = je["risk_score"].map(_band)

    return (je.reset_index()
              .sort_values(["risk_score", "amount"], ascending=[False, False])
              .reset_index(drop=True))


# ---------------------------------------------------------------------------
# SAMPLING  (risk-based + random, per SA 530)
# ---------------------------------------------------------------------------
def build_samples(je, cfg):
    """Top-N journals by risk score, plus a random pick from the remainder so
    that every entry has a chance of selection (unpredictability, SA 240.A44).

    The random seed is new on every run (so the client cannot predict which
    entries will be picked) and is recorded in the workpaper, so the same
    selection can be re-performed by entering that seed in Settings."""
    n_risk = int(cfg.get("risk_sample_size", 25))
    n_rand = int(cfg.get("random_sample_size", 15))
    seed_txt = str(cfg.get("random_seed", "")).strip()
    seed = int(seed_txt) if seed_txt.isdigit() else secrets.randbelow(1_000_000)
    risk = je.sort_values(["risk_score", "amount"], ascending=False).head(n_risk).copy()
    risk["Sampling Method"] = "Risk-based (highest score)"
    rest = je.drop(risk.index)
    rand = rest.sample(min(n_rand, len(rest)), random_state=seed).copy()
    rand["Sampling Method"] = "Random"
    return pd.concat([risk, rand], ignore_index=True), seed


# ---------------------------------------------------------------------------
# EXPLAINABILITY  --  why each High / Critical entry was flagged
# ---------------------------------------------------------------------------
def build_explainability(je, cfg):
    weights = cfg["risk_weights"]
    rows = []
    for _, r in je[je["risk_category"].isin(("Critical", "High"))].iterrows():
        trig = [k for k in RULE_KEYS if r[k]]
        rows.append({
            "Journal Entry": r["je_id"],
            "Date": r["date"].strftime("%d-%m-%Y") if pd.notna(r["date"]) else "",
            "User": r["user"],
            "Doc Type": r["doc_type"],
            "Debit Account(s)": r["dr_accounts"],
            "Credit Account(s)": r["cr_accounts"],
            "Narration": r["narration"],
            "Amount (Dr)": round(float(r["amount"]), 2),
            "Risk Score": int(r["risk_score"]),
            "Risk Category": r["risk_category"],
            "Score Breakdown": "; ".join(f"{RULES[k][0]} (+{weights.get(k, 0)})" for k in trig),
            "Assertions Impacted": "; ".join(dict.fromkeys(RULES[k][1] for k in trig)),
            "SA Reference": "; ".join(dict.fromkeys(RULES[k][3] for k in trig)),
            "Suggested Audit Procedures": "  |  ".join(dict.fromkeys(RULES[k][2] for k in trig)),
        })
    return pd.DataFrame(rows)


def rule_frequency(df, je, cfg):
    weights = cfg["risk_weights"]
    rows = [{"Rule": RULES[k][0],
             "Weight": weights.get(k, 0),
             "Lines Flagged": int(df[k].sum()),
             "Journals Flagged": int(je[k].sum()),
             "Assertion": RULES[k][1],
             "SA Reference": RULES[k][3]} for k in RULE_KEYS]
    return (pd.DataFrame(rows).sort_values("Journals Flagged", ascending=False)
              .reset_index(drop=True))


def by_month(df):
    m = df.dropna(subset=["date"]).assign(Month=lambda x: x["date"].dt.strftime("%Y-%m"))
    return (m.groupby("Month")
             .agg(Lines=("row_id", "size"), Journals=("je_key", "nunique"),
                  **{"Total Debit": ("amount", lambda s: float(s[s > 0].sum()))})
             .reset_index())


# ---------------------------------------------------------------------------
# EXCEL WORKPAPER
# ---------------------------------------------------------------------------
HEADER_FILL = PatternFill("solid", fgColor="1A2744")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
TITLE_FONT  = Font(color="1A2744", bold=True, size=14)
SUB_FONT    = Font(color="1A2744", bold=True, size=11)
PASS_FONT   = Font(color="1B6B3A", bold=True)
WARN_FONT   = Font(color="C0392B", bold=True)
CAT_FILL = {
    "Critical": PatternFill("solid", fgColor="FDECEC"),
    "High":     PatternFill("solid", fgColor="FFF1E6"),
    "Medium":   PatternFill("solid", fgColor="FFF8E6"),
    "Low":      PatternFill("solid", fgColor="EEF7F2"),
}

METHODOLOGY = [
    ("Purpose",
     "This workpaper supports the auditor's response to the presumed risk of "
     "management override of controls under SA 240 (paragraphs 32-33). The full "
     "population of journal entries is risk-scored and high-risk entries are "
     "selected for substantive testing."),
    ("Completeness (GL linked to TB)",
     "When a Trial Balance is provided, the GL extract is linked to it account by "
     "account: the net movement of each account in the GL dump is compared with "
     "the TB movement (closing balance less opening balance). Accounts that agree "
     "show 'Agrees'; any 'DIFFERENCE' means the GL extract may be incomplete and "
     "must be resolved before relying on the testing (SA 500 - completeness and "
     "accuracy of information produced by the entity). Account names are also "
     "taken from the TB into the workpaper."),
    ("Approach",
     "Every GL line is tested against 12 simple, explainable rules grouped into four "
     "questions: WHEN was it posted (Sunday/non-working day, public holiday, month-end, "
     "back-dated), WHO posted it (privileged user, super-user manual entry, manual "
     "journal), HOW MUCH (round sum, large amount) and WHAT does the narration say "
     "(missing, generic, red-flag keyword). Each rule carries a weight; a journal's "
     "score is the sum of the weights of the rules it triggers, banded into Low / "
     "Medium / High / Critical."),
    ("Sampling",
     "Two methods are combined (SA 530): risk-based selection of the highest-scoring "
     "journals, and a random selection from the remaining population to add "
     "unpredictability (SA 240.A44). The random seed changes every run and is "
     "recorded on the Summary sheet, so the selection can be re-performed."),
    ("Explainability",
     "For every High / Critical journal the workpaper shows the rules triggered, the "
     "score breakdown, the assertions impacted and suggested audit procedures. Any "
     "score can be re-performed by adding the listed weights."),
    ("Limitations",
     "A flag is a prompt to investigate, not a conclusion. User lists, manual "
     "document types, holidays and thresholds must be set per client in "
     "je_config.json (or the Settings screen). Without a Trial Balance the tool "
     "cannot confirm that the GL extract is complete; in that case completeness "
     "must be established separately."),
]


def _style_header(ws, ncols, row=1):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = ws.cell(row=row + 1, column=1)


def _put_df(writer, df, sheet):
    if df is None or df.empty:
        df = pd.DataFrame({"(none)": []})
    df.to_excel(writer, sheet_name=sheet, index=False)
    ws = writer.book[sheet]
    _style_header(ws, len(df.columns))
    for i, col in enumerate(df.columns):
        sample = df[col].astype(str).head(200)
        width = max([len(str(col))] + [len(v) for v in sample]) + 2
        ws.column_dimensions[get_column_letter(i + 1)].width = min(max(width, 8), 55)
    return ws


def _colour_category(ws, header_name="Risk Category"):
    hdr = {ws.cell(row=1, column=c).value: c for c in range(1, ws.max_column + 1)}
    col = hdr.get(header_name)
    if not col:
        return
    for r in range(2, min(ws.max_row, 5000) + 1):
        v = ws.cell(row=r, column=col).value
        if v in CAT_FILL:
            ws.cell(row=r, column=col).fill = CAT_FILL[v]


def _journal_view(je, with_method=False):
    cols = (["Sampling Method"] if with_method else []) + [
        "je_id", "date", "company", "user", "doc_type", "n_lines", "amount",
        "dr_accounts", "cr_accounts", "narration", "n_flags", "risk_score",
        "risk_category", "triggered"]
    v = je[cols].copy()
    v["date"] = v["date"].dt.strftime("%d-%m-%Y").fillna("")
    return v.rename(columns={
        "je_id": "Journal Entry", "date": "Date", "company": "Company",
        "user": "User", "doc_type": "Doc Type", "n_lines": "Lines",
        "dr_accounts": "Debit Account(s)", "cr_accounts": "Credit Account(s)",
        "amount": "Amount (Dr)", "narration": "Narration", "n_flags": "# Flags",
        "risk_score": "Risk Score", "risk_category": "Risk Category",
        "triggered": "Triggered Rules"})


def _summary_rows(results):
    je, df, ig = results["je"], results["df"], results["integrity"]
    tot = len(je)
    vc = je["risk_category"].value_counts()
    val = je.groupby("risk_category")["amount"].sum()
    valid = df["date"].dropna()
    rng = f"{valid.min():%d-%m-%Y} to {valid.max():%d-%m-%Y}" if not valid.empty else ""
    rows = [
        ["Journal Entry Testing - Risk Assessment Summary", "", ""],
        [f"Source file: {results['source_name']}", "", ""],
        [f"Prepared by: {results.get('prepared_by') or 'command line'}   ·   "
         f"Run on {datetime.now():%d-%m-%Y %H:%M}", "", ""],
        ["", "", ""],
        ["Line items analysed", len(df), ""],
        ["Journal entries", tot, ""],
        ["Distinct accounts", df["account"].nunique(), ""],
        ["Distinct users", int(df["user"].replace("", np.nan).nunique()), ""],
        ["Posting date range", rng, ""],
        ["", "", ""],
        ["DATA QUALITY", "", ""],
        ["Data-quality issues found", results["n_issues"],
         "DATA HAS ERRORS - see Data Quality sheet" if results["n_errors"]
         else ("review - see Data Quality sheet" if results["n_issues"] else "CLEAN")],
        ["", "", ""],
        ["BALANCE CHECK (Debit vs Credit)", "", ""],
        ["Total Debit", round(ig["total_debit"], 2), ""],
        ["Total Credit", round(ig["total_credit"], 2), ""],
        ["Difference", round(ig["total_debit"] - ig["total_credit"], 2),
         "BALANCED" if ig["balanced"] else "DOES NOT TIE OUT"],
        ["", "", ""],
        ["GL LINKED TO TRIAL BALANCE", "", ""],
    ]
    tbs = results.get("tb_summary")
    if tbs:
        rows += [
            [f"Trial Balance file: {results['tb_name']}", "", ""],
            ["Accounts in TB", tbs["accounts_tb"], ""],
            ["Accounts agreeing with GL", tbs["agreed"], ""],
            ["Accounts with a DIFFERENCE", tbs["differences"],
             "GL MAY BE INCOMPLETE - see TB Reconciliation" if tbs["differences"]
             else "COMPLETE"],
            ["Accounts in GL but not in TB", tbs["gl_only"],
             "review" if tbs["gl_only"] else ""],
        ]
        if not tbs["has_opening"]:
            rows.append(["Note: TB has no opening-balance column", "",
                         "balance-sheet differences may be opening balances"])
    else:
        rows.append(["Trial Balance not provided", "",
                     "completeness of GL not confirmed"])
    rows += [
        ["", "", ""],
        ["RISK CATEGORY", "Journals", "Total Debit"],
    ]
    for c in ("Critical", "High", "Medium", "Low"):
        rows.append([f"  {c}", int(vc.get(c, 0)), round(float(val.get(c, 0)), 2)])
    hi = int(vc.get("Critical", 0) + vc.get("High", 0))
    rows += [
        ["", "", ""],
        ["High + Critical journals (test population)", hi,
         f"{100 * hi / max(tot, 1):.1f}% of all journals"],
        ["Samples selected", len(results["samples"]),
         f"random seed {results['seed']} (enter in Settings to re-perform)"],
        ["", "", ""],
        ["TOP RISK RULES (by journals flagged)", "", ""],
    ]
    for _, r in results["rule_freq"].head(6).iterrows():
        rows.append([f"  {r['Rule']}", int(r["Journals Flagged"]), f"weight {r['Weight']}"])
    return rows


def write_report(results, path):
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        # 1. Summary
        pd.DataFrame().to_excel(writer, sheet_name="Summary", index=False)
        ws = writer.book["Summary"]
        for r, row in enumerate(_summary_rows(results), start=1):
            for c, val in enumerate(row, start=1):
                cell = ws.cell(row=r, column=c, value=val)
                if r == 1:
                    cell.font = TITLE_FONT
                elif r == 2:
                    cell.font = Font(color="5A6A8A", italic=True)
                elif row[0] == "RISK CATEGORY":
                    cell.fill, cell.font = HEADER_FILL, HEADER_FONT
                elif row[0] in ("BALANCE CHECK (Debit vs Credit)", "DATA QUALITY",
                                "GL LINKED TO TRIAL BALANCE",
                                "TOP RISK RULES (by journals flagged)"):
                    cell.font = SUB_FONT
                elif val in ("BALANCED", "COMPLETE", "CLEAN"):
                    cell.font = PASS_FONT
                elif val == "DOES NOT TIE OUT" or str(val).startswith(("GL MAY BE", "DATA HAS")):
                    cell.font = WARN_FONT
        ws.column_dimensions["A"].width = 46
        ws.column_dimensions["B"].width = 20
        ws.column_dimensions["C"].width = 26

        # 2. Methodology
        pd.DataFrame().to_excel(writer, sheet_name="Methodology", index=False)
        wm = writer.book["Methodology"]
        wm.cell(row=1, column=1, value="Testing Methodology").font = TITLE_FONT
        rr = 3
        for head, body in METHODOLOGY:
            wm.cell(row=rr, column=1, value=head).font = SUB_FONT
            wm.cell(row=rr + 1, column=1, value=body).alignment = \
                Alignment(wrap_text=True, vertical="top")
            rr += 3
        wm.column_dimensions["A"].width = 110

        # 3-9. Tables
        wq = _put_df(writer, pd.DataFrame(results["data_quality"]["checks"],
                                          columns=["Check", "Value", "Status"]), "Data Quality")
        for r in range(2, wq.max_row + 1):
            st = wq.cell(row=r, column=3)
            if st.value == "ERROR":
                for c in range(1, 4):
                    wq.cell(row=r, column=c).fill = CAT_FILL["Critical"]
                st.font = WARN_FONT
            elif st.value == "review":
                st.font, st.fill = Font(color="B9770E", bold=True), CAT_FILL["Medium"]
            elif st.value == "ok":
                st.font = PASS_FONT
        if results.get("tb_recon") is not None:
            wt = _put_df(writer, results["tb_recon"], "TB Reconciliation")
            status_col = wt.max_column
            for r in range(2, wt.max_row + 1):
                c = wt.cell(row=r, column=status_col)
                if c.value == "DIFFERENCE":
                    c.font, c.fill = WARN_FONT, CAT_FILL["Critical"]
                elif str(c.value).startswith("Agrees"):
                    c.font = PASS_FONT
        _put_df(writer, _journal_view(results["je"]), "Risk Register")
        _put_df(writer, results["explainability"], "Explainability")
        _put_df(writer, _journal_view(results["samples"], with_method=True), "Samples")
        _put_df(writer, results["rule_freq"], "Rule Frequency")
        _put_df(writer, results["by_month"], "Population by Month")

        for sheet in ("Risk Register", "Explainability", "Samples"):
            _colour_category(writer.book[sheet])
        _neutralise_formulas(writer.book)
    return path


def _neutralise_formulas(wb):
    """SECURITY: text from the GL (e.g. a narration such as '=HYPERLINK(...)')
    would otherwise be saved as a live Excel formula.  The tool never writes
    formulas itself, so every formula cell is turned back into plain text."""
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.data_type == "f":
                    cell.data_type = "s"
                    cell.quotePrefix = True


# ---------------------------------------------------------------------------
# END-TO-END
# ---------------------------------------------------------------------------
def analyze_file(gl_path, out_dir=None, cfg=None, mapping=None, progress=None,
                 tb_path=None, prepared_by=""):
    """Full pipeline.  Returns (results dict, path to the Excel workpaper)."""
    def _say(msg):
        if progress:
            progress(msg)

    cfg = cfg or load_config()
    _say("Reading the GL extract...")
    raw = load_raw(gl_path)
    mapping = mapping or build_mapping(raw)
    validate_mapping(mapping)

    _say("Mapping columns & checking data quality...")
    df = apply_mapping(raw, mapping)
    dq = data_quality(df)

    tb_recon, tb_summary = None, None
    if tb_path:
        _say("Linking the GL to the Trial Balance...")
        tb, _ = load_tb(tb_path)
        df = add_tb_names(df, tb)
        tb_recon, tb_summary = reconcile_tb(df, tb, cfg)
        dq["checks"] += tb_checks(tb, tb_summary, cfg)

    _say("Running the 12 risk rules...")
    df = run_rules(df, cfg)

    _say("Scoring journal entries...")
    je = score_journals(df, cfg)

    _say("Selecting samples...")
    samples, seed = build_samples(je, cfg)
    results = {
        "df": df, "je": je, "cfg": cfg, "mapping": mapping,
        "source_name": Path(gl_path).name,
        "prepared_by": prepared_by,
        "tb_name": Path(tb_path).name if tb_path else "",
        "tb_recon": tb_recon, "tb_summary": tb_summary,
        "data_quality": dq,
        "n_issues": count_issues(dq["checks"]),
        "n_errors": sum(1 for c in dq["checks"] if c[2] == "ERROR"),
        "integrity": {"total_debit": dq["total_debit"],
                      "total_credit": dq["total_credit"],
                      "balanced": abs(dq["total_debit"] - dq["total_credit"]) <= 1.0},
        "rule_freq": rule_frequency(df, je, cfg),
        "by_month": by_month(df),
        "samples": samples, "seed": seed,
        "explainability": build_explainability(je, cfg),
    }

    out_dir = Path(out_dir) if out_dir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    xlsx = out_dir / f"JE_Testing_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    _say("Writing Excel workpaper...")
    write_report(results, xlsx)
    return results, xlsx


# ---------------------------------------------------------------------------
# COMMAND LINE
# ---------------------------------------------------------------------------
def _is_tb_name(path):
    return re.search(r"(^|[^a-z])(tb|trial)", Path(path).stem.lower()) is not None


def _data_files(folder):
    files = []
    for ext in (".xlsx", ".xls", ".csv"):
        files += [p for p in sorted(folder.glob(f"*{ext}")) if not p.name.startswith("~$")]
    return files


def find_inputs():
    """(GL, TB) from the input\\ folder (command line only).  A file whose name
    contains 'TB' or 'Trial' is treated as the Trial Balance."""
    if not INPUT_DIR.exists():
        return None, None
    files = _data_files(INPUT_DIR)
    gls = [p for p in files if not _is_tb_name(p)]
    tbs = [p for p in files if _is_tb_name(p)]
    return (gls[0] if gls else None), (tbs[0] if tbs else None)


def run():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        gl = Path(args[0])
        tb = Path(args[1]) if len(args) > 1 else None
    else:
        gl, tb = find_inputs()
    if gl is None or not gl.exists():
        print("  No GL file found.")
        print(f"  Put a GL extract (Excel/CSV) in: {INPUT_DIR}")
        return
    print(f"  Analysing: {gl.name}" + (f"   linked to TB: {tb.name}" if tb else ""))
    results, xlsx = analyze_file(gl, OUTPUT_DIR, load_config(),
                                 progress=lambda m: print("   -", m), tb_path=tb)
    je = results["je"]
    vc = je["risk_category"].value_counts()
    print("\n  ---------------- RESULT ----------------")
    print(f"   Line items     : {len(results['df']):,}")
    print(f"   Journal entries: {len(je):,}")
    for c in ("Critical", "High", "Medium", "Low"):
        print(f"     {c:9}: {int(vc.get(c, 0)):,}")
    print(f"   Balanced (Dr = Cr): {'Yes' if results['integrity']['balanced'] else 'NO'}")
    tbs = results["tb_summary"]
    if tbs:
        print(f"   GL vs TB       : {tbs['agreed']} of {tbs['accounts_tb']} accounts agree, "
              f"{tbs['differences']} with a DIFFERENCE")
    print(f"   Workpaper: {xlsx}")
    print("  ----------------------------------------\n")


if __name__ == "__main__":
    run()
