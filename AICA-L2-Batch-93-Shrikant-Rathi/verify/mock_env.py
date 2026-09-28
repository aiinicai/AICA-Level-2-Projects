"""
Offline test environment for the data bridge.

Creates a throw-away copy of the project whose cache is filled with synthetic
responses shaped exactly like the real sources (NSE EQUITY_L.csv, AMFI
NAVAll.txt, mfapi.in JSON, yfinance statements) plus AMC portfolio workbooks in
several real-world layouts. Every figure here is synthetic: this is only used
to test parsing, building and the app, never shipped.

    python verify/mock_env.py <target_dir>
"""
import json
import math
import random
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
DST = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/lt_mock")
if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns(".venv", "__pycache__", "logs", "cache", "live", "amc_portfolios"))
sys.path.insert(0, str(DST / "bridge"))
from common import CACHE, PORTFOLIO_DIR, isin_check_digit_ok, month_ends, now_iso, save_json, valuation_date  # noqa: E402

rnd = random.Random(7)
today = date.today()
uni = json.loads((DST / "data/config/universe.json").read_text())
schemes = json.loads((DST / "data/config/schemes.json").read_text())


def isin(i, sec="01"):
    for chk in range(10):
        s = f"INE{i:03d}A{sec}01{chk}"
        if isin_check_digit_ok(s):
            return s


EXTRA = [(f"MIDCO{i:02d}", f"Midco Industries {i} Limited") for i in range(1, 41)]
rows, sym_isin = [], {}
for i, u in enumerate(uni):
    sym_isin[u["symbol"]] = isin(100 + i)
    rows.append((u["symbol"], u["name"] + " Limited", sym_isin[u["symbol"]]))
for j, (s, n) in enumerate(EXTRA):
    sym_isin[s] = isin(500 + j)
    rows.append((s, n, sym_isin[s]))
CACHE.mkdir(parents=True, exist_ok=True)
with open(CACHE / "nse_equity_list.csv", "w") as f:
    f.write("SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE\n")
    for s, n, i in rows:
        f.write(f'{s},"{n}",EQ,01-JAN-2005,1,1,{i},1\n')

# ---------- daily prices (weekdays) for stocks and indices
start = date(today.year - 4, 1, 1)
days = [start + timedelta(d) for d in range((today - start).days) if (start + timedelta(d)).weekday() < 5]
mkt = [1.0]
for _ in days[1:]:
    mkt.append(mkt[-1] * (1 + rnd.gauss(0.0005, 0.009)))
prices = {}


def path(beta, drift, vol, p_end):
    v = [1.0]
    for k in range(1, len(days)):
        m = mkt[k] / mkt[k - 1] - 1
        v.append(v[-1] * (1 + beta * m + rnd.gauss(drift, vol)))
    sc = p_end / v[-1]
    return [x * sc for x in v]


for s in list(sym_isin):
    tk = s + ".NS"
    pts = path(rnd.uniform(0.6, 1.4), rnd.uniform(-0.0002, 0.0005), rnd.uniform(0.008, 0.02), rnd.uniform(150, 4000))
    if s == "KPITTECH":  # simulate a stock listed only 2 years ago
        pts = [None] * (len(days) - 500) + pts[-500:]
    prices[tk] = {"fetched": now_iso(), "points": [[d.isoformat(), round(p, 2)] for d, p in zip(days, pts) if p is not None]}
for tk, lvl in (("^NSEI", 24500), ("^CRSLDX", 22500), ("^NSEMDCP50", 16000), ("^CNXSC", 18000)):
    pts = path(1.0, 0.00005, 0.002, lvl)
    prices[tk] = {"fetched": now_iso(), "points": [[d.isoformat(), round(p, 2)] for d, p in zip(days, pts)]}
save_json(CACHE / "yahoo_prices.json", prices)
save_json(CACHE / "yahoo_mcap.json", {tk: {"fetched": now_iso(), "market_cap": rnd.uniform(5e10, 1.5e13), "shares": rnd.uniform(1e8, 5e9), "last_price": None, "currency": "INR"} for tk in prices})

