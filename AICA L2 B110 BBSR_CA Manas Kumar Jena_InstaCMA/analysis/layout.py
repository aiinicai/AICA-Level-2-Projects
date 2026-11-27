"""
Grouping of CMA heads into the T-form sections of the firm's format, and the
default projection basis of each head.
"""
from config.constants import HEAD_LABEL, FA_KEYS, FA_RATE_DEFAULT

DIRECT = ["wages", "power_fuel", "other_direct"]
INDIRECT = ["salary", "rent", "admin_exp", "selling_exp", "repairs", "audit_fee", "insurance", "bank_charges",
            "misc_exp"]

# heads kept as ONE line in the T-form whatever the client called them
SINGLE_HEADS = {"opening_stock", "purchases", "closing_stock", "interest", "depreciation", "tax", "capital",
                "reserves", "drawings", "capital_introduced", "cc", "creditors", "stock", "debtors",
                "cash_in_hand", "bank_balance"}

SINGLE_LABEL = {
    "opening_stock": "Opening Stock", "purchases": "Purchases", "closing_stock": "Closing Stock",
    "interest": "Bank Interest", "depreciation": "Depreciation", "tax": "Provision for Income Tax",
    "cc": "Cash Credit Loan", "creditors": "Sundry Creditors", "debtors": "Sundry Debtors",
    "cash_in_hand": "Cash in Hand", "bank_balance": "Cash at Bank", "new_term_loan": "Term Loan (Bank) - Proposed",
}

# default projection basis per head (lines may override)
DEFAULT_BASIS = {"other_income": "F", "rent": "F", "audit_fee": "F", "insurance": "F",
                 "unsecured_loans": "H", "statutory_dues": "H", "other_cl": "H", "investments": "H",
                 "loans_advances": "H", "other_ca": "S", "cash_in_hand": "S", "sales": "G"}
for _h in DIRECT + INDIRECT:
    DEFAULT_BASIS.setdefault(_h, "V")

PL_LINE_HEADS = ["sales", "other_income"] + DIRECT + INDIRECT
BS_LINE_HEADS = ["term_loans", "unsecured_loans", "statutory_dues", "other_cl", "investments", "loans_advances",
                 "other_ca"] + FA_KEYS


def basis_of(line):
    if line.basis:
        return line.basis
    return DEFAULT_BASIS.get(line.head, "V" if line.statement == "PL" else "H")


def rate_of(line, intake_rates=None):
    if line.rate is not None:
        return line.rate
    if intake_rates and line.head in intake_rates:
        return intake_rates[line.head]
    return FA_RATE_DEFAULT.get(line.head, 0.15)


def head_label(head):
    return SINGLE_LABEL.get(head) or HEAD_LABEL.get(head, head)


def is_tax_receivable(label):
    s = (label or "").lower()
    return any(w in s for w in ("tds", "tcs", "advance tax", "income tax", "self assessment", "it refund"))


def is_gst_receivable(label):
    s = (label or "").lower()
    return "gst" in s or "input" in s or "itc" in s


def is_deposit(label):
    return "deposit" in (label or "").lower() or "emd" in (label or "").lower()


def section_of(line):
    """Trading account (direct) or Profit & Loss account (indirect) for an expense line."""
    if line.section in ("trading", "pl"):
        return line.section
    return "trading" if line.head in DIRECT else "pl"


EXPENSE_HEADS = DIRECT + INDIRECT


SCHEDULE_III = {
    "sales": "Revenue from operations", "other_income": "Other income", "opening_stock": "Changes in inventories",
    "closing_stock": "Changes in inventories", "purchases": "Cost of materials / purchases",
    "wages": "Employee benefits expense", "salary": "Employee benefits expense", "interest": "Finance costs",
    "bank_charges": "Finance costs", "depreciation": "Depreciation and amortisation", "tax": "Tax expense",
    "capital": "Shareholders' funds - share capital", "reserves": "Shareholders' funds - reserves and surplus",
    "drawings": "Shareholders' funds - dividend", "capital_introduced": "Shareholders' funds",
    "term_loans": "Long-term borrowings", "unsecured_loans": "Long-term borrowings",
    "cc": "Short-term borrowings", "creditors": "Trade payables", "statutory_dues": "Other current liabilities",
    "other_cl": "Other current liabilities / short-term provisions", "investments": "Non-current investments",
    "loans_advances": "Long-term loans and advances", "stock": "Inventories", "debtors": "Trade receivables",
    "other_ca": "Other current assets", "cash_in_hand": "Cash and cash equivalents",
    "bank_balance": "Cash and cash equivalents"}
TFORM = {
    "sales": "Trading A/c - Cr", "closing_stock": "Trading A/c - Cr", "opening_stock": "Trading A/c - Dr",
    "purchases": "Trading A/c - Dr", "other_income": "P&L A/c - Cr", "interest": "P&L A/c - Dr",
    "depreciation": "P&L A/c - Dr", "tax": "P&L A/c - Dr", "capital": "Capital account",
    "reserves": "Capital account", "drawings": "Capital account", "capital_introduced": "Capital account",
    "term_loans": "Loans & borrowings", "unsecured_loans": "Loans & borrowings", "cc": "Loans & borrowings",
    "creditors": "Current liabilities", "statutory_dues": "Current liabilities", "other_cl": "Current liabilities",
    "investments": "Investments", "loans_advances": "Current assets, loans & advances",
    "stock": "Current assets, loans & advances", "debtors": "Current assets, loans & advances",
    "other_ca": "Current assets, loans & advances", "cash_in_hand": "Current assets, loans & advances",
    "bank_balance": "Current assets, loans & advances"}


def group_of(head, company, section=""):
    if head in FA_KEYS:
        return "Property, plant and equipment" if company else "Fixed assets"
    if head in EXPENSE_HEADS:
        if company:
            return SCHEDULE_III.get(head, "Other expenses")
        return "Trading A/c - Dr" if (section or ("trading" if head in DIRECT else "pl")) == "trading" else "P&L A/c - Dr"
    return (SCHEDULE_III if company else TFORM).get(head, "")
