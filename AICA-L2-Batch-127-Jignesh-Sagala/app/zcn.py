"""Reader for Zerodha 'Combined Equity Contract Note' PDFs (one file per trade day).

Reads the rows with the same position reader as the CDSL reader (cdsl.read_rows) and parses:
  header   : trade date, settlement date, settlement no, contract note no
  summary  : one row per ISIN, 12 numbers (buy side 5, sell side 5, net quantity, net total)
  charges  : label and the NET TOTAL column (last number on the row)
  trades   : one row per trade (order no, times, trade no, name/ISIN, B or S, exchange, quantity, two rates, total)
All money is Decimal. Nothing is guessed: a row that does not fit is counted as unread and the checks say so.
run_checks() returns (name, PASS/FAIL/INFO, detail) lines. Details are counts or sizes of a difference, never figures.
"""
import re
from datetime import datetime
from decimal import Decimal as D, InvalidOperation

ISIN = r"IN[EF][0-9A-Z]{9}|IN[0-9][0-9A-Z]{9}"
ISIN_RE = re.compile(r"^(?:%s)$" % ISIN)
NUM_TOKEN = re.compile(r"^\(?-?[\d,]+(?:\.\d+)?\)?$")
NUM_DEC = re.compile(r"^\(?-?[\d,]+\.\d+\)?$")
TRADE_RE = re.compile(
    r"^(\d{8,})\s+(\d\d:\d\d:\d\d)\s+(\d+)\s+(\d\d:\d\d:\d\d)\s+(.+?)/(" + ISIN + r")\s+([BS])\s+([A-Z]{3,4})\s+(\d+)\s+"
    r"(\(?-?[\d,]+\.\d+\)?)\s+(\(?-?[\d,]+\.\d+\)?)\s+(\(?-?[\d,]+\.\d+\)?)$")


def money(tok):
    """'(1,234.50)' -> Decimal('-1234.50'); '12.5' -> Decimal('12.5'). None if not a number."""
    t = tok.strip()
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()").replace(",", "")
    try:
        v = D(t)
    except InvalidOperation:
        return None
    return -v if neg else v


def _date(s):
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except ValueError:
        return None


def parse(pages):
    out = {"contract_no": None, "trade_date": None, "settle_date": None, "settle_no": None,
           "summary": [], "summary_unread": [], "charges": [], "trades": [], "rows_seen": 0}
    for rows in pages:
        for r in rows:
            out["rows_seen"] += 1
            m = re.search(r"Trade Date:\s*(\d\d/\d\d/\d{4})", r)
            if m and not out["trade_date"]:
                out["trade_date"] = _date(m.group(1))
            m = re.search(r"Settlement No:\s*(\w+)", r)
            if m and not out["settle_no"]:
                out["settle_no"] = m.group(1)
            m = re.search(r"Settlement Date:\s*(\d\d/\d\d/\d{4})", r)
            if m and not out["settle_date"]:
                out["settle_date"] = _date(m.group(1))
            m = re.search(r"Contract Note No:\s*(\S+)", r)
            if m and not out["contract_no"]:
                out["contract_no"] = m.group(1)

            t = TRADE_RE.match(r)
            if t:
                out["trades"].append({
                    "order_no": t.group(1), "order_time": t.group(2), "trade_no": t.group(3), "trade_time": t.group(4),
                    "name": t.group(5).strip(), "isin": t.group(6), "side": t.group(7), "exchange": t.group(8),
                    "qty": int(t.group(9)), "p1": money(t.group(10)), "p2": money(t.group(11)), "total": money(t.group(12))})
                continue

            tok = r.split()
            if tok and ISIN_RE.match(tok[0]):                    # summary row: ISIN name ... 12 numbers
                nums = []
                for x in reversed(tok[1:]):
                    if NUM_TOKEN.match(x):
                        nums.append(x)
                    else:
                        break
                nums.reverse()
                if len(nums) < 12:
                    out["summary_unread"].append(r)
                    continue
                data = [money(x) for x in nums[-12:]]
                name = " ".join(tok[1:len(tok) - 12])
                (bq, bw, bb, bn, bv, sq, sw, sb, sn, sv, nq, nt) = data
                out["summary"].append({"isin": tok[0], "name": name, "buy_qty": int(bq), "buy_wap": bw, "buy_brok": bb,
                                       "buy_wap_net": bn, "buy_value": bv, "sell_qty": int(sq), "sell_wap": sw,
                                       "sell_brok": sb, "sell_wap_net": sn, "sell_value": sv, "net_qty": int(nq), "net_total": nt})
                continue

            # charges: label then 1 to 3 decimal numbers; the last one is the NET TOTAL column
            vals = []
            for x in reversed(tok):
                if NUM_DEC.match(x):
                    vals.append(x)
                else:
                    break
            if vals and len(vals) < len(tok):
                vals.reverse()
                label = " ".join(tok[:len(tok) - len(vals)]).strip()
                if label and not label[0].isdigit() and re.search(r"[A-Za-z]{3}", label):
                    out["charges"].append({"label": label, "value": money(vals[-1]), "cols": len(vals)})
    return out


