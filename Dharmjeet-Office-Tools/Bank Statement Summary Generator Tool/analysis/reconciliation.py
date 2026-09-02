"""Reconciliation and Running Balance Validation Module."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple

def validate_running_balances(df: pd.DataFrame, tolerance: float = 0.05) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Validate running balance consistency:
    Balance[i] == Balance[i-1] + Credit[i] - Debit[i]
    
    Returns:
        (df_with_reconciliation_flags, reconciliation_summary)
    """
    if df is None or df.empty:
        return df, {
            "status": "NO_DATA",
            "total_accounts": 0,
            "discrepancies_found": 0,
            "accounts_summary": []
        }

    df_out = df.copy()
    if "reconciliation_error" not in df_out.columns:
        df_out["reconciliation_error"] = False
        df_out["expected_balance"] = 0.0
        df_out["balance_difference"] = 0.0

    accounts_summary = []
    total_discrepancies = 0

    # Group by account number or source file
    groupby_cols = ["source_file", "account_number"] if "account_number" in df_out.columns else ["source_file"]
    
    for (src_file, acc_no), group in df_out.groupby(["source_file", "account_number"]):
        group_sorted = group.sort_values(by="transaction_date", ascending=True)
        indices = group_sorted.index.tolist()
        
        if len(indices) < 2:
            accounts_summary.append({
                "source_file": src_file,
                "account_number": acc_no,
                "opening_balance": group_sorted.iloc[0]["balance"] if len(indices) > 0 else 0.0,
                "closing_balance": group_sorted.iloc[-1]["balance"] if len(indices) > 0 else 0.0,
                "total_credits": group_sorted["credit_amount"].sum(),
                "total_debits": group_sorted["debit_amount"].sum(),
                "discrepancies": 0,
                "status": "RECONCILED"
            })
            continue

        acc_discrepancies = 0
        first_row = group_sorted.iloc[0]
        # Infer opening balance before first transaction
        inferred_opening = first_row["balance"] - first_row["credit_amount"] + first_row["debit_amount"]
        prev_balance = first_row["balance"]

        for idx in indices[1:]:
            row = df_out.loc[idx]
            cr = float(row["credit_amount"] or 0.0)
            dr = float(row["debit_amount"] or 0.0)
            actual_bal = float(row["balance"] or 0.0)
            
            # If bank statement provides balance column
            if actual_bal > 0 or row["balance"] == 0:
                expected_bal = prev_balance + cr - dr
                diff = abs(actual_bal - expected_bal)
                
                df_out.loc[idx, "expected_balance"] = round(expected_bal, 2)
                df_out.loc[idx, "balance_difference"] = round(diff, 2)
                
                if diff > tolerance:
                    df_out.loc[idx, "reconciliation_error"] = True
                    acc_discrepancies += 1
                    total_discrepancies += 1
                    
                prev_balance = actual_bal
            else:
                prev_balance = prev_balance + cr - dr

        closing_row = group_sorted.iloc[-1]
        accounts_summary.append({
            "source_file": src_file,
            "account_number": acc_no,
            "opening_balance": round(inferred_opening, 2),
            "closing_balance": round(float(closing_row["balance"] or 0.0), 2),
            "total_credits": round(float(group_sorted["credit_amount"].sum()), 2),
            "total_debits": round(float(group_sorted["debit_amount"].sum()), 2),
            "discrepancies": acc_discrepancies,
            "status": "DISCREPANCIES_FOUND" if acc_discrepancies > 0 else "RECONCILED"
        })

    summary = {
        "status": "DISCREPANCIES_FOUND" if total_discrepancies > 0 else "RECONCILED",
        "total_accounts": len(accounts_summary),
        "discrepancies_found": total_discrepancies,
        "accounts_summary": accounts_summary
    }

    return df_out, summary
