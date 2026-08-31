"""Comprehensive Financial and Categorization Summaries for CA Practice."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

def generate_executive_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate overall executive KPI summary metrics."""
    if df is None or df.empty:
        return {
            "total_credits": 0.0,
            "total_debits": 0.0,
            "net_movement": 0.0,
            "total_transactions": 0,
            "credit_count": 0,
            "debit_count": 0,
            "start_date": None,
            "end_date": None,
            "accounts_count": 0,
            "banks_list": []
        }

    total_cr = float(df["credit_amount"].sum())
    total_dr = float(df["debit_amount"].sum())
    net_mov = total_cr - total_dr
    cr_cnt = int((df["credit_amount"] > 0).sum())
    dr_cnt = int((df["debit_amount"] > 0).sum())
    
    dates = df["transaction_date"].dropna()
    start_date = dates.min() if not dates.empty else None
    end_date = dates.max() if not dates.empty else None
    
    accounts = df["account_number"].unique().tolist() if "account_number" in df.columns else []
    banks = df["source_bank"].unique().tolist() if "source_bank" in df.columns else []

    return {
        "total_credits": round(total_cr, 2),
        "total_debits": round(total_dr, 2),
        "net_movement": round(net_mov, 2),
        "total_transactions": len(df),
        "credit_count": cr_cnt,
        "debit_count": dr_cnt,
        "start_date": str(start_date) if start_date else "N/A",
        "end_date": str(end_date) if end_date else "N/A",
        "accounts_count": len(accounts),
        "accounts_list": accounts,
        "banks_list": banks
    }

def generate_month_wise_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Generate month-wise (and FY quarter) summary table."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Month", "FY Quarter", "Receipts (Cr)", "Payments (Dr)", "Net Movement", "Cash Deposits", "Cash Withdrawals", "Txn Count"])

    # Aggregate by Month Sort Key, Month Year, and FY Quarter
    grouped = df.groupby(["month_sort_key", "month_year", "fy_quarter"]).agg(
        receipts=("credit_amount", "sum"),
        payments=("debit_amount", "sum"),
        txn_count=("transaction_date", "count")
    ).reset_index()

    # Calculate Cash movements
    cash_in = df[df["mode"].isin(["CASH", "CDM", "BNA"]) | (df["nature"] == "Cash Deposit")].groupby("month_sort_key")["credit_amount"].sum()
    cash_out = df[df["mode"].isin(["ATM", "CASH"]) | (df["nature"] == "Cash Withdrawal")].groupby("month_sort_key")["debit_amount"].sum()

    grouped["cash_deposits"] = grouped["month_sort_key"].map(cash_in).fillna(0.0)
    grouped["cash_withdrawals"] = grouped["month_sort_key"].map(cash_out).fillna(0.0)
    grouped["net_movement"] = grouped["receipts"] - grouped["payments"]

    grouped = grouped.sort_values(by="month_sort_key")
    
    res = pd.DataFrame({
        "Month": grouped["month_year"],
        "FY Quarter": grouped["fy_quarter"],
        "Receipts (Cr)": grouped["receipts"].round(2),
        "Payments (Dr)": grouped["payments"].round(2),
        "Net Movement": grouped["net_movement"].round(2),
        "Cash Deposits": grouped["cash_deposits"].round(2),
        "Cash Withdrawals": grouped["cash_withdrawals"].round(2),
        "Txn Count": grouped["txn_count"]
    })
    return res

