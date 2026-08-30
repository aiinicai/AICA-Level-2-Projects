"""
Forensic models implementation for Red Flag Engine.
MS-01: Beneish M-Score (1999)
MS-02: Altman Z"-Score (private/non-manufacturing)
MS-03: Sloan Accrual Ratio (1996)
MS-04: Piotroski F-Score (2000)

Note: All 4 models are external additions and not from the ICAI material.
"""
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

def compute_beneish_m_score(derived_prev: pd.Series, derived_curr: pd.Series) -> Dict[str, Any]:
    """
    Compute 8-variable Beneish M-Score comparing period t-1 and period t.
    M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI
    Flag threshold: M > -1.78
    """
    sales_t = max(1.0, float(derived_curr["revenue"]))
    sales_t_1 = max(1.0, float(derived_prev["revenue"]))
    
    rec_t = float(derived_curr["receivables"])
    rec_t_1 = float(derived_prev["receivables"])
    
    ta_t = max(1.0, float(derived_curr["total_assets"]))
    ta_t_1 = max(1.0, float(derived_prev["total_assets"]))
    
    cogs_t = float(derived_curr["cogs"])
    cogs_t_1 = float(derived_prev["cogs"])
    
    # 1. DSRI = (Receivables_t / Sales_t) / (Receivables_t-1 / Sales_t-1)
    dsr_t = rec_t / sales_t
    dsr_t_1 = rec_t_1 / sales_t_1 if rec_t_1 > 0 else dsr_t
    dsri = dsr_t / dsr_t_1 if dsr_t_1 > 0 else 1.0
    
    # 2. GMI = GM_t-1 / GM_t where GM = (Sales - COGS) / Sales
    gm_t = (sales_t - cogs_t) / sales_t
    gm_t_1 = (sales_t_1 - cogs_t_1) / sales_t_1
    gmi = gm_t_1 / gm_t if gm_t > 0.001 else 1.0
    
    # 3. AQI = (1 - (CA + NetBlock + Investments)/TA)_t / (1 - (CA + NetBlock + Investments)/TA)_t-1
    nca_t = float(derived_curr["current_assets"] + derived_curr["net_block"] + derived_curr["investments"])
    nca_t_1 = float(derived_prev["current_assets"] + derived_prev["net_block"] + derived_prev["investments"])
    aq_t = 1.0 - (nca_t / ta_t)
    aq_t_1 = 1.0 - (nca_t_1 / ta_t_1)
    aqi = (aq_t / aq_t_1) if abs(aq_t_1) > 0.001 else 1.0
    
    # 4. SGI = Sales_t / Sales_t-1
    sgi = sales_t / sales_t_1
    
    # 5. DEPI = DepRate_t-1 / DepRate_t where DepRate = Dep / (Dep + NetBlock)
    dep_t = float(derived_curr["depreciation"])
    dep_t_1 = float(derived_prev["depreciation"])
    nb_t = float(derived_curr["net_block"])
    nb_t_1 = float(derived_prev["net_block"])
    
    dep_rate_t = dep_t / (dep_t + nb_t) if (dep_t + nb_t) > 0 else 0.1
    dep_rate_t_1 = dep_t_1 / (dep_t_1 + nb_t_1) if (dep_t_1 + nb_t_1) > 0 else 0.1
    depi = dep_rate_t_1 / dep_rate_t if dep_rate_t > 0.001 else 1.0
    
    # 6. SGAI = (SGA_t / Sales_t) / (SGA_t-1 / Sales_t-1)
    sga_t = float(derived_curr["sga"])
    sga_t_1 = float(derived_prev["sga"])
    sga_note = None
    if sga_t == 0 and sga_t_1 == 0:
        sgai = 1.0
        sga_note = "SGAI unavailable — SG&A not separable"
    else:
        sga_rate_t = sga_t / sales_t
        sga_rate_t_1 = sga_t_1 / sales_t_1 if sga_t_1 > 0 else sga_rate_t
        sgai = sga_rate_t / sga_rate_t_1 if sga_rate_t_1 > 0 else 1.0
        
    # 7. LVGI = Lev_t / Lev_t-1 where Lev = (CL + LTBorrowings)/TA
    lev_t = (float(derived_curr["current_liabilities"]) + float(derived_curr["lt_borrowings"])) / ta_t
    lev_t_1 = (float(derived_prev["current_liabilities"]) + float(derived_prev["lt_borrowings"])) / ta_t_1
    lvgi = lev_t / lev_t_1 if lev_t_1 > 0.001 else 1.0
    
    # 8. TATA = (PBT - CFO) / TA
    cfo_t = derived_curr["cfo_indirect"]
    if cfo_t is None or pd.isna(cfo_t):
        cfo_t = float(derived_curr["pat"]) # fallback
    else:
        cfo_t = float(cfo_t)
    tata = (float(derived_curr["pbt"]) - cfo_t) / ta_t
    
    # Beneish M-Score Formula
    m_score = (
        -4.84
        + 0.920 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )
    
    confidence = min(1.0, max(0.0, (m_score + 1.78) / 2.0))
    is_flagged = m_score > -1.78
    
    components = {
        "DSRI": round(dsri, 4),
        "GMI": round(gmi, 4),
        "AQI": round(aqi, 4),
        "SGI": round(sgi, 4),
        "DEPI": round(depi, 4),
        "SGAI": round(sgai, 4),
        "LVGI": round(lvgi, 4),
        "TATA": round(tata, 4),
    }
    
    return {
        "fy": derived_curr["fy"],
        "m_score": round(m_score, 4),
        "is_flagged": is_flagged,
        "confidence": round(confidence, 4),
        "components": components,
        "sga_note": sga_note
    }

