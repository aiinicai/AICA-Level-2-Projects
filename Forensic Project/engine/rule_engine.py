"""
Core Rule Engine for Red Flag Forensic Accounting.
Loads rules from YAML files, manages registration, evaluates constraints,
and executes all 44 deterministic rules and 4 forensic models.
"""
import os
import re
import glob
import math
from typing import Callable, Dict, List, Any, Optional, Tuple
import yaml
import pandas as pd
import numpy as np

from engine.derive import load_group_nature
from engine.statistical import (
    compute_benford_first_digit,
    compute_rsf,
    fuzzy_find_duplicates,
    compute_unsupervised_outliers
)
from engine.models import (
    compute_beneish_m_score,
    compute_altman_z_score,
    compute_sloan_accrual,
    compute_piotroski_f_score
)

# Registry for rule functions
_RULE_REGISTRY: Dict[str, Callable] = {}

def rule(rule_id: str):
    """Decorator to register a rule function by its ID."""
    def decorator(fn: Callable):
        _RULE_REGISTRY[rule_id] = fn
        return fn
    return decorator

def load_rules_from_yaml(rules_dir: str = "rules") -> List[Dict[str, Any]]:
    """Load all rule definitions from YAML files in the rules directory."""
    rules_list = []
    yaml_files = sorted(glob.glob(os.path.join(rules_dir, "*.yaml")))
    for yf in yaml_files:
        if "methods_registry" in os.path.basename(yf):
            continue
        with open(yf, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, list):
                rules_list.extend(data)
    return rules_list

def load_lexicons(config_path: str = "config/lexicons.yaml") -> Dict[str, Any]:
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

# =====================================================================
# MODULE TB: TRIAL BALANCE STRUCTURE (14 RULES)
# =====================================================================

