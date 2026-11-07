"""Key-figure reconciliation: every amount, percentage, date and time-period in the draft against the executed copy.

An executive can read this table instead of the whole redline: a figure that exists on only one side is a risk, whatever
clause it sits in.  Figures are normalised (Rs. 10,00,000/-  =  ₹ 1000000  =  Rs. 10 lakh) before they are compared.
"""
import re
from collections import Counter, defaultdict

_MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_MULT = {"lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "crore": 1e7, "crores": 1e7, "cr": 1e7, "million": 1e6, "billion": 1e9, "thousand": 1e3}

_PCT = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*(?:%|per\s?cent\b|percent\b)", re.I)
_AMT = re.compile(r"(?P<cur>(?:Rs\.?|INR|₹|USD|US\$|\$)\s*)?(?P<num>\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?:\s*/-)?(?:\s*(?P<mul>lakhs?|lacs?|crores?|cr|million|billion|thousand)\b)?", re.I)
_DATE1 = re.compile(r"\b(\d{1,2}|[Il]st)\s*(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+(\d{4})\b", re.I)
_DATE2 = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4}|\d{2})\b")
_PER2 = re.compile(r"\(\s*(\d{1,4})\s*\)\s*(business\s+days?|working\s+days?|calendar\s+days?|days?|weeks?|months?|years?)\b", re.I)
_PER = re.compile(r"\b(\d{1,4})\s*(?:\(\s*\d{1,4}\s*\)\s*)?(business\s+days?|working\s+days?|calendar\s+days?|days?|weeks?|months?|years?)\b", re.I)


def _unit(u):
    u = u.lower().rstrip("s")
    return "business day" if u.startswith(("business", "working")) else ("day" if u.startswith(("calendar", "day")) else u)


def facts_of_text(text):
    """-> list of (kind, key, shown)"""
    out = []
    taken = []

    def free(span):
        return all(span[1] <= a or span[0] >= b for a, b in taken)

    for m in _DATE1.finditer(text):
        d, mo, y = (1 if m.group(1)[-2:].lower() == "st" and not m.group(1)[0].isdigit() else int(m.group(1))), _MON[m.group(2).lower()[:3]], int(m.group(3))
        out.append(("Date", f"{y:04d}-{mo:02d}-{d:02d}", m.group(0).strip())); taken.append(m.span())
    for m in _DATE2.finditer(text):
        if not free(m.span()):
            continue
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3)); y = y + 2000 if y < 100 else y
        if 1 <= d <= 31 and 1 <= mo <= 12:
            out.append(("Date", f"{y:04d}-{mo:02d}-{d:02d}", m.group(0))); taken.append(m.span())
    for m in _PCT.finditer(text):
        out.append(("Percentage", f"{float(m.group(1)):g}%", m.group(0).strip())); taken.append(m.span())
    for m in list(_PER.finditer(text)) + list(_PER2.finditer(text)):
        if free(m.span()):
            out.append(("Period", f"{int(m.group(1))} {_unit(m.group(2))}", m.group(0).strip())); taken.append(m.span())
    for m in _AMT.finditer(text):
        if not free(m.span()):
            continue
        raw = m.group("num"); v = float(raw.replace(",", ""))
        mul = (m.group("mul") or "").lower()
        if mul:
            v *= _MULT[mul]
        cur = bool(m.group("cur")) or "," in raw or bool(mul)
        if not cur and len(raw.replace(".", "")) >= 9 or v >= 1e12:
            continue                         # certificate / PAN / account style numbers
        if not cur and v < 10000:
            continue                         # clause numbers, years, counts of shares/directors, plot numbers …
        if not m.group("cur") and not mul and 1900 <= v <= 2100:
            continue
        out.append(("Amount", f"{v:,.2f}".rstrip("0").rstrip("."), m.group(0).strip().rstrip("/-").strip()))
    return out


def facts_of_doc(doc):
    res = []
    for b in doc.blocks:
        if getattr(b, "ignored", False):
            continue
        for kind, key, shown in facts_of_text(b.text):
            res.append(dict(kind=kind, key=key, shown=shown, clause=b.label or "", page=b.page if doc.kind in ("pdf", "image") else 0, conf=getattr(b, "conf", 100.0)))
    return res


KINDS = ("Amount", "Percentage", "Date", "Period")


def reconcile(result):
    """-> {kind: {"matched": n, "rows": [dict(status, draft, executed, clause, page)]}}"""
    fa, fb = facts_of_doc(result.doc_a), facts_of_doc(result.doc_b)
    out = {}
    for kind in KINDS:
        A = [f for f in fa if f["kind"] == kind]; B = [f for f in fb if f["kind"] == kind]
        ca, cb = Counter(f["key"] for f in A), Counter(f["key"] for f in B)
        matched = sum((ca & cb).values())
        left = defaultdict(list); right = defaultdict(list)
        used = Counter()
        for f in A + B:
            f["clause"] = re.sub(r"[.)\s]+$", "", f["clause"])
        for f in A:
            if used[f["key"]] < cb[f["key"]]:
                used[f["key"]] += 1
            else:
                left[f["clause"]].append(f)
        used = Counter()
        for f in B:
            if used[f["key"]] < ca[f["key"]]:
                used[f["key"]] += 1
            else:
                right[f["clause"]].append(f)
        rows = []
        for clause in list(dict.fromkeys(list(left) + list(right))):
            L, R = left.get(clause, []), right.get(clause, [])
            for i in range(max(len(L), len(R))):
                a = L[i] if i < len(L) else None; b = R[i] if i < len(R) else None
                low = bool(b and b["conf"] < 75)
                st = "Changed" if a and b else ("Missing in executed copy" if a else "Not in draft")
                rows.append(dict(status=st + (" (low OCR confidence – verify)" if low else ""), draft=a["shown"] if a else "—", executed=b["shown"] if b else "—",
                                 clause=clause or "—", page=b["page"] if b else 0))
        out[kind] = dict(matched=matched, draft_total=len(A), exec_total=len(B), rows=rows)
    return out
