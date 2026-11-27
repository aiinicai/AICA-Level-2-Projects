"""Readers for two bank statement layouts, built from masked layouts (no real data seen).

  kotak_parse(pages)  Kotak savings statement: one table, one amount column, running balance, page-2 summary.
  indus_parse(pages)  IndusInd-style customer statement: summary of accounts, term deposits, then one block
                      per account (Brought Forward, dated rows, Carried Forward).
  Both take pages as returned by cdsl.read_rows: a list of pages, each a list of text rows.
  Every figure the checks compare is read from the file itself. Nothing is guessed.
  Direction of a row (money in or out) is NOT printed in these files. It is worked out from the running balance:
  previous balance + amount = balance (money in) or previous balance - amount = balance (money out).
"""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

D = Decimal
M = r"-?\d[\d,]*\.\d{2}"
MONEY_END2 = re.compile(rf"^(.*?)\s+({M})\s+({M})\s*$")
MONEY_END1 = re.compile(rf"({M})\s*$")


def money(s):
    try:
        return D(s.replace(",", ""))
    except InvalidOperation:
        return None


def _date(s, fmts):
    for f in fmts:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def _lines(pages):
    for p in pages:
        for r in p:
            r = r.strip()
            if r:
                yield r


# ============================================================================ Kotak
K_ROW = re.compile(r"^(\d{1,4}) (\d{2} [A-Z][a-z]{2} \d{4}) (.+)$")
K_PERIOD = re.compile(r"(\d{2} [A-Z][a-z]{2} \d{4}) - (\d{2} [A-Z][a-z]{2} \d{4})")
K_SUMMARY = re.compile(rf"^(.*?)\s*\(([^)]*)\):\s*({M})\s+({M})\s*$")


def kotak_parse(pages):
    d = {"account": None, "period": None, "opening": None, "rows": [], "unread": 0, "summary": [], "total": None}
    in_summary = False
    for ln in _lines(pages):
        if d["account"] is None:
            m = re.match(r"^Account No\.?\s*(\d{6,})", ln)
            if m:
                d["account"] = m.group(1)
        if d["period"] is None:
            m = K_PERIOD.search(ln)
            if m and not K_ROW.match(ln):
                d["period"] = (_date(m.group(1), ["%d %b %Y"]), _date(m.group(2), ["%d %b %Y"]))
        if re.search(r"Opening Balance", ln) and not in_summary and d["opening"] is None:
            m = MONEY_END1.search(ln)
            if m and not re.search(r"Particulars", ln):
                d["opening"] = money(m.group(1))
                continue
        if ln.startswith("Account Summary"):
            in_summary = True
            continue
        if in_summary:
            m = K_SUMMARY.match(ln)
            if m:
                label, code = m.group(1).strip(), m.group(2).strip()
                rec = {"label": label, "code": code, "open": money(m.group(3)), "close": money(m.group(4))}
                if label.lower().startswith("total"):
                    d["total"] = rec
                else:
                    d["summary"].append(rec)
            elif ln.startswith("Nominee"):
                in_summary = False
            continue
        m = K_ROW.match(ln)
        if m:
            tail = m.group(3)
            t = MONEY_END2.match(tail)
            if not t:
                d["unread"] += 1
                continue
            d["rows"].append({"serial": int(m.group(1)), "date": _date(m.group(2), ["%d %b %Y"]),
                              "desc": t.group(1), "amount": money(t.group(2)), "balance": money(t.group(3))})
    _direction(d["rows"], d["opening"])
    return d


def _direction(rows, opening):
    """Adds r['dir'] = 'in' / 'out' / 'none' (no fit) from the running balance."""
    prev = opening
    for r in rows:
        r["dir"] = "none"
        if prev is None or r["amount"] is None or r["balance"] is None:
            prev = r["balance"]
            continue
        if abs(prev + r["amount"] - r["balance"]) <= D("0.005"):
            r["dir"] = "in"
        elif abs(prev - r["amount"] - r["balance"]) <= D("0.005"):
            r["dir"] = "out"
        prev = r["balance"]