def generate_nature_wise_summary(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate nature-wise summary for Receipts and Payments with % shares."""
    if df is None or df.empty:
        empty_df = pd.DataFrame(columns=["Nature Category", "Total Amount (INR)", "Txn Count", "% Share"])
        return empty_df, empty_df

    # Receipts
    credits_df = df[df["credit_amount"] > 0]
    total_cr = credits_df["credit_amount"].sum()
    if total_cr > 0:
        cr_group = credits_df.groupby("nature").agg(
            total_amount=("credit_amount", "sum"),
            txn_count=("credit_amount", "count")
        ).reset_index().sort_values(by="total_amount", ascending=False)
        cr_group["% Share"] = (cr_group["total_amount"] / total_cr * 100.0).round(2)
        cr_group["Total Amount (INR)"] = cr_group["total_amount"].round(2)
        cr_group = cr_group.rename(columns={"nature": "Nature Category", "txn_count": "Txn Count"})[["Nature Category", "Total Amount (INR)", "Txn Count", "% Share"]]
    else:
        cr_group = pd.DataFrame(columns=["Nature Category", "Total Amount (INR)", "Txn Count", "% Share"])

    # Payments
    debits_df = df[df["debit_amount"] > 0]
    total_dr = debits_df["debit_amount"].sum()
    if total_dr > 0:
        dr_group = debits_df.groupby("nature").agg(
            total_amount=("debit_amount", "sum"),
            txn_count=("debit_amount", "count")
        ).reset_index().sort_values(by="total_amount", ascending=False)
        dr_group["% Share"] = (dr_group["total_amount"] / total_dr * 100.0).round(2)
        dr_group["Total Amount (INR)"] = dr_group["total_amount"].round(2)
        dr_group = dr_group.rename(columns={"nature": "Nature Category", "txn_count": "Txn Count"})[["Nature Category", "Total Amount (INR)", "Txn Count", "% Share"]]
    else:
        dr_group = pd.DataFrame(columns=["Nature Category", "Total Amount (INR)", "Txn Count", "% Share"])

    return cr_group, dr_group

def generate_party_wise_summary(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate party-wise summary for Receipts and Payments."""
    if df is None or df.empty:
        empty_df = pd.DataFrame(columns=["Party Name", "Total Amount (INR)", "Txn Count", "First Txn Date", "Last Txn Date", "Primary Mode", "Dominant Nature"])
        return empty_df, empty_df

    # Receipts Party-wise
    credits_df = df[df["credit_amount"] > 0]
    if not credits_df.empty:
        cr_parties = credits_df.groupby("counterparty_name").agg(
            total_amount=("credit_amount", "sum"),
            txn_count=("credit_amount", "count"),
            first_txn=("transaction_date", "min"),
            last_txn=("transaction_date", "max"),
            primary_mode=("mode", lambda x: x.mode()[0] if not x.empty else "N/A"),
            dominant_nature=("nature", lambda x: x.mode()[0] if not x.empty else "N/A")
        ).reset_index().sort_values(by="total_amount", ascending=False)
        cr_parties["Total Amount (INR)"] = cr_parties["total_amount"].round(2)
        cr_parties = cr_parties.rename(columns={
            "counterparty_name": "Party Name",
            "txn_count": "Txn Count",
            "first_txn": "First Txn Date",
            "last_txn": "Last Txn Date",
            "primary_mode": "Primary Mode",
            "dominant_nature": "Dominant Nature"
        })[["Party Name", "Total Amount (INR)", "Txn Count", "First Txn Date", "Last Txn Date", "Primary Mode", "Dominant Nature"]]
    else:
        cr_parties = pd.DataFrame(columns=["Party Name", "Total Amount (INR)", "Txn Count", "First Txn Date", "Last Txn Date", "Primary Mode", "Dominant Nature"])

    # Payments Party-wise
    debits_df = df[df["debit_amount"] > 0]
    if not debits_df.empty:
        dr_parties = debits_df.groupby("counterparty_name").agg(
            total_amount=("debit_amount", "sum"),
            txn_count=("debit_amount", "count"),
            first_txn=("transaction_date", "min"),
            last_txn=("transaction_date", "max"),
            primary_mode=("mode", lambda x: x.mode()[0] if not x.empty else "N/A"),
            dominant_nature=("nature", lambda x: x.mode()[0] if not x.empty else "N/A")
        ).reset_index().sort_values(by="total_amount", ascending=False)
        dr_parties["Total Amount (INR)"] = dr_parties["total_amount"].round(2)
        dr_parties = dr_parties.rename(columns={
            "counterparty_name": "Party Name",
            "txn_count": "Txn Count",
            "first_txn": "First Txn Date",
            "last_txn": "Last Txn Date",
            "primary_mode": "Primary Mode",
            "dominant_nature": "Dominant Nature"
        })[["Party Name", "Total Amount (INR)", "Txn Count", "First Txn Date", "Last Txn Date", "Primary Mode", "Dominant Nature"]]
    else:
        dr_parties = pd.DataFrame(columns=["Party Name", "Total Amount (INR)", "Txn Count", "First Txn Date", "Last Txn Date", "Primary Mode", "Dominant Nature"])

    return cr_parties, dr_parties

def generate_cross_tab_summary(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate cross-tab summary: Nature x Party for Receipts and Payments."""
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()

    credits_df = df[df["credit_amount"] > 0]
    cr_cross = pd.pivot_table(
        credits_df,
        values="credit_amount",
        index="nature",
        columns="counterparty_name",
        aggfunc="sum",
        fill_value=0.0
    ) if not credits_df.empty else pd.DataFrame()

    debits_df = df[df["debit_amount"] > 0]
    dr_cross = pd.pivot_table(
        debits_df,
        values="debit_amount",
        index="nature",
        columns="counterparty_name",
        aggfunc="sum",
        fill_value=0.0
    ) if not debits_df.empty else pd.DataFrame()

    return cr_cross, dr_cross

def generate_top_and_extrema_transactions(df: pd.DataFrame, top_n: int = 10) -> Dict[str, Any]:
    """Generate Top N and Smallest/Largest transactions for Receipts and Payments."""
    if df is None or df.empty:
        return {
            "top_receipts": pd.DataFrame(),
            "top_payments": pd.DataFrame(),
            "largest_receipt": None,
            "smallest_receipt": None,
            "largest_payment": None,
            "smallest_payment": None
        }

    cols = ["transaction_date", "counterparty_name", "nature", "mode", "description"]
    
    credits_df = df[df["credit_amount"] > 0].copy()
    debits_df = df[df["debit_amount"] > 0].copy()

    top_cr = credits_df.sort_values(by="credit_amount", ascending=False).head(top_n)[cols + ["credit_amount"]].rename(columns={"credit_amount": "Amount (INR)"}) if not credits_df.empty else pd.DataFrame()
    top_dr = debits_df.sort_values(by="debit_amount", ascending=False).head(top_n)[cols + ["debit_amount"]].rename(columns={"debit_amount": "Amount (INR)"}) if not debits_df.empty else pd.DataFrame()

    largest_cr = credits_df.loc[credits_df["credit_amount"].idxmax()].to_dict() if not credits_df.empty else None
    smallest_cr = credits_df.loc[credits_df["credit_amount"].idxmin()].to_dict() if not credits_df.empty else None

    largest_dr = debits_df.loc[debits_df["debit_amount"].idxmax()].to_dict() if not debits_df.empty else None
    smallest_dr = debits_df.loc[debits_df["debit_amount"].idxmin()].to_dict() if not debits_df.empty else None

    return {
        "top_receipts": top_cr,
        "top_payments": top_dr,
        "largest_receipt": largest_cr,
        "smallest_receipt": smallest_cr,
        "largest_payment": largest_dr,
        "smallest_payment": smallest_dr
    }

def generate_cash_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate Cash Transactions Summary (Deposits, Withdrawals, Trends)."""
    if df is None or df.empty:
        return {
            "total_cash_deposits": 0.0,
            "total_cash_withdrawals": 0.0,
            "net_cash_movement": 0.0,
            "cash_deposit_count": 0,
            "cash_withdrawal_count": 0,
            "month_wise_cash": pd.DataFrame()
        }

    cash_dep_df = df[(df["mode"].isin(["CASH", "CDM", "BNA"])) | (df["nature"] == "Cash Deposit")]
    cash_wdl_df = df[(df["mode"].isin(["ATM", "CASH"])) | (df["nature"] == "Cash Withdrawal")]

    tot_dep = float(cash_dep_df["credit_amount"].sum())
    tot_wdl = float(cash_wdl_df["debit_amount"].sum())

    # Month wise trend
    dep_monthly = cash_dep_df.groupby("month_year")["credit_amount"].sum()
    wdl_monthly = cash_wdl_df.groupby("month_year")["debit_amount"].sum()
    
    all_months = df["month_year"].unique()
    monthly_trend = []
    for m in all_months:
        d = float(dep_monthly.get(m, 0.0))
        w = float(wdl_monthly.get(m, 0.0))
        monthly_trend.append({
            "Month": m,
            "Cash Deposits": round(d, 2),
            "Cash Withdrawals": round(w, 2),
            "Net Cash": round(d - w, 2)
        })

    return {
        "total_cash_deposits": round(tot_dep, 2),
        "total_cash_withdrawals": round(tot_wdl, 2),
        "net_cash_movement": round(tot_dep - tot_wdl, 2),
        "cash_deposit_count": len(cash_dep_df),
        "cash_withdrawal_count": len(cash_wdl_df),
        "month_wise_cash": pd.DataFrame(monthly_trend)
    }

def generate_bank_charges_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate summary of bank charges and fee reversals."""
    if df is None or df.empty:
        return {
            "total_bank_charges": 0.0,
            "total_reversals": 0.0,
            "charges_count": 0,
            "reversals_count": 0,
            "charges_breakdown": pd.DataFrame()
        }

    charges_df = df[(df["nature"] == "Bank Charges") | (df["mode"] == "BANK_CHG")]
    reversals_df = df[(df["nature"].str.contains("Reversal|Refund|Cashback", case=False, na=False)) & (df["credit_amount"] > 0)]

    tot_chg = float(charges_df["debit_amount"].sum())
    tot_rev = float(reversals_df["credit_amount"].sum())

    breakdown = charges_df.groupby("description")["debit_amount"].agg(["sum", "count"]).reset_index() if not charges_df.empty else pd.DataFrame(columns=["description", "sum", "count"])
    breakdown = breakdown.rename(columns={"description": "Charge Particulars", "sum": "Amount (INR)", "count": "Frequency"})

    return {
        "total_bank_charges": round(tot_chg, 2),
        "total_reversals": round(tot_rev, 2),
        "charges_count": len(charges_df),
        "reversals_count": len(reversals_df),
        "charges_breakdown": breakdown
    }
