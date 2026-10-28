"""Document series (GSTR-1 Table 13) worked out from the invoices actually received.

An invoice number is split into prefix + number + width (INV/0007 -> 'INV/', 7, 4; 1001 -> '', 1001, 4).
Numbers of one series are sorted and split into runs wherever a number is missing:

    1001..1009 and 1014..1023   ->   1001-1009 (9 docs)   and   1014-1023 (10 docs)

The missing numbers (1010-1013) are NOT put into any series; they are reported so that staff can enter them
as cancelled documents if they really were issued and cancelled.

Mode:  'prefix'   one family of series per prefix / number width (a single running sequence)
       'customer' one family of series per customer - needed when each customer has his own run of plain numbers
       'auto'     'customer' when the same plain number is used for more than one customer, else 'prefix'
"""
import re
from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from .models import DocSeries, STATUS_REJECTED

NATURE_INVOICE = "Invoices for outward supply"
NATURE_CREDIT = "Credit Note"
NATURE_DEBIT = "Debit Note"
_NO = re.compile(r"^(.*?)(\d+)$")
# VB/001/2026-2027 or INV/045/26-27: the running number sits before a financial-year suffix
_NO_FY = re.compile(r"^(.*?)(\d+)([/\-_ ]\d{2,4}[-/]\d{2,4})$")

# entry = (document number, customer key, nature)
Entry = Tuple[str, str, str]


def split_no(no: str):
    """'INV/0007' -> ('INV/', 7, 4, ''); 'VB/001/2026-2027' -> ('VB/', 1, 3, '/2026-2027').
    None when the number has no digits at the end."""
    t = (no or "").strip()
    m = _NO_FY.match(t)
    if m:
        return (m.group(1), int(m.group(2)), len(m.group(2)), m.group(3))
    m = _NO.match(t)
    return (m.group(1), int(m.group(2)), len(m.group(2)), "") if m else None


def customer_key(gstin: str, name: str) -> str:
    return (gstin or "").strip().upper() or (name or "").strip().upper() or "(UNREGISTERED)"


def entries_from_lines(lines) -> List[Entry]:
    out = []
    for l in lines:
        if l.review_status == STATUS_REJECTED or not (l.invoice_no or "").strip():
            continue
        nature = NATURE_CREDIT if l.note_type == "C" else NATURE_DEBIT if l.note_type == "D" else NATURE_INVOICE
        out.append((l.invoice_no.strip(), customer_key(l.recipient_gstin, l.recipient_name), nature))
    return out


def entries_from_sets(sets) -> List[Entry]:
    """Documents found in uploaded Master Template rows (invoices and notes)."""
    out = []
    for ds in sets or []:
        t = ds.get("tables", {})
        for key in ("b2b", "b2cl", "exp"):
            for r in t.get(key, []):
                if r.get("invoice_no"):
                    out.append((r["invoice_no"], customer_key(r.get("recipient_gstin", ""), r.get("recipient_name", "")),
                                NATURE_INVOICE))
        for key in ("cdnr", "cdnur"):
            for r in t.get(key, []):
                if r.get("note_no"):
                    nat = NATURE_DEBIT if r.get("note_type") == "D" else NATURE_CREDIT
                    out.append((r["note_no"], customer_key(r.get("recipient_gstin", ""), r.get("recipient_name", "")), nat))
    return out


def auto_mode(entries: Iterable[Entry]) -> str:
    """'customer' when one and the same number is used for different customers (separate series per customer)."""
    seen = defaultdict(set)
    for no, cust, nature in entries:
        sp = split_no(no)
        if sp:
            seen[(nature, sp[0].upper(), sp[2], sp[3].upper(), sp[1])].add(cust)
    return "customer" if any(len(v) > 1 for v in seen.values()) else "prefix"


def build_runs(entries: Iterable[Entry], mode: str = "auto") -> List[dict]:
    """-> [{nature, customer, prefix, width, first, last, total, from_no, to_no}] plus the gaps between runs
    ('gaps_after' = (first missing, last missing) or None)."""
    entries = list(entries)
    if mode == "auto":
        mode = auto_mode(entries)
    groups: Dict[tuple, set] = defaultdict(set)
    raw_prefix: Dict[tuple, str] = {}
    for no, cust, nature in entries:
        sp = split_no(no)
        if not sp:
            continue
        key = (nature, cust if mode == "customer" else "", sp[0].upper(), sp[2], sp[3].upper())
        groups[key].add(sp[1])
        raw_prefix.setdefault(key, (sp[0], sp[3]))
    runs: List[dict] = []
    for key in sorted(groups, key=lambda k: (k[0] != NATURE_INVOICE, k[0], k[1], k[2], k[3], k[4])):
        nature, cust, _p, width, _s = key
        prefix, suffix = raw_prefix[key]
        nums = sorted(groups[key])
        start = prev = nums[0]
        pieces = []
        for n in nums[1:]:
            if n != prev + 1:
                pieces.append((start, prev, (prev + 1, n - 1)))
                start = n
            prev = n
        pieces.append((start, prev, None))
        for a, b, gap in pieces:
            runs.append(dict(nature=nature, customer=cust, prefix=prefix, suffix=suffix, width=width, first=a, last=b,
                             total=b - a + 1, gap_after=gap,
                             from_no=f"{prefix}{str(a).zfill(width)}{suffix}", to_no=f"{prefix}{str(b).zfill(width)}{suffix}"))
    return runs


def runs_to_docs(runs: List[dict], mode: str) -> List[DocSeries]:
    out = []
    for r in runs:
        d = DocSeries(nature=r["nature"], from_no=r["from_no"], to_no=r["to_no"], total=r["total"], cancelled=0,
                      origin="derived")
        if mode == "customer" and r["customer"]:
            d.source_file = f"customer {r['customer']}"
        out.append(d)
    return out


def _covered_by_docs(r, docs, budget) -> bool:
    """True if the missing numbers after run r lie inside a typed / verified / uploaded series that declares enough
    cancelled documents, i.e. the user has already confirmed them as cancelled."""
    ga, gb = r["gap_after"]
    n = gb - ga + 1
    for d in docs or []:
        if d.origin == "derived" or (d.cancelled or 0) <= 0:
            continue
        f, t = split_no(d.from_no), split_no(d.to_no)
        if not f or not t or f[0].upper() != r["prefix"].upper() or t[0].upper() != r["prefix"].upper() \
                or f[3].upper() != r.get("suffix", "").upper() or t[3].upper() != r.get("suffix", "").upper():
            continue
        if f[1] <= ga and gb <= t[1] and budget.get(id(d), d.cancelled) >= n:
            budget[id(d)] = budget.get(id(d), d.cancelled) - n
            return True
    return False


def gap_report(runs: List[dict], docs=None) -> List[str]:
    """Human-readable list of missing numbers between consecutive runs.  Gaps that a typed / verified / uploaded
    series already accounts for as cancelled documents are left out."""
    out = []
    budget = {}
    for r in runs:
        if r["gap_after"]:
            if docs and _covered_by_docs(r, docs, budget):
                continue
            a, b = r["gap_after"]
            w = r["width"]
            sf = r.get("suffix", "")
            rng = f"{r['prefix']}{str(a).zfill(w)}{sf}" + (f" - {r['prefix']}{str(b).zfill(w)}{sf}" if b != a else "")
            who = f" [{r['customer']}]" if r["customer"] else ""
            out.append(f"{r['nature']}{who}: {rng} not in the file ({b - a + 1} number(s))")
    return out
