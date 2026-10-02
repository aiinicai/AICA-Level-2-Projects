"""
Network fetchers. Every fetch is cached under data/cache so the app can be
rebuilt offline and every figure can be traced to the raw file it came from.

Sources
  * NSE equity list (symbol ↔ ISIN)    archives.nseindia.com  EQUITY_L.csv
  * AMFI NAV file (scheme codes)        amfiindia.com NAVAll.txt
  * NAV history                          api.mfapi.in (community mirror of AMFI data)
  * Prices, financials, market data      Yahoo Finance via the yfinance library (unofficial)
"""
import csv
import io
import math
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime

from common import CACHE, load_json, log, month_ends, now_iso, save_json, fy_label

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "*/*", "Accept-Language": "en-IN,en;q=0.9"}


def http_get(url, timeout=30, retries=2):
    last = None
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - report any network failure
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET {url} failed: {last}")


# ------------------------------------------------------------------ NSE equity list
NSE_LIST_URLS = ["https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
                 "https://archives.nseindia.com/content/equities/EQUITY_L.csv"]


def nse_equity_list(refresh=False):
    """Return {symbol: {name, isin}} and {isin: symbol}. Cached for 7 days."""
    path = CACHE / "nse_equity_list.csv"
    if refresh or not path.exists() or time.time() - path.stat().st_mtime > 7 * 86400:
        for u in NSE_LIST_URLS:
            try:
                path.write_bytes(http_get(u))
                log.info("NSE equity list downloaded from %s", u)
                break
            except Exception as e:  # noqa: BLE001
                log.warning("NSE equity list: %s", e)
    by_sym, by_isin = {}, {}
    if path.exists():
        for row in csv.DictReader(io.StringIO(path.read_text(encoding="utf-8", errors="replace"))):
            row = {k.strip().upper(): (v or "").strip() for k, v in row.items() if k}
            sym, isin = row.get("SYMBOL"), row.get("ISIN NUMBER")
            if sym and isin:
                by_sym[sym] = {"name": row.get("NAME OF COMPANY", sym), "isin": isin, "series": row.get("SERIES", "")}
                by_isin[isin] = sym
    return by_sym, by_isin


# ------------------------------------------------------------------ AMFI
def amfi_navall(refresh=False):
    """Parse AMFI NAVAll.txt → list of {code, name, isin_growth, nav, date, amc}. Cached 1 day."""
    path = CACHE / "amfi_navall.txt"
    if refresh or not path.exists() or time.time() - path.stat().st_mtime > 86400:
        try:
            path.write_bytes(http_get("https://www.amfiindia.com/spages/NAVAll.txt", timeout=60))
            log.info("AMFI NAVAll.txt downloaded")
        except Exception as e:  # noqa: BLE001
            log.warning("AMFI NAVAll: %s", e)
    out, amc = [], ""
    if not path.exists():
        return out
    # Column positions come from the header row. AMFI moved Plan and Option out of the scheme name into their
    # own columns (8 columns instead of 6); rows that leave those columns blank still carry them in the name.
    col = {"code": 0, "isin_growth": 1, "isin_reinv": 2, "name": 3, "plan": None, "option": None, "nav": 4, "date": 5}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = [p.strip() for p in line.split(";")]
        if parts and parts[0].lower() == "scheme code":
            head = [p.lower() for p in parts]
            find = lambda *keys: next((i for i, h in enumerate(head) if any(k in h for k in keys)), None)  # noqa: E731
            col.update(code=0, isin_growth=find("growth"), isin_reinv=find("reinvest"), name=find("scheme name"),
                       plan=find("plan"), option=find("option"), nav=find("net asset value"), date=find("date"))
            if None in (col["name"], col["nav"], col["date"]):
                raise ValueError(f"AMFI NAVAll.txt header not recognised: {line!r}")
            continue
        if len(parts) > max(v for v in col.values() if v is not None) and parts[0].isdigit():
            g = lambda k: parts[col[k]] if col[k] is not None else ""  # noqa: E731
            full = " - ".join(x for x in (g("name"), g("plan"), g("option")) if x and x != "-")
            out.append({"code": g("code"), "isin_growth": g("isin_growth"), "isin_reinv": g("isin_reinv"), "name": full,
                        "nav": g("nav"), "date": g("date"), "amc": amc})
        elif line.strip() and ";" not in line and "Mutual Fund" in line:
            amc = line.strip()
    return out


BAD_WORDS = ("idcw", "dividend", "bonus", "payout", "reinvest", "segregated", "unclaimed", "institutional", "retail plan")


