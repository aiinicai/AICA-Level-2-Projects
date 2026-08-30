"""
Excel parser for Red Flag Engine.
Supports Long, Wide, and Multi-sheet layouts, plus Tally-specific export quirks.
"""
import re
from typing import Dict, List, Optional, Tuple, Union, BinaryIO
import openpyxl
import pandas as pd
import numpy as np

def parse_amount_str(val) -> Tuple[float, Optional[str]]:
    """
    Parse a numeric or text amount string into a float and an optional sign hint ('Dr', 'Cr').
    Handles:
    - 12345.67 -> (12345.67, None)
    - "1,23,456.78 Dr" -> (123456.78, 'Dr')
    - "1,234 Cr" -> (1234.0, 'Cr')
    - "(1,234)" -> (-1234.0, None)
    - "-1234" -> (-1234.0, None)
    """
    if pd.isna(val) or val is None or val == "":
        return 0.0, None
    if isinstance(val, (int, float)):
        return float(val), None
        
    s = str(val).strip()
    if not s:
        return 0.0, None
        
    # Check trailing Dr / Cr
    hint = None
    if re.search(r'\bdr\.?$', s, re.IGNORECASE):
        hint = 'Dr'
        s = re.sub(r'\bdr\.?$', '', s, flags=re.IGNORECASE).strip()
    elif re.search(r'\bcr\.?$', s, re.IGNORECASE):
        hint = 'Cr'
        s = re.sub(r'\bcr\.?$', '', s, flags=re.IGNORECASE).strip()
        
    # Check parentheses for negative numbers e.g. (1,234.50)
    is_paren_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_paren_negative = True
        s = s[1:-1].strip()
        
    # Remove commas and spaces
    s = s.replace(",", "").replace(" ", "").replace("₹", "").replace("Rs.", "").replace("Rs", "")
    
    try:
        num = float(s)
        if is_paren_negative:
            num = -abs(num)
        return num, hint
    except ValueError:
        return 0.0, None

def normalise_fy_str(sheet_or_col_name: str) -> Optional[str]:
    """
    Normalise strings like 'FY22', '2021-22', '2021-2022', 'FY 2022-23', '2024' -> 'FY22', 'FY23', 'FY24'.
    """
    s = str(sheet_or_col_name).strip()
    # Match FY22, FY 2022, FY2022
    m = re.search(r'fy\s*(\d{2,4})', s, re.IGNORECASE)
    if m:
        digits = m.group(1)
        if len(digits) == 4:
            return f"FY{digits[2:]}"
        return f"FY{digits}"
        
    # Match 2021-22, 2021-2022
    m2 = re.search(r'20(\d{2})[-/](\d{2,4})', s)
    if m2:
        return f"FY{m2.group(2)[-2:]}"
        
    # Match 4-digit year e.g. 2024 -> FY24
    m3 = re.search(r'20(\d{2})', s)
    if m3:
        return f"FY{m3.group(1)}"
        
    return None

def is_subtotal_or_header_row(name: str) -> bool:
    """Check if row is a Grand Total, Subtotal, or Header relic."""
    if not isinstance(name, str):
        return False
    s = name.strip().lower()
    return bool(re.search(r'^(grand\s+)?total\b|^total\b|^opening\b|^closing\b|^particulars\b|^ledger\s+name\b', s))

def find_header_row(df_raw: pd.DataFrame) -> int:
    """
    Locate the true header row by finding the row containing >= 3 expected column keywords.
    """
    expected_keywords = {"ledger", "particular", "group", "fy", "year", "opening", "debit", "credit", "closing", "turnover", "dr", "cr", "balance"}
    for idx, row in df_raw.head(10).iterrows():
        matches = 0
        for cell in row:
            if pd.isna(cell):
                continue
            words = str(cell).lower().split()
            if any(w in expected_keywords or any(k in w for k in expected_keywords) for w in words):
                matches += 1
        if matches >= 3:
            return idx
    return 0

def parse_excel(file_source: Union[str, BinaryIO, bytes]) -> pd.DataFrame:
    """
    Parse an Excel workbook (.xlsx or .xls) into a standardized raw DataFrame.
    Detects Long, Multi-sheet, or Wide layouts.
    """
    excel_file = pd.ExcelFile(file_source)
    sheet_names = excel_file.sheet_names
    
    # 1. Multi-sheet layout check:
    # Check if multiple sheets look like financial years (e.g. FY22, FY23, FY24)
    fy_sheets = []
    for sh in sheet_names:
        norm_fy = normalise_fy_str(sh)
        if norm_fy:
            fy_sheets.append((sh, norm_fy))
            
    if len(fy_sheets) >= 2:
        # Multi-sheet mode
        combined_dfs = []
        for orig_sheet, norm_fy in fy_sheets:
            df_sheet = excel_file.parse(orig_sheet, header=None)
            header_idx = find_header_row(df_sheet)
            df_sheet.columns = df_sheet.iloc[header_idx]
            df_sheet = df_sheet.iloc[header_idx + 1:].reset_index(drop=True)
            df_sheet["fy"] = norm_fy
            combined_dfs.append(df_sheet)
        raw_df = pd.concat(combined_dfs, ignore_index=True)
        return standardize_parsed_df(raw_df)
        
    # 2. Single sheet or primary sheet
    target_sheet = sheet_names[0]
    for sh in sheet_names:
        if "trial" in sh.lower() or "tb" in sh.lower() or "data" in sh.lower() or "long" in sh.lower():
            target_sheet = sh
            break
            
    df_raw = excel_file.parse(target_sheet, header=None)
    header_idx = find_header_row(df_raw)
    df_raw.columns = df_raw.iloc[header_idx]
    df_raw = df_raw.iloc[header_idx + 1:].reset_index(drop=True)
    
    return standardize_parsed_df(df_raw)

