"""
Statistical analysis tools for Red Flag Engine.
Includes Benford's Law, Relative Size Factor (RSF), Z-Score, IQR, Fuzzy Name Matching,
and Unsupervised IsolationForest / LOF outlier scoring.
"""
import re
import math
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
import rapidfuzz
import jellyfish
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

# Benford's Law Expected First-Digit Probabilities (d = 1..9)
BENFORD_P = {d: math.log10(1.0 + 1.0 / d) for d in range(1, 10)}

def compute_benford_first_digit(values: List[float], min_records: int = 300) -> Dict[str, Any]:
    """
    Perform Benford's Law first-digit digital analysis.
    Requires at least `min_records` positive values.
    Returns MAD and Nigrini conformity classification.
    """
    # Filter positive non-zero amounts
    clean_vals = [abs(v) for v in values if abs(v) > 0.01]
    n = len(clean_vals)
    if n < min_records:
        return {
            "can_run": False,
            "reason": f"Insufficient records for Benford analysis (found {n}, minimum {min_records})",
            "n": n
        }
        
    first_digits = []
    for v in clean_vals:
        s = f"{v:.6f}".replace(".", "").lstrip("0")
        if s:
            d = int(s[0])
            if 1 <= d <= 9:
                first_digits.append(d)
                
    counts = {d: first_digits.count(d) for d in range(1, 10)}
    observed_p = {d: counts[d] / len(first_digits) for d in range(1, 10)}
    
    # Compute MAD = (1/9) * sum(|Observed - Expected|)
    mad = sum(abs(observed_p[d] - BENFORD_P[d]) for d in range(1, 10)) / 9.0
    
    # Nigrini MAD conformity thresholds
    # < 0.006: Close conformity
    # 0.006 - 0.012: Acceptable conformity
    # 0.012 - 0.015: Marginal conformity
    # > 0.015: Non-conformity
    if mad < 0.006:
        conformity = "Close conformity"
    elif mad <= 0.012:
        conformity = "Acceptable conformity"
    elif mad <= 0.015:
        conformity = "Marginal conformity"
    else:
        conformity = "Non-conformity"
        
    return {
        "can_run": True,
        "n": len(first_digits),
        "mad": mad,
        "conformity": conformity,
        "counts": counts,
        "observed_proportions": observed_p,
        "expected_proportions": BENFORD_P,
        "is_flagged": mad > 0.015
    }

def compute_rsf(values: List[float]) -> Tuple[float, float, float]:
    """
    Compute Relative Size Factor = Largest / Second Largest.
    Returns (RSF, largest, second_largest).
    """
    clean = sorted([abs(v) for v in values if abs(v) > 0.01], reverse=True)
    if len(clean) < 2 or clean[1] == 0:
        return 1.0, clean[0] if clean else 0.0, 0.0
    return clean[0] / clean[1], clean[0], clean[1]

def fuzzy_find_duplicates(names: List[str], threshold: float = 88.0) -> List[Tuple[str, str, float, str]]:
    """
    Find near-duplicate names using RapidFuzz token_set_ratio and Jellyfish metaphone.
    Excludes pairs differing only by trailing numeric suffixes ('-1', 'II', '2', etc.).
    Returns list of (name1, name2, score, match_type).
    """
    results = []
    n = len(names)
    
    def strip_num_suffix(s: str) -> str:
        return re.sub(r'[\s\-_]+(ii|iii|iv|v|\d+)$', '', s.strip(), flags=re.IGNORECASE)

    for i in range(n):
        name1 = names[i]
        stem1 = strip_num_suffix(name1)
        meta1 = jellyfish.metaphone(name1)
        
        for j in range(i + 1, n):
            name2 = names[j]
            stem2 = strip_num_suffix(name2)
            
            # Exclude pairs that only differ by numerical suffix
            if stem1.lower() == stem2.lower() and name1.lower() != name2.lower():
                continue
                
            ratio = rapidfuzz.fuzz.token_set_ratio(name1, name2)
            meta2 = jellyfish.metaphone(name2)
            
            if ratio >= threshold:
                results.append((name1, name2, float(ratio), "token_set_ratio"))
            elif meta1 and meta2 and meta1 == meta2 and len(meta1) >= 4:
                results.append((name1, name2, 90.0, "metaphone"))
                
    return results

def compute_unsupervised_outliers(ledgers: pd.DataFrame, contamination: float = 0.02, random_state: int = 42) -> pd.DataFrame:
    """
    Compute unsupervised outlier score [0, 1] per unique ledger.
    Requires at least 100 distinct ledgers across 3 financial years.
    Used as tie-breaker ranking only (never creates flags on its own).
    """
    fys = sorted(ledgers["fy"].unique())
    unique_ledgers = ledgers["ledger_name"].unique()
    
    if len(unique_ledgers) < 100 or len(fys) < 3:
        return pd.DataFrame({"ledger_name": unique_ledgers, "ml_outlier_score": 0.0})
        
    fy1, fy2, fy3 = fys[0], fys[1], fys[2]
    
    # Pivot features across years
    piv_cl = ledgers.pivot(index="ledger_name", columns="fy", values="closing_net").fillna(0.0)
    piv_tot = ledgers.pivot(index="ledger_name", columns="fy", values="turnover_total").fillna(0.0)
    grp_map = ledgers.drop_duplicates("ledger_name").set_index("ledger_name")["group"]
    
    features = []
    for lname in unique_ledgers:
        c1 = piv_cl.loc[lname, fy1] if fy1 in piv_cl.columns else 0.0
        c2 = piv_cl.loc[lname, fy2] if fy2 in piv_cl.columns else 0.0
        c3 = piv_cl.loc[lname, fy3] if fy3 in piv_cl.columns else 0.0
        
        t3 = piv_tot.loc[lname, fy3] if fy3 in piv_tot.columns else 0.0
        
        # Feature 1: log1p(abs(closing_net_fy3))
        f_log_cl = math.log1p(abs(c3))
        
        # Feature 2: growth fy1->fy3
        f_growth = (c3 - c1) / (abs(c1) + 1.0)
        
        # Feature 3: group relative size
        grp = grp_map.get(lname, "Unclassified")
        grp_tot = piv_cl.loc[grp_map[grp_map == grp].index, fy3].abs().sum() if fy3 in piv_cl.columns else 1.0
        f_grp_rel = abs(c3) / (grp_tot + 1.0)
        
        # Feature 4: turnover to balance ratio
        f_turn_ratio = t3 / (abs(c3) + 1.0)
        
        # Feature 5: volatility across 3 years
        vals = [c1, c2, c3]
        f_vol = float(np.std(vals) / (np.mean(np.abs(vals)) + 1.0))
        
        # Feature 6: years present
        f_present = sum(1 for v in vals if abs(v) > 0.01)
        
        features.append([f_log_cl, f_growth, f_grp_rel, f_turn_ratio, f_vol, f_present])
        
    X = np.nan_to_num(np.array(features), nan=0.0, posinf=10.0, neginf=-10.0)
    
    # IsolationForest
    iso = IsolationForest(contamination=contamination, random_state=random_state)
    iso.fit(X)
    iso_scores = -iso.score_samples(X)  # higher = more anomalous
    
    # Min-max scale to [0, 1]
    min_s, max_s = iso_scores.min(), iso_scores.max()
    if max_s > min_s:
        norm_scores = (iso_scores - min_s) / (max_s - min_s)
    else:
        norm_scores = np.zeros(len(unique_ledgers))
        
    return pd.DataFrame({
        "ledger_name": unique_ledgers,
        "ml_outlier_score": norm_scores
    })
