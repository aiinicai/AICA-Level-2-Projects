"""
============================================================================
 JOURNAL ENTRY TESTING  (JE Testing)  --  Simplified Audit Analytics Tool
----------------------------------------------------------------------------
 Risk-based journal-entry testing for the risk of management override of
 controls (ICAI SA 240). Reads SAP and other ERP GL extracts.

 PIPELINE
   GL extract (Excel / CSV)  ->  column mapping  ->  data-quality checks
   ->  12 simple risk rules  ->  weighted risk score per journal entry
   ->  Low / Medium / High / Critical  ->  sample selection
   ->  audit-ready Excel workpaper

 This module is the ENGINE + command line.  je_testing_app.py is the
 desktop window.

 USAGE
     python je_testing.py --make-samples      # write a demo GL with planted red flags
     python je_testing.py "GL dump.xlsx"      # analyse a file
     python je_testing.py                     # analyse the first file in input\\

 Thresholds, risk weights, user lists, keywords and holidays live in
 je_config.json (auto-created next to the program on first run).
============================================================================
"""

import sys
import re
import json
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
OUTPUT_DIR  = BASE_DIR / "output"
SAMPLE_DIR  = BASE_DIR / "sample_data"
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
    "period":       ["yearmonth", "period", "fiscalperiod", "postingperiod"],
    "amount":       ["amountinlocalcurrency", "amountincompanycodecurrency",
                     "localamount", "amountlc", "dmbtr", "amount", "amountinr"],
    "narration":    ["text", "description", "narration", "linetext",
                     "itemtext", "sgtxt", "remarks", "headertext"],
}

# Fields we cannot run without.
ESSENTIAL_FIELDS = ["je_id", "account", "amount"]

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
    "privileged_users":   ["ADMIN01"],     # IT / admin IDs with elevated access
    "super_users":        ["CFO01"],       # senior users who can post anywhere

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
    "random_sample_size": 15               # random picks from the rest
}


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
        except Exception:
            pass
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
def load_raw(path):
    """Read a GL extract (Excel / CSV).  Finds the header row even if the file
    has title rows on top, and in a multi-sheet workbook picks the sheet whose
    headings look most like a GL dump."""
    path = Path(path)
    if path.suffix.lower() == ".csv":
        raw = pd.read_csv(path, header=None, dtype=str, keep_default_na=False)
        if raw.empty:
            raise ValueError("The file appears to be empty.")
        return _promote_header(raw)

    xl = pd.ExcelFile(path)
    best_raw, best_score = None, -1
    for sheet in xl.sheet_names:
        try:
            candidate = xl.parse(sheet, header=None)
        except Exception:
            continue
        if candidate.empty:
            continue
        score = max((_header_score(candidate.iloc[i])
                     for i in range(min(20, len(candidate)))), default=0)
        if score > best_score:
            best_score, best_raw = score, candidate
    if best_raw is None or best_raw.empty:
        raise ValueError("The file appears to be empty.")
    return _promote_header(best_raw)


def _header_score(row):
    norms = {_norm(v) for v in row.tolist() if pd.notna(v)}
    return sum(1 for names in COLUMN_ALIASES.values()
               if any(_norm(a) in norms for a in names))


def _promote_header(raw):
    best_row = max(range(min(20, len(raw))), key=lambda i: _header_score(raw.iloc[i]))
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


def build_mapping(df):
    """Return {canonical_field: actual_column} auto-detected from headers."""
    lookup = {}
    for actual in df.columns:
        lookup.setdefault(_norm(actual), actual)
    mapping = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if _norm(alias) in lookup:
                mapping[field] = lookup[_norm(alias)]
                break
    return mapping


def validate_mapping(mapping):
    missing = [f for f in ESSENTIAL_FIELDS if f not in mapping]
    if missing:
        raise ValueError(
            "Could not find these essential columns: " + ", ".join(missing)
            + ".\n  Rename the heading in your file, or add it to COLUMN_ALIASES.")


def apply_mapping(df, mapping):
    """Build the clean working table from the raw extract + mapping."""
    out = pd.DataFrame(index=df.index)
    for field, actual in mapping.items():
        if actual in df.columns:
            out[field] = df[actual]

    out["amount"] = to_number(out["amount"])
    for d in ("posting_date", "entry_date", "doc_date"):
        if d in out:
            out[d] = _parse_dates(out[d])
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
              "period", "narration"):
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


