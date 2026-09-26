"""Filled sample data matching the demo Tally masters (used by demo mode, tests and scripts)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.accounting.gst import gstin_checksum_char
from app.accounting.models import VoucherKind


def _gstin(first14: str) -> str:
    return first14 + gstin_checksum_char(first14)


GSTIN_ABC = _gstin("27AAPFA1234B1Z")   # Maharashtra
GSTIN_XYZ = _gstin("24AABCX5678C1Z")   # Gujarat
GSTIN_SHARMA = _gstin("27AAKFS4321D1Z")
GSTIN_METRO = _gstin("27AAECM8765E1Z")

D = datetime

SAMPLE_ROWS: dict[VoucherKind, list[dict[str, Any]]] = {
    VoucherKind.SALES: [
        {"voucher_date": D(2026, 9, 25), "invoice_number": "INV-1025", "customer_ledger": "ABC Traders",
         "customer_gstin": GSTIN_ABC, "customer_state": "Maharashtra", "place_of_supply": "Maharashtra",
         "reverse_charge": "No", "sales_ledger": "Sales - Services", "item_description": "Consulting services",
         "hsn_sac": "998311", "taxable_value": 100000, "cgst_rate": 9, "cgst_amount": 9000, "sgst_rate": 9,
         "sgst_amount": 9000, "round_off": 0, "invoice_total": 118000, "narration": "Consulting fee for September"},
        {"voucher_date": D(2026, 9, 26), "invoice_number": "INV-1026", "customer_ledger": "XYZ Enterprises",
         "customer_gstin": GSTIN_XYZ, "customer_state": "Gujarat", "place_of_supply": "Gujarat",
         "reverse_charge": "No", "sales_ledger": "Sales @ 18%", "item_description": "Steel Rod 12mm",
         "hsn_sac": "7214", "quantity": 100, "unit": "Kg", "rate": 55, "taxable_value": 5500, "igst_rate": 18,
         "igst_amount": 990, "round_off": 0, "invoice_total": 17110, "narration": "Material supply"},
        {"invoice_number": "INV-1026", "sales_ledger": "Sales @ 18%", "item_description": "Office Chair",
         "hsn_sac": "9401", "quantity": 2, "unit": "Nos", "rate": 4500, "taxable_value": 9000, "igst_rate": 18,
         "igst_amount": 1620},
    ],
    VoucherKind.PURCHASE: [
        {"voucher_date": D(2026, 9, 20), "supplier_ledger": "Sharma Suppliers", "supplier_gstin": GSTIN_SHARMA,
         "invoice_number": "SS/2026/881", "invoice_date": D(2026, 9, 18), "supplier_state": "Maharashtra",
         "place_of_supply": "Maharashtra", "reverse_charge": "No", "purchase_ledger": "Purchase @ 18%",
         "item_description": "Raw material", "hsn_sac": "7214", "taxable_value": 50000, "cgst_rate": 9,
         "cgst_amount": 4500, "sgst_rate": 9, "sgst_amount": 4500, "invoice_total": 59000,
         "itc_eligibility": "Eligible", "narration": "Purchase of raw material"},
        {"voucher_date": D(2026, 9, 22), "supplier_ledger": "Metro Office Supplies", "supplier_gstin": GSTIN_METRO,
         "invoice_number": "MOS-4471", "invoice_date": D(2026, 9, 22), "supplier_state": "Maharashtra",
         "place_of_supply": "Maharashtra", "purchase_ledger": "Office Expenses", "item_description": "Pantry items",
         "taxable_value": 2000.50, "cgst_rate": 9, "cgst_amount": 180.05, "sgst_rate": 9, "sgst_amount": 180.05,
         "round_off": -0.60, "invoice_total": 2360, "itc_eligibility": "Ineligible", "narration": "Pantry — ITC blocked"},
    ],
    VoucherKind.JOURNAL: [
        {"voucher_date": D(2026, 9, 30), "reference_number": "JV-001", "ledger": "Salary", "debit": 50000,
         "cost_centre": "Head Office", "narration": "Salary provision for September 2026"},
        {"voucher_date": D(2026, 9, 30), "reference_number": "JV-001", "ledger": "Salary Payable", "credit": 50000},
        {"voucher_date": D(2026, 9, 30), "reference_number": "JV-002", "ledger": "Rent", "debit": 20000,
         "narration": "Rent paid by partner"},
        {"voucher_date": D(2026, 9, 30), "reference_number": "JV-002", "ledger": "Capital A/c", "credit": 20000},
    ],
    VoucherKind.RECEIPT: [
        {"voucher_date": D(2026, 9, 27), "bank_ledger": "HDFC Bank", "party_ledger": "ABC Traders", "amount": 118000,
         "instrument_number": "HDFCN52026092712345", "instrument_date": D(2026, 9, 27), "reference_number": "INV-1025",
         "narration": "Received against INV-1025"},
        {"voucher_date": D(2026, 9, 28), "bank_ledger": "HDFC Bank", "party_ledger": "XYZ Enterprises", "amount": 10000,
         "instrument_number": "000451", "instrument_date": D(2026, 9, 28), "narration": "Advance received"},
    ],
    VoucherKind.PAYMENT: [
        {"voucher_date": D(2026, 9, 28), "bank_ledger": "ICICI Bank", "party_ledger": "Sharma Suppliers", "amount": 59000,
         "instrument_number": "ICICR52026092800991", "instrument_date": D(2026, 9, 28), "reference_number": "SS/2026/881",
         "narration": "Paid against SS/2026/881"},
        {"voucher_date": D(2026, 9, 30), "bank_ledger": "ICICI Bank", "party_ledger": "Bank Charges", "amount": 236,
         "narration": "Bank charges for September"},
    ],
}
