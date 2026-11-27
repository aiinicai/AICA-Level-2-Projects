"""Capital gains import from any broker, mutual fund platform or app statement.

Reads a transaction-wise capital gains / tax P&L sheet (Excel or CSV), lets the
user match the columns, works out the holding period and sorts each sale into
the four heads the tax engine uses:

    stcg_equity   short-term, listed shares / equity funds        (special rate)
    ltcg_equity   long-term, listed shares / equity funds         (special rate above the exemption)
    ltcg_other    long-term, other assets                         (special rate)
    stcg_other    short-term, other assets and debt funds         (slab rate)

Not handled, to be adjusted by hand: cost as on 31 Jan 2018 for old equity
holdings, indexation choice on land or building bought before 23 Jul 2024,
exemptions (reinvestment), and brought-forward losses.
"""
from __future__ import annotations

import pandas as pd

from advtax.tb_import import parse_amount, read_raw, sheet_names, build_table  # noqa: F401 - re-exported for the app

EQUITY = "Listed shares / equity funds"
OTHER = "Other assets"
DEBT = "Debt funds (always short-term)"
IGNORE = "Not capital gains"
CLASSES = [EQUITY, OTHER, DEBT, IGNORE]
TERMS = ["Short", "Long"]
BUCKETS = {"stcg_equity": "Short-term: listed shares / equity funds", "ltcg_equity": "Long-term: listed shares / equity funds",
           "ltcg_other": "Long-term: other assets", "stcg_other": "Short-term: other assets (slab rate)"}
LONG_TERM_MONTHS = {EQUITY: 12, OTHER: 24}

FIELDS = {
    "asset": ("Asset / scrip name", True), "type": ("Asset type", False), "term": ("Short / long term", False),
    "buy_date": ("Buy date", False), "sell_date": ("Sell date", False), "buy_value": ("Buy value (cost)", False),
    "sell_value": ("Sell value", False), "expenses": ("Expenses on transfer", False), "gain": ("Gain / loss", False),
}
_GUESS = {
    "asset": ("scrip", "symbol", "stock name", "scheme", "security", "asset", "instrument", "script", "company", "name", "particular"),
    "type": ("asset type", "asset class", "category", "segment", "type", "class"),
    "term": ("term", "holding type", "gain type", "stcg/ltcg", "nature"),
    "buy_date": ("buy date", "purchase date", "date of purchase", "acquisition date", "entry date", "date of acquisition", "invest"),
    "sell_date": ("sell date", "sale date", "date of sale", "redemption date", "exit date", "date of transfer", "sold"),
    "buy_value": ("buy value", "purchase value", "cost of acquisition", "purchase amount", "buy amount", "invested", "cost", "purchase"),
    "sell_value": ("sell value", "sale value", "sale consideration", "redemption amount", "sell amount", "consideration", "proceeds", "sale"),
    "expenses": ("expense", "brokerage", "charges", "stt"),
    "gain": ("realized p&l", "realised p&l", "capital gain", "gain/loss", "gain / loss", "profit/loss", "p&l", "pnl", "profit", "gain"),
}
_HEADER_WORDS = tuple({w for words in _GUESS.values() for w in words} | {"quantity", "qty", "isin", "date", "value"})
_EQUITY_WORDS = ("equity", "share", "stock", "listed", "etf")
_DEBT_WORDS = ("debt", "liquid", "bond fund", "gilt", "money market", "overnight", "fmp", "specified")
_OTHER_WORDS = ("property", "land", "building", "gold", "unlisted", "bond", "debenture", "jewel", "sgb", "reit", "invit", "foreign", "crypto", "vda")
_IGNORE_WORDS = ("intraday", "speculat", "f&o", "fno", "future", "option", "derivative", "commodity", "currency", "dividend")


# ------------------------------------------------------------------ reading
def detect_header_row(raw: pd.DataFrame, scan: int = 60) -> int:
    best, best_score = 0, 0
    for i in range(min(scan, len(raw))):
        cells = [str(c).strip().lower() for c in raw.iloc[i].tolist() if pd.notna(c)]
        score = sum(1 for c in cells if any(w in c for w in _HEADER_WORDS) and len(c) < 45)
        if score > best_score and len(cells) >= 3:
            best, best_score = i, score
    return best


def guess_columns(df: pd.DataFrame) -> dict:
    """Best guess of which column is which; each column is used once."""
    cols, used, out = list(df.columns), set(), {}
    for key in ("buy_date", "sell_date", "buy_value", "sell_value", "gain", "expenses", "term", "type", "asset"):
        for word in _GUESS[key]:
            hit = next((c for c in cols if c not in used and word in str(c).lower()), None)
            if hit is not None:
                out[key] = hit
                used.add(hit)
                break
    return out


# ----------------------------------------------------------- classification
def classify_asset(type_text: str, asset_text: str = "", default: str = EQUITY) -> str:
    t = f"{type_text} ".lower()
    if any(w in t for w in _IGNORE_WORDS):
        return IGNORE
    if any(w in t for w in _DEBT_WORDS):
        return DEBT
    if any(w in t for w in _OTHER_WORDS):
        return OTHER
    if any(w in t for w in _EQUITY_WORDS) or "eq" in t.replace("/", " ").replace("-", " ").split():
        return EQUITY
    a = asset_text.lower()
    if any(w in a for w in ("liquid fund", "debt fund", "gilt fund", "overnight fund", "money market")):
        return DEBT
    return default