# ---------- yfinance-shaped company files (4 fiscal years, rupees)
FIN_SECTOR = {u["symbol"]: u["sector"] for u in uni}
for u in uni:
    s, fin = u["symbol"], u["sector"] == "Financial Services"
    rev0 = rnd.uniform(5e10, 5e12)
    g = rnd.uniform(0.02, 0.2)
    years = []
    for k, fy in enumerate([2022, 2023, 2024, 2025]):
        rev = rev0 * (1 + g) ** k
        pm = rnd.uniform(0.05, 0.2)
        pat = rev * pm
        ta = rev * rnd.uniform(0.8, 1.6) * (8 if fin else 1)
        nw = ta * (0.12 if fin else rnd.uniform(0.35, 0.6))
        y = {"period_end": f"{fy}-03-31", "fy": f"FY{fy - 1}-{str(fy)[2:]}", "revenue": rev, "ebitda": None if fin else pat * 1.7, "depreciation": None if fin else rev * 0.03,
             "interest": rev * (0.4 if fin else 0.01), "pbt": pat / 0.75, "tax": pat / 3, "pat": pat, "total_assets": ta, "net_worth": nw,
             "total_debt": ta * (0.6 if fin else rnd.uniform(0, 0.25)), "cash_eq": ta * 0.05, "current_assets": None if fin else ta * 0.4,
             "current_liabilities": None if fin else ta * 0.25, "cfo": pat * rnd.uniform(0.6, 1.4), "capex": -rev * 0.05, "shares": 1e9}
        if s == "ASTRAL" and k == 0:
            y = {**y, **{kk: None for kk in ("ebitda", "cfo", "current_assets")}}  # patchy data
        years.append(y)
    info = {"longName": u["name"] + " Limited", "sector": "Financial Services" if fin else "Industrials", "industry": u["industry"], "marketCap": None,
            "sharesOutstanding": 1e9, "heldPercentInsiders": rnd.uniform(0.2, 0.7), "heldPercentInstitutions": rnd.uniform(0.1, 0.5), "currency": "INR"}
    if s == "COFORGE":
        years = []  # company with no statements → must surface a warning, not crash
    save_json(CACHE / f"yahoo_co_{s}.NS.json", {"symbol": s, "ticker": s + ".NS", "fetched": now_iso(), "info": info, "years": years,
                                                 "dividends_by_fy": {"FY2024-25": 12.5, "FY2023-24": 10.0}})

# ---------- AMFI NAVAll + mfapi histories
lines = ["Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date", "", "Open Ended Schemes(Equity Scheme - Large Cap Fund)", ""]
code = 120000
for s in schemes:
    lines.append(s["amc"])
    base = s["match_any"][0]
    title = " ".join(w.capitalize() for w in " ".join(base).split()) + (" Fund" if "fund" not in " ".join(base) else "")
    for plan in ("Direct", "Regular"):
        for opt in ("Growth", "IDCW"):
            code += 1
            nm = f"{title} - {plan} Plan - {opt}" if plan == "Direct" else f"{title} - {opt}"
            lines.append(f"{code};INF000A01{code % 1000:03d};-;{nm};100.0;{today.strftime('%d-%b-%Y')}")
            if opt == "Growth":
                nav, data, d0 = 50.0, [], date(today.year - 5, 1, 1)
                for k in range((today - d0).days):
                    d = d0 + timedelta(k)
                    if d.weekday() >= 5:
                        continue
                    nav *= 1 + rnd.gauss(0.0005 - (0.00004 if plan == "Regular" else 0), 0.009)
                    data.append({"date": d.strftime("%d-%m-%Y"), "nav": f"{nav:.4f}"})
                save_json(CACHE / f"mf_nav_{code}.json", {"meta": {"scheme_name": nm, "scheme_code": code}, "data": list(reversed(data)), "status": "SUCCESS"})
    code += 1
    lines.append(f"{code};INF000A01{code % 1000:03d};-;{title} Index Fund - Direct Plan - Growth ETF decoy;10;{today.strftime('%d-%b-%Y')}")
(CACHE / "amfi_navall.txt").write_text("\n".join(lines))

# ---------- AMC portfolio workbooks in varied layouts
import openpyxl  # noqa: E402

as_on = valuation_date()
months = month_ends(as_on, 2)
PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
large = [u["symbol"] for u in uni[:50]]
midsmall = [u["symbol"] for u in uni[50:]] + [s for s, _ in EXTRA]