def resolve_scheme(s, navall):
    """Pick Direct-Growth and Regular-Growth AMFI codes for a configured scheme."""
    res = {}
    for plan in ("direct", "regular"):
        cands = []
        for r in navall:
            n = r["name"].lower()
            if not any(all(k in n for k in grp) for grp in s["match_any"]):
                continue
            if any(x in n for x in s.get("exclude", [])) or any(x in n for x in BAD_WORDS):
                continue
            if "growth" not in n:
                continue
            is_direct = "direct" in n
            if (plan == "direct") != is_direct:
                continue
            cands.append(r)
        cands.sort(key=lambda r: (len(r["name"]), r["code"]))
        best = cands[0] if cands else None
        ties = [r["code"] for r in cands if best and r["name"].lower() == best["name"].lower()]
        if len(ties) > 1:  # identical names under different codes (e.g. lock-in variants): the pick is arbitrary
            log.warning("%s %s: %d AMFI codes share the name %r (%s); using %s. Pin the code in schemes.json.",
                        s["name"], plan, len(ties), best["name"], ", ".join(ties), best["code"])
        res[plan] = best
    return res


def _base_scheme_name(name):
    n = re.sub(r"\b(direct|regular|plan|growth|option|opt)\b", " ", name.lower())
    return " ".join(re.sub(r"[^a-z0-9&]+", " ", n).split())


def amfi_search(q, navall, limit=20):
    """Growth-option schemes matching q (words of the name, an AMFI code or an ISIN), paired as Direct / Regular."""
    q = (q or "").strip()
    toks = [t for t in re.split(r"\s+", q.lower()) if t]
    if not toks:
        return []
    exact = [r for r in navall if q.upper() in (r["code"], (r.get("isin_growth") or "").upper(), (r.get("isin_reinv") or "").upper())]
    bases = {_base_scheme_name(r["name"]) for r in exact}
    groups = {}
    for r in navall:
        n = r["name"].lower()
        if "growth" not in n or any(x in n for x in BAD_WORDS):
            continue
        base = _base_scheme_name(r["name"])
        if not (base in bases or (not exact and all(t in n for t in toks))):
            continue
        g = groups.setdefault((r["amc"], base), {"amc": r["amc"], "base": base, "direct": None, "regular": None})
        plan = "direct" if "direct" in n else "regular"
        cur = g[plan]
        if cur is None or len(r["name"]) < len(cur["name"]):  # prefer the plain Growth option over variants
            g[plan] = {"code": r["code"], "name": r["name"], "isin": r.get("isin_growth"), "nav": r.get("nav"), "date": r.get("date")}
    out = [g for g in groups.values() if g["direct"]]
    out.sort(key=lambda g: (g["regular"] is None, len(g["base"])))
    return out[:limit]


def mf_nav_history(code, refresh=False):
    """Full NAV history for an AMFI scheme code from api.mfapi.in. Cached 1 day."""
    path = CACHE / f"mf_nav_{code}.json"
    if refresh or not path.exists() or time.time() - path.stat().st_mtime > 86400:
        try:
            import json as _j
            raw = _j.loads(http_get(f"https://api.mfapi.in/mf/{code}", timeout=45))
            if raw.get("data"):
                save_json(path, raw)
        except Exception as e:  # noqa: BLE001
            log.warning("NAV history %s: %s", code, e)
    return load_json(path)


def monthly_from_daily(pairs, dates):
    """pairs: [(date, value)] any order → value on or before each month-end in dates (None if none within 10 days)."""
    pairs = sorted(pairs)
    out, j, last = [], 0, None
    for d in dates:
        while j < len(pairs) and pairs[j][0] <= d:
            last = pairs[j]
            j += 1
        out.append(round(last[1], 4) if last and (d - last[0]).days <= 10 else None)
    return out


def nav_monthly(raw, dates):
    pairs = []
    for x in (raw or {}).get("data", []):
        try:
            pairs.append((datetime.strptime(x["date"], "%d-%m-%Y").date(), float(x["nav"])))
        except (ValueError, KeyError):
            continue
    return monthly_from_daily(pairs, dates)


# ------------------------------------------------------------------ Yahoo Finance (yfinance)
def _yf():
    import yfinance as yf  # imported lazily so the server starts even if the package is missing
    return yf


def yahoo_ticker(symbol):
    if symbol.startswith("^") or "." in symbol:
        return symbol
    return f"{symbol}.NS"


def price_cache():
    """The cached daily closes, as the build reads them when it does not fetch."""
    return load_json(CACHE / "yahoo_prices.json", {}) or {}


def company_cache(ticker):
    """The cached profile and statements of one company (None if never fetched)."""
    return load_json(CACHE / f"yahoo_co_{ticker.replace('^', '_')}.json")


