"""
AI Auditor V8 - Excel Data Extractor
Robust multi-sheet and single-sheet Excel parser using openpyxl & pandas.
"""

import os
import openpyxl
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from core.models import FinancialModel, FinancialStatement, LineItem, CompanyInfo
from extraction.statement_detector import StatementDetector
from config.constants import (
    STATEMENT_BALANCE_SHEET, STATEMENT_PROFIT_LOSS, STATEMENT_CASH_FLOW
)

class ExcelExtractor:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)

    def extract(self) -> FinancialModel:
        """Parses the Excel file and returns a populated FinancialModel."""
        model = FinancialModel()
        model.company_info.source_file = self.filename
        
        # Load workbook
        wb = openpyxl.load_workbook(self.filepath, data_only=True)
        sheet_names = wb.sheetnames
        
        # 1. First scan for company header info across top rows of first sheet
        first_sheet = wb[sheet_names[0]]
        self._extract_header_metadata(first_sheet, model.company_info)
        
        # 2. Check if workbook has segregated sheets (e.g. "BS", "PL", "CF") or single combined sheet
        if len(sheet_names) == 1:
            self._parse_single_combined_sheet(first_sheet, model)
        else:
            for name in sheet_names:
                sheet = wb[name]
                detected_type = StatementDetector.detect_statement_type(name)
                self._parse_sheet_into_statement(sheet, model, detected_type)
                
        # Fill in default periods if missing
        if not model.balance_sheet.periods and model.profit_loss.periods:
            model.balance_sheet.periods = list(model.profit_loss.periods)
        elif not model.profit_loss.periods and model.balance_sheet.periods:
            model.profit_loss.periods = list(model.balance_sheet.periods)
            
        return model

    def _extract_header_metadata(self, sheet, company_info: CompanyInfo):
        """Scans the first 10 rows for company name, unit, and financial years."""
        full_text = []
        for r in range(1, min(12, sheet.max_row + 1)):
            row_vals = [str(cell.value) for cell in sheet[r] if cell.value is not None]
            full_text.extend(row_vals)
            # Check company name heuristic (first prominent non-empty row)
            if r <= 3 and row_vals and not company_info.name_set:
                candidate = row_vals[0].strip()
                if len(candidate) > 3 and not any(kw in candidate.lower() for kw in ["balance sheet", "profit", "statement", "schedule", "period"]):
                    company_info.name = candidate
                    company_info.name_set = True
                    
        combined_header_str = " ".join(full_text)
        unit_label, multiplier = StatementDetector.detect_units(combined_header_str)
        company_info.unit_label = unit_label
        company_info.unit_multiplier = multiplier

    def _parse_sheet_into_statement(self, sheet, model: FinancialModel, statement_type: str):
        """Parses a specific worksheet into the specified statement."""
        stmt = model.get_statement(statement_type)
        
        # Convert sheet to rows of values
        rows_data = []
        for row in sheet.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                rows_data.append([c for c in row])
                
        if not rows_data:
            return

        # Find header row
        header_row_idx, period_cols = self._find_header_and_periods(rows_data)
        if not period_cols:
            # Fallback default: assume col 1 is CY, col 2 is PY
            period_cols = [(1, "Current Period"), (2, "Previous Period")]
            
        for _, p_name in period_cols:
            if p_name not in stmt.periods:
                stmt.periods.append(p_name)
                
        # Parse line items starting after header_row_idx
        for r_idx in range(header_row_idx + 1, len(rows_data)):
            row = rows_data[r_idx]
            if not row:
                continue
                
            # Find particulars (first non-empty text column)
            particulars = None
            part_col = 0
            for c_idx, val in enumerate(row):
                if val is not None and isinstance(val, str) and len(val.strip()) > 1:
                    # check if not a purely numeric string
                    if StatementDetector.clean_numeric_value(val) is None:
                        particulars = val.strip()
                        part_col = c_idx
                        break
                        
            if not particulars:
                continue
                
            # Extract period values
            val_dict = {}
            for col_idx, p_name in period_cols:
                if col_idx < len(row):
                    num = StatementDetector.clean_numeric_value(row[col_idx])
                    if num is not None:
                        val_dict[p_name] = num
                        
            if val_dict:
                item = LineItem(
                    original_name=particulars,
                    statement_type=statement_type,
                    values=val_dict
                )
                stmt.add_or_update_line_item(item)

    def _parse_single_combined_sheet(self, sheet, model: FinancialModel):
        """Handles single-sheet Excel files containing BS, P&L, and Cash Flow stacked vertically."""
        rows_data = []
        for row in sheet.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                rows_data.append([c for c in row])
                
        if not rows_data:
            return
            
        current_statement_type = STATEMENT_BALANCE_SHEET
        header_row_idx, period_cols = self._find_header_and_periods(rows_data)
        
        if not period_cols:
            period_cols = [(1, "FY 2023-24"), (2, "FY 2022-23")]
            
        for _, p_name in period_cols:
            for s in [model.balance_sheet, model.profit_loss, model.cash_flow]:
                if p_name not in s.periods:
                    s.periods.append(p_name)
                    
        for r_idx in range(len(rows_data)):
            row = rows_data[r_idx]
            if not row:
                continue
                
            # Check for statement section transition headers
            row_str = " ".join([str(c) for c in row if c is not None]).strip().lower()
            if "profit and loss" in row_str or "statement of profit" in row_str or "income statement" in row_str or "part ii - profit" in row_str:
                current_statement_type = STATEMENT_PROFIT_LOSS
                continue
            elif "cash flow" in row_str or "flow of cash" in row_str:
                current_statement_type = STATEMENT_CASH_FLOW
                continue
            elif "balance sheet" in row_str or "part i - balance" in row_str:
                current_statement_type = STATEMENT_BALANCE_SHEET
                continue
                
            # If line is header itself, re-detect period cols if necessary
            detected_periods = StatementDetector.detect_financial_periods([str(c or '') for c in row])
            if len(detected_periods) >= 2:
                period_cols = detected_periods
                continue
                
            # Particulars & numbers
            particulars = None
            for c_idx, val in enumerate(row):
                if val is not None and isinstance(val, str) and len(val.strip()) > 1:
                    if StatementDetector.clean_numeric_value(val) is None:
                        particulars = val.strip()
                        break
                        
            if not particulars:
                continue
                
            val_dict = {}
            for col_idx, p_name in period_cols:
                if col_idx < len(row):
                    num = StatementDetector.clean_numeric_value(row[col_idx])
                    if num is not None:
                        val_dict[p_name] = num
                        
            if val_dict:
                stmt = model.get_statement(current_statement_type)
                item = LineItem(
                    original_name=particulars,
                    statement_type=current_statement_type,
                    values=val_dict
                )
                stmt.add_or_update_line_item(item)

    def _find_header_and_periods(self, rows_data: List[List[Any]]) -> Tuple[int, List[Tuple[int, str]]]:
        """Finds row containing period headers."""
        best_row_idx = 0
        best_periods = []
        
        for r_idx in range(min(15, len(rows_data))):
            row_str = [str(c or '') for c in rows_data[r_idx]]
            periods = StatementDetector.detect_financial_periods(row_str)
            if len(periods) >= 2:
                return r_idx, periods
            elif len(periods) == 1 and not best_periods:
                best_row_idx = r_idx
                best_periods = periods
                
        return best_row_idx, best_periods
