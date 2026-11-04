# -*- coding: utf-8 -*-
"""
Second hand vessel valuation - financial model engine.

All background calculations (timing, commissions, loan schedule, dry-docking plan,
straight-line depreciation, monthly cash flow, XIRR, payback, MOIC, ROI, DSCR)
run in this file. build_html() writes a self-contained HTML investment report.

Standard library only - no third-party packages are needed for this file.
"""

import calendar
import html
import re
from datetime import date, datetime

APP_TITLE = "Second hand vessel valuation"

VESSEL_TYPES = ["Handysize", "Handymax", "Supramax", "Ultramax", "Panamax", "Kamsarmax", "Cape Size"]
PAYMENT_FREQ = ["Monthly", "Quarterly"]
USEFUL_LIFE_YEARS = 25.0
DAYS_PER_YEAR = 365.0
TCE_SLOTS = 4
DD_SLOTS = 10
TCE_LABELS = ["1A. First period", "1B. Second period", "1C. Third period", "1D. Fourth period"]

DEFAULT_INPUTS = {
    "vessel_name": "MV Example Star",
    "vessel_type": "Supramax",
    "analysis_date": "2026-11-02",
    "purchase_date": "2026-12-01",
    "delivery_date": "2016-06-15",
    "next_drydock_date": "2027-03-01",
    "purchase_price": 14500000.0,
    "lwt": 9800.0,
    "working_capital": 500000.0,
    "legal_fees": 150000.0,
    "use_full_life": False,
    "operating_years": 14.0,
    "offhire_days": 5.0,
    "tce1_months": 36, "tce1_rate": 13000.0,
    "tce2_months": 48, "tce2_rate": 14000.0,
    "tce3_months": 48, "tce3_rate": 12000.0,
    "tce4_months": 36, "tce4_rate": 13500.0,
    "addr_comm_pct": 2.5,
    "broker_comm_pct": 1.25,
    "mgr_cost_day": 950.0, "mgr_escalation": 3.0,
    "ins_cost_day": 450.0, "ins_escalation": 2.5,
    "dd_std_interval": 5.0,
    "dd_threshold_age": 15.0,
    "dd_alt_interval": 2.5,
    "equity_pct": 35.0,
    "upfront_fee_pct": 1.0,
    "interest_rate": 6.5,
    "loan_tenure": 8.0,
    "balloon_pct": 20.0,
    "payment_freq": "Quarterly",
    "scrap_rate": 400.0,
    "exit_premium": 0.0,
    "sp_fee_pct": 1.0,
    "target_irr": 12.0,
    "min_dscr": 1.25,
}
DEFAULT_INPUTS.update({f"dd_{k}_cost": 1200000.0 + 50000.0 * (k - 1) for k in range(1, DD_SLOTS + 1)})


class ModelError(Exception):
    """Raised when inputs fail validation. .errors holds the readable messages."""

    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = list(errors)


# ---------------------------------------------------------------- helpers

