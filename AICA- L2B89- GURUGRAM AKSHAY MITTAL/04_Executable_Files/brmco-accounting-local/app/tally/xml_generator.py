"""Tally adapter: Voucher objects -> TallyPrime import XML.

One builder class per voucher category, registered by ``VoucherKind``. If a Tally
release changes a tag, only the relevant builder changes; nothing upstream
(Excel, accounting engine, validation) is affected.

Tally sign convention used throughout:
    Debit  -> ISDEEMEDPOSITIVE = Yes, AMOUNT negative
    Credit -> ISDEEMEDPOSITIVE = No,  AMOUNT positive
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from abc import ABC
from datetime import date
from decimal import Decimal

from app.accounting.models import InventoryLine, LedgerPosting, Side, Voucher, VoucherKind, q2
from app.config.settings import AppConfig


def tally_date(d: date) -> str:
    return d.strftime("%Y%m%d")


def tally_amount(side: Side, amount: Decimal) -> str:
    value = q2(amount)
    return f"{-value if side == Side.DR else value:.2f}"


def yes_no(flag: bool) -> str:
    return "Yes" if flag else "No"


def _sub(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = text
    return el


def _qty(q: Decimal) -> str:
    return format(q.normalize(), "f")


class VoucherXmlBuilder(ABC):
    kind: VoucherKind
    view = "Accounting Voucher View"
    ledger_tag = "ALLLEDGERENTRIES.LIST"

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    # ---- template method ------------------------------------------------------
    def build(self, v: Voucher) -> ET.Element:
        vch_type = self.config.voucher_type_for(v.kind)
        view, ledger_tag = self._view(v)
        el = ET.Element("VOUCHER", {"VCHTYPE": vch_type, "ACTION": "Create", "OBJVIEW": view})
        _sub(el, "DATE", tally_date(v.date))
        _sub(el, "EFFECTIVEDATE", tally_date(v.date))
        _sub(el, "VOUCHERTYPENAME", vch_type)
        if v.voucher_number:
            _sub(el, "VOUCHERNUMBER", v.voucher_number)
        if v.reference:
            _sub(el, "REFERENCE", v.reference)
        if v.reference_date:
            _sub(el, "REFERENCEDATE", tally_date(v.reference_date))
        self.add_header(el, v)
        _sub(el, "NARRATION", v.narration or "")
        _sub(el, "PERSISTEDVIEW", view)
        _sub(el, "ISINVOICE", yes_no(view == "Invoice Voucher View"))
        for inv in v.inventory:
            self.add_inventory(el, inv)
        for p in v.postings:
            self.add_ledger(el, ledger_tag, p, v)
        return el

    def _view(self, v: Voucher) -> tuple[str, str]:
        return self.view, self.ledger_tag

    # ---- hooks ------------------------------------------------------------------
    def add_header(self, el: ET.Element, v: Voucher) -> None:
        if v.party_ledger:
            _sub(el, "PARTYLEDGERNAME", v.party_ledger)

    def add_ledger(self, parent: ET.Element, tag: str, p: LedgerPosting, v: Voucher) -> ET.Element:
        entry = _sub(parent, tag)
        _sub(entry, "LEDGERNAME", p.ledger)
        _sub(entry, "ISDEEMEDPOSITIVE", yes_no(p.side == Side.DR))
        _sub(entry, "ISPARTYLEDGER", yes_no(p.is_party))
        amount = tally_amount(p.side, p.amount)
        _sub(entry, "AMOUNT", amount)
        if p.bill_type in ("New Ref", "Agst Ref") and p.bill_name:
            bill = _sub(entry, "BILLALLOCATIONS.LIST")
            _sub(bill, "NAME", p.bill_name)
            _sub(bill, "BILLTYPE", p.bill_type)
            _sub(bill, "AMOUNT", amount)
        if p.cost_centre:
            cat = _sub(entry, "CATEGORYALLOCATIONS.LIST")
            _sub(cat, "CATEGORY", self.config.cost_category)
            _sub(cat, "ISDEEMEDPOSITIVE", yes_no(p.side == Side.DR))
            cc = _sub(cat, "COSTCENTREALLOCATIONS.LIST")
            _sub(cc, "NAME", p.cost_centre)
            _sub(cc, "AMOUNT", amount)
        return entry

    def add_inventory(self, parent: ET.Element, inv: InventoryLine) -> None:
        entry = _sub(parent, "ALLINVENTORYENTRIES.LIST")
        _sub(entry, "STOCKITEMNAME", inv.stock_item)
        _sub(entry, "ISDEEMEDPOSITIVE", yes_no(inv.side == Side.DR))
        # With a discount, post the effective rate so Qty x Rate = Amount in Tally.
        rate = inv.rate if not inv.discount or not inv.quantity else (inv.amount / inv.quantity)
        _sub(entry, "RATE", f"{q2(rate):.2f}/{inv.unit}")
        _sub(entry, "AMOUNT", tally_amount(inv.side, inv.amount))
        _sub(entry, "ACTUALQTY", f" {_qty(inv.quantity)} {inv.unit}")
        _sub(entry, "BILLEDQTY", f" {_qty(inv.quantity)} {inv.unit}")
        alloc = _sub(entry, "ACCOUNTINGALLOCATIONS.LIST")
        _sub(alloc, "LEDGERNAME", inv.ledger)
        _sub(alloc, "ISDEEMEDPOSITIVE", yes_no(inv.side == Side.DR))
        _sub(alloc, "AMOUNT", tally_amount(inv.side, inv.amount))


class _InvoiceXmlBuilder(VoucherXmlBuilder):
    def _view(self, v: Voucher) -> tuple[str, str]:
        if v.inventory:
            return "Invoice Voucher View", "LEDGERENTRIES.LIST"
        return "Accounting Voucher View", "ALLLEDGERENTRIES.LIST"

    def add_header(self, el: ET.Element, v: Voucher) -> None:
        super().add_header(el, v)
        if v.party_ledger:
            _sub(el, "PARTYNAME", v.party_ledger)
        if v.party_gstin:
            _sub(el, "PARTYGSTIN", v.party_gstin)
        if v.party_state:
            _sub(el, "STATENAME", v.party_state)
        _sub(el, "COUNTRYOFRESIDENCE", "India")
        if v.place_of_supply:
            _sub(el, "PLACEOFSUPPLY", v.place_of_supply)
        if v.reverse_charge:
            _sub(el, "ISREVERSECHARGEAPPLICABLE", "Yes")


class SalesXmlBuilder(_InvoiceXmlBuilder):
    kind = VoucherKind.SALES


class PurchaseXmlBuilder(_InvoiceXmlBuilder):
    kind = VoucherKind.PURCHASE


class JournalXmlBuilder(VoucherXmlBuilder):
    kind = VoucherKind.JOURNAL

    def add_header(self, el: ET.Element, v: Voucher) -> None:
        pass  # journals have no party


class _BankXmlBuilder(VoucherXmlBuilder):
    def add_ledger(self, parent: ET.Element, tag: str, p: LedgerPosting, v: Voucher) -> ET.Element:
        entry = super().add_ledger(parent, tag, p, v)
        if p.role == "bank" and p.instrument_number:
            bank = _sub(entry, "BANKALLOCATIONS.LIST")
            _sub(bank, "DATE", tally_date(v.date))
            _sub(bank, "INSTRUMENTDATE", tally_date(p.instrument_date or v.date))
            _sub(bank, "TRANSACTIONTYPE", "Others")
            _sub(bank, "PAYMENTFAVOURING", v.party_ledger or "")
            _sub(bank, "INSTRUMENTNUMBER", p.instrument_number)
            _sub(bank, "BANKPARTYNAME", v.party_ledger or "")
            _sub(bank, "AMOUNT", tally_amount(p.side, p.amount))
        return entry


class ReceiptXmlBuilder(_BankXmlBuilder):
    kind = VoucherKind.RECEIPT


class PaymentXmlBuilder(_BankXmlBuilder):
    kind = VoucherKind.PAYMENT


BUILDERS: dict[VoucherKind, type[VoucherXmlBuilder]] = {
    b.kind: b for b in (SalesXmlBuilder, PurchaseXmlBuilder, JournalXmlBuilder, ReceiptXmlBuilder, PaymentXmlBuilder)
}


class TallyXmlGenerator:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def voucher_element(self, v: Voucher) -> ET.Element:
        return BUILDERS[v.kind](self.config).build(v)

    def import_envelope(self, vouchers: list[Voucher]) -> bytes:
        env = ET.Element("ENVELOPE")
        header = _sub(env, "HEADER")
        _sub(header, "TALLYREQUEST", "Import Data")
        body = _sub(env, "BODY")
        imp = _sub(body, "IMPORTDATA")
        desc = _sub(imp, "REQUESTDESC")
        _sub(desc, "REPORTNAME", "Vouchers")
        if self.config.tally_company_name:
            static = _sub(desc, "STATICVARIABLES")
            _sub(static, "SVCURRENTCOMPANY", self.config.tally_company_name)
        data = _sub(imp, "REQUESTDATA")
        for v in vouchers:
            msg = _sub(data, "TALLYMESSAGE", None)
            msg.set("xmlns:UDF", "TallyUDF")
            msg.append(self.voucher_element(v))
        ET.indent(env, space=" ")
        return ET.tostring(env, encoding="utf-8")
