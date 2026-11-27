"""Opening position back-solve. Runs on this laptop only (real data). Prints counts and symbols, never prices or values.

Idea
  Holdings at the cut-off date (units, Zerodha average price) are known. Trades from the start date to the cut-off are known.
  Opening units = holding units - net trades.
  Under the average-cost rule the final cost is linear in the unknown opening cost: final = a x opening cost + b.
  So opening cost = (units x Zerodha average price - b) / a. Nothing is guessed. Anything that does not fit is flagged.

Use:  py open_position.py "<holdings xlsx>" [base folder]      (base folder default C:\\AICA_private)
Reads  <base>\\tradebooks\\*.csv, <base>\\zerodha_cn_out\\buys.csv and sells.csv
Writes <base>\\db_real_work\\opening_position.csv  (real figures, stays on this laptop)
Optional files in <base>\\db_real_work\\ : corporate_actions.csv (isin,date,type,ratio,note; type split or bonus),\n  isin_alias.csv (old_isin,new_isin) and manual_overrides.csv (symbol,isin,qty,avg_price,note)
"""
import csv
import sys
from decimal import Decimal as D, getcontext
from pathlib import Path

getcontext().prec = 40
OPEN_DATE = "2024-03-31"


def simulate(trades, u0, c0):
    """trades: list of (side, qty, price) in order. Average-cost rule. Returns (units, cost) or None if a sale exceeds the units held."""
    units, cost = D(u0), D(c0)
    for side, q, p in trades:
        if side == "B":
            units += q
            cost += q * p
        else:
            if q > units:
                return None
            if units > 0:
                cost -= q * (cost / units)
            units -= q
            if units == 0:
                cost = D(0)
    return units, cost


def simulate_fifo(trades, u0, c0):
    """First in, first out, as Zerodha computes the holding average price. The opening units are the oldest lot.
    Returns (units, cost) or None if a sale exceeds the units held."""
    lots = [[D(u0), D(c0)]] if u0 else []
    for side, q, p in trades:
        if side == "B":
            lots.append([q, q * p])
            continue
        left = q
        while left > 0:
            if not lots:
                return None
            lq, lc = lots[0]
            take = min(left, lq)
            lots[0] = [lq - take, lc - lc * take / lq]
            left -= take
            if lots[0][0] == 0:
                lots.pop(0)
    return sum((x[0] for x in lots), D(0)), sum((x[1] for x in lots), D(0))


def net_intraday(day_trades):
    """Zerodha leaves same-day buy and sell of one stock out of the holding average. day_trades: list of (side, qty, price)."""
    bq = sum(q for s, q, p in day_trades if s == "B")
    sq = sum(q for s, q, p in day_trades if s == "S")
    intra = min(bq, sq)
    out = []
    if bq - intra > 0:
        pb = sum(q * p for s, q, p in day_trades if s == "B") / bq
        out.append(("B", bq - intra, pb))
    if sq - intra > 0:
        ps = sum(q * p for s, q, p in day_trades if s == "S") / sq
        out.append(("S", sq - intra, ps))
    return out


def solve(trades, qty, avg_price, method="fifo"):
    """Returns a dict: status, u0 (opening units), c0 (opening total cost or None).
    method fifo = how Zerodha shows its average price; avg = the dashboard's average-cost rule."""
    sim = simulate_fifo if method == "fifo" else simulate
    qty = D(qty)
    target = qty * D(avg_price)
    net = sum((q if s == "B" else -q) for s, q, p in trades)
    u0 = qty - net
    if u0 < 0:
        return {"status": "FLAG_OPENING_UNITS_NEGATIVE", "u0": u0, "c0": None}
    if u0 != u0.to_integral_value():
        return {"status": "FLAG_OPENING_UNITS_FRACTION", "u0": u0, "c0": None}
    if u0 == 0:
        r = sim(trades, 0, 0)
        if r is None:
            return {"status": "FLAG_SALE_EXCEEDS_UNITS", "u0": u0, "c0": None}
        ok = abs(r[1] - target) <= max(D(1), target * D("0.001"))
        return {"status": "NO_OPENING_PASS" if ok else "NO_OPENING_FAIL", "u0": u0, "c0": D(0),
                "gap_pct": (r[1] - target) / target * 100 if target else None}
    r0, r1 = sim(trades, u0, 0), sim(trades, u0, 1)
    if r0 is None or r1 is None:
        return {"status": "FLAG_SALE_EXCEEDS_UNITS", "u0": u0, "c0": None}
    a = r1[1] - r0[1]
    if abs(a) < D("1e-12"):
        ok = abs(r0[1] - target) <= max(D(1), target * D("0.001"))
        return {"status": "NO_INFO_OPENING_SOLD_COST_MATCHES" if ok else "NO_INFO_OPENING_SOLD_COST_DIFFERS", "u0": u0, "c0": None,
                "gap_pct": (r0[1] - target) / target * 100 if target else None}
    c0 = (target - r0[1]) / a
    return {"status": "SOLVED" if c0 >= 0 else "FLAG_OPENING_COST_NEGATIVE", "u0": u0, "c0": c0}


