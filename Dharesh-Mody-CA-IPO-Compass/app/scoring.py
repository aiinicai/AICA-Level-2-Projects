"""
Faithful Python port of the scoring engine from CA_IPO_Compass_Standalone.html
so the same weights / verdict logic keep working in the desktop app.
"""
import math

RAW_WEIGHTS = {
    "business": 6, "revenue": 6, "pat": 6, "margin": 5, "cash": 10,
    "workingCapital": 6, "debt": 8, "returns": 5, "structure": 5,
    "valuation": 8, "concentration": 6, "anchor": 6, "qib": 7,
    "demand": 4, "gmp": 6, "gmpTrend": 5, "liquidity": 5,
}
FACTOR_NAMES = {
    "business": "Business quality", "revenue": "Revenue growth", "pat": "PAT growth",
    "margin": "Margins", "cash": "Cash-flow quality", "workingCapital": "Working capital",
    "debt": "Balance sheet / debt", "returns": "ROE / ROCE", "structure": "IPO structure",
    "valuation": "Valuation", "concentration": "Concentration risk", "anchor": "Anchor quality",
    "qib": "QIB demand", "demand": "HNI / retail demand", "gmp": "GMP level",
    "gmpTrend": "GMP trend", "liquidity": "Liquidity",
}
RAW_TOTAL = sum(RAW_WEIGHTS.values())
FUNDAMENTAL_KEYS = ["business", "revenue", "pat", "margin", "cash", "workingCapital",
                    "debt", "returns", "structure", "valuation", "concentration"]
MARKET_KEYS = ["anchor", "qib", "demand", "gmp", "gmpTrend", "liquidity"]


def has(x):
    if x is None or x == "":
        return False
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def clamp(v, a, b):
    return max(a, min(b, v))


def last(a):
    return float(a[-1]) if a and has(a[-1]) else None


def previous(a):
    return float(a[-2]) if a and len(a)>1 and has(a[-2]) else None


def first(a):
    for x in (a or []):
        if has(x):
            return float(x)
    return None


def total(a):
    return sum(float(x) for x in a) if a and all(has(x) for x in a) else None


def cagr(a):
    f, l = (a[0] if a else None), last(a)
    c = len(a or [])
    if has(f) and has(l) and f > 0 and l > 0 and c > 1:
        return (math.pow(l / f, 1 / (c - 1)) - 1) * 100
    return None


def growth_score(x):
    return clamp((40 + float(x) * 2) / 10, 0, 10) if has(x) else None


def margin_score(x):
    return clamp(float(x) / 2.5, 0, 10) if has(x) else None


def qib_score(x):
    if not has(x):
        return None
    x = float(x)
    for th, sc in [(100, 10), (50, 9.5), (25, 9), (15, 8.5), (10, 8), (5, 7), (2, 6), (1, 5)]:
        if x >= th:
            return sc
    return 3


def gmp_score(x):
    if not has(x):
        return None
    x = float(x)
    for th, sc in [(50, 10), (40, 9.5), (30, 9), (20, 8), (15, 7), (10, 6)]:
        if x >= th:
            return sc
    return 5 if x > 0 else 2


def sub_score(x):
    if not has(x):
        return None
    x = float(x)
    for th, sc in [(50, 10), (25, 9), (10, 8), (5, 7), (2, 6), (1, 5)]:
        if x >= th:
            return sc
    return 3


def debt_score(x):
    if not has(x):
        return None
    x = float(x)
    if x < .25:
        return 10
    if x < .5:
        return 8.5
    if x < 1:
        return 6.5
    if x <= 2:
        return 4
    return 2


def liquidity_score(current_ratio):
    """
    0-10 proxy for the "Liquidity" factor, derived from the balance-sheet
    current ratio (current assets / current liabilities) when no manual
    liquidity judgement has been entered. This measures short-term
    solvency, not post-listing trading/exit liquidity (lot size, free
    float, market cap) — a real but different notion of "liquidity" that
    this app has no automated way to measure. Treat this as a stand-in,
    and override it manually if you want the factor to reflect trading
    liquidity instead.
    """
    if not has(current_ratio):
        return None
    x = float(current_ratio)
    if x <= 0:
        return None
    if x >= 2:
        return 9
    if x >= 1.5:
        return 7.5
    if x >= 1.2:
        return 6.5
    if x >= 1:
        return 5.5
    if x >= .75:
        return 4
    return 2


def returns_score(roe, roce):
    v = float(roce) if has(roce) else (float(roe) if has(roe) else None)
    if v is None:
        return None
    if v > 40:
        return 10
    if v >= 25:
        return 9
    if v >= 15:
        return 7
    if v >= 10:
        return 5
    return 3