def term_for(klass: str, buy, sell, stated: str = "") -> tuple[str, bool]:
    """(term, needs_check). Uses the dates when both are present, else the statement's own short/long column."""
    if klass == DEBT:
        return "Short", False
    if pd.notna(buy) and pd.notna(sell):
        months = LONG_TERM_MONTHS.get(klass, 24)
        return ("Long" if sell > buy + pd.DateOffset(months=months) else "Short"), False
    low = (stated or "").lower()
    if "long" in low or "ltcg" in low:
        return "Long", False
    if "short" in low or "stcg" in low:
        return "Short", False
    return "Short", True


def _dates(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    return pd.to_datetime(series, errors="coerce", dayfirst=True, format="mixed")


def normalise(df: pd.DataFrame, mapping: dict, default_class: str = EQUITY) -> pd.DataFrame:
    """One row per sale: asset, dates, days held, cost, sale, gain, class, term and a 'check' flag."""
    if not mapping.get("asset"):
        raise ValueError("Choose the column that has the asset or scrip name.")
    has_values = mapping.get("buy_value") and mapping.get("sell_value")
    if not mapping.get("gain") and not has_values:
        raise ValueError("Choose either the gain / loss column, or both the buy value and sell value columns.")

    def col(key):
        name = mapping.get(key)
        return df[name] if name else pd.Series([None] * len(df), index=df.index)

    def money(key):
        return col(key).map(lambda v: parse_amount(v) if pd.notna(v) and str(v).strip() != "" else None)

    out = pd.DataFrame({"asset": col("asset").astype(str).str.strip()})
    out["buy_date"], out["sell_date"] = _dates(col("buy_date")), _dates(col("sell_date"))
    cost, sale, exp, gain = money("buy_value"), money("sell_value"), money("expenses"), money("gain")
    computed = sale.astype(float) - cost.astype(float) - exp.fillna(0).astype(float)
    out["cost"], out["sale"] = cost.astype(float), sale.astype(float)
    out["gain"] = gain.astype(float).where(gain.notna(), computed) if mapping.get("gain") else computed
    types, stated = col("type").fillna("").astype(str), col("term").fillna("").astype(str)
    out["class"] = [classify_asset(t, a, default_class) for t, a in zip(types, out["asset"])]
    terms = [term_for(k, b, s, st) for k, b, s, st in zip(out["class"], out["buy_date"], out["sell_date"], stated)]
    out["term"], out["check"] = [t for t, _ in terms], [c for _, c in terms]
    out["days"] = (out["sell_date"] - out["buy_date"]).dt.days
    junk = out["asset"].str.lower().str.contains(r"^(?:nan|none|)$|total|^grand|summary", regex=True)
    out = out[~junk & out["gain"].notna()].reset_index(drop=True)
    return out[["asset", "buy_date", "sell_date", "days", "cost", "sale", "gain", "class", "term", "check"]]


# ------------------------------------------------------------------- totals
def bucket_of(klass: str, term: str) -> str | None:
    if klass == IGNORE:
        return None
    if klass == DEBT:
        return "stcg_other"
    if klass == EQUITY:
        return "ltcg_equity" if term == "Long" else "stcg_equity"
    return "ltcg_other" if term == "Long" else "stcg_other"


def summarise(rows: pd.DataFrame) -> dict:
    totals = {k: 0.0 for k in BUCKETS}
    ignored = 0.0
    for r in rows.itertuples():
        gain = float(r.gain) if pd.notna(r.gain) else 0.0
        bucket = bucket_of(rows.at[r.Index, "class"], r.term)
        if bucket is None:
            ignored += gain
        else:
            totals[bucket] += gain
    return {"buckets": {k: round(v) for k, v in totals.items()}, "ignored": round(ignored),
            "rows": len(rows), "to_check": int(rows["check"].sum()) if len(rows) else 0}


def set_off(buckets: dict) -> dict:
    """Set losses off within the capital gains head.

    A long-term loss can go only against long-term gains. A short-term loss can go
    against any capital gain; it is used first where the tax rate is highest
    (slab-rate gains, then short-term equity, then long-term). What is left is
    carried forward and is not set off against other income.
    """
    b = {k: float(buckets.get(k, 0)) for k in BUCKETS}

    def absorb(loss: float, order: list) -> float:
        for key in order:
            if loss <= 0:
                break
            used = min(loss, max(0.0, b[key]))
            b[key] -= used
            loss -= used
        return loss

    lt_loss = 0.0
    for key, against in (("ltcg_equity", "ltcg_other"), ("ltcg_other", "ltcg_equity")):
        if b[key] < 0:
            loss, b[key] = -b[key], 0.0
            lt_loss += absorb(loss, [against])
    st_loss = 0.0
    for key in ("stcg_other", "stcg_equity"):
        if b[key] < 0:
            loss, b[key] = -b[key], 0.0
            st_loss += absorb(loss, ["stcg_other", "stcg_equity", "ltcg_other", "ltcg_equity"])
    return {"buckets": {k: round(v) for k, v in b.items()},
            "short_term_loss_carried": round(st_loss), "long_term_loss_carried": round(lt_loss)}


TEMPLATE_COLUMNS = ["Asset / scrip", "Asset type", "Buy date", "Sell date", "Quantity", "Buy value", "Sell value",
                    "Expenses on transfer", "Gain / loss (optional)"]
