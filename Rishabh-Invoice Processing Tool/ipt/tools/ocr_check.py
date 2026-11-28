"""Read-only OCR check: runs the current extraction (both OCR passes) on a PDF/image and prints what
would be extracted per invoice. Writes nothing to the IPT database.

    python -m ipt.tools.ocr_check "path\\to\\file.pdf" [company GSTIN]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from ipt.services.extraction.pipeline import extract_group, fill_from_known
from ipt.services.extraction.sources import page_words, split_invoices

FIELDS = ("supplier_name", "supplier_gstin", "invoice_no", "invoice_date", "taxable_total", "cgst", "sgst",
          "igst", "round_off", "invoice_total")


def main() -> None:
    path = Path(sys.argv[1])
    gstin = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        import cv2
        print("OpenCV", cv2.__version__, "- full image cleaning + deskew")
    except ImportError:
        print("OpenCV not installed - simpler cleaning")
    t = time.monotonic()
    pages = page_words(path, "auto", progress=lambda p, n: print(f"  reading page {p + 1}/{n}", flush=True))
    groups = split_invoices(pages)
    res = [extract_group(path, pages, a, b, gstin) for a, b in groups]
    fill_from_known([r for r, _ in res], [t for _, t in res], {}, gstin)
    for n, ((a, b), (r, _)) in enumerate(zip(groups, res), 1):
        print(f"\n=== Invoice {n} (pages {a + 1}-{b + 1}) ===")
        for k in FIELDS:
            v = r.fields.get(k)
            c = r.confidence.get(k)
            flag = "" if v is None or (c or 0) >= 0.60 else "   <- CHECK"
            print(f"  {k:15} {'-' if v is None else v!s:30} {'' if c is None else round(c, 2)}{flag}")
        if r.fields.get("remarks"):
            print("  NOTE:", r.fields["remarks"])
        if r.confidence.get("supplier_gstin_source"):
            print("  GSTIN source:", r.confidence["supplier_gstin_source"])
        print(f"  items: {len(r.items)} (confidence {round(r.item_confidence or 0, 2)})")
        for it in r.items:
            print("   ", {k: str(it.get(k)) for k in ("description", "hsn_sac", "qty", "unit", "rate",
                                                       "taxable_value")})
    print(f"\nDone in {time.monotonic() - t:.0f} s")


if __name__ == "__main__":
    main()
