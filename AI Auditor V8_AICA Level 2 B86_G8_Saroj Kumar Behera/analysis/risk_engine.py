"""
AI Auditor V8 - Risk Identification & Red Flag Detection Engine
Detects potential financial distress, working capital anomalies, and audit attention areas.
"""

from typing import Dict, List, Any, Optional
from core.models import FinancialModel

class RiskEngine:

    @classmethod
    def evaluate_risks(cls, model: FinancialModel) -> List[Dict[str, Any]]:
        """
        Scans financial model metrics and ratios to identify POTENTIAL RISK / ATTENTION AREAS.
        """
        periods = model.periods
        if not periods:
            return []

        curr_p = periods[0]
        prev_p = periods[1] if len(periods) > 1 else None

        risks = []

        def bs_val(k: str, p: Optional[str]) -> float:
            if not p: return 0.0
            return model.balance_sheet.get_value_by_key(k, p, 0.0)

        def pl_val(k: str, p: Optional[str]) -> float:
            if not p: return 0.0
            return model.profit_loss.get_value_by_key(k, p, 0.0)

        def cf_val(k: str, p: Optional[str]) -> float:
            if not p: return 0.0
            return model.cash_flow.get_value_by_key(k, p, 0.0)

        # 1. Revenue Decline Risk
        rev_cy = pl_val("revenue_operations", curr_p)
        rev_py = pl_val("revenue_operations", prev_p) if prev_p else 0.0
        if rev_py > 0 and rev_cy < rev_py:
            drop_pct = ((rev_py - rev_cy) / rev_py) * 100.0
            if drop_pct >= 5.0:
                risks.append({
                    "category": "Top-Line Contraction",
                    "severity": "High" if drop_pct >= 15.0 else "Medium",
                    "title": f"Revenue Declined by {round(drop_pct, 1)}%",
                    "description": f"Revenue from operations fell from {rev_py:,.2f} to {rev_cy:,.2f}. Prolonged sales contraction impacts fixed cost absorption and operating leverage.",
                    "audit_implication": "Assess going concern assumptions, customer concentration, and fixed asset impairment testing under AS 28 / Ind AS 36."
                })

        # 2. Profitability / Net Losses
        pat_cy = pl_val("profit_after_tax", curr_p)
        pat_py = pl_val("profit_after_tax", prev_p) if prev_p else 0.0
        if pat_cy < 0:
            risks.append({
                "category": "Operational Loss",
                "severity": "High",
                "title": "Net Loss Incurred in Current Period",
                "description": f"The entity reported a net loss of {pat_cy:,.2f} for {curr_p}. Losses erode shareholders' equity and strain debt servicing capacity.",
                "audit_implication": "Review cash-burn runway, debt repayment schedule, and management's turnaround strategy."
            })
        elif pat_py > 0 and pat_cy < pat_py and ((pat_py - pat_cy) / pat_py) >= 0.20:
            drop_pat = ((pat_py - pat_cy) / pat_py) * 100.0
            risks.append({
                "category": "Profit Margin Erosion",
                "severity": "Medium",
                "title": f"Net Profit Dropped by {round(drop_pat, 1)}%",
                "description": f"Net profit fell significantly from {pat_py:,.2f} to {pat_cy:,.2f} despite operational volume.",
                "audit_implication": "Scrutinize gross margins, rising input costs, higher finance costs, or one-off exceptional items."
            })

        # 3. Negative Net Working Capital (Current Ratio < 1.0)
        ca_cy = (bs_val("inventories", curr_p) + bs_val("trade_receivables", curr_p) +
                 bs_val("cash_and_bank", curr_p) + bs_val("short_term_investments", curr_p) +
                 bs_val("other_current_assets", curr_p))
        cl_cy = (bs_val("short_term_borrowings", curr_p) + bs_val("trade_payables", curr_p) +
                 bs_val("other_current_liabilities", curr_p))
        if cl_cy > 0 and ca_cy < cl_cy:
            deficit = cl_cy - ca_cy
            risks.append({
                "category": "Liquidity Distress",
                "severity": "High",
                "title": "Negative Net Working Capital (Current Ratio < 1.0x)",
                "description": f"Current liabilities ({cl_cy:,.2f}) exceed current assets ({ca_cy:,.2f}) by a deficit of {deficit:,.2f}. Current ratio is {round(ca_cy/cl_cy, 2):.2f}x.",
                "audit_implication": "Indicates short-term liquidity stress and potential dependency on short-term bank limit rollovers or delayed vendor payments."
            })

        # 4. Excessive Leverage (Debt-Equity > 2.0x)
        equity_cy = bs_val("share_capital", curr_p) + bs_val("reserves_surplus", curr_p)
        debt_cy = bs_val("long_term_borrowings", curr_p) + bs_val("short_term_borrowings", curr_p)
        if equity_cy > 0 and (debt_cy / equity_cy) > 2.0:
            de_ratio = debt_cy / equity_cy
            risks.append({
                "category": "Capital Structure & Solvency",
                "severity": "High",
                "title": f"High Debt-Equity Ratio ({round(de_ratio, 2)}x)",
                "description": f"Total debt of {debt_cy:,.2f} is {round(de_ratio, 2)} times the net worth of {equity_cy:,.2f}.",
                "audit_implication": "Verify debt covenants, lender NOCs, charge registration on ROC, and risk of interest rate sensitivity."
            })

        # 5. Weak Interest Coverage (< 1.5x)
        fin_cy = pl_val("finance_costs", curr_p)
        pbt_cy = pl_val("profit_before_tax", curr_p)
        ebit_cy = (pbt_cy + fin_cy) if pbt_cy != 0.0 else 0.0
        if fin_cy > 0:
            icr = ebit_cy / fin_cy
            if icr < 1.5:
                risks.append({
                    "category": "Debt Servicing Capacity",
                    "severity": "High" if icr < 1.0 else "Medium",
                    "title": f"Low Interest Coverage Ratio ({round(icr, 2)}x)",
                    "description": f"Operational profit (EBIT: {ebit_cy:,.2f}) provides narrow coverage for finance costs ({fin_cy:,.2f}).",
                    "audit_implication": "Evaluate lender default risk and obtain external bank confirmation of timely debt servicing."
                })

        # 6. Receivables Spurt Exceeding Revenue
        rec_cy = bs_val("trade_receivables", curr_p)
        rec_py = bs_val("trade_receivables", prev_p) if prev_p else 0.0
        if prev_p and rec_py > 0 and rev_py > 0:
            rec_growth = ((rec_cy - rec_py) / rec_py) * 100.0
            rev_growth = ((rev_cy - rev_py) / rev_py) * 100.0
            if rec_growth > rev_growth + 10.0 and rec_growth > 15.0:
                risks.append({
                    "category": "Receivables & Credit Risk",
                    "severity": "Medium",
                    "title": f"Receivables Growth ({round(rec_growth, 1)}%) Outpaces Revenue Growth ({round(rev_growth, 1)}%)",
                    "description": "Debtors have expanded substantially faster than top-line revenue, indicating extended credit or collection delays.",
                    "audit_implication": "Perform extensive customer balance confirmations (SA 505) and review debtor ageing (> 180 days) for ECL provisioning."
                })

        # 7. Quality of Earnings / Cash Flow Mismatch
        cfo_cy = cf_val("cf_operations", curr_p)
        if pat_cy > 0 and cfo_cy < 0:
            risks.append({
                "category": "Earnings Quality & Cash Flow Divergence",
                "severity": "High",
                "title": "Positive Net Profit with Negative Operating Cash Flow",
                "description": f"Reported PAT is positive ({pat_cy:,.2f}), but Operating Cash Flow is negative ({cfo_cy:,.2f}). Operating profits are locked in working capital or non-cash revenues.",
                "audit_implication": "Examine revenue cut-off, inventory buildup, and debtors collection cycle to verify real cash generation."
            })

        # 8. Surge in Borrowings
        if prev_p:
            debt_py = bs_val("long_term_borrowings", prev_p) + bs_val("short_term_borrowings", prev_p)
            if debt_py > 0 and debt_cy > debt_py:
                borrowing_growth = ((debt_cy - debt_py) / debt_py) * 100.0
                if borrowing_growth >= 25.0:
                    risks.append({
                        "category": "Leverage Expansion",
                        "severity": "Medium",
                        "title": f"Total Borrowings Increased by {round(borrowing_growth, 1)}%",
                        "description": f"Debt portfolio expanded from {debt_py:,.2f} to {debt_cy:,.2f}.",
                        "audit_implication": "Verify loan sanction conditions, end-use verification of funds, and compliance with statutory charge creation (CHG-1)."
                    })

        model.risks = risks
        return risks