def data_quality(df):
    """Completeness checks shown to the auditor before relying on the data."""
    checks = []
    checks.append(["Total line items", len(df), ""])
    checks.append(["Distinct journal entries", df["je_key"].nunique(), ""])
    checks.append(["Distinct accounts", df["account"].nunique(), ""])
    checks.append(["Distinct users", df["user"].replace("", np.nan).nunique(), ""])

    for label, n in (("Lines with zero/blank amount", int((df["abs_amount"] == 0).sum())),
                     ("Lines with no posting date", int(df["date"].isna().sum())),
                     ("Lines with no user", int((df["user"] == "").sum()))):
        checks.append([label, n, "review" if n else "ok"])

    unbal = int((df.groupby("je_key")["amount"].sum().abs() > 1.0).sum())
    checks.append(["Journal entries that do not net to 0", unbal,
                   "review" if unbal else "ok"])

    total_dr = float(df.loc[df["amount"] > 0, "amount"].sum())
    total_cr = float(-df.loc[df["amount"] < 0, "amount"].sum())
    checks.append(["Total debits", round(total_dr, 2), ""])
    checks.append(["Total credits", round(total_cr, 2), ""])
    checks.append(["Debit - Credit difference", round(total_dr - total_cr, 2),
                   "ok" if abs(total_dr - total_cr) <= 1 else "review"])

    valid = df["date"].dropna()
    rng = f"{valid.min():%d-%m-%Y} to {valid.max():%d-%m-%Y}" if not valid.empty else ""
    checks.append(["Posting date range", rng, ""])
    return {"checks": checks, "total_debit": total_dr, "total_credit": total_cr}


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
    that every entry has a chance of selection (unpredictability, SA 240.A44)."""
    n_risk = int(cfg.get("risk_sample_size", 25))
    n_rand = int(cfg.get("random_sample_size", 15))
    risk = je.sort_values(["risk_score", "amount"], ascending=False).head(n_risk).copy()
    risk["Sampling Method"] = "Risk-based (highest score)"
    rest = je.drop(risk.index)
    rand = rest.sample(min(n_rand, len(rest)), random_state=42).copy()
    rand["Sampling Method"] = "Random"
    return pd.concat([risk, rand], ignore_index=True)


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
     "unpredictability (SA 240.A44)."),
    ("Explainability",
     "For every High / Critical journal the workpaper shows the rules triggered, the "
     "score breakdown, the assertions impacted and suggested audit procedures. Any "
     "score can be re-performed by adding the listed weights."),
    ("Limitations",
     "A flag is a prompt to investigate, not a conclusion. User lists, manual "
     "document types, holidays and thresholds must be set per client in "
     "je_config.json (or the Settings screen). The tool relies on the completeness "
     "of the GL extract, which should be agreed to the trial balance separately."),
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
        "narration", "n_flags", "risk_score", "risk_category", "triggered"]
    v = je[cols].copy()
    v["date"] = v["date"].dt.strftime("%d-%m-%Y").fillna("")
    return v.rename(columns={
        "je_id": "Journal Entry", "date": "Date", "company": "Company",
        "user": "User", "doc_type": "Doc Type", "n_lines": "Lines",
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
        ["", "", ""],
        ["Line items analysed", len(df), ""],
        ["Journal entries", tot, ""],
        ["Distinct accounts", df["account"].nunique(), ""],
        ["Distinct users", int(df["user"].replace("", np.nan).nunique()), ""],
        ["Posting date range", rng, ""],
        ["", "", ""],
        ["BALANCE CHECK (Debit vs Credit)", "", ""],
        ["Total Debit", round(ig["total_debit"], 2), ""],
        ["Total Credit", round(ig["total_credit"], 2), ""],
        ["Difference", round(ig["total_debit"] - ig["total_credit"], 2),
         "BALANCED" if ig["balanced"] else "DOES NOT TIE OUT"],
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
                elif row[0] in ("BALANCE CHECK (Debit vs Credit)",
                                "TOP RISK RULES (by journals flagged)"):
                    cell.font = SUB_FONT
                elif val == "BALANCED":
                    cell.font = PASS_FONT
                elif val == "DOES NOT TIE OUT":
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

        # 3-8. Tables
        _put_df(writer, pd.DataFrame(results["data_quality"]["checks"],
                                     columns=["Check", "Value", "Status"]), "Data Quality")
        _put_df(writer, _journal_view(results["je"]), "Risk Register")
        _put_df(writer, results["explainability"], "Explainability")
        _put_df(writer, _journal_view(results["samples"], with_method=True), "Samples")
        _put_df(writer, results["rule_freq"], "Rule Frequency")
        _put_df(writer, results["by_month"], "Population by Month")

        for sheet in ("Risk Register", "Explainability", "Samples"):
            _colour_category(writer.book[sheet])
    return path


# ---------------------------------------------------------------------------
# END-TO-END
# ---------------------------------------------------------------------------
def analyze_file(gl_path, out_dir=None, cfg=None, mapping=None, progress=None):
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

    _say("Running the 12 risk rules...")
    df = run_rules(df, cfg)

    _say("Scoring journal entries...")
    je = score_journals(df, cfg)

    _say("Selecting samples...")
    results = {
        "df": df, "je": je, "cfg": cfg, "mapping": mapping,
        "source_name": Path(gl_path).name,
        "data_quality": dq,
        "integrity": {"total_debit": dq["total_debit"],
                      "total_credit": dq["total_credit"],
                      "balanced": abs(dq["total_debit"] - dq["total_credit"]) <= 1.0},
        "rule_freq": rule_frequency(df, je, cfg),
        "by_month": by_month(df),
        "samples": build_samples(je, cfg),
        "explainability": build_explainability(je, cfg),
    }

    out_dir = Path(out_dir) if out_dir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    xlsx = out_dir / f"JE_Testing_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    _say("Writing Excel workpaper...")
    write_report(results, xlsx)
    return results, xlsx


# ---------------------------------------------------------------------------
# DEMO GL  --  synthetic SAP-style data with one planted case per rule
# ---------------------------------------------------------------------------
def make_samples():
    """Write sample_data/sample_GL.xlsx: ~300 ordinary journals plus planted
    red flags, so every rule can be demonstrated.  All data is fictitious."""
    import random
    random.seed(11)
    users = [f"3000{n:04d}" for n in range(1, 7)]
    rows = []
    docno = 4900000000

    def doc(day, dtype, user, dr_acc, cr_acc, amt, text, entry=None):
        nonlocal docno
        docno += 1
        entry = entry or day
        for acc, a in ((dr_acc, amt), (cr_acc, -amt)):
            rows.append(["1000", acc, str(docno), user, dtype, entry, day, day,
                         f"{day.year}/{day.month:02d}", a, "INR", text])

    # ordinary business, Monday to Saturday
    for _ in range(300):
        day = datetime(2025, 4, 1) + timedelta(days=random.randint(0, 360))
        if day.weekday() == 6:
            day -= timedelta(days=1)
        amt = round(random.uniform(5000, 900000), 2)
        doc(day, random.choice(["KR", "KZ", "DR", "DZ"]), random.choice(users),
            "50020000", "11010000", amt,
            random.choice(["Vendor invoice INV-%d" % random.randint(1000, 9999),
                           "Payment to supplier", "Freight charges Apr-Mar",
                           "Customer receipt"]))

    # ---- planted red flags (one or more rules each) ----
    # 1. CFO manual top-side to revenue on 31 March, entered 10 days later,
    #    round crore amount, red-flag narration  -> Critical
    doc(datetime(2026, 3, 31), "SA", "CFO01", "13010000", "40010000",
        10000000.0, "Year end topside adjustment as instructed",
        entry=datetime(2026, 4, 10))
    # 2. Sunday manual entry by IT admin, generic narration
    doc(datetime(2025, 7, 6), "SA", "ADMIN01", "13010000", "11010000",
        2500000.0, "adjustment")
    # 3. Public holiday (Independence Day) posting with no narration
    doc(datetime(2025, 8, 15), "SA", "30000002", "60030000", "11010000",
        750000.0, "")
    # 4. Fraud keyword
    doc(datetime(2025, 11, 12), "SA", "30000003", "60030000", "11010000",
        48500.0, "balancing figure plug")
    # 5. Large amount at month-end
    doc(datetime(2025, 9, 30), "KR", "30000004", "50020000", "21010000",
        25750000.0, "Capital goods invoice INV-8812")
    # 6. Back-dated vendor invoice
    doc(datetime(2025, 12, 5), "KR", "30000005", "50020000", "21010000",
        310000.0, "Vendor invoice INV-9901", entry=datetime(2026, 1, 20))

    df = pd.DataFrame(rows, columns=[
        "Company Code", "G/L Account", "Document Number", "User Name",
        "Document Type", "Entry Date", "Document Date", "Posting Date",
        "Year/Month", "Amount in Local Currency", "Local Currency", "Text"])
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    out = SAMPLE_DIR / "sample_GL.xlsx"
    df.to_excel(out, index=False)
    print(f"  Sample GL written to: {out}")
    return out


# ---------------------------------------------------------------------------
# COMMAND LINE
# ---------------------------------------------------------------------------
def find_gl():
    """First Excel/CSV in input\\, else the bundled sample."""
    for folder in (INPUT_DIR, SAMPLE_DIR):
        for ext in (".xlsx", ".xls", ".csv"):
            for cand in sorted(folder.glob(f"*{ext}")):
                if not cand.name.startswith("~$"):
                    return cand
    return None


def run():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    gl = Path(args[0]) if args else find_gl()
    if gl is None or not gl.exists():
        print("  No GL file found.")
        print(f"  Put a GL extract (Excel/CSV) in: {INPUT_DIR}")
        print("  Or create demo data:  python je_testing.py --make-samples")
        return
    print(f"  Analysing: {gl.name}")
    results, xlsx = analyze_file(gl, OUTPUT_DIR, load_config(),
                                 progress=lambda m: print("   -", m))
    je = results["je"]
    vc = je["risk_category"].value_counts()
    print("\n  ---------------- RESULT ----------------")
    print(f"   Line items     : {len(results['df']):,}")
    print(f"   Journal entries: {len(je):,}")
    for c in ("Critical", "High", "Medium", "Low"):
        print(f"     {c:9}: {int(vc.get(c, 0)):,}")
    print(f"   Balanced (Dr = Cr): {'Yes' if results['integrity']['balanced'] else 'NO'}")
    print(f"   Workpaper: {xlsx}")
    print("  ----------------------------------------\n")


if __name__ == "__main__":
    if "--make-samples" in sys.argv:
        make_samples()
    else:
        run()
