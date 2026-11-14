"""Six-pillar scorecard (0 to 100) and the Buy / Hold / Sell rule.

Every metric is scored by straight-line interpolation between a 'worst' value (score 0)
and a 'best' value (score 100), clipped at both ends. A pillar is the average of its
available metric scores. The composite is the weighted average of available pillars,
with weights renormalised when a pillar has no data.

Rating rule (rating key follows the convention of Indian broker research notes):
    1. Base rating from upside to the blended 12-month target:
           BUY   upside of 15 percent or more
           HOLD  upside from -5 percent to below 15 percent
           SELL  upside below -5 percent
    2. Quality gate: a BUY with composite score below 50 is cut to HOLD.
    3. Weak-stock gate: a HOLD with composite score below 35 and upside below 5 percent
       becomes SELL.
    4. Provisional gate: the rating is marked Provisional when only one valuation method is
       usable, a download the rating depends on failed, results the data should contain are
       overdue, or Claude's research found newer results or a data conflict. A provisional
       rating cannot be BUY (it is cut to HOLD) and its conviction is Low.
    5. No target price (no valuation method usable): the rating is HOLD, marked
       'Not rated on valuation', and conviction is Low.

The scorecard deliberately excludes upside to the model's own target, so that the target
cannot raise the score that is then used to confirm it.
"""

from __future__ import annotations

from .fmt import clamp, fmt_num, fmt_pct, fmt_x, num

PILLAR_WEIGHTS = {
    "Quality": 25,
    "Growth": 20,
    "Valuation": 20,
    "Technical trend": 15,
    "Relative strength": 10,
    "Risk": 10,
}

BUY_UPSIDE = 15.0
SELL_UPSIDE = -5.0
BUY_MIN_SCORE = 50.0
SELL_MAX_SCORE = 35.0


def lin(x, worst: float, best: float) -> float | None:
    x = num(x)
    if x is None:
        return None
    t = (x - worst) / (best - worst)
    return clamp(t, 0.0, 1.0) * 100.0


def rsi_score(r) -> float | None:
    r = num(r)
    if r is None:
        return None
    if 45 <= r <= 65:
        return 100.0
    if r > 65:
        return lin(r, 80, 65)
    return lin(r, 25, 45)


def _metric(name, value, score, shown):
    return {"metric": name, "value": value, "display": shown, "score": score}


