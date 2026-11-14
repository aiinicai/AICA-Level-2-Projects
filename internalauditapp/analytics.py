"""Transaction data analytics (CAATs) - pure Python, no pandas required.

Supports CSV and Excel files. Each test returns a dict:
    {"summary": {...}, "exceptions": [row, ...], "chart": {...} | None}
"""
import csv
import io
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

MAX_EXCEPTIONS = 5000

TESTS = {
    "duplicates": {
        "name": "Duplicate Transactions",
        "description": "Same party and amount (and optional document no.) appearing more than once, or within N days.",
        "needs": ["amount", "party"], "optional": ["date", "doc_no"],
        "params": {"window_days": 7},
    },
    "benford": {
        "name": "Benford's Law (First Digit)",
        "description": "Compares first-digit distribution of amounts to Benford's expected frequencies to spot manipulation.",
        "needs": ["amount"], "optional": [], "params": {"min_amount": 10},
    },
    "weekend": {
        "name": "Weekend / Holiday Postings",
        "description": "Transactions dated on weekend days or listed public holidays.",
        "needs": ["date"], "optional": ["amount"],
        "params": {"weekend_days": "Sat,Sun", "holidays": ""},
    },
    "round_amounts": {
        "name": "Round Amount Transactions",
        "description": "Amounts that are exact multiples of a round figure (e.g. 1,000) above a threshold.",
        "needs": ["amount"], "optional": [], "params": {"multiple": 1000, "min_amount": 5000},
    },
    "outliers": {
        "name": "Statistical Outliers",
        "description": "Amounts more than Z standard deviations from the mean (overall or per party).",
        "needs": ["amount"], "optional": ["party"], "params": {"z": 3, "per_party": "yes"},
    },
    "sequence_gaps": {
        "name": "Document Sequence Gaps & Duplicates",
        "description": "Missing or duplicated numbers in a document sequence (invoices, receipts, POs).",
        "needs": ["doc_no"], "optional": [], "params": {"max_gap_report": 500},
    },
    "split": {
        "name": "Split Transactions (Approval Limit Avoidance)",
        "description": "Multiple transactions to the same party within N days, each below the approval limit but together above it.",
        "needs": ["amount", "party", "date"], "optional": [],
        "params": {"limit": 50000, "window_days": 3},
    },
    "below_threshold": {
        "name": "Just-Below Approval Threshold",
        "description": "Transactions between X% and 100% of an approval limit.",
        "needs": ["amount"], "optional": [], "params": {"limit": 50000, "pct": 90},
    },
    "sod": {
        "name": "Segregation of Duties (Creator = Approver)",
        "description": "Transactions created and approved by the same user.",
        "needs": ["user", "approver"], "optional": [], "params": {},
    },
    "period_end": {
        "name": "Period-End Cut-off Postings",
        "description": "Transactions dated within N days of month-end (cut-off / window-dressing risk).",
        "needs": ["date"], "optional": ["amount"], "params": {"days": 2, "min_amount": 0},
    },
    "stratification": {
        "name": "Stratification & Top Parties",
        "description": "Value bands, counts and top 20 parties by value - useful for scoping and sampling.",
        "needs": ["amount"], "optional": ["party"], "params": {},
    },
}

BENFORD = {d: math.log10(1 + 1 / d) for d in range(1, 10)}
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d-%b-%Y", "%d %b %Y",
                "%Y/%m/%d", "%d.%m.%Y", "%d-%b-%y", "%d/%m/%y", "%b %d, %Y", "%Y%m%d"]


# ---------------------------------------------------------------- file loading
def read_table(path):
    """Return (headers, rows as list of dicts) from a CSV or XLSX file."""
    if path.lower().endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        it = ws.iter_rows(values_only=True)
        headers = None
        rows = []
        for r in it:
            if headers is None:
                if r and any(c not in (None, "") for c in r):
                    headers = [str(c).strip() if c is not None else f"Column{i + 1}" for i, c in enumerate(r)]
                continue
            if r is None or all(c in (None, "") for c in r):
                continue
            rows.append({headers[i]: r[i] if i < len(r) else None for i in range(len(headers))})
        wb.close()
        return headers or [], rows
    with open(path, "rb") as fh:
        raw = fh.read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = [h.strip() for h in (reader.fieldnames or [])]
    rows = []
    for r in reader:
        rows.append({(k or "").strip(): v for k, v in r.items()})
    return headers, rows