def kotak_checks(d):
    res = []

    def add(name, ok, det=""):
        res.append((name, "PASS" if ok else "FAIL", det))
    rows = d["rows"]
    add("Account number and period found", bool(d["account"]) and bool(d["period"] and all(d["period"])))
    add("Opening balance row found", d["opening"] is not None)
    add("Every dated row has an amount and a balance", d["unread"] == 0, f"{d['unread']} rows without both")
    ser = [r["serial"] for r in rows]
    add("Row numbers run 1, 2, 3 ... without a gap", ser == list(range(1, len(ser) + 1)),
        f"first {ser[0] if ser else '-'}, last {ser[-1] if ser else '-'}, count {len(ser)}")
    if d["period"] and all(d["period"]):
        bad = sum(1 for r in rows if not r["date"] or not (d["period"][0] <= r["date"] <= d["period"][1]))
        add("Every row date is inside the statement period", bad == 0, f"{bad} outside")
    dates = [r["date"] for r in rows if r["date"]]
    add("Dates never go backwards", all(a <= b for a, b in zip(dates, dates[1:])))
    nofit = sum(1 for r in rows if r["dir"] == "none")
    add("Running balance: previous balance plus or minus amount = balance, every row", nofit == 0, f"{nofit} rows do not fit")
    sav = d["summary"][0] if d["summary"] else None
    add("Summary line for the savings account found", sav is not None)
    if sav and d["opening"] is not None:
        add("Opening balance in table = opening balance in summary", d["opening"] == sav["open"],
            f"difference {abs(d['opening'] - sav['open'])}")
    if sav:
        last = rows[-1]["balance"] if rows else d["opening"]
        add("Last row balance = closing balance in summary", last is not None and last == sav["close"],
            f"difference {abs(last - sav['close']) if last is not None else 'n/a'}")
    if d["total"]:
        so = sum((r["open"] for r in d["summary"]), D(0))
        sc = sum((r["close"] for r in d["summary"]), D(0))
        add("Total balance line = sum of the lines above it (opening and closing)",
            so == d["total"]["open"] and sc == d["total"]["close"],
            f"differences {abs(so - d['total']['open'])} and {abs(sc - d['total']['close'])}")
    return res


def kotak_balances(d):
    """Real figures (laptop only). One record per balance line in the summary."""
    out = []
    end = d["period"][1] if d["period"] else None
    acc = (d["account"] or "")[-4:]
    for i, r in enumerate(d["summary"]):
        out.append({"bank": "Kotak", "account_last4": acc if i == 0 else acc + "+linked", "kind": r["label"],
                    "currency": "INR", "as_of": end, "balance": r["close"], "opening": r["open"]})
    return out


# ============================================================================ IndusInd-style
I_ACCT = r"[0-9A-Z]{8,20}"
I_SUM_ROW = re.compile(rf"^({I_ACCT})\s+(.*?)\s+([A-Z]{{3}})\s+({M})\s+({M})\s*$")
I_DATE = r"\d{2}-[A-Za-z]{3}-\d{2,4}"
I_FD_ROW = re.compile(rf"^({I_ACCT})\s+(.*?)\s+({I_DATE})\s+({I_DATE})\s+([A-Z]{{3}})\s+([\d.]+)%\s+({M})\s+({M})\s*$")
I_TOTAL = re.compile(rf"^Total\s+({M})\s*$")
I_TXN = re.compile(r"^(\d{2}-[A-Za-z]{3}-\d{4})\s+(.+)$")


