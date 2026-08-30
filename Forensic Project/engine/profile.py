"""
Data Profiling and Quality Assessment module for Red Flag Engine.
Evaluates Dr = Cr balance, opening balance completeness, group coverage.
"""
from typing import Dict, List, Any
import pandas as pd
import numpy as np

def profile_trial_balance(ledgers: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate a data quality and profile report for the canonical `ledgers` DataFrame.
    """
    fys = sorted(ledgers["fy"].unique())
    fy_reports = []
    
    overall_balanced = True
    has_all_opening = True
    
    for fy in fys:
        df_fy = ledgers[ledgers["fy"] == fy]
        
        tot_cl_dr = float(df_fy["closing_dr"].sum())
        tot_cl_cr = float(df_fy["closing_cr"].sum())
        cl_diff = abs(tot_cl_dr - tot_cl_cr)
        cl_balanced = cl_diff < 1.0
        
        tot_op_dr = float(df_fy["opening_dr"].sum())
        tot_op_cr = float(df_fy["opening_cr"].sum())
        op_diff = abs(tot_op_dr - tot_op_cr)
        has_op = (tot_op_dr > 0 or tot_op_cr > 0)
        op_balanced = (op_diff < 1.0) if has_op else False
        
        if not cl_balanced:
            overall_balanced = False
        if not has_op:
            has_all_opening = False
            
        unclassified_count = int((df_fy["group"].str.lower() == "unclassified").sum())
        zero_bal_count = int(((df_fy["closing_dr"] == 0) & (df_fy["closing_cr"] == 0)).sum())
        
        fy_reports.append({
            "fy": fy,
            "ledger_count": len(df_fy),
            "closing_dr_sum": tot_cl_dr,
            "closing_cr_sum": tot_cl_cr,
            "closing_difference": cl_diff,
            "closing_balanced": cl_balanced,
            "opening_dr_sum": tot_op_dr,
            "opening_cr_sum": tot_op_cr,
            "opening_difference": op_diff,
            "has_opening_balances": has_op,
            "opening_balanced": op_balanced,
            "groups_count": df_fy["group"].nunique(),
            "unclassified_count": unclassified_count,
            "zero_balance_count": zero_bal_count
        })
        
    return {
        "financial_years": fys,
        "num_years": len(fys),
        "total_rows": len(ledgers),
        "distinct_ledgers": ledgers["ledger_name"].nunique(),
        "overall_closing_balanced": overall_balanced,
        "has_all_opening_balances": has_all_opening,
        "fy_reports": fy_reports
    }
