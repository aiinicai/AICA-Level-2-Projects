"""
analytics.py
Audit Analytics, SA 240 / SA 330 Journal Entry Testing Rules,
Benford's Law First-Digit Analysis, and Audit Sampling Engine.
"""

from datetime import datetime, time
import math
import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    stats = None
    HAS_SCIPY = False

# Default suspicious audit keywords for Indian statutory audits
DEFAULT_AUDIT_KEYWORDS = [
    "adjustment", "rectification", "management entry", "reversal", "dummy",
    "urgent", "suspense", "error", "write-off", "prior period", "as per discussion",
    "verbal instruction", "plug", "cfo", "director instruction", "manual",
    "true up", "year end", "round off"
]

# Default generic or blank narrations
DEFAULT_GENERIC_NARRATIONS = [
    "", "na", "n/a", "none", "nil", "being", "being entry passed",
    "being journal entry passed", "being rectification done", "misc",
    "adjustment", "jv", "journal", "general", "to transfer", "being transfer"
]

# Sensitive / high-risk account patterns
DEFAULT_SENSITIVE_ACCOUNTS = [
    "cash", "suspense", "petty cash", "director", "related party",
    "loan from director", "advance to director", "clearing", "reconciliation",
    "inter company", "holding", "subsidiary", "unclaimed", "miscellaneous balance"
]


def validate_materiality(
    om: float,
    pm: float,
    ctt: float
) -> Dict[str, Any]:
    """
    Validate audit materiality hierarchy according to ICAI SA 320 / SA 450.
    Rule: 0 < CTT < PM < OM.
    """
    errors = []
    warnings = []

    if om <= 0:
        errors.append("Overall Materiality (OM) must be strictly greater than 0.")
    if pm <= 0:
        errors.append("Performance Materiality (PM) must be strictly greater than 0.")
    if ctt <= 0:
        errors.append("Clearly Trivial Threshold (CTT) must be strictly greater than 0.")

    if om > 0 and pm >= om:
        errors.append("Performance Materiality (PM) must be less than Overall Materiality (OM).")
    if pm > 0 and ctt >= pm:
        errors.append("Clearly Trivial Threshold (CTT) must be less than Performance Materiality (PM).")

    # Audit best-practice benchmarks
    if om > 0 and pm > 0 and pm < om:
        pm_pct = (pm / om) * 100
        if pm_pct < 50.0:
            warnings.append(f"PM is {pm_pct:.1f}% of OM (standard benchmark is typically 50% - 75% for Indian audits).")
        elif pm_pct > 85.0:
            warnings.append(f"PM is {pm_pct:.1f}% of OM (benchmark rarely exceeds 75% - 80% without documented low RMM).")

    if om > 0 and ctt > 0:
        ctt_pct = (ctt / om) * 100
        if ctt_pct > 10.0:
            warnings.append(f"CTT is {ctt_pct:.1f}% of OM (standard benchmark is 1% - 5%, rarely exceeding 5%).")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "om": om,
        "pm": pm,
        "ctt": ctt
    }


