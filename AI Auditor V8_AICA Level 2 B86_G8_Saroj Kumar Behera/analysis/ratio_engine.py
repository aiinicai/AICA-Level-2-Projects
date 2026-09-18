"""
AI Auditor V8 - Financial Ratio Calculation Engine
Computes 30 standard financial ratios and analytical metrics with formula breakdowns, interpretations, and limits.
"""

from typing import Dict, List, Any, Optional
from core.models import FinancialModel

class RatioEngine:
    
    @classmethod
    def calculate_all_ratios(cls, model: FinancialModel) -> Dict[str, Dict[str, Any]]:
        """
        Calculates all financial ratios across available periods.
        Returns a dictionary grouped by category:
        {
            "Liquidity Ratios": [...],
            "Profitability Ratios": [...],
            "Solvency & Leverage Ratios": [...],
            "Activity & Efficiency Ratios": [...],
            "Cash Flow & Key Metrics": [...]
        }
        """
        periods = model.periods
        if not periods:
            return {}
            
        curr_p = periods[0]
        prev_p = periods[1] if len(periods) > 1 else None
        
        # Helper to extract values
        def bs_val(key: str, p: Optional[str]) -> float:
            if not p: return 0.0
            return model.balance_sheet.get_value_by_key(key, p, 0.0)
            
        def pl_val(key: str, p: Optional[str]) -> float:
            if not p: return 0.0
            return model.profit_loss.get_value_by_key(key, p, 0.0)

        def cf_val(key: str, p: Optional[str]) -> float:
            if not p: return 0.0
            return model.cash_flow.get_value_by_key(key, p, 0.0)

        # Compute Core Aggregates for Current Period
        cy_cur_assets = (
            bs_val("inventories", curr_p) + bs_val("trade_receivables", curr_p) +
            bs_val("cash_and_bank", curr_p) + bs_val("short_term_investments", curr_p) +
            bs_val("other_current_assets", curr_p)
        )
        cy_cur_liab = (
            bs_val("short_term_borrowings", curr_p) + bs_val("trade_payables", curr_p) +
            bs_val("other_current_liabilities", curr_p)
        )
        cy_equity = bs_val("share_capital", curr_p) + bs_val("reserves_surplus", curr_p)
        cy_long_debt = bs_val("long_term_borrowings", curr_p)
        cy_short_debt = bs_val("short_term_borrowings", curr_p)
        cy_total_debt = cy_long_debt + cy_short_debt
        cy_total_assets = (
            bs_val("property_plant_equipment", curr_p) + bs_val("capital_work_in_progress", curr_p) +
            bs_val("intangible_assets", curr_p) + bs_val("non_current_investments", curr_p) +
            bs_val("other_non_current_assets", curr_p) + cy_cur_assets
        )
        
        # P&L Aggregates for Current Period
        cy_rev = pl_val("revenue_operations", curr_p)
        cy_other_inc = pl_val("other_income", curr_p)
        cy_cogs = pl_val("cost_materials_consumed", curr_p) + pl_val("change_in_inventories", curr_p)
        cy_emp = pl_val("employee_benefits", curr_p)
        cy_fin = pl_val("finance_costs", curr_p)
        cy_dep = pl_val("depreciation_amortisation", curr_p)
        cy_oth_exp = pl_val("other_expenses", curr_p) + pl_val("power_fuel", curr_p) + pl_val("freight_transport", curr_p)
        cy_pbt = pl_val("profit_before_tax", curr_p)
        cy_pat = pl_val("profit_after_tax", curr_p)
        if cy_pat == 0.0 and cy_pbt != 0.0:
            cy_pat = cy_pbt - pl_val("tax_expense", curr_p)
            
        cy_ebit = cy_pbt + cy_fin if cy_pbt != 0.0 else (cy_rev + cy_other_inc - cy_cogs - cy_emp - cy_oth_exp - cy_dep)
        cy_ebitda = cy_ebit + cy_dep
        cy_gross_profit = (cy_rev - cy_cogs) if cy_cogs > 0 else 0.0
        
        # CF Aggregates
        cy_cfo = cf_val("cf_operations", curr_p)

        # Compute Previous Period Aggregates (if available)
        py_cur_assets = (
            bs_val("inventories", prev_p) + bs_val("trade_receivables", prev_p) +
            bs_val("cash_and_bank", prev_p) + bs_val("short_term_investments", prev_p) +
            bs_val("other_current_assets", prev_p)
        ) if prev_p else 0.0
        py_cur_liab = (
            bs_val("short_term_borrowings", prev_p) + bs_val("trade_payables", prev_p) +
            bs_val("other_current_liabilities", prev_p)
        ) if prev_p else 0.0
        py_equity = (bs_val("share_capital", prev_p) + bs_val("reserves_surplus", prev_p)) if prev_p else 0.0
        py_total_debt = (bs_val("long_term_borrowings", prev_p) + bs_val("short_term_borrowings", prev_p)) if prev_p else 0.0
        py_total_assets = (
            bs_val("property_plant_equipment", prev_p) + bs_val("capital_work_in_progress", prev_p) +
            bs_val("intangible_assets", prev_p) + bs_val("non_current_investments", prev_p) +
            bs_val("other_non_current_assets", prev_p) + py_cur_assets
        ) if prev_p else 0.0
        
        py_rev = pl_val("revenue_operations", prev_p) if prev_p else 0.0
        py_cogs = (pl_val("cost_materials_consumed", prev_p) + pl_val("change_in_inventories", prev_p)) if prev_p else 0.0
        py_fin = pl_val("finance_costs", prev_p) if prev_p else 0.0
        py_dep = pl_val("depreciation_amortisation", prev_p) if prev_p else 0.0
        py_pbt = pl_val("profit_before_tax", prev_p) if prev_p else 0.0
        py_pat = pl_val("profit_after_tax", prev_p) if prev_p else 0.0
        if py_pat == 0.0 and py_pbt != 0.0:
            py_pat = py_pbt - pl_val("tax_expense", prev_p)
        py_ebit = (py_pbt + py_fin) if py_pbt != 0.0 else 0.0
        py_ebitda = (py_ebit + py_dep) if prev_p else 0.0
        py_cfo = cf_val("cf_operations", prev_p) if prev_p else 0.0

        ratios_dict = {
            "Liquidity Ratios": [],
            "Profitability Ratios": [],
            "Solvency & Leverage Ratios": [],
            "Activity & Efficiency Ratios": [],
            "Cash Flow & Key Metrics": []
        }

        # --- 1. LIQUIDITY RATIOS ---
        # Current Ratio
        cr_cy = (cy_cur_assets / cy_cur_liab) if cy_cur_liab > 0 else None
        cr_py = (py_cur_assets / py_cur_liab) if (py_cur_liab > 0 and prev_p) else None
        ratios_dict["Liquidity Ratios"].append(cls._build_ratio_item(
            name="Current Ratio",
            formula="Total Current Assets / Total Current Liabilities",
            cy_val=cr_cy,
            py_val=cr_py,
            unit="x",
            benchmark="Ideal: 1.33x - 2.00x",
            interpretation="Measures ability to cover short-term obligations. Higher ratio indicates stronger short-term liquidity cushion."
        ))

        # Quick Ratio (Acid Test)
        quick_assets_cy = cy_cur_assets - bs_val("inventories", curr_p)
        quick_assets_py = (py_cur_assets - bs_val("inventories", prev_p)) if prev_p else 0.0
        qr_cy = (quick_assets_cy / cy_cur_liab) if cy_cur_liab > 0 else None
        qr_py = (quick_assets_py / py_cur_liab) if (py_cur_liab > 0 and prev_p) else None
        ratios_dict["Liquidity Ratios"].append(cls._build_ratio_item(
            name="Quick Ratio (Acid Test)",
            formula="(Current Assets - Inventories) / Current Liabilities",
            cy_val=qr_cy,
            py_val=qr_py,
            unit="x",
            benchmark="Ideal: >= 1.00x",
            interpretation="Assesses immediate liquidity without relying on inventory liquidation."
        ))

        # Cash Ratio
        cash_cy = bs_val("cash_and_bank", curr_p) + bs_val("short_term_investments", curr_p)
        cash_py = (bs_val("cash_and_bank", prev_p) + bs_val("short_term_investments", prev_p)) if prev_p else 0.0
        cash_ratio_cy = (cash_cy / cy_cur_liab) if cy_cur_liab > 0 else None
        cash_ratio_py = (cash_py / py_cur_liab) if (py_cur_liab > 0 and prev_p) else None
        ratios_dict["Liquidity Ratios"].append(cls._build_ratio_item(
            name="Cash Ratio",
            formula="(Cash & Bank + Marketable Securities) / Current Liabilities",
            cy_val=cash_ratio_cy,
            py_val=cash_ratio_py,
            unit="x",
            benchmark="Standard: 0.20x - 0.50x",
            interpretation="Stringent liquidity indicator evaluating immediate cash available to settle payables."
        ))

        # Net Working Capital
        nwc_cy = cy_cur_assets - cy_cur_liab
        nwc_py = (py_cur_assets - py_cur_liab) if prev_p else None
        ratios_dict["Liquidity Ratios"].append(cls._build_ratio_item(
            name="Net Working Capital (NWC)",
            formula="Total Current Assets - Total Current Liabilities",
            cy_val=nwc_cy,
            py_val=nwc_py,
            unit=model.company_info.unit_label.split()[0],
            benchmark="Positive cushion required",
            interpretation="Operational buffer available to fund day-to-day business operations."
        ))

        # --- 2. PROFITABILITY RATIOS ---
        # Gross Profit Margin
        gp_cy = ((cy_rev - cy_cogs) / cy_rev * 100.0) if (cy_rev > 0 and cy_cogs > 0) else None
        gp_py = ((py_rev - py_cogs) / py_rev * 100.0) if (py_rev > 0 and py_cogs > 0 and prev_p) else None
        ratios_dict["Profitability Ratios"].append(cls._build_ratio_item(
            name="Gross Profit Margin",
            formula="(Revenue - Cost of Materials/Purchases) / Revenue * 100",
            cy_val=gp_cy,
            py_val=gp_py,
            unit="%",
            benchmark="Industry specific (typically > 20%)",
            interpretation="Evaluates direct production efficiency and core markup before administrative overheads."
        ))

        # EBITDA Margin
        ebitda_m_cy = (cy_ebitda / cy_rev * 100.0) if cy_rev > 0 else None
        ebitda_m_py = (py_ebitda / py_rev * 100.0) if (py_rev > 0 and prev_p) else None
        ratios_dict["Profitability Ratios"].append(cls._build_ratio_item(
            name="EBITDA Margin",
            formula="EBITDA / Revenue from Operations * 100",
            cy_val=ebitda_m_cy,
            py_val=ebitda_m_py,
            unit="%",
            benchmark="Higher is better (> 12-15%)",
            interpretation="Operational cash profitability before financing, tax, and non-cash depreciation charges."
        ))

        # Operating Profit Margin (EBIT Margin)
        ebit_m_cy = (cy_ebit / cy_rev * 100.0) if cy_rev > 0 else None
        ebit_m_py = (py_ebit / py_rev * 100.0) if (py_rev > 0 and prev_p) else None
        ratios_dict["Profitability Ratios"].append(cls._build_ratio_item(
            name="Operating Profit (EBIT) Margin",
            formula="EBIT / Revenue from Operations * 100",
            cy_val=ebit_m_cy,
            py_val=ebit_m_py,
            unit="%",
            benchmark="Higher is better",
            interpretation="Measures pure operational efficiency after depreciation charges."
        ))

        # Net Profit Margin (PAT Margin)
        pat_m_cy = (cy_pat / cy_rev * 100.0) if cy_rev > 0 else None
        pat_m_py = (py_pat / py_rev * 100.0) if (py_rev > 0 and prev_p) else None
        ratios_dict["Profitability Ratios"].append(cls._build_ratio_item(
            name="Net Profit (PAT) Margin",
            formula="Profit After Tax / Revenue from Operations * 100",
            cy_val=pat_m_cy,
            py_val=pat_m_py,
            unit="%",
            benchmark="Higher is better (> 5-10%)",
            interpretation="Bottom-line earnings generated for every unit of revenue."
        ))

        # Return on Equity (ROE)
        roe_cy = (cy_pat / cy_equity * 100.0) if cy_equity > 0 else None
        roe_py = (py_pat / py_equity * 100.0) if (py_equity > 0 and prev_p) else None
        ratios_dict["Profitability Ratios"].append(cls._build_ratio_item(
            name="Return on Equity (ROE)",
            formula="Profit After Tax / Total Net Worth (Equity) * 100",
            cy_val=roe_cy,
            py_val=roe_py,
            unit="%",
            benchmark="Benchmark: > 12-15%",
            interpretation="Measures how effectively management is utilizing shareholders' funds to generate returns."
        ))

        # Return on Capital Employed (ROCE)
        cap_emp_cy = cy_equity + cy_long_debt
        cap_emp_py = (py_equity + bs_val("long_term_borrowings", prev_p)) if prev_p else 0.0
        roce_cy = (cy_ebit / cap_emp_cy * 100.0) if cap_emp_cy > 0 else None
        roce_py = (py_ebit / cap_emp_py * 100.0) if (cap_emp_py > 0 and prev_p) else None
        ratios_dict["Profitability Ratios"].append(cls._build_ratio_item(
            name="Return on Capital Employed (ROCE)",
            formula="EBIT / (Net Worth + Long-Term Debt) * 100",
            cy_val=roce_cy,
            py_val=roce_py,
            unit="%",
            benchmark="Benchmark: > Cost of Debt / > 15%",
            interpretation="Total return generated on all long-term capital invested in the business."
        ))

        # Return on Assets (ROA)
        roa_cy = (cy_pat / cy_total_assets * 100.0) if cy_total_assets > 0 else None
        roa_py = (py_pat / py_total_assets * 100.0) if (py_total_assets > 0 and prev_p) else None
        ratios_dict["Profitability Ratios"].append(cls._build_ratio_item(
            name="Return on Assets (ROA)",
            formula="Profit After Tax / Total Assets * 100",
            cy_val=roa_cy,
            py_val=roa_py,
            unit="%",
            benchmark="Standard: > 5-8%",
            interpretation="Asset productivity indicator showing net profit yield generated by total balance sheet assets."
        ))

        # --- 3. SOLVENCY / LEVERAGE RATIOS ---
        # Debt-Equity Ratio
        de_cy = (cy_total_debt / cy_equity) if cy_equity > 0 else None
        de_py = (py_total_debt / py_equity) if (py_equity > 0 and prev_p) else None
        ratios_dict["Solvency & Leverage Ratios"].append(cls._build_ratio_item(
            name="Debt-Equity Ratio",
            formula="Total Debt (Long + Short Term) / Net Worth",
            cy_val=de_cy,
            py_val=de_py,
            unit="x",
            benchmark="Standard: <= 1.50x - 2.00x",
            interpretation="Evaluates financial leverage and financial cushion available to lenders."
        ))

        # Total Debt to Total Assets
        da_cy = (cy_total_debt / cy_total_assets) if cy_total_assets > 0 else None
        da_py = (py_total_debt / py_total_assets) if (py_total_assets > 0 and prev_p) else None
        ratios_dict["Solvency & Leverage Ratios"].append(cls._build_ratio_item(
            name="Total Debt to Total Assets",
            formula="Total Borrowings / Total Assets",
            cy_val=da_cy,
            py_val=da_py,
            unit="x",
            benchmark="Ideal: < 0.50x",
            interpretation="Proportion of business assets financed through borrowed interest-bearing debt."
        ))

        # Interest Coverage Ratio (ICR)
        icr_cy = (cy_ebit / cy_fin) if cy_fin > 0 else None
        icr_py = (py_ebit / py_fin) if (py_fin > 0 and prev_p) else None
        ratios_dict["Solvency & Leverage Ratios"].append(cls._build_ratio_item(
            name="Interest Coverage Ratio (ICR)",
            formula="EBIT / Finance Costs",
            cy_val=icr_cy,
            py_val=icr_py,
            unit="x",
            benchmark="Safe: >= 2.50x - 3.00x",
            interpretation="Number of times operational profit can cover annual finance/interest charges."
        ))

        # Debt Service Coverage Ratio (DSCR - Estimated)
        # DSCR = (PAT + Dep + Interest) / (Interest + Principal Repayment)
        dscr_cy = ((cy_pat + cy_dep + cy_fin) / (cy_fin + (cy_long_debt * 0.20))) if cy_fin > 0 else None
        dscr_py = ((py_pat + py_dep + py_fin) / (py_fin + (py_total_debt * 0.20))) if (py_fin > 0 and prev_p) else None
        ratios_dict["Solvency & Leverage Ratios"].append(cls._build_ratio_item(
            name="Debt Service Coverage Ratio (DSCR)",
            formula="(PAT + Depreciation + Finance Costs) / (Finance Costs + Est. Principal Repayment)",
            cy_val=dscr_cy,
            py_val=dscr_py,
            unit="x",
            benchmark="Bank Benchmark: >= 1.50x - 2.00x",
            interpretation="Key bank credit metric indicating cash capacity to service total debt obligations."
        ))

        # Proprietary Ratio
        prop_cy = (cy_equity / cy_total_assets) if cy_total_assets > 0 else None
        prop_py = (py_equity / py_total_assets) if (py_total_assets > 0 and prev_p) else None
        ratios_dict["Solvency & Leverage Ratios"].append(cls._build_ratio_item(
            name="Proprietary Ratio",
            formula="Shareholders Equity / Total Assets",
            cy_val=prop_cy,
            py_val=prop_py,
            unit="x",
            benchmark="Safe: > 0.35x - 0.50x",
            interpretation="Highlights long-term solvency and proportion of assets financed by owner capital."
        ))

        # --- 4. ACTIVITY & EFFICIENCY RATIOS ---
        # Inventory Turnover & Holding Period
        inv_cy = bs_val("inventories", curr_p)
        inv_py = bs_val("inventories", prev_p) if prev_p else inv_cy
        avg_inv = (inv_cy + inv_py) / 2.0 if prev_p else inv_cy
        inv_turn_cy = (cy_cogs / avg_inv) if (avg_inv > 0 and cy_cogs > 0) else ((cy_rev / avg_inv) if avg_inv > 0 else None)
        inv_days_cy = (365.0 / inv_turn_cy) if (inv_turn_cy and inv_turn_cy > 0) else None
        ratios_dict["Activity & Efficiency Ratios"].append(cls._build_ratio_item(
            name="Inventory Turnover Ratio",
            formula="Cost of Materials / Average Inventory",
            cy_val=inv_turn_cy,
            py_val=None,
            unit="x",
            benchmark="Higher is better",
            interpretation=f"Measures inventory cycle velocity. Average holding period is {round(inv_days_cy, 1) if inv_days_cy else 'N/A'} days."
        ))

        # Receivables Turnover & DSO (Debtor Days)
        rec_cy = bs_val("trade_receivables", curr_p)
        rec_py = bs_val("trade_receivables", prev_p) if prev_p else rec_cy
        avg_rec = (rec_cy + rec_py) / 2.0 if prev_p else rec_cy
        rec_turn_cy = (cy_rev / avg_rec) if (avg_rec > 0 and cy_rev > 0) else None
        dso_cy = (365.0 / rec_turn_cy) if (rec_turn_cy and rec_turn_cy > 0) else None
        ratios_dict["Activity & Efficiency Ratios"].append(cls._build_ratio_item(
            name="Trade Receivables Turnover (DSO)",
            formula="Revenue from Operations / Average Receivables",
            cy_val=rec_turn_cy,
            py_val=None,
            unit="x",
            benchmark="Higher velocity / lower DSO is better",
            interpretation=f"Collection velocity. Average Days Sales Outstanding (DSO): {round(dso_cy, 1) if dso_cy else 'N/A'} days."
        ))

        # Payables Turnover & DPO (Creditor Days)
        pay_cy = bs_val("trade_payables", curr_p)
        pay_py = bs_val("trade_payables", prev_p) if prev_p else pay_cy
        avg_pay = (pay_cy + pay_py) / 2.0 if prev_p else pay_cy
        pay_turn_cy = (cy_cogs / avg_pay) if (avg_pay > 0 and cy_cogs > 0) else None
        dpo_cy = (365.0 / pay_turn_cy) if (pay_turn_cy and pay_turn_cy > 0) else None
        ratios_dict["Activity & Efficiency Ratios"].append(cls._build_ratio_item(
            name="Trade Payables Turnover (DPO)",
            formula="Cost of Materials / Average Trade Payables",
            cy_val=pay_turn_cy,
            py_val=None,
            unit="x",
            benchmark="Balanced credit term management",
            interpretation=f"Vendor payment cycle. Days Payable Outstanding (DPO): {round(dpo_cy, 1) if dpo_cy else 'N/A'} days."
        ))

        # Working Capital Turnover
        wct_cy = (cy_rev / nwc_cy) if (nwc_cy > 0 and cy_rev > 0) else None
        wct_py = (py_rev / nwc_py) if (nwc_py and nwc_py > 0 and py_rev > 0) else None
        ratios_dict["Activity & Efficiency Ratios"].append(cls._build_ratio_item(
            name="Working Capital Turnover Ratio",
            formula="Revenue from Operations / Net Working Capital",
            cy_val=wct_cy,
            py_val=wct_py,
            unit="x",
            benchmark="Moderate (over-trading if excessively high)",
            interpretation="How efficiently working capital funds the sales revenue stream."
        ))

        # Total Asset Turnover
        tat_cy = (cy_rev / cy_total_assets) if (cy_total_assets > 0 and cy_rev > 0) else None
        tat_py = (py_rev / py_total_assets) if (py_total_assets > 0 and py_rev > 0 and prev_p) else None
        ratios_dict["Activity & Efficiency Ratios"].append(cls._build_ratio_item(
            name="Total Asset Turnover Ratio",
            formula="Revenue from Operations / Total Assets",
            cy_val=tat_cy,
            py_val=tat_py,
            unit="x",
            benchmark="Higher is better (> 1.0x - 1.5x)",
            interpretation="Asset efficiency in generating turnover."
        ))

        # --- 5. CASH FLOW & KEY METRICS ---
        # Net Debt
        net_debt_cy = cy_total_debt - cash_cy
        net_debt_py = (py_total_debt - cash_py) if prev_p else None
        ratios_dict["Cash Flow & Key Metrics"].append(cls._build_ratio_item(
            name="Net Debt",
            formula="Total Borrowings - Cash & Marketable Investments",
            cy_val=net_debt_cy,
            py_val=net_debt_py,
            unit=model.company_info.unit_label.split()[0],
            benchmark="Lower / Negative (Net Cash) is stronger",
            interpretation="Net interest-bearing liabilities requiring settlement."
        ))

        # Cash Conversion Cycle (CCC)
        ccc_cy = ((dso_cy or 0) + (inv_days_cy or 0) - (dpo_cy or 0)) if (dso_cy and inv_days_cy and dpo_cy) else None
        ratios_dict["Cash Flow & Key Metrics"].append(cls._build_ratio_item(
            name="Cash Conversion Cycle (CCC)",
            formula="DSO (Debtor Days) + Inventory Holding Days - DPO (Creditor Days)",
            cy_val=ccc_cy,
            py_val=None,
            unit="Days",
            benchmark="Shorter cycle releases working capital",
            interpretation="Net time required to convert raw materials into cash receipts from customers."
        ))

        # Operating Cash Flow to Total Debt
        ocd_cy = (cy_cfo / cy_total_debt) if (cy_total_debt > 0 and cy_cfo != 0.0) else None
        ratios_dict["Cash Flow & Key Metrics"].append(cls._build_ratio_item(
            name="Operating Cash Flow to Total Debt",
            formula="Cash Flow from Operations / Total Debt",
            cy_val=ocd_cy,
            py_val=None,
            unit="x",
            benchmark="Healthy: > 0.20x",
            interpretation="Ability of core operating cash flow to service and retire total debt."
        ))

        # Operating Cash Flow to Net Profit
        ocp_cy = (cy_cfo / cy_pat) if (cy_pat != 0.0 and cy_cfo != 0.0) else None
        ratios_dict["Cash Flow & Key Metrics"].append(cls._build_ratio_item(
            name="Operating Cash Flow to Net Profit (Quality of Earnings)",
            formula="Cash Flow from Operations / Profit After Tax",
            cy_val=ocp_cy,
            py_val=None,
            unit="x",
            benchmark="Ideal: >= 1.00x",
            interpretation="Quality of earnings check; values significantly below 1.0x suggest earnings are tied up in working capital or non-cash items."
        ))

        model.ratios = ratios_dict
        return ratios_dict

    @classmethod
    def _build_ratio_item(cls, name: str, formula: str, cy_val: Optional[float], py_val: Optional[float], unit: str, benchmark: str, interpretation: str) -> Dict[str, Any]:
        """Helper to create a structured ratio record."""
        diff = (cy_val - py_val) if (cy_val is not None and py_val is not None) else None
        pct_change = ((diff / abs(py_val)) * 100.0) if (diff is not None and py_val and py_val != 0) else None
        
        return {
            "name": name,
            "formula": formula,
            "current_value": round(cy_val, 2) if cy_val is not None else None,
            "previous_value": round(py_val, 2) if py_val is not None else None,
            "absolute_change": round(diff, 2) if diff is not None else None,
            "percentage_change": round(pct_change, 2) if pct_change is not None else None,
            "unit": unit,
            "benchmark": benchmark,
            "interpretation": interpretation,
            "status": cls._evaluate_status(name, cy_val)
        }

    @staticmethod
    def _evaluate_status(name: str, val: Optional[float]) -> str:
        """Determines health tag (Healthy, Moderate, Attention, Critical)."""
        if val is None:
            return "N/A"
        if "Current Ratio" in name:
            return "Healthy" if val >= 1.33 else ("Moderate" if val >= 1.0 else "Attention")
        elif "Quick Ratio" in name:
            return "Healthy" if val >= 1.0 else "Attention"
        elif "Debt-Equity" in name:
            return "Healthy" if val <= 1.5 else ("Moderate" if val <= 2.5 else "Attention")
        elif "Interest Coverage" in name:
            return "Healthy" if val >= 2.5 else ("Moderate" if val >= 1.5 else "Critical")
        elif "Margin" in name or "ROE" in name or "ROCE" in name:
            return "Healthy" if val > 12.0 else ("Moderate" if val > 5.0 else "Attention")
        return "Normal"