def apply_split(trades, ratio):
    """trades before the split date, as (side, qty, price): units x ratio, price / ratio. A 1 for 1 bonus is ratio 2."""
    r = D(ratio)
    return [(s, q * r, p / r) for s, q, p in trades]


def _read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    import openpyxl
    base = Path(argv[2].strip('"')) if len(argv) > 2 else Path(r"C:\AICA_private")
    work = base / "db_real_work"
    work.mkdir(exist_ok=True)
    alias = {}
    if (work / "isin_alias.csv").exists():
        alias = {r["old_isin"]: r["new_isin"] for r in _read_csv(work / "isin_alias.csv")}
    ca = _read_csv(work / "corporate_actions.csv") if (work / "corporate_actions.csv").exists() else []
    over = {}
    if (work / "manual_overrides.csv").exists():
        over = {r["symbol"]: r for r in _read_csv(work / "manual_overrides.csv")}

    # ---- tradebooks
    seen, tb, label = set(), [], {}
    for p in sorted((base / "tradebooks").glob("*.csv")):
        for r in _read_csv(p):
            if r["trade_id"] in seen:
                continue
            seen.add(r["trade_id"])
            isin = alias.get(r["isin"].strip(), r["isin"].strip())
            label.setdefault(isin, r["symbol"].strip())
            tb.append({"date": r["trade_date"], "isin": isin, "side": "B" if r["trade_type"].lower() == "buy" else "S",
                       "qty": D(r["quantity"]), "price": D(r["price"]), "time": r["order_execution_time"]})
    tb_last = max(t["date"] for t in tb)
    print(f"Tradebook trades: {len(tb)} (duplicates removed)   from {min(t['date'] for t in tb)} to {tb_last}")

    # ---- holdings (31 Oct file), keyed by ISIN
    wb = openpyxl.load_workbook(argv[1].strip('"'), data_only=True)
    hold, skipped = {}, []
    for r in wb["Equity"].iter_rows(min_row=24, values_only=True):
        if not r[1]:
            continue
        sym, isin, qty, avg = r[1], (r[2] or "").strip(), D(str(r[4])) + D(str(r[5])), D(str(r[9]))
        if sym in over:
            o = over[sym]
            isin, qty, avg = o["isin"], D(o["qty"]), D(o["avg_price"])
        elif not isin or avg == 0:
            skipped.append(sym)
            continue
        hold[isin] = {"qty": qty, "avg": avg}
        label.setdefault(isin, sym)
    print(f"Holdings rows used: {len(hold)}   skipped (no ISIN or zero cost): {len(skipped)} {', '.join(skipped) or '-'}")
    if over:
        print(f"Manual overrides applied: {', '.join(sorted(over))}")

    # ---- contract notes
    notes, tie_ok, tie_bad = [], 0, []
    tbsum = {}
    for t in tb:
        a = tbsum.setdefault((t["date"], t["isin"], t["side"]), [D(0), D(0)])
        a[0] += t["qty"]
        a[1] += t["qty"] * t["price"]
    for fname, side, qk in (("buys.csv", "B", "buy_qty"), ("sells.csv", "S", "sell_qty")):
        p = base / "zerodha_cn_out" / fname
        if not p.exists():
            continue
        for r in _read_csv(p):
            isin = alias.get(r["isin"], r["isin"])
            label.setdefault(isin, r["name"])
            q, gross = D(r[qk]), D(r["gross_value"])
            if r["trade_date"] <= tb_last:
                a = tbsum.get((r["trade_date"], isin, side))
                if a and a[0] == q and abs(a[1] - gross) <= max(D(1), gross * D("0.001")):
                    tie_ok += 1
                else:
                    tie_bad.append(f"{label[isin]} {r['trade_date']} {side}")
                continue
            notes.append({"date": r["trade_date"], "isin": isin, "side": side, "qty": q, "price": gross / q,
                          "time": "99:99:99" if side == "S" else "99:99:00"})
    print(f"Contract notes on days already in the tradebooks: {tie_ok} rows match, {len(tie_bad)} differ {', '.join(tie_bad) or ''}")
    print(f"Contract-note rows added after {tb_last}: {len(notes)}")
    trades = sorted(tb + notes, key=lambda t: (t["date"], t["side"] == "S" and t["time"] >= "99", t["time"]))
    by = {}
    for t in trades:
        by.setdefault(t["isin"], []).append(t)

    def seq(isin, intraday=True):
        days = {}
        for t in by.get(isin, []):
            q, p = t["qty"], t["price"]
            for c in ca:
                if c["isin"] == isin and t["date"] < c["date"]:
                    if c["type"].lower() == "coa":
                        p = p * D(c["ratio"])   # cost apportionment after a demerger: quantity unchanged, cost scaled
                        continue
                    f = D(c["ratio"]) + (1 if c["type"].lower() == "bonus" else 0)
                    q, p = q * f, p / f
            days.setdefault(t["date"], []).append((t["side"], q, p))
        out = []
        for d in sorted(days):
            out.extend(net_intraday(days[d]) if intraday else days[d])
        return out

    rows, groups = [], {}
    for isin, h in sorted(hold.items(), key=lambda kv: label[kv[0]]):
        tr = seq(isin)
        gap = ""
        if not tr:
            res = {"status": "OPENING_ONLY_NO_TRADES", "u0": h["qty"], "c0": h["qty"] * h["avg"]}
        else:
            res = solve(tr, h["qty"], h["avg"])
            firstbuy = next((p for s, q, p in tr if s == "B"), None)
            if res["status"] == "SOLVED" and firstbuy and res["u0"] > 0:
                ratio = (res["c0"] / res["u0"]) / firstbuy
                if ratio > 5 or ratio < D("0.2"):
                    res["status"] = "CHECK_OPENING_PRICE_FAR_FROM_FIRST_BUY"
            if res.get("gap_pct") is not None and res["status"] in ("NO_OPENING_FAIL", "NO_INFO_OPENING_SOLD_COST_DIFFERS"):
                gap = f" ({res['gap_pct']:+.1f}%)"
        groups.setdefault(res["status"], []).append(label[isin] + gap)
        rows.append([label[isin], isin, OPEN_DATE, res["u0"], "" if res["c0"] is None else res["c0"],
                     "" if (res["c0"] is None or res["u0"] == 0) else (res["c0"] / res["u0"]).quantize(D("0.0001")), res["status"]])
    for isin in sorted(set(by) - set(hold), key=lambda i: label[i]):
        net = sum((q if s == "B" else -q) for s, q, p in seq(isin))
        st = "OPENING_COST_UNKNOWN_SOLD_OUT" if net < 0 else ("NO_OPENING_ROUND_TRIP" if net == 0 else "FLAG_BOUGHT_NOT_HELD")
        groups.setdefault(st, []).append(label[isin])
        rows.append([label[isin], isin, OPEN_DATE, -net if net < 0 else 0, "", "", st])

    with open(work / "opening_position.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "isin", "opening_date", "opening_qty", "opening_cost", "opening_price", "status"])
        w.writerows(rows)
    print("\nRESULT BY STATUS")
    for st, syms in sorted(groups.items()):
        show = "" if st in ("SOLVED", "NO_OPENING_PASS", "NO_OPENING_ROUND_TRIP", "NO_INFO_OPENING_SOLD_COST_MATCHES") else ": " + ", ".join(syms)
        print(f"  {st}: {len(syms)}{show}")
    print("\nSaved (real figures, stays on this laptop, do NOT attach):", work / "opening_position.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
