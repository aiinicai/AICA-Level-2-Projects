"""Symbol resolution and data download from Yahoo Finance (via the yfinance package).

Every download is wrapped so that one failed endpoint becomes a warning, not a crash.
The rest of the package never calls the network directly.
"""

from __future__ import annotations

import logging
import re
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from .fmt import num
from .peers import ALIASES, BENCHMARK, SENSEX

IST = ZoneInfo("Asia/Kolkata")

logging.getLogger("yfinance").setLevel(logging.CRITICAL)


class ResolveError(Exception):
    """The query could not be matched to a listed Indian equity."""


def _yf():
    try:
        import yfinance as yf  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - environment problem
        raise SystemExit(
            "The yfinance package is missing. Run scripts/setup_env.sh (or "
            "pip install -r scripts/requirements.txt) and try again."
        ) from exc
    # yfinance code triggers pandas deprecation warnings; they are noise for the user.
    warnings.filterwarnings("ignore", message=".*inplace keyword.*")
    warnings.filterwarnings("ignore", module="yfinance")
    return yf


def _has_prices(symbol: str) -> bool:
    try:
        h = _yf().Ticker(symbol).history(period="5d", auto_adjust=False)
        return not h.empty
    except Exception:
        return False


def resolve(query: str) -> dict:
    """Map a company name, NSE symbol or BSE code to a Yahoo ticker.

    Order: explicit suffix, 6-digit BSE code, alias table, bare symbol on NSE,
    Yahoo search (NSE preferred over BSE), bare symbol on BSE.
    """
    q = query.strip()
    if not q:
        raise ResolveError("Empty stock name.")
    qu = q.upper().replace(" ", "")
    tried: list[str] = []

    def ok(sym: str, how: str) -> dict | None:
        tried.append(sym)
        if _has_prices(sym):
            return {"symbol": sym, "exchange": "NSE" if sym.endswith(".NS") else "BSE", "matched_by": how}
        return None

    if qu.endswith((".NS", ".BO")):
        hit = ok(qu, "explicit ticker")
        if hit:
            return hit
    if re.fullmatch(r"\d{6}", qu):
        hit = ok(f"{qu}.BO", "BSE code")
        if hit:
            return hit
    alias = ALIASES.get(q.lower())
    if alias:
        hit = ok(f"{alias}.NS", "alias")
        if hit:
            return hit
    if re.fullmatch(r"[A-Z0-9&\-]{2,20}", qu) and " " not in q:
        hit = ok(f"{qu}.NS", "NSE symbol")
        if hit:
            return hit

    try:
        quotes = _yf().Search(q, max_results=10, news_count=0).quotes
    except Exception:
        quotes = []
    indian = [x for x in quotes if x.get("exchange") in ("NSI", "BSE") and x.get("quoteType", "EQUITY") == "EQUITY"]
    indian.sort(key=lambda x: 0 if x.get("exchange") == "NSI" else 1)
    for x in indian:
        hit = ok(x["symbol"], "Yahoo search")
        if hit:
            hit["search_name"] = x.get("longname") or x.get("shortname")
            return hit

    if re.fullmatch(r"[A-Z0-9&\-]{2,20}", qu):
        hit = ok(f"{qu}.BO", "BSE symbol")
        if hit:
            return hit
    raise ResolveError(
        f"Could not find an NSE or BSE listed equity for '{query}'. Tried: {', '.join(tried) or 'search only'}. "
        "Try the exact NSE symbol (for example TATASTEEL) or the 6-digit BSE code."
    )


@dataclass
class RawData:
    symbol: str
    exchange: str
    info: dict
    ohlc: pd.DataFrame
    bench: pd.Series
    sensex_last: float | None
    income: pd.DataFrame
    balance: pd.DataFrame
    cashflow: pd.DataFrame
    q_income: pd.DataFrame
    news: list[dict]
    fx_to_inr: float = 1.0
    fetched_at: str = ""
    warnings: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)  # downloads that failed after retries
    q_sources: dict[str, str] = field(default_factory=dict)  # quarter end -> source, for quarters from filings


RETRY_WAITS = (2.0, 4.0)  # seconds between attempts for the downloads the rating depends on


def _safe(label: str, fn, warnings: list[str], default, retries: int = 0, failed: list[str] | None = None,
          valid=None):
    """Call fn, retrying on errors (or on an invalid result when `valid` is given).

    A download that still fails is recorded in `failed`, so the pipeline can tell
    "the source has no data" apart from "the download did not work".
    """
    last_err = "empty response"
    for attempt in range(retries + 1):
        try:
            out = fn()
            if out is not None and (valid is None or valid(out)):
                return out
            if valid is None:
                return default
        except Exception as exc:  # network, parsing or upstream schema change
            last_err = type(exc).__name__
        if attempt < retries:
            time.sleep(RETRY_WAITS[min(attempt, len(RETRY_WAITS) - 1)])
    warnings.append(f"{label}: not available ({last_err}).")
    if failed is not None:
        failed.append(label)
    return default


def _profile_ok(info) -> bool:
    return isinstance(info, dict) and bool(info.get("marketCap") or info.get("longName") or info.get("shortName"))


def _frame_ok(df) -> bool:
    return isinstance(df, pd.DataFrame) and not df.empty


def _close_series(df: pd.DataFrame) -> pd.Series:
    if df is None or df.empty:
        return pd.Series(dtype=float)
    s = df["Close"].dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return s


