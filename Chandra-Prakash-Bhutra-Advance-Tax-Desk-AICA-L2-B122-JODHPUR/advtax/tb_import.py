"""Read a trial balance exported from any accounting software.

Works with Tally, Busy, Zoho Books, QuickBooks, Marg or the bundled template:
the user (or the auto-detector) says which column holds the ledger name, the
group and the amounts, and every ledger is then tagged Income / Expense /
Opening Stock / Ignore (balance-sheet items).
"""
from __future__ import annotations

import io
import re

import pandas as pd

TYPES = ["Income", "Expense", "Opening Stock", "Ignore"]

_HEADER_WORDS = ("particular", "ledger", "account", "name", "debit", "credit", "balance", "amount",
                 "group", "type", "dr", "cr", "closing", "head")

_BS_GROUPS = ("capital", "loan", "liabilit", "asset", "bank", "cash", "debtor", "creditor", "duties",
              "tax", "provision", "investment", "deposit", "suspense", "reserve", "branch", "equity",
              "receivable", "payable", "advance", "drawing")
_STOCK_GROUPS = ("stock", "inventory")
_EXP_GROUPS = ("purchase", "expense", "cost of goods", "cogs", "direct exp", "indirect exp", "cost of sales")
_INC_GROUPS = ("sales", "income", "revenue", "turnover")

_TAX_NAMES = ("income tax", "advance tax", "tds", "tcs", "gst", "cgst", "sgst", "igst", "payable", "receivable")
_STRONG_INC = ("sales", "received", "income", "revenue", "receipts")
_STRONG_EXP = ("expense", "exp.", "charges", "purchase", "salary", "salaries", "wages", "depreciation", "freight")
_IGNORE_NAMES = ("income tax", "advance tax", "tds", "tcs", "gst", "cgst", "sgst", "igst", "capital",
                 "drawing", "loan", "bank", "cash", "debtor", "creditor", "deposit", "furniture",
                 "machinery", "computer", "vehicle", "building", "land", "investment", "payable",
                 "receivable", "provision", "suspense")
_EXP_NAMES = ("purchase", "expense", "exp.", "charges", "salary", "salaries", "wages", "rent paid",
              "interest paid", "interest on loan", "freight", "carriage", "repair", "depreciation",
              "commission paid", "fees", "electricity", "power", "fuel", "insurance", "printing",
              "stationery", "telephone", "internet", "travelling", "conveyance", "audit", "discount allowed",
              "bonus", "advertisement", "packing", "labour", "donation", "bad debt", "rent", "rates")
_INC_NAMES = ("sales", "sale of", "income", "interest received", "interest on fd", "discount received",
              "commission received", "service receipts", "job work receipts", "revenue", "dividend")
_ONE_OFF_NAMES = ("profit on sale", "loss on sale", "insurance claim", "prior period", "bad debt",
                  "written off", "written back", "subsidy", "exceptional", "sale of asset", "sale of fixed")


def read_raw(data: bytes, filename: str, sheet: str | int = 0) -> pd.DataFrame:
    """Load the file with no header assumption."""
    name = filename.lower()
    if name.endswith(".csv") or name.endswith(".txt"):
        for enc in ("utf-8-sig", "latin-1"):
            try:
                return pd.read_csv(io.BytesIO(data), header=None, dtype=str, encoding=enc,
                                   sep=None, engine="python")
            except UnicodeDecodeError:
                continue
    return pd.read_excel(io.BytesIO(data), header=None, dtype=str, sheet_name=sheet)


def sheet_names(data: bytes, filename: str) -> list:
    if filename.lower().endswith((".csv", ".txt")):
        return []
    return pd.ExcelFile(io.BytesIO(data)).sheet_names


def detect_header_row(raw: pd.DataFrame, scan: int = 40) -> int:
    best, best_score = 0, 0
    for i in range(min(scan, len(raw))):
        cells = [str(c).strip().lower() for c in raw.iloc[i].tolist() if pd.notna(c)]
        score = sum(1 for c in cells if any(w in c for w in _HEADER_WORDS) and len(c) < 40)
        if score > best_score and len(cells) >= 2:
            best, best_score = i, score
    return best


def _is_sub_header(row: list) -> bool:
    cells = [str(c).strip().lower() for c in row if pd.notna(c) and str(c).strip()]
    if not cells or any(re.search(r"\d", c) for c in cells):
        return False
    return any(c in ("debit", "credit", "dr", "cr", "dr.", "cr.") for c in cells)


def build_table(raw: pd.DataFrame, header_row: int) -> pd.DataFrame:
    """Use header_row as column titles. A second title row (Tally prints
    'Closing Balance' above 'Debit | Credit') is merged into the first."""
    top = [str(c).strip() if pd.notna(c) and str(c).strip() else "" for c in raw.iloc[header_row].tolist()]
    first_data = header_row + 1
    if first_data < len(raw) and _is_sub_header(raw.iloc[first_data].tolist()):
        sub = [str(c).strip() if pd.notna(c) and str(c).strip() else "" for c in raw.iloc[first_data].tolist()]
        parent, merged = "", []
        for t, u in zip(top, sub):
            parent = t or parent
            merged.append(f"{parent} {u}".strip() if u else t)
        top, first_data = merged, first_data + 1
    header = [h if h else f"Column {i + 1}" for i, h in enumerate(top)]
    seen, cols = {}, []
    for h in header:
        seen[h] = seen.get(h, 0) + 1
        cols.append(h if seen[h] == 1 else f"{h} ({seen[h]})")
    df = raw.iloc[first_data:].copy()
    df.columns = cols
    df = df.dropna(how="all").reset_index(drop=True)
    return df


