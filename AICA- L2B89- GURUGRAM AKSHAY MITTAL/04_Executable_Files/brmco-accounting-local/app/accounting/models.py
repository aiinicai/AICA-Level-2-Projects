"""Accounting domain model.

This is the pivot of the system:

    INPUT (Excel today; AI extraction / API later)
        -> Voucher (this module)
        -> validation
        -> Tally adapter (XML)
        -> TallyPrime

Nothing in this module knows about Excel or Tally XML.
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

ZERO = Decimal("0")
CENT = Decimal("0.01")


def q2(value: Decimal | int | float | str | None) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


class VoucherKind(str, Enum):
    SALES = "sales"
    PURCHASE = "purchase"
    JOURNAL = "journal"
    RECEIPT = "receipt"
    PAYMENT = "payment"

    @property
    def label(self) -> str:
        return {"sales": "Sales", "purchase": "Purchase", "journal": "Journal",
                "receipt": "Bank Receipt", "payment": "Bank Payment"}[self.value]

    @property
    def tally_voucher_type(self) -> str:
        """Default Tally voucher type name (a Tally company can rename these)."""
        return {"sales": "Sales", "purchase": "Purchase", "journal": "Journal",
                "receipt": "Receipt", "payment": "Payment"}[self.value]


class Side(str, Enum):
    DR = "Dr"
    CR = "Cr"


class ValidationIssue(BaseModel):
    severity: Literal["error", "warning"]
    message: str
    row: int | None = None
    column: str | None = None
    voucher: str | None = None
    code: str = ""


class LedgerPosting(BaseModel):
    ledger: str
    side: Side
    amount: Decimal
    role: str = ""                    # party | income | expense | tax | round_off | bank | journal
    is_party: bool = False
    cost_centre: str | None = None
    bill_name: str | None = None
    bill_type: str | None = None      # New Ref | Agst Ref | On Account
    instrument_number: str | None = None
    instrument_date: date | None = None
    source_row: int | None = None
    source_column: str | None = None  # Excel header, or "Settings: <field>" for configured ledgers


class InventoryLine(BaseModel):
    stock_item: str
    ledger: str                       # sales / purchase ledger the value is allocated to
    side: Side
    quantity: Decimal
    unit: str
    rate: Decimal
    discount: Decimal = ZERO
    amount: Decimal
    hsn: str | None = None
    source_row: int | None = None


class InvoiceLine(BaseModel):
    """One Excel line of a sales/purchase invoice with its GST breakdown."""

    row: int
    ledger: str
    description: str | None = None
    hsn: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    rate: Decimal | None = None
    discount: Decimal = ZERO
    taxable_value: Decimal = ZERO
    cgst_rate: Decimal = ZERO
    cgst_amount: Decimal = ZERO
    sgst_rate: Decimal = ZERO
    sgst_amount: Decimal = ZERO
    igst_rate: Decimal = ZERO
    igst_amount: Decimal = ZERO
    cess_rate: Decimal = ZERO
    cess_amount: Decimal = ZERO
    itc_eligible: bool = True
    is_stock_item: bool = False

    @property
    def tax_total(self) -> Decimal:
        return self.cgst_amount + self.sgst_amount + self.igst_amount + self.cess_amount


class Voucher(BaseModel):
    kind: VoucherKind
    date: date
    voucher_number: str | None = None
    reference: str | None = None
    reference_date: date | None = None
    party_ledger: str | None = None
    party_gstin: str | None = None
    party_state: str | None = None
    place_of_supply: str | None = None
    reverse_charge: bool = False
    narration: str = ""
    lines: list[InvoiceLine] = Field(default_factory=list)
    postings: list[LedgerPosting] = Field(default_factory=list)
    inventory: list[InventoryLine] = Field(default_factory=list)
    round_off: Decimal = ZERO
    invoice_total: Decimal | None = None   # as stated in Excel (for cross-checking)
    rows: list[int] = Field(default_factory=list)

    # ---- identification ---------------------------------------------------
    @property
    def label(self) -> str:
        if self.voucher_number:
            return self.voucher_number
        if self.reference:
            return self.reference
        return f"Row {self.rows[0]}" if self.rows else "(unnumbered)"

    @property
    def first_row(self) -> int | None:
        return self.rows[0] if self.rows else None

    # ---- totals -------------------------------------------------------------
    def _sum(self, attr: str) -> Decimal:
        return sum((getattr(line, attr) for line in self.lines), ZERO)

    @property
    def taxable_total(self) -> Decimal:
        return self._sum("taxable_value")

    @property
    def tax_totals(self) -> dict[str, Decimal]:
        return {k: self._sum(f"{k}_amount") for k in ("cgst", "sgst", "igst", "cess")}

    @property
    def computed_invoice_total(self) -> Decimal:
        return q2(self.taxable_total + sum(self.tax_totals.values(), ZERO) + self.round_off)

    @property
    def total_debit(self) -> Decimal:
        return q2(sum((p.amount for p in self.postings if p.side == Side.DR), ZERO)
                  + sum((i.amount for i in self.inventory if i.side == Side.DR), ZERO))

    @property
    def total_credit(self) -> Decimal:
        return q2(sum((p.amount for p in self.postings if p.side == Side.CR), ZERO)
                  + sum((i.amount for i in self.inventory if i.side == Side.CR), ZERO))

    @property
    def is_balanced(self) -> bool:
        return self.total_debit == self.total_credit and self.total_debit > ZERO

    @property
    def amount(self) -> Decimal:
        return self.total_debit

    # ---- duplicate keys -------------------------------------------------------
    def exact_key(self) -> str | None:
        """Key that must never repeat within a company + financial year once posted."""
        def norm(s: str | None) -> str:
            return (s or "").strip().upper()
        if self.kind == VoucherKind.SALES and self.voucher_number:
            return f"SALES|{norm(self.voucher_number)}"
        if self.kind == VoucherKind.PURCHASE and self.reference:
            return f"PURCHASE|{norm(self.party_ledger)}|{norm(self.reference)}"
        if self.kind == VoucherKind.JOURNAL and self.reference:
            return f"JOURNAL|{self.date.isoformat()}|{norm(self.reference)}"
        if self.kind in (VoucherKind.RECEIPT, VoucherKind.PAYMENT):
            bank = next((p for p in self.postings if p.role == "bank"), None)
            if bank and bank.instrument_number:
                return f"{self.kind.value.upper()}|{norm(bank.ledger)}|{norm(bank.instrument_number)}"
        return None

    def fuzzy_key(self) -> str:
        """Same date + party + amount — flagged as a *possible* duplicate."""
        party = self.party_ledger or next((p.ledger for p in self.postings), "")
        return f"{self.kind.value}|{self.date.isoformat()}|{party.strip().upper()}|{self.amount}"

    # ---- presentation -----------------------------------------------------------
    def preview(self) -> dict[str, Any]:
        taxes = self.tax_totals
        entries: list[dict[str, Any]] = []
        for p in self.postings:
            entries.append({"ledger": p.ledger, "side": p.side.value, "amount": str(p.amount),
                            "cost_centre": p.cost_centre})
        for i in self.inventory:
            entries.append({"ledger": i.ledger, "side": i.side.value, "amount": str(i.amount),
                            "stock_item": i.stock_item, "quantity": str(i.quantity), "unit": i.unit,
                            "rate": str(i.rate)})
        return {
            "kind": self.kind.value,
            "voucher_type": self.kind.label,
            "label": self.label,
            "voucher_number": self.voucher_number,
            "reference": self.reference,
            "date": self.date.isoformat(),
            "party": self.party_ledger,
            "party_gstin": self.party_gstin,
            "place_of_supply": self.place_of_supply,
            "reverse_charge": self.reverse_charge,
            "taxable_value": str(self.taxable_total) if self.lines else None,
            "cgst": str(taxes["cgst"]), "sgst": str(taxes["sgst"]),
            "igst": str(taxes["igst"]), "cess": str(taxes["cess"]),
            "round_off": str(self.round_off),
            "total": str(self.amount),
            "total_debit": str(self.total_debit),
            "total_credit": str(self.total_credit),
            "balanced": self.is_balanced,
            "narration": self.narration,
            "rows": self.rows,
            "entries": entries,
        }
