"""
Energy Charge Verification Engine — calculates expected energy charges
based on OERC Retail Supply Tariff rules defined in
LT_Category_Energy_Charge_Calculator.xlsx.
"""

import numpy as np
import pandas as pd


def calc_domestic_ec(units: pd.Series | np.ndarray) -> np.ndarray:
    u = np.maximum(np.nan_to_num(units, nan=0.0), 0.0)
    s1 = np.clip(u, 0, 50) * 2.90
    s2 = np.clip(u - 50, 0, 150) * 4.70
    s3 = np.clip(u - 200, 0, 200) * 5.70
    s4 = np.maximum(u - 400, 0) * 6.10
    return s1 + s2 + s3 + s4


def calc_general_purpose_ec(units: pd.Series | np.ndarray) -> np.ndarray:
    u = np.maximum(np.nan_to_num(units, nan=0.0), 0.0)
    s1 = np.clip(u, 0, 100) * 5.90
    s2 = np.clip(u - 100, 0, 200) * 7.00
    s3 = np.maximum(u - 300, 0) * 7.60
    return s1 + s2 + s3


def calc_flat_rate_ec(cat: str, units: pd.Series | np.ndarray) -> np.ndarray:
    u = np.maximum(np.nan_to_num(units, nan=0.0), 0.0)
    cat_upper = str(cat).upper().strip()

    if "IRRIGATION" in cat_upper or "AGRICULTUR" in cat_upper:
        rate = 1.50
    elif "ALLIED AGRI" in cat_upper:
        rate = 1.60
    elif "AGRO-INDUSTRIAL" in cat_upper:
        rate = 3.10
    elif "PUBLIC LIGHT" in cat_upper:
        rate = 6.20
    elif "SPECIFIED PUBLIC" in cat_upper:
        rate = 6.20
    elif "WATER WORKS" in cat_upper or "SEWERAGE" in cat_upper:
        rate = 6.20
    elif "KUTIR" in cat_upper:
        rate = 0.0
    else:
        rate = 0.0

    return u * rate


def calculate_row_expected_ec(cat: str, kwh: float) -> float:
    c = str(cat).upper().strip()
    try:
        u = float(kwh)
        if np.isnan(u) or u < 0:
            u = 0.0
    except (TypeError, ValueError):
        u = 0.0

    if "DOMESTIC" in c:
        return float(calc_domestic_ec(np.array([u]))[0])
    elif "GENERAL PURPOSE" in c or "GP" in c:
        return float(calc_general_purpose_ec(np.array([u]))[0])
    else:
        return float(calc_flat_rate_ec(c, np.array([u]))[0])


def find_column_by_candidates(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols_upper = {str(c).upper().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.upper() in cols_upper:
            return cols_upper[cand.upper()]
    # Check partial match
    for cand in candidates:
        for cu, orig in cols_upper.items():
            if cand.upper() in cu:
                return orig
    return None


def run_energy_charge_audit(df: pd.DataFrame, target_category: str = "All", tolerance: float = 1.0) -> tuple[pd.DataFrame, dict]:
    """
    Computes calculated energy charge vs actual energy charge in compiled dataset.
    Returns (discrepancy_df, metrics_dict).
    Discrepancy DataFrame contains ONLY mismatched rows (abs(diff) > tolerance).
    """
    if df is None or df.empty:
        empty_res = pd.DataFrame()
        metrics = {
            "total_audited": 0,
            "total_mismatched": 0,
            "mismatch_pct": 0.0,
            "net_discrepancy_amt": 0.0,
            "underbilled_amt": 0.0,
            "overbilled_amt": 0.0,
        }
        return empty_res, metrics

    # Identify key columns
    cat_col = find_column_by_candidates(df, ["CAT_CODE", "TARIFF", "RATE_CATEGORY", "CATEGORY"])
    kwh_col = find_column_by_candidates(df, ["KWH_UNITS", "BILLED_KWH", "KWH", "BILLED_UNITS"])
    ec_col = find_column_by_candidates(df, ["ENERGY_CHG", "ENERGY_AMT", "CURREC", "BILL_TOT"])

    if not cat_col or not kwh_col or not ec_col:
        raise ValueError(
            f"Missing required columns for energy charge audit. "
            f"Detected: Category={cat_col}, kWh={kwh_col}, Billed EC={ec_col}"
        )

    # Filter to target category if specified
    audit_df = df.copy()
    if target_category and target_category != "All Categories" and target_category != "All":
        mask = audit_df[cat_col].astype(str).str.strip().str.upper() == str(target_category).strip().upper()
        audit_df = audit_df[mask].copy()

    if audit_df.empty:
        return pd.DataFrame(), {
            "total_audited": 0,
            "total_mismatched": 0,
            "mismatch_pct": 0.0,
            "net_discrepancy_amt": 0.0,
            "underbilled_amt": 0.0,
            "overbilled_amt": 0.0,
        }

    # Extract arrays
    categories = audit_df[cat_col].astype(str).values
    units = pd.to_numeric(audit_df[kwh_col], errors="coerce").fillna(0.0).values
    actual_ec = pd.to_numeric(audit_df[ec_col], errors="coerce").fillna(0.0).values

    # Calculate expected energy charge
    calculated_ec = np.zeros(len(audit_df), dtype=float)
    for i in range(len(audit_df)):
        calculated_ec[i] = calculate_row_expected_ec(categories[i], units[i])

    diff = actual_ec - calculated_ec  # Positive = Overbilled, Negative = Underbilled

    # Add calculation columns to audit_df
    audit_df["Calculated_EC"] = np.round(calculated_ec, 2)
    audit_df["Actual_EC"] = np.round(actual_ec, 2)
    audit_df["Discrepancy_Diff"] = np.round(diff, 2)

    status_col = []
    for d in diff:
        if d < -tolerance:
            status_col.append("UNDER-BILLED")
        elif d > tolerance:
            status_col.append("OVER-BILLED")
        else:
            status_col.append("MATCH")
    audit_df["Audit_Status"] = status_col

    # Filter ONLY mismatch cases
    mismatch_mask = np.abs(diff) > tolerance
    discrepancy_df = audit_df[mismatch_mask].copy()

    # Re-order columns so audit details appear prominently first
    ident_cols = [c for c in ["Source Division", "Source File", "SCNO", "CA_NUMBER", cat_col, kwh_col] if c in discrepancy_df.columns]
    calc_cols = ["Actual_EC", "Calculated_EC", "Discrepancy_Diff", "Audit_Status"]
    other_cols = [c for c in discrepancy_df.columns if c not in ident_cols and c not in calc_cols]
    final_cols = ident_cols + calc_cols + other_cols
    discrepancy_df = discrepancy_df[final_cols]

    total_audited = len(audit_df)
    total_mismatched = int(mismatch_mask.sum())
    mismatch_pct = (total_mismatched / total_audited * 100) if total_audited > 0 else 0.0

    mismatch_diffs = diff[mismatch_mask]
    underbilled_amt = float(np.abs(mismatch_diffs[mismatch_diffs < 0].sum()))
    overbilled_amt = float(mismatch_diffs[mismatch_diffs > 0].sum())
    net_discrepancy_amt = float(np.abs(mismatch_diffs).sum())

    metrics = {
        "total_audited": total_audited,
        "total_mismatched": total_mismatched,
        "mismatch_pct": mismatch_pct,
        "net_discrepancy_amt": net_discrepancy_amt,
        "underbilled_amt": underbilled_amt,
        "overbilled_amt": overbilled_amt,
    }

    return discrepancy_df, metrics
