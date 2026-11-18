"""12-month target price from three independent methods, blended.

Method A  Relative multiple
          Non-financial: forward EPS x target P/E. Target P/E = median of (own FY-end P/E history,
          peer median P/E), capped at RERATE_CAP x the current P/E. Financial: forward book value
          per share x target P/B, same logic.
Method B  Intrinsic value
          Non-financial: 10-year two-stage free cash flow DCF discounted at WACC.
          Financial: justified P/B = (ROE - g) / (CoE - g) applied to forward book value.
          Rolled forward 12 months at (cost of equity - dividend yield).
Method C  Street consensus
          Mean analyst target price (only when at least 3 analysts cover the stock).

Weights 40 / 30 / 30, renormalised over the methods that produce a value. A method whose
value is outside 0.4x to 2.5x the current price is excluded as an outlier and reported.
The blended target is then capped at CONSENSUS_CAP x the highest analyst target.

All earnings figures exclude one-off items (see fundamentals.normalise).
"""

from __future__ import annotations

from .fmt import clamp, fmt_cr, fmt_pct, fmt_rs, fmt_x, median, num, safe_div

ASSUMPTIONS = {
    "risk_free": 6.5,          # India 10-year G-Sec yield, percent (approximate; override with --rf)
    "equity_risk_premium": 7.0,  # India equity risk premium, percent
    "cost_of_debt": 9.0,       # Pre-tax cost of debt, percent
    "tax_rate": 25.17,         # Section 115BAA effective corporate rate incl. surcharge and cess, percent
    "terminal_growth": 5.0,    # Long-run nominal growth, percent
    "high_growth_years": 5,
    "explicit_years": 10,
    "wacc_floor": 10.0,
}
WEIGHTS = {"relative": 0.40, "intrinsic": 0.30, "consensus": 0.30}
BOUNDS = (0.4, 2.5)
FWD_EPS_CAP = 1.4     # forward EPS used in the relative method is at most 1.4x trailing EPS
FWD_GROWTH_MAX = 20.0  # growth applied to trailing EPS when there is no consensus forward EPS
RERATE_CAP = 1.25     # target multiple is at most 1.25x the current multiple (no larger re-rating in 12 months)
CONSENSUS_CAP = 1.15  # blended target is at most 1.15x the highest analyst target
FCF_TO_PAT_LOW = 0.5  # below this, historical free cash flow is flagged as unrepresentative for the DCF

# Bear / bull cases: change to forward earnings (or book value) and to the multiple.
SCENARIOS = {
    "Bear": {"earnings": -0.15, "multiple": 0.80, "text": "earnings 15% below base; multiple 20% below the lower "
                                                          "of current and target"},
    "Base": {"earnings": 0.0, "multiple": 1.0, "text": "forward earnings and target multiple as used in the "
                                                        "relative method"},
    "Bull": {"earnings": 0.10, "multiple": 1.15, "text": "earnings 10% above base; multiple 15% above target"},
}


def cost_of_capital(beta: float | None, market_cap: float | None, debt: float | None, a: dict) -> dict:
    raw = num(beta) if num(beta) is not None else 1.0
    # Blume adjustment pulls a 1-year raw beta towards 1, then bounds it.
    b = clamp(0.67 * raw + 0.33, 0.7, 1.5)
    coe = a["risk_free"] + b * a["equity_risk_premium"]
    kd = a["cost_of_debt"] * (1 - a["tax_rate"] / 100)
    e = max(num(market_cap) or 0.0, 0.0)
    d = max(num(debt) or 0.0, 0.0)
    we = e / (e + d) if (e + d) > 0 else 1.0
    wacc = max(we * coe + (1 - we) * kd, a["wacc_floor"])
    return {"beta_raw": raw, "beta_used": b, "cost_of_equity": coe, "cost_of_debt_post_tax": kd, "weight_equity": we * 100,
            "wacc": wacc}


