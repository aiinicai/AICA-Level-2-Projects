"""
Data normalisation module for Red Flag Engine.
Converts raw parsed DataFrames into the canonical `ledgers` schema.
"""
import re
from typing import Optional
import pandas as pd
import numpy as np
from engine.parse_excel import parse_amount_str, is_subtotal_or_header_row, normalise_fy_str

def normalise_ledgers(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise any raw parsed trial balance DataFrame into the canonical `ledgers` schema.
    """
    df = df_raw.copy()
    
    # 1. Check essential columns or provide fallbacks
    if "ledger_name" not in df.columns:
        # Find first string-like column
        for col in df.columns:
            if df[col].dtype == object:
                df = df.rename(columns={col: "ledger_name"})
                break
                
    if "group" not in df.columns:
        df["group"] = "Unclassified"
        
    if "sub_group" not in df.columns:
        df["sub_group"] = None
        
    if "fy" not in df.columns:
        df["fy"] = "FY24"
    else:
        df["fy"] = df["fy"].apply(lambda x: normalise_fy_str(x) or str(x).strip())
        
    # Drop rows without ledger name or subtotal / grand total rows
    df = df[df["ledger_name"].notna()]
    df["ledger_name"] = df["ledger_name"].astype(str).str.strip()
    df = df[~df["ledger_name"].apply(is_subtotal_or_header_row)]
    df = df[df["ledger_name"] != ""]
    
    # 2. Fill and parse numeric columns
    num_cols = ["opening_dr", "opening_cr", "turnover_dr", "turnover_cr", "closing_dr", "closing_cr"]
    for col in num_cols:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = df[col].apply(lambda v: parse_amount_str(v)[0])
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            
    # Handle raw balance columns if present e.g. opening_balance_raw, closing_balance_raw
    if "closing_balance_raw" in df.columns:
        for idx, row in df.iterrows():
            if row["closing_dr"] == 0.0 and row["closing_cr"] == 0.0:
                val, hint = parse_amount_str(row["closing_balance_raw"])
                if hint == "Cr" or val < 0:
                    df.at[idx, "closing_cr"] = abs(val)
                else:
                    df.at[idx, "closing_dr"] = abs(val)
                    
    if "opening_balance_raw" in df.columns:
        for idx, row in df.iterrows():
            if row["opening_dr"] == 0.0 and row["opening_cr"] == 0.0:
                val, hint = parse_amount_str(row["opening_balance_raw"])
                if hint == "Cr" or val < 0:
                    df.at[idx, "opening_cr"] = abs(val)
                else:
                    df.at[idx, "opening_dr"] = abs(val)

    # 3. Fill missing group values via forward fill if hierarchical
    df["group"] = df["group"].fillna("Unclassified").astype(str).str.strip()
    df.loc[df["group"] == "", "group"] = "Unclassified"
    
    if "sub_group" in df.columns:
        df["sub_group"] = df["sub_group"].apply(lambda x: str(x).strip() if pd.notna(x) and str(x).strip() != "" else None)

    # 4. Compute derived helper columns
    df["closing_net"] = df["closing_dr"] - df["closing_cr"]
    df["opening_net"] = df["opening_dr"] - df["opening_cr"]
    df["movement"] = df["closing_net"] - df["opening_net"]
    df["turnover_total"] = df["turnover_dr"] + df["turnover_cr"]

    # Canonical column ordering
    canonical_cols = [
        "ledger_name", "group", "sub_group", "fy",
        "opening_dr", "opening_cr", "turnover_dr", "turnover_cr", "closing_dr", "closing_cr",
        "closing_net", "opening_net", "movement", "turnover_total"
    ]
    
    # Keep any extra columns at the end if present
    extra_cols = [c for c in df.columns if c not in canonical_cols]
    return df[canonical_cols + extra_cols].reset_index(drop=True)
