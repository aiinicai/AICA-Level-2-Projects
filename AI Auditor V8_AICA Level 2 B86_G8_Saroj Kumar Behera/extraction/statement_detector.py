"""
AI Auditor V8 - Statement Detector & Pattern Recognition
Identifies statement types (BS, P&L, CFS), period columns, units, and company information from raw tabular data or text.
"""

import re
from typing import List, Dict, Tuple, Optional, Any
from config.constants import (
    STATEMENT_BALANCE_SHEET, STATEMENT_PROFIT_LOSS, STATEMENT_CASH_FLOW, UNITS_MAP
)

class StatementDetector:
    
    @staticmethod
    def detect_statement_type(title_or_content: str) -> str:
        """Determines if text/sheet belongs to Balance Sheet, P&L, or Cash Flow."""
        text = title_or_content.lower()
        
        # Cash Flow Check
        if any(term in text for term in ["cash flow", "cashflow", "flow of cash"]):
            return STATEMENT_CASH_FLOW
            
        # P&L / Income Statement Check
        if any(term in text for term in [
            "profit and loss", "profit & loss", "statement of profit", "income statement",
            "revenue from operations", "p&l", "statement of operations", "statement of comprehensive income"
        ]):
            return STATEMENT_PROFIT_LOSS
            
        # Balance Sheet Check
        if any(term in text for term in [
            "balance sheet", "statement of financial position", "equity and liabilities",
            "assets and liabilities", "sources of funds", "application of funds"
        ]):
            return STATEMENT_BALANCE_SHEET
            
        return STATEMENT_BALANCE_SHEET  # Default assumption

    @staticmethod
    def detect_units(text: str) -> Tuple[str, float]:
        """Detects unit scale (e.g. ₹ in Lakhs, Crores, Millions) and returns label & multiplier."""
        clean = text.lower()
        if "crore" in clean or "cr" in clean.split():
            return "₹ in Crores (1,00,00,000)", 10_000_000.0
        elif "lakh" in clean or "lac" in clean or "lacs" in clean:
            return "₹ in Lakhs (1,00,000)", 100_000.0
        elif "million" in clean or "mn" in clean.split():
            return "₹ in Millions (10,00,000)", 1_000_000.0
        elif "thousand" in clean or "'000" in clean or "k" in clean.split():
            return "₹ in Thousands (000s)", 1_000.0
        elif "$" in clean:
            if "million" in clean:
                return "$ in Millions", 1_000_000.0
            elif "thousand" in clean:
                return "$ in Thousands", 1_000.0
            return "$ (Exact)", 1.0
        return "₹ (Exact)", 1.0

    @staticmethod
    def detect_financial_periods(headers: List[str]) -> List[Tuple[int, str]]:
        """
        Inspects row strings to find columns representing financial years / dates.
        Returns list of (col_index, period_name) ordered with current period first.
        """
        year_pattern = re.compile(r'(?:FY\s*20\d\d[-/]\d\d|FY\s*20\d\d|20\d\d[-/]\d\d|20\d\d|31(?:st)?\s*(?:Mar|March|Dec|December)[a-z]*\s*20\d\d|31[./-]03[./-]20\d\d)', re.IGNORECASE)
        
        detected = []
        for idx, h in enumerate(headers):
            h_str = str(h).strip()
            if not h_str or len(h_str) > 60:
                continue
            h_lower = h_str.lower()
            if any(ign in h_lower for ign in [
                "particulars", "line item", "notes", "note no", "note", "schedule", "description",
                "s.no", "sr.no", "balance sheet as at", "statement of", "for the year ended", "for the period"
            ]):
                continue
            
            match = year_pattern.search(h_str)
            if match:
                # Extract clean period name
                p_name = h_str
                # If there is a FY inside parentheses, prioritize it
                fy_match = re.search(r'(FY\s*\d{4}[-/]\d{2,4})', h_str, re.IGNORECASE)
                if fy_match:
                    p_name = fy_match.group(1).upper()
                detected.append((idx, p_name))
            elif any(word in h_lower for word in ["current year", "previous year", "cy", "py"]):
                detected.append((idx, h_str))
                
        return detected

    @staticmethod
    def clean_numeric_value(val: Any) -> Optional[float]:
        """Converts strings with commas, brackets, dashes to clean float."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
            
        s = str(val).strip().replace(",", "").replace(" ", "").replace("₹", "").replace("$", "").replace("€", "")
        if s == "" or s in ["-", "—", "–", "N/A", "NA", "nil", "Nil", "."]:
            return 0.0
            
        # Handle parentheses for negative numbers e.g. (1,234.50)
        if s.startswith("(") and s.endswith(")"):
            s = "-" + s[1:-1]
            
        try:
            return float(s)
        except ValueError:
            return None
