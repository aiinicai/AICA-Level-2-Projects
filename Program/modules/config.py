"""
Configuration and Defaults for Ind AS 116 Lease Accounting Tool
"""
from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Dict, List

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_GUIDANCE_DIR = (BASE_DIR.parent / "Knowlege").resolve()

# Common Windows paths for Tesseract
TESSERACT_SEARCH_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    "tesseract"
]

# Common Windows paths for Poppler
POPPLER_SEARCH_PATHS = [
    r"C:\Program Files\poppler\bin",
    r"C:\Program Files (x86)\poppler\bin",
    r"C:\poppler\bin",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\poppler\bin")
]

# Accounting Standards Defaults
DEFAULT_CURRENCY = "INR"
DEFAULT_CURRENCY_SYMBOL = "₹"
DEFAULT_DISCOUNT_RATE = 8.50  # 8.5% annual Incremental Borrowing Rate (IBR)
LOW_VALUE_THRESHOLD_INR = 400000.0  # Approx USD 5,000 per Ind AS 116 guidance
SHORT_TERM_THRESHOLD_MONTHS = 12

PAYMENT_FREQUENCY_MAP = {
    "Monthly": 12,
    "Quarterly": 4,
    "Half-Yearly": 2,
    "Annual": 1
}

# Extraction Fields Specification
EXTRACTION_FIELDS = [
    {"key": "lessor_name", "label": "Lessor Name", "type": "str", "required": True},
    {"key": "lessee_name", "label": "Lessee Name", "type": "str", "required": True},
    {"key": "asset_description", "label": "Underlying Asset Description", "type": "str", "required": True},
    {"key": "commencement_date", "label": "Lease Commencement Date", "type": "date", "required": True},
    {"key": "possession_date", "label": "Possession / Handover Date", "type": "date", "required": False},
    {"key": "lease_term_months", "label": "Lease Term (Months)", "type": "int", "required": True},
    {"key": "fixed_rental_amount", "label": "Fixed Rental Amount per Period", "type": "float", "required": True},
    {"key": "payment_frequency", "label": "Payment Frequency", "type": "str", "required": True, "options": ["Monthly", "Quarterly", "Half-Yearly", "Annual"]},
    {"key": "payment_timing", "label": "Payment Timing", "type": "str", "required": True, "options": ["In Arrears", "In Advance"]},
    {"key": "due_date_convention", "label": "Due Date Convention", "type": "str", "required": False},
    {"key": "rent_free_period_months", "label": "Rent-Free Period (Months)", "type": "int", "required": False},
    {"key": "escalation_clause", "label": "Escalation Clause Present?", "type": "bool", "required": False},
    {"key": "escalation_pct", "label": "Escalation Percentage (%)", "type": "float", "required": False},
    {"key": "escalation_frequency_months", "label": "Escalation Interval (Months)", "type": "int", "required": False},
    {"key": "security_deposit", "label": "Security Deposit Amount", "type": "float", "required": False},
    {"key": "lease_incentive", "label": "Lease Incentive Received/Receivable", "type": "float", "required": False},
    {"key": "initial_direct_costs", "label": "Initial Direct Costs Incurred", "type": "float", "required": False},
    {"key": "restoration_obligation", "label": "Estimated Dismantling / Restoration Cost", "type": "float", "required": False},
    {"key": "renewal_option", "label": "Renewal / Extension Option", "type": "str", "required": False},
    {"key": "renewal_certain", "label": "Renewal Reasonably Certain to be Exercised?", "type": "bool", "required": False},
    {"key": "termination_option", "label": "Termination Option", "type": "str", "required": False},
    {"key": "purchase_option", "label": "Purchase Option Present?", "type": "bool", "required": False},
    {"key": "purchase_option_price", "label": "Purchase Option Strike Price", "type": "float", "required": False},
    {"key": "purchase_certain", "label": "Purchase Option Reasonably Certain?", "type": "bool", "required": False},
    {"key": "variable_lease_payments", "label": "Variable Lease Payments Clause", "type": "str", "required": False},
    {"key": "non_lease_components", "label": "Non-Lease Components (CAM/Maintenance/Insurance/Tax)", "type": "float", "required": False},
    {"key": "discount_rate", "label": "Incremental Borrowing Rate / Discount Rate (%)", "type": "float", "required": True},
    {"key": "residual_value_guarantee", "label": "Residual Value Guarantee Expected Payment", "type": "float", "required": False},
    {"key": "restrictions_covenants", "label": "Restrictions, Use Covenants & Conditions", "type": "str", "required": False},
    {"key": "indemnity_clauses", "label": "Indemnity & Other Significant Clauses", "type": "str", "required": False}
]

# Standard Disclaimer
STATUTORY_DISCLAIMER = (
    "DISCLAIMER & PROFESSIONAL NOTICE:\n"
    "This calculation schedule and report is generated as an automated draft to assist "
    "finance and accounting professionals under Indian Accounting Standard 116 (Ind AS 116 - Leases). "
    "It does not replace professional auditing judgment, technical review by a qualified Chartered Accountant, "
    "or formal management assessment of contracts. All inputs, options, dates, and accounting elections "
    "must be verified against primary executed lease agreements and audited financial policies."
)