def holdings_for(sid, cat, m_idx):
    r = random.Random(int(sid[1:]) * 97)
    if cat in ("Mid Cap", "Small Cap"):
        pool = midsmall + r.sample(large, 5)
    elif cat == "Index Fund":
        pool = large[:50]
    else:
        pool = large + r.sample(midsmall, 10)
    picks = r.sample(pool, min(len(pool), 50 if cat == "Index Fund" else 35))
    if sid in ("S01", "S02", "S04", "S06", "S10", "S12") and "HDFCBANK" not in picks:
        picks[0] = "HDFCBANK"
    w = [r.uniform(0.5, 3) ** 2 for _ in picks]
    if "HDFCBANK" in picks:
        w[picks.index("HDFCBANK")] = 30
    eq = 97 if cat != "Aggressive Hybrid" else 70
    tot = sum(w)
    ws = [x / tot * eq for x in w]
    if m_idx == 0:  # previous month: drop one, perturb
        ws = [x * r.uniform(0.9, 1.1) for x in ws]
    return list(zip(picks, ws))


def sheet_rows(sid, name, month, hold, frac=False, split_header=False, debt=True):
    rows = [[f"{name}"], [f"Monthly Portfolio Statement as on {month.strftime('%d %B %Y')}"], []]
    if split_header:
        rows += [["Name of the Instrument", "ISIN", "Industry / Rating", "Quantity", "Market Value (Rs. Lakhs)", "% to"], [None, None, None, None, None, "NAV"]]
    else:
        rows += [["Sr", "Name of the Instrument", "ISIN", "Industry / Rating", "Quantity", "Market value (Rs. in Lakhs)", "% to Net Assets"]]
    rows.append(["Equity & Equity related"])
    for sym, w in hold:
        vals = [sym.title() + " Ltd", sym_isin[sym], "Banks" if FIN_SECTOR.get(sym) == "Financial Services" else "Industrial Products", 1000, round(w * 10, 2), round(w / 100 if frac else w, 6 if frac else 2)]
        rows.append(vals if split_header else [None] + vals)
    tot = sum(w for _, w in hold)
    rows.append(([] if split_header else [None]) + ["Sub Total", None, None, None, None, round(tot / 100 if frac else tot, 4)])
    if debt:
        rows.append(([] if split_header else [None]) + ["7.18% GOI 2033", "IN0020230085", "SOVEREIGN", 10, 1, 1.5 / 100 if frac else 1.5])
        rows.append(([] if split_header else [None]) + ["HDFC Bank NCD 2027", isin(140, "07"), "CRISIL AAA", 10, 1, 0.8 / 100 if frac else 0.8])
        rows.append(([] if split_header else [None]) + ["Alphabet Inc", "US02079K3059", "Foreign Equity", 10, 1, 0.5 / 100 if frac else 0.5])
    rows.append(([] if split_header else [None]) + ["TREPS / Net Receivables", None, None, None, None, 0.7])
    rows.append(([] if split_header else [None]) + ["Grand Total", None, None, None, None, 100])
    return rows


by_amc = {}
for s in schemes:
    by_amc.setdefault(s["amc"], []).append(s)
for m_idx, month in enumerate(months):
    for amc, lst in by_amc.items():
        tag = month.strftime("%b%Y")
        if amc.startswith("ICICI"):  # one workbook, one sheet per scheme (short sheet codes)
            wb = openpyxl.Workbook()
            wb.remove(wb.active)
            ws0 = wb.create_sheet("Index")
            ws0.append(["Scheme code", "Scheme"])
            for s in lst:
                ws = wb.create_sheet(s["scheme_id"] + "X")
                for r in sheet_rows(s["scheme_id"], s["name"].replace("Large Cap Fund", "Bluechip Fund"), month, holdings_for(s["scheme_id"], s["category"], m_idx)):
                    ws.append(r)
            wb.save(PORTFOLIO_DIR / f"ICICI_Monthly_Portfolio_{tag}.xlsx")
        else:
            for s in lst:
                frac = amc.startswith("HDFC")
                split = amc.startswith("Nippon")
                rows = sheet_rows(s["scheme_id"], s["name"], month, holdings_for(s["scheme_id"], s["category"], m_idx), frac=frac, split_header=split)
                if amc.startswith("Mirae"):  # CSV export
                    import csv
                    with open(PORTFOLIO_DIR / f"{s['name'].replace(' ', '_')}_{tag}.csv", "w", newline="") as f:
                        csv.writer(f).writerows(rows)
                    continue
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Portfolio"
                for r in rows:
                    ws.append(r)
                wb.save(PORTFOLIO_DIR / f"{s['name'].replace(' ', '_')}_{tag}.xlsx")
print("mock environment ready at", DST)
