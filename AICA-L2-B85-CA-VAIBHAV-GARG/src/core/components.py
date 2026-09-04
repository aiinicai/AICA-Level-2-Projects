"""Component dictionary, normalization, and fuzzy auto-mapper with deterministic ambiguity resolution rules."""
from dataclasses import dataclass, field
import re
from typing import Dict, List, Optional, Tuple, Any
from rapidfuzz import fuzz

from src.core.excel_parser import ParsedLineItem, WorkbookParseResult, normalize_whitespace, strip_leading_enumerators


@dataclass
class ComponentDefinition:
    key: str
    name: str
    statement: str  # 'BS', 'PL', 'CF'
    exact_labels: List[str]
    fuzzy_aliases: List[str]
    required_by_ratios: List[int] = field(default_factory=list)


@dataclass
class MappingDecision:
    component_key: str
    source_sheet: str
    source_row: Optional[int]
    source_label: str
    amount_reporting: float
    amount_comparative: float
    confidence: str  # 'High', 'Medium', 'Low', 'Default'
    resolution_rule: str
    is_manual: bool = False
    manual_amount_reporting: Optional[float] = None
    manual_amount_comparative: Optional[float] = None
    remark: str = ""
    candidate_sources: List[Dict[str, Any]] = field(default_factory=list)


