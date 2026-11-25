"""OCR system check — run this first if scanned notices come out blank.

    python scripts\\check_ocr.py              (checks Tesseract + Poppler, runs a tiny self-test)
    python scripts\\check_ocr.py some.pdf     (also extracts that PDF and reports every page)

It prints paths and versions only. It never prints .env values other than the two OCR paths.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import os  # noqa: E402

os.chdir(ROOT)  # so .env in the V3 folder is the one that is loaded
from noticemate.core import config  # noqa: E402,F401  (loads .env)
from noticemate.services.extraction import extract, ocr_health  # noqa: E402


def main() -> int:
    h = ocr_health()
    t, p, s = h["tesseract"], h["poppler"], h["self_test"]
    print("=" * 60)
    print(f"OCR STATUS: {h['status']}")
    print("=" * 60)
    print(f"Tesseract path : {t['configured_path']}")
    print(f"  found        : {'YES' if t['found'] else 'NO'}   version: {t['version'] or '-'}")
    print(f"  English data : {'YES' if t['eng_available'] else 'NO'}")
    if t["error"]:
        print(f"  PROBLEM      : {t['error']}")
    print(f"Poppler path   : {p['configured_path']}")
    print(f"  pdftoppm     : {'YES' if p['pdftoppm_found'] else 'NO'}   pdfinfo: {'YES' if p['pdfinfo_found'] else 'NO'}")
    if p["error"]:
        print(f"  PROBLEM      : {p['error']}")
    if s["ran"]:
        print(f"Self-test      : {'PASSED' if s['ok'] else 'FAILED'} (confidence {s['confidence']})")
    if h["fixes"]:
        print("\nWHAT TO DO:")
        for i, f in enumerate(h["fixes"], 1):
            print(f"  {i}. {f}")

    rc = 0 if h["status"] == "READY" else 1
    if len(sys.argv) > 1:
        f = Path(sys.argv[1])
        print(f"\nExtracting: {f.name}")
        ex = extract(f.suffix, f.read_bytes())
        print(f"Result: {ex.status}   pages: {ex.page_count}   characters: {len(ex.text.strip())}")
        for pg in ex.pages:
            conf = "-" if pg["confidence"] is None else f"{pg['confidence']:.0f}%"
            print(f"  page {pg['page']:>3}: {pg['method']:<4} {pg['status']:<15} chars={pg['chars']:<6} confidence={conf}")
        for n in ex.notes:
            print(f"  NOTE: {n}")
        if ex.status in ("FAILED", "PARTIAL"):
            rc = 2
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