def guess_mapping(headers):
    hints = {
        "amount": ["amount", "value", "total", "net", "gross", "debit", "amt", "invoice amount"],
        "date": ["date", "posting", "doc date", "invoice date", "txn date", "transaction date"],
        "party": ["vendor", "supplier", "customer", "party", "payee", "name", "account name"],
        "doc_no": ["invoice no", "invoice number", "document", "doc no", "voucher", "receipt", "number", "ref"],
        "user": ["created by", "user", "entered by", "prepared by", "posted by"],
        "approver": ["approved by", "approver", "authorised by", "authorized by"],
    }
    mapping = {}
    lower = {h: h.lower() for h in headers}
    for field, keys in hints.items():
        for k in keys:
            match = next((h for h in headers if k in lower[h] and h not in mapping.values()), None)
            if match:
                mapping[field] = match
                break
    return mapping


# ---------------------------------------------------------------- parsers
def to_amount(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    neg = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[^0-9.\-]", "", s)
    if s in ("", "-", ".", "-."):
        return None
    try:
        val = float(s)
    except ValueError:
        return None
    return -abs(val) if neg else val


def to_date(v):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float)) and 20000 < v < 80000:  # Excel serial date
        return date(1899, 12, 30) + timedelta(days=int(v))
    s = str(v).strip()
    s = s.split("T")[0]
    if " " in s and ":" in s:
        s = s.rsplit(" ", 1)[0] if s.count(":") else s
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _txt(v):
    return "" if v is None else str(v).strip()


def _serialise(row):
    out = {}
    for k, v in row.items():
        if isinstance(v, (datetime, date)):
            v = v.isoformat()[:10]
        elif v is not None and not isinstance(v, (str, int, float, bool)):
            v = str(v)
        out[str(k)] = v
    return out


# ---------------------------------------------------------------- tests
def run_test(test, headers, rows, mapping, params):
    if test not in TESTS:
        raise ValueError(f"Unknown test {test}")
    spec = TESTS[test]
    missing = [f for f in spec["needs"] if not mapping.get(f)]
    if missing:
        raise ValueError("Please map the required column(s): " + ", ".join(missing))
    p = dict(spec["params"])
    p.update({k: v for k, v in (params or {}).items() if v not in (None, "")})
    fn = globals()[f"_t_{test}"]
    result = fn(rows, mapping, p)
    result["exceptions"] = [_serialise(r) for r in result["exceptions"][:MAX_EXCEPTIONS]]
    result.setdefault("chart", None)
    result["summary"]["total_records"] = len(rows)
    result["summary"]["exceptions"] = result["summary"].get("exceptions", len(result["exceptions"]))
    cols = []
    for r in result["exceptions"][:200]:
        for k in r:
            if k not in cols:
                cols.append(k)
    result["columns"] = cols or ["_reason"] + headers
    return result


def _amounts(rows, col):
    return [(r, to_amount(r.get(col))) for r in rows]


def _t_duplicates(rows, m, p):
    window = int(float(p["window_days"]))
    groups = defaultdict(list)
    for r in rows:
        amt = to_amount(r.get(m["amount"]))
        if amt is None or amt == 0:
            continue
        groups[(_txt(r.get(m["party"])).lower(), round(amt, 2))].append(r)
    exc, value = [], 0.0
    for (party, amt), items in groups.items():
        if len(items) < 2:
            continue
        flagged = []
        if m.get("doc_no"):
            docs = Counter(re.sub(r"\W", "", _txt(i.get(m["doc_no"])).lower()) for i in items)
            for i in items:
                if docs[re.sub(r"\W", "", _txt(i.get(m["doc_no"])).lower())] > 1:
                    flagged.append((i, "Exact duplicate: same party, amount and document no."))
        if m.get("date"):
            dated = sorted(((to_date(i.get(m["date"])), i) for i in items), key=lambda x: x[0] or date.min)
            for a, b in zip(dated, dated[1:]):
                if a[0] and b[0] and (b[0] - a[0]).days <= window:
                    for d, i in (a, b):
                        flagged.append((i, f"Same party & amount within {window} days"))
        if not m.get("doc_no") and not m.get("date"):
            flagged = [(i, "Same party and amount") for i in items]
        seen = set()
        for i, reason in flagged:
            if id(i) in seen:
                continue
            seen.add(id(i))
            row = {"_reason": reason}
            row.update(i)
            exc.append(row)
            value += amt
    return {"summary": {"potential_duplicate_value": round(value, 2), "exceptions": len(exc)},
            "exceptions": exc}