def compute_altman_z_score(row: pd.Series) -> Dict[str, Any]:
    """
    Compute Altman Z"-Score (private / non-manufacturing variant).
    X1 = working_capital / total_assets
    X2 = retained_earnings / total_assets
    X3 = ebit / total_assets
    X4 = net_worth / total_liabilities
    Z" = 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4
    """
    ta = max(1.0, float(row["total_assets"]))
    tl = max(1.0, float(row["total_liabilities"]))
    
    x1 = float(row["working_capital"]) / ta
    x2 = float(row["retained_earnings"]) / ta
    x3 = float(row["ebit"]) / ta
    x4 = float(row["net_worth"]) / tl
    
    z_score = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4
    
    if z_score > 2.60:
        zone = "Safe"
        is_distress = False
    elif z_score >= 1.10:
        zone = "Grey"
        is_distress = False
    else:
        zone = "Distress"
        is_distress = True
        
    return {
        "fy": row["fy"],
        "z_score": round(z_score, 4),
        "zone": zone,
        "is_distress": is_distress,
        "components": {
            "X1 (WC/TA)": round(x1, 4),
            "X2 (RE/TA)": round(x2, 4),
            "X3 (EBIT/TA)": round(x3, 4),
            "X4 (NW/TL)": round(x4, 4),
        }
    }

def compute_sloan_accrual(derived_prev: Optional[pd.Series], derived_curr: pd.Series) -> Dict[str, Any]:
    """
    Compute Sloan Accrual Ratio.
    accrual_ratio = (pat - cfo_indirect) / avg_total_assets
    Flag threshold: > 0.10
    """
    ta_curr = float(derived_curr["total_assets"])
    if derived_prev is not None:
        ta_prev = float(derived_prev["total_assets"])
        avg_ta = (ta_curr + ta_prev) / 2.0
    else:
        avg_ta = ta_curr
        
    avg_ta = max(1.0, avg_ta)
    
    pat = float(derived_curr["pat"])
    cfo = derived_curr["cfo_indirect"]
    
    if cfo is None or pd.isna(cfo):
        return {
            "fy": derived_curr["fy"],
            "can_run": False,
            "reason": "missing opening balances for cash flow",
            "accrual_ratio": None,
            "is_flagged": False
        }
        
    cfo = float(cfo)
    accrual_ratio = (pat - cfo) / avg_ta
    is_flagged = accrual_ratio > 0.10
    
    return {
        "fy": derived_curr["fy"],
        "can_run": True,
        "accrual_ratio": round(accrual_ratio, 4),
        "pat": pat,
        "cfo_indirect": cfo,
        "avg_total_assets": round(avg_ta, 2),
        "is_flagged": is_flagged
    }

