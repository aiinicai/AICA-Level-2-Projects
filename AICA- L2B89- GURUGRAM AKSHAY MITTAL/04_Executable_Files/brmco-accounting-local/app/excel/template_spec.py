"""Single source of truth for every Excel template.

The generator, the reader and the row validator all read these definitions, so
adding a column or bumping a template version happens in exactly one place.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.accounting.models import VoucherKind

META_SHEET = "_brmco_meta"
SUPPORTED_VERSIONS = {"1.0"}
CURRENT_VERSION = "1.0"
ITC_CHOICES = ("Eligible", "Ineligible")


@dataclass(frozen=True)
class Column:
    key: str
    header: str
    type: str                 # date | text | amount | signed | qty | gst_rate | rate | yesno | gstin | state | choice
    required: bool = False
    level: str = "line"       # voucher (same on every row of a voucher) | line
    width: int = 16
    list_source: str | None = None   # ledgers | bank_ledgers | stock_items | units | states | yesno | itc | cgst_rates | igst_rates
    help: str = ""
    choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class TemplateSpec:
    kind: VoucherKind
    template_id: str
    sheet_name: str
    title: str
    columns: tuple[Column, ...]
    group_by: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)
    version: str = CURRENT_VERSION

    @property
    def headers(self) -> list[str]:
        return [c.header for c in self.columns]

    def column(self, key: str) -> Column:
        return next(c for c in self.columns if c.key == key)

    def header(self, key: str) -> str:
        return self.column(key).header


def _gst_columns() -> tuple[Column, ...]:
    return (
        Column("hsn_sac", "HSN/SAC", "text", width=11),
        Column("quantity", "Quantity", "qty", width=10),
        Column("unit", "Unit", "text", width=8, list_source="units"),
        Column("rate", "Rate", "amount", width=11),
        Column("discount", "Discount", "amount", width=10, help="Discount amount (not %)"),
        Column("taxable_value", "Taxable Value", "amount", width=14,
               help="Leave blank to compute Quantity x Rate - Discount"),
        Column("cgst_rate", "CGST Rate", "gst_rate", width=9, list_source="cgst_rates"),
        Column("cgst_amount", "CGST Amount", "amount", width=12),
        Column("sgst_rate", "SGST Rate", "gst_rate", width=9, list_source="cgst_rates"),
        Column("sgst_amount", "SGST Amount", "amount", width=12),
        Column("igst_rate", "IGST Rate", "gst_rate", width=9, list_source="igst_rates"),
        Column("igst_amount", "IGST Amount", "amount", width=12),
        Column("cess_rate", "Cess Rate", "rate", width=9),
        Column("cess_amount", "Cess Amount", "amount", width=12),
        Column("round_off", "Round Off", "signed", level="voucher", width=10,
               help="Invoice-level; may be negative"),
        Column("invoice_total", "Invoice Total", "amount", level="voucher", width=14,
               help="Invoice-level; checked against the computed total"),
    )


SALES = TemplateSpec(
    kind=VoucherKind.SALES,
    template_id="BRMCO-SALES",
    sheet_name="Sales Entries",
    title="Sales Voucher Template",
    group_by=("invoice_number",),
    columns=(
        Column("voucher_date", "Voucher Date", "date", True, "voucher", 13),
        Column("invoice_number", "Invoice Number", "text", True, "voucher", 15),
        Column("customer_ledger", "Customer Ledger", "text", True, "voucher", 26, "ledgers"),
        Column("customer_gstin", "Customer GSTIN", "gstin", False, "voucher", 17, help="Blank for unregistered"),
        Column("customer_state", "Customer State", "state", False, "voucher", 18, "states"),
        Column("place_of_supply", "Place of Supply", "state", True, "voucher", 18, "states"),
        Column("reverse_charge", "Reverse Charge", "yesno", False, "voucher", 9, "yesno"),
        Column("sales_ledger", "Sales Ledger", "text", True, "line", 22, "ledgers"),
        Column("item_description", "Item/Description", "text", False, "line", 26, "stock_items",
               help="If this matches a Tally stock item and Quantity is given, it posts as an inventory line"),
        *_gst_columns(),
        Column("narration", "Narration", "text", False, "voucher", 30),
    ),
    notes=(
        "One row per invoice line. Rows with the same Invoice Number form one invoice.",
        "Invoice-level columns (date, customer, GSTIN, place of supply, round off, total, narration) "
        "may be left blank on the 2nd and later rows of an invoice.",
        "Intra-state supply (place of supply = company state): CGST + SGST. Inter-state: IGST.",
    ),
)

PURCHASE = TemplateSpec(
    kind=VoucherKind.PURCHASE,
    template_id="BRMCO-PURCHASE",
    sheet_name="Purchase Entries",
    title="Purchase Voucher Template",
    group_by=("supplier_ledger", "invoice_number"),
    columns=(
        Column("voucher_date", "Voucher Date", "date", True, "voucher", 13),
        Column("supplier_ledger", "Supplier Ledger", "text", True, "voucher", 26, "ledgers"),
        Column("supplier_gstin", "Supplier GSTIN", "gstin", False, "voucher", 17),
        Column("invoice_number", "Invoice Number", "text", True, "voucher", 15, help="Supplier's invoice number"),
        Column("invoice_date", "Invoice Date", "date", True, "voucher", 13),
        Column("supplier_state", "Supplier State", "state", False, "voucher", 18, "states"),
        Column("place_of_supply", "Place of Supply", "state", True, "voucher", 18, "states"),
        Column("reverse_charge", "Reverse Charge", "yesno", False, "voucher", 9, "yesno"),
        Column("purchase_ledger", "Purchase/Expense Ledger", "text", True, "line", 24, "ledgers"),
        Column("item_description", "Item/Description", "text", False, "line", 26, "stock_items"),
        *_gst_columns(),
        Column("itc_eligibility", "ITC Eligibility", "choice", False, "line", 12, "itc", choices=ITC_CHOICES,
               help="Ineligible tax is added to the purchase/expense ledger"),
        Column("narration", "Narration", "text", False, "voucher", 30),
    ),
    notes=(
        "One row per invoice line. Rows with the same Supplier Ledger + Invoice Number form one purchase.",
        "Reverse charge invoices: leave the tax columns blank/zero. RCM liability is booked separately in Phase 1.",
        "ITC Eligibility = Ineligible adds that line's GST to the purchase/expense ledger instead of input tax.",
    ),
)

JOURNAL = TemplateSpec(
    kind=VoucherKind.JOURNAL,
    template_id="BRMCO-JOURNAL",
    sheet_name="Journal Entries",
    title="Journal Voucher Template",
    group_by=("voucher_date", "reference_number"),
    columns=(
        Column("voucher_date", "Voucher Date", "date", True, "voucher", 13),
        Column("reference_number", "Reference Number", "text", True, "voucher", 16,
               help="Rows with the same date + reference form one journal"),
        Column("ledger", "Ledger", "text", True, "line", 30, "ledgers"),
        Column("debit", "Debit", "amount", False, "line", 14),
        Column("credit", "Credit", "amount", False, "line", 14),
        Column("cost_centre", "Cost Centre", "text", False, "line", 18),
        Column("narration", "Narration", "text", False, "voucher", 36),
    ),
    notes=(
        "Each row has either a Debit or a Credit amount, not both.",
        "Total Debit must equal Total Credit for every journal, otherwise nothing is posted.",
    ),
)

_BANK_COMMON_TAIL = (
    Column("amount", "Amount", "amount", True, "voucher", 14),
    Column("instrument_number", "Instrument/UTR", "text", False, "voucher", 18),
    Column("instrument_date", "Instrument Date", "date", False, "voucher", 13),
    Column("reference_number", "Reference Number", "text", False, "voucher", 16,
           help="Bill/invoice this receipt or payment settles (optional)"),
    Column("narration", "Narration", "text", False, "voucher", 36),
)

RECEIPT = TemplateSpec(
    kind=VoucherKind.RECEIPT,
    template_id="BRMCO-BANK-RECEIPT",
    sheet_name="Bank Receipts",
    title="Bank Receipt Template",
    columns=(
        Column("voucher_date", "Voucher Date", "date", True, "voucher", 13),
        Column("bank_ledger", "Bank Ledger", "text", True, "voucher", 24, "bank_ledgers"),
        Column("party_ledger", "Party Ledger", "text", True, "voucher", 28, "ledgers"),
        *_BANK_COMMON_TAIL,
    ),
    notes=("One row per receipt.  Accounting: Bank A/c Dr  To Party A/c.",),
)

PAYMENT = TemplateSpec(
    kind=VoucherKind.PAYMENT,
    template_id="BRMCO-BANK-PAYMENT",
    sheet_name="Bank Payments",
    title="Bank Payment Template",
    columns=(
        Column("voucher_date", "Voucher Date", "date", True, "voucher", 13),
        Column("bank_ledger", "Bank Ledger", "text", True, "voucher", 24, "bank_ledgers"),
        Column("party_ledger", "Party/Expense Ledger", "text", True, "voucher", 28, "ledgers"),
        *_BANK_COMMON_TAIL,
    ),
    notes=("One row per payment.  Accounting: Party/Expense A/c Dr  To Bank A/c.",),
)

SPECS: dict[VoucherKind, TemplateSpec] = {s.kind: s for s in (SALES, PURCHASE, JOURNAL, RECEIPT, PAYMENT)}
SPECS_BY_ID: dict[str, TemplateSpec] = {s.template_id: s for s in SPECS.values()}


def spec_for(kind: VoucherKind | str) -> TemplateSpec:
    return SPECS[VoucherKind(kind)]
