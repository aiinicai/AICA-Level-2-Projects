"""Excel and CSV Bank Statement Reader."""

import os
import io
import pandas as pd
from typing import Tuple, Optional, List
from rapidfuzz import process, fuzz

from normalization.schema_mapper import (
    normalize_dataframe, load_bank_templates, detect_bank_from_header_text, extract_account_number
)

HEADER_INDICATOR_KEYWORDS = ["date", "particular", "narration", "description", "debit", "credit", "withdrawal", "deposit", "balance"]

def find_table_header_row(df_raw: pd.DataFrame, max_scan_rows: int = 35) -> Tuple[int, List[str]]:
    """
    Scan top rows of an Excel/CSV dataframe to locate the table column header row.
    Returns (header_row_index, list_of_column_names).
    """
    best_row_idx = 0
    max_score = 0
    
    rows_to_scan = min(len(df_raw), max_scan_rows)
    for i in range(rows_to_scan):
        row_vals = [str(x).lower().strip() for x in df_raw.iloc[i].values if pd.notna(x)]
        if not row_vals:
            continue
            
        score = 0
        for kw in HEADER_INDICATOR_KEYWORDS:
            if any(kw in v for v in row_vals):
                score += 1
                
        if score > max_score and score >= 3:
            max_score = score
            best_row_idx = i
            
    if max_score >= 3:
        headers = [str(x).strip() if pd.notna(x) else f"col_{idx}" for idx, x in enumerate(df_raw.iloc[best_row_idx].values)]
        return best_row_idx, headers
        
    return 0, [str(c) for c in df_raw.columns]

def read_excel_statement(
    file_path_or_bytes: any,
    filename: str = "",
    sheet_name: Optional[any] = 0
) -> pd.DataFrame:
    """
    Read an Excel (.xlsx, .xls) bank statement file and return a normalized DataFrame.
    """
    templates = load_bank_templates()
    fname = filename or (file_path_or_bytes if isinstance(file_path_or_bytes, str) else "statement.xlsx")
    
    # Read raw content without headers
    try:
        if isinstance(file_path_or_bytes, (bytes, bytearray)):
            df_raw = pd.read_excel(io.BytesIO(file_path_or_bytes), sheet_name=sheet_name, header=None)
        else:
            df_raw = pd.read_excel(file_path_or_bytes, sheet_name=sheet_name, header=None)
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return pd.DataFrame()
        
    if df_raw.empty:
        return pd.DataFrame()
        
    # Extract metadata text from header rows above table
    header_idx, headers = find_table_header_row(df_raw)
    
    metadata_text = ""
    if header_idx > 0:
        meta_rows = df_raw.iloc[:header_idx].values.flatten()
        metadata_text = " ".join([str(m).strip() for m in meta_rows if pd.notna(m) and str(m).strip() not in ("nan", "None", "")])
        
    bank_name, bank_tmpl = detect_bank_from_header_text(metadata_text, templates)
    account_no = extract_account_number(metadata_text)
    
    # Extract transaction data
    df_data = df_raw.iloc[header_idx + 1:].copy()
    df_data.columns = headers
    
    # Remove all-NA rows
    df_data = df_data.dropna(how="all")
    
    return normalize_dataframe(
        df_data,
        source_file=fname,
        source_bank=bank_name,
        account_number=account_no,
        bank_template=bank_tmpl
    )

def read_csv_statement(
    file_path_or_bytes: any,
    filename: str = ""
) -> pd.DataFrame:
    """
    Read a CSV bank statement file and return a normalized DataFrame.
    """
    templates = load_bank_templates()
    fname = filename or (file_path_or_bytes if isinstance(file_path_or_bytes, str) else "statement.csv")
    
    try:
        if isinstance(file_path_or_bytes, (bytes, bytearray)):
            # Try utf-8 first, fallback to latin-1
            try:
                df_raw = pd.read_csv(io.BytesIO(file_path_or_bytes), header=None, encoding='utf-8')
            except Exception:
                df_raw = pd.read_csv(io.BytesIO(file_path_or_bytes), header=None, encoding='latin-1')
        else:
            try:
                df_raw = pd.read_csv(file_path_or_bytes, header=None, encoding='utf-8')
            except Exception:
                df_raw = pd.read_csv(file_path_or_bytes, header=None, encoding='latin-1')
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return pd.DataFrame()
        
    if df_raw.empty:
        return pd.DataFrame()
        
    header_idx, headers = find_table_header_row(df_raw)
    
    metadata_text = ""
    if header_idx > 0:
        meta_rows = df_raw.iloc[:header_idx].values.flatten()
        metadata_text = " ".join([str(m).strip() for m in meta_rows if pd.notna(m) and str(m).strip() not in ("nan", "None", "")])
        
    bank_name, bank_tmpl = detect_bank_from_header_text(metadata_text, templates)
    account_no = extract_account_number(metadata_text)
    
    df_data = df_raw.iloc[header_idx + 1:].copy()
    df_data.columns = headers
    df_data = df_data.dropna(how="all")
    
    return normalize_dataframe(
        df_data,
        source_file=fname,
        source_bank=bank_name,
        account_number=account_no,
        bank_template=bank_tmpl
    )
