"""
Document extraction layer (Module 3 — Computer Vision & Text Extraction).
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict

import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image


@dataclass
class ExtractedDoc:
    filename: str
    doc_type: str  # "agreement", "invoice", or "revenue_schedule"
    raw_text: str
    extraction_method: str  # "pdf_text" or "ocr"

    invoice_no: Optional[str] = None
    invoice_date: Optional[str] = None
    provider_name: Optional[str] = None
    recipient_name: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    currency: Optional[str] = None
    amount: Optional[float] = None
    referenced_revenue: Optional[float] = None

    fee_percentage: Optional[float] = None

    # Revenue Support Schedule fields
    schedule_month: Optional[str] = None
    operating_revenue: Optional[float] = None
    extraordinary_income: Optional[float] = None
    total_revenue: Optional[float] = None

    low_confidence_fields: List[str] = field(default_factory=list)
    extraction_warnings: List[str] = field(default_factory=list)


def _is_image_file(path: str) -> bool:
    return path.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp"))


def _pdf_has_extractable_text(path: str) -> bool:
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                if page.extract_text() and len(page.extract_text().strip()) > 20:
                    return True
    except Exception:
        return False
    return False


def _extract_raw_text(path: str) -> tuple[str, str]:
    if _is_image_file(path):
        img = Image.open(path)
        text = pytesseract.image_to_string(img)
        return text, "ocr"

    if path.lower().endswith(".pdf"):
        if _pdf_has_extractable_text(path):
            text = ""
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
            return text, "pdf_text"
        else:
            images = convert_from_path(path, dpi=200)
            text = ""
            for img in images:
                text += pytesseract.image_to_string(img) + "\n"
            return text, "ocr"

    raise ValueError(f"Unsupported file type: {path}")


def _parse_indian_number(s: str) -> Optional[float]:
    try:
        cleaned = re.sub(r"[^\d.]", "", s.strip())
        return float(cleaned) if cleaned else None
    except (ValueError, AttributeError):
        return None


def _find(pattern: str, text: str, group: int = 1, flags=re.IGNORECASE) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(group).strip() if m else None


def extract_invoice_fields(doc: ExtractedDoc) -> ExtractedDoc:
    text = doc.raw_text

    doc.invoice_no = _find(r"Invoice\s*No[:\s]+([A-Za-z0-9\-\/]+)", text)
    doc.invoice_date = _find(r"Invoice\s*Date[:\s]+([\d]{1,2}\s+\w+\s+\d{4})", text)

    doc.provider_name = _find(r"From[:\s]+([^\n\r]+)", text)
    if not doc.provider_name:
        doc.extraction_warnings.append("Could not extract provider ('From') name from invoice.")
        doc.low_confidence_fields.append("provider_name")

    doc.recipient_name = _find(r"To[:\s]+([^\n\r]+)", text)
    if not doc.recipient_name:
        doc.extraction_warnings.append("Could not extract recipient ('To') name from invoice.")
        doc.low_confidence_fields.append("recipient_name")

    period_match = re.search(
        r"Period\s*Covered[:\s]+(\d{1,2}\s+\w+\s+\d{4})\s+to\s+(\d{1,2}\s+\w+\s+\d{4})",
        text, re.IGNORECASE
    )
    if period_match:
        doc.period_start = period_match.group(1)
        doc.period_end = period_match.group(2)
    else:
        doc.extraction_warnings.append("Could not locate period-covered dates.")
        doc.low_confidence_fields.append("period")

    # Match fee line: "Management services fee ... INR 6,000,000.00" or "Total Due INR ..."
    fee_line_match = re.search(
        r"(?:Management services fee|Total Due)[\s\S]*?(?:INR|USD|EUR|GBP)?\s*([A-Z]{3})?\s*([0-9,]+(?:\.[0-9]+)?)",
        text, re.IGNORECASE
    )
    
    # Currency extraction
    ccy_match = re.search(r"(?:Settlement Currency|Currency)[:\s]*([A-Z]{3})", text, re.IGNORECASE)
    if ccy_match:
        doc.currency = ccy_match.group(1).upper()
    elif fee_line_match and fee_line_match.group(1):
        doc.currency = fee_line_match.group(1).upper()
    else:
        found_ccy = re.search(r"\b(INR|USD|EUR|GBP)\b", text)
        doc.currency = found_ccy.group(1).upper() if found_ccy else None

    # Amount extraction
    amount_match = re.search(r"Total Due\s*\|\s*(?:[A-Z]{3})?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
    if amount_match:
        doc.amount = _parse_indian_number(amount_match.group(1))
    else:
        total_match = re.search(r"Total Due[:\s]*(?:[A-Z]{3})?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        if total_match:
            doc.amount = _parse_indian_number(total_match.group(1))
        elif fee_line_match and fee_line_match.group(2):
            doc.amount = _parse_indian_number(fee_line_match.group(2))
        else:
            doc.extraction_warnings.append("Could not confidently extract fee amount.")
            doc.low_confidence_fields.append("amount")

    # Flexible matching for any percentage (not hardcoded to 5%)
    revenue_match = re.search(
        r"\d+(?:\.\d+)?%\s*of\s*(Total\s+Operating\s+Revenue|Operating\s+Revenue|Total\s+Revenue)"
        r"[^\d]*?([0-9,]+(?:\.[0-9]+)?)",
        text, re.IGNORECASE
    )
    if revenue_match:
        doc.referenced_revenue = _parse_indian_number(revenue_match.group(2))
        basis_label = revenue_match.group(1).strip().lower()
        if basis_label == "total revenue":
            doc.extraction_warnings.append(
                "Invoice text references 'Total Revenue' as the fee basis rather than 'Operating "
                "Revenue' — non-operating income may be erroneously included."
            )
    else:
        doc.extraction_warnings.append("Could not extract referenced revenue basis.")
        doc.low_confidence_fields.append("referenced_revenue")

    if doc.extraction_method == "ocr":
        for f in ("amount", "referenced_revenue"):
            if f not in doc.low_confidence_fields:
                doc.low_confidence_fields.append(f + " (OCR-sourced, verify)")

    return doc


def extract_agreement_fields(doc: ExtractedDoc) -> ExtractedDoc:
    text = doc.raw_text

    # Match bulleted or unbulleted provider name ending in entity type
    provider_match = re.search(
        r"(?:•|\*|-)?\s*([A-Z][\w\s\.]*?(?:B\.V\.|Ltd\.?|LLC|Inc\.?|Pte Ltd|GmbH))",
        text, re.MULTILINE
    )
    if provider_match:
        doc.provider_name = provider_match.group(1).strip()
    else:
        doc.extraction_warnings.append("Could not extract Service Provider name from agreement.")
        doc.low_confidence_fields.append("provider_name")

    # Match recipient name
    recipient_match = re.search(
        r"(?:•|\*|-)?\s*([A-Z][\w\s]+(?:Private Limited|Limited|Pvt\.? Ltd\.?|LLP))",
        text, re.MULTILINE
    )
    if recipient_match:
        doc.recipient_name = recipient_match.group(1).strip()
    else:
        doc.extraction_warnings.append("Could not extract Company/recipient name from agreement.")
        doc.low_confidence_fields.append("recipient_name")

    # Capture fee percentage dynamically (e.g., 6%)
    fee_pct_match = re.search(
        r"(\d+(?:\.\d+)?)%\s*(?:\([\w\s]+\))?\s*of the Company['\u2019]s\s+Operating Revenue",
        text, re.IGNORECASE
    )
    if fee_pct_match:
        doc.fee_percentage = float(fee_pct_match.group(1))
    else:
        doc.extraction_warnings.append("Could not extract fee percentage formula from agreement.")
        doc.low_confidence_fields.append("fee_percentage")

    currency_match = re.search(r"denominated in\s+([\w\s]+?)\s*\(([A-Z]{3})\)", text, re.IGNORECASE)
    if currency_match:
        doc.currency = currency_match.group(2).upper()
    else:
        ccy_fallback = re.search(r"\b(INR|USD|EUR|GBP)\b", text)
        doc.currency = ccy_fallback.group(1).upper() if ccy_fallback else None

    term_match = re.search(
        r"commence on\s+(\d{1,2}\s+\w+\s+\d{4}).*?(?:until|ending)\s+(\d{1,2}\s+\w+\s+\d{4})",
        text, re.IGNORECASE | re.DOTALL
    )
    if term_match:
        doc.period_start = term_match.group(1)
        doc.period_end = term_match.group(2)

    return doc


def extract_revenue_schedule_fields(doc: ExtractedDoc) -> ExtractedDoc:
    text = doc.raw_text

    # Extract Month (matches dashes, en-dashes, or em-dashes)
    month_match = re.search(
        r"Revenue Support Schedule\s*[\u2013\-\—]\s*"
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{4})",
        text, re.IGNORECASE
    )
    if month_match:
        doc.schedule_month = f"{month_match.group(1).title()} {month_match.group(2)}"
    else:
        doc.extraction_warnings.append("Could not identify schedule month.")
        doc.low_confidence_fields.append("schedule_month")

    # Operating Revenue: matches any parenthetical explanation
    op_rev_match = re.search(
        r"Operating Revenue(?:\s*\([^)]*\))?\s*\|?\s*\|?\s*([0-9,]+(?:\.[0-9]+)?)",
        text, re.IGNORECASE
    )
    if op_rev_match:
        doc.operating_revenue = _parse_indian_number(op_rev_match.group(1))
    else:
        doc.extraction_warnings.append("Could not extract Operating Revenue.")
        doc.low_confidence_fields.append("operating_revenue")

    # Extraordinary Income
    extra_line_match = re.search(
        r"Extraordinary\s*/\s*Non-Operating Income([^\n\r]*)", text, re.IGNORECASE
    )
    if extra_line_match:
        line = extra_line_match.group(1)
        if "nil" in line.lower():
            doc.extraordinary_income = 0.0
        else:
            nums = re.findall(r"[0-9,]{4,}", line)
            doc.extraordinary_income = _parse_indian_number(nums[-1]) if nums else 0.0
    else:
        doc.extraordinary_income = 0.0

    # Total Revenue
    total_match = re.search(
        r"Total Revenue(?:\s*\([^)]*\))?\s*\|?\s*\|?\s*([0-9,]+(?:\.[0-9]+)?)",
        text, re.IGNORECASE
    )
    if total_match:
        doc.total_revenue = _parse_indian_number(total_match.group(1))
    elif doc.operating_revenue is not None and doc.extraordinary_income is not None:
        doc.total_revenue = doc.operating_revenue + doc.extraordinary_income

    if doc.extraction_method == "ocr":
        for f in ("operating_revenue", "extraordinary_income", "total_revenue"):
            doc.low_confidence_fields.append(f + " (OCR-sourced, verify)")

    return doc


def build_operating_revenue_table(revenue_schedule_docs: List[ExtractedDoc]) -> Dict[str, dict]:
    table: Dict[str, dict] = {}
    for d in revenue_schedule_docs:
        if not d.schedule_month:
            continue
        table[d.schedule_month] = {
            "operating_revenue": d.operating_revenue,
            "extraordinary_income": d.extraordinary_income,
            "total_revenue": d.total_revenue,
            "source_filename": d.filename,
        }
    return table


def process_document(path: str, doc_type: str) -> ExtractedDoc:
    raw_text, method = _extract_raw_text(path)
    doc = ExtractedDoc(
        filename=os.path.basename(path),
        doc_type=doc_type,
        raw_text=raw_text,
        extraction_method=method,
    )
    if doc_type == "invoice":
        doc = extract_invoice_fields(doc)
    elif doc_type == "agreement":
        doc = extract_agreement_fields(doc)
    elif doc_type == "revenue_schedule":
        doc = extract_revenue_schedule_fields(doc)
    else:
        raise ValueError(f"Unknown doc_type: {doc_type}")
    return doc