def _num(inp, key, default=0.0):
    try:
        return float(inp.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def add_months(d, months):
    total = d.month - 1 + int(months)
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def safe_filename(text):
    """Remove characters Windows does not allow in file names."""
    cleaned = re.sub(r'[\\/:*?"<>|]+', " ", str(text))
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(".")
    return cleaned or "Vessel analysis"


def derive_timing(inp):
    """Age at purchase and remaining useful life (25 years less age), in years."""
    purchase = to_date(inp["purchase_date"])
    delivery = to_date(inp["delivery_date"])
    age_years = (purchase - delivery).days / 365.25
    return age_years, USEFUL_LIFE_YEARS - age_years


def dd_schedule_dates(delivery, purchase, exit_date, std_years, threshold_years, alt_years):
    """
    Dry-dock dates counted in months from the delivery date from the yard:
    every std_years while the vessel is younger than threshold_years, then every
    alt_years. Only dates from purchase up to (not including) exit are returned.
    """
    threshold_m = int(round(threshold_years * 12))
    std_m = max(1, int(round(std_years * 12)))
    alt_m = max(1, int(round(alt_years * 12)))
    dates = []
    offset = 0
    for _ in range(300):
        step = std_m if offset < threshold_m else alt_m
        offset += step
        d = add_months(delivery, offset)
        if d >= exit_date:
            break
        if d >= purchase:
            dates.append(d)
    return dates


def xirr(flows):
    """Annual XIRR on actual dates (365-day year). flows = [(date, amount), ...]."""
    if not (any(a > 0 for _, a in flows) and any(a < 0 for _, a in flows)):
        return None
    d0 = flows[0][0]
    pts = [((d - d0).days / DAYS_PER_YEAR, a) for d, a in flows if a != 0]

    def npv(rate):
        return sum(a / (1.0 + rate) ** t for t, a in pts)

    lo, hi = -0.99, 10.0
    f_lo = npv(lo)
    if f_lo * npv(hi) > 0:
        return None
    for _ in range(300):
        mid = (lo + hi) / 2.0
        f_mid = npv(mid)
        if f_lo * f_mid <= 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
        if hi - lo < 1e-10:
            break
    return (lo + hi) / 2.0


def preview(inp):
    """Quick derived figures for the input screen. Never raises."""
    out = {}
    try:
        age, rul = derive_timing(inp)
        pp = _num(inp, "purchase_price")
        op_years = rul if bool(inp.get("use_full_life", True)) else _num(inp, "operating_years")
        op_months = int(round(op_years * 12))
        purchase = to_date(inp["purchase_date"])
        delivery = to_date(inp["delivery_date"])
        exit_date = add_months(purchase, max(op_months, 0))
        upfront = pp * _num(inp, "upfront_fee_pct") / 100.0
        legal = _num(inp, "legal_fees")
        wc = _num(inp, "working_capital")
        equity = pp * _num(inp, "equity_pct") / 100.0
        dates = dd_schedule_dates(delivery, purchase, exit_date,
                                  _num(inp, "dd_std_interval"), _num(inp, "dd_threshold_age"),
                                  _num(inp, "dd_alt_interval"))
        out.update(
            age=age, rul=rul, op_years=op_years, op_months=op_months,
            exit_date=exit_date,
            tce_months=sum(int(_num(inp, f"tce{k}_months")) for k in range(1, TCE_SLOTS + 1)),
            upfront=upfront, equity=equity, debt=pp - equity,
            scrap=_num(inp, "lwt") * _num(inp, "scrap_rate"),
            uses=pp + upfront + legal + wc,
            dd_dates=[(d, (d - delivery).days / 365.25) for d in dates],
        )
    except Exception:
        pass
    return out


# ---------------------------------------------------------------- engine

def run_model(inp):
    """Validate inputs, run the monthly model and return a results dictionary."""
    errors, warnings, checks = [], [], []

    def check(label, ok, detail, blocking=True):
        checks.append({"label": label, "ok": bool(ok), "detail": detail})
        if blocking and not ok:
            errors.append(f"{label}: {detail}")

    # ---------- 1. Validation (blocking) ----------
    name = str(inp.get("vessel_name", "")).strip()
    check("Vessel name", name != "", "Please enter the vessel name.")
    purchase = to_date(inp["purchase_date"])
    delivery = to_date(inp["delivery_date"])
    next_dd = to_date(inp["next_drydock_date"])
    age, rul = derive_timing(inp)
    check("Purchase after delivery from yard", age >= 0,
          f"Age at purchase is {age:.2f} years; purchase date cannot precede delivery.")
    check("Remaining useful life", rul > 0,
          f"Remaining useful life is {rul:.2f} years (vessel is beyond 25 years).")

    pp = _num(inp, "purchase_price")
    check("Purchase price", pp > 0, "Purchase price must be greater than zero.")

    full_life = bool(inp.get("use_full_life", True))
    op_years = rul if full_life else _num(inp, "operating_years")
    op_months = int(round(op_years * 12))
    check("Operating period", op_months >= 1, "Operating period must be at least one month.")
    check("Operating period within maximum useful life", op_years <= rul + 1e-9,
          f"Operating period {op_years:.2f} years exceeds the maximum (remaining useful life "
          f"{rul:.2f} years, i.e. 25 years from delivery).")

    tce_inputs = [
        {"label": TCE_LABELS[k - 1], "months": int(_num(inp, f"tce{k}_months")), "rate": _num(inp, f"tce{k}_rate")}
        for k in range(1, TCE_SLOTS + 1)
    ]
    tce_total = sum(t["months"] for t in tce_inputs)
    check("Revenue periods match operating period", tce_total == op_months,
          f"TCE periods add up to {tce_total} months but the operating period is {op_months} months.")
    check("TCE periods", all(t["months"] >= 0 for t in tce_inputs),
          "Months in each TCE period cannot be negative.")

    addr_pct = _num(inp, "addr_comm_pct") / 100.0
    brok_pct = _num(inp, "broker_comm_pct") / 100.0
    check("Commission rates", addr_pct >= 0 and brok_pct >= 0 and addr_pct + brok_pct < 1,
          "Commission rates must be zero or positive and total less than 100%.")

    lwt = _num(inp, "lwt")
    scrap_value = lwt * _num(inp, "scrap_rate")
    check("Scrap value", 0 <= scrap_value < pp,
          f"Scrap value (USD {scrap_value:,.0f}) must be below the purchase price.")

    eq_pct = _num(inp, "equity_pct")
    check("Equity portion", 0 <= eq_pct <= 100, "Equity portion must be between 0% and 100%.")

    freq = 12 if inp.get("payment_freq") == "Monthly" else 4
    mpp = 12 // freq
    tenure = _num(inp, "loan_tenure")
    n_pay = int(round(tenure * freq))
    check("Loan tenure", n_pay >= 1, "Loan tenure must allow at least one repayment.")
    check("Loan tenure within operating period", tenure <= op_years + 1e-9,
          f"Loan tenure ({tenure:.2f} years) cannot exceed the operating period ({op_years:.2f} years).")

    std_interval = _num(inp, "dd_std_interval")
    threshold_age = _num(inp, "dd_threshold_age")
    alt_interval = _num(inp, "dd_alt_interval")
    check("Dry-dock intervals", std_interval > 0 and alt_interval > 0,
          "Dry-dock intervals must be positive.")
    check("Dry-dock age threshold", threshold_age >= 0, "Dry-dock age threshold cannot be negative.")
    check("Off-hire days", 0 <= _num(inp, "offhire_days") <= DAYS_PER_YEAR,
          "Off-hire days must be between 0 and 365.")

    if errors:
        raise ModelError(errors)

    # ---------- 2. Timing, depreciation and exit ----------
    exit_date = add_months(purchase, op_months)
    rate_period = _num(inp, "interest_rate") / 100.0 / freq

    dep_base = pp - scrap_value
    dep_per_year = dep_base / rul
    bv_exit = max(pp - dep_per_year * op_months / 12.0, 0.0)
    sale_price = bv_exit * (1 + _num(inp, "exit_premium") / 100.0)
    sp_fee = sale_price * _num(inp, "sp_fee_pct") / 100.0

    # ---------- 3. Funding ----------
    wc = _num(inp, "working_capital")
    legal = _num(inp, "legal_fees")
    equity_infusion = pp * eq_pct / 100.0
    debt = pp - equity_infusion
    upfront_fee = pp * _num(inp, "upfront_fee_pct") / 100.0
    equity_t0 = equity_infusion + upfront_fee + legal + wc
    total_uses = pp + upfront_fee + legal + wc
    balloon_amt = debt * _num(inp, "balloon_pct") / 100.0

    if rate_period == 0:
        payment = (debt - balloon_amt) / n_pay
    else:
        g = (1 + rate_period) ** n_pay
        payment = (debt * g - balloon_amt) * rate_period / (g - 1)

    # ---------- 4. Dry-dock schedule (future dockings only) ----------
    dd_costs = [_num(inp, f"dd_{k}_cost") for k in range(1, DD_SLOTS + 1)]
    dd_dates = dd_schedule_dates(delivery, purchase, exit_date, std_interval, threshold_age, alt_interval)
    dd_events = [
        {"no": k, "date": d, "cost": dd_costs[min(k, DD_SLOTS) - 1], "age": (d - delivery).days / 365.25}
        for k, d in enumerate(dd_dates, start=1)
    ]
    if dd_dates and (dd_dates[0].year, dd_dates[0].month) != (next_dd.year, next_dd.month):
        warnings.append(
            f"Next dry-dock per records ({next_dd:%d-%b-%Y}) differs from the schedule counted from "
            f"delivery ({dd_dates[0]:%d-%b-%Y}). The schedule from the delivery date is used.")

    bounds = [(add_months(purchase, m), add_months(purchase, m + 1)) for m in range(op_months)]
    dd_month = {}
    for ev in dd_events:
        for m, (s, e) in enumerate(bounds):
            if s <= ev["date"] < e:
                ev["year"] = m // 12 + 1
                dd_month[m] = dd_month.get(m, 0.0) + ev["cost"]
                break
    dd_events = [ev for ev in dd_events if "year" in ev]

    # ---------- 5. Revenue periods ----------
    rates, period_of = [], []
    for idx, t in enumerate(tce_inputs, start=1):
        rates += [t["rate"]] * t["months"]
        period_of += [idx] * t["months"]
        if t["months"] > 0 and t["rate"] <= 0:
            warnings.append(f"{t['label']} has {t['months']} months but a zero TCE rate; no revenue is earned.")

    # ---------- 6. Monthly cash flow ----------
    mgr_day = _num(inp, "mgr_cost_day")
    mgr_esc = _num(inp, "mgr_escalation") / 100.0
    ins_day = _num(inp, "ins_cost_day")
    ins_esc = _num(inp, "ins_escalation") / 100.0
    offhire = _num(inp, "offhire_days")

    rows = []
    balance = debt
    for m, (start, end) in enumerate(bounds):
        days = (end - start).days
        year_idx = m // 12
        off_days = offhire * days / DAYS_PER_YEAR
        gross = rates[m] * (days - off_days)
        addr = gross * addr_pct
        brok = gross * brok_pct
        revenue = gross - addr - brok                        # net of commissions
        mgr = mgr_day * days * (1 + mgr_esc) ** year_idx
        ins = ins_day * days * (1 + ins_esc) ** year_idx
        dd_cost = dd_month.get(m, 0.0)
        cfads = revenue - mgr - ins - dd_cost

        interest = principal = 0.0
        if balance > 0.005 and (m + 1) % mpp == 0:
            pay_no = (m + 1) // mpp
            if pay_no <= n_pay:
                interest = balance * rate_period
                if pay_no == n_pay:
                    principal = balance                      # final instalment clears the balloon
                else:
                    principal = min(balance, max(payment - interest, 0.0))
                balance -= principal
        debt_service = interest + principal

        exit_sale = exit_fee = exit_debt = wc_back = 0.0
        if m == op_months - 1:
            exit_sale, exit_fee, wc_back = sale_price, sp_fee, wc
            exit_debt = balance                              # outstanding loan repaid from sale
            balance = 0.0
        exit_net = exit_sale - exit_fee - exit_debt + wc_back
        equity_cf = cfads - debt_service + exit_net

        rows.append({
            "no": m + 1, "date": end, "start": start, "end": end, "days": days,
            "year": year_idx + 1, "period": period_of[m], "tce": rates[m],
            "offhire_days": off_days, "gross": gross, "addr": addr, "brok": brok,
            "commissions": addr + brok, "revenue": revenue,
            "mgr": mgr, "ins": ins, "dd": dd_cost, "cfads": cfads,
            "interest": interest, "principal": principal, "debt_service": debt_service,
            "balance": balance, "exit_debt": exit_debt, "exit_net": exit_net, "equity_cf": equity_cf,
        })

    tce_out = []
    for idx, t in enumerate(tce_inputs, start=1):
        seg = [r for r in rows if r["period"] == idx]
        tce_out.append({
            "label": t["label"], "months": t["months"], "rate": t["rate"],
            "days": sum(r["days"] for r in seg),
            "gross": sum(r["gross"] for r in seg),
            "commissions": sum(r["commissions"] for r in seg),
            "revenue": sum(r["revenue"] for r in seg),
        })

    # ---------- 7. Annual summary ----------
    n_years = (op_months + 11) // 12
    annual = [{
        "label": "Y0", "period": f"{purchase:%d-%b-%Y} (acquisition)",
        "gross": 0.0, "commissions": 0.0, "revenue": 0.0, "mgr": 0.0, "ins": 0.0, "dd": 0.0,
        "cfads": 0.0, "interest": 0.0, "principal": 0.0, "debt_service": 0.0, "exit_net": 0.0,
        "equity_cf": -equity_t0, "dscr": None,
    }]
    for y in range(1, n_years + 1):
        yr_rows = [r for r in rows if r["year"] == y]
        agg = {key: sum(r[key] for r in yr_rows)
               for key in ("gross", "commissions", "revenue", "mgr", "ins", "dd", "cfads", "interest",
                           "principal", "debt_service", "exit_net", "equity_cf")}
        agg["label"] = f"Y{y}"
        agg["period"] = f"{yr_rows[0]['start']:%b-%Y} to {yr_rows[-1]['end']:%b-%Y}"
        agg["dscr"] = agg["cfads"] / agg["debt_service"] if agg["debt_service"] > 0.005 else None
        annual.append(agg)
    cum = 0.0
    for a in annual:
        cum += a["equity_cf"]
        a["cumulative"] = cum

    # ---------- 8. Returns and metrics ----------
    flows = [(purchase, -equity_t0)] + [(r["date"], r["equity_cf"]) for r in rows]
    irr = xirr(flows)

    payback_years = None
    if equity_t0 <= 0:
        payback_years = 0.0
    else:
        running = -equity_t0
        for i, r in enumerate(rows):
            prev = running
            running += r["equity_cf"]
            if prev < 0 <= running:
                payback_years = (i + (-prev) / r["equity_cf"]) / 12.0
                break

    total_inflows = sum(a for _, a in flows if a > 0)
    total_outflows = -sum(a for _, a in flows if a < 0)
    moic = total_inflows / total_outflows if total_outflows > 0 else None
    net_profit = sum(a for _, a in flows)
    roi_total = net_profit / total_outflows if total_outflows > 0 else None
    years = op_months / 12.0
    roi_annual = None
    if roi_total is not None:
        roi_annual = (1 + roi_total) ** (1 / years) - 1 if roi_total > -1 else -1.0

    dscrs = [a["dscr"] for a in annual[1:] if a["dscr"] is not None]
    min_dscr_val = min(dscrs) if dscrs else None
    avg_dscr_val = sum(dscrs) / len(dscrs) if dscrs else None

    target_irr = _num(inp, "target_irr") / 100.0
    min_dscr_target = _num(inp, "min_dscr")

    viable = True
    reasons = []
    if irr is None:
        viable = False
        reasons.append("Equity XIRR cannot be calculated because the cash flows do not change sign.")
    elif irr < target_irr:
        viable = False
        reasons.append(f"Equity XIRR of {irr * 100:.1f}% is below the {target_irr * 100:.1f}% hurdle.")
    else:
        reasons.append(f"Equity XIRR of {irr * 100:.1f}% meets the {target_irr * 100:.1f}% hurdle.")
    if min_dscr_val is not None:
        if min_dscr_val < min_dscr_target:
            viable = False
            reasons.append(f"Minimum DSCR of {min_dscr_val:.2f}x is below the {min_dscr_target:.2f}x minimum.")
        else:
            reasons.append(f"Minimum DSCR of {min_dscr_val:.2f}x meets the {min_dscr_target:.2f}x minimum.")

    if payback_years is None:
        warnings.append("Equity is not paid back within the operating period.")
    if sale_price <= 0:
        warnings.append("Exit sale value is zero or negative; check the premium/discount input.")

    check("Equity XIRR computable", irr is not None,
          "Equity cash flows must include both outflows and inflows.", blocking=False)
    check("Exit sale value positive", sale_price > 0,
          f"Exit sale value is USD {sale_price:,.0f}.", blocking=False)
    check("Equity paid back within operating period", payback_years is not None,
          "Cumulative equity cash flow does not turn positive during the operating period.", blocking=False)
    check("Future dry-dockings in operating period", True, f"{len(dd_events)} dry-docking(s) scheduled.")

    return {
        "name": name,
        "purchase_date": purchase,
        "delivery_date": delivery,
        "exit_date": exit_date,
        "age_years": age,
        "rul_years": rul,
        "op_years": years,
        "op_months": op_months,
        "lwt": lwt,
        "pp": pp,
        "wc": wc,
        "legal": legal,
        "upfront_fee": upfront_fee,
        "equity_infusion": equity_infusion,
        "debt": debt,
        "equity_t0": equity_t0,
        "total_uses": total_uses,
        "scrap_value": scrap_value,
        "dep_base": dep_base,
        "dep_per_year": dep_per_year,
        "bv_exit": bv_exit,
        "sale_price": sale_price,
        "sp_fee": sp_fee,
        "balloon_amt": balloon_amt,
        "payment": payment,
        "n_pay": n_pay,
        "freq": freq,
        "dd_events": dd_events,
        "tce_periods": tce_out,
        "rows": rows,
        "annual": annual,
        "irr": irr,
        "payback_years": payback_years,
        "moic": moic,
        "roi_total": roi_total,
        "roi_annual": roi_annual,
        "total_inflows": total_inflows,
        "total_outflows": total_outflows,
        "net_profit": net_profit,
        "min_dscr": min_dscr_val,
        "avg_dscr": avg_dscr_val,
        "total_gross": sum(r["gross"] for r in rows),
        "total_commissions": sum(r["commissions"] for r in rows),
        "total_revenue": sum(r["revenue"] for r in rows),
        "viable": viable,
        "reasons": reasons,
        "warnings": warnings,
        "checks": checks,
    }


# ---------------------------------------------------------------- HTML report

def esc(x):
    return html.escape(str(x))


def _usd(x):
    return "-" if x is None else f"USD {x:,.0f}"


def _acc(x, dec=0):
    if x is None:
        return "-"
    s = f"{abs(x):,.{dec}f}"
    return f"({s})" if x < -0.5 * 10 ** (-dec) else s


def _pct(x, dec=1):
    return "-" if x is None else f"{x * 100:.{dec}f}%"


def _x(x):
    return "-" if x is None else f"{x:.2f}x"


def _yrs(x):
    return "Not reached" if x is None else f"{x:.2f} yrs"


def _fd(v):
    return f"{to_date(v):%d-%b-%Y}"


def _pos_periods(res):
    """TCE periods that carry both months and a rate. Zero-value periods are not reported."""
    return [p for p in res["tce_periods"] if p["months"] > 0 and p["rate"] > 0]


def _table(headers, rows, num_cols=(), total_last=False):
    head = "".join(
        '<th class="num">' + esc(h) + "</th>" if i in num_cols else "<th>" + esc(h) + "</th>"
        for i, h in enumerate(headers))
    body = []
    for ri, row in enumerate(rows):
        row_cls = ' class="total"' if total_last and ri == len(rows) - 1 else ""
        cells = []
        for i, c in enumerate(row):
            cls = ' class="num"' if i in num_cols else ""
            cells.append(f"<td{cls}>{esc(c)}</td>")
        body.append(f"<tr{row_cls}>" + "".join(cells) + "</tr>")
    return ('<div class="tablewrap"><table><thead><tr>' + head + "</tr></thead><tbody>"
            + "".join(body) + "</tbody></table></div>")


def _kv_card(title, rows):
    body = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in rows)
    return f'<div class="card"><h3>{esc(title)}</h3><table class="kv">{body}</table></div>'


