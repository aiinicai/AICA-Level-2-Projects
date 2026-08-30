"""
Financial Statement Derivation module for Red Flag Engine.
Derives Balance Sheet, Profit & Loss, Indirect Cash Flow, and Financial Ratios from canonical `ledgers`.
"""
import os
from typing import Dict, List, Optional, Any
import yaml
import pandas as pd
import numpy as np

def load_group_nature(config_path: str = "config/group_nature.yaml") -> Dict[str, Any]:
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("groups", {})

def map_ledger_to_line(group: str, name: str, group_nature_map: Dict[str, Any]) -> str:
    """
    Map a ledger group & name to one of the canonical statement lines.
    """
    grp_clean = str(group).strip()
    name_clean = str(name).strip()
    
    # 1. Exact match in group_nature.yaml
    if grp_clean in group_nature_map:
        return group_nature_map[grp_clean].get("statement_line", "other_expenses")
        
    grp_lower = grp_clean.lower()
    name_lower = name_clean.lower()
    
    # 2. Case-insensitive / substring checks
    for g_key, g_val in group_nature_map.items():
        if g_key.lower() == grp_lower:
            return g_val.get("statement_line", "other_expenses")
            
    # 3. Keyword heuristic fallbacks
    if any(k in grp_lower for k in ["debtor", "receivable"]):
        return "receivables"
    if any(k in grp_lower for k in ["creditor", "payable"]):
        return "payables"
    if any(k in grp_lower for k in ["bank", "cash"]):
        return "cash"
    if any(k in grp_lower for k in ["stock", "inventor"]):
        return "inventory"
    if any(k in grp_lower for k in ["cwip", "work in progress", "work-in-progress"]):
        return "cwip"
    if any(k in grp_lower for k in ["intangible"]):
        return "intangibles"
    if any(k in grp_lower for k in ["tangible", "fixed asset", "property, plant", "gross block", "plant & machinery"]):
        return "gross_block"
    if any(k in grp_lower for k in ["accumulated dep"]):
        return "accum_depreciation"
    if any(k in grp_lower for k in ["investment"]):
        return "investments"
    if any(k in grp_lower for k in ["working capital", "cash credit", "overdraft", "short term borrow"]):
        return "wc_borrowings"
    if any(k in grp_lower for k in ["long term borrow", "secured loan", "unsecured loan", "term loan"]):
        return "lt_borrowings"
    if any(k in grp_lower for k in ["share capital", "equity capital", "capital account"]):
        return "share_capital"
    if any(k in grp_lower for k in ["reserve", "surplus"]):
        return "reserves"
    if any(k in grp_lower for k in ["sales", "revenue", "turnover", "operating income"]):
        return "revenue"
    if any(k in grp_lower for k in ["other income", "indirect income"]):
        return "other_income"
    if any(k in grp_lower for k in ["material", "cogs", "raw material", "purchase", "direct expense"]):
        return "cogs"
    if any(k in grp_lower for k in ["salary", "wage", "employee", "staff"]):
        return "employee_cost"
    if any(k in grp_lower for k in ["finance", "interest"]):
        return "finance_cost"
    if any(k in grp_lower for k in ["depreciation"]):
        return "depreciation"
    if any(k in grp_lower for k in ["tax"]):
        return "tax"
    if any(k in grp_lower for k in ["admin", "selling", "distribution", "sga", "marketing"]):
        return "sga"
    if any(k in grp_lower for k in ["current asset"]):
        return "other_current_assets"
    if any(k in grp_lower for k in ["current liab", "duties"]):
        return "other_current_liabilities"
    if any(k in grp_lower for k in ["provision"]):
        return "provisions"
    if any(k in grp_lower for k in ["loan", "advance"]):
        return "loans_advances"
        
    return "other_expenses"

