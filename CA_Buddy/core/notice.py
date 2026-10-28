"""Reading notices: text extraction (with OCR fallback) and a quick local
guess at what kind of notice it is."""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from .pdf_tools import ToolError, ocr_page_text, open_pdf, tesseract_available


def extract_text(path: Path, password: str = "", allow_ocr: bool = True,
                 ocr_lang: str = "eng") -> tuple[str, dict]:
    doc = open_pdf(path, password)
    pages, ocr_pages, unreadable = [], [], []
    has_tess = None
    for page in doc:
        txt = page.get_text("text", sort=True)
        if len(txt.strip()) < 40 and (page.get_images() or not txt.strip()):
            if allow_ocr:
                if has_tess is None:
                    has_tess = tesseract_available()
                if has_tess:
                    try:
                        txt = ocr_page_text(page, ocr_lang)
                        ocr_pages.append(page.number + 1)
                    except Exception:  # noqa: BLE001
                        unreadable.append(page.number + 1)
                else:
                    unreadable.append(page.number + 1)
        pages.append(txt)
    doc.close()
    text = "\n\n".join(f"[Page {i}]\n{t.strip()}" for i, t in enumerate(pages, 1) if t.strip())
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    meta = {"pages": len(pages), "ocr_pages": ocr_pages, "unreadable_pages": unreadable}
    if not text.strip():
        if unreadable and not has_tess:
            raise ToolError("This notice is a scanned image and has no text. Install Tesseract OCR "
                            "(see README) so the app can read scanned notices, then try again.")
        raise ToolError("No readable text was found in this PDF.")
    return text, meta


GST_FORMS = [
    ("ASMT-10", "Scrutiny of returns – discrepancies (Sec 61)"),
    ("ASMT-14", "Show cause before assessment (Sec 63)"),
    ("ADT-01", "Audit intimation (Sec 65)"),
    ("ADT-02", "Audit report (Sec 65)"),
    ("DRC-01A", "Pre-show-cause intimation (Rule 142(1A))"),
    ("DRC-01B", "Liability in GSTR-1 exceeds GSTR-3B (Rule 88C)"),
    ("DRC-01C", "ITC in GSTR-2B exceeds GSTR-3B (Rule 88D)"),
    ("DRC-01", "Show cause notice – summary (Sec 73/74/74A)"),
    ("DRC-07", "Summary of order / demand"),
    ("DRC-13", "Recovery – notice to third person"),
    ("REG-03", "Clarification on registration application"),
    ("REG-17", "Show cause for cancellation of registration"),
    ("REG-23", "Show cause against revocation"),
    ("RFD-08", "Show cause for rejection of refund"),
    ("MOV-07", "Notice in transit detention"),
    ("MOV-09", "Order of demand in transit"),
]

IT_SECTIONS = [
    (r"143\s*\(\s*1\s*\)(?:\s*\(a\))?", "Intimation / prima facie adjustment u/s 143(1)"),
    (r"143\s*\(\s*2\s*\)", "Scrutiny notice u/s 143(2)"),
    (r"142\s*\(\s*1\s*\)", "Inquiry before assessment u/s 142(1)"),
    (r"148A", "Reassessment – show cause u/s 148A"),
    (r"\b148\b", "Reassessment notice u/s 148"),
    (r"133\s*\(\s*6\s*\)", "Call for information u/s 133(6)"),
    (r"\b245\b", "Set-off of refund against demand u/s 245"),
    (r"270A", "Penalty for under-reporting u/s 270A"),
    (r"274", "Penalty show cause u/s 274"),
    (r"\b263\b", "Revision by Commissioner u/s 263"),
    (r"139\s*\(\s*9\s*\)", "Defective return u/s 139(9)"),
    (r"\b156\b", "Notice of demand u/s 156"),
    (r"\b154\b", "Rectification u/s 154"),
]


def classify(text: str) -> dict:
    head = text[:12000]
    gst_score = len(re.findall(r"\b(?:CGST|SGST|IGST|GSTIN|Goods\s+and\s+Services\s+Tax|GSTR-?\d)", head, re.I))
    it_score = len(re.findall(r"(?:Income[- ]tax\s+Act|Assessment\s+Year|Tax\s+Year|\bA\.?Y\.?\b|"
                              r"Faceless|\bITR\b|Assessing\s+Officer)", head, re.I))
    law = "GST" if gst_score > it_score else "Income Tax" if it_score else "Unknown"
    form, desc = None, None
    if law == "GST":
        for f, d in GST_FORMS:
            pat = f.replace("-", r"\s*-?\s*")
            if re.search(rf"\b(?:GST\s*)?{pat}\b", head, re.I):
                form, desc = "GST " + f, d
                break
        if not form:
            sec = re.search(r"[Ss]ection\s+(74A|74|73|61|65|66|67|122|129|130)\b", head)
            if sec:
                form, desc = f"Section {sec.group(1)}", "GST notice"
    elif law == "Income Tax":
        for pat, d in IT_SECTIONS:
            if re.search(rf"(?:[Ss]ection|u/s|U/S|sec\.?)\s*{pat}", head):
                form, desc = None, d
                break
    m = re.search(r"(?:within|not\s+later\s+than)\s+(\d{1,2})\s+days", head, re.I)
    return {"law": law, "form": form, "description": desc,
            "reply_window": f"{m.group(1)} days" if m else None}
