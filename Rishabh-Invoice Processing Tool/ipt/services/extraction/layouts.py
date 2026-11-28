"""Learn where each supplier prints its fields, and use it on the next scanned bill of that supplier.

Learning: when a scanned invoice is approved (its values confirmed by the user), each confirmed value is looked
up among the OCR words of its first page; if exactly one word (or phrase) carries it, that position is stored
for the supplier GSTIN (a running average over the bills seen).

Using: for a new bill of the same supplier, a field that OCR left empty or unsure is read from the words at the
learned position. Values are checked (a date must be a date, amounts must make taxable + tax = total), and they
are marked as a guess so the review screen still asks for a look. A confident reading is never replaced.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select

from ipt.core.textnorm import normalize_invoice_no, parse_date
from ipt.db.models import Invoice, SupplierLayout

FIELDS = ("invoice_no", "invoice_date", "taxable_total", "cgst", "sgst", "igst", "invoice_total")
AMOUNTS = {"taxable_total", "cgst", "sgst", "igst", "invoice_total"}
GUESS, LOW, SURE = 0.65, 0.55, 0.6


def _words(boxes) -> list[tuple[str, float, float, float, float]]:
    """OCR boxes (often whole phrases) split into single words with a share of the box width."""
    out = []
    for text, x0, y0, x1, y1 in boxes:
        parts = str(text).split()
        if len(parts) <= 1:
            out.append((str(text), x0, y0, x1, y1))
            continue
        per = (x1 - x0) / max(1, len(text))
        pos = x0
        for p in parts:
            out.append((p, pos, y0, pos + per * len(p), y1))
            pos += per * (len(p) + 1)
    return out


def _amount(text: str) -> Decimal | None:
    m = re.search(r"\d[\d,]*\.\d{2}\b", text.replace("₹", ""))
    if not m:
        return None
    try:
        return Decimal(m.group(0).replace(",", ""))
    except InvalidOperation:
        return None


def _matches(field: str, value, text: str) -> bool:
    if value in (None, ""):
        return False
    if field in AMOUNTS:
        a = _amount(text)
        return a is not None and abs(a - Decimal(str(value))) < Decimal("0.005")
    if field == "invoice_date":
        return parse_date(text) == value
    return bool(normalize_invoice_no(text)) and normalize_invoice_no(text) == normalize_invoice_no(str(value))


def _read(field: str, text: str):
    if field in AMOUNTS:
        return _amount(text)
    if field == "invoice_date":
        return parse_date(text)
    t = text.strip(" .,:;")
    return t if re.search(r"\d", t) and len(t) <= 40 else None


def page_boxes(doc_path: Path, page_index: int):
    f = Path(str(doc_path) + ".ocr.json")
    try:
        return json.loads(f.read_text(encoding="utf-8"))[page_index]
    except (OSError, ValueError, IndexError):
        return None


def _ref(field: str, w) -> tuple[float, float]:
    """The point that stays put for a field: amounts are right-aligned, text fields left-aligned."""
    x = w[3] if field in AMOUNTS else w[1]
    return x, (w[2] + w[4]) / 2


def _letters(text: str) -> str:
    return re.sub(r"[^a-z]", "", str(text).lower())


LABELS = {"invoice_no": ("invoice", "bill", "inv"), "invoice_date": ("dated", "date"),
          "taxable_total": ("taxable", "value"), "cgst": ("cgst", "central"), "sgst": ("sgst", "state"),
          "igst": ("igst", "integrated"), "invoice_total": ("total", "grand")}


def _find_anchor(words, w):
    """The nearest label (a word with no digits) on the value's line to its left, or just above it."""
    best, best_d = None, 250.0
    cy, h = (w[2] + w[4]) / 2, max(4.0, w[4] - w[2])
    for a in words:
        if a is w or re.search(r"\d", a[0]) or len(_letters(a[0])) < 3:
            continue
        acy = (a[2] + a[4]) / 2
        if abs(acy - cy) < h * 0.6 and a[3] <= w[1] + 2:          # same line, to the left
            d = w[1] - a[3]
        elif a[4] <= w[2] + 2 and a[1] < w[3] and a[3] > w[1] - 30:  # above, overlapping or close
            d = w[2] - a[4]
            if d > 40:
                continue
        else:
            continue
        if 0 <= d < best_d:
            best, best_d = a, d
    return best


