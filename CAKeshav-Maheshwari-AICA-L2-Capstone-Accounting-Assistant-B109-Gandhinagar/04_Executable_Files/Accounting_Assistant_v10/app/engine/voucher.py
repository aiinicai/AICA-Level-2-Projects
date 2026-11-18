"""Proposed voucher (what the Review grid shows) and its TallyPrime XML."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from xml.sax.saxutils import escape

Q = Decimal("0.01")


@dataclass
class VLine:
    ledger: str
    amount: Decimal                 # always positive
    dr: bool
    kind: str = ""                  # party | expense | purchase | gst_in | gst_rcm_in | gst_rcm_out | tds | tcs | round | other
    note: str = ""                  # why this ledger (shown as tooltip)
    confidence: str = "red"         # green | amber | red
    bill_ref: str = ""              # for party line: New Ref name
    credit_days: int = 0
    bill_type: str = ""             # "" = New Ref when bill_ref set; "On Account" for bank entries
    bills: list = field(default_factory=list)   # explicit allocations [(name, type, amount)] - bill-wise settlement
    fx_cur: str = ""                # foreign-currency ledger: symbol ('$'); amount stays the rupee value
    fx_qty: Decimal | None = None   # foreign amount (positive); 0 for a pure exchange-difference line
    fx_rate: Decimal | None = None  # rupees per unit


@dataclass
class InvLine:
    """Inventory line for item-invoice mode."""
    stock_item: str
    qty: Decimal
    uom: str
    rate: Decimal
    amount: Decimal
    purchase_ledger: str
    godown: str = "Main Location"
    dr: bool = True                 # purchase / debit note side; False for sales / credit note


@dataclass
class Voucher:
    vtype: str                       # Tally voucher type name, e.g. Purchase / Journal / custom
    date: str                        # YYYYMMDD
    lines: list[VLine] = field(default_factory=list)
    inventory: list[InvLine] = field(default_factory=list)
    reference: str = ""              # supplier invoice no
    reference_date: str = ""
    party: str = ""
    narration: str = ""
    base_type: str = "Purchase"      # Purchase | Journal | Payment | Receipt | Contra | Sales | Debit Note | Credit Note
    number: str = ""                 # voucher number; blank = Tally numbers it

    @property
    def dr_total(self) -> Decimal:
        return sum((l.amount for l in self.lines if l.dr), Decimal(0)) + \
            sum((i.amount for i in self.inventory if i.dr), Decimal(0))

    @property
    def cr_total(self) -> Decimal:
        return sum((l.amount for l in self.lines if not l.dr), Decimal(0)) + \
            sum((i.amount for i in self.inventory if not i.dr), Decimal(0))

    @property
    def balanced(self) -> bool:
        return abs(self.dr_total - self.cr_total) < Decimal("0.005")

    def problems(self, known_ledgers: set[str] | None = None, known_items: set[str] | None = None) -> list[str]:
        out = []
        if not self.balanced:
            out.append(f"Dr {self.dr_total} and Cr {self.cr_total} differ by {self.dr_total - self.cr_total}")
        if not self.lines and not self.inventory:
            out.append("No lines")
        for l in self.lines:
            if not l.ledger:
                out.append("A line has no ledger")
            elif known_ledgers is not None and l.ledger not in known_ledgers:
                out.append(f"Ledger '{l.ledger}' does not exist in Tally")
            if l.amount <= 0:
                out.append(f"'{l.ledger}' has zero/negative amount")
            if l.bills:
                alloc = sum((Decimal(str(a)) for _n, _t, a in l.bills), Decimal(0))
                if abs(alloc - l.amount) >= Decimal("0.01"):
                    out.append(f"Bill allocations of '{l.ledger}' ({alloc}) don't add up to {l.amount}")
        for i in self.inventory:
            if known_items is not None and i.stock_item not in known_items:
                out.append(f"Stock item '{i.stock_item}' does not exist in Tally")
        return out


def _amt(v: Decimal, dr: bool) -> str:
    v = v.quantize(Q)
    return f"{-v}" if dr else f"{v}"


def _fx(l: VLine, inr: Decimal) -> str:
    """Tally's own format for a foreign-currency amount, e.g. '-$ 50000.00 @ ₹ 95.1625/$ = -₹ 4758125.00'
    (exactly as Tally exports it; a zero foreign amount is how Tally carries an exchange difference)."""
    sign = "-" if l.dr else ""
    inr = inr.quantize(Q)
    qty = (l.fx_qty or Decimal(0)).quantize(Q)
    if not qty:
        return f"{l.fx_cur} 0.00 @ \u20b9 /{l.fx_cur} = {sign}\u20b9 {inr}"
    return f"{sign}{l.fx_cur} {qty} @ \u20b9 {l.fx_rate}/{l.fx_cur} = {sign}\u20b9 {inr}"


def _a(l: VLine, v: Decimal) -> str:
    return _fx(l, Decimal(str(v))) if l.fx_cur else _amt(Decimal(str(v)), l.dr)


def _bill(l: VLine) -> str:
    if l.bills:
        out = ""
        for name, btype, amt in l.bills:
            if len(l.bills) == 1:
                amt = l.amount                    # a single allocation always carries the whole line
            nm = f"<NAME>{escape(name)}</NAME>" if name and btype != "On Account" else "<NAME/>"
            out += (f"<BILLALLOCATIONS.LIST>{nm}<BILLTYPE>{escape(btype)}</BILLTYPE>"
                    f"<AMOUNT>{_a(l, abs(Decimal(str(amt))))}</AMOUNT></BILLALLOCATIONS.LIST>")
        return out
    if l.bill_type == "On Account":
        return (f"<BILLALLOCATIONS.LIST><NAME/><BILLTYPE>On Account</BILLTYPE>"
                f"<AMOUNT>{_a(l, l.amount)}</AMOUNT></BILLALLOCATIONS.LIST>")
    if not l.bill_ref:
        return ""
    cp = f"<BILLCREDITPERIOD>{l.credit_days} Days</BILLCREDITPERIOD>" if l.credit_days else ""
    return (f"<BILLALLOCATIONS.LIST><NAME>{escape(l.bill_ref)}</NAME><BILLTYPE>New Ref</BILLTYPE>{cp}"
            f"<AMOUNT>{_a(l, l.amount)}</AMOUNT></BILLALLOCATIONS.LIST>")


def _ledger_entry(l: VLine, tag: str) -> str:
    party = "Yes" if l.kind in ("party",) else "No"
    return (f"<{tag}><LEDGERNAME>{escape(l.ledger)}</LEDGERNAME>"
            f"<ISDEEMEDPOSITIVE>{'Yes' if l.dr else 'No'}</ISDEEMEDPOSITIVE>"
            f"<ISPARTYLEDGER>{party}</ISPARTYLEDGER><AMOUNT>{_a(l, l.amount)}</AMOUNT>{_bill(l)}</{tag}>")


def to_xml(v: Voucher, remote_id: str = "") -> str:
    """One <VOUCHER> fragment. Accounting-voucher view for ledger-only entries;
    item-invoice view when inventory lines exist."""
    invoice_mode = bool(v.inventory)
    view = "Invoice Voucher View" if invoice_mode else "Accounting Voucher View"
    head = (f'<VOUCHER VCHTYPE="{escape(v.vtype)}" ACTION="Create" OBJVIEW="{view}"'
            + (f' REMOTEID="{escape(remote_id)}"' if remote_id else "") + ">"
            f"<DATE>{v.date}</DATE><EFFECTIVEDATE>{v.date}</EFFECTIVEDATE>"
            f"<VOUCHERTYPENAME>{escape(v.vtype)}</VOUCHERTYPENAME>"
            + (f"<VOUCHERNUMBER>{escape(v.number)}</VOUCHERNUMBER>" if v.number else "") +
            f"<PERSISTEDVIEW>{view}</PERSISTEDVIEW>")
    if v.reference:
        head += f"<REFERENCE>{escape(v.reference)}</REFERENCE>"
        if v.reference_date:
            head += f"<REFERENCEDATE>{v.reference_date}</REFERENCEDATE>"
    if v.party:
        head += f"<PARTYLEDGERNAME>{escape(v.party)}</PARTYLEDGERNAME><PARTYNAME>{escape(v.party)}</PARTYNAME>"
    if v.narration:
        head += f"<NARRATION>{escape(v.narration)}</NARRATION>"
    head += f"<ISINVOICE>{'Yes' if invoice_mode else 'No'}</ISINVOICE>"
    if invoice_mode:
        # without this TallyPrime saves the voucher as an Accounting Invoice: ledger lines kept, stock lines
        # silently dropped (no quantity in or out), and later outward entries fail for want of stock
        head += "<VCHENTRYMODE>Item Invoice</VCHENTRYMODE>"
    body = ""
    if invoice_mode:
        for i in v.inventory:
            qty = f" {i.qty.normalize():f} {i.uom}".rstrip()
            pos = "Yes" if i.dr else "No"
            a = _amt(i.amount, i.dr)
            body += (f"<ALLINVENTORYENTRIES.LIST><STOCKITEMNAME>{escape(i.stock_item)}</STOCKITEMNAME>"
                     f"<ISDEEMEDPOSITIVE>{pos}</ISDEEMEDPOSITIVE><RATE>{i.rate.quantize(Q)}/{escape(i.uom)}</RATE>"
                     f"<AMOUNT>{a}</AMOUNT><ACTUALQTY>{escape(qty)}</ACTUALQTY>"
                     f"<BILLEDQTY>{escape(qty)}</BILLEDQTY>"
                     f"<BATCHALLOCATIONS.LIST><GODOWNNAME>{escape(i.godown)}</GODOWNNAME>"
                     f"<BATCHNAME>Primary Batch</BATCHNAME><AMOUNT>{a}</AMOUNT>"
                     f"<ACTUALQTY>{escape(qty)}</ACTUALQTY><BILLEDQTY>{escape(qty)}</BILLEDQTY></BATCHALLOCATIONS.LIST>"
                     f"<ACCOUNTINGALLOCATIONS.LIST><LEDGERNAME>{escape(i.purchase_ledger)}</LEDGERNAME>"
                     f"<ISDEEMEDPOSITIVE>{pos}</ISDEEMEDPOSITIVE><AMOUNT>{a}</AMOUNT>"
                     f"</ACCOUNTINGALLOCATIONS.LIST></ALLINVENTORYENTRIES.LIST>")
        body += "".join(_ledger_entry(l, "LEDGERENTRIES.LIST") for l in v.lines)
    else:
        body += "".join(_ledger_entry(l, "ALLLEDGERENTRIES.LIST") for l in v.lines)
    return head + body + "</VOUCHER>"
