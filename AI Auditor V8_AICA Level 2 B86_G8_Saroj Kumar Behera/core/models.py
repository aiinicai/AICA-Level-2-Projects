"""
AI Auditor V8 - Core Financial Data Models
Structured data representations for Companies, Line Items, Financial Statements, and Financial Models.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import datetime

@dataclass
class CompanyInfo:
    name: str = "ABC Enterprises Ltd"
    name_set: bool = False
    identifier: str = ""  # CIN / PAN / Registration No
    financial_year_current: str = "FY 2023-24"
    financial_year_previous: str = "FY 2022-23"
    currency_symbol: str = "₹"
    unit_label: str = "₹ in Lakhs (1,00,000)"
    unit_multiplier: float = 100_000.0
    industry: str = "Manufacturing & Trading"
    engagement_type: str = "Statutory / Internal Audit & Credit Appraisal"
    auditor_name: str = "Chartered Accountant / Financial Analyst"
    analysis_date: str = field(default_factory=lambda: datetime.date.today().strftime("%d-%b-%Y"))
    source_file: str = ""

@dataclass
class LineItem:
    original_name: str
    standard_key: Optional[str] = None
    statement_type: str = "Balance Sheet"
    category: str = "Unclassified"
    values: Dict[str, float] = field(default_factory=dict)  # {"FY 2023-24": 150.0, "FY 2022-23": 120.0}
    is_subtotal: bool = False
    is_credit: bool = False  # For BS
    is_income: bool = False  # For P&L
    confidence_score: float = 1.0  # 0.0 - 1.0
    user_overridden: bool = False
    notes: str = ""

    def get_value(self, period: str, default: float = 0.0) -> float:
        return self.values.get(period, default)

    def set_value(self, period: str, val: float):
        self.values[period] = float(val)

@dataclass
class FinancialStatement:
    statement_type: str  # "Balance Sheet", "Profit and Loss", "Cash Flow Statement"
    periods: List[str] = field(default_factory=list)  # ["FY 2023-24", "FY 2022-23"]
    line_items: List[LineItem] = field(default_factory=list)

    def get_item_by_standard_key(self, standard_key: str) -> Optional[LineItem]:
        for item in self.line_items:
            if item.standard_key == standard_key:
                return item
        return None

    def get_value_by_key(self, standard_key: str, period: str, default: float = 0.0) -> float:
        item = self.get_item_by_standard_key(standard_key)
        if item:
            return item.get_value(period, default)
        return default

    def add_or_update_line_item(self, line_item: LineItem):
        for idx, existing in enumerate(self.line_items):
            if existing.original_name.strip().lower() == line_item.original_name.strip().lower():
                self.line_items[idx] = line_item
                return
        self.line_items.append(line_item)

@dataclass
class FinancialModel:
    company_info: CompanyInfo = field(default_factory=CompanyInfo)
    balance_sheet: FinancialStatement = field(default_factory=lambda: FinancialStatement("Balance Sheet"))
    profit_loss: FinancialStatement = field(default_factory=lambda: FinancialStatement("Profit and Loss"))
    cash_flow: FinancialStatement = field(default_factory=lambda: FinancialStatement("Cash Flow Statement"))
    other_schedules: Dict[str, FinancialStatement] = field(default_factory=dict)
    
    # Store analytical outputs
    ratios: Dict[str, Any] = field(default_factory=dict)
    variations: List[Dict[str, Any]] = field(default_factory=list)
    risks: List[Dict[str, Any]] = field(default_factory=list)
    audit_requirements: List[Dict[str, Any]] = field(default_factory=list)
    data_limitations: List[str] = field(default_factory=list)

    @property
    def periods(self) -> List[str]:
        # Return merged ordered list of periods
        seen = []
        for stmt in [self.balance_sheet, self.profit_loss, self.cash_flow]:
            for p in stmt.periods:
                if p not in seen:
                    seen.append(p)
        if not seen:
            return [self.company_info.financial_year_current, self.company_info.financial_year_previous]
        return seen

    def get_statement(self, statement_type: str) -> FinancialStatement:
        if "balance" in statement_type.lower():
            return self.balance_sheet
        elif "profit" in statement_type.lower() or "income" in statement_type.lower() or "loss" in statement_type.lower() or "p&l" in statement_type.lower():
            return self.profit_loss
        elif "cash" in statement_type.lower():
            return self.cash_flow
        else:
            if statement_type not in self.other_schedules:
                self.other_schedules[statement_type] = FinancialStatement(statement_type)
            return self.other_schedules[statement_type]
