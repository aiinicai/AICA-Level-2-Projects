"""
AI Auditor V8 - PDF Financial Statement Extractor
Parses native searchable PDFs and scanned PDFs using PyMuPDF (fitz), pdfplumber, and OCREngine.
"""

import os
import io
import pymupdf as fitz
import pdfplumber
from PIL import Image
from typing import Dict, List, Tuple, Optional, Any

from core.models import FinancialModel, FinancialStatement, LineItem, CompanyInfo
from extraction.statement_detector import StatementDetector
from extraction.ocr_engine import OCREngine
from config.constants import (
    STATEMENT_BALANCE_SHEET, STATEMENT_PROFIT_LOSS, STATEMENT_CASH_FLOW
)

class PDFExtractor:
    def __init__(self, filepath: str, use_ocr_if_needed: bool = True):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.use_ocr_if_needed = use_ocr_if_needed
        self.ocr_engine = OCREngine()

    def extract(self) -> FinancialModel:
        """Extracts financial data from PDF and constructs FinancialModel."""
        model = FinancialModel()
        model.company_info.source_file = self.filename
        
        # 1. Open with PyMuPDF to check text density & extract company metadata
        doc = fitz.open(self.filepath)
        total_pages = len(doc)
        full_doc_text = ""
        is_scanned = True
        
        for p_no in range(min(5, total_pages)):
            page_text = doc[p_no].get_text()
            if len(page_text.strip()) > 100:
                is_scanned = False
            full_doc_text += "\n" + page_text

        # Extract unit metadata from header text
        unit_label, multiplier = StatementDetector.detect_units(full_doc_text)
        model.company_info.unit_label = unit_label
        model.company_info.unit_multiplier = multiplier
        
        # Extract company name heuristic
        first_lines = [l.strip() for l in full_doc_text.splitlines() if l.strip()]
        for l in first_lines[:5]:
            if len(l) > 3 and not any(kw in l.lower() for kw in ["balance sheet", "profit", "financial statement", "cash flow", "as on", "for the year"]):
                model.company_info.name = l
                break

        if is_scanned and self.use_ocr_if_needed:
            self._extract_from_scanned_pdf(doc, model)
        else:
            self._extract_from_searchable_pdf(model)

        doc.close()

        # Synchronize periods across statements if needed
        periods = model.periods
        for stmt in [model.balance_sheet, model.profit_loss, model.cash_flow]:
            if not stmt.periods and periods:
                stmt.periods = list(periods)

        return model

    def _extract_from_searchable_pdf(self, model: FinancialModel):
        """Uses pdfplumber to extract structured tables from searchable PDF."""
        try:
            with pdfplumber.open(self.filepath) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    statement_type = StatementDetector.detect_statement_type(page_text)
                    
                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            self._process_raw_table(table, model, statement_type)
                    else:
                        # Fallback to line-by-line regex if table formatting is loose
                        self._process_text_lines(page_text, model, statement_type)
        except Exception as e:
            model.data_limitations.append(f"Error during PDF table extraction: {str(e)}")

    def _extract_from_scanned_pdf(self, doc: fitz.Document, model: FinancialModel):
        """Renders pages to images and runs OCR."""
        model.data_limitations.append("PDF appears to be scanned or image-based. Extracted via OCR.")
        if not OCREngine.is_tesseract_available():
            model.data_limitations.append("WARNING: Tesseract OCR is not installed. Scanned figures cannot be extracted automatically.")
            return

        for p_no in range(len(doc)):
            page = doc[p_no]
            # Render page to high-res image (300 DPI approx, zoom=2)
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            pil_img = Image.open(io.BytesIO(img_bytes))
            
            rows = self.ocr_engine.ocr_image_to_table_rows(pil_img)
            if rows:
                full_page_str = " ".join([" ".join(r) for r in rows])
                statement_type = StatementDetector.detect_statement_type(full_page_str)
                self._process_raw_table(rows, model, statement_type)

    def _process_raw_table(self, table: List[List[Any]], model: FinancialModel, default_statement_type: str):
        """Parses extracted 2D table data into statement LineItems."""
        if not table or len(table) < 2:
            return

        # Find period headers
        header_row_idx = -1
        period_cols = []
        
        for r_idx in range(min(5, len(table))):
            row_str = [str(c or '') for c in table[r_idx] if c is not None]
            detected = StatementDetector.detect_financial_periods(row_str)
            if len(detected) >= 1:
                header_row_idx = r_idx
                period_cols = detected
                break
                
        if header_row_idx == -1 or not period_cols:
            header_row_idx = 0
            # Heuristic: assign last two numeric-like columns
            period_cols = [(len(table[0]) - 2, "Current Period"), (len(table[0]) - 1, "Previous Period")]

        stmt = model.get_statement(default_statement_type)
        for _, p_name in period_cols:
            if p_name not in stmt.periods:
                stmt.periods.append(p_name)

        # Parse data rows
        for r_idx in range(header_row_idx + 1, len(table)):
            row = table[r_idx]
            if not row:
                continue

            # Check for section header switch
            row_text = " ".join([str(c or '') for c in row]).lower()
            if "profit and loss" in row_text or "statement of profit" in row_text:
                stmt = model.profit_loss
                continue
            elif "cash flow" in row_text:
                stmt = model.cash_flow
                continue
            elif "balance sheet" in row_text:
                stmt = model.balance_sheet
                continue

            # Extract line item text
            particulars = None
            for c in row:
                if c is not None and isinstance(c, str) and len(c.strip()) > 1:
                    if StatementDetector.clean_numeric_value(c) is None:
                        particulars = c.strip()
                        break
                        
            if not particulars or len(particulars) < 2:
                continue

            val_dict = {}
            for col_idx, p_name in period_cols:
                if col_idx < len(row) and row[col_idx] is not None:
                    num = StatementDetector.clean_numeric_value(row[col_idx])
                    if num is not None:
                        val_dict[p_name] = num

            if val_dict:
                item = LineItem(
                    original_name=particulars,
                    statement_type=stmt.statement_type,
                    values=val_dict
                )
                stmt.add_or_update_line_item(item)

    def _process_text_lines(self, text: str, model: FinancialModel, statement_type: str):
        """Fallback line-by-line parser for unstructured PDF text."""
        lines = text.splitlines()
        stmt = model.get_statement(statement_type)
        
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 3:
                # Check if last 1 or 2 parts are numbers
                val1 = StatementDetector.clean_numeric_value(parts[-1])
                val2 = StatementDetector.clean_numeric_value(parts[-2])
                
                if val1 is not None and val2 is not None:
                    name = " ".join(parts[:-2])
                    if len(name) > 2 and StatementDetector.clean_numeric_value(name) is None:
                        val_dict = {
                            "Current Period": val2,
                            "Previous Period": val1
                        }
                        item = LineItem(
                            original_name=name,
                            statement_type=statement_type,
                            values=val_dict
                        )
                        stmt.add_or_update_line_item(item)