def dcf_enterprise_value(base_fcf: float, g1: float, g_term: float, wacc: float,
                         high_years: int = 5, total_years: int = 10) -> dict:
    """Two-stage FCF DCF. Growth g1 for high_years, then linear fade to g_term by total_years."""
    if wacc <= g_term:
        raise ValueError("WACC must exceed terminal growth.")
    pv, f, flows = 0.0, base_fcf, []
    fade_years = total_years - high_years
    for y in range(1, total_years + 1):
        g = g1 if y <= high_years else g1 - (g1 - g_term) * (y - high_years) / fade_years
        f *= 1 + g / 100
        d = (1 + wacc / 100) ** y
        pv += f / d
        flows.append({"year": y, "growth": g, "fcf": f, "pv": f / d})
    tv = f * (1 + g_term / 100) / (wacc / 100 - g_term / 100)
    pv_tv = tv / (1 + wacc / 100) ** total_years
    ev = pv + pv_tv
    return {"ev": ev, "pv_explicit": pv, "pv_terminal": pv_tv, "terminal_share": pv_tv / ev * 100 if ev else None,
            "flows": flows}


def justified_pb(roe: float, g: float, coe: float) -> float | None:
    if coe <= g or roe <= g:
        return None
    return (roe - g) / (coe - g)


def target_multiple(anchors: list[float], current: float | None, lo: float, hi: float) -> tuple[float | None, str | None]:
    """Median of the anchors, bounded, then capped at RERATE_CAP x the current multiple."""
    anchors = [x for x in anchors if x]
    if not anchors:
        return None, None
    m = clamp(median(anchors), lo, hi)
    if current and current > 0 and m > RERATE_CAP * current:
        return RERATE_CAP * current, (f"Re-rating capped: the history and peer anchor of {fmt_x(m, 1)} is more than "
                                      f"{RERATE_CAP}x the current {fmt_x(current, 1)}, so {fmt_x(RERATE_CAP * current, 1)}"
                                      " is used.")
    return m, None


def scenarios(base_value_per_unit: float | None, base_multiple: float | None, current_multiple: float | None,
              cmp: float, unit: str, mult_name: str) -> list[dict]:
    """Bear, base and bull values from forward earnings (or book value) and a multiple."""
    if not base_value_per_unit or not base_multiple:
        return []
    out = []
    for case, s in SCENARIOS.items():
        units = base_value_per_unit * (1 + s["earnings"])
        if case == "Bear":
            mult = min(x for x in (base_multiple, current_multiple) if x) * s["multiple"]
        else:
            mult = base_multiple * s["multiple"]
        val = units * mult
        out.append({"case": case, unit: units, "multiple": mult, "value": val, "upside": (val / cmp - 1) * 100,
                    "assumption": s["text"], "multiple_name": mult_name})
    return out