def indus_parse(pages):
    d = {"period": None, "generated": None, "summary": [], "fds": [], "blocks": [], "unread": 0, "sum_totals": [], "fd_totals": []}
    pend_sum, pend_fd = [], []
    cur = None
    hdr = None
    expect_acct = False
    for ln in _lines(pages):
        if d["period"] is None:
            m = re.search(rf"Period\s*:\s*(\d{{2}}-[A-Za-z]{{3}}-\d{{4}})\s+To\s+(\d{{2}}-[A-Za-z]{{3}}-\d{{4}})", ln, re.I)
            if m:
                d["period"] = (_date(m.group(1), ["%d-%b-%Y"]), _date(m.group(2), ["%d-%b-%Y"]))
        if d["generated"] is None:
            m = re.search(rf"\bDate\s*:\s*(\d{{2}}-[A-Za-z]{{3}}-\d{{4}})", ln)
            if m and "Period" in ln:
                d["generated"] = _date(m.group(1), ["%d-%b-%Y"])
        if ln.startswith("Account Number Name Holding Status"):
            expect_acct = True
            continue
        if expect_acct:
            m = re.match(rf"^({I_ACCT})\b", ln)
            expect_acct = False
            if m:
                hdr = {"account": m.group(1), "product": None}
                continue
        if hdr is not None:
            m = re.search(r"Description\s*:\s*(.+?)(?:\s+Branch Address|$)", ln)
            if m and hdr["product"] is None:
                hdr["product"] = m.group(1).strip()
            if ln.startswith("Date Particulars"):          # end of the page header: a new block or the same one continued
                if cur is None or (cur["account"], cur["product"]) != (hdr["account"], hdr["product"]):
                    cur = {"account": hdr["account"], "product": hdr["product"], "bf": None, "cf": None, "rows": [], "bfs": [], "cfs": [], "stray2": 0, "stray1": 0}
                    d["blocks"].append(cur)
                hdr = None
                continue
        m = I_FD_ROW.match(ln)
        if m:
            pend_fd.append({"account": m.group(1), "type": m.group(2), "start": _date(m.group(3), ["%d-%b-%y", "%d-%b-%Y"]),
                            "maturity": _date(m.group(4), ["%d-%b-%y", "%d-%b-%Y"]), "currency": m.group(5),
                            "rate": D(m.group(6)), "lien": money(m.group(7)), "value": money(m.group(8))})
            continue
        m = I_SUM_ROW.match(ln)
        if m and not I_TXN.match(ln):
            pend_sum.append({"account": m.group(1), "type": m.group(2), "currency": m.group(3), "lien": money(m.group(4)), "balance": money(m.group(5))})
            continue
        m = I_TOTAL.match(ln)
        if m:
            tot = money(m.group(1))
            if pend_fd:
                d["fds"].extend(pend_fd)
                d["fd_totals"].append((tot, sum((r["value"] for r in pend_fd), D(0)), len(pend_fd)))
                pend_fd = []
            elif pend_sum:
                d["summary"].extend(pend_sum)
                d["sum_totals"].append((tot, sum((r["balance"] for r in pend_sum), D(0)), len(pend_sum)))
                pend_sum = []
            continue
        if cur is not None:
            m = re.match(rf"^(?:\d{{2}}-[A-Za-z]{{3}}-\d{{4}}\s+)?(Brought Forward|Carried Forward)\s+({M})\s*$", ln)
            if m:
                v = money(m.group(2))
                if m.group(1).startswith("Brought"):
                    cur["bfs"].append((len(cur["rows"]), v))
                    if cur["bf"] is None:
                        cur["bf"] = v              # opening of the block = the FIRST Brought Forward
                else:
                    cur["cfs"].append((len(cur["rows"]), v))
                    cur["cf"] = v                  # closing of the block = the LAST Carried Forward
                continue
            m = I_TXN.match(ln)
            if m:
                t = MONEY_END2.match(m.group(2))
                if not t:
                    d["unread"] += 1
                    continue
                cur["rows"].append({"date": _date(m.group(1), ["%d-%b-%Y"]), "desc": t.group(1), "amount": money(t.group(2)), "balance": money(t.group(3))})
                continue
            if MONEY_END2.match(ln):
                cur["stray2"] += 1                 # a line ending in two amounts that is not a dated row
            elif MONEY_END1.search(ln) and not ln.startswith(("Page", "Registered")):
                cur["stray1"] += 1
    d["fds"].extend(pend_fd)
    d["summary"].extend(pend_sum)
    d["leftover"] = (len(pend_sum), len(pend_fd))          # rows not closed by a Total line
    for b in d["blocks"]:
        _direction(b["rows"], b["bf"])
    return d


def summary_for(d, b):
    """The summary row of a transaction block. Account numbers can repeat between accounts, so the product text decides.
    Returns (row or None, reason). Reason is '' when found, 'none' or 'ambiguous' otherwise."""
    cand = [r for r in d["summary"] if r["account"] == b["account"]]
    if len(cand) > 1 and b.get("product"):
        p = b["product"].upper()
        narrowed = [r for r in cand if r["type"].upper().startswith(p) or p in r["type"].upper()]
        cand = narrowed or cand
    if not cand:
        return None, "none"
    if len(cand) > 1:
        return None, "ambiguous"
    return cand[0], ""