def cash_score(pat, cfo, prev, cpat, ccfo):
    if not has(cfo):
        return None
    cfo = float(cfo)
    if cfo < 0 and has(prev) and float(prev) < 0:
        return 2.5
    if cfo < 0:
        return 3.5
    if not has(pat) or float(pat) <= 0:
        return None
    pat = float(pat)
    conv = cfo / pat
    if has(cpat) and has(ccfo) and float(cpat) > 0 and float(ccfo) >= float(cpat):
        return 9.5
    if conv >= 1:
        return 9
    if conv >= .7:
        return 8
    if conv >= .5:
        return 7
    if conv >= .3:
        return 6
    return 4.5


def working_score(r):
    if not all(has(r.get(k)) for k in ("inv_days", "deb_days", "cred_days")):
        return None
    ccc = (float(r.get("inv_days") or 0) + float(r.get("deb_days") or 0)
           - float(r.get("cred_days") or 0))
    if ccc < 90:
        return 9
    if ccc <= 120:
        return 7.5
    if ccc <= 180:
        return 5
    return 2.5


def structure_score(r):
    fresh, issue = r.get("fresh"), r.get("issue_size")
    if not has(fresh) or not has(issue) or float(issue) <= 0:
        return None
    p = float(fresh) / float(issue) * 100
    if p >= 99:
        return 9.5
    if p > 75:
        return 8.5
    if p >= 50:
        return 7.5
    if p >= 25:
        return 6
    return 4


def valuation_score(r):
    pe, peer = r.get("pe"), r.get("peer_pe")
    if not has(pe) or float(pe) <= 0 or not has(peer) or float(peer) <= 0:
        return None
    rel = float(pe) / float(peer)
    if rel <= .7:
        return 9
    if rel <= .9:
        return 8
    if rel <= 1.1:
        return 7
    if rel <= 1.3:
        return 5.5
    if rel <= 1.6:
        return 4
    return 2.5


def concentration_score(r):
    vals = [float(x) for x in (r.get("top_cust"), r.get("top_supp")) if has(x)]
    if not vals:
        return None
    high = max(vals)
    if high > 80:
        return 2.5
    if high >= 60:
        return 4.5
    if high >= 40:
        return 6.5
    if high >= 20:
        return 8
    return 9.5


def trend_score(x):
    return {"Rising": 9, "Stable": 7, "Falling": 4, "Sharp Fall": 2, "Recovery": 6}.get(x)


def competition_score(r):
    share = [sub_score(r.get(k)) for k in ("sub_shni", "sub_bhni", "sub_nii", "sub_retail")]
    share = [s for s in share if s is not None]
    return sum(share) / len(share) if share else None


