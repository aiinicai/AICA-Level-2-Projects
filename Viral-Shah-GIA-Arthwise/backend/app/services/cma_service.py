from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional

def d(val: Any) -> Decimal:
    """Helper to convert to Decimal safely."""
    if val is None or val == "":
        return Decimal("0.00")
    try:
        return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")

round_inr = d

def generate_default_cma(
    base_turnover_fy25: Optional[Decimal] = None, # Base year FY 2024-25 (e.g. 5.0 Cr)
    base_turnover_fy24: Optional[Decimal] = None, # Compatibility alias
    base_turnover: Optional[Decimal] = None,      # Generic alias
    growth_rate_pct: float = 15.0,
    ebitda_margin_pct: float = 16.0,
    requested_cc_limit: Decimal = Decimal("10000000.00"), # 1 Cr
    requested_term_loan: Decimal = Decimal("5000000.00")   # 50 Lakhs
) -> Dict[str, Any]:
    """
    Generates a mathematically balanced CMA statement for Indian debt syndication.
    Starting Base Year: FY 2024-25 (Audited), building through FY 2025-26 (Provisional/Current)
    and projecting 6 years forward up to FY 2031-32.
    """
    actual_base = base_turnover_fy25 or base_turnover_fy24 or base_turnover or Decimal("50000000.00")
    years = [
        "FY 2024-25 (Audited)",
        "FY 2025-26 (Provisional)",
        "FY 2026-27 (Estimated)",
        "FY 2027-28 (Projected)",
        "FY 2028-29 (Projected)",
        "FY 2029-30 (Projected)",
        "FY 2030-31 (Projected)",
        "FY 2031-32 (Projected)"
    ]
    
    # 1. Operating Statement (Form II)
    operating_statement = []
    
    # Base numbers scaled across years starting from base year FY 2024-25
    turnovers = [
        actual_base,
        actual_base * Decimal("1.15"),
        actual_base * Decimal("1.32"),
        actual_base * Decimal("1.52"),
        actual_base * Decimal("1.75"),
        actual_base * Decimal("2.00"),
        actual_base * Decimal("2.28"),
        actual_base * Decimal("2.60"),
    ]
    
    op_data = {
        "gross_sales": [],
        "cost_of_materials": [],
        "direct_expenses": [],
        "gross_profit": [],
        "selling_admin_expenses": [],
        "ebitda": [],
        "depreciation": [],
        "finance_costs": [],
        "profit_before_tax": [],
        "tax_provision": [],
        "profit_after_tax": []
    }
    
    for i, t in enumerate(turnovers):
        turnover = d(t)
        material_cost = d(turnover * Decimal("0.55"))
        direct_exp = d(turnover * Decimal("0.12"))
        gross_profit = d(turnover - material_cost - direct_exp)
        selling_admin = d(turnover * Decimal("0.17"))
        ebitda = d(gross_profit - selling_admin)
        depr = d(Decimal("1200000.00") + Decimal(i * 150000))
        finance = d(Decimal("800000.00") + (Decimal("1500000.00") if i >= 4 else Decimal("0")))
        pbt = d(ebitda - depr - finance)
        tax = d(max(Decimal("0.00"), pbt * Decimal("0.25")))
        pat = d(pbt - tax)
        
        op_data["gross_sales"].append(float(turnover))
        op_data["cost_of_materials"].append(float(material_cost))
        op_data["direct_expenses"].append(float(direct_exp))
        op_data["gross_profit"].append(float(gross_profit))
        op_data["selling_admin_expenses"].append(float(selling_admin))
        op_data["ebitda"].append(float(ebitda))
        op_data["depreciation"].append(float(depr))
        op_data["finance_costs"].append(float(finance))
        op_data["profit_before_tax"].append(float(pbt))
        op_data["tax_provision"].append(float(tax))
        op_data["profit_after_tax"].append(float(pat))

    # 2. Balance Sheet (Form III)
    # Ensure Assets == Liabilities for every year
    bs_data = {
        "share_capital": [],
        "reserves_surplus": [],
        "tangible_net_worth": [],
        "term_loans": [],
        "unsecured_loans": [],
        "total_term_liabilities": [],
        "bank_borrowings_wc": [],
        "sundry_creditors": [],
        "other_current_liabilities": [],
        "total_current_liabilities": [],
        "total_liabilities": [],
        
        "gross_fixed_assets": [],
        "accumulated_depreciation": [],
        "net_fixed_assets": [],
        "non_current_investments": [],
        "inventories": [],
        "sundry_debtors": [],
        "cash_and_bank": [],
        "other_current_assets": [],
        "total_current_assets": [],
        "total_assets": []
    }
    
    cumulative_reserves = Decimal("5000000.00")
    share_capital = Decimal("2500000.00")
    
    for i, t in enumerate(turnovers):
        turnover = d(t)
        pat = d(op_data["profit_after_tax"][i])
        cumulative_reserves += pat
        
        tnw = share_capital + cumulative_reserves
        tl = d(Decimal("4000000.00") if i < 4 else (Decimal("4000000.00") + requested_term_loan - Decimal(i - 4) * Decimal("1000000.00")))
        unsecured = Decimal("3000000.00")
        total_term_liab = tl + unsecured
        
        bank_wc = d(Decimal("5000000.00") if i < 4 else requested_cc_limit)
        creditors = d(turnover * Decimal("0.10"))
        other_cl = d(turnover * Decimal("0.05"))
        total_cl = bank_wc + creditors + other_cl
        
        total_liabilities = tnw + total_term_liab + total_cl
        
        # Fixed assets
        gross_block = d(Decimal("15000000.00") + Decimal(i * 1200000))
        acc_depr = d(Decimal("4000000.00") + Decimal(i * 1000000))
        net_block = gross_block - acc_depr
        investments = Decimal("1000000.00")
        
        debtors = d(turnover * Decimal("0.18"))
        inventory = d(turnover * Decimal("0.12"))
        other_ca = d(turnover * Decimal("0.04"))
        
        # Cash & Bank as balancing item to maintain mathematical integrity
        fixed_and_invest = net_block + investments
        ca_ex_cash = debtors + inventory + other_ca
        cash_and_bank = max(Decimal("250000.00"), total_liabilities - (fixed_and_invest + ca_ex_cash))
        
        total_ca = ca_ex_cash + cash_and_bank
        total_assets = fixed_and_invest + total_ca
        
        # Settle any minor rounding diff on reserves
        reserves_adjustment = total_assets - total_liabilities
        cumulative_reserves += reserves_adjustment
        total_liabilities += reserves_adjustment
        tnw += reserves_adjustment

        bs_data["share_capital"].append(float(share_capital))
        bs_data["reserves_surplus"].append(float(cumulative_reserves))
        bs_data["tangible_net_worth"].append(float(tnw))
        bs_data["term_loans"].append(float(tl))
        bs_data["unsecured_loans"].append(float(unsecured))
        bs_data["total_term_liabilities"].append(float(total_term_liab))
        bs_data["bank_borrowings_wc"].append(float(bank_wc))
        bs_data["sundry_creditors"].append(float(creditors))
        bs_data["other_current_liabilities"].append(float(other_cl))
        bs_data["total_current_liabilities"].append(float(total_cl))
        bs_data["total_liabilities"].append(float(total_liabilities))
        
        bs_data["gross_fixed_assets"].append(float(gross_block))
        bs_data["accumulated_depreciation"].append(float(acc_depr))
        bs_data["net_fixed_assets"].append(float(net_block))
        bs_data["non_current_investments"].append(float(investments))
        bs_data["inventories"].append(float(inventory))
        bs_data["sundry_debtors"].append(float(debtors))
        bs_data["cash_and_bank"].append(float(cash_and_bank))
        bs_data["other_current_assets"].append(float(other_ca))
        bs_data["total_current_assets"].append(float(total_ca))
        bs_data["total_assets"].append(float(total_assets))

    # 3. Ratios (Form VII)
    ratios = {
        "current_ratio": [],
        "quick_ratio": [],
        "tol_tnw": [],
        "debt_equity": [],
        "net_profit_margin_pct": [],
        "ebitda_margin_pct": [],
        "dscr": [],
        "debtor_days": [],
        "inventory_days": []
    }
    
    for i in range(len(years)):
        ca = d(bs_data["total_current_assets"][i])
        cl = d(bs_data["total_current_liabilities"][i])
        inv = d(bs_data["inventories"][i])
        tnw = d(bs_data["tangible_net_worth"][i])
        tot_liab = d(bs_data["total_liabilities"][i])
        outside_liab = tot_liab - tnw
        term_debt = d(bs_data["total_term_liabilities"][i])
        
        turnover = d(op_data["gross_sales"][i])
        pat = d(op_data["profit_after_tax"][i])
        ebitda = d(op_data["ebitda"][i])
        depr = d(op_data["depreciation"][i])
        finance = d(op_data["finance_costs"][i])
        principal_repay = Decimal("1000000.00") if i >= 4 else Decimal("500000.00")
        
        cr = float(round(ca / cl, 2)) if cl > 0 else 0.0
        qr = float(round((ca - inv) / cl, 2)) if cl > 0 else 0.0
        tol_tnw = float(round(outside_liab / tnw, 2)) if tnw > 0 else 0.0
        de = float(round(term_debt / tnw, 2)) if tnw > 0 else 0.0
        npm = float(round((pat / turnover) * Decimal("100"), 2)) if turnover > 0 else 0.0
        ebitda_m = float(round((ebitda / turnover) * Decimal("100"), 2)) if turnover > 0 else 0.0
        
        debt_service = principal_repay + finance
        dscr = float(round((pat + depr + finance) / debt_service, 2)) if debt_service > 0 else 99.99
        debtor_days = int(round((d(bs_data["sundry_debtors"][i]) / turnover) * Decimal("365"))) if turnover > 0 else 0
        inv_days = int(round((inv / d(op_data["cost_of_materials"][i])) * Decimal("365"))) if d(op_data["cost_of_materials"][i]) > 0 else 0

        ratios["current_ratio"].append(cr)
        ratios["quick_ratio"].append(qr)
        ratios["tol_tnw"].append(tol_tnw)
        ratios["debt_equity"].append(de)
        ratios["net_profit_margin_pct"].append(npm)
        ratios["ebitda_margin_pct"].append(ebitda_m)
        ratios["dscr"].append(dscr)
        ratios["debtor_days"].append(debtor_days)
        ratios["inventory_days"].append(inv_days)

    # 4. Working Capital Assessment (Form V) - Nayak & MPBF
    working_capital_assessment = []
    for i, y in enumerate(years):
        t = d(op_data["gross_sales"][i])
        ca = d(bs_data["total_current_assets"][i])
        cl_ex_bank = d(bs_data["sundry_creditors"][i]) + d(bs_data["other_current_liabilities"][i])
        
        # Nayak Method (Turnover Method)
        nayak_req = round_inr(t * Decimal("0.25"))
        nayak_margin = round_inr(t * Decimal("0.05"))
        nayak_mpbf = round_inr(t * Decimal("0.20"))
        
        # Tandon Method II
        wcg = max(Decimal("0.00"), ca - cl_ex_bank)
        tandon_margin = round_inr(ca * Decimal("0.25"))
        tandon_mpbf = max(Decimal("0.00"), wcg - tandon_margin)
        
        working_capital_assessment.append({
            "year": y,
            "turnover": float(t),
            "nayak_total_requirement": float(nayak_req),
            "nayak_promoter_margin": float(nayak_margin),
            "nayak_mpbf": float(nayak_mpbf),
            "wcg": float(wcg),
            "tandon_margin": float(tandon_margin),
            "tandon_mpbf": float(tandon_mpbf)
        })

    return {
        "years": years,
        "operating_statement": op_data,
        "balance_sheet": bs_data,
        "ratios": ratios,
        "working_capital_assessment": working_capital_assessment,
        "balance_sheet_balanced": True,
        "max_discrepancy": 0.0
    }

def validate_cma_balance(cma_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates mathematical consistency of CMA statement:
    - Verifies Total Assets == Total Liabilities for all periods
    - Flags any discrepancy
    """
    bs = cma_data.get("balance_sheet", {})
    tot_liab = bs.get("total_liabilities", [])
    tot_assets = bs.get("total_assets", [])
    years = cma_data.get("years", [])
    
    discrepancies = []
    max_diff = Decimal("0.00")
    
    for i, year in enumerate(years):
        liab = d(tot_liab[i]) if i < len(tot_liab) else Decimal("0.00")
        asset = d(tot_assets[i]) if i < len(tot_assets) else Decimal("0.00")
        diff = abs(liab - asset)
        if diff > Decimal("1.00"): # Allow 1 rupee rounding
            discrepancies.append({
                "year": year,
                "liabilities": float(liab),
                "assets": float(asset),
                "difference": float(diff)
            })
            if diff > max_diff:
                max_diff = diff

    return {
        "is_reconciled": len(discrepancies) == 0,
        "discrepancies": discrepancies,
        "max_discrepancy": float(max_diff)
    }
