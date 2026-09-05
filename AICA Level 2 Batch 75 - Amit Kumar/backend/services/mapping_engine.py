import re
from sqlalchemy.orm import Session
from models import MappingRule, TrialBalanceLine

# CRITICAL: Ordered by priority (High-precision specific rules FIRST, general rules SECOND)
DEFAULT_RULES = [
    # 1. High Precision Specific Expenses / Income / CWIP (Rule 1-8 of ICAI Audit Standards)
    {"pattern": r"depreciation|amortisation|amortization", "target_classification": "Depreciation and Amortisation Expense", "target_statement": "Profit & Loss", "note_number": "7.4", "current_non_current": "P&L Expense"},
    {"pattern": r"cwip|capital work in progress|work in progress - capital|capital work-in-progress", "target_classification": "Capital Work-in-Progress", "target_statement": "Balance Sheet", "note_number": "4.2", "current_non_current": "Non-Current"},
    {"pattern": r"interest income|fd interest|bank fd income|dividend income|profit on sale|gain on sale|scrap sale|discount received", "target_classification": "Other Income", "target_statement": "Profit & Loss", "note_number": "6.2", "current_non_current": "P&L Income"},
    {"pattern": r"interest|finance cost|interest on loan|interest expense|bank charges|borrowing cost|interest on term loan|finance charge", "target_classification": "Finance Costs", "target_statement": "Profit & Loss", "note_number": "7.3", "current_non_current": "P&L Expense"},
    {"pattern": r"provision for income tax|tax provision|current tax expense|income tax expense|deferred tax expense|tax expense", "target_classification": "Tax Expense", "target_statement": "Profit & Loss", "note_number": "7.6", "current_non_current": "P&L Tax"},
    {"pattern": r"raw material consumed|material consumed|cost of materials|purchases|direct material|purchase of raw material", "target_classification": "Cost of Materials Consumed", "target_statement": "Profit & Loss", "note_number": "7.1", "current_non_current": "P&L Expense"},
    {"pattern": r"salary|salaries|wages|bonus|pf contribution|staff welfare|remuneration", "target_classification": "Employee Benefit Expenses", "target_statement": "Profit & Loss", "note_number": "7.2", "current_non_current": "P&L Expense"},
    {"pattern": r"gst payable|statutory dues|tds payable|pf payable|esic payable|provident fund payable|outstanding expense", "target_classification": "Other Current Liabilities", "target_statement": "Balance Sheet", "note_number": "3.3", "current_non_current": "Current"},
    {"pattern": r"cash credit|overdraft|working capital loan|short term loan", "target_classification": "Short-term Borrowings", "target_statement": "Balance Sheet", "note_number": "3.1", "current_non_current": "Current"},
    {"pattern": r"term loan|long term loan|secured loan|unsecured loan|debentures|bonds", "target_classification": "Long-term Borrowings", "target_statement": "Balance Sheet", "note_number": "2.1", "current_non_current": "Non-Current"},


    # 2. General Balance Sheet Rules
    {"pattern": r"share capital|equity capital|paid up capital", "target_classification": "Share Capital", "target_statement": "Balance Sheet", "note_number": "1.1", "current_non_current": "Shareholders' Funds"},
    {"pattern": r"reserve|surplus|retained earnings|general reserve|security premium|p&l balance", "target_classification": "Reserves and Surplus", "target_statement": "Balance Sheet", "note_number": "1.2", "current_non_current": "Shareholders' Funds"},
    {"pattern": r"creditor|trade payable|vendor payable|payable for goods", "target_classification": "Trade Payables", "target_statement": "Balance Sheet", "note_number": "3.2", "current_non_current": "Current"},
    {"pattern": r"debtor|trade receivable|customer receivable|receivable for goods", "target_classification": "Trade Receivables", "target_statement": "Balance Sheet", "note_number": "5.2", "current_non_current": "Current"},
    {"pattern": r"stock|inventory|finished goods|work in progress inventory", "target_classification": "Inventories", "target_statement": "Balance Sheet", "note_number": "5.1", "current_non_current": "Current"},
    {"pattern": r"bank|cash|petty cash|fixed deposit|cheque in hand", "target_classification": "Cash and Bank Balances", "target_statement": "Balance Sheet", "note_number": "5.3", "current_non_current": "Current"},
    {"pattern": r"plant|machinery|furniture|equipment|building|vehicle|computer|office equipment|land", "target_classification": "Property, Plant and Equipment", "target_statement": "Balance Sheet", "note_number": "4.1", "current_non_current": "Non-Current"},
    {"pattern": r"investment|mutual fund|shares in subsidiary", "target_classification": "Non-current Investments", "target_statement": "Balance Sheet", "note_number": "4.3", "current_non_current": "Non-Current"},

    # 3. P&L Expenses Rules
    {"pattern": r"sales|revenue|turnover|operating income|income from operations", "target_classification": "Revenue from Operations", "target_statement": "Profit & Loss", "note_number": "6.1", "current_non_current": "P&L Income"},
    {"pattern": r"rent|rates|taxes|electricity|power|travel|audit fee|legal|office expense|miscellaneous expense|advertisement|freight|repair|maintenance|general expense|insurance|telephone|postage", "target_classification": "Other Expenses", "target_statement": "Profit & Loss", "note_number": "7.5", "current_non_current": "P&L Expense"}
]