def run_journal_entry_tests(
    df: pd.DataFrame,
    pm: float,
    start_business_hour: time = time(9, 0),
    end_business_hour: time = time(19, 0),
    round_multiples: List[float] = [100000.0, 500000.0, 1000000.0],
    auth_thresholds: List[float] = [500000.0, 1000000.0, 2500000.0, 5000000.0],
    threshold_margin_pct: float = 5.0,  # within 5% below threshold
    custom_keywords: Optional[List[str]] = None,
    custom_sensitive_accounts: Optional[List[str]] = None,
    enabled_tests: Optional[Dict[str, bool]] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Execute 10 configurable Journal Entry tests as mandated by SA 240 / SA 330.
    Returns:
    - enriched_df: Original df with flag indicators and max risk level.
    - flags_df: Normalized dataframe of all flagged items with source row, test details,
                risk level, reason, and suggested audit procedure.
    """
    if enabled_tests is None:
        enabled_tests = {f"test_{i}": True for i in range(1, 11)}

    keywords = custom_keywords if custom_keywords is not None else DEFAULT_AUDIT_KEYWORDS
    sensitive_patterns = custom_sensitive_accounts if custom_sensitive_accounts is not None else DEFAULT_SENSITIVE_ACCOUNTS

    all_flags = []
    
    # Pre-calculate working fields
    df = df.copy()
    
    # Dates
    v_dates = df["parsed_voucher_date"]
    p_dates = df["parsed_posting_date"]
    amounts = df["amount"]
    narrations = df["Narration"].astype(str).str.strip()
    accounts = df["Account/Ledger Name"].astype(str).str.strip()
    makers = df["Created By"].astype(str).str.strip().str.lower()
    checkers = df["Approved By"].astype(str).str.strip().str.lower()

    # -------------------------------------------------------------
    # Test 1: Posted on Sundays
    # -------------------------------------------------------------
    if enabled_tests.get("test_1", True):
        # Check weekday of voucher_date and posting_date (6 == Sunday)
        sunday_mask = (v_dates.dt.weekday == 6) | (p_dates.dt.weekday == 6)
        for idx in df[sunday_mask].index:
            row = df.loc[idx]
            d_val = row["parsed_voucher_date"].strftime("%d-%m-%Y") if pd.notna(row["parsed_voucher_date"]) else "Unknown"
            all_flags.append({
                "source_row_index": int(row["source_row_index"]),
                "voucher_number": str(row["Voucher Number"]),
                "voucher_date": d_val,
                "account_name": str(row["Account/Ledger Name"]),
                "amount": float(row["amount"]),
                "test_id": "TEST_01",
                "test_name": "Sunday Postings",
                "risk_level": "Medium",
                "reason": f"Transaction dated or entered on Sunday ({d_val}), outside standard working week.",
                "audit_procedure": "Inspect physical voucher authorization, underlying operational justification, and confirm if transaction occurred during authorized overtime."
            })

    # -------------------------------------------------------------
    # Test 2: Outside Configured Business Hours
    # -------------------------------------------------------------
    if enabled_tests.get("test_2", True):
        # Only evaluate if posting date has non-midnight or real time component
        has_time = p_dates.dt.time.notna() & ((p_dates.dt.hour != 0) | (p_dates.dt.minute != 0))
        if has_time.any():
            times = p_dates.dt.time
            off_hours_mask = has_time & ((times < start_business_hour) | (times > end_business_hour))
            for idx in df[off_hours_mask].index:
                row = df.loc[idx]
                time_str = row["parsed_posting_date"].strftime("%H:%M:%S")
                all_flags.append({
                    "source_row_index": int(row["source_row_index"]),
                    "voucher_number": str(row["Voucher Number"]),
                    "voucher_date": row["parsed_voucher_date"].strftime("%d-%m-%Y") if pd.notna(row["parsed_voucher_date"]) else "",
                    "account_name": str(row["Account/Ledger Name"]),
                    "amount": float(row["amount"]),
                    "test_id": "TEST_02",
                    "test_name": "Off-Hours Postings",
                    "risk_level": "Medium",
                    "reason": f"Entry posted at {time_str}, outside configured business hours ({start_business_hour.strftime('%H:%M')} to {end_business_hour.strftime('%H:%M')}).",
                    "audit_procedure": "Verify system audit logs to confirm user login authenticity; inquire why transaction was keyed during off-hours."
                })

    # -------------------------------------------------------------
    # Test 3: Backdated Entries Posted After 31 March (Year-end cutoff)
    # -------------------------------------------------------------
    if enabled_tests.get("test_3", True):
        # Look for vouchers dated in March (especially <= 31 March) but posted in April or later
        backdated_mask = (
            (v_dates.dt.month == 3) &
            (p_dates.dt.month > 3) &
            (p_dates.dt.year >= v_dates.dt.year)
        )
        for idx in df[backdated_mask].index:
            row = df.loc[idx]
            v_str = row["parsed_voucher_date"].strftime("%d-%m-%Y") if pd.notna(row["parsed_voucher_date"]) else ""
            p_str = row["parsed_posting_date"].strftime("%d-%m-%Y") if pd.notna(row["parsed_posting_date"]) else ""
            all_flags.append({
                "source_row_index": int(row["source_row_index"]),
                "voucher_number": str(row["Voucher Number"]),
                "voucher_date": v_str,
                "account_name": str(row["Account/Ledger Name"]),
                "amount": float(row["amount"]),
                "test_id": "TEST_03",
                "test_name": "Post-Year-End Backdated Cutoff",
                "risk_level": "High",
                "reason": f"Voucher dated {v_str} (Q4/year-end) but posted into system on {p_str} post-balance sheet date.",
                "audit_procedure": "Perform rigorous subsequent events and cutoff procedures per SA 560; examine whether entry was used to manipulate reporting period financial results or hide liabilities."
            })

    # -------------------------------------------------------------
    # Test 4: Round-Value Transactions
    # -------------------------------------------------------------
    if enabled_tests.get("test_4", True):
        # Matches if amount >= 1,00,000 and is an exact multiple of configured round amounts
        for multiple in sorted(round_multiples, reverse=True):
            round_mask = (amounts >= multiple) & (amounts % multiple == 0)
            for idx in df[round_mask].index:
                row = df.loc[idx]
                amt_val = float(row["amount"])
                all_flags.append({
                    "source_row_index": int(row["source_row_index"]),
                    "voucher_number": str(row["Voucher Number"]),
                    "voucher_date": row["parsed_voucher_date"].strftime("%d-%m-%Y") if pd.notna(row["parsed_voucher_date"]) else "",
                    "account_name": str(row["Account/Ledger Name"]),
                    "amount": amt_val,
                    "test_id": "TEST_04",
                    "test_name": "Round-Value Transaction",
                    "risk_level": "Low",
                    "reason": f"Transaction amount ₹{amt_val:,.2f} is an exact round multiple of ₹{multiple:,.0f}.",
                    "audit_procedure": "Review supporting calculation and contracts to verify if round number represents an arbitrary estimate or true contractual billing."
                })

    # -------------------------------------------------------------
    # Test 5: Transactions Immediately Below Authorization Thresholds
    # -------------------------------------------------------------
    if enabled_tests.get("test_5", True):
        for threshold in auth_thresholds:
            lower_bound = threshold * (1 - threshold_margin_pct / 100.0)
            threshold_mask = (amounts >= lower_bound) & (amounts < threshold)
            for idx in df[threshold_mask].index:
                row = df.loc[idx]
                amt_val = float(row["amount"])
                margin_diff = threshold - amt_val
                all_flags.append({
                    "source_row_index": int(row["source_row_index"]),
                    "voucher_number": str(row["Voucher Number"]),
                    "voucher_date": row["parsed_voucher_date"].strftime("%d-%m-%Y") if pd.notna(row["parsed_voucher_date"]) else "",
                    "account_name": str(row["Account/Ledger Name"]),
                    "amount": amt_val,
                    "test_id": "TEST_05",
                    "test_name": "Below Authorization Threshold",
                    "risk_level": "High",
                    "reason": f"Amount ₹{amt_val:,.2f} is within {threshold_margin_pct}% (short by ₹{margin_diff:,.2f}) below approval ceiling of ₹{threshold:,.0f}.",
                    "audit_procedure": "Inquire whether transactions were intentionally structured or split to bypass higher management/board approval under the Delegation of Authority (DOA)."
                })

    # -------------------------------------------------------------
    # Test 6: Blank or Suspiciously Generic Narrations
    # -------------------------------------------------------------
    if enabled_tests.get("test_6", True):
        clean_narr = narrations.str.lower().str.strip()
        generic_mask = clean_narr.isin([g.lower() for g in DEFAULT_GENERIC_NARRATIONS]) | (clean_narr.str.len() <= 3)
        for idx in df[generic_mask].index:
            row = df.loc[idx]
            raw_narr = row["Narration"]
            all_flags.append({
                "source_row_index": int(row["source_row_index"]),
                "voucher_number": str(row["Voucher Number"]),
                "voucher_date": row["parsed_voucher_date"].strftime("%d-%m-%Y") if pd.notna(row["parsed_voucher_date"]) else "",
                "account_name": str(row["Account/Ledger Name"]),
                "amount": float(row["amount"]),
                "test_id": "TEST_06",
                "test_name": "Blank / Generic Narration",
                "risk_level": "Medium",
                "reason": f"Narration is blank or non-descriptive: '{raw_narr}'.",
                "audit_procedure": "Request physical vouchers and commercial background; require management to substantiate the business purpose of the entry."
            })

    # -------------------------------------------------------------
    # Test 7: Suspicious Audit Keywords in Narration
    # -------------------------------------------------------------
    if enabled_tests.get("test_7", True):
        kw_pattern = "|".join([re.escape(k.lower()) for k in keywords])
        kw_mask = narrations.str.lower().str.contains(kw_pattern, regex=True, na=False)
        for idx in df[kw_mask].index:
            row = df.loc[idx]
            found_kws = [k for k in keywords if re.search(r"\b" + re.escape(k.lower()), str(row["Narration"]).lower())]
            match_str = ", ".join(found_kws) if found_kws else "audit keyword"
            all_flags.append({
                "source_row_index": int(row["source_row_index"]),
                "voucher_number": str(row["Voucher Number"]),
                "voucher_date": row["parsed_voucher_date"].strftime("%d-%m-%Y") if pd.notna(row["parsed_voucher_date"]) else "",
                "account_name": str(row["Account/Ledger Name"]),
                "amount": float(row["amount"]),
                "test_id": "TEST_07",
                "test_name": "Audit Keyword in Narration",
                "risk_level": "High",
                "reason": f"Narration contains sensitive audit keyword(s): [{match_str}]. Text: '{row['Narration']}'.",
                "audit_procedure": "Examine root cause of adjustment/rectification per SA 240; verify whether entry represents management override or unauthorized manipulation."
            })

    # -------------------------------------------------------------
    # Test 8: High-Value Entries Exceeding Performance Materiality (PM)
    # -------------------------------------------------------------
    if enabled_tests.get("test_8", True):
        pm_mask = amounts > pm
        for idx in df[pm_mask].index:
            row = df.loc[idx]
            amt_val = float(row["amount"])
            all_flags.append({
                "source_row_index": int(row["source_row_index"]),
                "voucher_number": str(row["Voucher Number"]),
                "voucher_date": row["parsed_voucher_date"].strftime("%d-%m-%Y") if pd.notna(row["parsed_voucher_date"]) else "",
                "account_name": str(row["Account/Ledger Name"]),
                "amount": amt_val,
                "test_id": "TEST_08",
                "test_name": "Exceeding Performance Materiality",
                "risk_level": "High",
                "reason": f"Amount ₹{amt_val:,.2f} exceeds Performance Materiality (PM = ₹{pm:,.2f}).",
                "audit_procedure": "Perform 100% substantive testing of invoices, contracts, bank statements, and relevant board resolutions per SA 330."
            })

    # -------------------------------------------------------------
    # Test 9: Affecting Sensitive / Suspense / Cash Accounts
    # -------------------------------------------------------------
    if enabled_tests.get("test_9", True):
        sens_pattern = "|".join([re.escape(s.lower()) for s in sensitive_patterns])
        sens_mask = accounts.str.lower().str.contains(sens_pattern, regex=True, na=False)
        for idx in df[sens_mask].index:
            row = df.loc[idx]
            matched_terms = [s for s in sensitive_patterns if s.lower() in str(row["Account/Ledger Name"]).lower()]
            term_str = ", ".join(matched_terms) if matched_terms else "sensitive account"
            all_flags.append({
                "source_row_index": int(row["source_row_index"]),
                "voucher_number": str(row["Voucher Number"]),
                "voucher_date": row["parsed_voucher_date"].strftime("%d-%m-%Y") if pd.notna(row["parsed_voucher_date"]) else "",
                "account_name": str(row["Account/Ledger Name"]),
                "amount": float(row["amount"]),
                "test_id": "TEST_09",
                "test_name": "Sensitive / Suspense Account",
                "risk_level": "High",
                "reason": f"Affects high-risk account category: [{term_str}]. Ledger: '{row['Account/Ledger Name']}'.",
                "audit_procedure": "Scrutinize ledger entries, verify CARO 2020 Clause (ix) regarding fund diversion and Companies Act Section 188 related party disclosures."
            })

    # -------------------------------------------------------------
    # Test 10: Admin-User or Maker-Checker Anomaly
    # -------------------------------------------------------------
    if enabled_tests.get("test_10", True):
        admin_patterns = ["admin", "administrator", "root", "superuser", "system", "sysadmin"]
        is_admin_maker = makers.isin(admin_patterns)
        same_maker_checker = (makers != "") & (checkers != "") & (makers == checkers)
        anomaly_mask = is_admin_maker | same_maker_checker

        for idx in df[anomaly_mask].index:
            row = df.loc[idx]
            m = str(row["Created By"])
            c = str(row["Approved By"])
            reason_parts = []
            if m.lower() in admin_patterns:
                reason_parts.append(f"Created by privileged system account '{m}'")
            if m and c and m.lower() == c.lower():
                reason_parts.append(f"Maker and Checker are identical ('{m}') violating dual-control Segregation of Duties")
            
            all_flags.append({
                "source_row_index": int(row["source_row_index"]),
                "voucher_number": str(row["Voucher Number"]),
                "voucher_date": row["parsed_voucher_date"].strftime("%d-%m-%Y") if pd.notna(row["parsed_voucher_date"]) else "",
                "account_name": str(row["Account/Ledger Name"]),
                "amount": float(row["amount"]),
                "test_id": "TEST_10",
                "test_name": "Admin / Maker-Checker Anomaly",
                "risk_level": "High",
                "reason": " and ".join(reason_parts) + ".",
                "audit_procedure": "Test IT general controls (ITGC), evaluate segregation of duties (SoD), and verify secondary executive sign-off."
            })

    flags_df = pd.DataFrame(all_flags)
    if flags_df.empty:
        flags_df = pd.DataFrame(columns=[
            "source_row_index", "voucher_number", "voucher_date", "account_name",
            "amount", "test_id", "test_name", "risk_level", "reason", "audit_procedure"
        ])
    else:
        # Standardize sorting
        risk_order = {"High": 1, "Medium": 2, "Low": 3}
        flags_df["risk_weight"] = flags_df["risk_level"].map(risk_order).fillna(9)
        flags_df = flags_df.sort_values(by=["risk_weight", "amount"], ascending=[True, False]).drop(columns=["risk_weight"])

    # Enrich df with flag summary
    df["is_flagged"] = False
    df["flag_count"] = 0
    df["max_risk"] = "None"

    if not flags_df.empty:
        counts = flags_df.groupby("source_row_index")["test_id"].count()
        df["flag_count"] = df["source_row_index"].map(counts).fillna(0).astype(int)
        df["is_flagged"] = df["flag_count"] > 0

        # Calculate max risk per row
        row_max_risk = {}
        for row_idx, grp in flags_df.groupby("source_row_index"):
            risks = set(grp["risk_level"])
            if "High" in risks:
                row_max_risk[row_idx] = "High"
            elif "Medium" in risks:
                row_max_risk[row_idx] = "Medium"
            elif "Low" in risks:
                row_max_risk[row_idx] = "Low"
            else:
                row_max_risk[row_idx] = "None"
        df["max_risk"] = df["source_row_index"].map(row_max_risk).fillna("None")

    return df, flags_df


def perform_benford_analysis(amounts_series: pd.Series) -> Dict[str, Any]:
    """
    Perform First-Digit Benford's Law Analysis on non-zero transaction amounts.
    Uses log10(1 + 1/d) for expected proportions, and computes Chi-square goodness of fit.
    Includes auditor limitation notes adhering to SA 240 / ICAI guidance.
    """
    # Filter positive amounts
    valid_amounts = amounts_series.dropna()
    valid_amounts = valid_amounts[valid_amounts > 0]

    # Extract first non-zero digit
    def get_first_digit(val: float) -> Optional[int]:
        s = f"{val:.6f}".replace(".", "").lstrip("0")
        if len(s) > 0 and s[0].isdigit():
            d = int(s[0])
            if 1 <= d <= 9:
                return d
        return None

    digits = valid_amounts.apply(get_first_digit).dropna().astype(int)
    n = len(digits)

    # Benford theoretical probabilities
    expected_prob = {d: math.log10(1.0 + 1.0 / d) for d in range(1, 10)}
    observed_counts = {d: 0 for d in range(1, 10)}
    actual_counts = digits.value_counts().to_dict()
    for d, c in actual_counts.items():
        if d in observed_counts:
            observed_counts[d] = int(c)

    table_data = []
    obs_list = []
    exp_list = []

    for d in range(1, 10):
        obs = observed_counts[d]
        exp_prob = expected_prob[d]
        exp_count = exp_prob * n
        obs_prob = (obs / n) if n > 0 else 0.0
        diff_prob = obs_prob - exp_prob
        z_score = 0.0
        if n > 0 and (exp_prob * (1 - exp_prob)) > 0:
            std_err = math.sqrt(exp_prob * (1 - exp_prob) / n)
            z_score = diff_prob / std_err

        table_data.append({
            "Digit": d,
            "Observed Count": obs,
            "Expected Count": round(exp_count, 1),
            "Observed Proportion (%)": round(obs_prob * 100, 2),
            "Expected Proportion (%)": round(exp_prob * 100, 2),
            "Deviation (%)": round(diff_prob * 100, 2),
            "Z-Score": round(z_score, 2)
        })
        obs_list.append(obs)
        exp_list.append(exp_count)

    summary_df = pd.DataFrame(table_data)

    # Chi-square Goodness of Fit Test
    chi2_stat = np.nan
    p_value = np.nan
    is_valid_chi2 = (n >= 50) and all(exp >= 5 for exp in exp_list)

    if is_valid_chi2:
        try:
            # Rescale expected counts slightly if sum mismatch due to rounding
            exp_arr = np.array(exp_list) * (sum(obs_list) / sum(exp_list))
            if HAS_SCIPY and stats is not None:
                res = stats.chisquare(f_obs=obs_list, f_exp=exp_arr)
                chi2_stat = float(res.statistic)
                p_value = float(res.pvalue)
            else:
                # Direct Chi-Square Statistic sum((O - E)^2 / E)
                obs_arr = np.array(obs_list, dtype=float)
                chi2_stat = float(np.sum(((obs_arr - exp_arr) ** 2) / exp_arr))
                # Exact closed-form upper-tail p-value for df = 8:
                # P(X >= chi2) = e^(-z) * (1 + z + z^2/2 + z^3/6) where z = chi2 / 2
                z = chi2_stat / 2.0
                if z >= 0:
                    p_value = float(math.exp(-z) * (1.0 + z + (z ** 2) / 2.0 + (z ** 3) / 6.0))
                    p_value = max(0.0, min(1.0, p_value))
        except Exception:
            pass

    # Audit Interpretation Note
    conforms = False
    if not math.isnan(p_value):
        # Null hypothesis H0: data follows Benford's law. p < 0.05 rejects H0.
        conforms = p_value >= 0.05

    limitation_note = (
        "Statistical Note (SA 240 / ICAI Guidance):\n"
        "• Benford's Law assesses digit distributions in naturally occurring, scale-invariant datasets.\n"
        "• Deviations (p < 0.05) indicate non-conformance with theoretical distribution, but do NOT constitute proof of fraud or error.\n"
        "• Natural operational causes for deviation include: uniform price tariffs, standard recurring invoices, regulatory limits (e.g. TDS/PF thresholds), round travel allowances, or batch ledger allocations.\n"
        "• Deviations should be used solely as an exploratory pointer to guide targeted audit sampling."
    )

    return {
        "summary_df": summary_df,
        "sample_size": n,
        "chi2_stat": chi2_stat,
        "p_value": p_value,
        "degrees_of_freedom": 8,
        "is_valid_test": is_valid_chi2,
        "conforms": conforms,
        "limitation_note": limitation_note
    }


def generate_audit_sample(
    df: pd.DataFrame,
    flags_df: pd.DataFrame,
    pm: float,
    sample_high_risk: bool = True,
    random_sample_size: int = 25,
    random_seed: int = 42
) -> pd.DataFrame:
    """
    Audit Sampling Strategy distinguishing Targeted Testing from Statistical Sampling (SA 530):
    - Strata 1: 100% of items > PM (Exceeding Performance Materiality).
    - Strata 2: Targeted selection of High-Risk flagged items.
    - Strata 3: Representative Random Sample from the remaining unselected population.
    Avoids duplicate selections and tags each record with its selection method and source row.
    """
    selected_indices = set()
    sample_records = []

    # 1. Strata 1: Exceeding PM
    pm_items = df[df["amount"] > pm]
    for idx, row in pm_items.iterrows():
        src_row = int(row["source_row_index"])
        if src_row not in selected_indices:
            selected_indices.add(src_row)
            sample_records.append({
                "source_row_index": src_row,
                "voucher_number": str(row["Voucher Number"]),
                "voucher_date": row["parsed_voucher_date"].strftime("%d-%m-%Y") if pd.notna(row["parsed_voucher_date"]) else "",
                "account_name": str(row["Account/Ledger Name"]),
                "debit": float(row["parsed_debit"]) if pd.notna(row["parsed_debit"]) else 0.0,
                "credit": float(row["parsed_credit"]) if pd.notna(row["parsed_credit"]) else 0.0,
                "amount": float(row["amount"]),
                "narration": str(row["Narration"]),
                "selection_method": "Targeted: Exceeding PM (> Materiality)",
                "stratum": "Stratum 1 (Key Items)",
                "risk_level": "High"
            })

    # 2. Strata 2: High Risk Flagged Items
    if sample_high_risk and not flags_df.empty:
        high_risk_flags = flags_df[flags_df["risk_level"] == "High"]
        for _, flag in high_risk_flags.iterrows():
            src_row = int(flag["source_row_index"])
            if src_row not in selected_indices:
                selected_indices.add(src_row)
                orig_rows = df[df["source_row_index"] == src_row]
                if not orig_rows.empty:
                    orig_row = orig_rows.iloc[0]
                    sample_records.append({
                        "source_row_index": src_row,
                        "voucher_number": str(orig_row["Voucher Number"]),
                        "voucher_date": orig_row["parsed_voucher_date"].strftime("%d-%m-%Y") if pd.notna(orig_row["parsed_voucher_date"]) else "",
                        "account_name": str(orig_row["Account/Ledger Name"]),
                        "debit": float(orig_row["parsed_debit"]) if pd.notna(orig_row["parsed_debit"]) else 0.0,
                        "credit": float(orig_row["parsed_credit"]) if pd.notna(orig_row["parsed_credit"]) else 0.0,
                        "amount": float(orig_row["amount"]),
                        "narration": str(orig_row["Narration"]),
                        "selection_method": f"Targeted: High Risk Flag ({flag['test_name']})",
                        "stratum": "Stratum 2 (Risk Anomalies)",
                        "risk_level": "High"
                    })

    # 3. Strata 3: Representative Random Sample from Remaining Population
    remaining_df = df[~df["source_row_index"].isin(selected_indices)]
    actual_random_size = min(random_sample_size, len(remaining_df))
    if actual_random_size > 0:
        random_sample = remaining_df.sample(n=actual_random_size, random_state=random_seed)
        for _, row in random_sample.iterrows():
            src_row = int(row["source_row_index"])
            selected_indices.add(src_row)
            sample_records.append({
                "source_row_index": src_row,
                "voucher_number": str(row["Voucher Number"]),
                "voucher_date": row["parsed_voucher_date"].strftime("%d-%m-%Y") if pd.notna(row["parsed_voucher_date"]) else "",
                "account_name": str(row["Account/Ledger Name"]),
                "debit": float(row["parsed_debit"]) if pd.notna(row["parsed_debit"]) else 0.0,
                "credit": float(row["parsed_credit"]) if pd.notna(row["parsed_credit"]) else 0.0,
                "amount": float(row["amount"]),
                "narration": str(row["Narration"]),
                "selection_method": "Representative: Unbiased Random Sample",
                "stratum": "Stratum 3 (Remaining Population)",
                "risk_level": str(row.get("max_risk", "Low"))
            })

    sample_df = pd.DataFrame(sample_records)
    if sample_df.empty:
        return pd.DataFrame(columns=[
            "source_row_index", "voucher_number", "voucher_date", "account_name",
            "debit", "credit", "amount", "narration", "selection_method", "stratum", "risk_level"
        ])

    return sample_df.sort_values(by="source_row_index").reset_index(drop=True)
