"""PDF Extraction and Document Structure Identification Engine.

Extracts text from text-based PDFs, preserves page numbers, identifies financial statements
(Balance Sheet, P&L, Cash Flow, SOCIE, Notes, Auditor's Report, CARO),
and flags scanned / unreadable documents with actionable user notifications.
"""

import io
import re
from typing import Dict, Any, List, Optional
import pymupdf  # PyMuPDF


class PDFExtractor:
    """Extracts text and detects structural financial sections from PDF documents."""

    SECTION_PATTERNS = {
        "auditor_report": [
            r"independent\s+auditor'?s\s+report",
            r"auditors?'\s+report",
            r"report\s+on\s+the\s+audit\s+of\s+the\s+financial\s+statements",
        ],
        "caro_report": [
            r"companies\s+\(auditor'?s\s+report\)\s+order",
            r"annexure\s+[a-z\d]\s+to\s+the\s+independent\s+auditors?'\s+report",
            r"caro[,\s]+2020",
            r"caro[,\s]+2016",
        ],
        "balance_sheet": [
            r"balance\s+sheet\s+as\s+at",
            r"balance\s+sheet\b",
            r"statement\s+of\s+financial\s+position",
        ],
        "profit_and_loss": [
            r"statement\s+of\s+profit\s+and\s+loss",
            r"profit\s+and\s+loss\s+statement",
            r"statement\s+of\s+comprehensive\s+income",
        ],
        "cash_flow": [
            r"statement\s+of\s+cash\s+flows?",
            r"cash\s+flow\s+statement",
        ],
        "changes_in_equity": [
            r"statement\s+of\s+changes\s+in\s+equity",
            r"socie",
        ],
        "notes_to_accounts": [
            r"notes\s+to\s+(?:the\s+)?financial\s+statements",
            r"notes\s+forming\s+part\s+of\s+(?:the\s+)?financial\s+statements",
            r"significant\s+accounting\s+policies",
        ],
    }

    @classmethod
    def extract_from_bytes(cls, file_bytes: bytes, filename: str = "document.pdf") -> Dict[str, Any]:
        """Extracts text from PDF or Excel bytes and maps out sections with page/sheet references."""
        # Dispatch to Excel extractor if Excel file
        if filename.lower().endswith((".xlsx", ".xls", ".xlsm")):
            return cls.extract_from_excel_bytes(file_bytes, filename)

        try:
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            return {
                "success": False,
                "is_scanned": False,
                "error": f"Failed to open PDF document: {str(e)}",
                "total_pages": 0,
                "pages": [],
                "sections": {},
                "full_text": "",
            }

        total_pages = len(doc)
        if total_pages == 0:
            return {
                "success": False,
                "is_scanned": False,
                "error": "The uploaded PDF document has zero pages.",
                "total_pages": 0,
                "pages": [],
                "sections": {},
                "full_text": "",
            }

        pages_data: List[Dict[str, Any]] = []
        total_chars = 0
        full_text_list = []

        for page_idx in range(total_pages):
            page = doc[page_idx]
            text = page.get_text("text")
            char_count = len(text.strip())
            total_chars += char_count

            pages_data.append({
                "page_num": page_idx + 1,
                "text": text,
                "char_count": char_count,
            })
            full_text_list.append(f"--- PAGE {page_idx + 1} ---\n{text}")

        full_text = "\n\n".join(full_text_list)
        avg_chars_per_page = total_chars / total_pages if total_pages > 0 else 0

        # Scanned PDF check: less than 60 characters per page indicates an image scan
        is_scanned = avg_chars_per_page < 60 and total_pages > 0

        if is_scanned:
            return {
                "success": False,
                "is_scanned": True,
                "filename": filename,
                "total_pages": total_pages,
                "avg_chars_per_page": avg_chars_per_page,
                "error": (
                    "Scanned / Image-Only PDF Detected: The document contains insufficient selectable text "
                    f"(average {avg_chars_per_page:.1f} characters per page). Financial Reporting Review Board (FRRB) "
                    "review procedures require searchable, text-based financial statements. Please upload a searchable "
                    "PDF (exported directly from ERP / accounting software or OCR-processed)."
                ),
                "pages": pages_data,
                "sections": {},
                "full_text": "",
            }

        # Identify sections across pages
        sections = cls._identify_sections(pages_data)

        return {
            "success": True,
            "is_scanned": False,
            "filename": filename,
            "total_pages": total_pages,
            "avg_chars_per_page": round(avg_chars_per_page, 1),
            "pages": pages_data,
            "sections": sections,
            "full_text": full_text,
            "error": None,
        }

    @classmethod
    def extract_from_excel_bytes(cls, excel_bytes: bytes, filename: str = "document.xlsx") -> Dict[str, Any]:
        """Extracts text and financial statement tables from an Excel (.xlsx / .xls) workbook."""
        import openpyxl
        try:
            # values only: skipping links to other workbooks makes loading several times faster
            wb = openpyxl.load_workbook(io.BytesIO(excel_bytes), data_only=True, read_only=True, keep_links=False)
        except Exception as e:
            return {
                "success": False,
                "is_scanned": False,
                "error": f"Failed to open Excel workbook: {str(e)}",
                "total_pages": 0,
                "pages": [],
                "sections": {},
                "full_text": "",
            }

        pages_data: List[Dict[str, Any]] = []
        full_text_list = []
        total_chars = 0

        for idx, sheetname in enumerate(wb.sheetnames, start=1):
            ws = wb[sheetname]
            sheet_lines = [f"=== SHEET {idx}: {sheetname.upper()} ==="]
            ws.reset_dimensions()

            for row in ws.iter_rows(values_only=True):
                # Filter out empty rows
                non_empty = [str(cell).strip() for cell in row if cell is not None and str(cell).strip() != ""]
                if non_empty:
                    sheet_lines.append(" | ".join(non_empty))

            sheet_text = "\n".join(sheet_lines)
            char_count = len(sheet_text.strip())
            total_chars += char_count

            pages_data.append({
                "page_num": idx,
                "sheet_name": sheetname,
                "text": sheet_text,
                "char_count": char_count,
            })
            full_text_list.append(f"--- SHEET {idx}: {sheetname} ---\n{sheet_text}")

        wb.close()
        full_text = "\n\n".join(full_text_list)
        total_pages = len(pages_data)
        avg_chars = total_chars / total_pages if total_pages > 0 else 0

        sections = cls._identify_sections(pages_data)

        return {
            "success": True,
            "is_scanned": False,
            "filename": filename,
            "total_pages": total_pages,
            "avg_chars_per_page": round(avg_chars, 1),
            "pages": pages_data,
            "sections": sections,
            "full_text": full_text,
            "error": None,
        }

    @classmethod
    def _identify_sections(cls, pages: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Scans pages to locate start page and text extracts for each financial section."""
        detected_sections: Dict[str, Dict[str, Any]] = {}

        for sec_name, patterns in cls.SECTION_PATTERNS.items():
            detected_sections[sec_name] = {
                "detected": False,
                "start_page": None,
                "pages": [],
                "extract": "",
            }

            for page in pages:
                text_lower = page["text"].lower()
                for pattern in patterns:
                    if re.search(pattern, text_lower):
                        if not detected_sections[sec_name]["detected"]:
                            detected_sections[sec_name]["detected"] = True
                            detected_sections[sec_name]["start_page"] = page["page_num"]
                        if page["page_num"] not in detected_sections[sec_name]["pages"]:
                            detected_sections[sec_name]["pages"].append(page["page_num"])
                        break

        # Consolidate extracts for detected sections
        for sec_name, data in detected_sections.items():
            if data["detected"]:
                pages_included = data["pages"][:5]  # limit to first 5 pages for preview
                sample_texts = [
                    p["text"] for p in pages if p["page_num"] in pages_included
                ]
                data["extract"] = "\n\n".join(sample_texts)

        return detected_sections

    @classmethod
    def extract_key_metrics(cls, text: str) -> Dict[str, Optional[float]]:
        """Parses common financial figures from statement text (Assets, Liabilities, Revenue, PAT)."""
        metrics: Dict[str, Optional[float]] = {
            "total_assets": None,
            "total_equity_and_liabilities": None,
            "total_revenue": None,
            "profit_after_tax": None,
            "cash_and_cash_equivalents": None,
        }

        # Look for Total Assets
        m_assets = re.search(
            r"total\s+assets[^\d]{0,60}?([\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE
        )
        if m_assets:
            val_str = m_assets.group(1).replace(",", "")
            try:
                metrics["total_assets"] = float(val_str)
            except ValueError:
                pass

        # Look for Total Equity & Liabilities
        m_eq_liab = re.search(
            r"total\s+equity\s+and\s+liabilities[^\d]{0,60}?([\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE
        )
        if m_eq_liab:
            val_str = m_eq_liab.group(1).replace(",", "")
            try:
                metrics["total_equity_and_liabilities"] = float(val_str)
            except ValueError:
                pass

        # Look for Total Revenue
        m_rev = re.search(
            r"(?:total\s+income|total\s+revenue)[^\d]{0,60}?([\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE
        )
        if m_rev:
            val_str = m_rev.group(1).replace(",", "")
            try:
                metrics["total_revenue"] = float(val_str)
            except ValueError:
                pass

        # Look for Profit for the year / PAT
        m_pat = re.search(
            r"(?:profit\s+for\s+the\s+year|profit\s+after\s+tax)[^\d]{0,60}?([\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE
        )
        if m_pat:
            val_str = m_pat.group(1).replace(",", "")
            try:
                metrics["profit_after_tax"] = float(val_str)
            except ValueError:
                pass

        return metrics
