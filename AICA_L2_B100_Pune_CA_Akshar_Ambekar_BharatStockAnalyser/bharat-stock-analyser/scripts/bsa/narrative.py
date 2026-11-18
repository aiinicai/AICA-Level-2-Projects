"""Rule-based, data-cited narrative: positives, concerns, headline and summary.

Every sentence quotes a number that exists in the analysis. Nothing here is free text
from a language model; Claude's own commentary is added separately and labelled.
"""

from __future__ import annotations

from .fmt import fmt_cr, fmt_pct, fmt_rs, fmt_x


def build(meta: dict, price: dict, fund: dict, val: dict, tech: dict, sc: dict, rt: dict, peers: dict,
          holdings: dict) -> dict:
    pos: list[str] = []
    con: list[str] = []
    a = fund["annual"]
    last = a[-1] if a else {}
    g = fund["growth"]
    fin = fund["is_financial"]
    m = val["multiples"]
    qc = fund["quarter_changes"]
    span = f"{g.get('from')} to {g.get('to')}" if g.get("years") else ""

    # Growth
    if g.get("revenue") is not None:
        first_rev = a[-1 - g["years"]]["revenue"]
        verb = "grew" if g["revenue"] >= 0 else "declined"
        s = (f"Revenue {verb} at a {fmt_pct(abs(g['revenue']))} CAGR over {span} "
             f"(Rs {fmt_cr(first_rev)} cr to Rs {fmt_cr(last.get('revenue'))} cr).")
        if g["revenue"] >= 10:
            pos.append(s)
        elif g["revenue"] < 3:
            con.append(s)
    if g.get("eps") is not None:
        if g["eps"] >= 12:
            pos.append(f"Earnings per share excluding one-offs compounded at {fmt_pct(g['eps'])} a year over {span}.")
        elif g["eps"] < 0:
            con.append(f"Earnings per share excluding one-offs declined at {fmt_pct(abs(g['eps']))} a year over "
                       f"{span}.")
    yoy = qc.get("yoy", {})
    if yoy.get("pat_norm") is not None:
        lab = f"{qc['latest']} vs {qc['year_ago']}"
        if yoy["pat_norm"] >= 15:
            pos.append(f"Latest quarter net profit excluding one-offs rose {fmt_pct(yoy['pat_norm'])} year on year "
                       f"({lab}).")
        elif yoy["pat_norm"] <= -10:
            con.append(f"Latest quarter net profit excluding one-offs fell {fmt_pct(abs(yoy['pat_norm']))} year on "
                       f"year ({lab}).")
    lq = fund["quarters"][-1] if fund["quarters"] else {}
    if lq.get("one_off") and lq.get("pat") and lq["one_off_after_tax"] >= 0.15 * abs(lq["pat"]):
        con.append(f"Earnings quality: {lq['label']} profit of Rs {fmt_cr(lq['pat'])} cr includes an estimated "
                   f"one-off gain of Rs {fmt_cr(lq['one_off_after_tax'])} cr after tax ({lq['one_off_source']}); "
                   f"excluding it, profit is Rs {fmt_cr(lq['pat_norm'])} cr.")

    # Quality
    roe = last.get("roe")
    if roe is not None:
        if roe >= (15 if fin else 18):
            pos.append(f"Return on equity of {fmt_pct(roe)} in {last['label']} is strong.")
        elif roe < (10 if fin else 10):
            con.append(f"Return on equity of {fmt_pct(roe)} in {last['label']} is below the cost of equity "
                       f"of {fmt_pct(val['cost_of_capital']['cost_of_equity'])}.")
    if not fin:
        nde = last.get("net_debt_equity")
        if nde is not None:
            if nde <= 0:
                pos.append(f"Net cash balance sheet (net debt to equity of {fmt_x(nde, 2)}).")
            elif nde > 1.0:
                con.append(f"High leverage: net debt to equity of {fmt_x(nde, 2)} "
                           f"(net debt Rs {fmt_cr(last.get('net_debt'))} cr).")
        ic = last.get("interest_cover")
        if ic is not None and ic < 3:
            con.append(f"Thin interest cover of {fmt_x(ic)} (EBIT to interest).")
        conv = [r["cfo_to_pat"] for r in a[-3:] if r.get("cfo_to_pat") is not None]
        if conv:
            avg = sum(conv) / len(conv)
            if avg >= 1.0:
                pos.append(f"Profits convert to cash: operating cash flow averaged {fmt_x(avg, 2)} of net profit "
                           "over the last three years.")
            elif avg < 0.7:
                con.append(f"Weak cash conversion: operating cash flow averaged only {fmt_x(avg, 2)} of net profit.")
    else:
        roa = last.get("roa")
        if roa is not None and roa >= 1.5:
            pos.append(f"Return on assets of {fmt_pct(roa, 2)} is healthy for a lender.")
        elif roa is not None and roa < 0.8:
            con.append(f"Return on assets of {fmt_pct(roa, 2)} is low for a lender.")

    # Valuation
    if not fin and m.get("pe_vs_history"):
        r = m["pe_vs_history"]
        if r <= 0.85:
            pos.append(f"Trades at {fmt_x(m['pe'])} trailing earnings, a {fmt_pct((1 - r) * 100, 0)} discount to "
                       f"its own FY-end median of {fmt_x(fund['pe_history_median'])}.")
        elif r >= 1.25:
            con.append(f"Trades at {fmt_x(m['pe'])} trailing earnings, a {fmt_pct((r - 1) * 100, 0)} premium to "
                       f"its own FY-end median of {fmt_x(fund['pe_history_median'])}.")
    if fin and m.get("pb_vs_history"):
        r = m["pb_vs_history"]
        if r <= 0.85:
            pos.append(f"Trades at {fmt_x(m['pb'], 2)} book, below its FY-end median of "
                       f"{fmt_x(fund['pb_history_median'], 2)}.")
        elif r >= 1.25:
            con.append(f"Trades at {fmt_x(m['pb'], 2)} book, above its FY-end median of "
                       f"{fmt_x(fund['pb_history_median'], 2)}.")
    cons = val["consensus"]
    if cons.get("mean") and cons.get("analysts", 0) >= 3:
        up = (cons["mean"] / price["cmp"] - 1) * 100
        s = (f"{cons['analysts']} analysts have a mean target of {fmt_rs(cons['mean'])} "
             f"({fmt_pct(up, signed=True)} from the current price).")
        if up >= 10:
            pos.append(s)
        elif up < 0:
            con.append(s)

    # Technicals and relative strength
    c = tech["close"]
    if tech.get("sma200"):
        if c > tech["sma200"] and (tech.get("sma50") or 0) > tech["sma200"]:
            pos.append(f"Price trend is up: the stock is above its 200-day average ({fmt_rs(tech['sma200'])}) "
                       "and the 50-day average is above the 200-day.")
        elif c < tech["sma200"] and (tech.get("sma50") or 0) < tech["sma200"]:
            con.append(f"Price trend is down: the stock is below its 200-day average ({fmt_rs(tech['sma200'])}) "
                       "and the 50-day average is below the 200-day.")
    rs, br = tech.get("returns", {}).get("1y"), tech.get("bench_returns", {}).get("1y")
    if rs is not None and br is not None:
        rel = rs - br
        if rel >= 10:
            pos.append(f"Outperformed the Nifty 50 by {fmt_pct(rel)} over 12 months ({fmt_pct(rs, signed=True)} vs "
                       f"{fmt_pct(br, signed=True)}).")
        elif rel <= -10:
            con.append(f"Underperformed the Nifty 50 by {fmt_pct(abs(rel))} over 12 months "
                       f"({fmt_pct(rs, signed=True)} vs {fmt_pct(br, signed=True)}).")
    r = tech.get("rsi14")
    if r is not None and r >= 70:
        con.append(f"Short-term overbought: RSI (14) is {r:.0f}.")
    if tech.get("volatility_1y") and tech["volatility_1y"] >= 40:
        con.append(f"High price volatility of {fmt_pct(tech['volatility_1y'])} a year.")
    if tech.get("max_drawdown_1y") is not None and tech["max_drawdown_1y"] <= -35:
        con.append(f"Fell as much as {fmt_pct(abs(tech['max_drawdown_1y']))} from a peak in the last year.")

    # Ownership: the exchange shareholding pattern when available, else the source's insider split
    pr = holdings.get("promoter")
    ins = holdings.get("insiders")
    if pr is not None:
        as_of = f" as of {holdings['as_of']}" if holdings.get("as_of") else ""
        if pr >= 50:
            pos.append(f"Promoter holding is high at {fmt_pct(pr)}{as_of}.")
        elif 0 < pr < 15 and not fin:
            con.append(f"Promoter holding is low at {fmt_pct(pr)}{as_of}.")
        tr = holdings.get("promoter_trend") or []
        if len(tr) >= 2 and tr[0]["promoter"] > 0:
            move = tr[-1]["promoter"] - tr[0]["promoter"]
            text = (f"promoter holding moved from {tr[0]['promoter']:.2f}% ({tr[0]['date']}) to "
                    f"{tr[-1]['promoter']:.2f}% ({tr[-1]['date']})")
            if move <= -2:
                con.append(f"Promoters are selling: {text}.")
            elif move >= 2:
                pos.append(f"Promoters are buying: {text}.")
        pledged = holdings.get("pledged_pct_of_promoter")
        if pledged is not None and pledged >= 1:
            con.append(f"{fmt_pct(pledged)} of promoter shares are pledged{as_of}; a falling price can force sales.")
        inst = (holdings.get("fii") or 0) + (holdings.get("dii") or 0)
        if holdings.get("fii") is not None and inst >= 40:
            pos.append(f"Institutions hold {fmt_pct(inst)} (FII {fmt_pct(holdings['fii'])}, DII "
                       f"{fmt_pct(holdings.get('dii'))}){as_of}.")
    elif ins is not None:
        if ins >= 50:
            pos.append(f"Promoter and insider holding is high at {fmt_pct(ins)}.")
        elif ins < 15 and not fin:
            con.append(f"Promoter and insider holding is low at {fmt_pct(ins)}.")

    for x in val.get("excluded_conflicts", []):
        con.append(f"Valuation cross-check disagrees: {x}")

    # Headline and summary
    rating = rt["rating"] + (" (provisional)" if rt.get("provisional") else "")
    if val.get("target"):
        headline = (f"{rating}: target {fmt_rs(val['target'])}, {fmt_pct(val['upside'], signed=True)} "
                    f"from {fmt_rs(price['cmp'])}")
    else:
        headline = f"{rating}: not rated on valuation"
    pillars = {p["pillar"]: p["score"] for p in sc["pillars"]}
    best = max((k for k in pillars if pillars[k] is not None), key=lambda k: pillars[k], default=None)
    worst = min((k for k in pillars if pillars[k] is not None), key=lambda k: pillars[k], default=None)
    used = [mm["name"] for mm in val["methods"] if mm["included"]]
    parts = []
    if val.get("target"):
        parts.append(
            f"We arrive at a 12-month target price of {fmt_rs(val['target'])} for {meta['name']}, a blend of "
            f"{_join(used)}. This implies {fmt_pct(val['upside'], signed=True)} from the current market price "
            f"of {fmt_rs(price['cmp'])}.")
        parts += val.get("adjustments", [])
    else:
        parts.append(f"No valuation method produced a usable value for {meta['name']}, so the stock is not rated "
                     "on valuation.")
    if sc.get("composite") is not None:
        parts.append(f"The stock scores {sc['composite']:.0f} out of 100 on our six-pillar scorecard; "
                     f"the strongest pillar is {best} ({pillars[best]:.0f}) and the weakest is "
                     f"{worst} ({pillars[worst]:.0f}).")
    parts.append(f"Rating: {rating} with {rt['conviction'].lower()} conviction.")
    if rt.get("provisional"):
        parts.append("The rating is provisional and should not be acted on until the reasons listed under 'How the "
                     "rating was reached' are resolved.")
    return {"headline": headline, "summary": " ".join(parts), "positives": pos[:8], "concerns": con[:10]}


def _join(items: list[str]) -> str:
    # Lower-case the first word only, keeping acronyms such as P/E and P/B intact.
    items = [i[0].lower() + i[1:] for i in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]
