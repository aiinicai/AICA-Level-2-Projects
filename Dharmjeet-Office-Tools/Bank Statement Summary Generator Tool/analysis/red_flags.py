"""Red Flag and Tax Scrutiny Anomaly Detection Module."""

import os
import yaml
import pandas as pd
import numpy as np
from datetime import timedelta
from typing import Dict, Any, List, Optional, Tuple

from classification.profile_manager import load_client_profile

DEFAULT_THRESHOLDS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "thresholds.yaml"
)

def load_thresholds(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load red flag thresholds from YAML."""
    path = config_path or DEFAULT_THRESHOLDS_PATH
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data.get("thresholds", {}) if data else {}
        except Exception as e:
            print(f"Error loading thresholds: {e}")
    return {}

def detect_red_flags(
    df: pd.DataFrame,
    client_name: Optional[str] = None,
    thresholds_path: Optional[str] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Scan transactions for tax scrutiny anomalies and compliance red flags.
    Updates df with 'is_flagged' and 'flag_reasons'.
    Returns (enriched_df, red_flag_summary).
    """
    if df is None or df.empty:
        return df, {
            "total_flagged_transactions": 0,
            "total_flagged_amount": 0.0,
            "categories_summary": {},
            "flagged_items": []
        }

    thresh = load_thresholds(thresholds_path)
    client_profile = load_client_profile(client_name) if client_name else {}
    custom_th = client_profile.get("custom_thresholds", {})

    # Extract threshold parameters
    single_cash_th = custom_th.get("single_cash_deposit_threshold", thresh.get("single_cash_deposit_threshold", 50000.0))
    sft_savings_th = custom_th.get("aggregate_savings_cash_deposit_fy", thresh.get("aggregate_savings_cash_deposit_fy", 1000000.0))
    sft_current_th = custom_th.get("aggregate_current_cash_deposit_fy", thresh.get("aggregate_current_cash_deposit_fy", 5000000.0))
    struct_lower = thresh.get("structuring_lower_bound", 40000.0)
    struct_upper = thresh.get("structuring_upper_bound", 49999.0)
    sec_269ss_th = thresh.get("sec_269ss_cash_loan_threshold", 20000.0)
    high_val_th = custom_th.get("high_value_transaction_threshold", thresh.get("high_value_transaction_threshold", 200000.0))
    round_multiples = thresh.get("round_figure_multiples", [50000, 100000, 500000])
    round_min_amt = thresh.get("round_figure_min_amount", 100000.0)
    reversal_days = thresh.get("reversal_window_days", 2)
    reversal_tol_pct = thresh.get("reversal_amount_tolerance_pct", 2.0)

    df_out = df.copy()
    if "is_flagged" not in df_out.columns:
        df_out["is_flagged"] = False
    if "flag_reasons" not in df_out.columns:
        df_out["flag_reasons"] = [[] for _ in range(len(df_out))]

    flag_map = {idx: [] for idx in df_out.index}

    # 1. Single Cash Deposit >= ₹50,000 (PAN Rule)
    for idx, row in df_out.iterrows():
        cr = float(row["credit_amount"] or 0.0)
        mode = str(row["mode"] or "").upper()
        nature = str(row["nature"] or "")
        
        if (mode in ("CASH", "CDM", "BNA") or nature == "Cash Deposit") and cr >= single_cash_th:
            flag_map[idx].append(f"High Cash Deposit: ₹{cr:,.2f} >= ₹{single_cash_th:,.0f} (PAN Rule 114B)")

    # 2. Section 269SS & 269T Cash Loan / Repayment >= ₹20,000
    for idx, row in df_out.iterrows():
        cr = float(row["credit_amount"] or 0.0)
        dr = float(row["debit_amount"] or 0.0)
        mode = str(row["mode"] or "").upper()
        nature = str(row["nature"] or "")
        desc = str(row["description"] or "").upper()

        if mode in ("CASH", "CDM", "BNA") or "CASH" in desc:
            if cr >= sec_269ss_th and ("LOAN" in desc or "ADVANCE" in desc or "BORROW" in desc or nature == "Loan Received"):
                flag_map[idx].append(f"Sec 269SS Violation Risk: Cash Loan Acceptance ₹{cr:,.2f} >= ₹{sec_269ss_th:,.0f}")
            if dr >= sec_269ss_th and ("LOAN" in desc or "REPAY" in desc or nature == "Loan Repayment (EMI/Principal/Interest)"):
                flag_map[idx].append(f"Sec 269T Violation Risk: Cash Loan Repayment ₹{dr:,.2f} >= ₹{sec_269ss_th:,.0f}")

    # 3. Cash Structuring / Smurfing Pattern (Deposits ₹40k - ₹49.9k within 3 consecutive days)
    cash_deposits_df = df_out[(df_out["credit_amount"] >= struct_lower) & (df_out["credit_amount"] <= struct_upper)].copy()
    if len(cash_deposits_df) >= 2:
        cash_deposits_df = cash_deposits_df.sort_values(by="transaction_date")
        indices = cash_deposits_df.index.tolist()
        for i in range(len(indices) - 1):
            idx1 = indices[i]
            idx2 = indices[i + 1]
            d1 = df_out.loc[idx1, "transaction_date"]
            d2 = df_out.loc[idx2, "transaction_date"]
            if d1 and d2 and abs((d2 - d1).days) <= 3:
                flag_map[idx1].append("Structuring Flag: Multiple cash deposits just below ₹50,000 threshold within 3 days")
                flag_map[idx2].append("Structuring Flag: Multiple cash deposits just below ₹50,000 threshold within 3 days")

    # 4. Round Figure High-Value Transactions
    for idx, row in df_out.iterrows():
        amt = max(float(row["credit_amount"] or 0.0), float(row["debit_amount"] or 0.0))
        if amt >= round_min_amt:
            for mult in round_multiples:
                if amt % mult == 0:
                    flag_map[idx].append(f"Round Figure Flag: Exact multiple of ₹{mult:,.0f} (₹{amt:,.2f})")
                    break

    # 5. Unidentified High-Value Entries
    for idx, row in df_out.iterrows():
        amt = max(float(row["credit_amount"] or 0.0), float(row["debit_amount"] or 0.0))
        nature = str(row["nature"] or "")
        if amt >= high_val_th and ("Unidentified" in nature or "Unclassified" in nature):
            flag_map[idx].append(f"High-Value Unidentified Entry: ₹{amt:,.2f} >= ₹{high_val_th:,.0f} requires CA review")

    # 6. Rapid Accommodation Entry / 2-day Reversal Pattern (Credit followed by near-identical Debit)
    credits_idx = df_out[df_out["credit_amount"] >= 50000.0].index.tolist()
    debits_idx = df_out[df_out["debit_amount"] >= 50000.0].index.tolist()
    
    for c_idx in credits_idx:
        c_row = df_out.loc[c_idx]
        c_date = c_row["transaction_date"]
        c_amt = float(c_row["credit_amount"])
        if not c_date:
            continue
            
        for d_idx in debits_idx:
            d_row = df_out.loc[d_idx]
            d_date = d_row["transaction_date"]
            d_amt = float(d_row["debit_amount"])
            if not d_date:
                continue
                
            day_diff = (d_date - c_date).days
            if 0 <= day_diff <= reversal_days:
                # Compare amounts within tolerance %
                amt_diff_pct = abs(c_amt - d_amt) / c_amt * 100.0
                if amt_diff_pct <= reversal_tol_pct:
                    flag_map[c_idx].append(f"Potential Accommodation Entry: Credit of ₹{c_amt:,.2f} followed by ₹{d_amt:,.2f} debit within {day_diff} days")
                    flag_map[d_idx].append(f"Potential Accommodation Entry: Debit of ₹{d_amt:,.2f} follows ₹{c_amt:,.2f} credit within {day_diff} days")

    # 7. SFT Aggregate Cash Deposit check (Account level / FY level)
    for (acc_no, fy), group in df_out.groupby(["account_number", "fy"]):
        cash_sum = group[group["mode"].isin(["CASH", "CDM", "BNA"]) | (group["nature"] == "Cash Deposit")]["credit_amount"].sum()
        sft_limit = sft_savings_th  # Default to savings limit
        if cash_sum >= sft_limit:
            for g_idx in group[group["mode"].isin(["CASH", "CDM", "BNA"]) | (group["nature"] == "Cash Deposit")].index:
                flag_map[g_idx].append(f"SFT Aggregate Threshold Exceeded: Total FY Cash Deposits ₹{cash_sum:,.2f} >= ₹{sft_limit:,.0f} (Rule 114E)")

    # Update DataFrame
    flagged_items = []
    total_flagged_amt = 0.0
    category_counts = {}

    for idx, reasons in flag_map.items():
        unique_reasons = list(dict.fromkeys(reasons))  # preserve order, remove duplicates
        if unique_reasons:
            df_out.at[idx, "is_flagged"] = True
            df_out.at[idx, "flag_reasons"] = unique_reasons
            
            row = df_out.loc[idx]
            amt = max(float(row["credit_amount"] or 0.0), float(row["debit_amount"] or 0.0))
            total_flagged_amt += amt
            
            for r in unique_reasons:
                cat = r.split(":")[0]
                category_counts[cat] = category_counts.get(cat, 0) + 1
                
            flagged_items.append({
                "date": str(row["transaction_date"]),
                "description": row["description"],
                "party": row["counterparty_name"],
                "mode": row["mode"],
                "debit": float(row["debit_amount"] or 0.0),
                "credit": float(row["credit_amount"] or 0.0),
                "nature": row["nature"],
                "flag_reasons": unique_reasons
            })
        else:
            df_out.at[idx, "is_flagged"] = False
            df_out.at[idx, "flag_reasons"] = []

    summary = {
        "total_flagged_transactions": len(flagged_items),
        "total_flagged_amount": round(total_flagged_amt, 2),
        "categories_summary": category_counts,
        "flagged_items": flagged_items
    }

    return df_out, summary
