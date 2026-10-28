"""
ingestion.py
Data Ingestion, Column Mapping, Data Integrity Checks and Synthetic Data Generator
for Audit Analytics & Journal Entry Testing Tool.
"""

from datetime import datetime, time
import io
import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

# Canonical internal column names used throughout the tool
CANONICAL_COLUMNS = {
    "voucher_date": "Voucher Date",
    "posting_date": "Posting Date",
    "voucher_number": "Voucher Number",
    "voucher_type": "Voucher Type",
    "account_name": "Account/Ledger Name",
    "debit": "Debit",
    "credit": "Credit",
    "narration": "Narration",
    "created_by": "Created By",
    "approved_by": "Approved By",
}

# Heuristic patterns for auto-mapping columns from Tally, Zoho, SAP, Oracle, Busy, etc.
COLUMN_ALIASES = {
    "voucher_date": [
        "voucher date", "vch date", "date", "txn date", "transaction date",
        "doc date", "document date", "jv date", "trans date", "dt"
    ],
    "posting_date": [
        "posting date", "system date", "created date", "entry date",
        "entered on", "timestamp", "datetime", "post date", "creation date"
    ],
    "voucher_number": [
        "voucher number", "voucher no", "vch no", "doc no", "document no",
        "trans no", "trn no", "reference no", "ref no", "jv no", "voucher #"
    ],
    "voucher_type": [
        "voucher type", "vch type", "type", "doc type", "document type",
        "trans type", "journal type", "sub ledger"
    ],
    "account_name": [
        "account name", "ledger name", "particulars", "account", "ledger",
        "gl account", "head of account", "gl name", "account description"
    ],
    "debit": [
        "debit", "dr", "debit amount", "dr amount", "dr (inr)", "debit (inr)",
        "debit rs", "dr rs", "debit (rs.)"
    ],
    "credit": [
        "credit", "cr", "credit amount", "cr amount", "cr (inr)", "credit (inr)",
        "credit rs", "cr rs", "credit (rs.)"
    ],
    "narration": [
        "narration", "description", "remarks", "memo", "line text", "text",
        "notes", "narration / remarks"
    ],
    "created_by": [
        "created by", "entered by", "user", "username", "maker", "operator",
        "posted by", "userid", "user id", "creator"
    ],
    "approved_by": [
        "approved by", "authorizer", "checker", "verified by", "approver",
        "authorized by"
    ]
}


def suggest_column_mappings(df_columns: List[str]) -> Dict[str, Optional[str]]:
    """
    Intelligently suggest column mappings from input dataframe columns
    to the canonical audit columns.
    """
    mappings: Dict[str, Optional[str]] = {key: None for key in CANONICAL_COLUMNS}
    used_cols = set()

    clean_cols = {col: re.sub(r"[_\s\-\.\/]+", " ", str(col)).strip().lower() for col in df_columns}

    for canonical_key, aliases in COLUMN_ALIASES.items():
        # Exact alias match first
        for orig_col, clean_col in clean_cols.items():
            if orig_col in used_cols:
                continue
            if clean_col in aliases:
                mappings[canonical_key] = orig_col
                used_cols.add(orig_col)
                break
        
        # Substring match if not found
        if mappings[canonical_key] is None:
            for orig_col, clean_col in clean_cols.items():
                if orig_col in used_cols:
                    continue
                for alias in aliases:
                    if alias in clean_col:
                        mappings[canonical_key] = orig_col
                        used_cols.add(orig_col)
                        break
                if mappings[canonical_key] is not None:
                    break

    return mappings


def parse_numeric(series: pd.Series) -> pd.Series:
    """
    Safely parse numeric currency amounts, handling commas, spaces, currency symbols,
    Dr/Cr suffixes, and negative values.
    """
    def _clean_val(v: Any) -> float:
        if pd.isna(v) or v is None or v == "":
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        # Remove currency symbols and formatting commas
        s = re.sub(r"[₹\$,\s]", "", s)
        # Handle brackets for negative: (100.00) -> -100.00
        if s.startswith("(") and s.endswith(")"):
            s = "-" + s[1:-1]
        # Handle trailing/leading Dr/Cr
        s = re.sub(r"(?i)cr|dr", "", s).strip()
        try:
            return float(s)
        except ValueError:
            return np.nan

    return series.apply(_clean_val)


