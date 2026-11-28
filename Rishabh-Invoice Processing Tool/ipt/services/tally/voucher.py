"""Builds a TallyPrime purchase voucher (XML) from an approved IPT invoice.

The structure mirrors the user's own purchase vouchers exported from Tally:
Item Invoice mode, ALLINVENTORYENTRIES with batch (godown) and accounting
allocations, party credit with a New Ref bill, input tax ledgers and a
round-off ledger. Debits are negative with ISDEEMEDPOSITIVE=Yes; credits are
positive with ISDEEMEDPOSITIVE=No; all AMOUNTs must sum to exactly 0.00.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from ipt.core.states import state_name
from ipt.db.models import Company, Invoice
from ipt.services.tally.client import esc
from ipt.services.tally.mapping import norm_desc

TWO = Decimal("0.01")
MAX_AUTO_ROUND_OFF = Decimal("1.00")


@dataclass
class Line:
    ledger: str
    amount: Decimal          # positive = debit, negative = credit (accounting sense)
    note: str = ""


@dataclass
class BuiltVoucher:
    xml: str = ""
    lines: list[Line] = field(default_factory=list)
    inventory: list[dict] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    debit: Decimal = Decimal(0)
    credit: Decimal = Decimal(0)

    @property
    def ok(self) -> bool:
        return not self.blockers and self.debit == self.credit and self.debit > 0


def _d(v) -> Decimal:
    return Decimal(v or 0).quantize(TWO, rounding=ROUND_HALF_UP)


def _qty(q: Decimal, unit: str) -> str:
    return f" {Decimal(q).normalize():f} {unit}".rstrip()


def build_purchase(inv: Invoice, company: Company, mapping: dict, missing: list[str],
                   mode: str = "inventory", unit_of: dict[str, str] | None = None,
                   against: str | None = None) -> BuiltVoucher:
    """Purchase voucher for a tax invoice / bill of supply / supplier debit note; for a supplier CREDIT note
    the same entries reversed (party Dr, purchase and input tax Cr) in a Debit Note voucher. 'against' is the
    original bill's name in Tally for a note, if that bill is known to be there."""
    out = BuiltVoucher()
    sign = Decimal(-1) if inv.doc_type == "credit_note" else Decimal(1)
    unit_of = unit_of or {}
    b = out.blockers
    # ---------------------------------------------------------------- pre-checks
    if inv.status != "approved":
        b.append("Invoice is not approved yet (approve it in Processed Invoices)")
    if inv.doc_type in ("credit_note", "debit_note") and mode == "inventory":
        b.append("Credit / debit notes are imported without items (Accounting mode)")
    if inv.reverse_charge:
        b.append("Reverse-charge invoices cannot be imported yet – enter them in Tally manually")
    if (inv.currency or "INR") != "INR":
        b.append("Foreign-currency invoices cannot be imported yet")
    for f, label in (("invoice_no", "Invoice number"), ("invoice_date", "Invoice date"),
                     ("invoice_total", "Invoice total"), ("taxable_total", "Taxable value")):
        if getattr(inv, f) in (None, ""):
            b.append(f"{label} is missing")
    b += [f"Not mapped – {m}" for m in missing]
    if mode == "inventory":
        for it in inv.items:
            if it.qty in (None, 0) or it.taxable_value is None:
                b.append(f"Line {it.line_no}: quantity and taxable value are needed for an inventory voucher")
    if b and any(x.endswith("is missing") for x in b):
        return out

    party = mapping.get("party")
    total = _d(inv.invoice_total)
    taxable = _d(inv.taxable_total)
    taxes = {h: _d(getattr(inv, a)) for h, a in (("CGST", "cgst"), ("SGST", "sgst"), ("IGST", "igst"),
                                                 ("CESS", "cess")) if getattr(inv, a)}
    charges = {k: _d(getattr(inv, k)) for k in ("freight", "packing", "other_charges") if getattr(inv, k)}

    # ---------------------------------------------------------------- debit side
    purchase_ledger = mapping.get("purchase_ledger")
    if mode == "inventory":
        items_total = sum((_d(it.taxable_value) for it in inv.items), Decimal(0))
        if items_total != taxable:
            b.append(f"Items add up to {items_total} but taxable value is {taxable}")
        for it in inv.items:
            item_name = mapping["stock_item"].get(norm_desc(it.description))
            if not (item_name or "").strip() and not (it.description or "").strip():   # named items: 'Not mapped'
                b.append(f"Line {it.line_no}: no Tally stock item for '{it.description or '(no description)'}' – "
                         "add a description and map it in Master Mapping (or book this supplier to a ledger)")
            unit = unit_of.get(item_name or "", "") or (it.unit or "")
            amt = _d(it.taxable_value)
            rate = (amt / Decimal(it.qty)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if it.qty else Decimal(0)
            out.inventory.append({"item": item_name, "qty": Decimal(it.qty or 0), "unit": unit, "rate": rate,
                                  "amount": amt, "ledger": purchase_ledger})
        out.lines.append(Line(purchase_ledger or "?", taxable, "via stock items"))
    else:
        out.lines.append(Line(purchase_ledger or "?", taxable))
    for h, v in taxes.items():
        out.lines.append(Line(mapping["tax_ledger"].get(h, "?"), v, h))
    for k, v in charges.items():
        out.lines.append(Line(mapping["charge_ledger"].get(k, "?"), v, k))
    debit_before_round = sum((ln.amount for ln in out.lines), Decimal(0))
    diff = total - debit_before_round
    if sign < 0:                       # credit note: everything on the other side
        for ln in out.lines:
            ln.amount = -ln.amount
        diff = -diff
    if diff:
        if abs(diff) > MAX_AUTO_ROUND_OFF:
            b.append(f"Total {total} differs from taxable + tax + charges ({debit_before_round}) by {diff}; "
                     f"fix the invoice before importing")
        elif not mapping.get("round_off"):
            b.append("Not mapped – Round-off ledger (needed for the difference of " + str(abs(diff)) + ")")
        else:
            out.lines.append(Line(mapping["round_off"], diff, "round off"))
    out.lines.append(Line(party or "?", -total * sign, "party"))
    out.debit = sum((ln.amount for ln in out.lines if ln.amount > 0), Decimal(0))
    out.credit = -sum((ln.amount for ln in out.lines if ln.amount < 0), Decimal(0))
    if out.debit != out.credit:
        b.append(f"Voucher does not balance (Dr {out.debit} / Cr {out.credit})")
    if b:
        return out
    out.xml = _xml(inv, company, mapping, out, mode, against)
    return out


def _ledger_entry(name: str, amount: Decimal, party: bool = False, bill: str | None = None,
                  round_off: bool = False, bill_type: str = "New Ref") -> str:
    # Tally sign: debit -> negative, ISDEEMEDPOSITIVE Yes; credit -> positive, No
    tally_amt = -amount
    deemed = "Yes" if amount > 0 else "No"
    x = (f"<LEDGERENTRIES.LIST><LEDGERNAME>{esc(name)}</LEDGERNAME><ISDEEMEDPOSITIVE>{deemed}</ISDEEMEDPOSITIVE>"
         f"<ISPARTYLEDGER>{'Yes' if party else 'No'}</ISPARTYLEDGER>"
         + ("<ROUNDTYPE>Normal Rounding</ROUNDTYPE>" if round_off else "")
         + f"<AMOUNT>{tally_amt:.2f}</AMOUNT>")
    if bill:
        x += (f"<BILLALLOCATIONS.LIST><NAME>{esc(bill)}</NAME><BILLTYPE>{bill_type}</BILLTYPE>"
              f"<AMOUNT>{tally_amt:.2f}</AMOUNT></BILLALLOCATIONS.LIST>")
    return x + "</LEDGERENTRIES.LIST>"


def _xml(inv: Invoice, company: Company, mapping: dict, v: BuiltVoucher, mode: str,
         against: str | None = None) -> str:
    date = inv.invoice_date.strftime("%Y%m%d")
    party = mapping["party"]
    vtype = mapping.get("voucher_type") or "Purchase"
    pos = state_name(inv.place_of_supply) if inv.place_of_supply else ""
    sup_state = state_name((inv.supplier_gstin or "")[:2] or inv.supplier_state_code)
    cmp_state = state_name((company.gstin or "")[:2] or company.state_code)
    head = (f'<VOUCHER VCHTYPE="{esc(vtype)}" ACTION="Create" OBJVIEW="Invoice Voucher View">'
            f"<DATE>{date}</DATE><REFERENCEDATE>{date}</REFERENCEDATE><EFFECTIVEDATE>{date}</EFFECTIVEDATE>"
            f"<VOUCHERTYPENAME>{esc(vtype)}</VOUCHERTYPENAME><VOUCHERNUMBER>{esc(inv.invoice_no)}</VOUCHERNUMBER>"
            f"<REFERENCE>{esc(inv.invoice_no)}</REFERENCE>"
            f"<PARTYLEDGERNAME>{esc(party)}</PARTYLEDGERNAME><PARTYNAME>{esc(party)}</PARTYNAME>"
            f"<BASICBASEPARTYNAME>{esc(party)}</BASICBASEPARTYNAME><PARTYMAILINGNAME>{esc(party)}</PARTYMAILINGNAME>"
            + (f"<PARTYGSTIN>{inv.supplier_gstin}</PARTYGSTIN><GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>"
               if inv.supplier_gstin else "<GSTREGISTRATIONTYPE>Unregistered/Consumer</GSTREGISTRATIONTYPE>")
            + (f"<STATENAME>{esc(sup_state)}</STATENAME>" if sup_state else "")
            + "<COUNTRYOFRESIDENCE>India</COUNTRYOFRESIDENCE>"
            + (f"<PLACEOFSUPPLY>{esc(pos)}</PLACEOFSUPPLY>" if pos else "")
            + (f"<CONSIGNEESTATENAME>{esc(cmp_state)}</CONSIGNEESTATENAME>"
               "<CONSIGNEECOUNTRYNAME>India</CONSIGNEECOUNTRYNAME>" if cmp_state else "")
            + (f"<CMPGSTIN>{company.gstin}</CMPGSTIN><CMPGSTREGISTRATIONTYPE>Regular</CMPGSTREGISTRATIONTYPE>"
               if company.gstin else "")
            + (f"<CMPGSTSTATE>{esc(cmp_state)}</CMPGSTSTATE>" if cmp_state else "")
            + f"<BASICBUYERNAME>{esc(company.tally_company_name or company.name)}</BASICBUYERNAME>"
            "<PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>"
            f"<VCHENTRYMODE>{'Item Invoice' if mode == 'inventory' else 'Accounting Invoice'}</VCHENTRYMODE>"
            "<ISINVOICE>Yes</ISINVOICE><ISREVERSECHARGEAPPLICABLE>No</ISREVERSECHARGEAPPLICABLE>"
            f"<NARRATION>{esc(_narration(inv))}</NARRATION>")
    body = ""
    godown = mapping.get("godown") or "Main Location"
    if mode == "inventory":
        for it in v.inventory:
            amt = -it["amount"]
            qty = _qty(it["qty"], it["unit"])
            body += (f"<ALLINVENTORYENTRIES.LIST><STOCKITEMNAME>{esc(it['item'])}</STOCKITEMNAME>"
                     "<ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>"
                     f"<RATE>{it['rate']:.2f}/{esc(it['unit'])}</RATE><AMOUNT>{amt:.2f}</AMOUNT>"
                     f"<ACTUALQTY>{qty}</ACTUALQTY><BILLEDQTY>{qty}</BILLEDQTY>"
                     f"<BATCHALLOCATIONS.LIST><GODOWNNAME>{esc(godown)}</GODOWNNAME><BATCHNAME>Primary Batch</BATCHNAME>"
                     f"<AMOUNT>{amt:.2f}</AMOUNT><ACTUALQTY>{qty}</ACTUALQTY><BILLEDQTY>{qty}</BILLEDQTY>"
                     "</BATCHALLOCATIONS.LIST>"
                     f"<ACCOUNTINGALLOCATIONS.LIST><LEDGERNAME>{esc(it['ledger'])}</LEDGERNAME>"
                     f"<ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>{amt:.2f}</AMOUNT>"
                     "</ACCOUNTINGALLOCATIONS.LIST></ALLINVENTORYENTRIES.LIST>")
    # Tally's invoice view treats the FIRST ledger entry as the party (as in the user's own vouchers):
    # party, then taxes, charges and round off. Sending the party last hides the first tax ledger.
    ordered = [ln for ln in v.lines if ln.note == "party"] + [ln for ln in v.lines if ln.note != "party"]
    for ln in ordered:
        if ln.note == "via stock items":
            continue
        is_party = ln.note == "party"
        body += _ledger_entry(ln.ledger, ln.amount, party=is_party,
                              bill=(against or inv.invoice_no) if is_party else None,
                              bill_type="Agst Ref" if against else "New Ref",
                              round_off=(ln.note == "round off"))
    voucher = head + body + "</VOUCHER>"
    return ("<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC>"
            "<REPORTNAME>Vouchers</REPORTNAME><STATICVARIABLES>"
            f"<SVCURRENTCOMPANY>{esc(company.tally_company_name)}</SVCURRENTCOMPANY></STATICVARIABLES>"
            "</REQUESTDESC><REQUESTDATA><TALLYMESSAGE xmlns:UDF=\"TallyUDF\">" + voucher +
            "</TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>")


def _narration(inv: Invoice) -> str:
    kind = {"credit_note": "Supplier credit note", "debit_note": "Supplier debit note"}.get(inv.doc_type,
                                                                                          "Supplier inv")
    orig = f" against inv {inv.original_invoice_ref}" if inv.original_invoice_ref and inv.doc_type in (
        "credit_note", "debit_note") else ""
    return f"Imported by IPT | {kind} {inv.invoice_no} dt {inv.invoice_date:%d-%m-%Y}{orig} | IPT #{inv.id}"


def amounts_sum_zero(xml: str) -> bool:
    """Safety net: the top-level AMOUNTs (party, ledgers, inventory) must add up to exactly 0.00."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml)
    total = Decimal(0)
    for v in root.iter("VOUCHER"):
        for le in v.findall("LEDGERENTRIES.LIST"):
            total += Decimal(le.findtext("AMOUNT"))
        for ie in v.findall("ALLINVENTORYENTRIES.LIST"):
            total += Decimal(ie.findtext("AMOUNT"))
    return total == 0