def compute_piotroski_f_score(derived_prev: pd.Series, derived_curr: pd.Series) -> Dict[str, Any]:
    """
    Compute Piotroski F-Score (9 binary signals across Profitability, Leverage/Liquidity, Operating Efficiency).
    Flag when F <= 3 AND revenue growth > 0.15.
    """
    ta_t = max(1.0, float(derived_curr["total_assets"]))
    ta_t_1 = max(1.0, float(derived_prev["total_assets"]))
    
    pat_t = float(derived_curr["pat"])
    pat_t_1 = float(derived_prev["pat"])
    
    cfo_t = derived_curr["cfo_indirect"]
    cfo_val = float(cfo_t) if cfo_t is not None and not pd.isna(cfo_t) else 0.0
    
    roa_t = pat_t / ta_t
    roa_t_1 = pat_t_1 / ta_t_1
    
    # 1. Profitability Signals
    p1 = 1 if roa_t > 0 else 0
    p2 = 1 if cfo_val > 0 else 0
    p3 = 1 if roa_t > roa_t_1 else 0
    p4 = 1 if cfo_val > pat_t else 0
    
    # 2. Leverage & Liquidity
    lt_debt_t = float(derived_curr["lt_borrowings"]) / ta_t
    lt_debt_t_1 = float(derived_prev["lt_borrowings"]) / ta_t_1
    p5 = 1 if lt_debt_t < lt_debt_t_1 else 0
    
    cr_t = float(derived_curr["current_assets"]) / max(1.0, float(derived_curr["current_liabilities"]))
    cr_t_1 = float(derived_prev["current_assets"]) / max(1.0, float(derived_prev["current_liabilities"]))
    p6 = 1 if cr_t > cr_t_1 else 0
    
    sc_t = float(derived_curr["share_capital"])
    sc_t_1 = float(derived_prev["share_capital"])
    p7 = 1 if sc_t <= sc_t_1 else 0
    
    # 3. Operating Efficiency
    rev_t = max(1.0, float(derived_curr["revenue"]))
    rev_t_1 = max(1.0, float(derived_prev["revenue"]))
    
    gm_t = (rev_t - float(derived_curr["cogs"])) / rev_t
    gm_t_1 = (rev_t_1 - float(derived_prev["cogs"])) / rev_t_1
    p8 = 1 if gm_t > gm_t_1 else 0
    
    at_t = rev_t / ta_t
    at_t_1 = rev_t_1 / ta_t_1
    p9 = 1 if at_t > at_t_1 else 0
    
    f_score = p1 + p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
    rev_growth = (rev_t - rev_t_1) / rev_t_1
    
    is_flagged = (f_score <= 3) and (rev_growth > 0.15)
    
    signals = {
        "ROA > 0": p1,
        "CFO > 0": p2,
        "ΔROA > 0": p3,
        "CFO > PAT (Accrual Quality)": p4,
        "Δ(LT Debt / TA) < 0": p5,
        "ΔCurrent Ratio > 0": p6,
        "No Share Dilution": p7,
        "ΔGross Margin > 0": p8,
        "ΔAsset Turnover > 0": p9,
    }
    
    return {
        "fy": derived_curr["fy"],
        "f_score": f_score,
        "revenue_growth": round(rev_growth, 4),
        "is_flagged": is_flagged,
        "signals": signals
    }
