"""
Multi-strategy PDF text and metadata extractor for Indian TDS/TCS Certificates.
Utilizes PyMuPDF layout analysis, coordinate-aware block parsing, and specialized regex heuristics.
"""

import re
import time
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

import pymupdf as fitz
from core.models import CertificateData, ProcessingStatus
from core.classifier import CertificateClassifier
from config import ACT_1961, ACT_2025


class CertificateExtractor:
    """Extracts structured metadata from TDS/TCS certificates."""

    def __init__(self, classifier: Optional[CertificateClassifier] = None, enable_ocr: bool = True):
        self.classifier = classifier or CertificateClassifier()
        self.enable_ocr = enable_ocr

    def extract(self, file_path: Path) -> CertificateData:
        """
        Extract all metadata fields from a PDF file.
        Returns a populated CertificateData object.
        """
        start_time = time.perf_counter()
        file_path = Path(file_path)
        cert = CertificateData(file_path=file_path)

        if not file_path.exists():
            cert.status = ProcessingStatus.ERROR
            cert.message = "File does not exist"
            return cert

        try:
            doc = fitz.open(str(file_path))
        except Exception as e:
            cert.status = ProcessingStatus.ERROR
            cert.message = f"Failed to open PDF: {str(e)}"
            return cert

        try:
            if len(doc) == 0:
                cert.status = ProcessingStatus.ERROR
                cert.message = "PDF document is empty (0 pages)"
                return cert

            # TRACES certificates place all primary metadata on Page 1
            page = doc[0]
            # Capture both stream order and visual layout reading order
            stream_text = page.get_text("text") or ""
            sorted_text = page.get_text("text", sort=True) or ""
            raw_text = stream_text
            combined_text = f"{stream_text}\n{sorted_text}"
            blocks = page.get_text("blocks") or []

            # Check for scanned PDF (empty or near-empty text layer)
            if len(raw_text.strip()) < 40:
                cert.is_scanned = True
                if self.enable_ocr:
                    raw_text = self._try_ocr(page)
                    combined_text = raw_text
                    blocks = []

            cert.raw_text_snippet = raw_text[:1000]

            # Step 1: Classification (Form Code, Form Name, Act, Category)
            code, name, act, category, confidence = self.classifier.classify(combined_text)
            cert.form_code = code
            cert.form_type = name
            cert.act = act
            cert.category = category
            cert.confidence_score = confidence

            # Step 2: Extract Deductee / Collectee / Employee Name
            cert.deductee_name = self._extract_deductee_name(sorted_text, blocks, code)

            # Step 3: Extract PAN of Deductee
            cert.deductee_pan = self._extract_deductee_pan(sorted_text, stream_text)

            # Step 4: Extract TAN of Deductor / Collector
            cert.deductor_tan = self._extract_deductor_tan(combined_text)

            # Step 5: Extract Assessment Year & Financial Year
            cert.assessment_year, cert.financial_year = self._extract_years(combined_text)

            # Step 6: Extract Quarter
            cert.quarter = self._extract_quarter(combined_text, file_path.name)

            # Step 7: Extract Certificate Number
            all_pages_text = "\n".join(p.get_text("text", sort=True) for p in doc) if len(doc) > 1 else sorted_text
            cert.certificate_no = self._extract_certificate_no(combined_text, all_pages_text)

            # Step 8: Deduce status & validation message
            if cert.deductee_name:
                cert.status = ProcessingStatus.EXTRACTED
                cert.message = "Metadata extracted successfully"
            else:
                cert.status = ProcessingStatus.ERROR
                cert.message = "Could not identify Deductee/Collectee name"

        except Exception as e:
            cert.status = ProcessingStatus.ERROR
            cert.message = f"Extraction error: {str(e)}"
        finally:
            doc.close()
            cert.processing_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return cert

    # ==========================================================================
    # INTERNAL EXTRACTION HEURISTICS
    # ==========================================================================

    def _extract_deductee_name(self, text: str, blocks: List[Tuple], form_code: str = "") -> str:
        """Extract and clean Deductee / Collectee / Employee name."""
        target_labels = [
            "name and address of the deductee",
            "name & address of the deductee",
            "name and address of the collectee",
            "name & address of the collectee",
            "name and address of the employee",
            "name & address of the employee",
            "name and address of the payee",
            "name & address of the payee",
            "name and address of the transferor",
            "name & address of the transferor",
            "name of the employee",
            "name of the deductee",
            "name of deductee",
            "name of employee",
            "name of collectee",
        ]

        # Strategy 1: Label and Name are inside the SAME block (e.g. mock certificates)
        if blocks:
            for b in blocks:
                b_text = b[4].strip()
                b_lower = b_text.lower()
                for label in target_labels:
                    if label in b_lower:
                        name = self._parse_name_from_block(b_text, label)
                        if name:
                            return name

        # Strategy 1.5: Act 2025 Form 130-133 section "Details of the deductee / employee / payee / collectee"
        # Under Income-tax Act, 2025, Deductee name is in row "Name" within the "Details of the deductee" section
        m_2025 = re.search(
            r"Details\s+of\s+the\s+(?:deductee|payee|employee|collectee)[\s\S]*?(?:9\.?\s*Name|\bName\b)\s*\n+([\s\S]*?)(?=\n\s*(?:10\.|\(?refer\s+Note\s*2\)?|Address|Permanent\s+Account|PART\s+B))",
            text,
            re.IGNORECASE,
        )
        if m_2025:
            cand_block = m_2025.group(1).strip()
            for line in cand_block.splitlines():
                clean = self._sanitize_name_candidate(line)
                if clean:
                    return clean

        if blocks:
            deductee_section_y = None
            part_b_y = 10000.0
            for b in blocks:
                b_text_l = b[4].lower()
                if any(h in b_text_l for h in ["details of the deductee", "details of deductee", "details of the employee", "details of the payee", "details of the collectee"]):
                    deductee_section_y = b[3]
                elif "part b" in b_text_l or "summary of payment" in b_text_l:
                    part_b_y = b[1]

            if deductee_section_y is not None:
                cands_2025 = []
                for b in blocks:
                    if b[0] >= 200 and deductee_section_y <= b[1] <= part_b_y:
                        lines = [l.strip() for l in b[4].splitlines() if l.strip()]
                        if lines:
                            clean = self._sanitize_name_candidate(lines[0])
                            if clean:
                                cands_2025.append((b[1], clean))
                if cands_2025:
                    cands_2025.sort(key=lambda x: x[0])
                    return cands_2025[0][1]

        # Strategy 2: Spatial coordinate lookup for TRACES 1961 Page 1
        # In official TRACES certificates (Form 16, 16A, 27D, etc.), Deductor/Collector is in left column (x0 < 270)
        # and Deductee/Collectee is in right column (x0 >= 265, y between 140 and 265).
        if blocks:
            header_y1 = None
            for b in blocks:
                b_lower = b[4].strip().lower()
                if any(h in b_lower for h in ["name and address", "name & address"]):
                    header_y1 = b[3]
                    break

            if header_y1 is not None:
                min_y = header_y1 - 2
                right_candidates = []
                for b in blocks:
                    center_x = (b[0] + b[2]) / 2
                    if (b[0] >= 265 or center_x > 280) and (min_y <= b[1] <= 265):
                        lines = [l.strip() for l in b[4].splitlines() if l.strip()]
                        if not lines:
                            continue
                        clean = self._sanitize_name_candidate(lines[0])
                        if clean:
                            right_candidates.append((b[1], clean))

                if right_candidates:
                    right_candidates.sort(key=lambda x: x[0])
                    return right_candidates[0][1]

        # Strategy 3: Regex search across full text
        patterns = [
            r"Name\s+(?:and|&)\s+address\s+of\s+the\s+(?:Deductee|Employee|Collectee|Payee|Transferor)[\s:]*([^\n\r]+)",
            r"Name\s+of\s+(?:the\s+)?(?:Deductee|Employee|Collectee|Employee/Deductee)[\s:]*([^\n\r]+)",
            r"Employee\s+Name[\s:]*([^\n\r]+)",
            r"Deductee\s+Name[\s:]*([^\n\r]+)",
            r"Collectee\s+Name[\s:]*([^\n\r]+)",
        ]

        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                clean = self._sanitize_name_candidate(candidate)
                if clean:
                    return clean

        # Strategy 4: Multiline extraction between header and next field
        multiline_pat = (
            r"Name\s+(?:and|&)\s+address\s+of\s+the\s+(?:Deductee|Employee|Collectee|Payee|Transferor)\s*[\n\r]+"
            r"([A-Za-z0-9\s.,&/\-'\(\)]+?)(?=\n\s*(?:PAN|Address|PIN|CIT|Flat|Plot|Road|District|State|\d{6}))"
        )
        match_ml = re.search(multiline_pat, text, re.IGNORECASE)
        if match_ml:
            candidate = match_ml.group(1).strip().splitlines()[0]
            clean = self._sanitize_name_candidate(candidate)
            if clean:
                return clean

        return ""

    def _parse_name_from_block(self, block_text: str, matched_label: str) -> str:
        """Parse the actual name line from a text block containing the target label."""
        lines = [line.strip() for line in block_text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            if matched_label in line.lower():
                # Check if name is on the same line after colon
                parts = re.split(r":|—|-", line, maxsplit=1)
                if len(parts) > 1:
                    clean = self._sanitize_name_candidate(parts[1])
                    if clean:
                        return clean
                # Otherwise, take the next line as the name
                if idx + 1 < len(lines):
                    clean = self._sanitize_name_candidate(lines[idx + 1])
                    if clean:
                        return clean
        return ""

    def _sanitize_name_candidate(self, raw: str) -> str:
        """Clean name candidate from noise, addresses, numbers, and honorifics."""
        if not raw:
            return ""

        name = raw.strip()
        # Remove note references like '(refer Note 1)'
        name = re.sub(r"\(refer\s+Note.*?\)", "", name, flags=re.IGNORECASE).strip()
        # Remove common prefixes
        name = re.sub(r"^(?:M/s\.?|Shri\.?|Smt\.?|Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Name\s*:?)\s*", "", name, flags=re.IGNORECASE)
        # Remove trailing/leading colon, dashes, slashes, ampersands
        name = re.sub(r"^[ :\-_/&]+|[ :\-_/&]+$", "", name)

        # Reject alphanumeric IDs / Certificate Numbers (e.g. AAI262719021825, TR16A9928172)
        if re.search(r"\d{4,}", name):
            return ""
        if sum(c.isdigit() for c in name) > 3:
            return ""
        if re.match(r"^[A-Z]{3,5}\d{5,}$", name):
            return ""

        # Disallow table headers, labels, and metadata markers
        disallowed = [
            "name and address", "name & address", "address of", "collector", "deductor",
            "deductee", "collectee", "employee", "payee", "transferor",
            "pan of", "tan of", "summary", "annexure", "details of tax", "details of",
            "certificate no", "certificate number", "assessment year", "financial year", "tax year", "quarter",
            "government of india", "income tax department", "traces", "reference no",
            "book identification", "challan", "total (rs", "amount", "date of", "signature",
            "see rule", "form no", "nature of", "status of matching", "original", "statement",
            "the commissioner", "income-tax", "income tax", "permanent account number",
            "contact number", "email id", "country code"
        ]
        name_lower = name.lower()
        if any(d in name_lower for d in disallowed):
            return ""

        # Remove address tails if accidentally matched (e.g., street, pincode)
        name = re.split(r",|\b(?:Plot|Flat|Door|Street|Road|Lane|Sector|Nagar|PIN|Pincode)\b", name, flags=re.IGNORECASE)[0]
        name = name.strip()

        # Check reasonable length
        if 2 <= len(name) <= 90 and re.search(r"[A-Za-z]", name):
            # Normalize whitespace
            name = " ".join(name.split())
            return name.upper()

        return ""

    def _extract_deductee_pan(self, text: str, fallback_text: str = "") -> str:
        """Extract 10-character PAN of Deductee/Employee/Collectee."""
        # Standard PAN regex: 5 uppercase letters, 4 digits, 1 uppercase letter
        pan_pat = r"[A-Z]{5}[0-9]{4}[A-Z]"

        texts_to_check = [text]
        if fallback_text and fallback_text != text:
            texts_to_check.append(fallback_text)

        for src_text in texts_to_check:
            # Act 2025 context: Details of the deductee -> Permanent Account Number
            m_2025_pan = re.search(
                rf"Details\s+of\s+the\s+(?:deductee|payee|employee|collectee)[\s\S]{{0,500}}?Permanent\s+Account\s+Number[\s:]*({pan_pat})",
                src_text,
                re.IGNORECASE,
            )
            if m_2025_pan:
                return m_2025_pan.group(1).upper()

            # Specific context: PAN of Deductee / Employee / Collectee (note TRACES sometimes spells 'Collctee')
            context_patterns = [
                rf"PAN\s+of\s+(?:the\s+)?(?:Deductee|Employee|Coll?ectee|Payee|Transferor)[\s:]*({pan_pat})",
                rf"Deductee\s+PAN[\s:]*({pan_pat})",
                rf"Employee\s+PAN[\s:]*({pan_pat})",
                rf"Coll?ectee\s+PAN[\s:]*({pan_pat})",
            ]

            for pat in context_patterns:
                match = re.search(pat, src_text, re.IGNORECASE)
                if match:
                    return match.group(1).upper()

        # Secondary search: search for all PAN matches
        all_pans = re.findall(pan_pat, text)
        if len(all_pans) >= 2:
            # Usually the second PAN is Deductee's PAN (1st is Deductor's PAN)
            return all_pans[1].upper()
        elif len(all_pans) == 1:
            return all_pans[0].upper()

        return ""

    def _extract_deductor_tan(self, text: str) -> str:
        """Extract 10-character TAN of Deductor (4 letters, 5 digits, 1 letter)."""
        tan_pat = r"\b[A-Z]{4}[0-9]{5}[A-Z]\b"
        match = re.search(tan_pat, text)
        return match.group(0).upper() if match else ""

    def _extract_years(self, text: str) -> Tuple[str, str]:
        """Extract Assessment Year (AY) and Financial Year (FY) or Tax Year (Act 2025)."""
        ay = ""
        fy = ""

        # Search for Assessment Year e.g. 2024-25 or 2024-2025
        ay_match = re.search(r"Assessment\s+Year\s*:?\s*(\b20\d{2}\s*[-/]\s*(?:\d{2}|\d{4})\b)", text, re.IGNORECASE)
        if not ay_match:
            ay_match = re.search(r"Assessment\s+Year[\s\S]{0,120}?(\b20\d{2}\s*[-/]\s*(?:\d{2}|\d{4})\b)", text, re.IGNORECASE)
        if ay_match:
            ay_raw = ay_match.group(1).replace(" ", "")
            ay = self._normalize_year_str(ay_raw)

        # Search for Financial Year e.g. 2023-24
        fy_match = re.search(r"Financial\s+Year\s*:?\s*(\b20\d{2}\s*[-/]\s*(?:\d{2}|\d{4})\b)", text, re.IGNORECASE)
        if not fy_match:
            fy_match = re.search(r"(?:Financial\s+Year|\bFY\b)[\s\S]{0,60}?(\b20\d{2}\s*[-/]\s*(?:\d{2}|\d{4})\b)", text, re.IGNORECASE)
        if fy_match:
            fy_raw = fy_match.group(1).replace(" ", "")
            fy = self._normalize_year_str(fy_raw)
        elif ay:
            # Compute FY from AY: FY is 1 year prior to AY (e.g. AY 2024-25 -> FY 2023-24)
            fy = self._infer_fy_from_ay(ay)

        # Search for Tax Year under Income-tax Act, 2025 e.g. "Tax year 2026-27"
        if not ay and not fy:
            tax_yr_match = re.search(r"Tax\s+year\s*:?\s*(\b20\d{2}\s*[-/]\s*(?:\d{2}|\d{4})\b)", text, re.IGNORECASE)
            if not tax_yr_match:
                tax_yr_match = re.search(r"Tax\s+year[\s\S]{0,60}?(\b20\d{2}\s*[-/]\s*(?:\d{2}|\d{4})\b)", text, re.IGNORECASE)
            if tax_yr_match:
                ty_raw = tax_yr_match.group(1).replace(" ", "")
                tax_year = self._normalize_year_str(ty_raw)
                ay = tax_year
                fy = tax_year

        return ay, fy

    def _normalize_year_str(self, raw: str) -> str:
        """Normalize 2024-2025 or 2024/25 to 2024-25."""
        raw = raw.replace("/", "-")
        parts = raw.split("-")
        if len(parts) == 2:
            start_yr = parts[0]
            end_yr = parts[1]
            if len(end_yr) == 4:
                end_yr = end_yr[-2:]
            return f"{start_yr}-{end_yr}"
        return raw

    def _infer_fy_from_ay(self, ay: str) -> str:
        """Convert AY 2024-25 -> FY 2023-24."""
        match = re.match(r"^(\d{4})-(\d{2})$", ay)
        if match:
            ay_start = int(match.group(1))
            fy_start = ay_start - 1
            fy_end = (fy_start + 1) % 100
            return f"{fy_start}-{fy_end:02d}"
        return ""

    def _extract_quarter(self, text: str, filename: str = "") -> str:
        """Extract Quarter (Q1, Q2, Q3, Q4)."""
        # Look for explicit Quarter: Q1, Q2, Q3, Q4
        match = re.search(r"Quarter\s*:?\s*(Q[1-4]|[1-4])\b", text, re.IGNORECASE)
        if match:
            q = match.group(1).upper()
            if not q.startswith("Q"):
                q = f"Q{q}"
            return q

        # Look for Quarter table cell or near Quarter/Quarterly label
        q_table_match = re.search(r"(?:Quarter|Quarterly)[\s\S]{1,250}?\b(Q[1-4])\b", text, re.IGNORECASE)
        if q_table_match:
            return q_table_match.group(1).upper()

        # Look for period-based Quarter (e.g., April to June -> Q1)
        if re.search(r"01-Apr.*?to.*?30-Jun|April.*?June", text, re.IGNORECASE | re.DOTALL):
            return "Q1"
        if re.search(r"01-Jul.*?to.*?30-Sep|July.*?September", text, re.IGNORECASE | re.DOTALL):
            return "Q2"
        if re.search(r"01-Oct.*?to.*?31-Dec|October.*?December", text, re.IGNORECASE | re.DOTALL):
            return "Q3"
        if re.search(r"01-Jan.*?to.*?31-Mar|January.*?March", text, re.IGNORECASE | re.DOTALL):
            return "Q4"

        # Look for standalone Q1-Q4
        m_q = re.search(r"\b(Q[1-4])\b", text)
        if m_q:
            return m_q.group(1).upper()

        # Fallback to filename
        if filename:
            m_fn = re.search(r"_(Q[1-4])_", filename, re.IGNORECASE)
            if m_fn:
                return m_fn.group(1).upper()

        return ""

    def _extract_certificate_no(self, text: str, all_pages_text: str = "") -> str:
        """Extract TRACES Certificate Number."""
        combined_text = f"{text}\n{all_pages_text}" if all_pages_text else text
        disallowed = [
            "ASSESSMENT", "SECTION", "DETAILS", "PERIOD", "SUMMARY", "GOVERNMENT",
            "SOURCE", "ORIGINAL", "COLLECTEE", "DEDUCTEE", "COLLECTOR", "DEDUCTOR"
        ]

        # Pattern 1: Certificate No. / Certificate Number followed by alphanumeric/hyphen
        match = re.search(r"Certificate\s+(?:No\.?|Number)\s*:?\s*([A-Za-z0-9\-]{6,25})", combined_text, re.IGNORECASE)
        if match:
            cand = match.group(1).strip().upper().strip(".-_")
            if not any(d in cand for d in disallowed):
                return cand

        # Pattern 2: Alphanumeric code followed by Certificate No
        match_rev = re.search(r"\b([A-Za-z0-9\-]{6,25})\s*[\n\r]+\s*Certificate\s+No\.?", text, re.IGNORECASE)
        if match_rev:
            cand = match_rev.group(1).strip().upper().strip(".-_")
            if not any(d in cand for d in disallowed):
                return cand

        return ""

    def _try_ocr(self, page) -> str:
        """Fallback OCR for scanned certificates."""
        try:
            import pytesseract
            from PIL import Image
            import io

            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes()))
            return pytesseract.image_to_string(img)
        except Exception:
            return ""
