"""Reader for the Zerodha funds ledger (weekly account statement, 'Statement of Account ... of Funds').
Built from a masked layout. Each ledger row: transaction date, optional settlement date, text, then three amounts:
debit, credit, balance. Continuation lines (settlement number, voucher date) are ignored.
The sign convention of the balance is not printed, so it is found from the rows themselves:
credit-positive (balance = previous + credit - debit) or debit-positive (balance = previous + debit - credit).
Row order on the page is not trusted: each row must follow from exactly one other row, and one row (the first) follows from nothing.
"""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

D = Decimal
M = r"-?\d[\d,]*\.\d{2}"
ROW = re.compile(rf"^(\d{{4}}-\d{{2}}-\d{{2}})(?:\s+(\d{{4}}-\d{{2}}-\d{{2}}))?\s+(.*?)\s+(?<![\d.])({M})\s+({M})\s+({M})\s*$")
ROW_START = re.compile(r"^\d{4}-\d{2}-\d{2}\b")


def money(s):
    try:
        return D(s.replace(",", ""))
    except InvalidOperation:
        return None


def _d(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def parse(pages):
    d = {"from": None, "to": None, "is_funds": False, "rows": [], "unread": 0}
    for p in pages:
        for ln in p:
            ln = ln.strip()
            if not ln:
                continue
            if re.search(r"Statement of .* of Funds", ln, re.I):
                d["is_funds"] = True
            if d["from"] is None:
                m = re.search(r"From Date:\s*(\d{4}-\d{2}-\d{2})", ln)
                if m:
                    d["from"] = _d(m.group(1))
            if d["to"] is None:
                m = re.search(r"To Date:\s*(\d{4}-\d{2}-\d{2})", ln)
                if m:
                    d["to"] = _d(m.group(1))
            if not ROW_START.match(ln) or not d["is_funds"]:
                continue
            m = ROW.match(ln)
            if not m:
                if re.search(r"\d\.\d{2}\s*$", ln):
                    d["unread"] += 1
                continue
            d["rows"].append({"date": _d(m.group(1)), "sdate": _d(m.group(2)) if m.group(2) else None, "desc": m.group(3),
                              "debit": money(m.group(4)), "credit": money(m.group(5)), "balance": money(m.group(6))})
    d["convention"] = _convention(d["rows"])
    d["chain"] = _chain(d["rows"], d["convention"])
    return d


def _step(conv, prev, r):
    return prev + r["credit"] - r["debit"] if conv == "credit" else prev + r["debit"] - r["credit"]


def _links(rows, conv):
    """For each row, the indexes of other rows whose balance leads to it."""
    out = []
    for i, r in enumerate(rows):
        out.append([j for j, q in enumerate(rows) if j != i and abs(_step(conv, q["balance"], r) - r["balance"]) <= D("0.005")])
    return out


def _convention(rows):
    best, bestn = None, -1
    for conv in ("credit", "debit"):
        n = sum(1 for lk in _links(rows, conv) if lk)
        if n > bestn:
            best, bestn = conv, n
    return best


def _chain(rows, conv):
    """Order-independent chain check. Returns dict: no_predecessor, ambiguous, end_index (row nobody follows from)."""
    if not rows or conv is None:
        return {"no_pred": len(rows), "ambiguous": 0, "ends": len(rows), "end": None}
    lk = _links(rows, conv)
    no_pred = sum(1 for x in lk if not x)
    amb = sum(1 for x in lk if len(x) > 1)
    used = {j for x in lk for j in x}
    ends = [i for i in range(len(rows)) if i not in used]
    return {"no_pred": no_pred, "ambiguous": amb, "ends": len(ends), "end": ends[0] if len(ends) == 1 else None}


def printed_order_misfits(d):
    conv, prev, bad = d["convention"], None, 0
    for r in d["rows"]:
        if prev is not None and abs(_step(conv, prev, r) - r["balance"]) > D("0.005"):
            bad += 1
        prev = r["balance"]
    return bad


def checks(d):
    res = []

    def add(name, ok, det=""):
        res.append((name, "PASS" if ok else "FAIL", det))
    rows = d["rows"]
    add("File is a funds ledger and its period is found", d["is_funds"] and bool(d["from"] and d["to"]))
    add("Ledger rows read", len(rows) > 0, f"{len(rows)} rows")
    add("Every dated row has debit, credit and balance", d["unread"] == 0, f"{d['unread']} rows without all three")
    if d["from"] and d["to"]:
        out = sum(1 for r in rows if not (d["from"] <= r["date"] <= d["to"]))
        add("Every transaction date is inside the statement period", out == 0, f"{out} outside")
    c = d["chain"]
    add("Balance chain: every row except the first follows from another row", len(rows) > 0 and c["no_pred"] == 1,
        f"convention {d['convention']}, {c['no_pred']} rows follow from nothing (expect 1)")
    add("Balance chain: one row only is the end of the chain", len(rows) > 0 and c["ends"] == 1, f"{c['ends']} rows are chain ends (expect 1)")
    return res


def closing(d):
    """Balance after the last row in the chain (laptop only)."""
    c = d["chain"]
    if c["end"] is None:
        return None
    r = d["rows"][c["end"]]
    return {"as_of": d["to"], "balance": r["balance"], "convention": d["convention"]}


def diag(d):
    c = d["chain"]
    return [f"    rows {len(d['rows'])}, convention {d['convention']}, rows with no predecessor {c['no_pred']}, rows with more than one possible predecessor {c['ambiguous']}, chain ends {c['ends']}, "
            f"printed order misfits {printed_order_misfits(d)}, unread {d['unread']}"]