def derive_financial_statements(ledgers: pd.DataFrame, params: Optional[Dict[str, Any]] = None, config_path: str = "config/group_nature.yaml") -> pd.DataFrame:
    """
    Derive the canonical `derived` table (one row per financial year).
    """
    params = params or {}
    group_nature_map = load_group_nature(config_path)
    
    fys = sorted(ledgers["fy"].unique())
    derived_rows = []
    
    related_parties = params.get("related_parties", [])
    if isinstance(related_parties, str):
        related_parties = [r.strip() for r in related_parties.split("\n") if r.strip()]
        
    for fy in fys:
        df_fy = ledgers[ledgers["fy"] == fy].copy()
        
        # Add mapped statement lines
        df_fy["line"] = df_fy.apply(lambda r: map_ledger_to_line(r["group"], r["ledger_name"], group_nature_map), axis=1)
        
        # P&L Line Items
        # Revenue from operations (Credit net or turnover_cr)
        rev_df = df_fy[df_fy["line"] == "revenue"]
        revenue = float(rev_df["closing_cr"].sum() if rev_df["closing_cr"].sum() > 0 else abs(rev_df["closing_net"].sum()))
        
        other_inc_df = df_fy[df_fy["line"] == "other_income"]
        other_income = float(other_inc_df["closing_cr"].sum() if other_inc_df["closing_cr"].sum() > 0 else abs(other_inc_df["closing_net"].sum()))
        
        cogs_df = df_fy[df_fy["line"] == "cogs"]
        cogs = float(cogs_df["closing_dr"].sum() if cogs_df["closing_dr"].sum() > 0 else abs(cogs_df["closing_net"].sum()))
        
        emp_df = df_fy[df_fy["line"] == "employee_cost"]
        employee_cost = float(emp_df["closing_dr"].sum() if emp_df["closing_dr"].sum() > 0 else abs(emp_df["closing_net"].sum()))
        
        sga_df = df_fy[df_fy["line"] == "sga"]
        sga = float(sga_df["closing_dr"].sum() if sga_df["closing_dr"].sum() > 0 else abs(sga_df["closing_net"].sum()))
        
        oth_exp_df = df_fy[df_fy["line"] == "other_expenses"]
        other_expenses = float(oth_exp_df["closing_dr"].sum() if oth_exp_df["closing_dr"].sum() > 0 else abs(oth_exp_df["closing_net"].sum()))
        
        dep_df = df_fy[df_fy["line"] == "depreciation"]
        depreciation = float(dep_df["closing_dr"].sum() if dep_df["closing_dr"].sum() > 0 else abs(dep_df["closing_net"].sum()))
        
        fin_df = df_fy[df_fy["line"] == "finance_cost"]
        finance_cost = float(fin_df["closing_dr"].sum() if fin_df["closing_dr"].sum() > 0 else abs(fin_df["closing_net"].sum()))
        
        tax_df = df_fy[df_fy["line"] == "tax"]
        tax = float(tax_df["closing_dr"].sum() if tax_df["closing_dr"].sum() > 0 else abs(tax_df["closing_net"].sum()))
        
        gross_profit = revenue - cogs
        ebitda = revenue + other_income - cogs - employee_cost - other_expenses - sga
        ebit = ebitda - depreciation
        pbt = ebit - finance_cost
        pat = pbt - tax
        
        # Balance Sheet Assets
        rec_df = df_fy[df_fy["line"] == "receivables"]
        receivables = float(rec_df["closing_dr"].sum() - rec_df["closing_cr"].sum())
        
        inv_df = df_fy[df_fy["line"] == "inventory"]
        inventory = float(inv_df["closing_dr"].sum() - inv_df["closing_cr"].sum())
        
        cash_df = df_fy[df_fy["line"] == "cash"]
        cash = float(cash_df["closing_dr"].sum() - cash_df["closing_cr"].sum())
        
        oca_df = df_fy[df_fy["line"] == "other_current_assets"]
        other_current_assets = float(oca_df["closing_dr"].sum() - oca_df["closing_cr"].sum())
        
        current_assets = receivables + inventory + cash + other_current_assets
        
        gb_df = df_fy[df_fy["line"] == "gross_block"]
        gross_block = float(gb_df["closing_dr"].sum() - gb_df["closing_cr"].sum())
        
        ad_df = df_fy[df_fy["line"] == "accum_depreciation"]
        accum_depreciation = float(ad_df["closing_cr"].sum() - ad_df["closing_dr"].sum())
        net_block = max(0.0, gross_block - accum_depreciation)
        
        cwip_df = df_fy[df_fy["line"] == "cwip"]
        cwip = float(cwip_df["closing_dr"].sum() - cwip_df["closing_cr"].sum())
        
        int_df = df_fy[df_fy["line"] == "intangibles"]
        intangibles = float(int_df["closing_dr"].sum() - int_df["closing_cr"].sum())
        
        invst_df = df_fy[df_fy["line"] == "investments"]
        investments = float(invst_df["closing_dr"].sum() - invst_df["closing_cr"].sum())
        
        la_df = df_fy[df_fy["line"] == "loans_advances"]
        loans_advances = float(la_df["closing_dr"].sum() - la_df["closing_cr"].sum())
        
        total_assets = current_assets + net_block + cwip + intangibles + investments + loans_advances
        
        # Balance Sheet Liabilities & Equity
        pay_df = df_fy[df_fy["line"] == "payables"]
        payables = float(pay_df["closing_cr"].sum() - pay_df["closing_dr"].sum())
        
        ocl_df = df_fy[df_fy["line"] == "other_current_liabilities"]
        other_current_liabilities = float(ocl_df["closing_cr"].sum() - ocl_df["closing_dr"].sum())
        
        prov_df = df_fy[df_fy["line"] == "provisions"]
        provisions = float(prov_df["closing_cr"].sum() - prov_df["closing_dr"].sum())
        
        wcb_df = df_fy[df_fy["line"] == "wc_borrowings"]
        wc_borrowings = float(wcb_df["closing_cr"].sum() - wcb_df["closing_dr"].sum())
        
        current_liabilities = payables + other_current_liabilities + wc_borrowings + provisions
        
        ltb_df = df_fy[df_fy["line"] == "lt_borrowings"]
        lt_borrowings = float(ltb_df["closing_cr"].sum() - ltb_df["closing_dr"].sum())
        
        total_liabilities = current_liabilities + lt_borrowings
        
        sc_df = df_fy[df_fy["line"] == "share_capital"]
        share_capital = float(sc_df["closing_cr"].sum() - sc_df["closing_dr"].sum())
        
        res_df = df_fy[df_fy["line"] == "reserves"]
        reserves = float(res_df["closing_cr"].sum() - res_df["closing_dr"].sum())
        
        # If retained earnings in TB does not already reflect current year PAT, net worth = share_capital + reserves + pat
        retained_earnings = reserves + pat
        net_worth = share_capital + retained_earnings
        
        working_capital = current_assets - current_liabilities
        
        # Special fields: Related party balances & Unbilled revenue
        if related_parties:
            rp_mask = df_fy["ledger_name"].isin(related_parties) | df_fy["group"].str.contains(r'related|associate|group co', case=False, na=False)
        else:
            rp_mask = df_fy["group"].str.contains(r'related|associate|group co', case=False, na=False)
        rp_df = df_fy[rp_mask]
        related_party_balance = float(abs(rp_df["closing_net"].sum()))
        
        unb_mask = df_fy["ledger_name"].str.contains("unbilled", case=False, na=False)
        unbilled_revenue = float(abs(df_fy[unb_mask]["closing_net"].sum()))
        
        # Fixed asset additions and opening gross block
        op_gb = float(gb_df["opening_dr"].sum() - gb_df["opening_cr"].sum())
        fa_additions = float(gb_df["turnover_dr"].sum())
        fa_disposals = float(gb_df["turnover_cr"].sum())
        
        # Indirect Cash Flow
        # cfo = pat + depreciation + finance_cost - Δreceivables - Δinventory - Δother_current_assets + Δpayables + Δother_current_liabilities - tax_paid
        has_opening = (df_fy["opening_dr"].sum() > 0 or df_fy["opening_cr"].sum() > 0)
        cfo_indirect = None
        if has_opening:
            delta_rec = float((rec_df["closing_dr"] - rec_df["closing_cr"]).sum() - (rec_df["opening_dr"] - rec_df["opening_cr"]).sum())
            delta_inv = float((inv_df["closing_dr"] - inv_df["closing_cr"]).sum() - (inv_df["opening_dr"] - inv_df["opening_cr"]).sum())
            delta_oca = float((oca_df["closing_dr"] - oca_df["closing_cr"]).sum() - (oca_df["opening_dr"] - oca_df["opening_cr"]).sum())
            delta_pay = float((pay_df["closing_cr"] - pay_df["closing_dr"]).sum() - (pay_df["opening_cr"] - pay_df["opening_dr"]).sum())
            delta_ocl = float((ocl_df["closing_cr"] - ocl_df["closing_dr"]).sum() - (ocl_df["opening_cr"] - ocl_df["opening_dr"]).sum())
            
            tax_paid = tax
            cfo_indirect = (
                pat
                + depreciation
                + finance_cost
                - delta_rec
                - delta_inv
                - delta_oca
                + delta_pay
                + delta_ocl
                - tax_paid
            )
            
        derived_rows.append({
            "fy": fy,
            "revenue": round(revenue, 2),
            "other_income": round(other_income, 2),
            "cogs": round(cogs, 2),
            "gross_profit": round(gross_profit, 2),
            "employee_cost": round(employee_cost, 2),
            "other_expenses": round(other_expenses, 2),
            "sga": round(sga, 2),
            "depreciation": round(depreciation, 2),
            "finance_cost": round(finance_cost, 2),
            "pbt": round(pbt, 2),
            "tax": round(tax, 2),
            "pat": round(pat, 2),
            "receivables": round(receivables, 2),
            "inventory": round(inventory, 2),
            "cash": round(cash, 2),
            "other_current_assets": round(other_current_assets, 2),
            "current_assets": round(current_assets, 2),
            "gross_block": round(gross_block, 2),
            "accum_depreciation": round(accum_depreciation, 2),
            "net_block": round(net_block, 2),
            "cwip": round(cwip, 2),
            "intangibles": round(intangibles, 2),
            "investments": round(investments, 2),
            "loans_advances": round(loans_advances, 2),
            "total_assets": round(total_assets, 2),
            "payables": round(payables, 2),
            "other_current_liabilities": round(other_current_liabilities, 2),
            "current_liabilities": round(current_liabilities, 2),
            "wc_borrowings": round(wc_borrowings, 2),
            "lt_borrowings": round(lt_borrowings, 2),
            "provisions": round(provisions, 2),
            "total_liabilities": round(total_liabilities, 2),
            "share_capital": round(share_capital, 2),
            "reserves": round(reserves, 2),
            "retained_earnings": round(retained_earnings, 2),
            "net_worth": round(net_worth, 2),
            "cfo_indirect": round(cfo_indirect, 2) if cfo_indirect is not None else None,
            "ebit": round(ebit, 2),
            "ebitda": round(ebitda, 2),
            "working_capital": round(working_capital, 2),
            "related_party_balance": round(related_party_balance, 2),
            "unbilled_revenue": round(unbilled_revenue, 2),
            "opening_gross_block": round(op_gb, 2),
            "fixed_asset_additions": round(fa_additions, 2),
            "fixed_asset_disposals": round(fa_disposals, 2),
        })
        
    return pd.DataFrame(derived_rows)
