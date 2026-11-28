"""Extraction pipeline for one document.

Automatic mode: PDF text layer first; pages without text (scans) and images go to
Tesseract OCR. If nothing usable is read, the document is marked failed with the
reason. Cloud AI extraction is not part of this build (no document leaves the PC).
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from ipt.db.models import Company, Document, ExtractionResult
from ipt.services.extraction.layout import group_lines
from ipt.services.extraction.parser import LOW, fill_known_gstin, invoice_no_anchors, parse
from ipt.services.extraction.sources import (OcrUnavailable, group_warnings, page_words, read_below_label,
                                              second_pass_words, split_invoices)

log = logging.getLogger(__name__)
MODES = {"auto": "Automatic (text, then OCR)", "text": "Digital PDF text only", "ocr": "OCR only"}
CORE_FIELDS = ("invoice_no", "invoice_date", "invoice_total")
# a scanned invoice missing any of these gets a second OCR pass; it only fills fields still empty
TOTAL_KEYS = ("taxable_total", "cgst", "sgst", "igst", "cess", "round_off", "invoice_total")
SECOND_PASS_FIELDS = ("invoice_no", "invoice_date", "supplier_gstin", "taxable_total", "invoice_total")


@dataclass
class Outcome:
    document_id: int
    ok: bool
    invoice_id: int | None = None
    method: str = ""
    message: str = ""


def _fill_missing(first, second) -> None:
    """Take from the second OCR pass only fields the first pass could not read (never replaces)."""
    for k, v in second.fields.items():
        if k not in first.fields:
            first.fields[k] = v
            first.confidence[k] = second.confidence.get(k, 0.55)
    if not first.items and second.items:
        first.items, first.item_confidence = second.items, second.item_confidence


def extract_group(path, pages, first: int, last: int, company_gstin: str | None, progress=None):
    """Parse one invoice (pages first..last): first pass, then for scans a second OCR pass and a
    zoomed re-read of the invoice number, each only filling what is still missing."""
    words = []
    for pno in range(first, last + 1):
        for w in pages[pno][0]:
            w.page = pno
            words.append(w)
    lines = group_lines(words)
    text = "\n".join(ln.text for ln in lines)
    from_ocr = any(pages[p][1] == "ocr" for p in range(first, last + 1))
    parsed = parse(lines, from_ocr=from_ocr, company_gstin=company_gstin)
    if from_ocr and any(k not in parsed.fields for k in SECOND_PASS_FIELDS):
        if progress:
            progress(f"Second OCR pass, page {first + 1}")
        words2 = []
        try:
            for pno in range(first, last + 1):
                if pages[pno][1] == "ocr":
                    for w in second_pass_words(path, pno):
                        w.page = pno
                        words2.append(w)
        except OcrUnavailable:
            words2 = []          # second pass needs Tesseract; without it the first pass stands
        lines2 = group_lines(words2)
        _fill_missing(parsed, parse(lines2, from_ocr=True, company_gstin=company_gstin))
        text += "\n----- second OCR pass -----\n" + "\n".join(ln.text for ln in lines2)
    if from_ocr and "invoice_no" not in parsed.fields:
        if progress:
            progress(f"Zoomed read of the invoice number, page {first + 1}")
        for pno, x0, bottom in invoice_no_anchors(lines):
            if pages[pno][1] != "ocr":
                continue
            try:
                val = read_below_label(path, pno, x0, bottom)
            except OcrUnavailable:
                break
            if val:
                parsed.put("invoice_no", val, LOW)     # read from a zoomed box: please verify
                text += f"\n----- zoomed read of invoice no: {val} -----"
                break
    warn = group_warnings(pages, first, last)
    if warn:
        # a page of a multi-page invoice is missing here: every amount may be partial - never trust it
        for k in TOTAL_KEYS:
            if k in parsed.confidence:
                parsed.confidence[k] = min(parsed.confidence[k], LOW)
        parsed.fields["remarks"] = warn
        text += f"\n----- {warn} -----"
    return parsed, text


def words_file(path: Path) -> Path:
    return Path(str(path) + ".ocr.json")


def save_words(path: Path, pages) -> None:
    """Keep the OCR words (595-pt-wide page coordinates) next to the stored document. Best effort."""
    import json
    try:
        words_file(path).write_text(json.dumps([[[str(w.text), round(float(w.x0), 1), round(float(w.y0), 1),
                                                  round(float(w.x1), 1), round(float(w.y1), 1)] for w in ws]
                                                for ws, _ in pages]), encoding="utf-8")
    except (OSError, TypeError, ValueError):
        pass


def fill_from_known(parsed_list, texts, known: dict[str, str], company_gstin: str | None) -> None:
    """Supplier GSTINs OCR could not read: match against known suppliers plus the GSTINs read cleanly from
    the other bills in the same file (a batch of one supplier's bills is common)."""
    from ipt.core.gstin import validate_gstin
    pool: dict[str, set] = {g: {n} for g, n in known.items()}
    for p in parsed_list:
        g = p.fields.get("supplier_gstin")
        if g and p.confidence.get("supplier_gstin", 0) >= 0.6 and validate_gstin(g).valid:
            pool.setdefault(g, set()).add(p.fields.get("supplier_name") or "")
    for p, t in zip(parsed_list, texts):
        fill_known_gstin(t, p, pool, company_gstin)


class ExtractionPipeline:
    def __init__(self, services):
        self.s = services  # ui.services.Services (uses db, documents, invoices)

    def run(self, document_id: int, mode: str = "auto", progress=None) -> Outcome:
        """progress(message) is called as pages are read (for the UI status line)."""
        docs, invoices = self.s.documents, self.s.invoices
        doc: Document | None = docs.get(document_id)
        if doc is None:
            return Outcome(document_id, False, message="Document not found")
        done = invoices.pages_with_invoices(document_id) if invoices.invoice_for_document(document_id) else set()
        if done is None:
            return Outcome(document_id, False, message="Already extracted. Delete the invoice to extract again.")
        docs.set_status(document_id, "processing")
        start = time.monotonic()
        path = docs.absolute_path(doc)
        method, raw_text = "", ""
        try:
            pages = page_words(path, mode, progress=(lambda p, n: progress(f"Reading page {p + 1} of {n}"))
                               if progress else None)
            methods = {m for _, m in pages}
            method = "ocr" if "ocr" in methods else "pdf_text"
            if method == "ocr":
                save_words(path, pages)       # the review screen picks clicked values from this same reading
            with self.s.db.session() as ss:
                company = ss.get(Company, doc.company_id)
                company_gstin = company.gstin if company else None
            created, statuses = [], []
            groups = split_invoices(pages)
            todo = [(a, b) for a, b in groups if a + 1 not in done]
            if not todo:
                docs.set_status(document_id, "extracted", method)
                return Outcome(document_id, False, message="Every invoice in this file is already extracted.")
            results = [(first, last, *extract_group(path, pages, first, last, company_gstin, progress))
                       for first, last in todo]
            known = invoices.known_gstins(doc.company_id)
            fill_from_known([r[2] for r in results], [r[3] for r in results], known, company_gstin)
            if method == "ocr":
                from ipt.services.extraction import layouts
                with self.s.db.session() as ss:
                    for first, _last, parsed, _text in results:
                        boxes = [[w.text, w.x0, w.y0, w.x1, w.y1] for w in pages[first][0]]
                        layouts.apply(ss, doc.company_id, parsed, boxes)
            for first, last, parsed, text in results:
                raw_text += f"\n===== page {first + 1}-{last + 1} =====\n" + text
                if not any(k in parsed.fields for k in CORE_FIELDS) and not parsed.items and len(groups) == 1:
                    raise ValueError("No invoice details could be read from this document")
                iid = invoices.create_from_extraction(document_id, parsed.fields, parsed.confidence, parsed.items,
                                                      parsed.item_confidence, pages=(first + 1, last + 1))
                created.append(iid)
                statuses.append(invoices.get(iid).status)
                self._history(document_id, method, text, parsed.fields, parsed.confidence, start, "")
            docs.set_status(document_id, "needs_review" if "needs_review" in statuses else "extracted", method)
            msg = statuses[0] if len(created) == 1 else f"{len(created)} invoices found in this file"
            return Outcome(document_id, True, created[0], method, msg)
        except OcrUnavailable as e:
            msg = str(e)
        except Exception as e:  # noqa: BLE001 - every failure is shown to the user per file
            log.exception("Extraction failed for document %s", document_id)
            msg = str(e) or e.__class__.__name__
        self._history(document_id, method or mode, raw_text, {}, {}, start, msg)
        docs.set_status(document_id, "failed", method, msg)
        return Outcome(document_id, False, None, method, msg)

    def _history(self, document_id, method, raw_text, fields, conf, start, error):
        with self.s.db.session() as ss:
            ss.add(ExtractionResult(document_id=document_id, method=method, raw_text=raw_text[:200000],
                                    fields_json=json.dumps(fields, default=str), confidence_json=json.dumps(conf),
                                    duration_ms=int((time.monotonic() - start) * 1000), error=error))