def _find(charges, key):
    return [c for c in charges if re.search(key, c["label"], re.I)]


def run_checks(d):
    res = []

    def add(name, ok, detail=""):
        res.append((name, "PASS" if ok else "FAIL", detail))

    add("Header: trade date, settlement date, settlement no, contract note no",
        all([d["trade_date"], d["settle_date"], d["settle_no"], d["contract_no"]]),
        f"found {sum(1 for k in ('trade_date', 'settle_date', 'settle_no', 'contract_no') if d[k])} of 4")
    if d["trade_date"] and d["settle_date"]:
        add("Settlement date is on or after trade date", d["settle_date"] >= d["trade_date"])
    S = d["summary"]
    add("Summary rows read, every row has 12 numbers", len(S) > 0 and not d["summary_unread"],
        f"rows read {len(S)}, rows not read {len(d['summary_unread'])}")
    bad = [s["isin"] for s in S if s["net_qty"] != abs(s["buy_qty"] - s["sell_qty"])]
    add("Net quantity = difference of buy and sell quantity, shown as a positive number (every ISIN)", not bad, f"{len(bad)} ISIN differ")
    bad = []
    for s in S:
        if s["buy_qty"] and abs(s["buy_qty"] * s["buy_wap_net"] - s["buy_value"]) > max(D("1"), s["buy_value"] * D("0.001")):
            bad.append(s["isin"])
        if s["sell_qty"] and abs(s["sell_qty"] * s["sell_wap_net"] - s["sell_value"]) > max(D("1"), s["sell_value"] * D("0.001")):
            bad.append(s["isin"])
    add("Summary value = quantity x average price after brokerage (buy and sell, within 0.1%)", not bad, f"{len(bad)} rows differ")

    T = d["trades"]
    add("Trade rows read", len(T) > 0, f"{len(T)} trades")
    by = {}
    for t in T:
        k = (t["isin"], t["side"])
        a = by.setdefault(k, [0, D(0), 0])
        a[0] += t["qty"]
        a[1] += abs(t["total"])
        a[2] += 1
    bad_q, bad_v, bad_b = [], [], []
    brok_total = D(0)
    for s in S:
        for side, q, w, v in (("B", s["buy_qty"], s["buy_wap"], s["buy_value"]), ("S", s["sell_qty"], s["sell_wap"], s["sell_value"])):
            a = by.get((s["isin"], side), [0, D(0), 0])
            if a[0] != q:
                bad_q.append(s["isin"])
            if abs(a[1] - q * w) > D("1") + D("0.01") * a[2]:
                bad_v.append(s["isin"])
            brok = (v - a[1]) if side == "B" else (a[1] - v)      # buy value includes brokerage, sell value is after brokerage
            if brok < D("-1"):
                bad_b.append(s["isin"])
            brok_total += brok
    extra = [k for k in by if k[0] not in {s["isin"] for s in S}]
    add("Trades: quantity per ISIN and side equals summary", not bad_q and not extra, f"{len(bad_q)} differ, {len(extra)} ISIN not in summary")
    add("Trades: total per ISIN and side = quantity x average price before brokerage (within 1)", not bad_v, f"{len(bad_v)} differ")
    add("Brokerage implied by the summary is never negative", not bad_b, f"{len(bad_b)} ISIN negative")
    bad = [t["trade_no"] for t in T if not any(abs(t["qty"] * p - abs(t["total"])) <= max(D("1"), abs(t["total"]) * D("0.001")) for p in (t["p1"], t["p2"]))]
    add("Trade: quantity x one of the two rates = total (within 0.1%)", not bad, f"{len(bad)} trades differ")

    ob = _find(d["charges"], r"pay in")
    net = _find(d["charges"], r"net amount")
    add("Charges: pay-in/pay-out row and net amount row found", len(ob) == 1 and len(net) == 1, f"{len(ob)} and {len(net)} rows")
    if len(ob) == 1 and len(net) == 1:
        comp = [c for c in d["charges"] if c is not ob[0] and c is not net[0]]
        gap = abs(ob[0]["value"] + sum((c["value"] for c in comp), D(0)) - net[0]["value"])
        add("Charges: obligation + every charge = net amount (within 1)", gap <= D("1"), f"{len(comp)} charge rows, difference {gap}")
        sgn = sum((abs(t["total"]) if t["side"] == "S" else -abs(t["total"]) for t in T), D(0))
        gap2 = abs(abs(ob[0]["value"]) - abs(sgn))
        add("Pay-in/pay-out = sell trades - buy trades (within 1)", gap2 <= D("1"), f"difference {gap2}")
        br = _find(d["charges"], r"taxable value of supply")
        if len(br) == 1:
            gap3 = abs(abs(br[0]["value"]) - brok_total)
            add("Brokerage row in charges = brokerage implied by the summary (within 1)", gap3 <= D("1"), f"difference {gap3}")
        else:
            add("Brokerage row in charges found", False, f"{len(br)} rows")
    return res