def _svg_chart(labels, values, cumulative):
    if not labels:
        return ""
    width, height, pad = 920, 320, 48
    lo = min(min(values), min(cumulative), 0.0)
    hi = max(max(values), max(cumulative), 0.0)
    span = (hi - lo) or 1.0

    def ypos(v):
        return pad + (hi - v) / span * (height - 2 * pad)

    n = len(values)
    slot = (width - 2 * pad) / n
    zero = ypos(0.0)
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="Annual equity cash flow">']
    out.append(f'<line x1="{pad}" y1="{zero:.1f}" x2="{width - pad}" y2="{zero:.1f}" '
               'stroke="#94a3b8" stroke-dasharray="4 4"/>')
    for i, v in enumerate(values):
        x = pad + i * slot + slot * 0.18
        top = min(ypos(v), zero)
        h = max(abs(ypos(v) - zero), 1.0)
        color = "#10b981" if v >= 0 else "#f43f5e"
        out.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{slot * 0.64:.1f}" height="{h:.1f}" '
                   f'rx="4" fill="{color}"><title>{esc(labels[i])}: {esc(_acc(v))}</title></rect>')
    pts = " ".join(f"{pad + i * slot + slot / 2:.1f},{ypos(c):.1f}" for i, c in enumerate(cumulative))
    out.append(f'<polyline points="{pts}" fill="none" stroke="#7c3aed" stroke-width="3"/>')
    step = max(1, n // 14)
    for i in range(0, n, step):
        out.append(f'<text x="{pad + i * slot + slot / 2:.1f}" y="{height - 14}" font-size="11" '
                   f'text-anchor="middle" fill="#475569">{esc(labels[i])}</text>')
    out.append("</svg>")
    return "".join(out)


def _assumption_groups(inp, res):
    positive = _pos_periods(res)
    entered = sum(p["months"] for p in res["tce_periods"])
    dd_total = sum(ev["cost"] for ev in res["dd_events"])
    revenue_rows = [
        ("Off-hire days per annum", f"{_num(inp, 'offhire_days'):.1f} days"),
        ("Address commission", f"{_num(inp, 'addr_comm_pct'):.2f}% of gross TCE revenue"),
        ("Broker commission", f"{_num(inp, 'broker_comm_pct'):.2f}% of gross TCE revenue"),
        ("Revenue months entered vs operating months", f"{entered} entered / {res['op_months']} required"),
    ] + [(p["label"], f"{p['months']} months at USD {p['rate']:,.0f} per day") for p in positive]
    return [
        ("Vessel & timing", [
            ("Vessel type", inp["vessel_type"]),
            ("Date of analysis", _fd(inp["analysis_date"])),
            ("Expected date of purchase", _fd(res["purchase_date"])),
            ("Date of delivery from yard", _fd(res["delivery_date"])),
            ("Age at purchase", f"{res['age_years']:.2f} years"),
            ("Remaining useful life (25 years less age)", f"{res['rul_years']:.2f} years"),
            ("Light-weight tonnage (LWT)", f"{res['lwt']:,.0f} t"),
        ]),
        ("Acquisition & extra costs", [
            ("1. Purchase price", _usd(res["pp"])),
            ("6A. Working capital", _usd(res["wc"])),
            ("6B. Upfront finance cost", f"{_num(inp, 'upfront_fee_pct'):.2f}% of purchase price = {_usd(res['upfront_fee'])}"),
            ("6C. Legal / documentation fees", _usd(res["legal"])),
            ("Total acquisition outlay", _usd(res["total_uses"])),
        ]),
        ("Operating period & exit", [
            ("Operating basis", "Full remaining useful life" if inp.get("use_full_life") else "Shortened operating period"),
            ("Maximum operating period (remaining useful life)", f"{res['rul_years']:.2f} years"),
            ("Operating period applied", f"{res['op_years']:.2f} years ({res['op_months']} months)"),
            ("Exit date", _fd(res["exit_date"])),
        ]),
        ("Revenue assumptions", revenue_rows),
        ("Running costs (escalated annually)", [
            ("Ship manager cost", f"USD {_num(inp, 'mgr_cost_day'):,.0f} per day, escalating {_num(inp, 'mgr_escalation'):.2f}% p.a."),
            ("Insurance cost", f"USD {_num(inp, 'ins_cost_day'):,.0f} per day, escalating {_num(inp, 'ins_escalation'):.2f}% p.a."),
        ]),
        ("Dry-docking (counted from delivery date)", [
            ("Standard interval", f"every {_num(inp, 'dd_std_interval'):.1f} years while vessel age is below {_num(inp, 'dd_threshold_age'):.1f} years"),
            ("Interval after threshold", f"every {_num(inp, 'dd_alt_interval'):.1f} years"),
            ("Next dry-dock per class records (cross-check)", _fd(inp["next_drydock_date"])),
            ("Future dry-dockings in operating period", str(len(res["dd_events"]))),
            ("Total future dry-dock cost (estimate)", _usd(dd_total)),
        ]),
        ("Financing", [
            ("Equity portion", f"{_num(inp, 'equity_pct'):.2f}% of purchase price"),
            ("Equity infusion", _usd(res["equity_infusion"])),
            ("Debt (purchase price less equity)", _usd(res["debt"])),
            ("Rate of interest", f"{_num(inp, 'interest_rate'):.2f}% p.a."),
            ("Loan tenure", f"{_num(inp, 'loan_tenure'):.2f} years ({res['n_pay']} repayments)"),
            ("Payment terms", str(inp.get("payment_freq", ""))),
            ("Balloon payment", f"{_num(inp, 'balloon_pct'):.1f}% of debt = {_usd(res['balloon_amt'])}"),
            ("Repayment per instalment (before balloon)", _usd(res["payment"])),
        ]),
        ("Scrap, depreciation & exit", [
            ("Scrap rate per LWT tonne", f"USD {_num(inp, 'scrap_rate'):,.0f}"),
            ("Scrap value (LWT x scrap rate)", _usd(res["scrap_value"])),
            ("Depreciable amount (cost less scrap)", _usd(res["dep_base"])),
            ("Annual depreciation (straight line)", _usd(res["dep_per_year"])),
            ("Book value at exit", _usd(res["bv_exit"])),
            ("Exit premium / (discount) to book value", f"{_num(inp, 'exit_premium'):.2f}%"),
            ("Sale price at exit", _usd(res["sale_price"])),
            ("S&P commission at exit", f"{_num(inp, 'sp_fee_pct'):.2f}% = {_usd(res['sp_fee'])}"),
        ]),
        ("Decision criteria", [
            ("Target equity XIRR (hurdle)", f"{_num(inp, 'target_irr'):.2f}%"),
            ("Minimum DSCR", f"{_num(inp, 'min_dscr'):.2f}x"),
        ]),
    ]


CSS = """
:root{--ink:#1e1b4b;--muted:#64748b}
*{box-sizing:border-box}
body{margin:0;font-family:"Segoe UI",Arial,sans-serif;background:#f5f3ff;color:var(--ink)}
header{background:linear-gradient(120deg,#7c3aed,#db2777 55%,#f59e0b);color:#fff;padding:28px 40px}
header h1{margin:0;font-size:26px}
header p{margin:6px 0 0;opacity:.92}
main{padding:12px 40px 24px;max-width:1400px;margin:auto}
h2{color:#4c1d95;border-bottom:3px solid #c4b5fd;padding-bottom:6px;margin-top:34px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin-top:18px}
.kpi{border-radius:14px;padding:16px;color:#fff;display:flex;flex-direction:column;gap:4px;box-shadow:0 6px 18px rgba(76,29,149,.2)}
.kpi span{font-size:13px;opacity:.92}
.kpi strong{font-size:26px}
.kpi small{opacity:.88}
.c1{background:linear-gradient(135deg,#7c3aed,#a855f7)}
.c2{background:linear-gradient(135deg,#0ea5e9,#22d3ee)}
.c3{background:linear-gradient(135deg,#f97316,#facc15)}
.c4{background:linear-gradient(135deg,#ec4899,#f43f5e)}
.c5{background:linear-gradient(135deg,#10b981,#84cc16)}
.c6{background:linear-gradient(135deg,#6366f1,#3b82f6)}
.verdict{margin-top:20px;border-radius:14px;padding:18px 22px;font-size:18px;font-weight:700}
.verdict.ok{background:#d1fae5;color:#065f46;border:2px solid #10b981}
.verdict.bad{background:#ffe4e6;color:#9f1239;border:2px solid #f43f5e}
.verdict ul{font-size:14px;font-weight:400;margin:10px 0 0 18px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px}
.card{background:#fff;border-radius:14px;padding:16px 18px;box-shadow:0 4px 14px rgba(15,23,42,.06);border-top:4px solid #a855f7}
.card h3{margin:0 0 10px;color:#6d28d9;font-size:16px}
.chart{background:#fff;border-radius:14px;padding:16px;box-shadow:0 4px 14px rgba(15,23,42,.06)}
.chart p{color:var(--muted);font-size:13px;margin:0 0 8px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:7px 9px;border-bottom:1px solid #ede9fe;text-align:left;vertical-align:top}
thead th{background:#7c3aed;color:#fff;position:sticky;top:0}
tbody tr:nth-child(even){background:#faf5ff}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr.total td{font-weight:700;background:#ede9fe}
table.kv th{width:58%;color:#4c1d95;font-weight:600}
.tablewrap{overflow-x:auto;background:#fff;border-radius:14px;box-shadow:0 4px 14px rgba(15,23,42,.06);padding:4px;max-height:560px}
.badge{padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700}
.badge.ok{background:#d1fae5;color:#065f46}
.badge.bad{background:#ffe4e6;color:#9f1239}
details{margin-top:12px;background:#fff;border-radius:14px;padding:12px 16px;box-shadow:0 4px 14px rgba(15,23,42,.06)}
summary{cursor:pointer;font-weight:700;color:#6d28d9}
.note li{margin-bottom:6px;line-height:1.5}
footer{color:var(--muted);font-size:12px;padding:20px 40px}
"""


def build_html(inp, res):
    """Return the complete HTML investment report as a string."""
    target_pct = _num(inp, "target_irr")
    min_target = _num(inp, "min_dscr")
    title_name = res["name"] or "Unnamed vessel"

    cards = [
        ("Equity XIRR", _pct(res["irr"]), f"Hurdle {target_pct:.1f}%", "c1"),
        ("MOIC", _x(res["moic"]), "Equity inflows / equity invested", "c2"),
        ("Payback period", _yrs(res["payback_years"]), "From purchase date", "c3"),
        ("ROI (annualised)", _pct(res["roi_annual"]), f"Total ROI {_pct(res['roi_total'])}", "c4"),
        ("Minimum DSCR", _x(res["min_dscr"]), f"Covenant {min_target:.2f}x", "c5"),
        ("Equity invested", _usd(res["total_outflows"]), "Total equity outflows", "c6"),
    ]
    kpi_html = "".join(
        f'<div class="kpi {cls}"><span>{esc(t)}</span><strong>{esc(v)}</strong><small>{esc(s)}</small></div>'
        for t, v, s, cls in cards)

    verdict_cls = "ok" if res["viable"] else "bad"
    verdict_text = ("VIABLE - returns meet the investment criteria" if res["viable"]
                    else "NOT VIABLE on the current assumptions")
    reason_items = "".join("<li>" + esc(r) + "</li>" for r in res["reasons"])
    verdict_html = f'<div class="verdict {verdict_cls}">{esc(verdict_text)}<ul>{reason_items}</ul></div>'

    warn_html = ""
    if res["warnings"]:
        warn_items = "".join("<li>" + esc(w) + "</li>" for w in res["warnings"])
        warn_html = ('<div class="card" style="border-top-color:#f59e0b;margin-top:16px">'
                     f'<h3>Warnings</h3><ul class="note">{warn_items}</ul></div>')

    groups_html = "".join(_kv_card(t, rows) for t, rows in _assumption_groups(inp, res))

    su_uses = _table(["Uses of funds", "USD"], [
        ["Purchase price", _acc(res["pp"])],
        ["Upfront finance cost", _acc(res["upfront_fee"])],
        ["Legal / documentation fees", _acc(res["legal"])],
        ["Working capital", _acc(res["wc"])],
        ["Total uses", _acc(res["total_uses"])],
    ], num_cols=(1,), total_last=True)
    su_src = _table(["Sources of funds", "USD"], [
        ["Bank debt", _acc(res["debt"])],
        ["Equity infusion (purchase price)", _acc(res["equity_infusion"])],
        ["Equity for fees and working capital", _acc(res["equity_t0"] - res["equity_infusion"])],
        ["Total sources", _acc(res["debt"] + res["equity_t0"])],
    ], num_cols=(1,), total_last=True)

    tce_rows = []
    for p in _pos_periods(res):
        tce_rows.append([p["label"], str(p["months"]), _acc(p["rate"]), f"{p['days']:,.0f}",
                         _acc(p["gross"]), _acc(-p["commissions"]), _acc(p["revenue"])])
    pos = _pos_periods(res)
    tce_rows.append(["Total", str(sum(p["months"] for p in pos)), "",
                     f"{sum(p['days'] for p in pos):,.0f}",
                     _acc(sum(p["gross"] for p in pos)), _acc(-sum(p["commissions"] for p in pos)),
                     _acc(sum(p["revenue"] for p in pos))])
    tce_html = _table(["Period", "Months", "TCE per day (USD)", "Calendar days",
                       "Gross revenue (USD)", "Commissions (USD)", "Net revenue (USD)"],
                      tce_rows, num_cols=(1, 2, 3, 4, 5, 6), total_last=True)

    dd_rows = []
    for ev in res["dd_events"]:
        dd_rows.append([str(ev["no"]), f"{ev['date']:%d-%b-%Y}", f"{ev['age']:.2f}",
                        "Y" + str(ev["year"]), _acc(ev["cost"])])
    dd_rows.append(["Total", "", "", "", _acc(sum(ev["cost"] for ev in res["dd_events"]))])
    dd_html = _table(["Future dry-dock", "Scheduled date", "Vessel age (yrs)", "Operating year", "Cost (USD)"],
                     dd_rows, num_cols=(2, 4), total_last=True)

    ann_rows = []
    for a in res["annual"]:
        ann_rows.append([
            a["label"], a["period"],
            _acc(a["gross"]), _acc(-a["commissions"]), _acc(a["revenue"]),
            _acc(-a["mgr"]), _acc(-a["ins"]), _acc(-a["dd"]),
            _acc(a["cfads"]), _acc(-a["interest"]), _acc(-a["principal"]),
            _acc(a["exit_net"]), _acc(a["equity_cf"]), _acc(a["cumulative"]),
            _x(a["dscr"]),
        ])
    ann_html = _table(
        ["Year", "Period", "Gross revenue", "Commissions", "Net revenue", "Ship mgmt", "Insurance",
         "Dry-dock", "CFADS", "Interest", "Principal", "Exit (net)", "Equity CF", "Cumulative", "DSCR"],
        ann_rows, num_cols=tuple(range(2, 15)))

    chart_html = ('<div class="chart"><p>Bars: annual equity cash flow (green positive, red negative). '
                  'Purple line: cumulative equity cash flow.</p>'
                  + _svg_chart([a["label"] for a in res["annual"]],
                               [a["equity_cf"] for a in res["annual"]],
                               [a["cumulative"] for a in res["annual"]]) + "</div>")

    check_rows = []
    for c in res["checks"]:
        badge = '<span class="badge ok">PASS</span>' if c["ok"] else '<span class="badge bad">CHECK</span>'
        check_rows.append(f"<tr><td>{esc(c['label'])}</td><td>{badge}</td><td>{esc(c['detail'])}</td></tr>")
    check_html = ('<div class="tablewrap"><table><thead><tr><th>Check</th><th>Status</th><th>Detail</th></tr>'
                  "</thead><tbody>" + "".join(check_rows) + "</tbody></table></div>")

    m_rows = []
    for r in res["rows"]:
        m_rows.append([
            str(r["no"]), f"{r['date']:%d-%b-%Y}", str(r["days"]), _acc(r["tce"]),
            _acc(r["gross"]), _acc(-r["commissions"]), _acc(r["revenue"]),
            _acc(-r["mgr"]), _acc(-r["ins"]), _acc(-r["dd"]),
            _acc(-r["interest"]), _acc(-r["principal"]), _acc(r["balance"]),
            _acc(r["exit_net"]), _acc(r["equity_cf"]),
        ])
    monthly_html = ("<details><summary>Show monthly cash flow schedule (" + str(len(res["rows"]))
                    + " months)</summary>"
                    + _table(["#", "Month end", "Days", "TCE/day", "Gross revenue", "Commissions",
                              "Net revenue", "Ship mgmt", "Insurance", "Dry-dock", "Interest", "Principal",
                              "Debt balance", "Exit (net)", "Equity CF"],
                             m_rows, num_cols=tuple(range(2, 15)))
                    + "</details>")

    method_items = [
        "Gross revenue = TCE rate per day x (calendar days - off-hire days). Off-hire days are pro-rated from the annual figure (days per annum x days in month / 365).",
        "Address and broker commissions are percentages of gross revenue and are deducted to give net revenue.",
        "Dry-dock dates are counted in months from the delivery date from the yard: every standard interval while the vessel is younger than the age threshold, then every alternative interval. Only dockings after the purchase date and inside the operating period are costed.",
        "Ship management and insurance = daily cost x calendar days, escalated by (1 + escalation) raised to the operating year minus one.",
        "Loan: equal instalments sized so the balance left after the final instalment equals the balloon. The balloon is paid with the final instalment. Any balance outstanding at exit is repaid from sale proceeds.",
        "Depreciation is straight line: (purchase price less scrap value) / remaining useful life. It is non-cash; it only sets book value at exit. No tax is modelled.",
        "Exit: sale price = book value at exit x (1 + premium or discount). S&P commission is deducted from the sale price. Working capital is assumed recovered at exit.",
        "Equity cash flow at acquisition = equity infusion + upfront finance cost + legal fees + working capital. Monthly equity cash flows are dated at month end.",
        "Equity XIRR uses actual dates on a 365-day year. Payback is the point where cumulative equity cash flow turns positive, interpolated within the month.",
        "MOIC = total equity inflows / total equity outflows. ROI = net profit / equity invested; annualised ROI = (1 + ROI)^(1 / operating years) - 1.",
        "DSCR = annual cash flow available for debt service (after commissions, operating costs and dry-docking) / annual debt service.",
    ]
    method_html = "".join("<li>" + esc(t) + "</li>" for t in method_items)

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title_name)} - investment analysis</title>
<style>{CSS}</style>
</head>
<body>
<header>
<h1>{esc(title_name)} - Secondhand Vessel Investment Analysis</h1>
<p>{esc(inp['vessel_type'])} | Purchase {_fd(res['purchase_date'])} | Purchase price {_usd(res['pp'])} | Analysis date {_fd(inp['analysis_date'])}</p>
</header>
<main>
<div class="kpis">{kpi_html}</div>
{verdict_html}
{warn_html}
<h2>Assumptions summary</h2>
<div class="grid">{groups_html}</div>
<h2>Sources and uses of funds</h2>
<div class="grid">
<div class="card">{su_uses}</div>
<div class="card">{su_src}</div>
</div>
<h2>Revenue periods (time charter equivalent, positive periods only)</h2>
{tce_html}
<h2>Future dry-dock schedule</h2>
{dd_html}
<h2>Annual cash flow to equity</h2>
{chart_html}
<br>
{ann_html}
<h2>Model checks</h2>
{check_html}
<h2>Monthly cash flow</h2>
{monthly_html}
<h2>Methodology</h2>
<div class="card"><ul class="note">{method_html}</ul></div>
</main>
<footer>Generated by {esc(APP_TITLE)} on {datetime.now():%d-%b-%Y %H:%M}. All figures in USD unless stated.</footer>
</body>
</html>
"""
    return doc
