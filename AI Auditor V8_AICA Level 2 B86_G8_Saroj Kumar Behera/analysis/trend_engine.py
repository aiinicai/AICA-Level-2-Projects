"""
AI Auditor V8 - Trend & Horizontal/Vertical Analysis Engine
Performs YoY percentage changes, common-size vertical statements, and multi-period trajectories.
"""

from typing import Dict, List, Any, Optional
from core.models import FinancialModel, FinancialStatement, LineItem

class TrendEngine:

    @classmethod
    def analyze_trends(cls, model: FinancialModel) -> Dict[str, Any]:
        """
        Generates horizontal and vertical trend analyses across all statements.
        """
        periods = model.periods
        if not periods:
            return {}

        results = {
            "balance_sheet_trends": cls._analyze_statement_trends(model.balance_sheet, is_bs=True),
            "profit_loss_trends": cls._analyze_statement_trends(model.profit_loss, is_bs=False),
            "cash_flow_trends": cls._analyze_statement_trends(model.cash_flow, is_bs=False),
        }
        return results

    @classmethod
    def _analyze_statement_trends(cls, stmt: FinancialStatement, is_bs: bool) -> List[Dict[str, Any]]:
        """Calculates YoY variances and common-size percentages for each line item."""
        periods = stmt.periods
        if not periods:
            return []

        curr_p = periods[0]
        prev_p = periods[1] if len(periods) > 1 else None

        # Determine denominator for Common Size analysis
        base_cy = 0.0
        base_py = 0.0
        
        if is_bs:
            # Base = Total Assets
            for item in stmt.line_items:
                if item.standard_key in ["property_plant_equipment", "inventories", "trade_receivables", "cash_and_bank", "other_current_assets", "non_current_investments"]:
                    base_cy += item.get_value(curr_p, 0.0)
                    if prev_p: base_py += item.get_value(prev_p, 0.0)
        else:
            # Base = Revenue from Operations
            rev_item = stmt.get_item_by_standard_key("revenue_operations")
            if rev_item:
                base_cy = rev_item.get_value(curr_p, 0.0)
                if prev_p: base_py = rev_item.get_value(prev_p, 0.0)

        rows = []
        for item in stmt.line_items:
            val_cy = item.get_value(curr_p, 0.0)
            val_py = item.get_value(prev_p, 0.0) if prev_p else None

            abs_change = (val_cy - val_py) if val_py is not None else None
            pct_change = ((abs_change / abs(val_py)) * 100.0) if (abs_change is not None and val_py and val_py != 0) else None

            # Common size %
            cs_cy = (val_cy / base_cy * 100.0) if base_cy > 0 else 0.0
            cs_py = (val_py / base_py * 100.0) if (base_py > 0 and val_py is not None) else 0.0

            rows.append({
                "particulars": item.original_name,
                "standard_key": item.standard_key,
                "category": item.category,
                "cy_period": curr_p,
                "cy_value": val_cy,
                "py_period": prev_p or "N/A",
                "py_value": val_py,
                "abs_change": abs_change,
                "pct_change": pct_change,
                "common_size_cy": round(cs_cy, 2),
                "common_size_py": round(cs_py, 2) if prev_p else None,
                "trend_direction": "Increase" if (abs_change and abs_change > 0) else ("Decrease" if (abs_change and abs_change < 0) else "No Change")
            })

        return rows