def standardize_parsed_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map raw column names into canonical names and parse text numbers.
    Handles wide-to-long unpivoting if needed.
    """
    # Clean column headers
    clean_cols = [str(c).strip() if pd.notna(c) else f"col_{i}" for i, c in enumerate(df.columns)]
    df.columns = clean_cols
    
    # Drop completely empty columns & rows
    df = df.dropna(how="all").dropna(axis=1, how="all")
    
    # Check for Wide layout: repeating period blocks e.g. FY22 Closing, FY23 Closing
    wide_fy_matches = set()
    for col in df.columns:
        m = normalise_fy_str(col)
        if m:
            wide_fy_matches.add(m)
            
    if len(wide_fy_matches) >= 2 and not any(col.lower() in ["fy", "financial year", "year", "period"] for col in df.columns):
        # Melt wide format to long
        return melt_wide_df(df, wide_fy_matches)
        
    # Standard column mapping
    col_map = {}
    for col in df.columns:
        c_low = col.lower().replace("_", " ").replace(".", "")
        if c_low in ["financial year", "year", "period", "fy"]:
            col_map[col] = "fy"
        elif c_low in ["ledger name", "ledger", "particulars", "account name", "name"]:
            col_map[col] = "ledger_name"
        elif c_low in ["group", "primary group", "schedule iii group", "group name", "head"]:
            col_map[col] = "group"
        elif c_low in ["sub group", "subgroup", "secondary group"]:
            col_map[col] = "sub_group"
        elif "opening" in c_low and "dr" in c_low:
            col_map[col] = "opening_dr"
        elif "opening" in c_low and "cr" in c_low:
            col_map[col] = "opening_cr"
        elif ("turnover" in c_low or "debit" in c_low) and ("dr" in c_low or "debit" in c_low) and "closing" not in c_low and "opening" not in c_low:
            col_map[col] = "turnover_dr"
        elif ("turnover" in c_low or "credit" in c_low) and ("cr" in c_low or "credit" in c_low) and "closing" not in c_low and "opening" not in c_low:
            col_map[col] = "turnover_cr"
        elif "closing" in c_low and "dr" in c_low:
            col_map[col] = "closing_dr"
        elif "closing" in c_low and "cr" in c_low:
            col_map[col] = "closing_cr"
        elif "opening" in c_low and "balance" in c_low:
            col_map[col] = "opening_balance_raw"
        elif "closing" in c_low and "balance" in c_low:
            col_map[col] = "closing_balance_raw"
            
    df = df.rename(columns=col_map)
    return df

def melt_wide_df(df: pd.DataFrame, fys: set) -> pd.DataFrame:
    """Melt wide Tally comparative export into long DataFrame."""
    # Find ledger name and group columns
    name_col = next((c for c in df.columns if any(k in c.lower() for k in ["ledger", "particular", "name"])), df.columns[0])
    group_col = next((c for c in df.columns if "group" in c.lower()), None)
    
    records = []
    current_group = "Unclassified"
    
    for _, row in df.iterrows():
        raw_name = str(row[name_col]) if pd.notna(row[name_col]) else ""
        if not raw_name.strip() or is_subtotal_or_header_row(raw_name):
            continue
            
        # Check indentation for group hierarchy
        leading_spaces = len(raw_name) - len(raw_name.lstrip())
        name = raw_name.strip()
        
        grp = row[group_col] if group_col and pd.notna(row[group_col]) else None
        if grp is None:
            if leading_spaces == 0:
                current_group = name
            grp = current_group
            
        for fy in sorted(fys):
            # Extract columns for this FY
            fy_cols = [c for c in df.columns if fy.lower() in c.lower() or fy[-2:] in c.lower()]
            op_dr, op_cr, t_dr, t_cr, cl_dr, cl_cr = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
            
            for c in fy_cols:
                val, hint = parse_amount_str(row[c])
                c_low = c.lower()
                if "opening" in c_low:
                    if hint == "Cr" or "cr" in c_low:
                        op_cr = val
                    else:
                        op_dr = val
                elif "turnover" in c_low or "debit" in c_low or "credit" in c_low:
                    if hint == "Cr" or "cr" in c_low:
                        t_cr = val
                    else:
                        t_dr = val
                elif "closing" in c_low or "balance" in c_low:
                    if hint == "Cr" or "cr" in c_low:
                        cl_cr = val
                    else:
                        cl_dr = val
                        
            records.append({
                "fy": fy,
                "ledger_name": name,
                "group": grp,
                "sub_group": None,
                "opening_dr": op_dr,
                "opening_cr": op_cr,
                "turnover_dr": t_dr,
                "turnover_cr": t_cr,
                "closing_dr": cl_dr,
                "closing_cr": cl_cr
            })
            
    return pd.DataFrame(records)
