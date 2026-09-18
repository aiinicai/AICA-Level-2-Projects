"""
AI Auditor V8 - Significant Variation Analysis Engine
Identifies line items with movements >= threshold (default 5%), factoring in materiality and audit intelligence.
"""

from typing import Dict, List, Any, Optional
from core.models import FinancialModel, FinancialStatement, LineItem
from analysis.audit_rules import AuditRulesEngine

class VarianceEngine:

    @classmethod
    def analyze_variations(cls, model: FinancialModel, threshold_pct: float = 5.0, materiality_min: float = 0.0) -> List[Dict[str, Any]]:
        """
        Scans all statements for significant variations exceeding the threshold.
        Returns detailed list of variance records with Possible Reasons and Audit Requirements.
        """
        periods = model.periods
        if len(periods) < 2:
            model.data_limitations.append("Only single period data available; comparative variation analysis requires at least two periods.")
            return []

        curr_p = periods[0]
        prev_p = periods[1]

        variations = []
        
        # Scan Balance Sheet, Profit & Loss, and Cash Flow
        for stmt_name, stmt in [
            ("Balance Sheet", model.balance_sheet),
            ("Profit & Loss", model.profit_loss),
            ("Cash Flow Statement", model.cash_flow)
        ]:
            for item in stmt.line_items:
                val_cy = item.get_value(curr_p, 0.0)
                val_py = item.get_value(prev_p, 0.0)

                if val_py == 0.0 and val_cy == 0.0:
                    continue

                abs_diff = val_cy - val_py
                
                # Calculate percentage change
                if val_py != 0.0:
                    pct_diff = (abs_diff / abs(val_py)) * 100.0
                else:
                    # New line item introduced in current year
                    pct_diff = 100.0 if val_cy > 0 else -100.0

                # Check if exceeds threshold and materiality
                if abs(pct_diff) >= threshold_pct and abs(abs_diff) >= materiality_min:
                    is_inc = (abs_diff > 0)
                    rules = AuditRulesEngine.get_rules_for_item(item.standard_key, is_inc)
                    
                    var_record = {
                        "statement": stmt_name,
                        "particulars": item.original_name,
                        "standard_key": item.standard_key,
                        "category": item.category,
                        "previous_period_label": prev_p,
                        "previous_period_amount": val_py,
                        "current_period_label": curr_p,
                        "current_period_amount": val_cy,
                        "absolute_change": round(abs_diff, 2),
                        "percentage_change": round(pct_diff, 2),
                        "direction": "Increase" if is_inc else "Decrease",
                        "possible_reasons": rules["possible_reasons"],
                        "audit_verification": rules["audit_verification"],
                        "risk_level": rules["risk_level"],
                        "risk_note": rules["risk_note"]
                    }
                    variations.append(var_record)

        # Sort by largest absolute variation
        variations.sort(key=lambda x: abs(x["absolute_change"]), reverse=True)
        model.variations = variations
        return variations
