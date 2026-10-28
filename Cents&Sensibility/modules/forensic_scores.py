"""
Cents & Sensibility — Forensic Scoring Engine
Altman Z'-Score (private firm variant), Beneish M-Score (8-variable),
liquidity stress indicators, and the composite Financial Health Score.

Academic references (cite these in your capstone report):
- Altman, E. (1968, revised 1983 Z' for private firms)
- Beneish, M.D. (1999), "The Detection of Earnings Manipulation"
"""

from .data_ingestion import derive
from .ratio_engine import compute_ratios


# ---------------------------------------------------------------------------
# Altman Z'-Score — private company variant
# Z' = 0.717 X1 + 0.847 X2 + 3.107 X3 + 0.420 X4 + 0.998 X5
# ---------------------------------------------------------------------------
def altman_z(period: dict) -> dict:
    d = derive(period)
    ta = d["total_assets"]
    tl = d["total_liabilities"]
    if ta <= 0:
        return {"score": None, "zone": "N/A", "components": {}}

    x1 = d["working_capital"] / ta
    x2 = d["reserves"] / ta                       # retained earnings proxy
    x3 = d["ebit"] / ta
    x4 = d["total_equity"] / tl if tl > 0 else 4.0   # cap benefit when debt-free
    x5 = d["revenue"] / ta

    z = 0.717 * x1 + 0.847 * x2 + 3.107 * x3 + 0.420 * x4 + 0.998 * x5
    if z > 2.90:
        zone = "Safe Zone"
    elif z >= 1.23:
        zone = "Grey Zone"
    else:
        zone = "Distress Zone"

    return {
        "score": round(z, 2), "zone": zone,
        "components": {
            "X1 Working Capital / Total Assets": round(x1, 3),
            "X2 Retained Earnings / Total Assets": round(x2, 3),
            "X3 EBIT / Total Assets": round(x3, 3),
            "X4 Book Equity / Total Liabilities": round(x4, 3),
            "X5 Sales / Total Assets": round(x5, 3),
        },
    }


