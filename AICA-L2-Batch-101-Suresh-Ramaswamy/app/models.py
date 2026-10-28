"""Common internal transaction model. One Line = one item/rate row of an invoice."""
from collections import OrderedDict
from dataclasses import dataclass, field, asdict, fields
from decimal import Decimal
from typing import Dict, List

from .utils import D, norm_invoice_no, ZERO

AMOUNT_FIELDS = ("qty", "rate", "taxable", "igst", "cgst", "sgst", "cess", "invoice_total")

STATUS_PENDING = "Pending"
STATUS_APPROVED = "Approved"
STATUS_REJECTED = "Rejected"
STATUS_DUP = "Duplicate?"


@dataclass
class Line:
    id: int = 0
    source_file: str = ""
    source_ref: str = ""          # sheet!row or page
    supplier_gstin: str = ""
    supplier_name: str = ""
    recipient_gstin: str = ""
    recipient_name: str = ""
    invoice_no: str = ""
    invoice_date: str = ""        # ISO
    invoice_type: str = "Regular"
    note_type: str = ""           # '' invoice, 'C' credit note, 'D' debit note
    orig_invoice_no: str = ""
    orig_invoice_date: str = ""
    pos: str = ""                 # 2-digit state code
    reverse_charge: str = "N"
    ecom_gstin: str = ""
    hsn: str = ""
    description: str = ""
    uqc: str = ""
    qty: Decimal = ZERO
    rate: Decimal = ZERO
    taxable: Decimal = ZERO
    igst: Decimal = ZERO
    cgst: Decimal = ZERO
    sgst: Decimal = ZERO
    cess: Decimal = ZERO
    invoice_total: Decimal = ZERO
    nil_kind: str = ""            # '', 'Nil Rated', 'Exempted', 'Non-GST'  (for Table 8)
    export_type: str = ""         # '', 'WPAY', 'WOPAY'
    port_code: str = ""
    ship_bill_no: str = ""
    ship_bill_date: str = ""      # ISO
    confidence: float = 1.0
    review_status: str = STATUS_PENDING
    section: str = ""
    section_locked: bool = False
    note: str = ""

    @property
    def tax_total(self) -> Decimal:
        return self.igst + self.cgst + self.sgst

    @property
    def line_total(self) -> Decimal:
        return self.taxable + self.igst + self.cgst + self.sgst + self.cess

    @property
    def is_interstate(self) -> bool:
        if self.igst:
            return True
        if self.cgst or self.sgst:
            return False
        return bool(self.pos and self.supplier_gstin and self.pos != self.supplier_gstin[:2])

    def key(self):
        return (self.note_type, norm_invoice_no(self.invoice_no), self.invoice_date)

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in AMOUNT_FIELDS:
            d[k] = str(d[k])
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Line":
        names = {f.name for f in fields(cls)}
        kw = {k: v for k, v in d.items() if k in names}
        for k in AMOUNT_FIELDS:
            if k in kw:
                kw[k] = D(kw[k])
        return cls(**kw)


@dataclass
class DocSeries:
    """One row of the document-series register (Table 13)."""
    id: int = 0
    nature: str = "Invoices for outward supply"
    from_no: str = ""
    to_no: str = ""
    total: int = 0
    cancelled: int = 0
    origin: str = "manual"       # manual | register | derived
    source_file: str = ""

    @property
    def net(self) -> int:
        return self.total - self.cancelled

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})


def group_invoices(lines: List[Line]) -> Dict[tuple, List[Line]]:
    out: "OrderedDict[tuple, List[Line]]" = OrderedDict()
    for l in lines:
        out.setdefault(l.key(), []).append(l)
    return out


def invoice_value(group: List[Line]) -> Decimal:
    """Invoice-level value without double counting multi-line invoices."""
    totals = [l.invoice_total for l in group if l.invoice_total != 0]
    if totals:
        if len(set(totals)) > 1:      # differing values => they are line totals
            return sum(totals, ZERO)
        return totals[0]
    return sum((l.line_total for l in group), ZERO)


def computed_value(group: List[Line]) -> Decimal:
    return sum((l.line_total for l in group), ZERO)