def yahoo_prices(tickers, start, end, refresh=False):
    """Daily closes (split-adjusted, not dividend-adjusted) for many tickers → {ticker: [[iso_date, close], ...]}.
    Cached per ticker; only missing/stale tickers are downloaded."""
    cache = load_json(CACHE / "yahoo_prices.json", {}) or {}
    stale = [t for t in tickers if refresh or t not in cache or cache[t].get("fetched", "")[:10] != date.today().isoformat()]
    if stale:
        yf = _yf()
        for i in range(0, len(stale), 60):
            batch = stale[i:i + 60]
            try:
                df = yf.download(batch, start=start.isoformat(), end=end.isoformat(), interval="1d", auto_adjust=False,
                                 actions=False, group_by="ticker", threads=True, progress=False, timeout=30)
            except Exception as e:  # noqa: BLE001
                log.warning("Yahoo prices batch failed (%s…): %s", batch[0], e)
                continue
            for t in batch:
                try:
                    try:
                        s = df[t]["Close"]
                    except KeyError:
                        s = df["Close"]
                    s = s.dropna()
                    if hasattr(s, "columns"):
                        s = s.iloc[:, 0]
                    pts = [[ix.date().isoformat(), float(v)] for ix, v in s.items() if not math.isnan(float(v))]
                    if pts:
                        cache[t] = {"fetched": now_iso(), "points": pts}
                    else:
                        log.warning("No prices returned for %s", t)
                except Exception as e:  # noqa: BLE001
                    log.warning("Prices for %s unavailable: %s", t, e)
            log.info("Prices downloaded: %d/%d", min(i + 60, len(stale)), len(stale))
        save_json(CACHE / "yahoo_prices.json", cache)
    return cache


FIN_MAP = {
    "revenue": ["TotalRevenue", "OperatingRevenue"],
    "ebitda": ["EBITDA", "NormalizedEBITDA"],
    "depreciation": ["ReconciledDepreciation", "DepreciationAndAmortizationInIncomeStatement", "DepreciationAmortizationDepletionIncomeStatement"],
    "interest": ["InterestExpense", "InterestExpenseNonOperating"],
    "pbt": ["PretaxIncome"],
    "tax": ["TaxProvision"],
    "pat": ["NetIncomeCommonStockholders", "NetIncome", "NetIncomeFromContinuingOperationNetMinorityInterest"],
    "total_assets": ["TotalAssets"],
    "net_worth": ["StockholdersEquity", "CommonStockEquity"],
    "total_debt": ["TotalDebt"],
    "cash_eq": ["CashAndCashEquivalents", "CashCashEquivalentsAndShortTermInvestments"],
    "current_assets": ["CurrentAssets"],
    "current_liabilities": ["CurrentLiabilities"],
    "cfo": ["OperatingCashFlow", "CashFlowFromContinuingOperatingActivities"],
    "capex": ["CapitalExpenditure"],
    "shares": ["OrdinarySharesNumber", "ShareIssued"],
}


def _pick(df, keys, col):
    for k in keys:
        if k in df.index:
            v = df.at[k, col]
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
            if not math.isnan(v):
                return v
    return None


def yahoo_company(symbol, refresh=False):
    """Profile + yearly statements for one company. Cached 7 days. Amounts converted to ₹ crore."""
    tk = yahoo_ticker(symbol)
    path = CACHE / f"yahoo_co_{tk.replace('^', '_')}.json"
    cached = load_json(path)
    if cached and not refresh and (datetime.now() - datetime.fromisoformat(cached["fetched"])).days < 7:
        return cached
    yf = _yf()
    t = yf.Ticker(tk)
    info = {}
    try:
        info = t.get_info() or {}
    except Exception as e:  # noqa: BLE001
        log.warning("%s info unavailable: %s", tk, e)
    frames = {}
    for nm, fn in (("inc", t.get_income_stmt), ("bal", t.get_balance_sheet), ("cf", t.get_cash_flow)):
        try:
            frames[nm] = fn(pretty=False, freq="yearly")
        except Exception as e:  # noqa: BLE001
            log.warning("%s %s statement unavailable: %s", tk, nm, e)
    cols = set()
    for df in frames.values():
        if df is not None and not df.empty:
            cols |= set(df.columns)
    years = []
    for col in sorted(cols):
        row = {"period_end": col.date().isoformat(), "fy": fy_label(col.date())}
        for k, keys in FIN_MAP.items():
            v = None
            for df in frames.values():
                if df is not None and not df.empty and col in df.columns:
                    v = _pick(df, keys, col)
                    if v is not None:
                        break
            row[k] = v
        if row["revenue"] is None and row["pat"] is None:
            continue
        years.append(row)
    divs = {}
    try:
        for ix, v in t.get_dividends(period="10y").items():
            divs[fy_label(ix.date())] = divs.get(fy_label(ix.date()), 0.0) + float(v)
    except Exception as e:  # noqa: BLE001
        log.warning("%s dividends unavailable: %s", tk, e)
    keep = ("longName", "shortName", "sector", "industry", "marketCap", "sharesOutstanding", "heldPercentInsiders", "heldPercentInstitutions",
            "currentPrice", "previousClose", "currency", "financialCurrency", "exchange", "quoteType", "trailingPE", "priceToBook", "beta", "website")
    out = {"symbol": symbol, "ticker": tk, "fetched": now_iso(), "info": {k: info.get(k) for k in keep}, "years": years, "dividends_by_fy": divs}
    if not years:
        log.warning("%s: no financial statements returned", tk)
    save_json(path, out)
    return out