def _t_benford(rows, m, p):
    min_amt = float(p["min_amount"])
    digits, by_digit = Counter(), defaultdict(list)
    for r, a in _amounts(rows, m["amount"]):
        if a is None or abs(a) < min_amt:
            continue
        s = re.sub(r"[^1-9]", "", f"{abs(a):.2f}".lstrip("0."))
        if not s:
            continue
        d = int(s[0])
        digits[d] += 1
        by_digit[d].append(r)
    n = sum(digits.values())
    table, chi, mad, flagged = [], 0.0, 0.0, []
    for d in range(1, 10):
        exp = BENFORD[d]
        act = digits[d] / n if n else 0
        chi += ((digits[d] - exp * n) ** 2 / (exp * n)) if n else 0
        mad += abs(act - exp)
        z = 0.0
        if n:
            se = math.sqrt(exp * (1 - exp) / n)
            z = (abs(act - exp) - 1 / (2 * n)) / se if se else 0
        table.append({"digit": d, "count": digits[d], "actual_pct": round(act * 100, 2),
                      "expected_pct": round(exp * 100, 2), "z_stat": round(z, 2)})
        if z > 1.96 and act > exp:
            flagged.append(d)
    mad = mad / 9
    conformity = ("Close conformity" if mad < 0.006 else "Acceptable conformity" if mad < 0.012
                  else "Marginal conformity" if mad < 0.015 else "Non-conformity")
    exc = []
    for d in flagged:
        for r in by_digit[d]:
            row = {"_reason": f"First digit {d} over-represented (z={table[d - 1]['z_stat']})"}
            row.update(r)
            exc.append(row)
    return {"summary": {"records_tested": n, "chi_square": round(chi, 2), "mad": round(mad, 4),
                        "conformity": conformity, "flagged_digits": ", ".join(map(str, flagged)) or "None",
                        "exceptions": len(exc)},
            "exceptions": exc, "table": table,
            "chart": {"type": "benford", "labels": [str(t["digit"]) for t in table],
                      "actual": [t["actual_pct"] for t in table],
                      "expected": [t["expected_pct"] for t in table]}}


def _t_weekend(rows, m, p):
    names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    wk = {names.index(x.strip().lower()[:3]) for x in str(p["weekend_days"]).split(",")
          if x.strip().lower()[:3] in names}
    hol = {to_date(h.strip()) for h in str(p.get("holidays", "")).split(",") if h.strip()}
    exc, unparsed = [], 0
    for r in rows:
        d = to_date(r.get(m["date"]))
        if not d:
            unparsed += 1
            continue
        reason = None
        if d in hol:
            reason = "Posted on public holiday"
        elif d.weekday() in wk:
            reason = f"Posted on {d.strftime('%A')}"
        if reason:
            row = {"_reason": reason}
            row.update(r)
            exc.append(row)
    total = sum(to_amount(e.get(m["amount"])) or 0 for e in exc) if m.get("amount") else None
    s = {"unparsed_dates": unparsed, "exceptions": len(exc)}
    if total is not None:
        s["exception_value"] = round(total, 2)
    return {"summary": s, "exceptions": exc}


def _t_round_amounts(rows, m, p):
    mult, mn = float(p["multiple"]), float(p["min_amount"])
    exc = []
    for r, a in _amounts(rows, m["amount"]):
        if a is not None and abs(a) >= mn and mult and abs(a) % mult == 0:
            row = {"_reason": f"Round amount (multiple of {mult:,.0f})"}
            row.update(r)
            exc.append(row)
    return {"summary": {"exception_value": round(sum(to_amount(e[m['amount']]) for e in exc), 2),
                        "exceptions": len(exc)}, "exceptions": exc}


def _t_outliers(rows, m, p):
    z_lim = float(p["z"])
    per_party = str(p.get("per_party", "yes")).lower().startswith("y") and m.get("party")
    groups = defaultdict(list)
    for r, a in _amounts(rows, m["amount"]):
        if a is not None:
            groups[_txt(r.get(m["party"])) if per_party else "_all"].append((r, a))
    exc = []
    for g, items in groups.items():
        vals = [a for _, a in items]
        if len(vals) < 5:
            continue
        mu, sd = statistics.mean(vals), statistics.pstdev(vals)
        if not sd:
            continue
        for r, a in items:
            z = (a - mu) / sd
            if abs(z) >= z_lim:
                row = {"_reason": f"z-score {z:.1f} (mean {mu:,.0f})" + (f" for {g}" if per_party else "")}
                row.update(r)
                exc.append(row)
    return {"summary": {"groups_tested": len(groups), "exceptions": len(exc)}, "exceptions": exc}


def _t_sequence_gaps(rows, m, p):
    nums = defaultdict(list)
    for r in rows:
        s = _txt(r.get(m["doc_no"]))
        mt = re.match(r"^(.*?)(\d+)\D*$", s)
        if mt:
            nums[mt.group(1)].append((int(mt.group(2)), r))
    exc, gaps_total, dups_total = [], 0, 0
    limit = int(float(p["max_gap_report"]))
    for prefix, items in nums.items():
        counter = Counter(n for n, _ in items)
        for n, r in items:
            if counter[n] > 1:
                row = {"_reason": f"Duplicate document number {prefix}{n}"}
                row.update(r)
                exc.append(row)
                dups_total += 1
        seq = sorted(counter)
        for a, b in zip(seq, seq[1:]):
            if b - a > 1:
                missing = b - a - 1
                gaps_total += missing
                if len([e for e in exc if e["_reason"].startswith("Gap")]) < limit:
                    exc.append({"_reason": f"Gap: {missing} missing between {prefix}{a} and {prefix}{b}",
                                m["doc_no"]: f"{prefix}{a + 1} .. {prefix}{b - 1}"})
    return {"summary": {"series": len(nums), "missing_numbers": gaps_total,
                        "duplicate_numbers": dups_total, "exceptions": len(exc)}, "exceptions": exc}