COMPONENT_REGISTRY: List[ComponentDefinition] = [
    # Balance Sheet
    ComponentDefinition("share_capital", "Share Capital", "BS", ["Share Capital", "Equity Share Capital"], ["Paid-up Share Capital", "Paid up Share Capital", "Share Capital Subscribed"], [2, 4]),
    ComponentDefinition("preference_share_capital", "Preference Share Capital", "BS", ["Preference Share Capital"], ["Preference Shares", "Preference Share Capital Subscribed"], [4]),
    ComponentDefinition("reserves_surplus", "Reserves and Surplus", "BS", ["Reserves and Surplus", "Reserves & Surplus"], ["Other Equity", "Surplus in Statement of P&L"], [2, 4]),
    ComponentDefinition("long_term_borrowings", "Long-term Borrowings", "BS", ["Long-term Borrowings", "Long term Borrowings"], ["Non-current Borrowings", "Term Loans", "Borrowings (Non-Current)"], [2, 3, 10]),
    ComponentDefinition("deferred_tax_liability", "Deferred Tax Liability (Net)", "BS", ["Deferred Tax Liabilities (Net)", "Deferred Tax Liability (Net)"], ["DTL", "Deferred Tax Liabilities", "Deferred Tax Liability"], [10]),
    ComponentDefinition("other_lt_liabilities_net", "Other Long Term Liabilities (Net)", "BS", ["Other Long Term Liabilities (Net)", "Other Long term Liabilities (Net)"], [], []),
    ComponentDefinition("other_lt_liabilities", "Other Long Term Liabilities", "BS", ["Other Long term Liabilities", "Other Long Term Liabilities", "Other Non-current Liabilities", "Other Non Current Liabilities"], ["Other Long-term Liabilities"], []),
    ComponentDefinition("long_term_provisions", "Long Term Provisions", "BS", ["Long Term Provisions", "Long-term Provisions", "Non-current Provisions", "Non Current Provisions"], ["Provisions (Non-Current)"], []),
    ComponentDefinition("short_term_borrowings", "Short-Term Borrowings", "BS", ["Short-Term Borrowings", "Short Term Borrowings", "Current Borrowings"], ["Cash Credit", "Working Capital Loan", "Short Term Loans"], [1, 2, 3]),
    ComponentDefinition("current_maturities_ltd", "Current Maturities of Long Term Debt", "BS", ["Current Maturities of Long Term Debt", "Current Maturities of Long-Term Debt", "Current maturities of Long Term Borrowings"], ["Current Maturity of Long Term Debt", "Current Maturities of Term Loans"], [2, 3]),
    ComponentDefinition("trade_payables_other", "Trade Payables - Other", "BS", ["Total outstanding dues of creditors other than micro enterprises and small enterprises", "Trade Payables Other", "Total outstanding dues of creditors other than micro and small enterprises"], ["Other than micro and small enterprises", "Other Creditors Dues"], [1, 7]),
    ComponentDefinition("trade_payables_msme", "Trade Payables - MSME", "BS", ["Total outstanding dues of micro enterprises and small enterprises", "Trade Payables MSME", "Total outstanding dues of micro and small enterprises"], ["Micro and small enterprises", "MSME Dues"], [1, 7]),
    ComponentDefinition("trade_payables", "Trade Payables", "BS", ["Trade Payables"], ["Sundry Creditors", "Accounts Payable", "Trade Creditors"], [1, 7]),
    ComponentDefinition("other_current_liabilities", "Other Current Liabilities", "BS", ["Other Current Liabilities", "Other current liabilities"], ["Current Liabilities - Others"], [1]),
    ComponentDefinition("short_term_provisions", "Short-Term Provisions", "BS", ["Short-Term Provisions", "Short Term Provisions", "Current Provisions"], ["Provisions (Current)"], [1]),
    ComponentDefinition("reported_total_eq_liab", "TOTAL EQUITY AND LIABILITIES", "BS", ["TOTAL EQUITY AND LIABILITIES", "Total Equity and Liabilities"], ["Total Liabilities", "Total Equity & Liabilities", "Total Equity and Liabilities (I)"], []),
    ComponentDefinition("ppe", "Property, Plant and Equipment", "BS", ["Property, Plant and Equipment", "Property Plant and Equipment", "Tangible Assets", "Fixed Assets"], ["Property, Plant and Equipment and Intangible Assets", "PPE", "Fixed Assets (Tangible)"], []),
    ComponentDefinition("intangible_assets", "Intangible Assets", "BS", ["Intangible Assets", "Intangible assets"], ["Intangible Fixed Assets", "Intangibles"], [10]),
    ComponentDefinition("cwip", "Capital Work-in-Progress", "BS", ["Capital Work-in-Progress", "Capital Work in Progress", "CWIP"], ["Capital WIP", "Capital work in progress"], []),
    ComponentDefinition("non_current_investments", "Non-Current Investments", "BS", ["Non-Current Investments", "Non Current Investments", "Investments"], ["Long Term Investments", "Non-current Investments"], [11]),
    ComponentDefinition("current_investments", "Current Investments", "BS", ["Current Investments"], ["Short Term Investments", "Marketable Securities", "Current Investments (Quoted)"], [1, 11]),
    ComponentDefinition("deferred_tax_asset", "Deferred Tax Asset (Net)", "BS", ["Deferred Tax Assets (Net)", "Deferred tax assets (Net)", "Deferred Tax Asset (Net)"], ["DTA", "Deferred Tax Asset", "Deferred Tax Assets"], []),
    ComponentDefinition("other_non_current_assets", "Other Non-Current Assets", "BS", ["Other Non-current Assets", "Other non current assets", "Other Non Current Assets", "Long-Term Loans and Advances", "Long Term Loans and Advances"], ["Long-term Loans & Advances", "Other Non Current Assets (Net)"], []),
    ComponentDefinition("inventories", "Inventories", "BS", ["Inventories", "Stock-in-Trade", "Stock in Trade", "Closing Stock"], ["Inventory", "Finished Goods and Raw Materials"], [1, 5]),
    ComponentDefinition("trade_receivables", "Trade Receivables", "BS", ["Trade Receivables"], ["Sundry Debtors", "Accounts Receivable", "Book Debts"], [1, 6]),
    ComponentDefinition("cash_equivalents", "Cash and Cash Equivalents", "BS", ["Cash and Cash Equivalents", "Cash & Cash Equivalents", "Cash and Bank Balances"], ["Cash & Bank Balances", "Bank Balances", "Cash in hand and at bank"], [1]),
    ComponentDefinition("short_term_loans_advances", "Short-Term Loans and Advances", "BS", ["Short-Term Loans and Advances", "Short Term Loans and Advances"], ["Short Term Loans & Advances", "Current Loans and Advances"], [1]),
    ComponentDefinition("other_current_assets", "Other Current Assets", "BS", ["Other Current Assets", "Other current assets"], ["Current Assets - Others"], [1]),
    ComponentDefinition("reported_total_assets", "TOTAL ASSETS", "BS", ["TOTAL ASSETS", "Total Assets"], ["Total Assets (II)", "Grand Total Assets"], []),

    # Profit and Loss
    ComponentDefinition("revenue_gross", "Revenue from Operations (Gross)", "PL", ["Revenue from Operations (Gross)", "Gross Revenue", "Gross Turnover"], ["Turnover", "Gross Sales"], []),
    ComponentDefinition("gst", "Less: GST / Excise", "PL", ["Less : GST", "Less: GST", "Less GST", "GST"], ["Excise Duty", "Less: Excise Duty", "Less Excise Duty", "Service Tax"], []),
    ComponentDefinition("revenue_net", "Revenue from Operations (Net)", "PL", ["Revenue from Operations (Net)", "Revenue from Operations", "Net Sales", "Net Revenue"], ["Revenue from operations", "Net Turnover"], [6, 8, 9]),
    ComponentDefinition("other_income", "Other Income", "PL", ["Other Income", "Other income"], ["Other operating revenue", "Other Operating Income", "Non-Operating Income"], []),
    ComponentDefinition("total_income", "Total Income", "PL", ["Total Income (I + II)", "Total Revenue (I + II)", "Total Income", "Total Revenue"], ["Total Revenue from Operations and Other Income"], []),
    ComponentDefinition("cost_of_materials", "Cost of Materials Consumed", "PL", ["Cost of Materials Consumed", "Cost of materials consumed", "Raw Material Consumed"], ["Raw Materials Consumed", "Materials Consumed", "Raw materials consumed"], [5, 7]),
    ComponentDefinition("purchases_stock_in_trade", "Purchases of Stock-in-Trade", "PL", ["Purchases of Stock-in-Trade", "Purchases of Stock in Trade", "Purchase of Stock-in-Trade"], ["Purchase of traded goods", "Purchases of Traded Goods"], [5, 7]),
    ComponentDefinition("changes_in_inventories", "Changes in Inventories", "PL", ["Changes in Inventories of finished goods, Work-in-progress and Stock-in-Trade", "Changes in Inventories of finished goods Work-in-progress and Stock-in-Trade", "Changes in Inventories of finished goods , Work-in-progress and Stock-in-Trade", "Changes in Inventories"], ["Increase / Decrease in Stocks", "Change in Inventory", "Changes in Inventories of WIP and finished goods"], [5]),
    ComponentDefinition("employee_benefits", "Employee Benefit Expenses", "PL", ["Employee Benefit Expenses", "Employee Benefits Expense", "Employee Benefit Expense"], ["Salaries and Wages", "Staff Costs", "Employee Costs", "Personnel Expenses"], []),
    ComponentDefinition("finance_costs", "Finance Costs", "PL", ["Finance Costs", "Finance Cost", "Interest Expense"], ["Interest and Finance Charges", "Finance charges", "Interest Expenses"], [3, 10]),
    ComponentDefinition("depreciation", "Depreciation and Amortisation Expenses", "PL", ["Depreciation and Amortisation Expenses", "Depreciation and Amortization Expenses", "Depreciation"], ["Depreciation & Amortisation", "Depreciation and Amortisation"], [3]),
    ComponentDefinition("other_expenses", "Other Expenses", "PL", ["Other Expenses", "Other expenses"], ["Administrative and General Expenses", "Manufacturing and Other Expenses"], []),
    ComponentDefinition("total_expenses", "Total Expenses", "PL", ["Total Expenses", "Total expenses"], ["Total Expenses (IV)", "Expenses"], []),
    ComponentDefinition("pbt", "Profit/(Loss) Before Tax", "PL", ["Profit/(Loss) Before Tax", "Profit / (Loss) Before Tax", "Profit Before Tax"], ["PBT", "Profit / (Loss) before tax", "Profit/(Loss) before exceptional items and tax"], [10]),
    ComponentDefinition("current_tax", "Current Tax", "PL", ["Current tax", "Current Tax", "Provision for Tax"], ["Current Tax Expense", "Income Tax"], []),
    ComponentDefinition("deferred_tax", "Deferred Tax (P&L)", "PL", ["Deferred tax", "Deferred Tax"], ["Deferred Tax Charge / (Credit)", "Deferred Tax Expense"], []),
    ComponentDefinition("tax_earlier_years", "Tax Adjustment Earlier Years", "PL", ["Tax Adjustment Earlier Years", "Tax of Earlier Years", "Tax for earlier years", "Adjustment Earlier Years"], ["Tax Adjustments for Prior Periods", "Short / (Excess) Provision for Tax of earlier years"], []),
    ComponentDefinition("pat", "Profit/(Loss) for the Year", "PL", ["Profit/(Loss) for the Year", "Profit / (Loss) for the Year", "Profit After Tax", "PAT"], ["Profit for the year", "Net Profit for the period", "Profit / (Loss) After Tax"], [3, 4, 9]),

    # Cash Flow Statement
    ComponentDefinition("cf_proceeds_lt_borrowings", "CF: Proceeds from Long-term Borrowings", "CF", ["Proceeds from long-term borrowings", "Proceeds from long term borrowings"], ["Proceeds from term loans", "Inflow from long-term borrowings", "Drawdown of term loans"], [3]),
    ComponentDefinition("cf_repayment_lt_borrowings", "CF: Repayment of Long-term Borrowings", "CF", ["Repayment of long-term borrowings", "Repayment of long term borrowings"], ["Repayment of term loans", "Repayments of term loans", "Principal repayment of long term debt"], [3]),
    ComponentDefinition("cf_repayment_st_borrowings", "CF: Repayments of Short Term Borrowings", "CF", ["Repayments of short term borrowings", "Repayment of short term borrowings", "Repayments of short-term borrowings", "Repayment of short-term borrowings"], ["Repayment of working capital limit"], [3]),
    ComponentDefinition("cf_movement_st_borrowings", "CF: Increase/(Decrease) in Short Term Borrowings", "CF", ["Increase/(Decrease) in Short Term Borrowings", "Increase / (Decrease) in Short Term Borrowings"], ["Movement in short term borrowings", "Net movement in working capital loans"], []),
    ComponentDefinition("cf_increase_share_capital", "CF: Increase in Share Capital", "CF", ["Increase in Share capital", "Increase in Share Capital"], ["Proceeds from issue of share capital", "Proceeds from issue of shares", "Proceeds from equity issue"], []),
    ComponentDefinition("cf_interest_paid", "CF: Interest Paid", "CF", ["Interest paid", "Interest Paid"], ["Finance costs paid", "Finance cost paid", "Interest and finance charges paid"], [3]),
    ComponentDefinition("cf_interest_income", "CF: Interest Income", "CF", ["Interest income", "Interest income ", "Interest Income"], ["Interest received", "Interest Income received"], []),
    ComponentDefinition("cf_depreciation", "CF: Depreciation", "CF", ["Depreciation"], ["Depreciation and amortisation", "Depreciation add-back"], []),
    ComponentDefinition("cf_misc_written_off", "CF: Misc Expenses Written Off", "CF", ["Misc expenses w/off", "Misc Expenses w/off", "Misc expenses written off"], ["Miscellaneous expenditure written off", "Preliminary expenses written off", "Amortisation of share issue expenses"], [3]),
    ComponentDefinition("cf_purchase_fixed_assets", "CF: Purchase of Fixed Assets", "CF", ["Purchases of fixed assets", "Purchase of fixed assets"], ["Acquisition of PPE", "Capital expenditure", "Purchase of Property, Plant and Equipment"], []),
    ComponentDefinition("cf_dividend_income", "CF: Dividend Income", "CF", ["Dividend income", "Dividend received"], ["Dividend Income received"], []),
    ComponentDefinition("cf_profit_sale_investments", "CF: Profit on Sale of Investments", "CF", ["Profit on sale of investments", "Profit on Sale of Investments"], ["Gain on sale of investments"], []),
    ComponentDefinition("cf_margin_money", "CF: Margin Money Movement", "CF", ["In margin money with maturity less than 12 months"], ["Margin money", "Fixed deposits under lien"], []),
]