def yahoo_market_caps(tickers, refresh=False):
    """Market cap and shares for many tickers via fast_info (parallel). Cached 1 day."""
    cache = load_json(CACHE / "yahoo_mcap.json", {}) or {}
    todo = [t for t in tickers if refresh or t not in cache or cache[t].get("fetched", "")[:10] != date.today().isoformat()]
    if todo:
        yf = _yf()

        def one(tk):
            fi = yf.Ticker(tk).fast_info
            def g(attr):
                try:
                    return getattr(fi, attr)
                except Exception:  # noqa: BLE001 - some fields are missing for thinly traded stocks
                    return None
            return tk, {"fetched": now_iso(), "market_cap": g("market_cap"), "shares": g("shares"), "last_price": g("last_price"), "currency": g("currency")}

        with ThreadPoolExecutor(max_workers=8) as ex:
            for fut in as_completed([ex.submit(one, t) for t in todo]):
                try:
                    tk, v = fut.result()
                    cache[tk] = v
                except Exception as e:  # noqa: BLE001
                    log.warning("Market cap unavailable: %s", e)
        save_json(CACHE / "yahoo_mcap.json", cache)
    return cache


_QUOTES: dict = {}  # ticker -> {"price", "date", "prev_close", "t"}; in memory, a quote is reused for 2 minutes


def latest_quotes(tickers, max_age=120):
    """Latest price per ticker from Yahoo daily bars: during NSE hours the day's bar carries the current price (Yahoo
    delays NSE by about 15 minutes); outside hours it is the last close. Returns {ticker: {price, date, prev_close}}."""
    now = time.time()
    need = [t for t in tickers if t not in _QUOTES or now - _QUOTES[t]["t"] > max_age]
    for i in range(0, len(need), 100):
        batch = need[i:i + 100]
        try:
            df = _yf().download(batch, period="5d", interval="1d", auto_adjust=False, actions=False, group_by="ticker",
                                threads=True, progress=False, timeout=30)
        except Exception as e:  # noqa: BLE001 - no quote is shown rather than a stale one presented as current
            log.warning("Latest quotes failed (%s…): %s", batch[0], e)
            continue
        for t in batch:
            try:
                try:
                    s = df[t]["Close"]
                except KeyError:
                    s = df["Close"]
                s = s.dropna()
                if hasattr(s, "columns"):
                    s = s.iloc[:, 0]
                if len(s):
                    _QUOTES[t] = {"price": round(float(s.iloc[-1]), 2), "date": s.index[-1].date().isoformat(),
                                  "prev_close": round(float(s.iloc[-2]), 2) if len(s) > 1 else None, "t": now}
            except Exception as e:  # noqa: BLE001
                log.warning("Latest quote for %s unavailable: %s", t, e)
    return {t: {k: v for k, v in _QUOTES[t].items() if k != "t"} for t in tickers if t in _QUOTES}


def latest_navs():
    """Latest NAV per AMFI scheme code from NAVAll.txt (AMFI publishes it every business day): {code: {nav, date}}."""
    out = {}
    for r in amfi_navall():
        try:
            out[r["code"]] = {"nav": float(r["nav"]), "date": datetime.strptime(r["date"], "%d-%b-%Y").date().isoformat()}
        except (ValueError, TypeError):
            continue
    return out


def yahoo_search(q):
    try:
        res = _yf().Search(q, max_results=10, news_count=0, lists_count=0, include_cb=False, raise_errors=False).quotes or []
    except Exception as e:  # noqa: BLE001
        log.warning("Yahoo search failed: %s", e)
        return []
    out = []
    for r in res:
        sym, exch = r.get("symbol", ""), r.get("exchange", "")
        if exch in ("NSI", "BSE", "BOM") or sym.endswith((".NS", ".BO")):
            out.append({"ticker": sym, "symbol": sym.split(".")[0], "name": r.get("longname") or r.get("shortname") or sym,
                        "exchange": "NSE" if sym.endswith(".NS") else "BSE", "type": r.get("quoteType")})
    return out