def analyse(r):
    rg, pg = cagr(r.get("revenue")), cagr(r.get("pat"))
    rev, eb = last(r.get("revenue")), last(r.get("ebitda"))
    margin = (eb / rev * 100) if has(rev) and float(rev) != 0 and has(eb) else None
    lc, pc = last(r.get("cfo")), previous(r.get("cfo"))
    lp = last(r.get("pat"))
    cc, cp = total(r.get("cfo")), total(r.get("pat"))
    lf = last(r.get("fcf"))
    ratio = (lc / lp) if has(lc) and has(lp) and float(lp) > 0 else None
    cum = (cc / cp) if has(cc) and has(cp) and float(cp) > 0 else None
    de_display = r.get("post_de") if has(r.get("post_de")) else r.get("de")

    factors = {
        "business": float(r["business_score"]) if has(r.get("business_score")) else None,
        "revenue": growth_score(rg), "pat": growth_score(pg), "margin": margin_score(margin),
        "cash": cash_score(lp, lc, pc, cp, cc), "workingCapital": working_score(r),
        "debt": debt_score(de_display), "returns": returns_score(r.get("roe"), r.get("roce")),
        "structure": structure_score(r), "valuation": valuation_score(r),
        "concentration": concentration_score(r),
        "anchor": float(r["anchor"]) if has(r.get("anchor")) else None,
        "qib": qib_score(r.get("sub_qib")), "demand": competition_score(r),
        "gmp": gmp_score(r.get("gmp_pct")), "gmpTrend": trend_score(r.get("gmp_trend")),
        "liquidity": float(r["liquidity"]) if has(r.get("liquidity")) else None,
    }

    weighted = known = 0
    for k, v in factors.items():
        if has(v):
            weighted += v * RAW_WEIGHTS[k]
            known += RAW_WEIGHTS[k]
    score = (weighted / known) if known else None
    coverage = known / RAW_TOTAL * 100

    essential = all(has(x) for x in (ratio, de_display, r.get('pe'), r.get('sub_qib'), r.get('gmp_pct')))
    secondary_cash=(r.get('field_sources') or {}).get('cfo',{}).get('source')=='ipo360'
    research=r.get('research') or {}
    if (r.get('field_sources') or {}).get('cfo',{}).get('source')=='research':
        annual=r.get('years',[])
        latest_year=str(annual[-1]) if annual else ''
        latest_evidence=next((e for e in reversed(research.get('evidence',[])) if e.get('metric')=='cfo' and str(e.get('year'))==latest_year),{})
        secondary_cash=not latest_evidence.get('primary') or bool(research.get('conflicts'))
    if coverage < 60 or not essential or secondary_cash:
        auto = "Research needed"
    elif score is not None and score >= 8.2:
        auto = "STRONG APPLY"
    elif score is not None and score >= 7.5:
        auto = "APPLY"
    elif score is not None and score >= 6.8:
        auto = "WAIT / WATCH"
    elif score is not None and score >= 6:
        auto = "CAUTIOUS / HIGH RISK"
    else:
        auto = "SKIP"
    final = r.get("override_verdict") if r.get('override_reason') else auto
    final = final or auto

    def block(keys):
        w = v = 0
        for k in keys:
            if has(factors.get(k)):
                w += RAW_WEIGHTS[k]
                v += factors[k] * RAW_WEIGHTS[k]
        return (v / w) if w else None

    missing = []
    if secondary_cash: missing.append('primary-source cross-check of annual cash-flow figures')
    if not r.get("sector"):
        missing.append("business/sector")
    if not r.get("location"):
        missing.append("location/facilities")
    if not has(rev):
        missing.append("revenue")
    if not has(lp):
        missing.append("PAT")
    if not has(lc):
        missing.append("operating cash flow")
    if not has(r.get("de")) and not has(r.get("post_de")):
        missing.append("debt")
    if not has(r.get("pe")):
        missing.append("valuation")
    if not has(r.get("sub_qib")):
        missing.append("QIB demand")
    if not has(r.get("gmp_pct")):
        missing.append("GMP")

    flags, positives = [], []
    if has(lc) and lc < 0:
        flags.append("Negative latest operating cash flow")
    if has(lc) and has(pc) and lc < 0 and pc < 0:
        flags.append("Operating cash flow is negative for two consecutive periods")
    if has(ratio) and ratio < .3:
        flags.append("Latest CFO/PAT conversion is below 30%")
    if has(r.get("de")) and float(r["de"]) > 1:
        flags.append("High debt-equity ratio")
    if has(r.get("top_cust")) and float(r["top_cust"]) > 60:
        flags.append("High customer concentration")
    if has(r.get("top_supp")) and float(r["top_supp"]) > 80:
        flags.append("High supplier concentration")
    if has(r.get("fresh")) and has(r.get("issue_size")) and float(r["issue_size"]) > 0 and \
            float(r["fresh"]) / float(r["issue_size"]) < .25:
        flags.append("Large OFS / low fresh-issue component")
    if has(r.get("pe")) and has(r.get("peer_pe")) and float(r["pe"]) > float(r["peer_pe"]) * 1.3:
        flags.append("Valuation is materially above the entered peer median")
    if has(r.get("sub_qib")) and float(r["sub_qib"]) < 1:
        flags.append("Weak QIB subscription")
    if r.get("gmp_trend") in ("Falling", "Sharp Fall"):
        flags.append("GMP trend is weakening")
    if r.get("board") == "SME":
        flags.append("SME lot concentration and exit-liquidity risk")

    if has(rg) and rg > 15:
        positives.append("Strong revenue CAGR")
    if has(pg) and pg > 15:
        positives.append("Strong PAT CAGR")
    if has(ratio) and ratio >= .7:
        positives.append("Healthy CFO/PAT conversion")
    if has(r.get("post_de")) and float(r["post_de"]) < .25:
        positives.append("Low post-issue debt")
    if has(r.get("roce")) and float(r["roce"]) >= 25:
        positives.append("Strong ROCE")
    if has(r.get("fresh")) and has(r.get("issue_size")) and float(r["issue_size"]) and \
            float(r["fresh"]) / float(r["issue_size"]) > .75:
        positives.append("High fresh-issue component")
    if has(r.get("sub_qib")) and float(r["sub_qib"]) >= 10:
        positives.append("Strong QIB demand")
    if r.get("gmp_trend") == "Rising":
        positives.append("Rising GMP trend")

    return {
        "factors": factors, "score": score, "coverage": coverage, "auto": auto, "final": final,
        "fundamental": block(FUNDAMENTAL_KEYS), "market": block(MARKET_KEYS),
        "rg": rg, "pg": pg, "margin": margin, "lc": lc, "pc": pc, "lp": lp, "lf": lf,
        "cc": cc, "cp": cp, "ratio": ratio, "cum": cum,
        "missing": missing, "flags": flags, "positives": positives,
    }


def verdict_class(final):
    f = (final or "").upper()
    if "STRONG APPLY" in f:
        return "strong-apply"
    if f == "APPLY":
        return "apply"
    if "WAIT" in f:
        return "wait"
    if "CAUTIOUS" in f:
        return "caution"
    if "SKIP" in f:
        return "skip"
    return "research"