def indus_checks(d):
    res = []

    def add(name, ok, det=""):
        res.append((name, "PASS" if ok else "FAIL", det))
    add("Statement period found", bool(d["period"] and all(d["period"])))
    add("Account summary rows read", len(d["summary"]) > 0, f"{len(d['summary'])} rows")
    bad = [abs(t - s) for t, s, n in d["sum_totals"] if t != s]
    add("Account summary: each Total line = sum of its rows", d["sum_totals"] and not bad and d["leftover"][0] == 0,
        f"{len(d['sum_totals'])} tables, {len(bad)} differ, {d['leftover'][0]} rows without a Total line")
    add("Term deposit rows read", len(d["fds"]) > 0, f"{len(d['fds'])} rows")
    bad = [abs(t - s) for t, s, n in d["fd_totals"] if t != s]
    add("Term deposits: each Total line = sum of its rows", d["fd_totals"] and not bad and d["leftover"][1] == 0,
        f"{len(d['fd_totals'])} tables, {len(bad)} differ, {d['leftover'][1]} rows without a Total line")
    badfd = sum(1 for r in d["fds"] if not (r["start"] and r["maturity"] and r["start"] <= r["maturity"]))
    add("Term deposits: start date on or before maturity date", badfd == 0, f"{badfd} rows")
    add("Transaction blocks found", len(d["blocks"]) > 0, f"{len(d['blocks'])} blocks")
    add("Every dated row has an amount and a balance", d["unread"] == 0, f"{d['unread']} rows without both")
    nobf = sum(1 for b in d["blocks"] if b["bf"] is None or b["cf"] is None)
    add("Every block has a Brought Forward and a Carried Forward line", nobf == 0, f"{nobf} blocks without")
    st2 = sum(b["stray2"] for b in d["blocks"])
    add("No line ending in two amounts sits outside the dated rows", st2 == 0, f"{st2} lines")
    nofit = sum(1 for b in d["blocks"] for r in b["rows"] if r["dir"] == "none")
    add("Running balance: previous balance plus or minus amount = balance, every row", nofit == 0, f"{nofit} rows do not fit")
    pg_bad = 0
    for b in d["blocks"]:
        for k, v in b["bfs"][1:] + b["cfs"][:-1]:
            before = b["rows"][k - 1]["balance"] if k else b["bf"]
            pg_bad += before != v
    add("Page-level Brought Forward and Carried Forward lines equal the balance at that point", pg_bad == 0, f"{pg_bad} differ")
    lastbad = 0
    for b in d["blocks"]:
        last = b["rows"][-1]["balance"] if b["rows"] else b["bf"]
        if b["cf"] is None or last != b["cf"]:
            lastbad += 1
    add("Last row balance = Carried Forward, every block", lastbad == 0, f"{lastbad} blocks differ")
    if d["period"] and all(d["period"]):
        out = sum(1 for b in d["blocks"] for r in b["rows"] if not r["date"] or not (d["period"][0] <= r["date"] <= d["period"][1]))
        add("Every row date is inside the statement period", out == 0, f"{out} outside")
    found = [(b, summary_for(d, b)) for b in d["blocks"]]
    miss = sum(1 for b, (r, why) in found if why == "none")
    add("Every transaction block belongs to an account in the summary", miss == 0, f"{miss} blocks not in summary")
    amb = sum(1 for b, (r, why) in found if why == "ambiguous")
    cmp_bad = sum(1 for b, (r, why) in found if r and b["cf"] is not None and r["balance"] != b["cf"])
    cmp_n = sum(1 for b, (r, why) in found if r and b["cf"] is not None)
    add("Summary balance = Carried Forward of its block", cmp_bad == 0 and amb == 0,
        f"{cmp_n} compared, {cmp_bad} differ, {amb} blocks match more than one summary row; {len(d['summary']) - cmp_n} summary accounts have no block")
    return res


