"""Schema Mapper for Bank Statements.
Maps varied raw bank column layouts to the standardized normalized schema.
"""

import os
import glob
import re
import yaml
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from rapidfuzz import process, fuzz

from normalization.date_utils import (
    parse_date, get_financial_year, get_fy_quarter, get_month_year, get_month_sort_key
)
from normalization.narration_parser import parse_narration

NORMALIZED_COLUMNS = [
    "transaction_date",
    "value_date",
    "description",
    "reference_no",
    "debit_amount",
    "credit_amount",
    "balance",
    "mode",
    "counterparty_name",
    "counterparty_account",
    "source_file",
    "source_bank",
    "account_number",
    "fy",
    "fy_quarter",
    "month_year",
    "month_sort_key",
    "nature",
    "is_flagged",
    "flag_reasons"
]

def load_bank_templates(templates_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load all YAML bank templates from ingestion/bank_templates/."""
    if templates_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        templates_dir = os.path.join(base_dir, "ingestion", "bank_templates")
    
    templates = []
    if os.path.exists(templates_dir):
        for yaml_file in glob.glob(os.path.join(templates_dir, "*.yaml")):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data:
                        templates.append(data)
            except Exception as e:
                print(f"Error loading template {yaml_file}: {e}")
    return templates

def clean_amount(val: Any) -> float:
    """Clean and convert string or numeric amount representations to a positive float."""
    if val is None or pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return abs(float(val)) if not np.isnan(val) else 0.0
    
    text = str(val).strip()
    if not text or text in ("-", "--", "NA", "N/A", "Nil", ""):
        return 0.0
        
    # Remove commas, currency symbols, and spaces
    text = re.sub(r'[₹$,\s]', '', text)
    # Remove 'Cr', 'Dr', 'CR', 'DR'
    text = re.sub(r'(?i)[cd]r', '', text).strip()
    # Handle parenthesis negative e.g. (100.00)
    if text.startswith('(') and text.endswith(')'):
        text = text[1:-1]
        
    try:
        return abs(float(text))
    except ValueError:
        return 0.0

def clean_col_name(c: str) -> str:
    """Standardize column header string."""
    s = str(c).lower().strip()
    s = re.sub(r'[\r\n\t]+', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s

def match_columns_to_schema(df_columns: List[str], bank_template: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    Match raw dataframe column names to standard fields:
    'date', 'value_date', 'description', 'reference_no', 'debit', 'credit', 'balance', 'type_flag'
    """
    mapping = {}
    cols_clean = [(c, clean_col_name(c)) for c in df_columns]
    
    # Priority 1: Use bank template if matched
    if bank_template and "columns" in bank_template:
        t_cols = bank_template["columns"]
        for target_field, synonyms in t_cols.items():
            for syn in synonyms:
                syn_c = clean_col_name(syn)
                for orig_col, col_c in cols_clean:
                    if col_c == syn_c or syn_c in col_c or col_c in syn_c:
                        mapping[target_field] = orig_col
                        break
                if target_field in mapping:
                    break

    # Comprehensive Indian banking synonym dictionary
    synonyms_dict = {
        "date": [
            "date", "txn date", "transaction date", "tran date", "post date",
            "trans date", "booking date", "value dt", "txn dt"
        ],
        "value_date": [
            "value date", "val date", "value dt", "effective date", "v date"
        ],
        "description": [
            "narration", "particulars", "description", "remarks", "transaction details",
            "details", "transaction remarks", "transaction particulars", "particular"
        ],
        "reference_no": [
            "cheque no", "chq no", "ref no", "reference no", "cheque / ref no",
            "chq/ref no", "utr", "txn id", "journal no", "chq / ref no.", "chq/ref no.",
            "cheque number", "ref/cheque no."
        ],
        "debit": [
            "debit", "withdrawal", "withdrawal (dr)", "withdrawal amount", "debit amount",
            "withdrawal amt.", "withdrawal amt", "dr", "dr.", "debits", "paid out",
            "amount (dr)", "withdrawal (dr.)", "debit (inr)", "dr amount", "withdrawals"
        ],
        "credit": [
            "credit", "deposit", "deposit (cr)", "deposit amount", "credit amount",
            "deposit amt.", "deposit amt", "cr", "cr.", "credits", "paid in",
            "amount (cr)", "deposit (cr.)", "credit (inr)", "cr amount", "deposits"
        ],
        "balance": [
            "balance", "closing balance", "running balance", "available balance",
            "account balance", "closing bal", "net balance", "balance (inr)", "closing balance (inr)"
        ],
        "type_flag": [
            "type", "cr/dr", "dr/cr", "txn type", "indicator", "d/c", "cr / dr", "dr / cr"
        ]
    }
    
    for target_field, syn_list in synonyms_dict.items():
        if target_field not in mapping:
            # 1. Exact or substring match
            for syn in syn_list:
                syn_c = clean_col_name(syn)
                for orig_col, col_c in cols_clean:
                    if col_c == syn_c:
                        mapping[target_field] = orig_col
                        break
                    # Clean words match (e.g. "withdrawal (dr)" matches "withdrawal")
                    col_base = re.sub(r'[\(\)\[\]\.\-_/]', ' ', col_c).strip()
                    if syn_c in col_base.split() or col_base.startswith(syn_c):
                        mapping[target_field] = orig_col
                        break
                if target_field in mapping:
                    break
                    
            # 2. Fuzzy match fallback
            if target_field not in mapping:
                for orig_col, col_c in cols_clean:
                    best_match = process.extractOne(col_c, syn_list, scorer=fuzz.token_sort_ratio)
                    if best_match and best_match[1] >= 75:
                        mapping[target_field] = orig_col
                        break

    return mapping

def detect_bank_from_header_text(header_text: str, templates: List[Dict[str, Any]]) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Detect which bank the statement belongs to using header text and loaded templates."""
    if not header_text:
        return "Unknown Bank", None
    
    upper_text = header_text.upper()
    for tmpl in templates:
        for kw in tmpl.get("identifier_keywords", []):
            if kw.upper() in upper_text:
                return tmpl.get("bank_name", "Unknown Bank"), tmpl
                
    return "Generic Bank", None

def extract_account_number(text: str) -> str:
    """Extract account number from text (e.g., 'Account No: 123456789012' or masked 'XXXXXXXX1234')."""
    if not text:
        return "Not Identified"
    
    # Check for Account No patterns
    m = re.search(r'(?:account\s*no|a\/c\s*no|acc\s*no|account\s*number)[\s\:\-]+([X\d]{8,20})', text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
        
    # Check for standalone 11 to 18 digits or masked account numbers
    m_mask = re.search(r'\b(X{4,}[0-9]{3,6})\b', text, re.IGNORECASE)
    if m_mask:
        return m_mask.group(1)
        
    return "Not Identified"

def normalize_dataframe(
    df: pd.DataFrame,
    source_file: str = "",
    source_bank: str = "Generic Bank",
    account_number: str = "Not Identified",
    bank_template: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Normalize raw dataframe into standard schema.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=NORMALIZED_COLUMNS)
    
    # Detect column mapping
    col_map = match_columns_to_schema(df.columns.tolist(), bank_template)
    
    records = []
    prev_balance = 0.0
    
    for idx, row in df.iterrows():
        # Date extraction
        raw_date = row.get(col_map.get("date", ""), None) if "date" in col_map else None
        txn_date = parse_date(raw_date)
        
        # If no date found in this row, check if it's an empty or continuation row
        if not txn_date:
            continue
            
        raw_val_date = row.get(col_map.get("value_date", ""), None) if "value_date" in col_map else None
        val_date = parse_date(raw_val_date) or txn_date
        
        # Description / Narration
        narration = str(row.get(col_map.get("description", ""), "")).strip()
        if narration in ("nan", "None", ""):
            narration = ""
            
        # Reference No
        ref_no = str(row.get(col_map.get("reference_no", ""), "")).strip()
        if ref_no in ("nan", "None", "-"):
            ref_no = ""
            
        # Amount extraction
        debit_amt = 0.0
        credit_amt = 0.0
        
        if "debit" in col_map and "credit" in col_map:
            debit_amt = clean_amount(row.get(col_map["debit"]))
            credit_amt = clean_amount(row.get(col_map["credit"]))
        elif "debit" in col_map and "type_flag" in col_map:
            amt = clean_amount(row.get(col_map["debit"]))
            flag = str(row.get(col_map["type_flag"], "")).upper().strip()
            if "DR" in flag or "DEBIT" in flag or "WDL" in flag:
                debit_amt = amt
            else:
                credit_amt = amt
        elif "debit" in col_map:
            amt_raw = row.get(col_map["debit"])
            amt = clean_amount(amt_raw)
            if str(amt_raw).strip().startswith('-') or 'DR' in str(amt_raw).upper():
                debit_amt = amt
            else:
                credit_amt = amt
                
        # Running Balance
        balance = 0.0
        if "balance" in col_map:
            balance = clean_amount(row.get(col_map["balance"]))
            if balance > 0:
                prev_balance = balance
        else:
            # Approximate running balance if not provided
            balance = prev_balance + credit_amt - debit_amt
            prev_balance = balance
            
        # Parse narration for mode, party, handles
        parsed_n = parse_narration(narration)
        final_mode = parsed_n["mode"]
        counterparty_name = parsed_n["counterparty_name"]
        counterparty_account = parsed_n["counterparty_vpa"]
        if not ref_no and parsed_n["reference_no"]:
            ref_no = parsed_n["reference_no"]
            
        # Date breakdowns
        fy = get_financial_year(txn_date)
        fy_quarter = get_fy_quarter(txn_date)
        month_yr = get_month_year(txn_date)
        m_sort = get_month_sort_key(txn_date)
        
        records.append({
            "transaction_date": txn_date,
            "value_date": val_date,
            "description": narration,
            "reference_no": ref_no,
            "debit_amount": debit_amt,
            "credit_amount": credit_amt,
            "balance": balance,
            "mode": final_mode,
            "counterparty_name": counterparty_name,
            "counterparty_account": counterparty_account,
            "source_file": os.path.basename(source_file) if source_file else "",
            "source_bank": source_bank,
            "account_number": account_number,
            "fy": fy,
            "fy_quarter": fy_quarter,
            "month_year": month_yr,
            "month_sort_key": m_sort,
            "nature": "Unidentified Credit" if credit_amt > 0 else "Unidentified Debit",
            "is_flagged": False,
            "flag_reasons": []
        })
        
    res_df = pd.DataFrame(records, columns=NORMALIZED_COLUMNS)
    return res_df