# ---------------------------------------------------------------------------
# Beneish M-Score (8-variable model)
# M = -4.84 + 0.92 DSRI + 0.528 GMI + 0.404 AQI + 0.892 SGI
#     + 0.115 DEPI - 0.172 SGAI + 4.679 TATA - 0.327 LVGI
# M > -2.22 → possible earnings manipulation
# ---------------------------------------------------------------------------
def beneish_m(data: dict) -> dict:
    cy, py = derive(data["CY"]), derive(data["PY"])
    notes = []

    def ratio(a, b, name, default=1.0):
        if b in (0, 0.0):
            notes.append(f"{name}: denominator zero — index defaulted to {default}")
            return default
        return a / b

    if cy["revenue"] <= 0 or py["revenue"] <= 0:
        return {"score": None, "verdict": "N/A",
                "components": {}, "notes": ["Revenue missing — M-Score not computable"]}

    dsri = ratio(ratio(cy["receivables"], cy["revenue"], "DSRI-CY"),
                 ratio(py["receivables"], py["revenue"], "DSRI-PY"), "DSRI")
    gm_cy = (cy["revenue"] - cy["material_cost"]) / cy["revenue"]
    gm_py = (py["revenue"] - py["material_cost"]) / py["revenue"]
    gmi = ratio(gm_py, gm_cy, "GMI")             # PY margin / CY margin
    aq = lambda p: 1 - (p["current_assets"] + p["net_ppe"]) / p["total_assets"] \
        if p["total_assets"] else 0
    aqi = ratio(aq(cy), aq(py), "AQI") if aq(py) else 1.0
    sgi = ratio(cy["revenue"], py["revenue"], "SGI")
    dep_rate = lambda p: p["depreciation"] / (p["depreciation"] + p["net_ppe"]) \
        if (p["depreciation"] + p["net_ppe"]) else 0
    depi = ratio(dep_rate(py), dep_rate(cy), "DEPI") if dep_rate(cy) else 1.0
    sgai = ratio(ratio(cy["other_expenses"], cy["revenue"], "SGAI-CY"),
                 ratio(py["other_expenses"], py["revenue"], "SGAI-PY"), "SGAI")
    lev = lambda p: (p["total_debt"] + p["current_liab"]) / p["total_assets"] \
        if p["total_assets"] else 0
    lvgi = ratio(lev(cy), lev(py), "LVGI") if lev(py) else 1.0
    # TATA — accrual proxy: change in non-cash working capital less depreciation, over TA
    d_wc = (cy["working_capital"] - cy["cash"]) - (py["working_capital"] - py["cash"])
    tata = (d_wc - cy["depreciation"]) / cy["total_assets"] if cy["total_assets"] else 0
    notes.append("TATA computed via working-capital accrual proxy (cash flow statement not an input).")

    m = (-4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi
         + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi)

    verdict = "Possible Manipulator" if m > -2.22 else "Unlikely Manipulator"
    return {
        "score": round(m, 2), "verdict": verdict,
        "components": {
            "DSRI (Days' Sales in Receivables Index)": round(dsri, 3),
            "GMI (Gross Margin Index)": round(gmi, 3),
            "AQI (Asset Quality Index)": round(aqi, 3),
            "SGI (Sales Growth Index)": round(sgi, 3),
            "DEPI (Depreciation Index)": round(depi, 3),
            "SGAI (SG&A Index)": round(sgai, 3),
            "TATA (Total Accruals / Total Assets)": round(tata, 3),
            "LVGI (Leverage Index)": round(lvgi, 3),
        },
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Composite Financial Health Score (0–100)
# 40% solvency (Altman) + 25% earnings quality (Beneish) + 20% liquidity + 15% profitability
# ---------------------------------------------------------------------------
def health_score(data: dict, z: dict, m: dict) -> dict:
    ratios = compute_ratios(data["CY"])
    parts = {}

    # Solvency — map Z' onto 0–100 (1.23 → 40, 2.90 → 80)
    if z["score"] is not None:
        zs = max(0.0, min(100.0, (z["score"] / 2.90) * 80))
    else:
        zs = 50.0
    parts["Solvency (Altman Z')"] = round(zs, 1)

    # Earnings quality — distance of M below the -2.22 threshold
    if m["score"] is not None:
        ms = max(0.0, min(100.0, (-2.22 - m["score"]) / 2.0 * 100 + 50))
    else:
        ms = 50.0
    parts["Earnings Quality (Beneish M)"] = round(ms, 1)

    # Liquidity — current ratio scaled (2.0 → 100)
    cr = ratios.get("Current Ratio") or 0
    parts["Liquidity"] = round(max(0.0, min(100.0, cr / 2.0 * 100)), 1)

    # Profitability — net margin scaled (10% → 100)
    npm = ratios.get("Net Profit Margin %") or 0
    parts["Profitability"] = round(max(0.0, min(100.0, npm / 10.0 * 100)), 1)

    score = (0.40 * parts["Solvency (Altman Z')"]
             + 0.25 * parts["Earnings Quality (Beneish M)"]
             + 0.20 * parts["Liquidity"]
             + 0.15 * parts["Profitability"])
    score = round(score, 1)
    band = ("Strong" if score >= 70 else
            "Stable" if score >= 50 else
            "Watchlist" if score >= 35 else "Stressed")
    return {"score": score, "band": band, "parts": parts}


def liquidity_stress_flags(data: dict) -> list[str]:
    """Rule-based going-concern / stress indicators (feeds Auditor's Lens)."""
    cy = derive(data["CY"])
    py = derive(data["PY"])
    r = compute_ratios(data["CY"])
    flags = []
    if cy["working_capital"] < 0:
        flags.append("Negative net working capital in the current year.")
    if (r.get("Current Ratio") or 99) < 1.0:
        flags.append("Current ratio below 1.0 — current liabilities exceed current assets.")
    if (r.get("Interest Coverage (EBIT/Finance Cost)") or 99) < 1.5 and cy["finance_cost"] > 0:
        flags.append("Interest coverage below 1.5x — earnings barely service finance costs.")
    if cy["pat"] < 0:
        flags.append("Net loss incurred in the current year.")
    if cy["pat"] < 0 and py["pat"] < 0:
        flags.append("Losses in two consecutive years — SA 570 going-concern indicator.")
    if cy["total_equity"] < 0:
        flags.append("Negative net worth — strong going-concern doubt indicator.")
    if cy["cash"] < 0.02 * cy["total_assets"]:
        flags.append("Cash below 2% of total assets — thin liquidity buffer.")
    if py["revenue"] > 0 and cy["revenue"] < 0.8 * py["revenue"]:
        flags.append("Revenue declined more than 20% year-on-year.")
    if not flags:
        flags.append("No significant liquidity or going-concern stress indicators noted from the data.")
    return flags