def value(cmp: float, info: dict, fund: dict, tech: dict, peer_medians: dict, a: dict | None = None) -> dict:
    a = {**ASSUMPTIONS, **(a or {})}
    fin = fund["is_financial"]
    annual = fund["annual"]
    last = annual[-1] if annual else {}
    growth = fund["growth"]
    shares = fund["shares"]
    mcap = num(info.get("marketCap")) or (cmp * shares if shares else None)
    debt = last.get("total_debt") if last else None
    if debt is None:
        debt = num(info.get("totalDebt"))
    beta = tech.get("beta_1y") if tech.get("beta_1y") is not None else num(info.get("beta"))
    coc = cost_of_capital(beta, mcap, 0 if fin else debt, a)

    # Dividend yield from last fiscal-year dividends, fallback to the source figure (already percent).
    dps = last.get("dps_adj") if last else None
    dy = safe_div(dps, cmp) * 100 if dps and cmp else num(info.get("dividendYield"))
    dy = dy or 0.0

    # Trailing EPS excluding one-offs; the source's own trailing EPS is the last resort.
    trailing, trailing_basis = fund.get("trailing_eps"), fund.get("trailing_basis")
    if not trailing and num(info.get("trailingEps")):
        trailing, trailing_basis = num(info.get("trailingEps")), "source trailing EPS (one-offs not removed)"
    pe_now = safe_div(cmp, trailing) if trailing and trailing > 0 else None
    bvps_now = num(info.get("bookValue")) or last.get("bvps_adj")
    pb_now = safe_div(cmp, bvps_now)

    methods = []
    adjustments: list[str] = []
    fwd, fwd_growth, scen = None, None, []

    # ---------- Method A: relative multiple ----------
    if not fin:
        fwd_src = num(info.get("forwardEps"))
        eps_cagr = growth.get("eps")
        if fwd_src and trailing and trailing > 0 and 0.5 <= fwd_src / trailing <= FWD_EPS_CAP:
            fwd, fwd_note = fwd_src, "consensus forward EPS"
        elif fwd_src and trailing and trailing > 0 and fwd_src / trailing > FWD_EPS_CAP:
            # A historical P/E applied to a sharp earnings rebound double counts the recovery.
            fwd = trailing * FWD_EPS_CAP
            fwd_note = (f"consensus {fmt_rs(fwd_src)} is {fwd_src / trailing:.1f}x trailing; "
                        f"capped at {FWD_EPS_CAP}x")
        elif fwd_src and not trailing:
            fwd, fwd_note = fwd_src, "consensus forward EPS"
        elif trailing and trailing > 0:
            g = clamp(eps_cagr if eps_cagr is not None else 8.0, -10.0, FWD_GROWTH_MAX)
            fwd, fwd_note = trailing * (1 + g / 100), f"trailing EPS grown at {g:.1f}%"
        else:
            fwd, fwd_note = None, "EPS not positive"
        if fwd and trailing and trailing > 0:
            fwd_growth = (fwd / trailing - 1) * 100
        tm, cap_note = target_multiple([fund.get("pe_history_median"), peer_medians.get("pe")], pe_now, 5.0, 80.0)
        if cap_note:
            adjustments.append(cap_note)
        val = fwd * tm if fwd and fwd > 0 and tm else None
        methods.append({
            "key": "relative", "name": "Relative P/E", "value": val,
            "inputs": {"Trailing EPS": f"{fmt_rs(trailing)} ({trailing_basis or '-'})",
                       "Forward EPS (12m)": f"{fmt_rs(fwd)} ({fwd_note})",
                       "Own FY-end P/E median": fmt_x(fund.get("pe_history_median")),
                       "Peer median P/E": fmt_x(peer_medians.get("pe")), "Current P/E": fmt_x(pe_now),
                       "Target P/E applied": fmt_x(tm) + (f" (capped at {RERATE_CAP}x current)" if cap_note else "")},
            "note": None if val else "Not computed: forward EPS or P/E anchor unavailable.",
        })
        scen = scenarios(fwd, tm, pe_now, cmp, "eps", "P/E")
    else:
        roe = last.get("roe") or (num(info.get("returnOnEquity")) or 0) * 100 or None
        payout = last.get("payout") if last.get("payout") is not None else 25.0
        bvps_fwd = bvps_now * (1 + (roe or 0) * (1 - payout / 100) / 100) if bvps_now else None
        tm, cap_note = target_multiple([fund.get("pb_history_median"), peer_medians.get("pb")], pb_now, 0.5, 15.0)
        if cap_note:
            adjustments.append(cap_note)
        val = bvps_fwd * tm if bvps_fwd and tm else None
        methods.append({
            "key": "relative", "name": "Relative P/B", "value": val,
            "inputs": {"Book value per share": fmt_rs(bvps_now), "Forward book value (12m)": fmt_rs(bvps_fwd),
                       "Own FY-end P/B median": fmt_x(fund.get("pb_history_median"), 2),
                       "Peer median P/B": fmt_x(peer_medians.get("pb"), 2), "Current P/B": fmt_x(pb_now, 2),
                       "Target P/B applied": fmt_x(tm, 2) + (f" (capped at {RERATE_CAP}x current)" if cap_note
                                                             else "")},
            "note": None if val else "Not computed: book value or P/B anchor unavailable.",
        })
        scen = scenarios(bvps_fwd, tm, pb_now, cmp, "bvps", "P/B")

    # ---------- Method B: intrinsic ----------
    roll = 1 + (coc["cost_of_equity"] - dy) / 100
    fcf_to_pat = None
    if not fin:
        fcfs = [r["fcf"] for r in annual[-3:] if r.get("fcf") is not None]
        pats = [r["pat_norm"] for r in annual[-3:] if r.get("fcf") is not None and r.get("pat_norm") is not None]
        base = sum(fcfs) / len(fcfs) if fcfs else None
        fcf_to_pat = safe_div(sum(fcfs), sum(pats)) if fcfs and pats and sum(pats) > 0 else None
        rev_cagr = growth.get("revenue")
        g1 = clamp(rev_cagr if rev_cagr is not None else 8.0, 3.0, 15.0)
        val, inputs, note = None, {}, None
        if base and base > 0 and shares:
            d = dcf_enterprise_value(base, g1, a["terminal_growth"], coc["wacc"], a["high_growth_years"],
                                     a["explicit_years"])
            net_debt = last.get("net_debt")
            if net_debt is None:
                net_debt = (num(info.get("totalDebt")) or 0) - (num(info.get("totalCash")) or 0)
            equity = d["ev"] - net_debt
            fair = equity / shares if equity > 0 else None
            val = fair * roll if fair else None
            inputs = {"Base FCF (avg of last %d yrs)" % len(fcfs): "Rs " + fmt_cr(base) + " cr",
                      "FCF / net profit (same years)": fmt_x(fcf_to_pat, 2),
                      "Growth yrs 1-5 (fades to terminal by yr 10)": fmt_pct(g1),
                      "Terminal growth": fmt_pct(a["terminal_growth"]), "WACC": fmt_pct(coc["wacc"]),
                      "Enterprise value": "Rs " + fmt_cr(d["ev"]) + " cr",
                      "Less net debt": "Rs " + fmt_cr(net_debt) + " cr",
                      "Terminal value share of EV": fmt_pct(d["terminal_share"], 0),
                      "Fair value today": fmt_rs(fair)}
            if not fair:
                note = "Not computed: net debt exceeds DCF enterprise value."
        else:
            note = "Not computed: average free cash flow is not positive (common for capex-heavy years)."
        methods.append({"key": "intrinsic", "name": "Discounted cash flow", "value": val, "inputs": inputs,
                        "note": note})
    else:
        roes = [r["roe"] for r in annual[-3:] if r.get("roe") is not None]
        roe = sum(roes) / len(roes) if roes else ((num(info.get("returnOnEquity")) or 0) * 100 or None)
        payout = last.get("payout") if last.get("payout") is not None else 25.0
        val, inputs, note = None, {}, None
        if roe and bvps_now:
            g = clamp(roe * (1 - payout / 100), 0.0, min(10.0, coc["cost_of_equity"] - 1.0))
            pbj = justified_pb(roe, g, coc["cost_of_equity"])
            bvps_fwd = bvps_now * (1 + roe * (1 - payout / 100) / 100)
            val = pbj * bvps_fwd if pbj else None
            inputs = {"Average ROE (3 yrs)": fmt_pct(roe), "Sustainable growth": fmt_pct(g),
                      "Cost of equity": fmt_pct(coc["cost_of_equity"]), "Justified P/B": fmt_x(pbj, 2),
                      "Forward book value": fmt_rs(bvps_fwd)}
            if not pbj:
                note = "Not computed: ROE does not exceed sustainable growth."
        else:
            note = "Not computed: ROE or book value unavailable."
        methods.append({"key": "intrinsic", "name": "Justified P/B (Gordon growth)", "value": val,
                        "inputs": inputs, "note": note})

    # ---------- Method C: consensus ----------
    n_an = int(num(info.get("numberOfAnalystOpinions")) or 0)
    tmean = num(info.get("targetMeanPrice"))
    thigh = num(info.get("targetHighPrice"))
    rk = info.get("recommendationKey")
    view = rk.replace("_", " ").title() if rk and rk.lower() != "none" else None
    cval = tmean if tmean and n_an >= 3 else None
    methods.append({
        "key": "consensus", "name": "Street consensus", "value": cval,
        "inputs": {"Analysts": str(n_an), "Mean target": fmt_rs(tmean),
                   "Low / high target": f"{fmt_rs(num(info.get('targetLowPrice')))} / {fmt_rs(thigh)}",
                   "Consensus view": view or "-"},
        "note": None if cval else "Not used: fewer than 3 analysts or no target available.",
    })

    # ---------- Blend ----------
    lo, hi = BOUNDS
    for m in methods:
        v = m["value"]
        m["included"] = bool(v and lo * cmp <= v <= hi * cmp)
        if v and not m["included"]:
            m["note"] = (f"Excluded as an outlier: {fmt_rs(v)} is outside {lo}x to {hi}x of the current price.")
            if m["key"] == "intrinsic" and not fin and fcf_to_pat is not None and fcf_to_pat < FCF_TO_PAT_LOW:
                m["note"] += (f" Free cash flow was only {fmt_x(fcf_to_pat, 2)} of net profit over the base years "
                              "(capex and working capital absorbed cash), so a DCF on historical cash flow "
                              "understates value while the company invests for growth. The gap is still a warning: "
                              "the price assumes cash generation the company has not yet shown.")
        m["base_weight"] = WEIGHTS[m["key"]] * 100
    total_w = sum(WEIGHTS[m["key"]] for m in methods if m["included"])
    target = None
    for m in methods:
        m["weight"] = WEIGHTS[m["key"]] / total_w * 100 if m["included"] and total_w else 0.0
    if total_w:
        target = sum(m["value"] * m["weight"] / 100 for m in methods if m["included"])
    used = [m["value"] for m in methods if m["included"]]
    dispersion = (max(used) - min(used)) / target * 100 if target and len(used) > 1 else None
    target_uncapped = target

    # Consensus divergence cap: the model may not run far ahead of the most optimistic analyst.
    if target and thigh and n_an >= 3 and target > CONSENSUS_CAP * thigh:
        target = CONSENSUS_CAP * thigh
        adjustments.append(f"Target capped at {fmt_rs(target)}: the blended value of {fmt_rs(target_uncapped)} is more "
                           f"than {CONSENSUS_CAP}x the highest of {n_an} analyst targets ({fmt_rs(thigh)}).")

    # Excluded methods that point the other way from the target lower conviction.
    conflicts = []
    if target:
        for m in methods:
            v = m["value"]
            if v and not m["included"] and ((target > cmp and v < 0.8 * cmp) or (target < cmp and v > 1.2 * cmp)):
                conflicts.append(f"{m['name']} gives {fmt_rs(v)}, on the other side of the current price from the "
                                 f"target of {fmt_rs(target)}.")

    # Current multiples
    peg = safe_div(pe_now, fwd_growth) if pe_now and fwd_growth and fwd_growth > 0 else None
    ev = (mcap or 0) + (last.get("net_debt") or 0) if mcap else None
    ev_ebitda = safe_div(ev, last.get("ebitda")) if not fin and last.get("ebitda") and last["ebitda"] > 0 else None
    fcf_yield = safe_div(last.get("fcf"), mcap) * 100 if not fin and last.get("fcf") is not None and mcap else None

    return {
        "cmp": cmp,
        "target": target,
        "target_before_caps": target_uncapped,
        "upside": (target / cmp - 1) * 100 if target else None,
        "methods": methods,
        "methods_used": len(used),
        "dispersion": dispersion,
        "adjustments": adjustments,
        "excluded_conflicts": conflicts,
        "trailing_eps": trailing,
        "trailing_basis": trailing_basis,
        "forward_eps": fwd,
        "forward_growth": fwd_growth,
        "scenarios": scen,
        "cost_of_capital": coc,
        "assumptions": a,
        "dividend_yield": dy,
        "multiples": {
            "pe": pe_now, "pb": pb_now, "peg": peg, "ev_ebitda": ev_ebitda, "fcf_yield": fcf_yield,
            "pe_vs_history": safe_div(pe_now, fund.get("pe_history_median")),
            "pb_vs_history": safe_div(pb_now, fund.get("pb_history_median")),
            "pe_vs_peers": safe_div(pe_now, peer_medians.get("pe")),
            "pb_vs_peers": safe_div(pb_now, peer_medians.get("pb")),
            "market_cap": mcap,
            "enterprise_value": ev,
        },
        "consensus": {"analysts": n_an, "mean": tmean, "low": num(info.get("targetLowPrice")),
                      "high": thigh, "view": view},
    }