def scorecard(fund: dict, val: dict, tech: dict) -> dict:
    annual = fund["annual"]
    last = annual[-1] if annual else {}
    g = fund["growth"]
    qc = fund["quarter_changes"]
    fin = fund["is_financial"]
    p: dict[str, list[dict]] = {k: [] for k in PILLAR_WEIGHTS}

    # Quality
    if not fin:
        cfo_pat = [r["cfo_to_pat"] for r in annual[-3:] if r.get("cfo_to_pat") is not None]
        cfo_avg = sum(cfo_pat) / len(cfo_pat) if cfo_pat else None
        p["Quality"] += [
            _metric("Return on equity", last.get("roe"), lin(last.get("roe"), 5, 22), fmt_pct(last.get("roe"))),
            _metric("Return on capital employed", last.get("roce"), lin(last.get("roce"), 6, 25),
                    fmt_pct(last.get("roce"))),
            _metric("Net debt to equity", last.get("net_debt_equity"), lin(last.get("net_debt_equity"), 1.5, 0.0),
                    fmt_x(last.get("net_debt_equity"), 2)),
            _metric("Interest cover (EBIT / interest)", last.get("interest_cover"),
                    lin(last.get("interest_cover"), 1.5, 10), fmt_x(last.get("interest_cover"))),
            _metric("Cash conversion (CFO / PAT, 3-yr avg)", cfo_avg, lin(cfo_avg, 0.5, 1.1), fmt_x(cfo_avg, 2)),
        ]
    else:
        p["Quality"] += [
            _metric("Return on equity", last.get("roe"), lin(last.get("roe"), 8, 18), fmt_pct(last.get("roe"))),
            _metric("Return on assets", last.get("roa"), lin(last.get("roa"), 0.5, 2.0), fmt_pct(last.get("roa"), 2)),
            _metric("Book value CAGR", g.get("book_value"), lin(g.get("book_value"), 5, 18),
                    fmt_pct(g.get("book_value"))),
        ]

    # Growth (quarterly YoY is matched by date and uses profit excluding one-offs)
    rev_yoy = qc.get("yoy", {}).get("revenue")
    pat_yoy = qc.get("yoy", {}).get("pat_norm")
    ya = f" ({qc['latest']} vs {qc['year_ago']})" if qc.get("year_ago") else ""
    p["Growth"] += [
        _metric(f"Revenue CAGR ({g.get('years', 0)} yrs)", g.get("revenue"), lin(g.get("revenue"), 0, 15),
                fmt_pct(g.get("revenue"))),
        _metric(f"EPS CAGR excl. one-offs ({g.get('years', 0)} yrs)", g.get("eps"), lin(g.get("eps"), -5, 20),
                fmt_pct(g.get("eps"))),
        _metric(f"Latest quarter revenue YoY{ya}", rev_yoy, lin(rev_yoy, -5, 20), fmt_pct(rev_yoy)),
        _metric(f"Latest quarter PAT YoY excl. one-offs{ya}", pat_yoy, lin(pat_yoy, -10, 25), fmt_pct(pat_yoy)),
    ]

    # Valuation (upside to the model's own target is not scored, to avoid circularity)
    m = val["multiples"]
    if not fin:
        p["Valuation"] += [
            _metric("P/E vs own FY-end median", m.get("pe_vs_history"), lin(m.get("pe_vs_history"), 1.4, 0.8),
                    fmt_x(m.get("pe_vs_history"), 2)),
            _metric("P/E vs peer median", m.get("pe_vs_peers"), lin(m.get("pe_vs_peers"), 1.5, 0.8),
                    fmt_x(m.get("pe_vs_peers"), 2)),
            _metric("PEG ratio (forward growth)", m.get("peg"), lin(m.get("peg"), 3.0, 1.0), fmt_x(m.get("peg"), 2)),
            _metric("Free cash flow yield", m.get("fcf_yield"), lin(m.get("fcf_yield"), 0.0, 5.0),
                    fmt_pct(m.get("fcf_yield"))),
        ]
    else:
        p["Valuation"] += [
            _metric("P/B vs own FY-end median", m.get("pb_vs_history"), lin(m.get("pb_vs_history"), 1.4, 0.8),
                    fmt_x(m.get("pb_vs_history"), 2)),
            _metric("P/B vs peer median", m.get("pb_vs_peers"), lin(m.get("pb_vs_peers"), 1.5, 0.8),
                    fmt_x(m.get("pb_vs_peers"), 2)),
        ]

    # Technical trend
    c = tech["close"]

    def gap(level):
        return (c / level - 1) * 100 if level else None

    g200, g50 = gap(tech.get("sma200")), gap(tech.get("sma50"))
    cross = (tech["sma50"] / tech["sma200"] - 1) * 100 if tech.get("sma50") and tech.get("sma200") else None
    hist = tech.get("macd_hist")
    p["Technical trend"] += [
        _metric("Price vs 200-DMA", g200, lin(g200, -15, 10), fmt_pct(g200, signed=True)),
        _metric("Price vs 50-DMA", g50, lin(g50, -10, 8), fmt_pct(g50, signed=True)),
        _metric("50-DMA vs 200-DMA", cross, lin(cross, -8, 5), fmt_pct(cross, signed=True)),
        _metric("RSI (14)", tech.get("rsi14"), rsi_score(tech.get("rsi14")), fmt_num(tech.get("rsi14"), 1)),
        _metric("MACD histogram", hist, None if hist is None else (75.0 if hist > 0 else 25.0),
                "Positive" if hist and hist > 0 else ("Negative" if hist is not None else "-")),
    ]

    # Relative strength vs Nifty 50
    sr, br = tech.get("returns", {}), tech.get("bench_returns", {})
    for k, label in (("3m", "3-month"), ("6m", "6-month"), ("1y", "12-month")):
        rel = sr.get(k) - br.get(k) if sr.get(k) is not None and br.get(k) is not None else None
        p["Relative strength"].append(_metric(f"{label} return vs Nifty 50", rel, lin(rel, -15, 15),
                                              fmt_pct(rel, signed=True)))

    # Risk
    p["Risk"] += [
        _metric("Annualised volatility (1 yr)", tech.get("volatility_1y"), lin(tech.get("volatility_1y"), 50, 18),
                fmt_pct(tech.get("volatility_1y"))),
        _metric("Maximum drawdown (1 yr)", tech.get("max_drawdown_1y"), lin(tech.get("max_drawdown_1y"), -50, -12),
                fmt_pct(tech.get("max_drawdown_1y"))),
        _metric("Beta vs Nifty 50 (1 yr)", tech.get("beta_1y"), lin(tech.get("beta_1y"), 1.6, 0.7),
                fmt_num(tech.get("beta_1y"), 2)),
    ]

    pillars = []
    for name, weight in PILLAR_WEIGHTS.items():
        scores = [x["score"] for x in p[name] if x["score"] is not None]
        pillars.append({"pillar": name, "weight": weight, "score": sum(scores) / len(scores) if scores else None,
                        "metrics": p[name], "metrics_used": len(scores)})
    avail = [x for x in pillars if x["score"] is not None]
    wsum = sum(x["weight"] for x in avail)
    composite = sum(x["score"] * x["weight"] for x in avail) / wsum if wsum else None
    return {"pillars": pillars, "composite": composite}


