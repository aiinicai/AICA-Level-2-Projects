"""PDF Bank Statement Reader.
Supports digital PDFs via pdfplumber/PyMuPDF and scanned PDFs via OCR fallback.
"""

import os
import io
import pdfplumber
import fitz  # PyMuPDF
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from ingestion.detector import check_pdf_encrypted, decrypt_pdf, is_scanned_pdf
from ingestion.image_ocr import read_image_statement
from normalization.schema_mapper import (
    normalize_dataframe, load_bank_templates, detect_bank_from_header_text, extract_account_number
)

def extract_tables_from_digital_pdf(
    file_path_or_bytes: any,
    password: Optional[str] = None
) -> Tuple[List[List[str]], str]:
    """
    Extract table rows and header metadata text from a digital PDF using pdfplumber.
    """
    all_rows = []
    full_text = ""
    
    stream = open(file_path_or_bytes, "rb") if isinstance(file_path_or_bytes, str) else io.BytesIO(file_path_or_bytes)
    
    with pdfplumber.open(stream, password=password) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            full_text += "\n" + page_text
            
            # Extract tables with flexible settings
            tables = page.extract_tables({
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "snap_tolerance": 3,
                "join_tolerance": 3,
            })
            
            if not tables:
                # Fallback to text-based table extraction
                tables = page.extract_tables({
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 4,
                })
                
            for table in tables:
                if not table:
                    continue
                for row in table:
                    # Clean None values and multiline carriage returns in cells
                    cleaned_row = [
                        " ".join(str(cell).split()) if cell is not None else ""
                        for cell in row
                    ]
                    # Only add if row has at least one non-empty cell
                    if any(cleaned_row):
                        all_rows.append(cleaned_row)
                        
    return all_rows, full_text

def read_pdf_statement(
    file_path_or_bytes: any,
    filename: str = "",
    password: Optional[str] = None
) -> pd.DataFrame:
    """
    Ingest a PDF bank statement (digital or scanned) and return a normalized DataFrame.
    """
    fname = filename or (file_path_or_bytes if isinstance(file_path_or_bytes, str) else "statement.pdf")
    templates = load_bank_templates()
    
    # Check if PDF is encrypted
    if check_pdf_encrypted(file_path_or_bytes):
        if not password:
            print(f"File {fname} is password-protected. Please provide a password.")
            return pd.DataFrame()
        decrypted_bytes = decrypt_pdf(file_path_or_bytes, password)
        if not decrypted_bytes:
            print(f"Failed to decrypt {fname} with provided password.")
            return pd.DataFrame()
        file_input = decrypted_bytes
    else:
        file_input = file_path_or_bytes

    # Check if PDF is scanned / image-based
    if is_scanned_pdf(file_input, password=password):
        print(f"File {fname} detected as scanned image PDF. Running OCR pipeline...")
        # Render pages using PyMuPDF and run OCR
        doc = fitz.open(stream=file_input if isinstance(file_input, (bytes, bytearray)) else None,
                        filetype="pdf" if isinstance(file_input, (bytes, bytearray)) else None)
        if isinstance(file_input, str):
            doc = fitz.open(file_input)
            
        dfs = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            page_df = read_image_statement(img_bytes, filename=f"{fname}_p{page_idx+1}")
            if not page_df.empty:
                dfs.append(page_df)
                
        if dfs:
            return pd.concat(dfs, ignore_index=True)
        return pd.DataFrame()

    # Digital PDF path
    try:
        raw_rows, full_text = extract_tables_from_digital_pdf(file_input, password=password)
        if not raw_rows:
            # Fallback to PyMuPDF text parsing
            doc = fitz.open(stream=file_input if isinstance(file_input, (bytes, bytearray)) else None,
                            filetype="pdf" if isinstance(file_input, (bytes, bytearray)) else None)
            if isinstance(file_input, str):
                doc = fitz.open(file_input)
            full_text = "\n".join([page.get_text() for page in doc])
            lines = [line.strip() for line in full_text.splitlines() if line.strip()]
            from ingestion.image_ocr import parse_ocr_lines_to_transactions
            df_parsed = parse_ocr_lines_to_transactions(lines)
            bank_name, bank_tmpl = detect_bank_from_header_text(full_text, templates)
            acc_no = extract_account_number(full_text)
            return normalize_dataframe(
                df_parsed,
                source_file=fname,
                source_bank=bank_name,
                account_number=acc_no,
                bank_template=bank_tmpl
            )

        # Detect Bank and Account Number from statement text
        bank_name, bank_tmpl = detect_bank_from_header_text(full_text, templates)
        acc_no = extract_account_number(full_text)

        # Determine header row among extracted table rows
        from ingestion.excel_reader import find_table_header_row
        df_raw = pd.DataFrame(raw_rows)
        header_idx, headers = find_table_header_row(df_raw)
        
        df_data = df_raw.iloc[header_idx + 1:].copy()
        df_data.columns = headers
        df_data = df_data.dropna(how="all")

        return normalize_dataframe(
            df_data,
            source_file=fname,
            source_bank=bank_name,
            account_number=acc_no,
            bank_template=bank_tmpl
        )

    except Exception as e:
        print(f"Error reading PDF {fname}: {e}")
        return pd.DataFrame()