def parse_date_series(series: pd.Series) -> pd.Series:
    """
    Parse a series of date strings into pandas datetime objects.
    Tolerates dayfirst formats commonly used in India (DD/MM/YYYY).
    """
    return pd.to_datetime(series, dayfirst=True, errors="coerce")


def load_file(file_obj_or_path, file_type: str = "xlsx") -> pd.DataFrame:
    """
    Load data from uploaded Excel or CSV file into a pandas DataFrame.
    """
    if file_type.lower() in ["xlsx", "xls"]:
        df = pd.read_excel(file_obj_or_path, engine="openpyxl" if file_type.lower() == "xlsx" else None)
    elif file_type.lower() == "csv":
        # Attempt UTF-8, fallback to latin-1 for Indian accounting export encodings
        try:
            df = pd.read_csv(file_obj_or_path, encoding="utf-8")
        except UnicodeDecodeError:
            if hasattr(file_obj_or_path, "seek"):
                file_obj_or_path.seek(0)
            df = pd.read_csv(file_obj_or_path, encoding="latin-1")
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
    return df


def process_and_standardize_data(
    raw_df: pd.DataFrame,
    mapping: Dict[str, Optional[str]],
    fy_start: Optional[datetime] = None,
    fy_end: Optional[datetime] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Standardize the raw dataframe using verified column mappings.
    Assigns 1-based source_row_index, parses numeric values and dates,
    and runs data integrity and reconciliation diagnostics.
    Does NOT silently delete invalid rows or silently zero out missing amounts.
    """
    standardized = pd.DataFrame()
    # 1-based source row index corresponding to client original spreadsheet row (header is row 1)
    standardized["source_row_index"] = raw_df.index + 2

    # Map core columns
    for key, canonical_name in CANONICAL_COLUMNS.items():
        mapped_col = mapping.get(key)
        if mapped_col and mapped_col in raw_df.columns:
            standardized[canonical_name] = raw_df[mapped_col].copy()
        else:
            standardized[canonical_name] = np.nan

    # Keep original raw text values before coercion for auditing transparency
    standardized["raw_debit"] = standardized["Debit"].copy()
    standardized["raw_credit"] = standardized["Credit"].copy()
    standardized["raw_voucher_date"] = standardized["Voucher Date"].copy()

    # Parse Debit and Credit
    parsed_debit = parse_numeric(standardized["Debit"])
    parsed_credit = parse_numeric(standardized["Credit"])

    standardized["parsed_debit"] = parsed_debit
    standardized["parsed_credit"] = parsed_credit
    
    # Fill actual operational amount: whichever is > 0
    standardized["amount"] = standardized["parsed_debit"].fillna(0) + standardized["parsed_credit"].fillna(0)

    # Parse Dates
    standardized["parsed_voucher_date"] = parse_date_series(standardized["Voucher Date"])
    if standardized["Posting Date"].notna().any():
        standardized["parsed_posting_date"] = parse_date_series(standardized["Posting Date"])
    else:
        standardized["parsed_posting_date"] = standardized["parsed_voucher_date"]

    # String sanitization
    standardized["Voucher Number"] = standardized["Voucher Number"].astype(str).str.strip()
    standardized["Account/Ledger Name"] = standardized["Account/Ledger Name"].astype(str).str.strip()
    standardized["Narration"] = standardized["Narration"].fillna("").astype(str).str.strip()
    standardized["Created By"] = standardized["Created By"].fillna("SYSTEM").astype(str).str.strip()
    standardized["Approved By"] = standardized["Approved By"].fillna("").astype(str).str.strip()
    standardized["Voucher Type"] = standardized["Voucher Type"].fillna("Journal").astype(str).str.strip()

    # Run data integrity diagnostics
    total_rows = len(standardized)
    invalid_dates_count = int(standardized["parsed_voucher_date"].isna().sum())
    missing_account_count = int((standardized["Account/Ledger Name"].isna() | (standardized["Account/Ledger Name"] == "") | (standardized["Account/Ledger Name"] == "nan")).sum())
    missing_voucher_no_count = int((standardized["Voucher Number"].isna() | (standardized["Voucher Number"] == "") | (standardized["Voucher Number"] == "nan")).sum())
    invalid_debit_count = int(standardized["parsed_debit"].isna().sum())
    invalid_credit_count = int(standardized["parsed_credit"].isna().sum())

    # Duplicates detection
    dup_mask = standardized.duplicated(
        subset=["Voucher Number", "parsed_voucher_date", "Account/Ledger Name", "parsed_debit", "parsed_credit"],
        keep=False
    )
    duplicate_rows_count = int(dup_mask.sum())

    # Financial Year Boundary Check
    out_of_fy_count = 0
    if fy_start and fy_end:
        out_of_fy_mask = (standardized["parsed_voucher_date"] < fy_start) | (standardized["parsed_voucher_date"] > fy_end)
        out_of_fy_count = int(out_of_fy_mask.sum())
        standardized["is_out_of_fy"] = out_of_fy_mask
    else:
        standardized["is_out_of_fy"] = False

    # Financial Totals & Reconciliation
    total_debit = float(standardized["parsed_debit"].fillna(0).sum())
    total_credit = float(standardized["parsed_credit"].fillna(0).sum())
    reconciliation_difference = total_debit - total_credit
    is_balanced = abs(reconciliation_difference) < 0.01

    # Per-voucher balance check
    voucher_totals = standardized.groupby("Voucher Number")[["parsed_debit", "parsed_credit"]].sum()
    unbalanced_vouchers_df = voucher_totals[abs(voucher_totals["parsed_debit"] - voucher_totals["parsed_credit"]) > 0.01]
    unbalanced_vouchers_count = len(unbalanced_vouchers_df)

    diagnostics = {
        "total_rows": total_rows,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "difference": reconciliation_difference,
        "is_balanced": is_balanced,
        "invalid_dates_count": invalid_dates_count,
        "missing_account_count": missing_account_count,
        "missing_voucher_no_count": missing_voucher_no_count,
        "invalid_debit_count": invalid_debit_count,
        "invalid_credit_count": invalid_credit_count,
        "duplicate_rows_count": duplicate_rows_count,
        "out_of_fy_count": out_of_fy_count,
        "unbalanced_vouchers_count": unbalanced_vouchers_count,
    }

    return standardized, diagnostics


def generate_synthetic_audit_dataset(
    fy_year: int = 2023,
    num_entries: int = 350
) -> pd.DataFrame:
    """
    Generate an authentic, realistic Indian General Ledger / Journal Voucher dataset
    for testing. Features:
    - Normal Indian accounting heads (Revenue, GST, Trade Payables, Depreciation, TDS, Salaries)
    - Conforms closely to Benford's Law in normal operations
    - Injects specific test scenarios for SA 240 / CARO 2020 testing (Sunday postings,
      after-hours, backdated JVs, round amounts, thresholds, generic/suspicious narrations,
      PM exceedances, cash/suspense/related party, admin maker-checker anomalies).
    """
    np.random.seed(42)
    start_date = pd.Timestamp(f"{fy_year}-04-01")
    end_date = pd.Timestamp(f"{fy_year + 1}-03-31")

    regular_accounts = [
        "Sales Revenue A/c", "Purchases - Raw Materials", "Salaries & Wages A/c",
        "Rent Expense A/c", "Electricity & Utility Expenses", "Audit Fees A/c",
        "Legal & Professional Charges", "Repairs & Maintenance A/c",
        "Printing & Stationery", "Staff Welfare Expense", "Travelling & Conveyance",
        "Depreciation on Plant & Machinery", "TDS Payable A/c", "Output IGST A/c",
        "Input CGST A/c", "Input SGST A/c", "Trade Receivables - Domestic",
        "Trade Payables - Vendors", "Freight Inward Expense", "Telephone & Internet"
    ]

    users = ["akash.sharma", "priya.verma", "rahul.nair", "sunita.rao", "vikram.singh"]
    reviewers = ["amit.patel", "neha.gupta", "suresh.iyer"]
    voucher_types = ["Journal", "Journal Voucher", "Debit Note", "Credit Note", "Adjustment"]

    rows = []
    vch_counter = 1001

    # 1. Normal Operational JVs adhering to realistic distributions
    for _ in range(num_entries - 30):
        # Generate amount following log-uniform (Benford-like) distribution
        base_power = np.random.uniform(3, 5.8)  # 1,000 to ~630,000
        amount = round(10 ** base_power, 2)

        # Normal business date (Monday to Saturday)
        random_day_offset = np.random.randint(0, (end_date - start_date).days)
        entry_date = start_date + pd.Timedelta(days=random_day_offset)
        # Avoid Sunday in normal operational entries
        if entry_date.weekday() == 6:
            entry_date += pd.Timedelta(days=1)

        # Normal business hours between 09:30 and 18:30
        hour = np.random.randint(9, 18)
        minute = np.random.randint(0, 59)
        post_timestamp = entry_date.replace(hour=hour, minute=minute)

        vch_no = f"JV/{fy_year}-{(fy_year+1)%100}/{vch_counter:04d}"
        vch_counter += 1
        user = np.random.choice(users)
        approver = np.random.choice(reviewers)
        vch_type = np.random.choice(voucher_types, p=[0.7, 0.15, 0.05, 0.05, 0.05])

        dr_acct = np.random.choice(regular_accounts)
        cr_acct = np.random.choice([a for a in regular_accounts if a != dr_acct])

        narration = f"Being monthly allocation towards {dr_acct.lower()} for the period"

        # Debit leg
        rows.append({
            "Voucher Date": entry_date.strftime("%d-%m-%Y"),
            "Posting Date": post_timestamp.strftime("%d-%m-%Y %H:%M"),
            "Voucher Number": vch_no,
            "Voucher Type": vch_type,
            "Account/Ledger Name": dr_acct,
            "Debit": amount,
            "Credit": 0.0,
            "Narration": narration,
            "Created By": user,
            "Approved By": approver
        })
        # Credit leg
        rows.append({
            "Voucher Date": entry_date.strftime("%d-%m-%Y"),
            "Posting Date": post_timestamp.strftime("%d-%m-%Y %H:%M"),
            "Voucher Number": vch_no,
            "Voucher Type": vch_type,
            "Account/Ledger Name": cr_acct,
            "Debit": 0.0,
            "Credit": amount,
            "Narration": narration,
            "Created By": user,
            "Approved By": approver
        })

    # 2. Targeted Red Flag Injections matching the 10 Audit Rules
    flagged_scenarios = [
        # Test 1: Sunday Posting
        {
            "date": pd.Timestamp(f"{fy_year}-09-17"),  # Sunday
            "post_date": pd.Timestamp(f"{fy_year}-09-17 11:20"),
            "dr": "Consultancy Charges", "cr": "Trade Payables - Vendors",
            "amt": 125000.0, "narr": "Urgent Sunday consultant billing adjustment",
            "maker": "akash.sharma", "checker": "amit.patel", "type": "Journal"
        },
        # Test 2: Off-hours Posting (Late night 02:45 AM)
        {
            "date": pd.Timestamp(f"{fy_year}-11-14"),
            "post_date": pd.Timestamp(f"{fy_year}-11-14 02:45"),
            "dr": "Software License Expense", "cr": "Accrued Expenses",
            "amt": 340000.0, "narr": "Midnight server license renewal booking",
            "maker": "priya.verma", "checker": "neha.gupta", "type": "Journal"
        },
        # Test 3: Backdated voucher after 31 March (Year-end cutoff anomaly)
        {
            "date": pd.Timestamp(f"{fy_year + 1}-03-31"),  # Dated 31-March
            "post_date": pd.Timestamp(f"{fy_year + 1}-05-24 16:10"),  # Posted in late May!
            "dr": "Legal & Professional Charges", "cr": "Provision for Expenses",
            "amt": 850000.0, "narr": "Year-end retroactive audit fee provision booked post year-end close",
            "maker": "rahul.nair", "checker": "suresh.iyer", "type": "Adjustment"
        },
        # Test 4: Exact Round Value (₹15,00,000 & ₹5,00,000)
        {
            "date": pd.Timestamp(f"{fy_year}-08-10"),
            "post_date": pd.Timestamp(f"{fy_year}-08-10 14:00"),
            "dr": "Corporate Social Responsibility Expense", "cr": "HDFC Bank A/c",
            "amt": 1500000.0, "narr": "Round lump sum contribution to CSR trust",
            "maker": "sunita.rao", "checker": "amit.patel", "type": "Journal"
        },
        # Test 5: Immediately below approval threshold (e.g. ₹4,95,000 vs ₹5,00,000 authority limit)
        {
            "date": pd.Timestamp(f"{fy_year}-10-18"),
            "post_date": pd.Timestamp(f"{fy_year}-10-18 11:30"),
            "dr": "Advertising & Promotion", "cr": "Trade Payables - Vendors",
            "amt": 498500.0, "narr": "Campaign billing split to remain within regional director authorization limit",
            "maker": "vikram.singh", "checker": "neha.gupta", "type": "Journal"
        },
        # Test 6: Suspiciously blank or generic narration
        {
            "date": pd.Timestamp(f"{fy_year}-12-05"),
            "post_date": pd.Timestamp(f"{fy_year}-12-05 15:15"),
            "dr": "Miscellaneous Expenses", "cr": "Other Current Assets",
            "amt": 75000.0, "narr": "Being entry passed",  # Suspiciously generic
            "maker": "akash.sharma", "checker": "suresh.iyer", "type": "Journal"
        },
        # Test 7: Suspicious audit keywords in narration
        {
            "date": pd.Timestamp(f"{fy_year + 1}-01-20"),
            "post_date": pd.Timestamp(f"{fy_year + 1}-01-20 16:45"),
            "dr": "Suspense Account", "cr": "Sales Revenue A/c",
            "amt": 620000.0, "narr": "Management entry: dummy suspense rectification required as per CFO verbal instructions",
            "maker": "rahul.nair", "checker": "amit.patel", "type": "Adjustment"
        },
        # Test 8: High-Value Entry exceeding Performance Materiality (e.g. ₹75,00,000)
        {
            "date": pd.Timestamp(f"{fy_year + 1}-03-28"),
            "post_date": pd.Timestamp(f"{fy_year + 1}-03-28 17:00"),
            "dr": "Capital Work in Progress", "cr": "Trade Payables - Capital Goods",
            "amt": 7500000.0, "narr": "Major capitalization of enterprise ERP modules and plant expansion works",
            "maker": "priya.verma", "checker": "neha.gupta", "type": "Journal"
        },
        # Test 9: Affecting Sensitive Accounts (Suspense, Cash, Related Party / Director)
        {
            "date": pd.Timestamp(f"{fy_year}-07-15"),
            "post_date": pd.Timestamp(f"{fy_year}-07-15 13:20"),
            "dr": "Director Remuneration & Perks", "cr": "Loan from Managing Director A/c",
            "amt": 1200000.0, "narr": "Adjustment of executive perks against director unsecured loan account",
            "maker": "sunita.rao", "checker": "suresh.iyer", "type": "Journal"
        },
        # Test 10: Admin-user / Maker-Checker anomaly (Admin user or Maker == Checker)
        {
            "date": pd.Timestamp(f"{fy_year}-06-22"),
            "post_date": pd.Timestamp(f"{fy_year}-06-22 18:30"),
            "dr": "Office Renovation Charges", "cr": "Trade Payables - Vendors",
            "amt": 280000.0, "narr": "Direct system backend entry without independent verification",
            "maker": "admin", "checker": "admin", "type": "Journal"  # Both Maker & Checker are admin!
        }
    ]

    for scenario in flagged_scenarios:
        vch_no = f"JV/{fy_year}-{(fy_year+1)%100}/{vch_counter:04d}"
        vch_counter += 1
        d_str = scenario["date"].strftime("%d-%m-%Y")
        p_str = scenario["post_date"].strftime("%d-%m-%Y %H:%M")

        rows.append({
            "Voucher Date": d_str,
            "Posting Date": p_str,
            "Voucher Number": vch_no,
            "Voucher Type": scenario["type"],
            "Account/Ledger Name": scenario["dr"],
            "Debit": scenario["amt"],
            "Credit": 0.0,
            "Narration": scenario["narr"],
            "Created By": scenario["maker"],
            "Approved By": scenario["checker"]
        })
        rows.append({
            "Voucher Date": d_str,
            "Posting Date": p_str,
            "Voucher Number": vch_no,
            "Voucher Type": scenario["type"],
            "Account/Ledger Name": scenario["cr"],
            "Debit": 0.0,
            "Credit": scenario["amt"],
            "Narration": scenario["narr"],
            "Created By": scenario["maker"],
            "Approved By": scenario["checker"]
        })

    df = pd.DataFrame(rows)
    return df