def indus_diag(d):
    """Safe diagnostics: counts and sizes only."""
    out = []
    for i, b in enumerate(d["blocks"], 1):
        s, _why = summary_for(d, b)
        last = b["rows"][-1]["balance"] if b["rows"] else b["bf"]
        nofit = sum(1 for r in b["rows"] if r["dir"] == "none")
        diff = "n/a" if (s is None or b["cf"] is None) else str(abs(s["balance"] - b["cf"]))
        out.append(f"    block {i}: rows {len(b['rows'])}, brought forward {'yes' if b['bf'] is not None else 'no'}, carried forward {'yes' if b['cf'] is not None else 'no'}, "
                   f"in summary {'yes' if s else 'no'}, rows not fitting {nofit}, last vs carried diff {abs(last - b['cf']) if (last is not None and b['cf'] is not None) else 'n/a'}, summary vs carried diff {diff}")
        prev, shown = b["bf"], 0
        for j, r in enumerate(b["rows"], 1):
            if r["dir"] == "none" and prev is not None and shown < 3:
                out.append(f"      row {j}: previous + amount - balance = {prev + r['amount'] - r['balance']};  previous - amount - balance = {prev - r['amount'] - r['balance']};  "
                           f"balance change = {r['balance'] - prev}")
                shown += 1
            prev = r["balance"]
        left, bal, placed = list(b["rows"]), b["bf"], 0
        while left and bal is not None:
            hit = next((r for r in left if r["amount"] is not None and (abs(bal + r["amount"] - r["balance"]) <= D("0.005") or abs(bal - r["amount"] - r["balance"]) <= D("0.005"))), None)
            if hit is None:
                break
            bal = hit["balance"]
            left.remove(hit)
            placed += 1
        out.append(f"      lines ending in two amounts but not dated rows: {b['stray2']}; lines ending in one amount: {b['stray1']}")
        out.append(f"      rows that chain from Brought Forward in ANY order: {placed} of {len(b['rows'])}")
        out.append(f"      Brought Forward lines {len(b['bfs'])}, Carried Forward lines {len(b['cfs'])}, rows before each: {[k for k, _ in b['bfs']]} / {[k for k, _ in b['cfs']]}")
    for i, (t, s, n) in enumerate(d["sum_totals"], 1):
        out.append(f"    summary table {i}: rows {n}, total line minus sum of rows = {t - s}")
    for i, (t, s, n) in enumerate(d["fd_totals"], 1):
        out.append(f"    term deposit table {i}: rows {n}, total line minus sum of rows = {t - s}")
    return out


def _kind(text, currency, fd):
    """Short account label from the type text. Holder status and holder name are never kept."""
    t = text.upper()
    if currency != "INR":
        return "Foreign currency FD" if fd else "Foreign currency account"
    tag = "NRE" if "NRE" in t else "NRO" if "NRO" in t else ""
    if fd:
        return (tag + " tax saver FD" if "SAVER" in t else tag + " FD").strip()
    return (tag + " savings").strip()


def indus_balances(d):
    """Real figures (laptop only)."""
    end = d["period"][1] if d["period"] else None
    out = []
    for r in d["summary"]:
        out.append({"bank": "IndusInd", "account_last4": r["account"][-4:], "kind": _kind(r["type"], r["currency"], False), "currency": r["currency"], "as_of": end, "balance": r["balance"], "lien": r["lien"]})
    return out


def indus_fds(d):
    return [{"bank": "IndusInd", "account_last4": r["account"][-4:], "kind": _kind(r["type"], r["currency"], True), "start": r["start"], "maturity": r["maturity"],
             "currency": r["currency"], "rate_pct": r["rate"], "lien": r["lien"], "current_value": r["value"]} for r in d["fds"]]


def kotak_diag(d):
    """Safe diagnostics: counts and sizes of differences only."""
    n_in = sum(1 for r in d["rows"] if r["dir"] == "in")
    n_out = sum(1 for r in d["rows"] if r["dir"] == "out")
    out = [f"    rows {len(d['rows'])}, money in {n_in}, money out {n_out}, not fitting {len(d['rows']) - n_in - n_out}, "
           f"unread {d['unread']}, summary lines {len(d['summary'])}, total line {'yes' if d['total'] else 'no'}"]
    prev, shown = d["opening"], 0
    for r in d["rows"]:
        if r["dir"] == "none" and prev is not None and shown < 3:
            out.append(f"    row {r['serial']}: previous + amount - balance = {prev + r['amount'] - r['balance']};  previous - amount - balance = {prev - r['amount'] - r['balance']}")
            shown += 1
        prev = r["balance"]
    return out
