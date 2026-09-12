"""
PDF invoice extraction logic.

Given the huge variety of invoice layouts, this module uses a set of
heuristics rather than a rigid template:

  * Tables are located by scanning for a header cell containing "HSN" or
    "SAC". A lot of invoices split the header across two physical rows
    (e.g. "CGST" on one row, "% / Amount" on the next) so the row right
    after the header is merged in when it looks like a sub-header.
  * The vendor's GSTIN / name is assumed to appear before the first
    "Customer" / "Bill To" / "Buyer" label on the page - this matches the
    common convention of vendor details in the letterhead and customer
    details in a box below it.
  * If no table can be parsed (scanned image, unusual layout, etc.) a
    best-effort text scan is used instead, and the row is flagged in the
    Extraction Notes column so it can be manually reviewed.
  * Scanned invoices (a photo/scan saved as PDF, with no embedded text
    layer) are detected per-page and run through Tesseract OCR to recover
    text, which then goes through the same text-fallback scan above.
  * Some scanner software produces PDFs with a page structure that
    pdfplumber (via pdfminer.six) fails to parse at all - it reports 0
    pages even though the file opens fine elsewhere. For those, pages are
    rendered directly with pypdfium2 (the lower-level engine pdfplumber
    itself uses for images) and OCR'd the same way.
  * Customs Bill of Entry copies (a different document type entirely - no
    "Customer"/GST table, a CTH code instead of HSN/SAC, duty assessed at
    document level rather than per line) are detected separately and go
    through a dedicated parser instead of the tax-invoice heuristics above.
"""

import os
import re
import shutil

import pdfplumber
import pypdfium2 as pdfium
import pytesseract
from PIL import Image  # noqa: F401  (ensures a clear error if Pillow is missing)

_DEFAULT_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