def _similar(a: str, b: str) -> bool:
    from difflib import SequenceMatcher
    a, b = _letters(a), _letters(b)
    return len(a) >= 3 and len(b) >= 3 and SequenceMatcher(None, a, b).ratio() >= 0.7


def learn(s, inv: Invoice, doc_path: Path | None) -> int:
    """Store the positions of this approved invoice's values. Returns how many fields were learned."""
    if not inv.supplier_gstin or doc_path is None:
        return 0
    boxes = page_boxes(doc_path, (inv.page_from or 1) - 1)
    if not boxes:
        return 0                                   # not a scan (text PDF) or OCR words not kept
    words = _words(boxes)
    learned = 0
    for field in FIELDS:
        value = getattr(inv, field)
        hits = [w for w in words if _matches(field, value, w[0])]
        if field == "invoice_date" and not hits:   # '21-Oct-26' may be one box, '21 Oct 2026' three words
            hits = [tuple(b) for b in boxes if _matches(field, value, str(b[0]))]
        if len(hits) > 1:                          # printed twice: take the one under / beside its label
            labelled = [h for h in hits if (a := _find_anchor(words, h)) is not None
                        and any(_similar(a[0], k) or _letters(a[0]).startswith(k) for k in LABELS[field])]
            hits = labelled
        if len(hits) != 1:
            continue                               # not found, or printed twice: nothing reliable to learn
        w = hits[0]
        _, x0, y0, x1, y1 = w
        rx, ry = _ref(field, w)
        anchor = _find_anchor(words, w)
        a_text, dx, dy = (anchor[0], rx - _ref(field, anchor)[0], ry - _ref(field, anchor)[1]) if anchor \
            else ("", 0.0, 0.0)
        row = s.scalar(select(SupplierLayout).where(SupplierLayout.company_id == inv.company_id,
                                                    SupplierLayout.supplier_gstin == inv.supplier_gstin,
                                                    SupplierLayout.field == field))
        if row is None:
            s.add(SupplierLayout(company_id=inv.company_id, supplier_gstin=inv.supplier_gstin, field=field,
                                 x0=x0, y0=y0, x1=x1, y1=y1, samples=1, anchor=a_text, dx=dx, dy=dy))
        elif abs((row.x1 if field in AMOUNTS else row.x0) - rx) > 60 or abs((row.y0 + row.y1) / 2 - ry) > 40:
            row.samples -= 1                       # this bill puts it elsewhere: the majority decides
            if row.samples <= 0:
                row.x0, row.y0, row.x1, row.y1, row.samples = x0, y0, x1, y1, 1
                row.anchor, row.dx, row.dy = a_text, dx, dy
        else:
            n = row.samples
            row.x0, row.y0 = (row.x0 * n + x0) / (n + 1), (row.y0 * n + y0) / (n + 1)
            row.x1, row.y1 = (row.x1 * n + x1) / (n + 1), (row.y1 * n + y1) / (n + 1)
            if a_text and row.anchor and _similar(a_text, row.anchor):
                row.dx, row.dy = (row.dx * n + dx) / (n + 1), (row.dy * n + dy) / (n + 1)
            elif a_text and not row.anchor:
                row.anchor, row.dx, row.dy = a_text, dx, dy
            row.samples = n + 1
        learned += 1
    return learned


TOL_X, TOL_Y, CLEAR = 14.0, 8.0, 4.0   # how far the value may be from where it is expected; margin to the next


