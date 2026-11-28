"""Builds synthetic invoice PDFs for tests only (never used by the app)."""
from __future__ import annotations

from pathlib import Path

import pymupdf

from ipt.core.gstin import check_char


def gst(prefix14: str) -> str:
    return prefix14 + check_char(prefix14)


def make_invoice(path: Path, *, title="TAX INVOICE", supplier="Shree Ganesh Traders", supplier_gstin,
                 buyer="ABC Enterprises", buyer_gstin, inv_no="SGT/25-26/0147", inv_date="15-10-2025",
                 pos="08 - Rajasthan", items, totals, extra_lines=()) -> Path:
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    t = lambda x, y, s, size=9: p.insert_text((x, y), s, fontsize=size)  # noqa: E731
    t(40, 50, supplier, 14)
    t(380, 50, title, 12)
    t(40, 66, "12, Industrial Area, Jaipur")
    t(380, 66, f"Invoice No: {inv_no}")
    t(40, 80, f"GSTIN: {supplier_gstin}")
    t(380, 80, f"Invoice Date: {inv_date}")
    t(380, 94, f"Place of Supply: {pos}")
    t(380, 108, "Reverse Charge: No")
    for i, line in enumerate(extra_lines):
        t(380, 122 + 14 * i, line)
    t(40, 130, "Bill To:")
    t(40, 144, buyer)
    t(40, 158, f"GSTIN: {buyer_gstin}")
    cols = [(40, "S.No"), (75, "Description"), (230, "HSN"), (280, "Qty"), (320, "Rate"), (375, "Taxable Value"),
            (450, "GST %"), (500, "Total")]
    for x, h in cols:
        t(x, 200, h)
    y = 220
    for n, it in enumerate(items, 1):
        vals = [str(n), it[0], it[1], it[2], it[3], it[4], it[5], it[6]]
        for (x, _), v in zip(cols, vals):
            t(x, y, v)
        y += 16
    y += 20
    for label, value in totals:
        t(330, y, label)
        t(470, y, value)
        y += 14
    t(40, y + 10, "Amount in Words: Rupees as above Only")
    doc.save(path)
    return path
