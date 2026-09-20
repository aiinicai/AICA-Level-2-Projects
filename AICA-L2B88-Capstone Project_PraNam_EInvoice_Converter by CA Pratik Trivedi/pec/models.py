"""Plain data containers shared by reader, transformer, validator, writer and GUI."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

RED, AMBER, GREEN = "RED", "AMBER", "GREEN"


@dataclass
class Issue:
    level: str                 # RED / AMBER / GREEN
    field: str                 # e.g. "Invoice Date", "HSN"
    message: str
    item_no: int | None = None

    def text(self) -> str:
        where = f"Item {self.item_no}: " if self.item_no else ""
        return f"[{self.level}] {where}{self.message}"


class Issues(list):
    def red(self, field, msg, item=None): self.append(Issue(RED, field, msg, item))
    def amber(self, field, msg, item=None): self.append(Issue(AMBER, field, msg, item))
    def green(self, field, msg, item=None): self.append(Issue(GREEN, field, msg, item))

    def n(self, level): return sum(1 for i in self if i.level == level)
    @property
    def has_red(self): return any(i.level == RED for i in self)


@dataclass
class SourceValue:
    """A value read from the source workbook together with where it came from."""
    value: object = None
    cell: str = ""             # e.g. "Invoice!F4"
    note: str = ""             # e.g. "formula result (cached)"
    formula_uncached: bool = False

    @property
    def text(self) -> str:
        from .util import clean_text
        return clean_text(self.value)

    def where(self) -> str:
        return self.cell or "not found in source"


@dataclass
class Party:
    name: str = ""
    lines: list[str] = field(default_factory=list)   # address lines after the name
    cell: str = ""
    email: str = ""
    phone: str = ""
    gstin: str = ""


@dataclass
class SourceItem:
    sl_no: int
    row: int
    description: SourceValue
    hsn: SourceValue
    hsn_was_number: bool = False
    values: dict[str, SourceValue] = field(default_factory=dict)   # role -> value (cartons, amount ...)
    hidden_row: bool = False
    packing_net_kg: Decimal | None = None
    packing_desc: str = ""

    def num(self, role) -> Decimal | None:
        from .util import to_decimal, first_number
        sv = self.values.get(role)
        if sv is None or sv.value is None:
            return None
        return first_number(sv.value) if role == "pack_size" else to_decimal(sv.value)


@dataclass
class SourceInvoice:
    path: str
    sheet: str
    fields: dict[str, SourceValue] = field(default_factory=dict)
    consignee: Party = field(default_factory=Party)
    notify_party: Party = field(default_factory=Party)
    buyer_block: Party = field(default_factory=Party)
    buyer_block2: Party = field(default_factory=Party)
    exporter_block: Party = field(default_factory=Party)
    header_row: int = 0
    columns: dict[str, str] = field(default_factory=dict)          # role -> column letter
    header_labels: dict[str, str] = field(default_factory=dict)    # role -> header text
    currency: SourceValue = field(default_factory=SourceValue)
    items: list[SourceItem] = field(default_factory=list)
    source_total: SourceValue = field(default_factory=SourceValue)
    source_grand_total: SourceValue = field(default_factory=SourceValue)
    all_text: list[tuple[str, str]] = field(default_factory=list)     # (cell, text) of every text cell
    packing_sheet: str = ""
    read_issues: Issues = field(default_factory=Issues)
    signature: dict = field(default_factory=dict)


@dataclass
class ConversionOptions:
    transaction_type: str = "Export"      # Export | Domestic
    supply_type: str = ""                 # EXPWOP | EXPWP
    doc_type: str = "Tax Invoice"
    exchange_rate: Decimal | None = None
    exchange_rate_source: str = ""        # "user" | cell reference
    buyer_gstin: str = ""                 # set when the invoice is a domestic (B2B) supply
    buyer_party: str = ""                 # consignee | notify_party | buyer_block | buyer_fields
    buyer_location: str = ""
    buyer_pin: str = ""
    quantity_basis: str = ""              # cartons | packs | net_kg_computed | net_kg_packing | source_qty
    uqc: str = ""                         # NIC master unit DESCRIPTION, e.g. "CARTONS"
    port_code: str = ""
    port_from_profile: bool = False
    country_code: str = ""
    supplier_refund: str = ""             # "" | Yes | No
    shipping_bill_no: str = ""
    shipping_bill_date: str = ""
    export_duty: Decimal | None = None
    round_off: bool = False
    reverse_charge: str = "No"                 # Yes | No
    igst_on_intra: str = "No"                  # Yes | No
    reporting_30d_applies: bool = False        # offline user-controlled AATO >= Rs 10 crore flag
    rsp_based_relaxation: bool = False         # offline user-controlled RSP rule flag
    dayfirst: bool = True
    tolerance_inr: Decimal = Decimal("1.00")
    tolerance_fc: Decimal = Decimal("0.05")
    item_gst_rates: dict[int, Decimal] = field(default_factory=dict)
    rate_from_memory: set = field(default_factory=set)
    write_mode: str = "replace"           # replace demo/existing rows | append
    test_note: str = ""
    auto_notes: list = field(default_factory=list)   # (level, field, message) from automatic derivation


@dataclass
class Supplier:
    legal_name: str = ""
    trade_name: str = ""
    gstin: str = ""
    address1: str = ""
    address2: str = ""
    location: str = ""
    state: str = ""
    state_code: str = ""
    pin: str = ""
    phone: str = ""
    email: str = ""


@dataclass
class MappedField:
    field: str
    source: str
    value: str
    target: str
    status: str
    remarks: str = ""


@dataclass
class ConversionResult:
    source: SourceInvoice
    options: ConversionOptions
    header: dict[str, str] = field(default_factory=dict)          # NIC column code -> text
    items: list[dict[str, str]] = field(default_factory=list)
    field_log: list[MappedField] = field(default_factory=list)
    issues: Issues = field(default_factory=Issues)
    totals: dict[str, Decimal] = field(default_factory=dict)
    recon: list[tuple[str, str, str, str, str]] = field(default_factory=list)  # check, a, b, diff, status
    doc_date: dt.date | None = None