def _t_split(rows, m, p):
    limit, window = float(p["limit"]), int(float(p["window_days"]))
    groups = defaultdict(list)
    for r in rows:
        a, d = to_amount(r.get(m["amount"])), to_date(r.get(m["date"]))
        if a is not None and d and 0 < a < limit:
            groups[_txt(r.get(m["party"])).lower()].append((d, a, r))
    exc, clusters = [], 0
    for party, items in groups.items():
        items.sort(key=lambda x: x[0])
        i = 0
        while i < len(items):
            j, total = i, 0.0
            cluster = []
            while j < len(items) and (items[j][0] - items[i][0]).days <= window:
                total += items[j][1]
                cluster.append(items[j])
                j += 1
            if len(cluster) > 1 and total >= limit:
                clusters += 1
                for d, a, r in cluster:
                    row = {"_reason": f"Cluster #{clusters}: {len(cluster)} txns totalling {total:,.2f} within {window} days"}
                    row.update(r)
                    exc.append(row)
                i = j
            else:
                i += 1
    return {"summary": {"clusters": clusters, "exceptions": len(exc)}, "exceptions": exc}


def _t_below_threshold(rows, m, p):
    limit, pct = float(p["limit"]), float(p["pct"])
    lo = limit * pct / 100
    exc = []
    for r, a in _amounts(rows, m["amount"]):
        if a is not None and lo <= a < limit:
            row = {"_reason": f"{a / limit * 100:.1f}% of approval limit {limit:,.0f}"}
            row.update(r)
            exc.append(row)
    return {"summary": {"band": f"{lo:,.0f} - {limit:,.0f}", "exceptions": len(exc)}, "exceptions": exc}


def _t_sod(rows, m, p):
    exc = []
    for r in rows:
        u, a = _txt(r.get(m["user"])).lower(), _txt(r.get(m["approver"])).lower()
        if u and u == a:
            row = {"_reason": "Created and approved by the same user"}
            row.update(r)
            exc.append(row)
    return {"summary": {"exceptions": len(exc)}, "exceptions": exc}


def _t_period_end(rows, m, p):
    days, mn = int(float(p["days"])), float(p.get("min_amount") or 0)
    exc = []
    for r in rows:
        d = to_date(r.get(m["date"]))
        if not d:
            continue
        nxt = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
        to_end = (nxt - d).days - 1
        if to_end < days:
            a = to_amount(r.get(m["amount"])) if m.get("amount") else None
            if a is not None and abs(a) < mn:
                continue
            row = {"_reason": f"{to_end} day(s) before month-end"}
            row.update(r)
            exc.append(row)
    return {"summary": {"exceptions": len(exc)}, "exceptions": exc}


def _t_stratification(rows, m, p):
    bands = [0, 1000, 5000, 10000, 50000, 100000, 500000, 1000000, float("inf")]
    strata = [{"band": (f"{bands[i]:,.0f} - {bands[i + 1]:,.0f}" if bands[i + 1] != float("inf")
                        else f">= {bands[i]:,.0f}"), "count": 0, "value": 0.0} for i in range(len(bands) - 1)]
    neg = {"band": "Negative / credits", "count": 0, "value": 0.0}
    parties = defaultdict(float)
    total = 0.0
    for r, a in _amounts(rows, m["amount"]):
        if a is None:
            continue
        total += a
        if m.get("party"):
            parties[_txt(r.get(m["party"]))] += a
        if a < 0:
            neg["count"] += 1
            neg["value"] += a
            continue
        for i in range(len(bands) - 1):
            if bands[i] <= a < bands[i + 1]:
                strata[i]["count"] += 1
                strata[i]["value"] += a
                break
    strata.append(neg)
    for s in strata:
        s["value"] = round(s["value"], 2)
        s["pct_value"] = round(s["value"] / total * 100, 2) if total else 0
    top = sorted(parties.items(), key=lambda x: -x[1])[:20]
    exc = [{"_reason": f"Top party #{i + 1}", "Party": k, "Total Value": round(v, 2),
            "% of Total": round(v / total * 100, 2) if total else 0} for i, (k, v) in enumerate(top)]
    return {"summary": {"total_value": round(total, 2), "exceptions": 0},
            "exceptions": exc, "table": strata,
            "chart": {"type": "bars", "labels": [s["band"] for s in strata],
                      "values": [s["value"] for s in strata]}}
