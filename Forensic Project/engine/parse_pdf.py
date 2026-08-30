"""
PDF parser for Red Flag Engine.
Extracts structured trial balance tables from text-based PDFs using pdfplumber and camelot.
Raises ScannedPDFError for non-text or image-only scanned PDFs.
"""
import io
import os
from typing import BinaryIO, Union
import pandas as pd
import pdfplumber

class ScannedPDFError(Exception):
    """Raised when a PDF contains scanned images or lacks extractable digital text."""
    pass

def parse_pdf(file_source: Union[str, BinaryIO, bytes]) -> pd.DataFrame:
    """
    Extract trial balance data from a PDF document.
    Attempts table extraction via pdfplumber, falling back to camelot-py.
    Raises ScannedPDFError if no extractable text is found.
    """
    if isinstance(file_source, bytes):
        pdf_stream = io.BytesIO(file_source)
    elif isinstance(file_source, str):
        with open(file_source, "rb") as f:
            pdf_stream = io.BytesIO(f.read())
    else:
        pdf_stream = file_source

    # Check for extractable text across pages using pdfplumber
    pdf_stream.seek(0)
    all_tables = []
    has_any_text = False
    
    with pdfplumber.open(pdf_stream) as pdf:
        if len(pdf.pages) == 0:
            raise ScannedPDFError("This PDF contains images, not text. Please supply the trial balance as Excel, or use the template in templates/.")
            
        for page in pdf.pages:
            text = page.extract_text()
            if text and len(text.strip()) > 10:
                has_any_text = True
                
            # Extract tables
            tables = page.extract_tables()
            for t in tables:
                if t and len(t) > 1:
                    df_t = pd.DataFrame(t[1:], columns=t[0])
                    all_tables.append(df_t)

    if not has_any_text:
        raise ScannedPDFError("This PDF contains images, not text. Please supply the trial balance as Excel, or use the template in templates/.")

    if all_tables:
        combined = pd.concat(all_tables, ignore_index=True)
        from engine.parse_excel import standardize_parsed_df
        return standardize_parsed_df(combined)

    # Fallback to camelot if pdfplumber didn't find structured tables
    if isinstance(file_source, str):
        try:
            import camelot
            tables = camelot.read_pdf(file_source, flavor="stream", pages="all")
            if len(tables) > 0:
                df_list = [t.df for t in tables]
                combined = pd.concat(df_list, ignore_index=True)
                from engine.parse_excel import standardize_parsed_df
                return standardize_parsed_df(combined)
        except Exception:
            pass

    raise ScannedPDFError("This PDF contains images, not text. Please supply the trial balance as Excel, or use the template in templates/.")