def buys(d):
    """Rows for the private cost file. Real figures; laptop only.
    gross_value = sum of the day's buy trades; value_incl_brokerage = summary value; brokerage = difference."""
    gross = {}
    for t in d["trades"]:
        if t["side"] == "B":
            gross[t["isin"]] = gross.get(t["isin"], D(0)) + abs(t["total"])
    rows = []
    for s in d["summary"]:
        if s["buy_qty"]:
            g = gross.get(s["isin"], D(0))
            rows.append({"trade_date": d["trade_date"], "isin": s["isin"], "name": s["name"], "buy_qty": s["buy_qty"],
                         "gross_value": g, "brokerage": s["buy_value"] - g, "value_incl_brokerage": s["buy_value"],
                         "avg_price_incl_brokerage": (s["buy_value"] / s["buy_qty"]).quantize(D("0.0001"))})
    return rows


def sells(d):
    """Sell rows for the private cost file. Real figures; laptop only.
    gross_value = sum of the day's sell trades; value_after_brokerage = summary value; brokerage = difference."""
    gross = {}
    for t in d["trades"]:
        if t["side"] == "S":
            gross[t["isin"]] = gross.get(t["isin"], D(0)) + abs(t["total"])
    rows = []
    for s in d["summary"]:
        if s["sell_qty"]:
            g = gross.get(s["isin"], D(0))
            rows.append({"trade_date": d["trade_date"], "isin": s["isin"], "name": s["name"], "sell_qty": s["sell_qty"],
                         "gross_value": g, "brokerage": g - s["sell_value"], "value_after_brokerage": s["sell_value"],
                         "avg_price_after_brokerage": (s["sell_value"] / s["sell_qty"]).quantize(D("0.0001"))})
    return rows


def diagnose(d, limit=6):
    """Safe diagnostic lines for a note that fails: sizes of differences and yes/no facts. No names, prices or amounts of holdings."""
    out = []
    S, T = d["summary"], d["trades"]
    tb, ts = {}, {}
    for t in T:
        tgt = tb if t["side"] == "B" else ts
        a = tgt.setdefault(t["isin"], [0, D(0), 0])
        a[0] += t["qty"]
        a[1] += abs(t["total"])
        a[2] += 1
    k = 0
    for s in S:
        k += 1
        if k > limit:
            break
        a = tb.get(s["isin"], [0, D(0), 0])
        b = ts.get(s["isin"], [0, D(0), 0])
        kind = "both" if s["buy_qty"] and s["sell_qty"] else ("buy only" if s["buy_qty"] else "sell only")
        dbv = a[1] - s["buy_value"]
        dsv = b[1] - s["sell_value"]
        pu_b = (dbv / s["buy_qty"]).quantize(D("0.0001")) if s["buy_qty"] else None
        pu_s = (dsv / s["sell_qty"]).quantize(D("0.0001")) if s["sell_qty"] else None
        nq = s["net_qty"]
        form = "buy-sell" if nq == s["buy_qty"] - s["sell_qty"] else ("sell-buy" if nq == s["sell_qty"] - s["buy_qty"] else "other")
        nt_rel = []
        if s["buy_qty"] and not s["sell_qty"]:
            nt_rel = [("net_total - buy_value", s["net_total"] - s["buy_value"]), ("net_total + buy_value", s["net_total"] + s["buy_value"])]
        elif s["sell_qty"] and not s["buy_qty"]:
            nt_rel = [("net_total - sell_value", s["net_total"] - s["sell_value"]), ("net_total + sell_value", s["net_total"] + s["sell_value"])]
        out.append(f"  ISIN {k}: {kind}; trades B {a[2]} S {b[2]}; trade total minus summary value: buy {dbv}, sell {dsv}; per unit: buy {pu_b}, sell {pu_s}; "
                   f"net qty is {form}; brokerage columns all zero: {s['buy_brok'] == 0 and s['sell_brok'] == 0}; avg price = avg price after brokerage: "
                   f"{s['buy_wap'] == s['buy_wap_net'] and s['sell_wap'] == s['sell_wap_net']}; "
                   + "; ".join(f"{n} = {v}" for n, v in nt_rel))
    ob = _find(d["charges"], r"pay in")
    if len(ob) == 1:
        ov = ob[0]["value"]
        sb = sum((s["buy_value"] for s in S), D(0))
        ss = sum((s["sell_value"] for s in S), D(0))
        tsum = sum((t["total"] for t in T), D(0))
        nts = sum((s["net_total"] for s in S), D(0))
        out.append(f"  Obligation minus (sell - buy from summary): {ov - (ss - sb)}")
        out.append(f"  Obligation minus sum of signed trade totals: {ov - tsum}")
        out.append(f"  Obligation minus sum of summary net totals: {ov - nts}   (and plus: {ov + nts})")
        out.append(f"  Charge rows: {len(d['charges'])}; labels: " + " | ".join(c['label'][:28] + f" [{c['cols']}]" for c in d["charges"]))
    return out