def download_history(symbol: str, period: str = "5y") -> pd.DataFrame:
    df = _yf().Ticker(symbol).history(period=period, auto_adjust=False, actions=False)
    if df.empty:
        return df
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


def fetch(symbol: str, exchange: str) -> RawData:
    yf = _yf()
    warnings: list[str] = []
    failed: list[str] = []
    t = yf.Ticker(symbol)

    info = _safe("Company profile", lambda: t.info, warnings, {}, retries=2, failed=failed, valid=_profile_ok)
    ohlc = _safe("Price history", lambda: download_history(symbol), warnings, pd.DataFrame())
    if ohlc.empty:
        raise ResolveError(f"No price history returned for {symbol}.")

    bench = _close_series(_safe("Nifty 50 history", lambda: download_history(BENCHMARK[0]), warnings,
                                pd.DataFrame()))
    sensex = _close_series(_safe("Sensex level", lambda: download_history(SENSEX[0], "5d"), warnings,
                                 pd.DataFrame()))
    def stmt(label, fn):
        return _safe(label, fn, warnings, pd.DataFrame(), retries=2, failed=failed, valid=_frame_ok)

    income = stmt("Annual income statement", lambda: t.income_stmt)
    balance = stmt("Annual balance sheet", lambda: t.balance_sheet)
    cashflow = stmt("Annual cash flow", lambda: t.cashflow)
    q_income = stmt("Quarterly results", lambda: t.quarterly_income_stmt)

    def _news():
        items = yf.Search(symbol, max_results=1, news_count=8).news or []
        if not items and info.get("shortName"):
            items = yf.Search(info["shortName"], max_results=1, news_count=8).news or []
        out = []
        for n in items:
            ts = n.get("providerPublishTime")
            out.append({
                "title": n.get("title"),
                "publisher": n.get("publisher"),
                "link": n.get("link"),
                "date": datetime.fromtimestamp(ts, IST).strftime("%d-%b-%Y") if ts else None,
            })
        return out

    news = _safe("News headlines", _news, warnings, [])

    # Statements for some dual-listed companies are filed in USD. Convert to INR.
    fx = 1.0
    fin_ccy = (info.get("financialCurrency") or "INR").upper()
    if fin_ccy != "INR":
        rate = _close_series(_safe(f"{fin_ccy}/INR rate", lambda: download_history(f"{fin_ccy}INR=X", "5d"),
                                   warnings, pd.DataFrame()))
        if not rate.empty:
            fx = float(rate.iloc[-1])
            warnings.append(f"Financial statements are reported in {fin_ccy}; converted at {fx:.2f} INR per {fin_ccy}.")
        else:
            warnings.append(f"Financial statements are in {fin_ccy} and could not be converted. Ratios may be wrong.")

    return RawData(
        symbol=symbol, exchange=exchange, info=info or {}, ohlc=ohlc, bench=bench,
        sensex_last=num(sensex.iloc[-1]) if not sensex.empty else None,
        income=income if income is not None else pd.DataFrame(),
        balance=balance if balance is not None else pd.DataFrame(),
        cashflow=cashflow if cashflow is not None else pd.DataFrame(),
        q_income=q_income if q_income is not None else pd.DataFrame(),
        news=news, fx_to_inr=fx,
        fetched_at=datetime.now(IST).strftime("%d-%b-%Y %H:%M IST"),
        warnings=warnings, failed=failed,
    )


def fetch_sector_index(ticker: str) -> pd.Series:
    try:
        return _close_series(download_history(ticker, "2y"))
    except Exception:
        return pd.Series(dtype=float)


PEER_FIELDS = ("longName", "shortName", "marketCap", "trailingPE", "forwardPE", "priceToBook", "returnOnEquity",
               "operatingMargins", "profitMargins", "dividendYield", "revenueGrowth", "currentPrice",
               "regularMarketPrice", "enterpriseToEbitda", "financialCurrency")


def fetch_peers(bases: list[str]) -> list[dict]:
    """Snapshot metrics and 1-year return for each peer. Peers with no data are dropped."""
    if not bases:
        return []
    yf = _yf()
    tickers = [f"{b}.NS" for b in bases]

    def one(sym: str) -> dict | None:
        inf = {}
        for attempt in range(2):
            try:
                inf = yf.Ticker(sym).info or {}
            except Exception:
                inf = {}
            if inf.get("marketCap"):
                break
            if attempt == 0:
                time.sleep(RETRY_WAITS[0])
        if not inf.get("marketCap"):
            return None
        row = {k: inf.get(k) for k in PEER_FIELDS}
        row["symbol"] = sym
        return row

    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = [r for r in pool.map(one, tickers) if r]

    try:
        px = yf.download(tickers, period="13mo", progress=False, auto_adjust=True)["Close"]
        if isinstance(px, pd.Series):
            px = px.to_frame(tickers[0])
        px.index = pd.to_datetime(px.index).tz_localize(None)
    except Exception:
        px = pd.DataFrame()
    for r in rows:
        r["return_1y"] = None
        if r["symbol"] in getattr(px, "columns", []):
            s = px[r["symbol"]].dropna()
            if len(s) > 200:
                start = s.asof(s.index[-1] - pd.DateOffset(years=1))
                if start and start > 0:
                    r["return_1y"] = (s.iloc[-1] / start - 1) * 100
    return rows
