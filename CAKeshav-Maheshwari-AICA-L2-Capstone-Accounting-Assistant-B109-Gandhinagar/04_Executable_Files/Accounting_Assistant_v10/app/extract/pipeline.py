"""Gemini-first extraction.

  1. Read the file: text layer (PDF/Word/Excel) and page images (scans, or PDFs rendered by Windows).
  2. OCR the first page image: gives text for scans and word boxes for redaction.
  3. Local parse of the text (offline result + cross-check).
  4. Gemini reads the redacted image(s) + masked text, with the buying company as a hint; if its answer fails
     the GST arithmetic it is asked once to re-check.
  0. Supplier layout memory: if this supplier's layout has been learned and the offline reading through it passes
     every check, Gemini is skipped entirely (fully offline).
  5. The better-validated result wins; fields where Gemini and the local reading agree get top confidence,
     disagreements are shown to the reviewer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import copy
import re

from . import gemini, layout as layout_mod, ocr as ocr_mod, qr as qr_mod, readers
from .parser import hsn_codes, parse
from .redact import mask_text, redact_image
from .schema import Invoice
from .validator import Issue, Validation, validate

COMPARE = [("supplier_gstin", "Supplier GSTIN"), ("invoice_no", "Invoice no"), ("invoice_date", "Date"),
           ("taxable_total", "Taxable value"), ("grand_total", "Invoice total")]


@dataclass
class ExtractOptions:
    company_gstin: str = ""
    company_state: str = ""
    company_name: str = ""
    gemini_key: str = ""
    gemini_model: str = "auto"
    gemini_threshold: float = 0.8          # unused in Gemini-first mode (kept for settings compatibility)
    allow_unredacted_image: bool = False
    use_gemini: bool = True
    layouts: dict = field(default_factory=dict)      # vendor_key -> learned layout fields (offline reading)


@dataclass
class ExtractResult:
    invoice: Invoice
    validation: Validation
    doc: readers.Document
    trail: list[str] = field(default_factory=list)
    ocr_engine: str = ""
    local: Invoice | None = None


def _merge_qr(inv: Invoice, q: Invoice | None) -> Invoice:
    if not q:
        return inv
    for f in ("supplier_gstin", "buyer_gstin", "invoice_no", "invoice_date", "irn"):
        if getattr(q, f):
            setattr(inv, f, getattr(q, f))
            inv.field_confidence[f] = 0.99
    if q.grand_total and abs(q.grand_total - inv.grand_total) > 1:
        inv.grand_total = q.grand_total
        inv.field_confidence["grand_total"] = 0.99
    if inv.supplier_gstin:
        inv.supplier_pan = inv.supplier_gstin[2:12]
    return inv


def _errors_for_retry(inv: Invoice, opt: ExtractOptions, today) -> list[str]:
    v = validate(inv, opt.company_gstin, opt.company_state, today)
    return [i.message for i in v.issues if i.level == "error" and i.field not in ("invoice_date",)]


def local_vendor_key(inv: Invoice) -> str:
    """Same key as the rules engine: GSTIN, else PAN, else normalised name."""
    if inv.supplier_gstin:
        return inv.supplier_gstin
    if inv.supplier_pan:
        return f"PAN:{inv.supplier_pan}"
    n = re.sub(r"[^a-z0-9]", "", (inv.supplier_name or "").lower())[:60]
    return f"NAME:{n}" if n else ""


def process(path: Path, opt: ExtractOptions, today: date | None = None) -> ExtractResult:
    trail: list[str] = []
    path = Path(path)
    doc = readers.read(path)
    trail.append(f"Read {doc.kind}, {doc.pages} page(s), text layer: {'yes' if doc.has_text_layer else 'no'}")

    # page images: scans already have them; text PDFs are rendered so Gemini can see the layout
    if doc.kind == "pdf" and not doc.page_images:
        doc.page_images = readers.render_pdf(path)[:3] if doc.has_text_layer else doc.page_images
    if doc.page_images:
        trail.append(f"{len(doc.page_images)} page image(s) available")

    # e-invoice QR (optional decoders)
    qr_inv = None
    for img in doc.page_images[:2]:
        for token in qr_mod.decode_qr(img):
            payload = qr_mod.jwt_payload(token)
            if payload and payload.get("SellerGstin"):
                qr_inv = qr_mod.invoice_from_qr(payload)
                trail.append("E-invoice QR decoded (signature not verified)")
                break
        if qr_inv:
            break

    # OCR: text for scans + word boxes for redaction of every page image we may send
    words_by_page, ocr_engine, text = {}, "", doc.text
    ocr_texts = []
    for i, img in enumerate(doc.page_images[:3]):
        r = ocr_mod.ocr(img)
        if r.text:
            ocr_engine = r.engine
            words_by_page[i] = (r.words, ocr_mod.ocr_width(img))
            ocr_texts.append(r.text)
        elif r.error:
            trail.append(f"OCR page {i + 1}: {r.error[:160]}")
    if not doc.has_text_layer:
        text = "\n\f\n".join(ocr_texts)
    if ocr_engine:
        trail.append(f"OCR ({ocr_engine}) on {len(words_by_page)} page(s)")

    # local reading (offline result and cross-check)
    local = parse(text, opt.company_gstin)
    local.source = {"pdf": "text", "docx": "docx", "xlsx": "xlsx"}.get(doc.kind, "ocr") if doc.has_text_layer \
        else "ocr"
    local.hsn_codes = hsn_codes(text)
    local = _merge_qr(local, qr_inv)
    lval = validate(local, opt.company_gstin, opt.company_state, today)
    trail.append(f"Local reading: {lval.status}, confidence {lval.confidence:.2f}")
    inv, val = local, lval

    # Supplier layout memory: read offline when this supplier is known and the result passes every check
    vk = local_vendor_key(local)
    if opt.layouts and vk not in opt.layouts:        # supplier GSTIN printed but not picked up by the parser
        for g in re.findall(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z]\b", text.upper()):
            if g in opt.layouts and g != opt.company_gstin:
                vk = g
                local.supplier_gstin = local.supplier_gstin or g
                local.supplier_pan = local.supplier_pan or g[2:12]
                break
    if vk and vk in opt.layouts and text.strip():
        lay_inv, got = layout_mod.apply(copy.deepcopy(local), opt.layouts[vk], text)
        lay_inv.source = "layout"
        layval = validate(lay_inv, opt.company_gstin, opt.company_state, today)
        if got and not layval.errors and lay_inv.grand_total:
            trail.append(f"Read offline with this supplier's learned layout ({len(got)} field(s)): "
                         f"{layval.status}, confidence {layval.confidence:.2f}. Gemini not needed.")
            lay_inv.raw_text = text
            return ExtractResult(lay_inv, layval, doc, trail, ocr_engine, local)
        trail.append(f"Learned layout tried: {len(layval.errors)} check(s) failed, falling back")

    # Gemini-first
    if opt.use_gemini and opt.gemini_key:
        masked, n_red = mask_text(text) if text.strip() else ("", 0)
        images = []
        for i, img in enumerate(doc.page_images[:3]):
            if i in words_by_page:
                red, n = redact_image(img, *words_by_page[i])
                images.append(red)
                n_red += n
            elif opt.allow_unredacted_image:
                images.append(img)
                trail.append(f"WARNING: page {i + 1} sent without redaction (no OCR boxes)")
        if not images and doc.page_images:
            trail.append("Page images not sent: no OCR boxes to redact against (text only)")
        if masked or images:
            try:
                g = gemini.extract(opt.gemini_key, opt.gemini_model, text=masked, images=images,
                                   file_name=path.name, redactions=n_red, buyer_name=opt.company_name,
                                   buyer_gstin=opt.company_gstin,
                                   check=lambda x: _errors_for_retry(x, opt, today))
                g.hsn_codes = g.hsn_codes or local.hsn_codes
                g.raw_text = text
                g = _merge_qr(g, qr_inv)
                gval = validate(g, opt.company_gstin, opt.company_state, today)
                trail.append(f"Gemini ({g.model}, {len(images)} image(s), {n_red} item(s) redacted): {gval.status}, "
                             f"confidence {gval.confidence:.2f}" + (f". Note: {g.notes}" if g.notes else ""))
                if len(gval.errors) <= len(lval.errors):
                    disagreements = []
                    for f, label in COMPARE:
                        a, b = getattr(g, f), getattr(local, f)
                        if a and b and a == b:
                            g.field_confidence[f] = 0.98
                        elif a and b and local.field_confidence.get(f, 0) >= 0.85:
                            g.field_confidence[f] = 0.7
                            shown = lambda v: (f"{v[6:8]}-{v[4:6]}-{v[:4]}" if f == "invoice_date" else v)
                            disagreements.append(Issue("warn", f, f"{label}: Gemini read {shown(a)}, the text "
                                                                  f"layer says {shown(b)} - check the document"))
                    inv = g
                    val = validate(g, opt.company_gstin, opt.company_state, today)
                    val.issues += disagreements
                    if disagreements and val.status == "green":
                        val.status = "amber"
                else:
                    trail.append("Kept the local reading: it passes more checks than Gemini's")
            except gemini.GeminiError as e:
                trail.append(f"Gemini failed: {e}")
    elif opt.use_gemini:
        trail.append("Gemini not used: no API key in Settings")
    inv.raw_text = text
    return ExtractResult(inv, val, doc, trail, ocr_engine, local)