COMPONENT_MAP: Dict[str, ComponentDefinition] = {c.key: c for c in COMPONENT_REGISTRY}


def clean_label_for_matching(text: str) -> str:
    if not text:
        return ""
    text = normalize_whitespace(text).lower()
    text = strip_leading_enumerators(text).lower()
    text = text.replace("&", "and")
    text = text.replace("'", "").replace('"', "").replace("’", "").replace("`", "")
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s*\(refer\s*note\s*[\d\w\.]+\)\s*$", "", text, flags=re.IGNORECASE)
    return normalize_whitespace(text).strip()


def find_best_component_for_line(
    line: ParsedLineItem
) -> Optional[Tuple[ComponentDefinition, int, str]]:
    cleaned = clean_label_for_matching(line.normalised_label)
    if not cleaned:
        return None
        
    # Phase 1: Exact label matches
    for comp in COMPONENT_REGISTRY:
        if comp.statement != line.sheet:
            continue
        for exact in comp.exact_labels:
            if cleaned == clean_label_for_matching(exact):
                return (comp, 100, "Exact")
                
    # Phase 2: Exact alias matches
    for comp in COMPONENT_REGISTRY:
        if comp.statement != line.sheet:
            continue
        for alias in comp.fuzzy_aliases:
            if cleaned == clean_label_for_matching(alias):
                return (comp, 95, "Alias")
                
    # Phase 3: RapidFuzz token_set_ratio
    best_comp = None
    best_score = 0
    best_type = ""
    
    for comp in COMPONENT_REGISTRY:
        if comp.statement != line.sheet:
            continue
        for cand in comp.exact_labels + comp.fuzzy_aliases:
            score = fuzz.token_set_ratio(cleaned, clean_label_for_matching(cand))
            if score > best_score:
                best_score = score
                best_comp = comp
                best_type = "Fuzzy High" if score >= 85 else "Fuzzy Low"
                
    if best_score >= 70 and best_comp:
        return (best_comp, int(best_score), best_type)
        
    return None


