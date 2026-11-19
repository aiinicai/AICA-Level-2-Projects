"""Canonical invoice produced by every extraction route (QR / text / OCR / Gemini)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal


@dataclass
class Line:
    description: str = ""
    hsn: str = ""
    qty: Decimal = Decimal(0)
    uom: str = ""
    rate: Decimal = Decimal(0)
    taxable: Decimal = Decimal(0)
    gst_rate: Decimal = Decimal(0)


@dataclass
class TaxRow:
    """One GST rate slab of the invoice."""
    rate: Decimal                      # total GST % (e.g. 18)
    taxable: Decimal = Decimal(0)
    igst: Decimal = Decimal(0)
    cgst: Decimal = Decimal(0)
    sgst: Decimal = Decimal(0)
    cess: Decimal = Decimal(0)


@dataclass
class Invoice:
    supplier_name: str = ""
    supplier_gstin: str = ""
    supplier_pan: str = ""
    buyer_gstin: str = ""
    invoice_no: str = ""
    invoice_date: str = ""             # YYYYMMDD
    place_of_supply: str = ""          # state code, e.g. "24"
    irn: str = ""
    lines: list[Line] = field(default_factory=list)
    taxes: list[TaxRow] = field(default_factory=list)
    taxable_total: Decimal = Decimal(0)
    igst_total: Decimal = Decimal(0)
    cgst_total: Decimal = Decimal(0)
    sgst_total: Decimal = Decimal(0)
    cess_total: Decimal = Decimal(0)
    tcs: Decimal = Decimal(0)
    round_off: Decimal = Decimal(0)
    grand_total: Decimal = Decimal(0)
    reverse_charge: bool = False
    hsn_codes: list[str] = field(default_factory=list)
    document_type: str = ""            # tax_invoice | bill_of_supply | credit_note | debit_note | ...
    original_invoice_no: str = ""      # credit / debit note: the invoice it is issued against
    notes: str = ""
    model: str = ""
    source: str = ""                   # qr | text | docx | xlsx | ocr | gemini
    field_confidence: dict = field(default_factory=dict)   # field -> 0..1
    raw_text: str = ""

    @property
    def tax_total(self) -> Decimal:
        return self.igst_total + self.cgst_total + self.sgst_total + self.cess_total

    def to_json(self) -> dict:
        def conv(o):
            if isinstance(o, Decimal):
                return str(o)
            if isinstance(o, list):
                return [conv(x) for x in o]
            if isinstance(o, dict):
                return {k: conv(v) for k, v in o.items()}
            return o
        d = asdict(self)
        d.pop("raw_text", None)
        return conv(d)

    @classmethod
    def from_json(cls, d: dict) -> "Invoice":
        D = lambda v: Decimal(str(v or 0))
        inv = cls(**{k: v for k, v in d.items()
                     if k in cls.__dataclass_fields__ and k not in ("lines", "taxes")})
        inv.hsn_codes = list(d.get("hsn_codes") or [])
        for k in ("taxable_total", "igst_total", "cgst_total", "sgst_total", "cess_total", "tcs",
                  "round_off", "grand_total"):
            setattr(inv, k, D(getattr(inv, k)))
        inv.lines = [Line(l.get("description", ""), l.get("hsn", ""), D(l.get("qty")), l.get("uom", ""),
                          D(l.get("rate")), D(l.get("taxable")), D(l.get("gst_rate"))) for l in d.get("lines", [])]
        inv.taxes = [TaxRow(D(t.get("rate")), D(t.get("taxable")), D(t.get("igst")), D(t.get("cgst")),
                            D(t.get("sgst")), D(t.get("cess"))) for t in d.get("taxes", [])]
        return inv
