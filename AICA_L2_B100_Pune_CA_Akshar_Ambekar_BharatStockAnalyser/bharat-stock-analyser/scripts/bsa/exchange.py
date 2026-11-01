"""Exchange layer: official filings from NSE (primary) and BSE (fallback).

What it adds to the Yahoo data:
    results freshness   board meetings for financial results (last held, next scheduled)
    latest quarters     consolidated quarterly results parsed from the XBRL filed with NSE
                        (SEBI integrated filing, from the December 2024 quarter onwards)
    shareholding        promoter, FII, DII and public split, and the share of promoter
                        holding that is pledged, from the shareholding pattern XBRL

These are the exchanges' website endpoints, not documented APIs. They need a browser-like
session (cookies and a TLS fingerprint, via curl_cffi) and can change or be blocked without
notice. The layer is therefore optional: every call is wrapped, a failure becomes a warning,
and the report runs on Yahoo data alone. Only public filings are read; nothing is written.
Set BSA_NO_EXCHANGE=1 (or pass --no-exchange) to switch the layer off.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import pandas as pd

from .fmt import num, q_label

NSE_HOME = "https://www.nseindia.com/"
NSE_API = "https://www.nseindia.com/api/"
BSE_HOME = "https://www.bseindia.com/"
BSE_API = "https://api.bseindia.com/BseIndiaAPI/api/"
TIMEOUT = 15
MAX_QUARTERS = 6  # XBRL files parsed per run; enough to cover a year-ago quarter and one gap

# Differences between Yahoo and the filing that are reported as a data note.
REVENUE_TOLERANCE = 0.02
PAT_TOLERANCE = 0.05


def enabled() -> bool:
    return os.environ.get("BSA_NO_EXCHANGE", "").strip().lower() not in ("1", "true", "yes")


# ---------------------------------------------------------------- network

class _Client:
    """One browser-like session per site, opened lazily with a visit to the home page."""

    def __init__(self):
        self._sessions: dict[str, object] = {}

    def _session(self, home: str):
        if home not in self._sessions:
            try:
                from curl_cffi import requests as http  # noqa: PLC0415
                s = http.Session(impersonate="chrome")
            except ImportError:  # BSE rejects plain requests; NSE mostly accepts them
                import requests as http  # noqa: PLC0415
                s = http.Session()
                s.headers["User-Agent"] = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                                           "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
            s.get(home, timeout=TIMEOUT)
            self._sessions[home] = s
        return self._sessions[home]

    def get(self, home: str, url: str, params: dict | None = None, json: bool = True):
        headers = {"Referer": home, "Accept": "application/json, text/plain, */*"}
        if home == BSE_HOME:
            headers["Origin"] = BSE_HOME.rstrip("/")
        last = None
        for attempt in range(2):
            try:
                r = self._session(home).get(url, params=params, headers=headers, timeout=TIMEOUT)
                if r.status_code == 200:
                    return r.json() if json else r.text
                last = f"HTTP {r.status_code}"
            except Exception as exc:  # network error, blocked session or bad JSON
                last = type(exc).__name__
                self._sessions.pop(home, None)  # a fresh session gets fresh cookies
            if attempt == 0:
                time.sleep(2.0)
        raise RuntimeError(last or "no response")


# ---------------------------------------------------------------- parsers (pure, tested offline)

_FACT = re.compile(r"<(?:[\w-]+):(\w+)\b([^>]*?)(?:/>|>([^<]*)</)", re.S)
_CONTEXT = re.compile(r"<xbrli:context\b[^>]*\bid=\"([^\"]+)\"[^>]*>(.*?)</xbrli:context>", re.S)


def _facts(text: str) -> dict[str, dict[str, str]]:
    """{element name: {context id: value}} for every fact in an XBRL instance."""
    out: dict[str, dict[str, str]] = {}
    for name, attrs, value in _FACT.findall(text):
        m = re.search(r'contextRef="([^"]+)"', attrs)
        if m and value is not None:
            out.setdefault(name, {})[m.group(1)] = value.strip()
    return out


def _contexts(text: str) -> dict[str, dict]:
    out = {}
    for cid, body in _CONTEXT.findall(text):
        start = re.search(r"<xbrli:startDate>([^<]+)<", body)
        end = re.search(r"<xbrli:endDate>([^<]+)<", body)
        instant = re.search(r"<xbrli:instant>([^<]+)<", body)
        out[cid] = {"start": start.group(1).strip() if start else None,
                    "end": (end or instant).group(1).strip() if (end or instant) else None,
                    "member": re.findall(r"explicitMember[^>]*>([^<]+)<", body)}
    return out


def _first(facts: dict, ctx: str, *names: str) -> float | None:
    for n in names:
        v = num(facts.get(n, {}).get(ctx))
        if v is not None:
            return v
    return None


def parse_results_xbrl(text: str) -> dict | None:
    """Quarterly figures from a SEBI results XBRL file (integrated or older format).

    Values in the instance are absolute rupees. The quarter is the plain (no dimension)
    duration context of about three months ending on the reporting period end date.
    """
    facts, ctxs = _facts(text), _contexts(text)
    end = None
    for v in facts.get("DateOfEndOfReportingPeriod", {}).values():
        end = v
    plain = {cid: c for cid, c in ctxs.items() if not c["member"] and c["start"] and c["end"]}
    quarter_ctx = None
    for cid, c in plain.items():
        try:
            days = (date.fromisoformat(c["end"]) - date.fromisoformat(c["start"])).days
        except ValueError:
            continue
        if 80 <= days <= 100 and (end is None or c["end"] == end):
            quarter_ctx = cid
            end = c["end"]
            break
    if quarter_ctx is None or end is None:
        return None
    q = quarter_ctx
    nature = next(iter(facts.get("NatureOfReportStandaloneConsolidated", {}).values()), None)
    revenue = _first(facts, q, "RevenueFromOperations")
    interest_earned = _first(facts, q, "InterestEarned")
    pbt = _first(facts, q, "ProfitBeforeTax", "ProfitLossFromOrdinaryActivitiesBeforeTax")
    pbt_pre = _first(facts, q, "ProfitBeforeExceptionalItemsAndTax",
                     "ProfitLossFromOrdinaryActivitiesBeforeExceptionalItemsAndTax")
    exceptional = (pbt - pbt_pre) if pbt is not None and pbt_pre is not None else \
        _first(facts, q, "ExceptionalItemsBeforeTax", "ExceptionalItems")
    pat_total = _first(facts, q, "ProfitLossForPeriod", "ProfitLossForThePeriod",
                       "NetProfitLossForThePeriod")
    owners = _first(facts, q, "ProfitOrLossAttributableToOwnersOfParent",
                    "ProfitOrLossAttributableToOwnersOfParentForPeriod",
                    "ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates")
    minority = _first(facts, q, "ProfitOrLossAttributableToNonControllingInterests", "ProfitLossOfMinorityInterest")
    if owners is None and pat_total is not None:
        owners = pat_total - (minority or 0.0)
    rec = {
        "period_start": plain[q]["start"],
        "period_end": end,
        "label": q_label(pd.Timestamp(end)),
        "nature": nature,
        "audited": next(iter(facts.get("WhetherResultsAreAuditedOrUnaudited", {}).values()), None),
        "is_bank": revenue is None and interest_earned is not None,
        "revenue": revenue,
        "interest_earned": interest_earned,
        "interest_expended": _first(facts, q, "InterestExpended"),
        "total_income": _first(facts, q, "Income", "TotalIncome"),
        "other_income": _first(facts, q, "OtherIncome"),
        "finance_costs": _first(facts, q, "FinanceCosts"),
        "depreciation": _first(facts, q, "DepreciationDepletionAndAmortisationExpense"),
        "exceptional": exceptional,
        "pbt": pbt,
        "tax": _first(facts, q, "TaxExpense"),
        "pat_total": pat_total,
        "pat": owners,
        "minority": minority,
        "eps_basic": _first(facts, q, "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations",
                            "BasicEarningsLossPerShareFromContinuingOperations",
                            "BasicEarningsPerShareAfterExtraordinaryItems"),
    }
    return rec if (rec["revenue"] is not None or rec["interest_earned"] is not None) and rec["pat"] is not None \
        else None


def parse_shareholding_xbrl(text: str) -> dict | None:
    """Promoter, FII, DII and public split (percent of shares) and promoter pledge."""
    facts, ctxs = _facts(text), _contexts(text)
    pct = facts.get("ShareholdingAsAPercentageOfTotalNumberOfShares", {})

    def share(member: str) -> float | None:
        for cid, c in ctxs.items():
            if c["member"] and c["member"][0].split(":")[-1] == member and cid in pct:
                v = num(pct[cid])
                return None if v is None else v * 100
        return None

    def promoter_fact(name: str) -> float | None:
        for cid, c in ctxs.items():
            if c["member"] and c["member"][0].split(":")[-1] == "ShareholdingOfPromoterAndPromoterGroupMember":
                v = num(facts.get(name, {}).get(cid))
                if v is not None:
                    return v
        return None

    promoter = share("ShareholdingOfPromoterAndPromoterGroupMember")
    public = share("PublicShareholdingMember")
    if promoter is None and public is None:
        return None
    fii, dii = share("InstitutionsForeignMember"), share("InstitutionsDomesticMember")
    flag = next(iter(facts.get("WhetherAnySharesHeldByPromotersAreEncumberedUnderPledged", {}).values()), None)
    pledged = promoter_fact("EncumberedShareUnderPledgedAsPercentageOfTotalNumberOfShares")
    encumbered = promoter_fact("EncumberedSharesHeldAsPercentageOfTotalNumberOfShares")
    as_of = next(iter(facts.get("DateOfReport", {}).values()), None)
    return {
        "as_of": as_of,
        "promoter": promoter,
        "fii": fii,
        "dii": dii,
        "mutual_funds": share("MutualFundsOrUTIMember"),
        "public": public,
        "public_other": (public - (fii or 0) - (dii or 0)) if public is not None else None,
        "pledge_reported": None if flag is None else flag.strip().lower() in ("true", "yes"),
        "pledged_pct_of_promoter": pledged * 100 if pledged is not None else (0.0 if flag and flag.lower() in (
            "false", "no") else None),
        "encumbered_pct_of_promoter": encumbered * 100 if encumbered is not None else None,
    }


def _d(text: str | None, fmts=("%d-%b-%Y", "%d-%b-%Y %H:%M:%S", "%d-%B-%Y", "%Y-%m-%dT%H:%M:%S.%f",
                               "%Y-%m-%dT%H:%M:%S")) -> date | None:
    if not text:
        return None
    t = text.strip().title() if "T" not in text else text.strip()
    for f in fmts:
        try:
            return datetime.strptime(t, f).date()
        except ValueError:
            continue
    return None


def quarter_end_before(d: date) -> date:
    """Latest quarter end strictly before d (results meetings follow the quarter they report)."""
    for months_back in range(0, 13):
        y, m = d.year, d.month - months_back
        while m <= 0:
            m += 12
            y -= 1
        if m in (3, 6, 9, 12):
            e = date(y, m, 31 if m in (3, 12) else 30)
            if e < d:
                return e
    return d


def results_meetings(rows: list[dict], today: date) -> dict:
    """Last held and next scheduled board meeting for financial results.

    A meeting counts when its purpose or description mentions financial results. The quarter
    it reports is the latest quarter end before the meeting date.
    """
    dates = set()
    for r in rows or []:
        text = f"{r.get('bm_purpose') or r.get('purpose') or ''} {r.get('bm_desc') or ''}".lower()
        if "result" in text:
            d = _d(r.get("bm_date") or r.get("date"))
            if d:
                dates.add(d)
    past = sorted(d for d in dates if d <= today)
    future = sorted(d for d in dates if d > today)
    out = {"last": None, "next": None}
    if future:
        out["next"] = {"date": future[0].strftime("%d-%b-%Y"),
                       "quarter": q_label(pd.Timestamp(quarter_end_before(future[0])))}
    if past:
        qe = quarter_end_before(past[-1])
        out["last"] = {"date": past[-1].strftime("%d-%b-%Y"), "quarter_end": qe.isoformat(),
                       "quarter": q_label(pd.Timestamp(qe)),
                       # A later meeting for the same quarter means this one was postponed.
                       "rescheduled": bool(future) and quarter_end_before(future[0]) == qe}
    return out


def pick_filings(rows: list[dict]) -> list[dict]:
    """One filing per quarter, newest first: consolidated where the company files it, latest revision."""
    fin = [r for r in rows or [] if "financ" in (r.get("type") or "Financials").lower() and r.get("xbrl")]
    has_cons = any((r.get("consolidated") or "").lower().startswith("consol") for r in fin)
    best: dict[date, dict] = {}
    for r in fin:
        if has_cons != (r.get("consolidated") or "").lower().startswith("consol"):
            continue
        qe, filed = _d(r.get("qe_Date")), _d(r.get("broadcast_Date"))
        if not qe:
            continue
        cur = best.get(qe)
        if cur is None or (filed or date.min) > (cur["_filed"] or date.min):
            best[qe] = dict(r, _filed=filed)
    out = []
    for qe in sorted(best, reverse=True):
        r = best[qe]
        out.append({"period_end": qe.isoformat(), "label": q_label(pd.Timestamp(qe)),
                    "nature": "Consolidated" if has_cons else "Standalone",
                    "filed": r["_filed"].strftime("%d-%b-%Y") if r["_filed"] else None,
                    "revised": (r.get("type_Sub") or "").lower().startswith("revis"), "xbrl": r["xbrl"]})
    return out


def promoter_trend(rows: list[dict]) -> list[dict]:
    """Promoter holding by quarter from the NSE shareholding master list, oldest first."""
    out = {}
    for r in rows or []:
        d, v = _d(r.get("date")), num(r.get("pr_and_prgrp"))
        if d and v is not None:
            out[d] = v
    return [{"date": d.strftime("%d-%b-%Y"), "promoter": out[d]} for d in sorted(out)][-5:]


# ---------------------------------------------------------------- merge with Yahoo

def to_yahoo_rows(rec: dict) -> dict:
    """Map a parsed filing to the Yahoo row names the fundamentals module reads.

    EBITDA follows Yahoo's definition (PBT + finance costs + depreciation, so it still includes
    other income and exceptional items); fundamentals then removes both. Minority interest is
    negative, as in Yahoo. For banks, revenue is total income, net interest income is interest
    earned less interest expended, and other income is left out because fee income is core
    income for a bank (Yahoo leaves it out too).
    """
    fc, dep, pbt = rec.get("finance_costs"), rec.get("depreciation"), rec.get("pbt")
    minority = -rec["minority"] if rec.get("minority") is not None else None
    if rec.get("is_bank"):
        ie, ix = rec.get("interest_earned"), rec.get("interest_expended")
        return {
            "Total Revenue": rec.get("total_income"),
            "Operating Revenue": rec.get("total_income"),
            "Net Interest Income": ie - ix if ie is not None and ix is not None else None,
            "Total Unusual Items": rec.get("exceptional"),
            "Pretax Income": pbt,
            "Tax Provision": rec.get("tax"),
            "Net Income Common Stockholders": rec.get("pat"),
            "Net Income Including Noncontrolling Interests": rec.get("pat_total"),
            "Minority Interests": minority,
        }
    ebitda = pbt + (fc or 0) + (dep or 0) if pbt is not None else None
    return {
        "Total Revenue": rec.get("revenue"),
        "Operating Revenue": rec.get("revenue"),
        "EBITDA": ebitda,
        "EBIT": pbt + (fc or 0) if pbt is not None else None,
        "Reconciled Depreciation": dep,
        "Interest Expense": fc,
        "Other Non Operating Income Expenses": rec.get("other_income"),
        "Total Unusual Items": rec.get("exceptional"),
        "Pretax Income": pbt,
        "Tax Provision": rec.get("tax"),
        "Net Income Common Stockholders": rec.get("pat"),
        "Net Income Including Noncontrolling Interests": rec.get("pat_total"),
        "Minority Interests": minority,
    }


def _match(columns, when: pd.Timestamp, tol: int = 20):
    for c in columns:
        try:
            if abs((pd.Timestamp(c) - when).days) <= tol:
                return c
        except Exception:
            continue
    return None


def _yahoo_value(df: pd.DataFrame, names: tuple[str, ...], col) -> float | None:
    for n in names:
        if n in df.index:
            v = num(df.at[n, col])
            if v is not None:
                return v
    return None


def cross_check(q_income: pd.DataFrame, records: list[dict], fx: float = 1.0) -> list[str]:
    """Notes where Yahoo's figure for a quarter differs from the exchange filing.

    Skipped when Yahoo reports in another currency (converting at today's rate would show
    differences that are only exchange rate moves). Bank revenue is not compared because Yahoo
    and the filing define it differently.
    """
    notes = []
    if q_income is None or q_income.empty or fx != 1.0:
        return notes
    for rec in records:
        col = _match(q_income.columns, pd.Timestamp(rec["period_end"]))
        if col is None:
            continue
        checks = [("net profit to owners", ("Net Income Common Stockholders", "Net Income"), "pat", PAT_TOLERANCE)]
        if not rec.get("is_bank"):
            checks.insert(0, ("revenue", ("Total Revenue", "Operating Revenue"), "revenue", REVENUE_TOLERANCE))
        for lab, names, key, tol in checks:
            y, e = _yahoo_value(q_income, names, col), rec.get(key)
            if y is None or e is None or e == 0:
                continue
            if abs(y / e - 1) > tol and abs(y - e) >= 1e7:
                notes.append(f"{rec['label']} {lab}: Yahoo Rs {y / 1e7:,.2f} cr, NSE filing Rs {e / 1e7:,.2f} cr "
                             f"({(y / e - 1) * 100:+.1f}%); the filing figure is used.")
    return notes


def merge_quarters(q_income: pd.DataFrame, records: list[dict], fx: float = 1.0) -> tuple[pd.DataFrame, dict]:
    """Quarterly frame with the filing figures in place of (or added to) Yahoo's columns.

    Returns the new frame and {period end (YYYY-MM-DD): source label} for the quarters taken
    from filings. Yahoo values are in the statement currency, so filings (always INR) are
    divided by fx to keep the frame in one currency.
    """
    df = q_income.copy() if q_income is not None and not q_income.empty else pd.DataFrame()
    sources = {}
    for rec in records:
        when = pd.Timestamp(rec["period_end"])
        col = _match(df.columns, when) if not df.empty else None
        if col is not None:
            df = df.drop(columns=[col])
        rows = {k: (v / fx if v is not None else None) for k, v in to_yahoo_rows(rec).items()}
        add = pd.Series(rows, name=when, dtype=float)
        df = add.to_frame() if df.empty else df.join(add, how="outer")
        sources[when.strftime("%Y-%m-%d")] = f"NSE filing ({(rec.get('nature') or 'consolidated').lower()})"
    if not df.empty:
        df = df[sorted(df.columns, key=pd.Timestamp, reverse=True)]
    return df, sources


# ---------------------------------------------------------------- fetch

@dataclass
class ExchangeData:
    source: str = ""                      # "NSE", "BSE" or "" when nothing was retrieved
    filings: list[dict] = field(default_factory=list)   # newest first, one per quarter
    quarters: list[dict] = field(default_factory=list)  # parsed results, oldest first
    meetings: dict = field(default_factory=lambda: {"last": None, "next": None})
    shareholding: dict | None = None
    bse_code: str | None = None
    links: list[dict] = field(default_factory=list)     # filings used, for the sources list
    warnings: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def checked(self) -> bool:
        """True when the exchange answered the results-date question."""
        return bool(self.filings) or self.meetings.get("last") is not None or self.meetings.get("next") is not None


def _try(label: str, fn, out: ExchangeData, default=None):
    try:
        return fn()
    except Exception as exc:
        out.failed.append(label)
        out.warnings.append(f"Exchange data: {label} not available ({str(exc)[:60] or type(exc).__name__}).")
        return default


def fetch(yahoo_symbol: str, today: date, client: _Client | None = None) -> ExchangeData:
    out = ExchangeData()
    if not enabled():
        return out
    client = client or _Client()
    base, suffix = (yahoo_symbol.rsplit(".", 1) + [""])[:2]
    if suffix.upper() == "NS":
        _fetch_nse(base, today, client, out)
    if not out.checked:
        code = out.bse_code or (base if re.fullmatch(r"\d{6}", base) else None) or _bse_code(base, client, out)
        if code:
            _fetch_bse_dates(code, today, client, out)
    return out


def _bse_code(symbol: str, client: _Client, out: ExchangeData) -> str | None:
    html = _try("BSE code lookup", lambda: client.get(BSE_HOME, BSE_API + "PeerSmartSearch/w",
                                                      params={"Type": "SS", "text": symbol}, json=False), out)
    for code, sym in re.findall(r"liclick\('(\d{6})'.*?<span>(?:<strong>)?([A-Z0-9&-]+)", html or "", re.S):
        if sym == symbol.upper():
            return code
    return None


def _fetch_nse(symbol: str, today: date, client: _Client, out: ExchangeData) -> None:
    def api(path, **params):
        return client.get(NSE_HOME, NSE_API + path, params=params)

    meet = _try("NSE board meetings", lambda: api("corporate-board-meetings", index="equities", symbol=symbol),
                out, [])
    out.meetings = results_meetings(meet if isinstance(meet, list) else [], today)

    listing = _try("NSE results filings", lambda: api("integrated-filing-results", index="equities", symbol=symbol,
                                                      period_ended="all", type="Integrated Filing- Financials"),
                   out, {})
    rows = listing.get("data", []) if isinstance(listing, dict) else listing or []
    out.filings = pick_filings(rows)
    for f in out.filings[:MAX_QUARTERS]:
        text = _try(f"NSE results XBRL {f['label']}", lambda u=f["xbrl"]: client.get(NSE_HOME, u, json=False), out)
        rec = parse_results_xbrl(text) if text else None
        if rec is None:
            if text:
                out.warnings.append(f"Exchange data: the {f['label']} results XBRL could not be read.")
            continue
        rec.update(filed=f["filed"], url=f["xbrl"], nature=rec.get("nature") or f["nature"])
        out.quarters.append(rec)
        out.links.append({"title": f"NSE results filing, {f['label']} ({f['nature'].lower()})", "url": f["xbrl"],
                          "date": f["filed"]})
        if not out.bse_code and text:
            m = re.search(r'ScripCode">\s*(\d{6})\s*<', text)
            out.bse_code = m.group(1) if m else None
    out.quarters.sort(key=lambda r: r["period_end"])

    master = _try("NSE shareholding pattern", lambda: api("corporate-share-holdings-master", index="equities",
                                                          symbol=symbol), out, [])
    master = master if isinstance(master, list) else []
    if master:
        latest = max(master, key=lambda r: _d(r.get("date")) or date.min)
        text = _try("NSE shareholding XBRL", lambda: client.get(NSE_HOME, latest["xbrl"], json=False), out) \
            if latest.get("xbrl") else None
        sh = parse_shareholding_xbrl(text) if text else None
        if sh is None:  # the master row still gives the promoter and public split
            sh = {"as_of": None, "promoter": num(latest.get("pr_and_prgrp")), "public": num(latest.get("public_val")),
                  "fii": None, "dii": None, "mutual_funds": None, "public_other": num(latest.get("public_val")),
                  "pledge_reported": None, "pledged_pct_of_promoter": None, "encumbered_pct_of_promoter": None}
        if sh.get("promoter") is None:  # no promoter group (for example HDFC Bank) is reported as 0
            sh["promoter"] = num(latest.get("pr_and_prgrp"))
        d = _d(latest.get("date"))
        sh["as_of"] = d.strftime("%d-%b-%Y") if d else sh.get("as_of")
        sh["promoter_trend"] = promoter_trend(master)
        sh["source"] = "NSE shareholding pattern"
        out.shareholding = sh
        if latest.get("xbrl"):
            out.links.append({"title": f"NSE shareholding pattern, {sh['as_of']}", "url": latest["xbrl"],
                              "date": (latest.get("broadcastDate") or "")[:11].title() or None})
    if out.filings or out.meetings["last"] or out.shareholding:
        out.source = "NSE"


def _fetch_bse_dates(code: str, today: date, client: _Client, out: ExchangeData) -> None:
    """Fallback: date of the latest results announcement on BSE (no figures)."""
    start = (today - timedelta(days=120)).strftime("%Y%m%d")
    res = _try("BSE results announcements", lambda: client.get(
        BSE_HOME, BSE_API + "AnnSubCategoryGetData/w",
        params={"pageno": 1, "strCat": "Result", "strPrevDate": start, "strScrip": code, "strSearch": "P",
                "strToDate": today.strftime("%Y%m%d"), "strType": "C", "subcategory": -1}), out, {})
    dates = [_d((r.get("NEWS_DT") or "")[:19]) for r in (res or {}).get("Table", [])]
    dates = [d for d in dates if d]
    if dates:
        d = max(dates)
        qe = quarter_end_before(d)
        out.meetings["last"] = {"date": d.strftime("%d-%b-%Y"), "quarter_end": qe.isoformat(),
                                "quarter": q_label(pd.Timestamp(qe)), "via": "BSE results announcement"}
        out.source = out.source or "BSE"
        out.bse_code = code