def guess_columns(df: pd.DataFrame) -> dict:
    """Best guess for the column mapping; every value may be None."""
    low = {c: c.lower() for c in df.columns}

    def find(*words, exclude=()):
        for c, l in low.items():
            if any(w in l for w in words) and not any(x in l for x in exclude):
                return c
        return None

    ledger = find("particular", "ledger", "account name", "account", "name", "head", exclude=("type", "group", "code"))
    group = find("group", "account type", "type", "parent", "category", exclude=("dr/cr", "dr / cr"))
    debit = find("debit", exclude=("credit",)) or find("dr", exclude=("cr", "dr/cr"))
    credit = find("credit", exclude=("debit",)) or find(" cr", exclude=("dr",))
    balance = find("closing", "balance", "amount", exclude=("debit", "credit", "opening"))
    drcr = find("dr/cr", "dr / cr", "nature")
    if group == ledger:
        group = None
    return {"ledger": ledger or df.columns[0], "group": group, "debit": debit, "credit": credit,
            "balance": balance if not (debit and credit) else None, "drcr": drcr}


def parse_amount(value) -> float:
    """'1,23,456.00 Dr' -> 123456.0 ; '(500)' -> -500 ; 'Cr' suffix gives a negative number."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    s = str(value).strip()
    if not s or s in ("-", "--", "nan", "None"):
        return 0.0
    negative = s.startswith("(") and s.endswith(")")
    lower = s.lower()
    if re.search(r"\bcr\b\.?$", lower):
        negative = not negative
    s = re.sub(r"[^\d.\-]", "", s)
    if s in ("", "-", "."):
        return 0.0
    try:
        num = float(s)
    except ValueError:
        return 0.0
    return -abs(num) if negative else num


def normalise(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Return ledger, group, net (debit positive, credit negative)."""
    out = pd.DataFrame()
    out["ledger"] = df[mapping["ledger"]].astype(str).str.strip()
    out["group"] = df[mapping["group"]].astype(str).str.strip() if mapping.get("group") else ""
    if mapping.get("debit") and mapping.get("credit"):
        out["net"] = df[mapping["debit"]].map(parse_amount).abs() - df[mapping["credit"]].map(parse_amount).abs()
    elif mapping.get("balance"):
        net = df[mapping["balance"]].map(parse_amount)
        if mapping.get("drcr"):
            side = df[mapping["drcr"]].astype(str).str.strip().str.lower()
            net = net.abs().where(~side.str.startswith("c"), -net.abs())
        out["net"] = net
    else:
        raise ValueError("Map either Debit and Credit columns, or a single Balance column.")
    out["group"] = out["group"].replace({"nan": "", "None": ""})
    bad = out["ledger"].str.lower().isin(["", "nan", "none", "total", "grand total", "difference in opening balances"])
    out = out[~bad & (out["net"].abs() > 0.004)].reset_index(drop=True)
    return out


def classify_one(ledger: str, group: str, net: float) -> tuple[str, bool]:
    """Return (type, needs_review)."""
    g, n = (group or "").lower(), (ledger or "").lower()
    if g:
        if any(k in g for k in _STOCK_GROUPS):
            return "Opening Stock", False
        if any(k in g for k in _EXP_GROUPS):
            return "Expense", False
        if any(k in g for k in _INC_GROUPS):
            return "Income", False
        if any(k in g for k in _BS_GROUPS):
            return "Ignore", False
    if "opening stock" in n:
        return "Opening Stock", False
    if any(k in n for k in _TAX_NAMES):
        return "Ignore", not g
    # Clear profit-and-loss words win over balance-sheet words ("Bank Charges", "Vehicle Expenses")
    if any(k in n for k in _STRONG_INC) and net <= 0:
        return "Income", not g
    if any(k in n for k in _STRONG_EXP) and net >= 0:
        return "Expense", not g
    if any(k in n for k in _IGNORE_NAMES):
        return "Ignore", not g
    if any(k in n for k in _EXP_NAMES) and net >= 0:
        return "Expense", not g
    if any(k in n for k in _INC_NAMES) and net <= 0:
        return "Income", not g
    return "Ignore", True


def classify(table: pd.DataFrame) -> pd.DataFrame:
    out = table.copy()
    res = [classify_one(l, g, v) for l, g, v in zip(out["ledger"], out["group"], out["net"])]
    out["type"] = [r[0] for r in res]
    out["review"] = [r[1] for r in res]
    out["one_off"] = [any(k in str(l).lower() for k in _ONE_OFF_NAMES) and t in ("Income", "Expense")
                      for l, t in zip(out["ledger"], out["type"])]
    return out


def summarise(table: pd.DataFrame) -> dict:
    """Totals for the projection. Income is credit-natured, expense debit-natured."""
    t = table
    inc = t[t["type"] == "Income"]
    exp = t[t["type"] == "Expense"]
    stock = t[t["type"] == "Opening Stock"]
    return {
        "recurring_income": float(-inc[~inc["one_off"]]["net"].sum()),
        "one_off_income": float(-inc[inc["one_off"]]["net"].sum()),
        "recurring_expense": float(exp[~exp["one_off"]]["net"].sum()),
        "one_off_expense": float(exp[exp["one_off"]]["net"].sum()),
        "opening_stock": float(stock["net"].sum()),
        "ledgers": int(len(t)),
        "needs_review": int(t["review"].sum()) if "review" in t else 0,
        "difference": float(t["net"].sum()),
    }