def init_default_rules(db: Session):
    db.query(MappingRule).delete()
    for r in DEFAULT_RULES:
        db_rule = MappingRule(**r)
        db.add(db_rule)
    db.commit()

def suggest_mapping_for_line(ledger_name: str, original_group: str, db: Session) -> dict:
    init_default_rules(db)
    rules = db.query(MappingRule).all()
    
    clean_ledger = ledger_name.lower().strip()
    clean_group = original_group.lower().strip() if original_group else ""
    combined = f"{clean_ledger} {clean_group}"

    for rule in rules:
        if re.search(rule.pattern, combined, re.IGNORECASE):
            return {
                "classification": rule.target_classification,
                "final_classification": rule.target_classification,
                "statement": rule.target_statement,
                "financial_statement": rule.target_statement,
                "note_number": rule.note_number,
                "current_non_current": rule.current_non_current
            }
    
    # Fallback to Other Expenses
    return {
        "classification": "Other Expenses",
        "final_classification": "Other Expenses",
        "statement": "Profit & Loss",
        "financial_statement": "Profit & Loss",
        "note_number": "7.5",
        "current_non_current": "P&L Expense"
    }

def apply_auto_mapping(client_id: int, db: Session):
    init_default_rules(db)
    lines = db.query(TrialBalanceLine).filter(TrialBalanceLine.client_id == client_id).all()
    for line in lines:
        if not line.user_override or not line.final_classification:
            mapped = suggest_mapping_for_line(line.ledger_name, line.original_group, db)
            line.suggested_classification = mapped["classification"]
            line.final_classification = mapped["classification"]
            line.financial_statement = mapped["statement"]
            line.note_number = mapped["note_number"]
            line.current_non_current = mapped["current_non_current"]
    db.commit()
    return lines

def auto_map_ledgers(client_id: int, db: Session):
    lines = apply_auto_mapping(client_id, db)
    mapped_count = len([l for l in lines if l.final_classification and l.final_classification != "Other Expenses"])
    unmapped_count = len(lines) - mapped_count
    return {
        "message": f"Auto-mapped {len(lines)} ledgers successfully.",
        "mapped_count": mapped_count,
        "unmapped_count": unmapped_count
    }

def save_manual_override(line_id: int, final_cls: str, statement: str, note_num: str, cur_non_cur: str, db: Session):
    line = db.query(TrialBalanceLine).filter(TrialBalanceLine.id == line_id).first()
    if not line:
        return {"error": "Line not found"}
    line.final_classification = final_cls
    line.financial_statement = statement
    line.note_number = note_num
    line.current_non_current = cur_non_cur
    line.user_override = True
    db.commit()
    return line

def suggest_mapping_rule(ledger_name: str, original_group: str, db: Session):
    return suggest_mapping_for_line(ledger_name, original_group, db)
