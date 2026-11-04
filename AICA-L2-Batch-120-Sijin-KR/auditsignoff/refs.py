"""Where-to-look references for findings: PDF page (+ printed page) or the nearest Word heading."""
from __future__ import annotations
import re


def _n(x):
    return re.sub(r"[\s ]+", " ", str(x)).lower()


def printed_map(doc):
    m = {}
    for i, p in enumerate(doc.pages):
        lines = [l.strip() for l in p.splitlines() if l.strip()]
        for l in lines[:2] + lines[-2:]:
            mm = re.search(r"(?:Analysis|Report|Update|Statements?)\s+(\d{1,3})$", l) or re.fullmatch(r"(?:page\s+)?(\d{1,3})(?:\s+of\s+\d+)?", l, re.I)
            if mm:
                m[i + 1] = int(mm.group(1))
                break
    return m


def needles(f):
    out = re.findall(r"'([^']{4,80})'", f.detail or "")
    for v in (f.found, f.expected):
        if v and len(str(v)) >= 4 and re.search(r"[A-Za-z0-9]", str(v)):
            out.append(str(v).strip("[]'\" "))
    out += [s.strip() for s in re.split(r"[;|]", f.detail or "") if 8 <= len(s.strip()) <= 70][:2]
    return [_n(x)[:60] for x in out if x]


def locate(doc, f):
    if re.search(r"\bp\.\s?\d|\bpage\s+\d|pdf p\.|table \d|body para|row \d|section \d|under heading|cell|sheet", f.location or "", re.I):
        return
    ns = needles(f)
    if doc.kind != "docx" and doc.pages:
        pm = None
        for n in ns:
            for i, pg in enumerate(doc.pages):
                if n and n in _n(pg):
                    pm = pm if pm is not None else printed_map(doc)
                    pr = pm.get(i + 1)
                    f.location = f"{f.location} - PDF p.{i + 1}" + (f" (printed p.{pr})" if pr else "")
                    return
    elif doc.kind == "docx":
        head = ""
        for p in doc.paragraphs:
            t = p.text.strip()
            if p.where != "body" or not t:
                continue
            if len(t) < 90 and (re.match(r"^\d+(\.\d+)*\.?\s+\S", t) or p.style.lower().startswith("heading")
                                or re.match(r"^(statement of|notes to|independent auditor|directors.? report)", t, re.I)):
                head = t
            for n in ns:
                if n and n in _n(t):
                    f.location = f"{f.location} - under heading '{head or 'start'}'"
                    return
        for tb in doc.tables:                    # evidence inside a table: give table location
            for r in tb.rows:
                if any(n and n in _n(" ".join(r)) for n in ns):
                    f.location = f"{f.location} - {tb.loc}"
                    return


def add_refs(doc, results):
    for r in results:
        for f in r.findings:
            try:
                locate(doc, f)
            except Exception:
                pass