def rating(upside: float | None, composite: float | None, methods_used: int, dispersion: float | None,
           provisional_reasons: list[str] | None = None, conflicts: list[str] | None = None) -> dict:
    """Apply the rating rules. `provisional_reasons` come from data checks and Claude's research."""
    trace = []
    reasons = list(provisional_reasons or [])
    if upside is not None and methods_used < 2:
        reasons.insert(0, "Only one valuation method is usable, so the target has no cross-check.")
    if upside is None:
        trace.append("No valuation method produced a usable value, so the stock is not rated on valuation.")
        return {"rating": "HOLD", "base_rating": None, "conviction": "Low", "trace": trace,
                "not_rated_on_valuation": True, "provisional": bool(reasons), "provisional_reasons": reasons}

    if upside >= BUY_UPSIDE:
        base = "BUY"
    elif upside >= SELL_UPSIDE:
        base = "HOLD"
    else:
        base = "SELL"
    trace.append(f"Upside of {upside:.1f}% to the blended target gives a base rating of {base} "
                 f"(BUY at {BUY_UPSIDE:.0f}% or more, SELL below {SELL_UPSIDE:.0f}%).")
    final = base
    score = composite if composite is not None else 50.0
    if base == "BUY" and score < BUY_MIN_SCORE:
        final = "HOLD"
        trace.append(f"Composite score of {score:.0f} is below {BUY_MIN_SCORE:.0f}, so BUY is cut to HOLD "
                     "(quality gate).")
    elif base == "HOLD" and score < SELL_MAX_SCORE and upside < 5.0:
        final = "SELL"
        trace.append(f"Composite score of {score:.0f} is below {SELL_MAX_SCORE:.0f} and upside is under 5%, so HOLD "
                     "becomes SELL (weak-stock gate).")
    else:
        trace.append(f"Composite score of {score:.0f} does not trigger a score gate.")

    if reasons:
        trace.append("The rating is provisional: " + " ".join(reasons))
        if final == "BUY":
            final = "HOLD"
            trace.append("A provisional rating cannot be BUY, so BUY is cut to HOLD (provisional gate).")

    # Conviction
    if reasons:
        conviction = "Low"
        trace.append("Conviction is Low because the rating is provisional.")
    elif methods_used < 2 or (dispersion is not None and dispersion > 60):
        conviction = "Low"
        trace.append("Conviction is Low: fewer than two valuation methods agree closely "
                     "(spread above 60% of target, or only one method).")
    elif conflicts:
        conviction = "Low"
        trace.append("Conviction is Low: an excluded valuation method points the other way. " + " ".join(conflicts))
    elif (final == "BUY" and score >= 65 and (dispersion or 0) <= 35) or \
         (final == "SELL" and score <= 40 and (dispersion or 0) <= 35):
        conviction = "High"
        trace.append("Conviction is High: the scorecard supports the rating and the valuation methods are close.")
    else:
        conviction = "Medium"
        trace.append("Conviction is Medium.")
    return {"rating": final, "base_rating": base, "conviction": conviction, "trace": trace,
            "not_rated_on_valuation": False, "provisional": bool(reasons), "provisional_reasons": reasons}