def map_workbook_components(
    parse_result: WorkbookParseResult,
    year_prefix: str = "CY"
) -> Tuple[Dict[str, MappingDecision], List[str]]:
    audit_events: List[str] = []
    
    candidates_by_comp: Dict[str, List[Tuple[ParsedLineItem, int, str]]] = {
        c.key: [] for c in COMPONENT_REGISTRY
    }
    
    for item in parse_result.line_items:
        if not item.normalised_label and not item.raw_label:
            continue
        match_res = find_best_component_for_line(item)
        if match_res:
            comp, score, mtype = match_res
            candidates_by_comp[comp.key].append((item, score, mtype))
            
    # Also handle specific multi-match resolution (e.g. other_lt_liabilities vs other_lt_liabilities_net)
    for item in parse_result.line_items:
        cl = clean_label_for_matching(item.normalised_label)
        if cl in ("other long term liabilities", "other long-term liabilities", "other non-current liabilities", "other non current liabilities"):
            if not any(c[0].row_no == item.row_no for c in candidates_by_comp["other_lt_liabilities"]):
                candidates_by_comp["other_lt_liabilities"].append((item, 100, "Exact"))
                
    mappings: Dict[str, MappingDecision] = {}
    
    for comp in COMPONENT_REGISTRY:
        candidates = candidates_by_comp[comp.key]
        
        if not candidates:
            mappings[comp.key] = MappingDecision(
                component_key=comp.key,
                source_sheet=comp.statement,
                source_row=None,
                source_label="[Not present in statement]",
                amount_reporting=0.0,
                amount_comparative=0.0,
                confidence="Default",
                resolution_rule="Rule 3 (Default: Not present)",
                remark=f"Component {comp.key} not present in {year_prefix} source; treated as nil."
            )
            continue
            
        cand_sources = [
            {"row": c[0].row_no, "label": c[0].raw_label, "rep": c[0].amount_reporting, "comp": c[0].amount_comparative}
            for c in candidates
        ]
        
        max_score = max(c[1] for c in candidates)
        top_candidates = [c for c in candidates if c[1] == max_score]
        
        if len(top_candidates) == 1:
            item, score, mtype = top_candidates[0]
            rep_amt = item.amount_reporting if item.amount_reporting is not None else 0.0
            comp_amt = item.amount_comparative if item.amount_comparative is not None else 0.0
            
            if score < 85:
                confidence = "Low"
                rule_name = "Rule 4 (Low confidence match)"
                remark = f"Low confidence ({score}%) match for '{item.raw_label}'."
                audit_events.append(f"[{year_prefix}] Rule 4 applied for {comp.key}: matched '{item.raw_label}' at row {item.row_no} with score {score}%.")
            else:
                confidence = "High" if score >= 90 else "Medium"
                rule_name = f"Exact/Alias Match ({mtype})"
                remark = ""
                
            mappings[comp.key] = MappingDecision(
                component_key=comp.key,
                source_sheet=item.sheet,
                source_row=item.row_no,
                source_label=item.raw_label,
                amount_reporting=rep_amt,
                amount_comparative=comp_amt,
                confidence=confidence,
                resolution_rule=rule_name,
                remark=remark,
                candidate_sources=cand_sources
            )
        else:
            non_zero_candidates = [
                c for c in top_candidates
                if (c[0].amount_reporting or 0.0) != 0.0 or (c[0].amount_comparative or 0.0) != 0.0
            ]
            
            if len(non_zero_candidates) == 1:
                chosen, score, mtype = non_zero_candidates[0]
                rep_amt = chosen.amount_reporting if chosen.amount_reporting is not None else 0.0
                comp_amt = chosen.amount_comparative if chosen.amount_comparative is not None else 0.0
                mappings[comp.key] = MappingDecision(
                    component_key=comp.key,
                    source_sheet=chosen.sheet,
                    source_row=chosen.row_no,
                    source_label=chosen.raw_label,
                    amount_reporting=rep_amt,
                    amount_comparative=comp_amt,
                    confidence="High",
                    resolution_rule="Rule 1 (Duplicate: Non-zero selected)",
                    remark=f"Selected row {chosen.row_no} ('{chosen.raw_label}') carrying non-zero value among {len(top_candidates)} matches.",
                    candidate_sources=cand_sources
                )
                audit_events.append(
                    f"[{year_prefix}] Rule 1 applied for {comp.key}: selected row {chosen.row_no} ('{chosen.raw_label}') "
                    f"carrying {rep_amt} over {len(top_candidates) - 1} nil/zero candidates."
                )
            elif len(non_zero_candidates) > 1:
                total_rep = sum((c[0].amount_reporting or 0.0) for c in non_zero_candidates)
                total_comp = sum((c[0].amount_comparative or 0.0) for c in non_zero_candidates)
                rows_str = ", ".join(str(c[0].row_no) for c in non_zero_candidates)
                labels_str = " + ".join(c[0].raw_label for c in non_zero_candidates)
                mappings[comp.key] = MappingDecision(
                    component_key=comp.key,
                    source_sheet=non_zero_candidates[0][0].sheet,
                    source_row=non_zero_candidates[0][0].row_no,
                    source_label=labels_str,
                    amount_reporting=total_rep,
                    amount_comparative=total_comp,
                    confidence="Medium",
                    resolution_rule="Rule 1 (Duplicate: Summed)",
                    remark=f"Summed {len(non_zero_candidates)} non-zero rows ({rows_str}).",
                    candidate_sources=cand_sources
                )
                audit_events.append(
                    f"[{year_prefix}] Rule 1 applied for {comp.key}: summed rows ({rows_str}) with total reporting amount {total_rep}."
                )
            else:
                chosen, score, mtype = top_candidates[0]
                rep_amt = chosen.amount_reporting if chosen.amount_reporting is not None else 0.0
                comp_amt = chosen.amount_comparative if chosen.amount_comparative is not None else 0.0
                mappings[comp.key] = MappingDecision(
                    component_key=comp.key,
                    source_sheet=chosen.sheet,
                    source_row=chosen.row_no,
                    source_label=chosen.raw_label,
                    amount_reporting=rep_amt,
                    amount_comparative=comp_amt,
                    confidence="High",
                    resolution_rule="Rule 1 (Duplicate: First selected)",
                    remark=f"Multiple zero candidates; selected first row {chosen.row_no}.",
                    candidate_sources=cand_sources
                )
                
    return mappings, audit_events