@rule("TB-01")
def tb_01(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """TB-01: For each fy: abs(Σclosing_dr − Σclosing_cr) > tolerance"""
    tol = cfg.get("params", {}).get("tolerance", 1.0)
    exceptions = []
    for fy in sorted(ledgers["fy"].unique()):
        df_fy = ledgers[ledgers["fy"] == fy]
        dr_sum = float(df_fy["closing_dr"].sum())
        cr_sum = float(df_fy["closing_cr"].sum())
        diff = abs(dr_sum - cr_sum)
        if diff > tol:
            exceptions.append({
                "rule_id": "TB-01",
                "fy": fy,
                "subject": f"Trial Balance {fy}",
                "observed_value": round(diff, 2),
                "threshold_value": tol,
                "exception_value": diff,
                "detail": f"Sum Dr ({dr_sum:,.2f}) != Sum Cr ({cr_sum:,.2f}), difference = {diff:,.2f}"
            })
    return exceptions

@rule("TB-02")
def tb_02(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """TB-02: Abnormal balance sign relative to Schedule III nature."""
    group_nature_map = load_group_nature()
    tol = cfg.get("params", {}).get("tolerance", 1.0)
    exceptions = []
    
    for idx, row in ledgers.iterrows():
        grp = row["group"]
        c_net = row["closing_net"]
        name = row["ledger_name"]
        fy = row["fy"]
        
        expected_sign = None
        if grp in group_nature_map:
            expected_sign = group_nature_map[grp].get("expected_sign")
            
        grp_lower = str(grp).lower()
        if expected_sign == "debit" and c_net < -tol:
            exceptions.append({
                "rule_id": "TB-02",
                "fy": fy,
                "subject": name,
                "observed_value": round(c_net, 2),
                "threshold_value": 0.0,
                "exception_value": abs(c_net),
                "detail": f"Debit nature group '{grp}' has credit balance ({c_net:,.2f})",
                "group": grp,
                "expected_sign": "debit",
            })
        elif expected_sign == "credit" and c_net > tol:
            exceptions.append({
                "rule_id": "TB-02",
                "fy": fy,
                "subject": name,
                "observed_value": round(c_net, 2),
                "threshold_value": 0.0,
                "exception_value": abs(c_net),
                "detail": f"Credit nature group '{grp}' has debit balance ({c_net:,.2f})",
                "group": grp,
                "expected_sign": "credit",
            })
        elif any(k in grp_lower for k in ["cash", "bank", "inventor", "stock"]) and c_net < -tol:
            exceptions.append({
                "rule_id": "TB-02",
                "fy": fy,
                "subject": name,
                "observed_value": round(c_net, 2),
                "threshold_value": 0.0,
                "exception_value": abs(c_net),
                "detail": f"Cash/Bank/Inventory account overdrawn ({c_net:,.2f})",
                "group": grp,
                "expected_sign": "debit",
            })
    return exceptions

@rule("TB-03")
def tb_03(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """TB-03: Suspense or control ledger carrying a year-end balance."""
    m = params.get("performance_materiality", 500000.0)
    p_cfg = cfg.get("params", {})
    patterns = p_cfg.get("name_patterns", ["suspense", "difference", "control", "clearing", "unadjusted"])
    min_pct = p_cfg.get("min_balance_pct_of_materiality", 0.25)
    threshold = min_pct * m
    
    exceptions = []
    for idx, row in ledgers.iterrows():
        name_lower = row["ledger_name"].lower()
        if any(p in name_lower for p in patterns):
            bal = abs(row["closing_net"])
            if bal > threshold:
                exceptions.append({
                    "rule_id": "TB-03",
                    "fy": row["fy"],
                    "subject": row["ledger_name"],
                    "observed_value": round(row["closing_net"], 2),
                    "threshold_value": round(threshold, 2),
                    "exception_value": bal,
                    "detail": f"Suspense ledger carries closing balance of {row['closing_net']:,.2f} (> {min_pct*100}% materiality)"
                })
    return exceptions

@rule("TB-04")
def tb_04(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """TB-04: High-value round-number closing balances."""
    m = params.get("performance_materiality", 500000.0)
    p_cfg = cfg.get("params", {})
    round_base = p_cfg.get("round_base", 100000)
    min_pct = p_cfg.get("min_materiality_pct", 0.20)
    threshold = min_pct * m
    
    exceptions = []
    for idx, row in ledgers.iterrows():
        bal = abs(row["closing_net"])
        if bal >= threshold and bal > 0:
            if int(bal) % round_base == 0 and abs(bal - int(bal)) < 0.01:
                exceptions.append({
                    "rule_id": "TB-04",
                    "fy": row["fy"],
                    "subject": row["ledger_name"],
                    "observed_value": round(row["closing_net"], 2),
                    "threshold_value": round_base,
                    "exception_value": bal,
                    "detail": f"Exact multiple of Rs. {round_base:,}: balance {row['closing_net']:,.2f}"
                })
    return exceptions

@rule("TB-05")
def tb_05(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """TB-05: Vague or generic ledger description with material balance."""
    m = params.get("performance_materiality", 500000.0)
    p_cfg = cfg.get("params", {})
    keywords = p_cfg.get("keywords", ["misc", "sundry", "other", "adjustment", "imprest", "unknown", "general", "temporary"])
    min_pct = p_cfg.get("min_materiality_pct", 0.50)
    threshold = min_pct * m
    
    exceptions = []
    for idx, row in ledgers.iterrows():
        # Exclude standard Sundry Debtors / Sundry Creditors group headers from trigger
        name_lower = row["ledger_name"].lower()
        if any(kw in name_lower for kw in keywords):
            bal = abs(row["closing_net"])
            if bal > threshold:
                exceptions.append({
                    "rule_id": "TB-05",
                    "fy": row["fy"],
                    "subject": row["ledger_name"],
                    "observed_value": round(row["closing_net"], 2),
                    "threshold_value": round(threshold, 2),
                    "exception_value": bal,
                    "detail": f"Generic/vague ledger with balance {row['closing_net']:,.2f} exceeding {min_pct*100}% materiality"
                })
    return exceptions

@rule("TB-06")
def tb_06(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """TB-06: Near-duplicate counterparty names within the same group."""
    p_cfg = cfg.get("params", {})
    thresh = p_cfg.get("fuzzy_threshold", 88.0)
    exceptions = []
    
    for fy in sorted(ledgers["fy"].unique()):
        df_fy = ledgers[ledgers["fy"] == fy]
        for grp in df_fy["group"].unique():
            names = df_fy[df_fy["group"] == grp]["ledger_name"].tolist()
            if len(names) < 2:
                continue
            dups = fuzzy_find_duplicates(names, threshold=thresh)
            for n1, n2, score, m_type in dups:
                exceptions.append({
                    "rule_id": "TB-06",
                    "fy": fy,
                    "subject": f"{n1} <-> {n2}",
                    "observed_value": score,
                    "threshold_value": thresh,
                    "exception_value": None,
                    "detail": f"Group '{grp}': Near-duplicate '{n1}' and '{n2}' (Score: {score:.1f}, {m_type})",
                    "group": grp,
                    "name_1": n1,
                    "name_2": n2,
                    "match_type": m_type,
                })
    return exceptions

@rule("TB-07")
def tb_07(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """TB-07: High-turnover ledger squaring to near-zero balance at year end."""
    m = params.get("performance_materiality", 500000.0)
    p_cfg = cfg.get("params", {})
    pct_thresh = p_cfg.get("closing_pct_threshold", 0.01)
    
    exceptions = []
    for idx, row in ledgers.iterrows():
        tot_turn = row["turnover_total"]
        c_net = abs(row["closing_net"])
        if tot_turn > m and c_net < (pct_thresh * tot_turn):
            exceptions.append({
                "rule_id": "TB-07",
                "fy": row["fy"],
                "subject": row["ledger_name"],
                "observed_value": round(c_net, 2),
                "threshold_value": round(pct_thresh * tot_turn, 2),
                "exception_value": tot_turn,
                "detail": f"Turnover {tot_turn:,.2f} (> M) squares to closing balance {row['closing_net']:,.2f} (< 1% turnover)",
                "turnover_total": f"{tot_turn:,.2f}",
                "closing_net": f"{row['closing_net']:,.2f}",
            })
    return exceptions

@rule("TB-08")
def tb_08(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """TB-08: Personal names in expense or creditor groups."""
    lexicons = load_lexicons()
    suffixes = lexicons.get("corporate_suffixes", ["ltd", "pvt", "llp", "& co", "enterprises", "traders", "industries", "services", "corporation", "associates"])
    
    exceptions = []
    for idx, row in ledgers.iterrows():
        grp = str(row["group"]).lower()
        if not (any(k in grp for k in ["expense", "creditor", "payable", "admin", "consulting", "professional"])):
            continue
            
        name = re.sub(r'^(sundry creditors\s*—\s*|direct expenses\s*—\s*|indirect expenses\s*—\s*)', '', row["ledger_name"], flags=re.IGNORECASE).strip()
        tokens = [t for t in re.split(r'[\s,\-_]+', name) if t.isalpha()]
        
        # Check if 2-3 alphabetic tokens and no corporate suffix
        if 2 <= len(tokens) <= 3:
            name_lower = name.lower()
            if not any(suf in name_lower for suf in suffixes):
                exceptions.append({
                    "rule_id": "TB-08",
                    "fy": row["fy"],
                    "subject": row["ledger_name"],
                    "observed_value": round(row["closing_net"], 2),
                    "threshold_value": None,
                    "exception_value": abs(row["closing_net"]),
                    "detail": f"Ledger '{row['ledger_name']}' in group '{row['group']}' matches personal name pattern"
                })
    return exceptions

@rule("TB-09")
def tb_09(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """TB-09: Ledger name token conflicts with assigned Schedule III group."""
    lexicons = load_lexicons()
    token_group_map = lexicons.get("token_group_map", {})
    
    exceptions = []
    for idx, row in ledgers.iterrows():
        name_lower = row["ledger_name"].lower()
        grp_clean = row["group"]
        
        for token, expected_grps in token_group_map.items():
            if re.search(r'\b' + re.escape(token) + r'\b', name_lower):
                # If current group is not in expected groups
                if not any(eg.lower() in grp_clean.lower() for eg in expected_grps):
                    exceptions.append({
                        "rule_id": "TB-09",
                        "fy": row["fy"],
                        "subject": row["ledger_name"],
                        "observed_value": grp_clean,
                        "threshold_value": ", ".join(expected_grps),
                        "exception_value": abs(row["closing_net"]),
                        "detail": f"Token '{token}' in ledger '{row['ledger_name']}' conflicts with group '{grp_clean}'",
                        "token": token,
                        "group": grp_clean,
                        "expected_groups": ", ".join(expected_grps),
                    })
                    break
    return exceptions

@rule("TB-10")
def tb_10(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """TB-10: Excessive cash on hand relative to scale of operations."""
    p_cfg = cfg.get("params", {})
    rev_pct = p_cfg.get("revenue_pct", 0.02)
    min_abs = p_cfg.get("min_absolute", 500000.0)
    
    exceptions = []
    for fy in sorted(ledgers["fy"].unique()):
        df_fy = ledgers[ledgers["fy"] == fy]
        cash_hand = df_fy[df_fy["group"].str.contains(r'cash-in-hand|cash in hand|petty cash', case=False, na=False)]["closing_dr"].sum()
        
        # Get revenue
        rev_row = derived[derived["fy"] == fy]
        rev = float(rev_row["revenue"].iloc[0]) if len(rev_row) > 0 else 0.0
        thresh = max(rev_pct * rev, min_abs)
        
        if cash_hand > thresh:
            exceptions.append({
                "rule_id": "TB-10",
                "fy": fy,
                "subject": f"Cash-in-Hand ({fy})",
                "observed_value": round(cash_hand, 2),
                "threshold_value": round(thresh, 2),
                "exception_value": cash_hand,
                "detail": f"Cash on hand of {cash_hand:,.2f} exceeds threshold {thresh:,.2f} (2% of revenue / 5L)"
            })
    return exceptions

@rule("TB-11")
def tb_11(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """TB-11: Loans and advances to related parties > 10% of net worth."""
    p_cfg = cfg.get("params", {})
    pct_thresh = p_cfg.get("net_worth_pct", 0.10)
    
    exceptions = []
    for fy in sorted(ledgers["fy"].unique()):
        d_row = derived[derived["fy"] == fy]
        if len(d_row) == 0:
            continue
        nw = float(d_row["net_worth"].iloc[0])
        rp_bal = float(d_row["related_party_balance"].iloc[0])
        
        if nw > 0 and (rp_bal / nw) > pct_thresh:
            exceptions.append({
                "rule_id": "TB-11",
                "fy": fy,
                "subject": f"Related Party Exposure ({fy})",
                "observed_value": round(rp_bal, 2),
                "threshold_value": round(pct_thresh * nw, 2),
                "exception_value": rp_bal,
                "detail": f"Related party balance {rp_bal:,.2f} represents {(rp_bal/nw)*100:.1f}% of net worth (threshold: 10%)"
            })
    return exceptions

@rule("TB-12")
def tb_12(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """TB-12: Benford first-digit non-conformity in ledger balances."""
    p_cfg = cfg.get("params", {})
    min_rec = p_cfg.get("min_records", 300)
    mad_thresh = p_cfg.get("mad_threshold", 0.015)
    
    exceptions = []
    for fy in sorted(ledgers["fy"].unique()):
        df_fy = ledgers[ledgers["fy"] == fy]
        vals = df_fy["closing_net"].abs().tolist()
        b_res = compute_benford_first_digit(vals, min_records=min_rec)
        if b_res["can_run"] and b_res["mad"] > mad_thresh:
            conf = min(1.0, b_res["mad"] / mad_thresh)
            exceptions.append({
                "rule_id": "TB-12",
                "fy": fy,
                "subject": f"Ledger Cohort ({fy})",
                "observed_value": round(b_res["mad"], 4),
                "threshold_value": mad_thresh,
                "exception_value": None,
                "confidence": round(conf, 2),
                "detail": f"Benford first-digit MAD of {b_res['mad']:.4f} indicates {b_res['conformity']}"
            })
    return exceptions

@rule("TB-13")
def tb_13(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """TB-13: Relative Size Factor (RSF) anomaly within group."""
    p_cfg = cfg.get("params", {})
    min_grp = p_cfg.get("min_group_records", 5)
    rsf_thresh = p_cfg.get("rsf_threshold", 10.0)
    
    exceptions = []
    for fy in sorted(ledgers["fy"].unique()):
        df_fy = ledgers[ledgers["fy"] == fy]
        for grp in df_fy["group"].unique():
            grp_ledgers = df_fy[df_fy["group"] == grp]
            if len(grp_ledgers) < min_grp:
                continue
            vals = grp_ledgers["closing_net"].abs().tolist()
            rsf, largest, second = compute_rsf(vals)
            if rsf > rsf_thresh:
                top_row = grp_ledgers[grp_ledgers["closing_net"].abs() == largest].iloc[0]
                exceptions.append({
                    "rule_id": "TB-13",
                    "fy": fy,
                    "subject": f"{grp} / {top_row['ledger_name']}",
                    "observed_value": round(rsf, 2),
                    "threshold_value": rsf_thresh,
                    "exception_value": largest,
                    "detail": f"Group '{grp}': largest ledger '{top_row['ledger_name']}' ({largest:,.2f}) is {rsf:.1f}x second largest ({second:,.2f})"
                })
    return exceptions

@rule("TB-14")
def tb_14(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """TB-14: Equal high-volume debit and credit turnover with negligible balance."""
    m = params.get("performance_materiality", 500000.0)
    p_cfg = cfg.get("params", {})
    diff_thresh = p_cfg.get("diff_pct_threshold", 0.02)
    cl_thresh = p_cfg.get("closing_pct_threshold", 0.01)
    
    exceptions = []
    for idx, row in ledgers.iterrows():
        t_dr = row["turnover_dr"]
        t_cr = row["turnover_cr"]
        c_net = abs(row["closing_net"])
        
        if t_dr > m and t_cr > m:
            max_t = max(t_dr, t_cr)
            if abs(t_dr - t_cr) / max_t < diff_thresh and c_net < (cl_thresh * t_dr):
                exceptions.append({
                    "rule_id": "TB-14",
                    "fy": row["fy"],
                    "subject": row["ledger_name"],
                    "observed_value": round(abs(t_dr - t_cr), 2),
                    "threshold_value": round(diff_thresh * max_t, 2),
                    "exception_value": max_t,
                    "detail": f"Turnover Dr ({t_dr:,.2f}) & Cr ({t_cr:,.2f}) matched within 2% with closing balance {row['closing_net']:,.2f}",
                    "turnover_dr": f"{t_dr:,.2f}",
                    "turnover_cr": f"{t_cr:,.2f}",
                    "closing_net": f"{row['closing_net']:,.2f}",
                })
    return exceptions

# =====================================================================
# MODULE LG: LEDGER TREND ACROSS YEARS (10 RULES - min_years: 3)
# =====================================================================

@rule("LG-01")
def lg_01(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """LG-01: Ledger absent in fy1 and fy2, present in fy3 with closing_net > M."""
    m = params.get("performance_materiality", 500000.0)
    fys = sorted(ledgers["fy"].unique())
    fy1, fy2, fy3 = fys[0], fys[1], fys[2]
    
    piv = ledgers.pivot(index="ledger_name", columns="fy", values="closing_net").fillna(0.0)
    exceptions = []
    
    for lname, row in piv.iterrows():
        c1 = abs(row.get(fy1, 0.0))
        c2 = abs(row.get(fy2, 0.0))
        c3 = abs(row.get(fy3, 0.0))
        
        if c1 < 1.0 and c2 < 1.0 and c3 > m:
            exceptions.append({
                "rule_id": "LG-01",
                "fy": fy3,
                "subject": lname,
                "observed_value": round(row.get(fy3, 0.0), 2),
                "threshold_value": m,
                "exception_value": c3,
                "detail": f"New ledger appeared in {fy3} with balance {row.get(fy3, 0.0):,.2f} after zero balance in {fy1} and {fy2}"
            })
    return exceptions

@rule("LG-02")
def lg_02(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """LG-02: Present in fy1 > M, absent in fy3 without identified write-off."""
    m = params.get("performance_materiality", 500000.0)
    fys = sorted(ledgers["fy"].unique())
    fy1, fy2, fy3 = fys[0], fys[1], fys[2]
    
    piv = ledgers.pivot(index="ledger_name", columns="fy", values="closing_net").fillna(0.0)
    exceptions = []
    
    for lname, row in piv.iterrows():
        c1 = abs(row.get(fy1, 0.0))
        c3 = abs(row.get(fy3, 0.0))
        if c1 > m and c3 < 1.0:
            exceptions.append({
                "rule_id": "LG-02",
                "fy": fy3,
                "subject": lname,
                "observed_value": round(row.get(fy1, 0.0), 2),
                "threshold_value": m,
                "exception_value": c1,
                "detail": f"Ledger with balance {row.get(fy1, 0.0):,.2f} in {fy1} disappeared by {fy3} without offsetting write-off"
            })
    return exceptions

@rule("LG-03")
def lg_03(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """LG-03: Sign flips between consecutive years where both > 0.25*M."""
    m = params.get("performance_materiality", 500000.0)
    thresh = 0.25 * m
    fys = sorted(ledgers["fy"].unique())
    piv = ledgers.pivot(index="ledger_name", columns="fy", values="closing_net").fillna(0.0)
    exceptions = []
    
    for lname, row in piv.iterrows():
        for i in range(len(fys) - 1):
            y_prev, y_curr = fys[i], fys[i+1]
            v_prev = row.get(y_prev, 0.0)
            v_curr = row.get(y_curr, 0.0)
            
            if abs(v_prev) > thresh and abs(v_curr) > thresh:
                if (v_prev > 0 and v_curr < 0) or (v_prev < 0 and v_curr > 0):
                    exceptions.append({
                        "rule_id": "LG-03",
                        "fy": y_curr,
                        "subject": lname,
                        "observed_value": f"{v_prev:,.0f} -> {v_curr:,.0f}",
                        "threshold_value": thresh,
                        "exception_value": max(abs(v_prev), abs(v_curr)),
                        "detail": f"Sign flip from {v_prev:,.2f} ({y_prev}) to {v_curr:,.2f} ({y_curr})"
                    })
    return exceptions

@rule("LG-04")
def lg_04(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """LG-04: Outlier growth in ledger balance relative to group cohort (z > 3)."""
    p_cfg = cfg.get("params", {})
    min_cohort = p_cfg.get("min_cohort_size", 10)
    z_thresh = p_cfg.get("z_threshold", 3.0)
    fys = sorted(ledgers["fy"].unique())
    fy1, fy3 = fys[0], fys[-1]
    
    exceptions = []
    for grp in ledgers["group"].unique():
        grp_df = ledgers[ledgers["group"] == grp]
        piv = grp_df.pivot(index="ledger_name", columns="fy", values="closing_net").fillna(0.0)
        if len(piv) < min_cohort:
            continue
            
        growths = []
        valid_ledgers = []
        for lname, row in piv.iterrows():
            c1 = row.get(fy1, 0.0)
            c3 = row.get(fy3, 0.0)
            if abs(c1) > 1000.0:
                g = (c3 / c1) - 1.0
                growths.append(g)
                valid_ledgers.append((lname, g, c1, c3))
                
        if len(growths) < min_cohort:
            continue
            
        mean_g = float(np.mean(growths))
        std_g = float(np.std(growths))
        if std_g < 0.001:
            continue
            
        for lname, g, c1, c3 in valid_ledgers:
            z = (g - mean_g) / std_g
            if z > z_thresh:
                exceptions.append({
                    "rule_id": "LG-04",
                    "fy": fy3,
                    "subject": f"{grp} / {lname}",
                    "observed_value": round(z, 2),
                    "threshold_value": z_thresh,
                    "exception_value": abs(c3 - c1),
                    "detail": f"Ledger grew {g*100:.1f}% ({fy1}->{fy3}) vs cohort mean {mean_g*100:.1f}% (Z-score: {z:.2f})",
                    "growth_pct": f"{g*100:.1f}",
                    "z_score": f"{z:.2f}",
                    "cohort_mean_pct": f"{mean_g*100:.1f}",
                    "group": grp,
                    "ledger_name": lname,
                })
    return exceptions

@rule("LG-05")
def lg_05(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """LG-05: Stagnant unchanging material balance across three consecutive years."""
    m = params.get("performance_materiality", 500000.0)
    p_cfg = cfg.get("params", {})
    tol = p_cfg.get("tolerance", 1.0)
    fys = sorted(ledgers["fy"].unique())
    fy1, fy2, fy3 = fys[0], fys[1], fys[2]
    
    piv = ledgers.pivot(index="ledger_name", columns="fy", values="closing_net").fillna(0.0)
    exceptions = []
    
    for lname, row in piv.iterrows():
        c1 = row.get(fy1, 0.0)
        c2 = row.get(fy2, 0.0)
        c3 = row.get(fy3, 0.0)
        
        if abs(c1) > m and abs(c1 - c2) <= tol and abs(c2 - c3) <= tol:
            exceptions.append({
                "rule_id": "LG-05",
                "fy": fy3,
                "subject": lname,
                "observed_value": round(c3, 2),
                "threshold_value": m,
                "exception_value": abs(c3),
                "detail": f"Stagnant balance of {c3:,.2f} unchanged across {fy1}, {fy2}, {fy3}"
            })
    return exceptions

@rule("LG-06")
def lg_06(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """LG-06: Expense group growth > 25% while revenue growth < 5%."""
    p_cfg = cfg.get("params", {})
    exp_growth_min = p_cfg.get("expense_growth_min", 0.25)
    rev_growth_max = p_cfg.get("revenue_growth_max", 0.05)
    
    fys = sorted(ledgers["fy"].unique())
    fy1, fy3 = fys[0], fys[-1]
    
    rev_1 = float(derived[derived["fy"] == fy1]["revenue"].iloc[0]) if len(derived[derived["fy"] == fy1]) > 0 else 1.0
    rev_3 = float(derived[derived["fy"] == fy3]["revenue"].iloc[0]) if len(derived[derived["fy"] == fy3]) > 0 else 1.0
    rev_growth = (rev_3 - rev_1) / rev_1 if rev_1 > 0 else 0.0
    
    exceptions = []
    # Test each expense group or specific anomalous expense groups
    expense_groups = [g for g in ledgers["group"].unique() if any(k in g.lower() for k in ["expense", "administrative", "selling", "consultancy", "professional", "indirect"])]
    
    for grp in expense_groups:
        e1 = float(ledgers[(ledgers["group"] == grp) & (ledgers["fy"] == fy1)]["closing_dr"].sum())
        e3 = float(ledgers[(ledgers["group"] == grp) & (ledgers["fy"] == fy3)]["closing_dr"].sum())
        if e1 > 10000.0:
            exp_growth = (e3 - e1) / e1
            if exp_growth > exp_growth_min and (rev_growth < rev_growth_max or exp_growth > (rev_growth + 0.20)):
                exceptions.append({
                    "rule_id": "LG-06",
                    "fy": fy3,
                    "subject": f"Expense Group: {grp}",
                    "observed_value": f"{exp_growth*100:.1f}%",
                    "threshold_value": f"{exp_growth_min*100:.1f}%",
                    "exception_value": abs(e3 - e1),
                    "detail": f"Expense group '{grp}' grew {exp_growth*100:.1f}% ({e1:,.0f} -> {e3:,.0f}) while revenue growth was {rev_growth*100:.1f}%",
                    "group": grp,
                    "expense_growth_pct": f"{exp_growth*100:.1f}",
                    "revenue_growth_pct": f"{rev_growth*100:.1f}",
                })
    return exceptions

@rule("LG-07")
def lg_07(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """LG-07: For all three years: turnover_total > M AND abs(closing_net) < 0.01 * turnover_total."""
    m = params.get("performance_materiality", 500000.0)
    p_cfg = cfg.get("params", {})
    cl_pct = p_cfg.get("closing_pct_threshold", 0.01)
    fys = sorted(ledgers["fy"].unique())
    
    piv_tot = ledgers.pivot(index="ledger_name", columns="fy", values="turnover_total").fillna(0.0)
    piv_cl = ledgers.pivot(index="ledger_name", columns="fy", values="closing_net").fillna(0.0)
    exceptions = []
    
    for lname in piv_tot.index:
        all_match = True
        tot_sum = 0.0
        for fy in fys:
            t = piv_tot.loc[lname, fy]
            c = abs(piv_cl.loc[lname, fy])
            tot_sum += t
            if not (t > m and c < (cl_pct * t)):
                all_match = False
                break
                
        if all_match:
            exceptions.append({
                "rule_id": "LG-07",
                "fy": fys[-1],
                "subject": lname,
                "observed_value": round(tot_sum, 2),
                "threshold_value": m,
                "exception_value": tot_sum,
                "detail": f"Ledger '{lname}' maintains turnover > M and squares to nil across all 3 years"
            })
    return exceptions

@rule("LG-08")
def lg_08(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """LG-08: Inverted V-spike or trough pattern (each leg > 30% and peak > M)."""
    m = params.get("performance_materiality", 500000.0)
    p_cfg = cfg.get("params", {})
    leg_pct = p_cfg.get("leg_pct_threshold", 0.30)
    fys = sorted(ledgers["fy"].unique())
    fy1, fy2, fy3 = fys[0], fys[1], fys[2]
    
    piv = ledgers.pivot(index="ledger_name", columns="fy", values="closing_net").fillna(0.0)
    exceptions = []
    
    for lname, row in piv.iterrows():
        v1 = abs(row.get(fy1, 0.0))
        v2 = abs(row.get(fy2, 0.0))
        v3 = abs(row.get(fy3, 0.0))
        
        # Peak in year 2: v2 > v1 and v2 > v3
        if v2 > m and (v2 - v1) > (leg_pct * (v1 + 1.0)) and (v2 - v3) > (leg_pct * (v3 + 1.0)):
            exceptions.append({
                "rule_id": "LG-08",
                "fy": fy2,
                "subject": lname,
                "observed_value": round(v2, 2),
                "threshold_value": m,
                "exception_value": v2,
                "detail": f"Inverted V-spike: {v1:,.0f} ({fy1}) -> {v2:,.0f} ({fy2}) -> {v3:,.0f} ({fy3})",
                "fy1": fy1, "fy2": fy2, "fy3": fy3,
                "val_fy1": f"{v1:,.0f}", "val_fy2": f"{v2:,.0f}", "val_fy3": f"{v3:,.0f}",
                "peak_val": f"{v2:,.0f}", "peak_fy": fy2,
            })
    return exceptions

@rule("LG-09")
def lg_09(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """LG-09: Strictly increasing proportion of misc/vague expenses across 3 years."""
    p_cfg = cfg.get("params", {})
    r3_thresh = p_cfg.get("ratio_fy3_threshold", 0.05)
    fys = sorted(ledgers["fy"].unique())
    
    lexicons = load_lexicons()
    keywords = lexicons.get("vague_keywords", ["misc", "sundry", "other", "adjustment", "imprest", "unknown", "general", "temporary"])
    
    ratios = []
    for fy in fys:
        df_fy = ledgers[ledgers["fy"] == fy]
        exp_df = df_fy[df_fy["group"].str.contains(r'expense|admin|selling', case=False, na=False)]
        tot_exp = exp_df["closing_dr"].sum()
        if tot_exp > 0:
            misc_mask = exp_df["ledger_name"].str.contains("|".join(keywords), case=False, na=False)
            misc_exp = exp_df[misc_mask]["closing_dr"].sum()
            ratios.append(misc_exp / tot_exp)
        else:
            ratios.append(0.0)
            
    if len(ratios) == 3 and (ratios[0] < ratios[1] < ratios[2]) and ratios[2] > r3_thresh:
        return [{
            "rule_id": "LG-09",
            "fy": fys[2],
            "subject": "Miscellaneous Expenses Proportion",
            "observed_value": f"{ratios[2]*100:.2f}%",
            "threshold_value": f"{r3_thresh*100:.2f}%",
            "exception_value": None,
            "detail": f"Misc expense proportion increased strictly: {ratios[0]*100:.1f}% -> {ratios[1]*100:.1f}% -> {ratios[2]*100:.1f}%"
        }]
    return []

@rule("LG-10")
def lg_10(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """LG-10: Top-5 debtor share of total receivables strictly increasing AND fy3 > 0.60."""
    p_cfg = cfg.get("params", {})
    r3_thresh = p_cfg.get("ratio_fy3_threshold", 0.60)
    fys = sorted(ledgers["fy"].unique())
    
    shares = []
    for fy in fys:
        df_fy = ledgers[ledgers["fy"] == fy]
        debtors = df_fy[df_fy["group"].str.contains(r'debtor|receivable', case=False, na=False)]
        tot_rec = debtors["closing_dr"].sum()
        if tot_rec > 0:
            top5 = debtors.nlargest(5, "closing_dr")["closing_dr"].sum()
            shares.append(top5 / tot_rec)
        else:
            shares.append(0.0)
            
    if len(shares) == 3 and (shares[0] < shares[1] < shares[2]) and shares[2] > r3_thresh:
        return [{
            "rule_id": "LG-10",
            "fy": fys[2],
            "subject": "Top-5 Debtor Concentration",
            "observed_value": f"{shares[2]*100:.1f}%",
            "threshold_value": f"{r3_thresh*100:.1f}%",
            "exception_value": None,
            "detail": f"Top 5 debtor share rose: {shares[0]*100:.1f}% -> {shares[1]*100:.1f}% -> {shares[2]*100:.1f}%"
        }]
    return []

# =====================================================================
# MODULE FS: STATEMENT LEVEL (16 RULES)
# =====================================================================

@rule("FS-01")
def fs_01(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-01: PAT > 0 AND cfo_indirect < 0 for >= 2 of 3 years."""
    divergent_years = []
    for idx, row in derived.iterrows():
        pat = row["pat"]
        cfo = row["cfo_indirect"]
        if cfo is not None and pat > 0 and cfo < 0:
            divergent_years.append(row["fy"])
            
    if len(divergent_years) >= 2:
        return [{
            "rule_id": "FS-01",
            "fy": ", ".join(divergent_years),
            "subject": "PAT vs Operating Cash Flow",
            "observed_value": f"{len(divergent_years)} / {len(derived)} years",
            "threshold_value": "2 years",
            "exception_value": None,
            "detail": f"Positive PAT accompanied by negative CFO in {len(divergent_years)} years ({', '.join(divergent_years)})"
        }]
    return []

@rule("FS-02")
def fs_02(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-02: GREEN FLAG - revenue_growth > peer.mean + 2*peer.std OR np_margin > peer.mean + 2*peer.std."""
    peers = params.get("peer_ratios", {})
    if not peers:
        return []
    exceptions = []
    for i in range(1, len(derived)):
        row_prev = derived.iloc[i-1]
        row_curr = derived.iloc[i]
        
        rev_prev = row_prev["revenue"]
        rev_curr = row_curr["revenue"]
        rev_growth = (rev_curr - rev_prev) / rev_prev if rev_prev > 0 else 0.0
        np_margin = row_curr["pat"] / rev_curr if rev_curr > 0 else 0.0
        
        if "revenue_growth" in peers:
            p_mean = peers["revenue_growth"].get("mean", 0.0)
            p_std = peers["revenue_growth"].get("std", 0.05)
            if rev_growth > (p_mean + 2.0 * p_std):
                exceptions.append({
                    "rule_id": "FS-02",
                    "fy": row_curr["fy"],
                    "subject": "Revenue Growth vs Industry",
                    "observed_value": f"{rev_growth*100:.1f}%",
                    "threshold_value": f"{(p_mean + 2*p_std)*100:.1f}%",
                    "exception_value": None,
                    "detail": f"Revenue growth of {rev_growth*100:.1f}% exceeds peer benchmark by > 2σ"
                })
        if "np_margin" in peers:
            p_mean = peers["np_margin"].get("mean", 0.0)
            p_std = peers["np_margin"].get("std", 0.02)
            if np_margin > (p_mean + 2.0 * p_std):
                exceptions.append({
                    "rule_id": "FS-02",
                    "fy": row_curr["fy"],
                    "subject": "NP Margin vs Industry",
                    "observed_value": f"{np_margin*100:.1f}%",
                    "threshold_value": f"{(p_mean + 2*p_std)*100:.1f}%",
                    "exception_value": None,
                    "detail": f"Net Profit margin of {np_margin*100:.1f}% exceeds peer benchmark by > 2σ"
                })
    return exceptions

@rule("FS-03")
def fs_03(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-03: Ratio deviation from peer benchmarks > 2 standard deviations."""
    peers = params.get("peer_ratios", {})
    if not peers:
        return []
    exceptions = []
    for idx, row in derived.iterrows():
        rev = max(1.0, row["revenue"])
        ta = max(1.0, row["total_assets"])
        nw = max(1.0, row["net_worth"])
        
        ratios = {
            "gp_margin": row["gross_profit"] / rev,
            "np_margin": row["pat"] / rev,
            "asset_turnover": rev / ta,
            "debt_equity": (row["lt_borrowings"] + row["wc_borrowings"]) / nw
        }
        for r_name, r_val in ratios.items():
            if r_name in peers:
                p_m = peers[r_name].get("mean", 0.0)
                p_s = peers[r_name].get("std", 1.0)
                if p_s > 0:
                    z = abs(r_val - p_m) / p_s
                    if z > 2.0:
                        exceptions.append({
                            "rule_id": "FS-03",
                            "fy": row["fy"],
                            "subject": f"Peer Ratio: {r_name}",
                            "observed_value": round(r_val, 4),
                            "threshold_value": round(p_m, 4),
                            "exception_value": None,
                            "detail": f"{r_name} of {r_val:.4f} deviates by {z:.2f}σ from peer mean ({p_m:.4f})"
                        })
    return exceptions

@rule("FS-04")
def fs_04(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-04: Debtor days rise > 30% YoY OR receivables_growth > 1.5 * revenue_growth."""
    p_cfg = cfg.get("params", {})
    mult = p_cfg.get("growth_multiplier", 1.5)
    dso_rise_thresh = p_cfg.get("debtor_days_increase_pct", 0.30)
    exceptions = []
    
    for i in range(1, len(derived)):
        prev = derived.iloc[i-1]
        curr = derived.iloc[i]
        
        rev_prev, rev_curr = prev["revenue"], curr["revenue"]
        rec_prev, rec_curr = prev["receivables"], curr["receivables"]
        
        rev_g = (rev_curr - rev_prev) / rev_prev if rev_prev > 0 else 0.0
        rec_g = (rec_curr - rec_prev) / rec_prev if rec_prev > 0 else 0.0
        
        dso_prev = (rec_prev / rev_prev) * 365 if rev_prev > 0 else 0.0
        dso_curr = (rec_curr / rev_curr) * 365 if rev_curr > 0 else 0.0
        dso_g = (dso_curr - dso_prev) / dso_prev if dso_prev > 0 else 0.0
        
        if (rec_g > mult * rev_g and rec_g > 0.10) or (dso_g > dso_rise_thresh):
            exceptions.append({
                "rule_id": "FS-04",
                "fy": curr["fy"],
                "subject": "Trade Receivables Growth",
                "observed_value": f"Rec Growth: {rec_g*100:.1f}%, DSO: {dso_curr:.0f}d",
                "threshold_value": f"Rev Growth: {rev_g*100:.1f}%, DSO Prev: {dso_prev:.0f}d",
                "exception_value": abs(rec_curr - rec_prev),
                "detail": f"Receivables grew {rec_g*100:.1f}% (vs sales {rev_g*100:.1f}%), DSO shifted from {dso_prev:.0f}d to {dso_curr:.0f}d",
                "rec_growth": f"{rec_g*100:.1f}",
                "rev_growth": f"{rev_g*100:.1f}",
                "dso_prev": f"{dso_prev:.0f}",
                "dso_curr": f"{dso_curr:.0f}",
            })
    return exceptions

@rule("FS-05")
def fs_05(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-05: Inventory growth > 1.5 * revenue growth."""
    p_cfg = cfg.get("params", {})
    mult = p_cfg.get("growth_multiplier", 1.5)
    exceptions = []
    
    for i in range(1, len(derived)):
        prev = derived.iloc[i-1]
        curr = derived.iloc[i]
        
        rev_g = (curr["revenue"] - prev["revenue"]) / prev["revenue"] if prev["revenue"] > 0 else 0.0
        inv_g = (curr["inventory"] - prev["inventory"]) / prev["inventory"] if prev["inventory"] > 0 else 0.0
        
        if inv_g > mult * rev_g and inv_g > 0.10:
            exceptions.append({
                "rule_id": "FS-05",
                "fy": curr["fy"],
                "subject": "Inventory Accumulation",
                "observed_value": f"{inv_g*100:.1f}%",
                "threshold_value": f"{mult*rev_g*100:.1f}%",
                "exception_value": abs(curr["inventory"] - prev["inventory"]),
                "detail": f"Inventory grew {inv_g*100:.1f}% vs revenue growth {rev_g*100:.1f}%"
            })
    return exceptions

@rule("FS-06")
def fs_06(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-06: abs(gp_margin_t - gp_margin_t-1) > 0.05 (5 percentage points)."""
    p_cfg = cfg.get("params", {})
    thresh = p_cfg.get("margin_change_threshold", 0.05)
    exceptions = []
    
    for i in range(1, len(derived)):
        prev = derived.iloc[i-1]
        curr = derived.iloc[i]
        
        gm_prev = prev["gross_profit"] / prev["revenue"] if prev["revenue"] > 0 else 0.0
        gm_curr = curr["gross_profit"] / curr["revenue"] if curr["revenue"] > 0 else 0.0
        diff = abs(gm_curr - gm_prev)
        
        if diff > thresh:
            exceptions.append({
                "rule_id": "FS-06",
                "fy": curr["fy"],
                "subject": "Gross Profit Margin Shift",
                "observed_value": f"{gm_curr*100:.1f}%",
                "threshold_value": f"{gm_prev*100:.1f}%",
                "exception_value": diff * curr["revenue"],
                "detail": f"Gross margin shifted by {diff*100:.1f}pp from {gm_prev*100:.1f}% to {gm_curr*100:.1f}%"
            })
    return exceptions

@rule("FS-07")
def fs_07(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-07: abs(pat_t / pat_t-1 - 1) > 0.50."""
    p_cfg = cfg.get("params", {})
    thresh = p_cfg.get("volatility_threshold", 0.50)
    exceptions = []
    
    for i in range(1, len(derived)):
        prev = derived.iloc[i-1]
        curr = derived.iloc[i]
        
        p1, p2 = prev["pat"], curr["pat"]
        if abs(p1) > 1000.0:
            change = abs(p2 / p1 - 1.0)
            if change > thresh:
                exceptions.append({
                    "rule_id": "FS-07",
                    "fy": curr["fy"],
                    "subject": "Net Profit Volatility",
                    "observed_value": f"{change*100:.1f}%",
                    "threshold_value": f"{thresh*100:.1f}%",
                    "exception_value": abs(p2 - p1),
                    "detail": f"PAT shifted by {change*100:.1f}% from {p1:,.0f} ({prev['fy']}) to {p2:,.0f} ({curr['fy']})"
                })
    return exceptions

@rule("FS-08")
def fs_08(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-08: (cwip + intangibles) growth > 0.20 AND revenue growth < 0.05."""
    p_cfg = cfg.get("params", {})
    cwip_g_thresh = p_cfg.get("cwip_growth_threshold", 0.20)
    rev_g_thresh = p_cfg.get("rev_growth_threshold", 0.05)
    exceptions = []
    
    for i in range(1, len(derived)):
        prev = derived.iloc[i-1]
        curr = derived.iloc[i]
        
        ci_prev = prev["cwip"] + prev["intangibles"]
        ci_curr = curr["cwip"] + curr["intangibles"]
        
        ci_g = (ci_curr - ci_prev) / ci_prev if ci_prev > 1000.0 else (1.0 if ci_curr > 100000.0 else 0.0)
        rev_g = (curr["revenue"] - prev["revenue"]) / prev["revenue"] if prev["revenue"] > 0 else 0.0
        
        if ci_g > cwip_g_thresh and rev_g < rev_g_thresh:
            exceptions.append({
                "rule_id": "FS-08",
                "fy": curr["fy"],
                "subject": "CWIP & Intangibles Capitalisation",
                "observed_value": f"CWIP Growth: {ci_g*100:.1f}%",
                "threshold_value": f"Rev Growth: {rev_g*100:.1f}%",
                "exception_value": abs(ci_curr - ci_prev),
                "detail": f"CWIP/Intangibles grew {ci_g*100:.1f}% during sluggish revenue growth ({rev_g*100:.1f}%)"
            })
    return exceptions

@rule("FS-09")
def fs_09(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-09: Fixed asset additions > 0.10 * opening_gross_block AND revenue_growth < 0.02."""
    p_cfg = cfg.get("params", {})
    add_pct_thresh = p_cfg.get("addition_pct_threshold", 0.10)
    rev_g_thresh = p_cfg.get("rev_growth_threshold", 0.02)
    exceptions = []
    
    for i in range(1, len(derived)):
        prev = derived.iloc[i-1]
        curr = derived.iloc[i]
        
        op_gb = curr.get("opening_gross_block", prev["gross_block"])
        additions = curr.get("fixed_asset_additions", curr["gross_block"] - prev["gross_block"])
        rev_g = (curr["revenue"] - prev["revenue"]) / prev["revenue"] if prev["revenue"] > 0 else 0.0
        
        if op_gb > 0 and (additions / op_gb) > add_pct_thresh and rev_g < rev_g_thresh:
            exceptions.append({
                "rule_id": "FS-09",
                "fy": curr["fy"],
                "subject": "Fixed Asset Additions vs Revenue",
                "observed_value": f"Capex Additions: {additions:,.0f} ({(additions/op_gb)*100:.1f}%)",
                "threshold_value": f"Rev Growth: {rev_g*100:.1f}%",
                "exception_value": additions,
                "detail": f"Fixed asset capex of {additions:,.0f} ({(additions/op_gb)*100:.1f}% of gross block) yielded only {rev_g*100:.1f}% revenue growth"
            })
    return exceptions

@rule("FS-10")
def fs_10(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-10: Δgross_block > (additions - disposals) + 1 -> unexplained uplift."""
    p_cfg = cfg.get("params", {})
    tol = p_cfg.get("tolerance", 1.0)
    exceptions = []
    
    for i in range(1, len(derived)):
        prev = derived.iloc[i-1]
        curr = derived.iloc[i]
        
        delta_gb = curr["gross_block"] - prev["gross_block"]
        additions = curr.get("fixed_asset_additions", delta_gb)
        disposals = curr.get("fixed_asset_disposals", 0.0)
        
        unexplained = delta_gb - (additions - disposals)
        if unexplained > tol:
            exceptions.append({
                "rule_id": "FS-10",
                "fy": curr["fy"],
                "subject": "Gross Block Revaluation Uplift",
                "observed_value": round(unexplained, 2),
                "threshold_value": tol,
                "exception_value": unexplained,
                "detail": f"Gross block increased by {delta_gb:,.0f}, exceeding net additions by {unexplained:,.0f}"
            })
    return exceptions

@rule("FS-11")
def fs_11(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-11: Related party balance / revenue > 0.10 OR its growth exceeds revenue growth."""
    p_cfg = cfg.get("params", {})
    thresh = p_cfg.get("revenue_pct_threshold", 0.10)
    exceptions = []
    
    for i in range(len(derived)):
        curr = derived.iloc[i]
        rev = curr["revenue"]
        rp_bal = curr["related_party_balance"]
        
        if rev > 0 and (rp_bal / rev) > thresh:
            exceptions.append({
                "rule_id": "FS-11",
                "fy": curr["fy"],
                "subject": "Related Party Revenue Exposure",
                "observed_value": f"{(rp_bal/rev)*100:.1f}%",
                "threshold_value": f"{thresh*100:.1f}%",
                "exception_value": rp_bal,
                "detail": f"Related party balance of {rp_bal:,.2f} represents {(rp_bal/rev)*100:.1f}% of revenue"
            })
    return exceptions

@rule("FS-12")
def fs_12(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-12: Working capital borrowings / revenue rises by > 0.05 (5pp) across period."""
    p_cfg = cfg.get("params", {})
    thresh = p_cfg.get("increase_pp_threshold", 0.05)
    fys = sorted(derived["fy"].unique())
    if len(fys) < 2:
        return []
        
    first = derived.iloc[0]
    last = derived.iloc[-1]
    
    r1 = first["wc_borrowings"] / first["revenue"] if first["revenue"] > 0 else 0.0
    r3 = last["wc_borrowings"] / last["revenue"] if last["revenue"] > 0 else 0.0
    diff = r3 - r1
    
    if diff > thresh:
        return [{
            "rule_id": "FS-12",
            "fy": last["fy"],
            "subject": "Working Capital Debt Intensity",
            "observed_value": f"{diff*100:.1f}pp",
            "threshold_value": f"{thresh*100:.1f}pp",
            "exception_value": abs(last["wc_borrowings"] - first["wc_borrowings"]),
            "detail": f"WC Borrowings/Revenue ratio expanded by {diff*100:.1f}pp (from {r1*100:.1f}% to {r3*100:.1f}%)"
        }]
    return []

@rule("FS-13")
def fs_13(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-13: Unbilled revenue growth > 0.25 YoY."""
    p_cfg = cfg.get("params", {})
    thresh = p_cfg.get("growth_threshold", 0.25)
    exceptions = []
    
    for i in range(1, len(derived)):
        prev = derived.iloc[i-1]
        curr = derived.iloc[i]
        
        u1, u2 = prev["unbilled_revenue"], curr["unbilled_revenue"]
        if u1 > 1000.0:
            g = (u2 - u1) / u1
            if g > thresh:
                exceptions.append({
                    "rule_id": "FS-13",
                    "fy": curr["fy"],
                    "subject": "Unbilled Revenue Accruals",
                    "observed_value": f"{g*100:.1f}%",
                    "threshold_value": f"{thresh*100:.1f}%",
                    "exception_value": abs(u2 - u1),
                    "detail": f"Unbilled revenue grew by {g*100:.1f}% YoY (from {u1:,.0f} to {u2:,.0f})"
                })
    return exceptions

@rule("FS-14")
def fs_14(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-14: Financial year length != 12m OR core ratio deviates > 3σ from 3-year baseline."""
    p_cfg = cfg.get("params", {})
    sigma_thresh = p_cfg.get("sigma_threshold", 3.0)
    exceptions = []
    
    if len(derived) >= 3:
        gp_margins = [row["gross_profit"] / max(1.0, row["revenue"]) for _, row in derived.iterrows()]
        mean_gp, std_gp = float(np.mean(gp_margins)), float(np.std(gp_margins))
        if std_gp > 0.001:
            for idx, row in derived.iterrows():
                val = row["gross_profit"] / max(1.0, row["revenue"])
                z = abs(val - mean_gp) / std_gp
                if z > sigma_thresh:
                    exceptions.append({
                        "rule_id": "FS-14",
                        "fy": row["fy"],
                        "subject": "Internal Ratio Deviation",
                        "observed_value": round(z, 2),
                        "threshold_value": sigma_thresh,
                        "exception_value": None,
                        "detail": f"Gross margin in {row['fy']} deviates by {z:.2f}σ from 3-year baseline"
                    })
    return exceptions

@rule("FS-15")
def fs_15(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-15: Same normalised prior-period adjustment description in >= 2 consecutive years."""
    adjustments = params.get("prior_adjustments", [])
    if not adjustments:
        return []
    descriptions_by_fy: Dict[str, List[str]] = {}
    for adj in adjustments:
        fy = adj.get("fy")
        desc = adj.get("description", "").strip().lower()
        if fy and desc:
            descriptions_by_fy.setdefault(fy, []).append(desc)
            
    fys = sorted(descriptions_by_fy.keys())
    exceptions = []
    for i in range(len(fys) - 1):
        y1, y2 = fys[i], fys[i+1]
        common = set(descriptions_by_fy[y1]).intersection(set(descriptions_by_fy[y2]))
        for c in common:
            exceptions.append({
                "rule_id": "FS-15",
                "fy": f"{y1}-{y2}",
                "subject": f"Prior Period Adjustment: {c}",
                "observed_value": "Repeated correction",
                "threshold_value": "1 year",
                "exception_value": None,
                "detail": f"Recurring prior-period adjustment description '{c}' across consecutive years ({y1} and {y2})"
            })
    return exceptions

@rule("FS-16")
def fs_16(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """FS-16: Cookie-jar provisioning (provisions increased in peak profit year and decreased in lowest profit year)."""
    if len(derived) < 3:
        return []
    pat_series = derived.set_index("fy")["pat"]
    prov_series = derived.set_index("fy")["provisions"]
    
    peak_fy = pat_series.idxmax()
    trough_fy = pat_series.idxmin()
    
    # Check provision movement
    fys = sorted(derived["fy"].unique())
    prov_diffs = {fys[i]: prov_series[fys[i]] - (prov_series[fys[i-1]] if i > 0 else prov_series[fys[i]]) for i in range(len(fys))}
    
    if prov_diffs.get(peak_fy, 0.0) > 0 and prov_diffs.get(trough_fy, 0.0) < 0:
        return [{
            "rule_id": "FS-16",
            "fy": f"{peak_fy}/{trough_fy}",
            "subject": "Cookie-Jar Provisioning",
            "observed_value": f"+{prov_diffs[peak_fy]:,.0f} / {prov_diffs[trough_fy]:,.0f}",
            "threshold_value": "Symmetric Movement",
            "exception_value": abs(prov_diffs[peak_fy]),
            "detail": f"Provisions boosted in peak profit year ({peak_fy}) and drawn down in trough profit year ({trough_fy})"
        }]
    return []

# =====================================================================
# MODULE MS: FORENSIC MODELS (4 MODELS)
# =====================================================================

@rule("MS-01")
def ms_01(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """MS-01: Beneish M-Score Earnings Manipulation Index (flag when M > -1.78)."""
    exceptions = []
    for i in range(1, len(derived)):
        prev = derived.iloc[i-1]
        curr = derived.iloc[i]
        res = compute_beneish_m_score(prev, curr)
        if res["is_flagged"]:
            comp_str = ", ".join([f"{k}={v}" for k, v in res["components"].items()])
            exceptions.append({
                "rule_id": "MS-01",
                "fy": curr["fy"],
                "subject": "Beneish M-Score",
                "observed_value": res["m_score"],
                "threshold_value": -1.78,
                "exception_value": None,
                "confidence": res["confidence"],
                "detail": f"M-Score of {res['m_score']:.4f} > -1.78 threshold (Indices: {comp_str})"
            })
    return exceptions

@rule("MS-02")
def ms_02(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """MS-02: Altman Z"-Score Financial Distress Indicator (flag in distress zone < 1.10)."""
    exceptions = []
    for idx, row in derived.iterrows():
        res = compute_altman_z_score(row)
        if res["is_distress"]:
            exceptions.append({
                "rule_id": "MS-02",
                "fy": row["fy"],
                "subject": "Altman Z\"-Score",
                "observed_value": res["z_score"],
                "threshold_value": 1.10,
                "exception_value": None,
                "detail": f"Z\"-Score of {res['z_score']:.4f} indicates financial distress (pressure leg of fraud triangle)"
            })
    return exceptions

@rule("MS-03")
def ms_03(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """MS-03: Sloan Accrual Anomaly Ratio (flag > 0.10)."""
    exceptions = []
    for i in range(len(derived)):
        prev = derived.iloc[i-1] if i > 0 else None
        curr = derived.iloc[i]
        res = compute_sloan_accrual(prev, curr)
        if res.get("can_run", True) and res.get("is_flagged", False):
            exceptions.append({
                "rule_id": "MS-03",
                "fy": curr["fy"],
                "subject": "Sloan Accrual Ratio",
                "observed_value": res["accrual_ratio"],
                "threshold_value": 0.10,
                "exception_value": abs(curr["pat"] - curr["cfo_indirect"]),
                "detail": f"Sloan accrual ratio of {res['accrual_ratio']:.4f} exceeds 0.10 (PAT: {res['pat']:,.0f}, CFO: {res['cfo_indirect']:,.0f})"
            })
    return exceptions

@rule("MS-04")
def ms_04(ledgers: pd.DataFrame, derived: pd.DataFrame, params: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """MS-04: Piotroski F-Score Divergence (F <= 3 AND revenue_growth > 0.15)."""
    exceptions = []
    for i in range(1, len(derived)):
        prev = derived.iloc[i-1]
        curr = derived.iloc[i]
        res = compute_piotroski_f_score(prev, curr)
        if res["is_flagged"]:
            exceptions.append({
                "rule_id": "MS-04",
                "fy": curr["fy"],
                "subject": "Piotroski F-Score",
                "observed_value": f"{res['f_score']}/9",
                "threshold_value": "F <= 3 & Rev Growth > 15%",
                "exception_value": None,
                "detail": f"Weak fundamental health score ({res['f_score']}/9) alongside strong revenue growth ({res['revenue_growth']*100:.1f}%)"
            })
    return exceptions

# =====================================================================
# ENGINE ORCHESTRATOR
# =====================================================================

def execute_all_rules(
    ledgers: pd.DataFrame,
    derived: pd.DataFrame,
    params: Optional[Dict[str, Any]] = None,
    rules_dir: str = "rules"
) -> Tuple[pd.DataFrame, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Execute all 44 rules against the normalised trial balance and derived statements.
    Returns:
    - exceptions_df (DataFrame of all fired flags)
    - executed_rules (List of executed rule metadata)
    - skipped_rules (List of skipped rules with stated reasons)
    """
    params = params or {}
    all_rule_defs = load_rules_from_yaml(rules_dir)
    all_fys = sorted(ledgers["fy"].unique())
    num_years = len(all_fys)
    has_opening = derived["cfo_indirect"].notna().any()

    # Analysis-year names, referenced by many hypothesis templates as {fy1}..{fy3}
    fy_context = {f"fy{i + 1}": fy for i, fy in enumerate(all_fys)}
    if all_fys:
        fy_context["fy_first"] = all_fys[0]
        fy_context["fy_last"] = all_fys[-1]
    
    all_exceptions = []
    executed_rules = []
    skipped_rules = []
    
    for r_def in all_rule_defs:
        r_id = r_def["id"]
        r_name = r_def["name"]
        min_y = r_def.get("min_years", 1)
        reqs = r_def.get("requires", ["trial_balance"])
        
        # Check constraints
        skip_reason = None
        if num_years < min_y:
            skip_reason = f"Requires {min_y} financial year(s), found {num_years}"
        elif "peer_ratios" in reqs and not params.get("peer_ratios"):
            skip_reason = "Missing required parameter: peer_ratios"
        elif "related_parties" in reqs and not params.get("related_parties"):
            skip_reason = "Missing required parameter: related_parties"
        elif "prior_adjustments" in reqs and not params.get("prior_adjustments"):
            skip_reason = "Missing required parameter: prior_adjustments"
        elif r_id in ["FS-01", "MS-03"] and not has_opening:
            skip_reason = "missing opening balances"
            
        if skip_reason:
            skipped_rules.append({
                "rule_id": r_id,
                "name": r_name,
                "reason": skip_reason
            })
            continue
            
        fn = _RULE_REGISTRY.get(r_id)
        if fn is None:
            skipped_rules.append({
                "rule_id": r_id,
                "name": r_name,
                "reason": "Function not registered in rule engine"
            })
            continue
            
        try:
            ex_list = fn(ledgers, derived, params, r_def)
            executed_rules.append({
                "rule_id": r_id,
                "name": r_name,
                "module": r_def.get("module"),
                "flag": r_def.get("flag", "red"),
                "weight": r_def.get("weight", 3),
                "confidence": r_def.get("confidence", 1.0),
                "branch": r_def.get("branch"),
                "scheme": r_def.get("scheme"),
                "source": r_def.get("source"),
                "hypothesis": r_def.get("hypothesis"),
                "procedure": r_def.get("procedure", [])
            })
            
            for ex in ex_list:
                # Merge rule metadata into exception row
                merged_ex = {
                    "rule_id": r_id,
                    "rule_name": r_name,
                    "module": r_def.get("module"),
                    "flag": r_def.get("flag", "red"),
                    "weight": r_def.get("weight", 3),
                    "confidence": ex.get("confidence", r_def.get("confidence", 1.0)),
                    "branch": r_def.get("branch"),
                    "scheme": r_def.get("scheme"),
                    "source": r_def.get("source"),
                    "hypothesis": r_def.get("hypothesis"),
                    "procedure": r_def.get("procedure", []),
                    "fy": ex.get("fy"),
                    "subject": ex.get("subject"),
                    "observed_value": ex.get("observed_value"),
                    "threshold_value": ex.get("threshold_value"),
                    "exception_value": ex.get("exception_value"),
                    "detail": ex.get("detail", ""),
                    # Any additional keys the rule computed are carried through so
                    # hypothesis templates can reference them by name. The analysis
                    # years are added for every rule since many templates cite them.
                    "context": {
                        **fy_context,
                        **{k: v for k, v in ex.items()
                           if k not in {"rule_id", "fy", "subject", "observed_value",
                                        "threshold_value", "exception_value", "detail",
                                        "confidence"}},
                    },
                }
                all_exceptions.append(merged_ex)
        except Exception as e:
            skipped_rules.append({
                "rule_id": r_id,
                "name": r_name,
                "reason": f"Execution error: {str(e)}"
            })
            
    exceptions_df = pd.DataFrame(all_exceptions)
    return exceptions_df, executed_rules, skipped_rules
