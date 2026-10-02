"""
LookThrough v3 - independent reference engine (pandas / numpy).

Control purpose: the browser app computes every figure in JavaScript. This
script recomputes the same metrics from data/live/dataset.json, written
separately, so the two engines can be reconciled (verify/reconcile_app.js).

Real data is incomplete (new listings, missing statements, schemes without an
AMC portfolio file), so every metric that cannot be computed is None here and
null in the app; the reconciliation checks that both engines agree on that too.

Usage:  python recompute.py [dataset.json]   ->  verify/reference_metrics.json

Also importable (the MCP server does this): set LOOKTHROUGH_DATASET to choose the
dataset; the module then exposes H, look_through(), conc(), fund, overlap, RAT,
tax, stress_market() and ref without writing anything.
"""
import calendar
import json
import math
import os
import sys
from datetime import date
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
# a fresh clone has no data/live: the committed 31-Aug-2026 snapshot is used (see data/snapshot/_README.txt)
_LIVE = HERE.parent / "data" / "live" / "dataset.json"
SRC = Path(sys.argv[1] if __name__ == "__main__" and len(sys.argv) > 1
           else os.environ.get("LOOKTHROUGH_DATASET") or (_LIVE if _LIVE.exists() else HERE.parent / "data" / "snapshot" / "dataset.json"))
DS = json.loads(SRC.read_text(encoding="utf-8"))
POL, META = DS["policy"], DS["meta"]
AS_ON, DATES = META["as_on"], META["dates"]
T = len(DATES) - 1
RF = POL["risk_free_pct"] / 100
NAN = float("nan")