def _expected(field: str, r: SupplierLayout, words) -> tuple[float, float]:
    """Where the value should be on this page: from its label when the label is found, else the average spot."""
    rx, ry = (r.x1 if field in AMOUNTS else r.x0), (r.y0 + r.y1) / 2
    if r.anchor:
        ax, ay = rx - r.dx, ry - r.dy                      # where the label was on the learned bills
        labels = [a for a in words if _similar(a[0], r.anchor)]
        labels = [(abs(_ref(field, a)[0] - ax) + abs(_ref(field, a)[1] - ay), a) for a in labels]
        labels = [la for la in labels if la[0] < 80]
        if labels:
            a = min(labels, key=lambda la: la[0])[1]
            lx, ly = _ref(field, a)
            return lx + r.dx, ly + r.dy
    return rx, ry


def _date_plausible(d, invoice_no) -> bool:
    """A date inside the financial year printed in the invoice number ('2359/26-27'), and not in the future
    nor years old."""
    import datetime as dt
    today = dt.date.today()
    if d > today + dt.timedelta(days=31) or d < today - dt.timedelta(days=730):
        return False
    m = re.search(r"(?<!\d)(\d{2})[-/](\d{2})(?!\d)", str(invoice_no or ""))
    if m and int(m.group(2)) == (int(m.group(1)) + 1) % 100:
        start = dt.date(2000 + int(m.group(1)), 4, 1)
        return start <= d < dt.date(start.year + 1, 4, 1)
    return True


def apply(s, company_id: int, parsed, boxes) -> list[str]:
    """Fill empty / unsure fields of a parsed scanned bill from the learned positions. Returns the fields
    filled."""
    gstin = parsed.fields.get("supplier_gstin")
    if not gstin or parsed.confidence.get("supplier_gstin", 0) < SURE or not boxes:
        return []
    layout = {r.field: r for r in s.scalars(select(SupplierLayout).where(
        SupplierLayout.company_id == company_id, SupplierLayout.supplier_gstin == gstin))}
    if not layout:
        return []
    words = _words(boxes)
    filled = []
    for field, r in layout.items():
        if field in parsed.fields and parsed.confidence.get(field, 0) >= SURE:
            continue                               # a confident reading stays
        ex, ey = _expected(field, r, words)
        cands = []
        for w in words:
            v = _read(field, w[0])
            if v is None:
                continue
            wx, wy = _ref(field, w)
            # scans of one supplier differ in scale by a few per cent: allow more the farther the label is
            if abs(wx - ex) <= TOL_X + 0.08 * abs(r.dx) and abs(wy - ey) <= TOL_Y + 0.08 * abs(r.dy):
                cands.append((abs(wx - ex) + abs(wy - ey), v))
        if not cands:
            continue
        cands.sort(key=lambda c: c[0])
        value = cands[0][1]
        if any(v != value and d < cands[0][0] + CLEAR for d, v in cands[1:]):
            continue                               # two different values about as close: do not guess
        if field in parsed.fields and parsed.fields[field] != value:
            parsed.confidence[field] = min(parsed.confidence.get(field, LOW), LOW)   # disagree: user checks
            continue
        # one or two approved bills can teach the wrong spot: until three agree, the user checks every fill
        conf = GUESS if r.samples >= 3 else LOW
        if field == "invoice_date" and not _date_plausible(value, parsed.fields.get("invoice_no")):
            conf = LOW
        parsed.put(field, value, conf)
        parsed.confidence[f"{field}_source"] = "learned position for this supplier"
        filled.append(field)
    # amounts filled this way must add up; otherwise they stay marked for checking
    if any(f in AMOUNTS for f in filled):
        f = parsed.fields
        tax = sum((f.get(k) or Decimal(0)) for k in ("cgst", "sgst", "igst"))
        if f.get("taxable_total") is None or f.get("invoice_total") is None or \
                abs(f["taxable_total"] + tax - f["invoice_total"]) > 1:
            for k in filled:
                if k in AMOUNTS:
                    parsed.confidence[k] = LOW
    return filled