if os.environ.get("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]
elif not shutil.which(pytesseract.pytesseract.tesseract_cmd):
    for candidate in _DEFAULT_TESSERACT_PATHS:
        if os.path.isfile(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            break

# Pages with less native text than this are treated as scanned/image-only
# and sent through OCR instead.
MIN_NATIVE_TEXT_CHARS = 20
OCR_RESOLUTION = 300

GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b")

INVOICE_NO_RE = re.compile(
    r"invoice\s*(?:no\.?|number|#)\s*[:\-]?\s*(.+)", re.IGNORECASE
)

CUSTOMER_LABELS = ["customer", "bill to", "buyer", "consignee", "ship to"]

COMPANY_SUFFIX_RE = re.compile(
    r"\b(pvt\.?\s*ltd\.?|private\s+limited|llp|ltd\.?|limited|inc\.?|"
    r"corporation|corp\.?|enterprises|industries)\b",
    re.IGNORECASE,
)

DOC_TITLE_SKIP_WORDS = [
    "invoice", "tax invoice", "reimbursement", "bill of", "receipt",
    "statement", "credit note", "debit note",
]

SUBHEADER_TOKENS = ["%", "tax", "amt", "amount", "value", "rate"]

CODE_LENGTHS = (4, 6, 8)

# Date-shaped tokens (dd-Mon-yyyy, dd-mm-yyyy, yyyy-mm-dd, yyyy.mm.dd) are
# stripped before the line-item text fallback runs, since OCR text is a wall
# of unrelated dates/reference numbers that otherwise get misread as HSN/SAC
# codes (e.g. "2025" from "11-Jul-2025", or its "2025.07.29" signature-date
# form getting misread as a currency amount).
DATE_TOKEN_RE = re.compile(
    r"\b\d{1,2}[-/](?:\d{1,2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
    r"[-/]\d{2,4}\b",
    re.IGNORECASE,
)
ISO_DATE_RE = re.compile(r"\b\d{4}[-.]\d{2}[-.]\d{2}\b")

# Bill of Entry (customs import document) detection and field patterns.
BOE_MARKER_RE = re.compile(r"bill\s+of\s+entry", re.IGNORECASE)
CTH_MARKER_RE = re.compile(r"\bCTH\b", re.IGNORECASE)
BE_NO_DATE_RE = re.compile(r"\b(\d{6,8})\s+(\d{2}[/-]\d{2}[/-]\d{4})\b")
EXCHANGE_RATE_RE = re.compile(r"1\s*USD\s*=\s*([\d.]+)\s*INR", re.IGNORECASE)
IMPORTER_LABEL_RE = re.compile(r"IMPORTER\s*NAME", re.IGNORECASE)
SUPPLIER_LABEL_RE = re.compile(r"SUPPLIER\s*NAME", re.IGNORECASE)
SELLER_LABEL_RE = re.compile(r"SELLER'?S?\s*NAME", re.IGNORECASE)
# A CTH item line: row no., 8-digit CTH code, description, then unit price /
# quantity / unit-of-measure / amount - e.g.
# "1 38221990 AOCS 1011-A2, MON ... 280.000000 1.000000 NOS 280.00"
CTH_ITEM_LINE_RE = re.compile(
    r"\b(\d{8})\b.*?(\d+\.\d{4,6})\s+(\d+\.\d{4,6})\s+[A-Za-z]{2,4}"
    r"\s*[|©_~—\-]*\s*([\d,]+\.\d{2})\)?\s*$"
)

# GSTIN check-digit alphabet (base-36: digits then letters).
GSTIN_CHECK_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# ---------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------

def parse_number(cell):
    """Best-effort parse of a table cell into a float, or None."""
    if cell is None:
        return None
    s = str(cell).replace("\n", " ").strip()
    if s == "" or s in ("-", "--", "—", "–", "NIL", "Nil", "nil"):
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    s = re.sub(r"[^\d.\-]", "", s)
    if s in ("", "-", "."):
        return None
    try:
        val = float(s)
    except ValueError:
        return None
    return -val if neg else val


def clean_header_cell(cell):
    return (cell or "").replace("\n", " ").strip().lower()


def clean_code(cell):
    """Return a plausible HSN/SAC code string from a cell, or None."""
    if cell is None:
        return None
    s = str(cell).replace("\n", " ").strip()
    if s == "":
        return None
    if not re.fullmatch(r"[\d\s]+", s):
        return None
    digits = re.sub(r"\s", "", s)
    if len(digits) in CODE_LENGTHS:
        return digits
    return None


def get_cell(row, idx):
    if idx is None or idx >= len(row):
        return None
    return row[idx]


def is_valid_gstin(gstin):
    """Best-effort GSTIN check-digit validation (used only as a confidence
    signal, never to reject data - OCR misreads are common enough that a
    "invalid" result just means "double check this one", not "discard it").
    """
    if not gstin or not GSTIN_RE.fullmatch(gstin):
        return False
    total = 0
    for i, ch in enumerate(gstin[:14]):
        if ch not in GSTIN_CHECK_CHARS:
            return False
        value = GSTIN_CHECK_CHARS.index(ch)
        factor = 1 if i % 2 == 0 else 2
        product = value * factor
        product = (product // 36) + (product % 36)
        total += product
    checksum_char = GSTIN_CHECK_CHARS[(36 - (total % 36)) % 36]
    return checksum_char == gstin[14]


# ---------------------------------------------------------------------
# Invoice-level fields: invoice number, vendor name, vendor GSTIN
# ---------------------------------------------------------------------

def find_invoice_number(text):
    for line in text.split("\n"):
        m = INVOICE_NO_RE.search(line)
        if not m:
            continue
        value = m.group(1).strip()
        # Cut off if another field got appended on the same line
        # (PDF text extraction often collapses column gaps to big spaces).
        value = re.split(r"\s{2,}|\t", value)[0]
        value = value.strip(" :\t-")
        if value:
            return value
    return None


def find_customer_offset(text):
    lower = text.lower()
    positions = [lower.find(lbl) for lbl in CUSTOMER_LABELS]
    positions = [p for p in positions if p != -1]
    return min(positions) if positions else None


def find_gstins_with_pos(text):
    return [(m.group(), m.start()) for m in GSTIN_RE.finditer(text)]


def find_vendor_gstin(text, cust_offset):
    gstins = find_gstins_with_pos(text)
    if not gstins:
        return None
    if cust_offset is not None:
        before = [g for g, pos in gstins if pos < cust_offset]
        if before:
            return before[0]
    return gstins[0][0]


def find_vendor_name(text, cust_offset):
    lines = text.split("\n")
    offset = 0
    candidates = []
    for line in lines:
        line_start = offset
        offset += len(line) + 1
        if cust_offset is not None and line_start >= cust_offset:
            break
        if COMPANY_SUFFIX_RE.search(line):
            candidates.append(line.strip())
    if candidates:
        return candidates[0]
    for line in lines:
        l = line.strip()
        if not l:
            continue
        if any(w in l.lower() for w in DOC_TITLE_SKIP_WORDS):
            continue
        return l
    return None


# ---------------------------------------------------------------------
# Table parsing: HSN/SAC, taxable value, tax
# ---------------------------------------------------------------------

def is_subheader_row(row):
    non_empty = [c for c in row if c and str(c).strip()]
    if not non_empty:
        return False
    match_count = sum(
        1 for c in row if c and any(t in clean_header_cell(c) for t in SUBHEADER_TOKENS)
    )
    return match_count >= max(1, len(non_empty) // 2)


def find_column_map(header_row):
    mapping = {}
    for i, cell in enumerate(header_row):
        h = clean_header_cell(cell)
        if not h:
            continue
        if "hsn" in h or "sac" in h:
            mapping.setdefault("hsn", i)
        elif "taxable" in h:
            mapping.setdefault("taxable", i)
        elif "assessable" in h:
            mapping.setdefault("assessable", i)
        elif "non gst" in h or "non-gst" in h or "exempt" in h:
            mapping.setdefault("non_gst", i)
        elif "cgst" in h and "%" not in h:
            mapping.setdefault("cgst", i)
        elif "sgst" in h and "%" not in h:
            mapping.setdefault("sgst", i)
        elif "igst" in h and "%" not in h:
            mapping.setdefault("igst", i)
        elif "utgst" in h and "%" not in h:
            mapping.setdefault("utgst", i)
        elif ("gst" in h or "tax" in h) and "%" not in h:
            mapping.setdefault("tax_generic", i)
        elif "total" in h:
            mapping.setdefault("total", i)
    return mapping


def extract_rows_from_table(table):
    if not table:
        return None

    header_idx = None
    for i, row in enumerate(table):
        joined = " ".join(clean_header_cell(c) for c in row)
        if "hsn" in joined or "sac" in joined:
            header_idx = i
            break
    if header_idx is None:
        return None

    header_row = list(table[header_idx])
    data_start = header_idx + 1

    if data_start < len(table) and is_subheader_row(table[data_start]):
        sub = table[data_start]
        merged = []
        for i, c in enumerate(header_row):
            extra = sub[i] if i < len(sub) else ""
            merged.append(f"{c or ''} {extra or ''}")
        header_row = merged
        data_start += 1

    colmap = find_column_map(header_row)
    if "hsn" not in colmap:
        return None

    items = []
    for row in table[data_start:]:
        code = clean_code(get_cell(row, colmap.get("hsn")))
        if not code:
            continue

        taxable = None
        for key in ("taxable", "assessable", "non_gst", "total"):
            if key in colmap:
                val = parse_number(get_cell(row, colmap[key]))
                if val:
                    taxable = val
                    break

        cgst_val = parse_number(get_cell(row, colmap["cgst"])) if "cgst" in colmap else None
        sgst_val = parse_number(get_cell(row, colmap["sgst"])) if "sgst" in colmap else None
        igst_val = parse_number(get_cell(row, colmap["igst"])) if "igst" in colmap else None
        utgst_val = parse_number(get_cell(row, colmap["utgst"])) if "utgst" in colmap else None

        tax_total = 0.0
        tax_found = False
        for val in (cgst_val, sgst_val, igst_val, utgst_val):
            if val is not None:
                tax_total += val
                tax_found = True
        if not tax_found and "tax_generic" in colmap:
            val = parse_number(get_cell(row, colmap["tax_generic"]))
            if val is not None:
                tax_total = val
                tax_found = True

        # Business-rule sanity checks: CGST/SGST should always be equal
        # (same rate split two ways), and IGST is mutually exclusive with
        # CGST+SGST (intra-state vs inter-state supply). A mismatch usually
        # means a table/OCR misread rather than a genuinely unusual invoice.
        warning = None
        if cgst_val is not None and sgst_val is not None and abs(cgst_val - sgst_val) > 0.01:
            warning = "CGST/SGST amounts don't match - please verify"
        elif igst_val and (cgst_val or sgst_val):
            warning = "IGST and CGST/SGST both present on this line - please verify"

        items.append({
            "hsn": code,
            "taxable": taxable if taxable is not None else 0.0,
            "tax": tax_total if tax_found else 0.0,
            "source": "table",
            "warning": warning,
        })

    return items


# ---------------------------------------------------------------------
# Fallback: no table could be parsed, scan raw text for code-like tokens
# ---------------------------------------------------------------------

def fallback_extract_items(text):
    items = []
    line_re = re.compile(r"\b(\d{4}|\d{6}|\d{8})\b")
    number_re = re.compile(r"[\d,]+\.\d{1,2}")
    for line in text.split("\n"):
        line = DATE_TOKEN_RE.sub(" ", line)
        line = ISO_DATE_RE.sub(" ", line)
        code_match = line_re.search(line)
        if not code_match:
            continue
        numbers = [parse_number(n) for n in number_re.findall(line)]
        numbers = [n for n in numbers if n is not None]
        if not numbers:
            continue
        taxable = numbers[0]
        tax = numbers[1] if len(numbers) > 1 else 0.0
        items.append({
            "hsn": code_match.group(1),
            "taxable": taxable,
            "tax": tax,
            "source": "text_fallback",
            "warning": None,
        })
    return items


# ---------------------------------------------------------------------
# Bill of Entry (customs import document) parsing
# ---------------------------------------------------------------------

def is_bill_of_entry(text):
    return bool(BOE_MARKER_RE.search(text)) and bool(CTH_MARKER_RE.search(text))


def find_label_value(lines, label_re, max_lookahead=4):
    """Value on the line(s) following a form label like 'IMPORTER NAME &
    ADDRESS' - OCR/PDF text extraction puts the label and its value on
    separate lines for these boxed form fields."""
    for i, line in enumerate(lines):
        if label_re.search(line):
            for j in range(i + 1, min(i + 1 + max_lookahead, len(lines))):
                candidate = lines[j].strip(" |@").strip()
                candidate = re.sub(r"^[\d.\s|@]+", "", candidate).strip()
                # Drop a leading run of stray lowercase OCR noise (e.g. "ra "
                # before "AMERICAN OIL...") by starting at the first
                # substantial run of capitalized text, if there is one.
                m = re.search(r"[A-Z][A-Z&,.'\s]{3,}", candidate)
                if m:
                    candidate = candidate[m.start():].strip()
                if len(candidate) > 3 and not re.match(r"^\d", candidate):
                    return candidate
    return None


def extract_boe_data(text):
    """Parse a customs Bill of Entry: BE No/date, importer, supplier, and
    CTH-coded line items. Structurally different from a GST tax invoice -
    duty (BCD/IGST/CVD) is assessed once for the whole document rather than
    per line, so no per-item tax figure is available."""
    lines = text.split("\n")

    be_no = None
    m = BE_NO_DATE_RE.search(text)
    if m:
        be_no = m.group(1)

    importer_name = find_label_value(lines, IMPORTER_LABEL_RE)
    supplier_name = find_label_value(lines, SUPPLIER_LABEL_RE)
    if not supplier_name:
        supplier_name = find_label_value(lines, SELLER_LABEL_RE)

    gstins = find_gstins_with_pos(text)
    importer_gstin = gstins[0][0] if gstins else None

    rate_match = EXCHANGE_RATE_RE.search(text)
    exchange_rate = parse_number(rate_match.group(1)) if rate_match else None

    items = []
    for line in lines:
        m = CTH_ITEM_LINE_RE.search(line)
        if not m:
            continue
        cth, _unit_price, _qty, amount = m.groups()
        amount_val = parse_number(amount)
        if amount_val is None:
            continue
        taxable = amount_val * exchange_rate if exchange_rate else amount_val
        items.append({
            "hsn": cth,
            "taxable": round(taxable, 2),
            "tax": 0.0,
            "source": "boe",
            "warning": None,
        })

    note = (
        "Bill of Entry - CTH code shown as HSN/SAC code; GSTIN shown is the "
        "IMPORTER's own GSTIN (no vendor GSTIN applies to a foreign supplier); "
        "Taxable Value is the item amount"
        + (f" converted to INR at 1 USD = {exchange_rate} INR" if exchange_rate else "")
        + ". Duty (BCD/IGST/CVD) is assessed once for the whole Bill of Entry, "
        "not per line item - check the BE's duty summary directly for that."
    )
    if not items:
        note += " No CTH line items could be parsed - manual review needed."

    return {
        "invoice_number": f"BE {be_no}" if be_no else None,
        "vendor_name": supplier_name or importer_name,
        "vendor_gstin": importer_gstin,
        "items": items,
        "note": note,
    }


# ---------------------------------------------------------------------
# OCR fallback: pages with no embedded text (scanned/photographed invoices)
# ---------------------------------------------------------------------

def ocr_page_text(page):
    """Rasterize a page and run Tesseract OCR on it. Returns (text, error)."""
    try:
        image = page.to_image(resolution=OCR_RESOLUTION).original
        text = pytesseract.image_to_string(image)
        return text, None
    except pytesseract.TesseractNotFoundError:
        return "", "tesseract_not_found"
    except Exception as e:
        return "", str(e)


def get_page_text(page):
    """Native text if present, otherwise OCR. Returns (text, was_ocr, ocr_error)."""
    native_text = page.extract_text() or ""
    if len(native_text.strip()) >= MIN_NATIVE_TEXT_CHARS:
        return native_text, False, None
    ocr_text, ocr_error = ocr_page_text(page)
    if ocr_text.strip():
        return ocr_text, True, None
    # OCR failed or found nothing - fall back to whatever native text exists.
    return native_text, False, ocr_error


def ocr_pdf_via_pdfium(path):
    """OCR every page by rendering it directly with pypdfium2.

    Used when pdfplumber can't parse a PDF's page structure at all (some
    scanner software emits PDFs like this - pdfminer sees 0 pages even
    though the file is perfectly valid). Returns (text, used_ocr, error).
    """
    try:
        doc = pdfium.PdfDocument(path)
    except Exception as e:
        return "", False, str(e)

    scale = OCR_RESOLUTION / 72
    text_parts = []
    ocr_error = None
    try:
        for page in doc:
            image = page.render(scale=scale).to_pil()
            try:
                text_parts.append(pytesseract.image_to_string(image))
            except pytesseract.TesseractNotFoundError:
                ocr_error = "tesseract_not_found"
                break
            except Exception as e:
                ocr_error = str(e)
    finally:
        doc.close()

    full_text = "\n".join(text_parts)
    return full_text, bool(full_text.strip()), ocr_error


# ---------------------------------------------------------------------
# Entry point: process a single PDF
# ---------------------------------------------------------------------

def process_pdf(path):
    result = {
        "invoice_number": None,
        "vendor_name": None,
        "vendor_gstin": None,
        "items": [],
        "note": "",
        "used_ocr": False,
        "doc_type": "invoice",
    }
    try:
        with pdfplumber.open(path) as pdf:
            if len(pdf.pages) == 0:
                # pdfplumber/pdfminer couldn't parse this PDF's page
                # structure at all - render pages directly with pypdfium2
                # and OCR them instead (see module docstring).
                full_text, used_ocr, ocr_error = ocr_pdf_via_pdfium(path)
                all_items = []
            else:
                page_texts = []
                used_ocr = False
                ocr_error = None
                for page in pdf.pages:
                    text, was_ocr, err = get_page_text(page)
                    page_texts.append(text)
                    used_ocr = used_ocr or was_ocr
                    ocr_error = ocr_error or err
                full_text = "\n".join(page_texts)
                all_items = None  # computed below only if not a Bill of Entry

            result["used_ocr"] = used_ocr

            if is_bill_of_entry(full_text):
                boe = extract_boe_data(full_text)
                result["doc_type"] = "bill_of_entry"
                result["invoice_number"] = boe["invoice_number"]
                result["vendor_name"] = boe["vendor_name"]
                result["vendor_gstin"] = boe["vendor_gstin"]
                result["items"] = boe["items"]
                result["note"] = boe["note"]
                return result

            if all_items is None:
                all_items = []
                for page in pdf.pages:
                    tables = []
                    try:
                        tables = page.extract_tables() or []
                    except Exception:
                        tables = []
                    if not tables:
                        try:
                            tables = page.extract_tables({
                                "vertical_strategy": "text",
                                "horizontal_strategy": "text",
                            }) or []
                        except Exception:
                            tables = []
                    for table in tables:
                        items = extract_rows_from_table(table)
                        if items:
                            all_items.extend(items)

            result["invoice_number"] = find_invoice_number(full_text)
            cust_off = find_customer_offset(full_text)
            result["vendor_gstin"] = find_vendor_gstin(full_text, cust_off)
            result["vendor_name"] = find_vendor_name(full_text, cust_off)

            if not all_items:
                all_items = fallback_extract_items(full_text)
                if all_items:
                    if used_ocr:
                        result["note"] = "Scanned PDF - line items found via OCR - please verify carefully."
                    else:
                        result["note"] = "Line items found via text fallback - please verify."
                elif ocr_error == "tesseract_not_found":
                    result["note"] = (
                        "Scanned PDF detected but Tesseract OCR is not installed - "
                        "manual review needed."
                    )
                elif used_ocr:
                    result["note"] = "Scanned PDF - OCR ran but no HSN/SAC codes found - manual review needed."
                else:
                    result["note"] = "No HSN/SAC line items detected - manual review needed."
            elif used_ocr:
                result["note"] = "Scanned PDF - some text recovered via OCR - please verify carefully."

            result["items"] = all_items

    except Exception as e:
        result["note"] = f"Error processing PDF: {e}"

    return result


# ---------------------------------------------------------------------
# Confidence scoring - how much to trust one extracted row
# ---------------------------------------------------------------------

def compute_confidence(result, item=None):
    """High/Medium/Low rating for one output row, based on how the data was
    extracted rather than what it says. Never affects the extracted values
    themselves - purely a "how much should I double-check this" signal."""
    if result.get("note", "").startswith("Error processing PDF"):
        return "Low"
    if item is None or not item.get("hsn"):
        return "Low"
    if item.get("warning"):
        return "Low"

    gstin = result.get("vendor_gstin")
    gstin_ok = is_valid_gstin(gstin) if gstin else False
    source = item.get("source")
    used_ocr = result.get("used_ocr")

    if source == "table" and not used_ocr:
        return "High" if gstin_ok else "Medium"
    if source in ("text_fallback", "boe") or used_ocr:
        return "Medium" if gstin_ok else "Low"
    return "Low"
