"""Unified Ingestion Package for Bank Statements."""

import os
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple, Union

from ingestion.detector import detect_file_type, check_pdf_encrypted
from ingestion.pdf_reader import read_pdf_statement
from ingestion.excel_reader import read_excel_statement, read_csv_statement
from ingestion.word_reader import read_word_statement
from ingestion.image_ocr import read_image_statement
from normalization.schema_mapper import NORMALIZED_COLUMNS

def ingest_statement(
    file_path_or_bytes: any,
    filename: str = "",
    password: Optional[str] = None
) -> pd.DataFrame:
    """
    Auto-detect format and ingest a single statement into a normalized DataFrame.
    """
    fname = filename or (file_path_or_bytes if isinstance(file_path_or_bytes, str) else "statement")
    ftype = detect_file_type(file_path_or_bytes, fname)
    
    if ftype == 'pdf':
        return read_pdf_statement(file_path_or_bytes, filename=fname, password=password)
    elif ftype == 'excel':
        return read_excel_statement(file_path_or_bytes, filename=fname)
    elif ftype == 'csv':
        return read_csv_statement(file_path_or_bytes, filename=fname)
    elif ftype == 'word':
        return read_word_statement(file_path_or_bytes, filename=fname)
    elif ftype == 'image':
        return read_image_statement(file_path_or_bytes, filename=fname)
    else:
        # Fallback: try image OCR first if it might be an image without standard extension, then excel
        try:
            df = read_image_statement(file_path_or_bytes, filename=fname)
            if not df.empty:
                return df
        except Exception:
            pass
        try:
            df = read_excel_statement(file_path_or_bytes, filename=fname)
            if not df.empty:
                return df
        except Exception:
            pass
        return pd.DataFrame(columns=NORMALIZED_COLUMNS)

def ingest_multiple_statements_with_diagnostics(
    file_inputs: List[Dict[str, Any]]
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Ingest multiple statement files in batch mode with detailed per-file diagnostic logs.
    """
    dfs = []
    diagnostics = []

    for item in file_inputs:
        f = item.get("file")
        fname = item.get("filename", "statement")
        pwd = item.get("password", None)
        ftype = detect_file_type(f, fname)
        
        try:
            df = ingest_statement(f, filename=fname, password=pwd)
            if not df.empty:
                dfs.append(df)
                bank_detected = df["source_bank"].iloc[0] if "source_bank" in df.columns else "Generic Bank"
                diagnostics.append({
                    "filename": fname,
                    "format": ftype.upper(),
                    "status": "SUCCESS",
                    "rows_extracted": len(df),
                    "bank": bank_detected,
                    "message": f"Successfully parsed {len(df)} transactions ({bank_detected})."
                })
            else:
                msg = "No transactions could be parsed. Check if file contains tabular entries or valid password."
                if ftype == 'pdf' and check_pdf_encrypted(f) and not pwd:
                    msg = "PDF is password-protected. Please enter the password in the sidebar."
                diagnostics.append({
                    "filename": fname,
                    "format": ftype.upper(),
                    "status": "FAILED",
                    "rows_extracted": 0,
                    "bank": "Unknown",
                    "message": msg
                })
        except Exception as e:
            diagnostics.append({
                "filename": fname,
                "format": ftype.upper(),
                "status": "ERROR",
                "rows_extracted": 0,
                "bank": "Unknown",
                "message": f"Error: {str(e)}"
            })

    if not dfs:
        return pd.DataFrame(columns=NORMALIZED_COLUMNS), diagnostics

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.sort_values(by=["transaction_date", "source_file"], ascending=[True, True]).reset_index(drop=True)
    return combined, diagnostics

def ingest_multiple_statements(
    file_inputs: List[Dict[str, Any]]
) -> pd.DataFrame:
    """Ingest multiple statement files."""
    df, _ = ingest_multiple_statements_with_diagnostics(file_inputs)
    return df