def num(v):
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def clean(v):
    """JSON-safe: NaN / inf -> None, numpy -> python."""
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, (np.floating, float)):
        return None if not np.isfinite(v) else float(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def d(s):
    return date.fromisoformat(s)


def add_months(dt, n):
    y, m = divmod(dt.month - 1 + n, 12)
    y += dt.year
    m += 1
    return date(y, m, min(dt.day, calendar.monthrange(y, m)[1]))


def is_lt(buy, on):
    return add_months(d(buy), POL["lt_months"]) < d(on)


ELSS = {s["scheme_id"] for s in DS["schemes"] if s.get("category") == "ELSS"}


def is_locked(asset, inst, buy, on):
    """ELSS units are locked in for three years from each allotment (redeemable from the third anniversary)."""
    return asset == "MF" and inst in ELSS and add_months(d(buy), 36) > d(on)


def xirr(flows):
    if not flows:
        return None
    t0 = min(d(x[0]) for x in flows)
    ts = [((d(a) - t0).days / 365.0, v) for a, v in flows]

    def npv(r):
        return sum(v / (1 + r) ** t for t, v in ts)

    # A rate is only published if the NPV at that rate is actually ~0 (same rule as the app engine).
    tol = 1e-7 * sum(abs(v) for _, v in ts)

    def root(x):
        return x if abs(npv(x)) <= tol else None

    lo, hi = -0.9999, 10.0
    if npv(lo) * npv(hi) > 0:
        return None
    r = 0.1
    for _ in range(100):
        f = npv(r)
        df = sum(-t * v / (1 + r) ** (t + 1) for t, v in ts)
        if df == 0:
            break
        nr = r - f / df
        if not (lo < nr < hi):
            break
        if abs(nr - r) < 1e-10 and root(nr) is not None:
            return nr
        r = nr
    for _ in range(300):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return root((lo + hi) / 2)


# ---------------------------------------------------------------- aligned monthly series (NaN = missing)
def series(rows, key_cols, val):
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(index=DATES)
    df = df[df.date.isin(DATES)]
    df["k"] = df[key_cols].astype(str).agg("|".join, axis=1) if isinstance(key_cols, list) else df[key_cols]
    return df.pivot_table(index="date", columns="k", values=val, aggfunc="last").reindex(DATES).astype(float)


PX = series(DS["prices"], "code", "close")
NAV = series(DS["nav_history"], ["scheme_id", "plan"], "nav")
IDX = series(DS["indices"], "index_code", "level")
MKT_CODE = "NIFTY500" if "NIFTY500" in IDX else "NIFTY50" if "NIFTY50" in IDX else (IDX.columns[0] if len(IDX.columns) else None)
MKT = IDX[MKT_CODE].values if MKT_CODE else None
COS = {c["code"]: c for c in DS["companies"]}
SCH = {s["scheme_id"]: s for s in DS["schemes"]}
MEMBERS = [m["member_id"] for m in DS["members"]]


def arr(frame, key):
    return frame[key].values if key in frame else None


def paired(a, b):
    """Month-on-month returns where both series have both ends."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = ~np.isnan(a[1:]) & ~np.isnan(a[:-1]) & ~np.isnan(b[1:]) & ~np.isnan(b[:-1])
    x = a[1:] / a[:-1] - 1
    y = b[1:] / b[:-1] - 1
    return x[ok], y[ok]


# ---------------------------------------------------------------- FIFO holdings
def cur_price(at, inst, plan):
    a = arr(NAV, f"{inst}|{plan}") if at == "MF" else arr(PX, inst)
    return None if a is None or np.isnan(a[T]) else float(a[T])


tx = pd.DataFrame(DS["transactions"])
tx["plan"] = tx["plan"].fillna("")
tx = tx.sort_values(["date", "txn_id"], kind="mergesort")
holdings, realised = [], []
for key, g in tx.groupby(["member_id", "asset_type", "instrument", "plan"], sort=True):
    lots, flows = [], []
    for r in g.itertuples():
        if r.txn_type == "Sell":
            q = r.units
            flows.append((r.date, r.amount))
            while q > 1e-9 and lots:
                lot = lots[0]
                take = min(q, lot[1])
                realised.append(dict(member_id=key[0], sell_date=r.date, gain=take * (r.price - lot[2]),
                                     term="LT" if is_lt(lot[0], r.date) else "ST"))
                lot[1] -= take
                q -= take
                if lot[1] <= 1e-9:
                    lots.pop(0)
        else:
            lots.append([r.date, r.units, r.price])
            flows.append((r.date, -r.amount))
    if not lots:
        continue
    cp = cur_price(key[1], key[2], key[3])
    if cp is None:
        continue
    units = sum(l[1] for l in lots)
    cost = sum(l[1] * l[2] for l in lots)
    value = units * cp
    holdings.append(dict(member_id=key[0], asset_type=key[1], instrument=key[2], plan=key[3], units=units, cost=cost, value=value,
                         unrealised=value - cost,
                         lt_gain=sum(l[1] * (cp - l[2]) for l in lots if is_lt(l[0], AS_ON)),
                         st_gain=sum(l[1] * (cp - l[2]) for l in lots if not is_lt(l[0], AS_ON)),
                         locked_value=sum(l[1] * cp for l in lots if is_locked(key[1], key[2], l[0], AS_ON)),
                         locked_lt=sum(l[1] * (cp - l[2]) for l in lots if is_locked(key[1], key[2], l[0], AS_ON) and is_lt(l[0], AS_ON)),
                         locked_st=sum(l[1] * (cp - l[2]) for l in lots if is_locked(key[1], key[2], l[0], AS_ON) and not is_lt(l[0], AS_ON)),
                         xirr=xirr(flows + [(AS_ON, value)])))
H = pd.DataFrame(holdings)
R = pd.DataFrame(realised, columns=["member_id", "sell_date", "gain", "term"])


def xirr_for(mask, value):
    f = [(r.date, r.amount if r.txn_type == "Sell" else -r.amount) for r in tx[mask].itertuples()]
    return xirr(f + [(AS_ON, value)])


member_x = {m: xirr_for(tx.member_id == m, H[H.member_id == m].value.sum()) for m in MEMBERS}
family_x = xirr_for(tx.member_id.notna(), H.value.sum())

# ---------------------------------------------------------------- tax (indicative, current tax year)
RY = R[R.sell_date >= POL["tax_year_start"]]
tax = {}
for m in MEMBERS:
    h, rl = H[H.member_id == m], RY[RY.member_id == m]
    r_st, r_lt = float(rl[rl.term == "ST"].gain.sum()), float(rl[rl.term == "LT"].gain.sum())
    st, lt = float(h.st_gain.sum()), float(h.lt_gain.sum())
    lk_st, lk_lt = float(h.locked_st.sum()), float(h.locked_lt.sum())
    tot_st, tot_lt = st - lk_st + r_st, lt - lk_lt + r_lt   # "if sold" = sellable units only (ELSS lock-in excluded)
    if tot_st < 0:                      # ST loss may be set off against LT gain; not vice versa
        tot_lt += tot_st
        tot_st = 0.0
    taxable_lt = max(0.0, tot_lt - POL["ltcg_exemption"])
    net_realised_lt = r_lt + min(0.0, r_st)                    # after mandatory set-off of realised losses
    room = max(0.0, POL["ltcg_exemption"] - net_realised_lt)    # tax-free gain room; can exceed the exemption
    tax[m] = dict(realised_st=r_st, realised_lt=r_lt, unrealised_st=st, unrealised_lt=lt, locked_value=float(h.locked_value.sum()),
                  tax_if_all_sold=tot_st * POL["stcg_rate_pct"] / 100 + taxable_lt * POL["ltcg_rate_pct"] / 100,
                  exemption_left=max(0.0, POL["ltcg_exemption"] - max(0.0, net_realised_lt)),
                  harvest_headroom=min(room, max(0.0, lt - lk_lt)))

# ---------------------------------------------------------------- scheme portfolios: each scheme's own latest / previous month
SP = pd.DataFrame(DS["scheme_portfolios"], columns=None if DS["scheme_portfolios"] else ["scheme_id", "portfolio_date", "code", "weight_pct"])
SP = SP[SP.portfolio_date <= AS_ON]  # no AMC files applied yet -> empty frame, every scheme unmapped
PORT_DATES = {s: sorted(g.portfolio_date.unique()) for s, g in SP.groupby("scheme_id")}


def port(sid, back=0):
    ds = PORT_DATES.get(sid, [])
    if len(ds) <= back:
        return None
    g = SP[(SP.scheme_id == sid) & (SP.portfolio_date == ds[-1 - back])]
    return g.groupby("code").weight_pct.sum()


LATEST = {s: port(s) for s in PORT_DATES}


def look_through(member=None):
    h = H if member is None else H[H.member_id == member]
    mf, eq = h[h.asset_type == "MF"], h[h.asset_type == "EQ"]
    agg = mf.groupby("instrument").value.sum()
    parts, debt, cash, unmapped = [], 0.0, 0.0, 0.0
    for sid, v in agg.items():
        w = LATEST.get(sid)
        if w is None:
            unmapped += v
            continue
        s = SCH[sid]
        dv = v * (s.get("debt_pct") or 0) / 100
        debt += dv
        cash += v - v * w.sum() / 100 - dv          # cash & other = balancing residual
        parts.append((w * v / 100).rename("via"))
    via = pd.concat(parts).groupby(level=0).sum() if parts else pd.Series(dtype=float, name="via")
    direct = eq.groupby("instrument").value.sum().rename("direct")
    lt = pd.concat([direct, via.rename("via")], axis=1).fillna(0)
    lt["total"] = lt.direct + lt.via
    lt = lt[lt.total > 0].sort_values("total", ascending=False, kind="mergesort")
    return lt, debt, cash, unmapped, float(mf.value.sum()), float(eq.value.sum())


def conc(lt):
    if lt.empty:
        return dict(equity=0.0, hhi=None, eff_n=None, top10=None, top_pct=None, n=0)
    w = lt.total / lt.total.sum()
    hhi = float((w ** 2).sum())
    return dict(equity=float(lt.total.sum()), hhi=hhi, eff_n=1 / hhi, top10=float(w.head(10).sum() * 100),
                top_pct=float(w.iloc[0] * 100), n=int(len(lt)))


def co_field(code, field):
    v = (COS.get(code) or {}).get(field)
    return v if v else ("Unclassified" if field == "cap" else "Others")


# ---------------------------------------------------------------- stock analytics
stock_beta, stock_1y = {}, {}
for c in PX.columns:
    p = PX[c].values
    if np.isnan(p[T]) or MKT is None:
        continue
    x, y = paired(p, MKT)
    stock_beta[c] = float(np.cov(x, y, ddof=1)[0, 1] / np.var(y, ddof=1)) if len(x) > 12 else None
    stock_1y[c] = float(p[T] / p[T - 12] - 1) if not np.isnan(p[T - 12]) else None


def beta_or_1(c):
    b = stock_beta.get(c)
    return 1.0 if b is None else b


def port_beta(lt):
    if lt.empty:
        return None
    w = lt.total / lt.total.sum()
    return float(sum(w[c] * beta_or_1(c) for c in w.index))


# ---------------------------------------------------------------- fund analytics (Direct plan)
rf_m = (1 + RF) ** (1 / 12) - 1
fund = {}
for sid, s in SCH.items():
    n = arr(NAV, f"{sid}|Direct")
    if n is None or np.isnan(n[T]):
        continue
    bn = arr(IDX, s.get("benchmark")) if s.get("benchmark") in IDX else MKT
    full = not np.isnan(n[0]) and bn is not None and not np.isnan(bn[0]) and not np.isnan(bn[T])
    cagr = (n[T] / n[0]) ** (1 / 3) - 1 if not np.isnan(n[0]) else None
    bcagr = (bn[T] / bn[0]) ** (1 / 3) - 1 if full else None
    r, br = paired(n, bn) if bn is not None else (np.array([]), np.array([]))
    enough = len(r) > 12
    vol = float(np.std(r, ddof=1) * math.sqrt(12)) if enough else None
    dd = float(math.sqrt(np.mean(np.minimum(0, r - rf_m) ** 2)) * math.sqrt(12)) if enough else None
    beta = float(np.cov(r, br, ddof=1)[0, 1] / np.var(br, ddof=1)) if enough else None
    te = float(np.std(r - br, ddof=1) * math.sqrt(12)) if enough else None
    nn = n[~np.isnan(n)]
    mdd = float(np.max(1 - nn / np.maximum.accumulate(nn)))
    beats = []
    for t in range(12, T + 1):
        if bn is None:
            break
        if not any(np.isnan([n[t], n[t - 12], bn[t], bn[t - 12]])):
            beats.append((n[t] / n[t - 12] - 1) > (bn[t] / bn[t - 12] - 1))
    up, dn = br > 0, br < 0
    fund[sid] = dict(
        r1y=float(n[T] / n[T - 12] - 1) if not np.isnan(n[T - 12]) else None, cagr3=cagr, bench3=bcagr, vol=vol,
        sharpe=(cagr - RF) / vol if cagr is not None and vol else None,
        sortino=(cagr - RF) / dd if cagr is not None and dd else None, mdd=mdd, beta=beta,
        alpha=cagr - (RF + beta * (bcagr - RF)) if None not in (cagr, bcagr, beta) else None, te=te,
        ir=(cagr - bcagr) / te if None not in (cagr, bcagr) and te else None,
        up_capture=float(r[up].mean() / br[up].mean()) if up.any() else None,
        down_capture=float(r[dn].mean() / br[dn].mean()) if dn.any() else None,
        roll_beat=float(np.mean(beats)) if beats else None)

corr = {}
fids = sorted(fund)
for a, b in combinations(fids, 2):
    x, y = paired(NAV[f"{a}|Direct"].values, NAV[f"{b}|Direct"].values)
    corr[f"{a}|{b}"] = float(np.corrcoef(x, y)[0, 1]) if len(x) > 12 else None

# ---------------------------------------------------------------- overlap and month-on-month activity
ids = sorted(SCH)
overlap = {}
for a, b in combinations(ids, 2):
    wa, wb = LATEST.get(a), LATEST.get(b)
    if wa is None or wb is None:
        overlap[f"{a}|{b}"] = None
        continue
    common = wa.index.intersection(wb.index)
    overlap[f"{a}|{b}"] = float(np.minimum(wa[common], wb[common]).sum())

act, cons = {}, {}
for sid in ids:
    L, P = port(sid, 0), port(sid, 1)
    if L is None or P is None:
        act[sid] = None
        continue
    allc = L.index.union(P.index)
    a, p = L.reindex(allc, fill_value=0), P.reindex(allc, fill_value=0)
    # active change = actual weight - passive weight, passive = prev x (1 + stock return) / (1 + fund return)
    i0, i1 = DATES.index(PORT_DATES[sid][-2]), DATES.index(PORT_DATES[sid][-1])

    def ret(series):
        if series is None or np.isnan(series[i0]) or np.isnan(series[i1]) or not series[i0]:
            return None
        return series[i1] / series[i0] - 1

    rf = ret(arr(NAV, f"{sid}|Direct"))
    rf = 0.0 if rf is None else rf
    passive = pd.Series({c: p[c] * (1 + (ret(arr(PX, c)) if ret(arr(PX, c)) is not None else rf)) / (1 + rf) for c in allc})
    dw = a - passive
    act[sid] = dict(entries=int(((a > 0) & (p == 0)).sum()), exits=int(((a == 0) & (p > 0)).sum()), turnover=float(dw.abs().sum() / 2))
    for c in allc:
        x = cons.setdefault(c, dict(adding=0, reducing=0, holders=0, net_w=0.0))
        x["adding"] += int(dw[c] > 0.25)
        x["reducing"] += int(dw[c] < -0.25)
        x["holders"] += int(a[c] > 0)
        x["net_w"] += float(dw[c])

# ---------------------------------------------------------------- company ratios (null-tolerant)
FIN = pd.DataFrame(DS["financials"])


def g_(row, k):
    v = row.get(k) if isinstance(row, dict) else None
    return v if num(v) else None


def div(a, b):
    return a / b if a is not None and b is not None and b != 0 else None


def cagr_pct(a, b, yrs):
    return ((a / b) ** (1 / yrs) - 1) * 100 if a is not None and b is not None and a > 0 and b > 0 else None


def avg2(a, b):
    return (a + b) / 2 if a is not None and b is not None else a


def ratios(code):
    c = COS.get(code)
    rows = sorted(FIN[FIN.code == code].to_dict("records"), key=lambda r: r["fy"]) if len(FIN) else []
    if c is None or len(rows) < 2:
        return None
    n, t, p = len(rows), rows[-1], rows[-2]
    q = rows[-3] if n >= 3 else None
    G = lambda r, k: g_(r, k)  # noqa: E731
    price, shares = c.get("price") if num(c.get("price")) else None, c.get("shares_cr") or G(t, "shares_cr")
    avg_nw, avg_ta = avg2(G(t, "net_worth"), G(p, "net_worth")), avg2(G(t, "total_assets"), G(p, "total_assets"))
    pat, rev, nw = G(t, "pat"), G(t, "revenue"), G(t, "net_worth")
    eps = div(pat, shares)
    o = dict(roe=div(pat, avg_nw) * 100 if div(pat, avg_nw) is not None else None,
             roa=div(pat, avg_ta) * 100 if div(pat, avg_ta) is not None else None,
             pe=price / eps if price is not None and eps is not None and eps > 0 else None,
             pb=price / (nw / shares) if price is not None and nw is not None and nw > 0 and shares else None,
             rev_cagr3=cagr_pct(rev, G(rows[n - 4], "revenue"), 3) if n >= 4 else None,
             pat_cagr3=cagr_pct(pat, G(rows[n - 4], "pat"), 3) if n >= 4 else None,
             rev_cagr5=cagr_pct(rev, G(rows[n - 6], "revenue"), 5) if n >= 6 else None,
             div_yield=G(t, "dividend_ps") / price * 100 if G(t, "dividend_ps") is not None and price else None)
    if not c.get("is_financial"):
        pbt, intr, debt = G(t, "pbt"), G(t, "interest"), G(t, "total_debt")
        ebit = pbt + intr if pbt is not None and intr is not None else None
        ce = lambda r: G(r, "net_worth") + (G(r, "total_debt") or 0) if G(r, "net_worth") is not None else None  # noqa: E731
        avg_ce = avg2(ce(t), ce(p))
        cfo, capex, ebitda, mcap = G(t, "cfo"), G(t, "capex"), G(t, "ebitda"), c.get("mcap_cr") if num(c.get("mcap_cr")) else None
        o.update(roce=div(ebit, avg_ce) * 100 if div(ebit, avg_ce) is not None else None,
                 de=debt / nw if debt is not None and nw is not None and nw > 0 else None,
                 int_cover=ebit / intr if ebit is not None and intr is not None and intr > 0 else None,
                 current_ratio=div(G(t, "current_assets"), G(t, "current_liabilities")),
                 ev_ebitda=(mcap + (debt or 0) - (G(t, "cash_eq") or 0)) / ebitda if mcap is not None and ebitda is not None and ebitda > 0 else None,
                 fcf_yield=(cfo - capex) / mcap * 100 if cfo is not None and capex is not None and mcap else None,
                 cfo_pat=div(cfo, pat) if pat is not None and pat > 0 else None,
                 dupont_margin=pat / rev * 100 if div(pat, rev) is not None else None,
                 dupont_turnover=div(rev, avg_ta), dupont_leverage=div(avg_ta, avg_nw))
        if q is not None:
            def cmp(a, b, f):
                return None if a is None or b is None else f(a, b)
            roa_t, roa_p = div(pat, G(p, "total_assets")), div(G(p, "pat"), G(q, "total_assets"))
            tests = [
                None if roa_t is None else roa_t > 0,
                None if cfo is None else cfo > 0,
                cmp(roa_t, roa_p, lambda a, b: a > b),
                cmp(cfo, pat, lambda a, b: a > b),
                cmp(div(debt or 0, G(t, "total_assets")), div(G(p, "total_debt") or 0, G(p, "total_assets")), lambda a, b: a <= b),
                cmp(div(G(t, "current_assets"), G(t, "current_liabilities")), div(G(p, "current_assets"), G(p, "current_liabilities")), lambda a, b: a > b),
                cmp(G(t, "shares_cr"), G(p, "shares_cr"), lambda a, b: a <= b * 1.001),
                cmp(div(ebitda, rev), div(G(p, "ebitda"), G(p, "revenue")), lambda a, b: a > b),
                cmp(div(rev, G(p, "total_assets")), div(G(p, "revenue"), G(q, "total_assets")), lambda a, b: a > b),
            ]
            known = [x for x in tests if x is not None]
            o["fscore"] = sum(known) if len(known) >= 7 else None
    else:
        for k in ("gnpa_pct", "nnpa_pct", "car_pct", "nim_pct"):
            if G(t, k) is not None:
                o[k.replace("_pct", "")] = float(G(t, k))
    return o


RAT = {c: ratios(c) for c in COS}

# ---------------------------------------------------------------- weighted TER, implied Regular-Direct gap
def implied_gap(sid):
    dn, rn = arr(NAV, f"{sid}|Direct"), arr(NAV, f"{sid}|Regular")
    if dn is None or rn is None or np.isnan([dn[T], dn[T - 12], rn[T], rn[T - 12]]).any():
        return None
    return ((dn[T] / dn[T - 12]) / (rn[T] / rn[T - 12]) - 1) * 100


MFH = H[H.asset_type == "MF"]


def ter(r):
    v = SCH[r.instrument].get("ter_regular" if r.plan == "Regular" else "ter_direct")
    return v if num(v) else None


ters = [ter(r) for r in MFH.itertuples()]
weighted_ter = None if not len(MFH) or any(t is None for t in ters) else float(sum(r.value * t for r, t in zip(MFH.itertuples(), ters)) / MFH.value.sum())
direct_saving = float(sum(r.value * (implied_gap(r.instrument) or 0) / 100 for r in MFH[MFH.plan == "Regular"].itertuples()))

# ---------------------------------------------------------------- stress (beta 1 where no history; market move where no price)
lt_all, debt_all, cash_all, unmapped_all, mf_all, eq_all = look_through()


def stress_market(shock):
    # funds without a portfolio file: fully equity at beta 1 (same assumption as the app)
    # a share cannot lose more than its whole value: beta x move is floored at -100% (same rule as the app)
    return float(sum(lt_all.total[c] * max(-1.0, beta_or_1(c) * shock) for c in lt_all.index) + unmapped_all * max(-1.0, shock))


def stress_sector(sector, shock):
    return float(sum(lt_all.total[c] * shock for c in lt_all.index if (COS.get(c) or {}).get("sector") == sector))


def stress_hist(t0, t1):
    tot = 0.0
    for c in lt_all.index:
        p = arr(PX, c)
        if p is not None and not np.isnan(p[t0]) and not np.isnan(p[t1]):
            tot += lt_all.total[c] * (p[t1] / p[t0] - 1)
        elif MKT is not None:
            tot += lt_all.total[c] * (MKT[t1] / MKT[t0] - 1)
    if MKT is not None:
        tot += unmapped_all * (MKT[t1] / MKT[t0] - 1)
    return float(tot)


sectors = {}
for c, v in lt_all.total.items():
    k = co_field(c, "sector")
    sectors[k] = sectors.get(k, 0.0) + v
sectors = {k: v / lt_all.total.sum() * 100 for k, v in sectors.items()}

ref = dict(
    holdings={f"{r.member_id}|{r.asset_type}|{r.instrument}|{r.plan}": dict(units=r.units, cost=r.cost, value=r.value, unrealised=r.unrealised,
                                                                              lt_gain=r.lt_gain, st_gain=r.st_gain, xirr=r.xirr) for r in H.itertuples()},
    realised_count=len(R), realised_gain_total=float(R.gain.sum()) if len(R) else 0.0,
    member_xirr=member_x, family_xirr=family_x,
    family=dict(value=float(H.value.sum()), cost=float(H.cost.sum()), mf=mf_all, eq=eq_all, debt_in_funds=debt_all, cash_in_funds=cash_all,
                unmapped=unmapped_all, **conc(lt_all), port_beta=port_beta(lt_all)),
    per_member={m: dict(value=float(H[H.member_id == m].value.sum()), **{k: v for k, v in conc(look_through(m)[0]).items() if k in ("hhi", "top10", "eff_n")}) for m in MEMBERS},
    top10={k: float(v) for k, v in lt_all.total.head(10).items()},
    sectors=sectors, weighted_ter=weighted_ter, direct_switch_saving=direct_saving,
    tax=tax, overlap=overlap, fund=fund, corr=corr, activity=act, consensus=cons,
    stock_beta=stock_beta, stock_1y=stock_1y, ratios={k: v for k, v in RAT.items() if v is not None},
    stress=dict(market_minus20=stress_market(-0.20), fin_minus20=stress_sector("Financial Services", -0.20), hist_correction=stress_hist(13, 18)),
    market_index=MKT_CODE,
)
ref = clean(ref)

if __name__ == "__main__":
    (HERE / "reference_metrics.json").write_text(json.dumps(ref, indent=1))
    f = ref["family"]
    print(f"Source {SRC} | market index {MKT_CODE}")
    print(f"Value {f['value']/1e7:.2f} cr | cost {f['cost']/1e7:.2f} | MF {f['mf']/1e7:.2f} | EQ {f['eq']/1e7:.2f} | unmapped {f['unmapped']/1e7:.2f} | XIRR {family_x*100:.2f}%")
    print(f"HHI {f['hhi']:.4f} EffN {f['eff_n']:.1f} Top10 {f['top10']:.1f}% top {f['top_pct']:.2f}% beta {f['port_beta']:.2f} n={f['n']}")
    print(f"Holdings {len(H)} | realised lots {len(R)} | funds with stats {len(fund)} | companies with ratios {len(ref['ratios'])} | stock betas {sum(v is not None for v in stock_beta.values())}")
