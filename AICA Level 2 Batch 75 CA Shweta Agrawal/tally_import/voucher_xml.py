"""
Builds Tally <VOUCHER> XML fragments for each voucher type used by this tool.
Amounts follow Tally convention inside ALLLEDGERENTRIES.LIST: debit = positive
in DR party context is represented via ISDEEMEDPOSITIVE; we always set the
amount sign explicitly per leg (negative = debit-side outflow from that ledger,
positive = credit-side inflow) as Tally's importer expects.
"""
from __future__ import annotations

import datetime as dt
from xml.sax.saxutils import escape


def _tdate(d: dt.date) -> str:
    return d.strftime("%Y%m%d")


def _ledger_entry(ledger_name: str, amount: float, is_deemed_positive: bool, is_party_ledger: bool = False, bill_ref: str | None = None) -> str:
    """is_deemed_positive marks which side this leg represents for THIS voucher
    (True = debit/Dr, False = credit/Cr). Tally's XML convention requires AMOUNT
    itself to be negative for a debit and positive for a credit -- the sign is
    enforced here from is_deemed_positive regardless of what magnitude/sign the
    caller passed in, so callers can just supply a plain magnitude.
    is_party_ledger sets ISPARTYLEDGER, required on the party leg for Invoice
    Voucher View postings (verified against a real Tally-created invoice-mode
    voucher's exported XML) -- harmless to include on plain Voucher-mode
    postings too, so every caller can set it consistently.
    bill_ref, when given, adds a "New Ref" BILLALLOCATIONS.LIST entry -- required
    on the party leg for Invoice Voucher View imports against a bill-wise-on
    party ledger (also confirmed against the same real export; plain Voucher
    mode posts fine without it)."""
    magnitude = abs(amount)
    signed_amount = -magnitude if is_deemed_positive else magnitude
    bill_xml = ""
    if bill_ref:
        bill_xml = f"""
    <BILLALLOCATIONS.LIST>
      <NAME>{escape(bill_ref)}</NAME>
      <BILLTYPE>New Ref</BILLTYPE>
      <AMOUNT>{signed_amount:.2f}</AMOUNT>
    </BILLALLOCATIONS.LIST>
        """
    return f"""
    <ALLLEDGERENTRIES.LIST>
      <LEDGERNAME>{escape(ledger_name)}</LEDGERNAME>
      <ISDEEMEDPOSITIVE>{"Yes" if is_deemed_positive else "No"}</ISDEEMEDPOSITIVE>
      <ISPARTYLEDGER>{"Yes" if is_party_ledger else "No"}</ISPARTYLEDGER>
      <AMOUNT>{signed_amount:.2f}</AMOUNT>
      {bill_xml}
    </ALLLEDGERENTRIES.LIST>
    """


def _voucher_shell(
    voucher_type: str,
    date: dt.date,
    narration: str,
    ledger_entries_xml: str,
    voucher_number: str | None = None,
    reference: str | None = None,
) -> str:
    vn = f"<VOUCHERNUMBER>{escape(voucher_number)}</VOUCHERNUMBER>" if voucher_number else ""
    ref = f"<REFERENCE>{escape(reference)}</REFERENCE>" if reference else ""
    return f"""
    <VOUCHER VCHTYPE="{escape(voucher_type)}" ACTION="Create">
      <DATE>{_tdate(date)}</DATE>
      <VOUCHERTYPENAME>{escape(voucher_type)}</VOUCHERTYPENAME>
      {vn}
      {ref}
      <NARRATION>{escape(narration or "")}</NARRATION>
      {ledger_entries_xml}
    </VOUCHER>
    """


def payment_voucher(date: dt.date, bank_ledger: str, contra_ledger: str, amount: float, narration: str, ref: str | None = None) -> str:
    """Money paid out of the bank ledger to contra_ledger."""
    entries = (
        _ledger_entry(contra_ledger, amount, True, is_party_ledger=True)   # debit: money going to contra party
        + _ledger_entry(bank_ledger, -amount, False)  # credit: bank reduces
    )
    return _voucher_shell("Payment", date, narration, entries, reference=ref)


def receipt_voucher(date: dt.date, bank_ledger: str, contra_ledger: str, amount: float, narration: str, ref: str | None = None) -> str:
    """Money received into the bank ledger from contra_ledger."""
    entries = (
        _ledger_entry(bank_ledger, amount, True)      # debit: bank increases
        + _ledger_entry(contra_ledger, -amount, False, is_party_ledger=True)  # credit: contra party
    )
    return _voucher_shell("Receipt", date, narration, entries, reference=ref)


def contra_voucher(date: dt.date, from_ledger: str, to_ledger: str, amount: float, narration: str, ref: str | None = None) -> str:
    """Transfer between two bank/cash ledgers."""
    entries = (
        _ledger_entry(to_ledger, amount, True)
        + _ledger_entry(from_ledger, -amount, False)
    )
    return _voucher_shell("Contra", date, narration, entries, reference=ref)


def journal_voucher(date: dt.date, debit_ledger: str, credit_ledger: str, amount: float, narration: str) -> str:
    entries = (
        _ledger_entry(debit_ledger, amount, True)
        + _ledger_entry(credit_ledger, -amount, False)
    )
    return _voucher_shell("Journal", date, narration, entries)


def purchase_voucher(
    date: dt.date,
    supplier_ledger: str,
    purchase_ledger: str,
    taxable_value: float,
    tax_legs: list[tuple[str, float]],
    narration: str,
    ref: str | None = None,
    voucher_type: str = "Purchase",
) -> str:
    """One Purchase-type voucher: Dr expense/purchase/asset ledger + tax, Cr supplier
    (party payable). voucher_type lets the caller post under a custom Tally Voucher
    Type (e.g. 'Indirect Expense', 'Capital Asset') based on the Purchase base type,
    instead of always posting under the plain 'Purchase' type."""
    total = taxable_value + sum(amt for _, amt in tax_legs)
    entries = _ledger_entry(purchase_ledger, taxable_value, True)
    for tax_ledger, amt in tax_legs:
        entries += _ledger_entry(tax_ledger, amt, True)
    entries += _ledger_entry(supplier_ledger, -total, False, is_party_ledger=True)
    return _voucher_shell(voucher_type, date, narration, entries, reference=ref)


def _invoice_shell(
    voucher_type: str,
    date: dt.date,
    narration: str,
    party_ledger: str,
    ledger_entries_xml: str,
    voucher_number: str | None = None,
    reference: str | None = None,
) -> str:
    """Accounting Invoice mode -- verified field-by-field against a real
    invoice-mode Sales voucher's exported XML from this Tally installation.
    Differs from _voucher_shell (plain "As Voucher" mode) by OBJVIEW/
    PERSISTEDVIEW/VCHENTRYMODE/ISINVOICE/PARTYLEDGERNAME; the ledger-entries
    structure and Dr/Cr sign convention are otherwise identical."""
    vn = f"<VOUCHERNUMBER>{escape(voucher_number)}</VOUCHERNUMBER>" if voucher_number else ""
    ref = f"<REFERENCE>{escape(reference)}</REFERENCE>" if reference else ""
    return f"""
    <VOUCHER VCHTYPE="{escape(voucher_type)}" ACTION="Create" OBJVIEW="Invoice Voucher View">
      <DATE>{_tdate(date)}</DATE>
      <VOUCHERTYPENAME>{escape(voucher_type)}</VOUCHERTYPENAME>
      <PARTYLEDGERNAME>{escape(party_ledger)}</PARTYLEDGERNAME>
      <PARTYNAME>{escape(party_ledger)}</PARTYNAME>
      <BASICBUYERNAME>{escape(party_ledger)}</BASICBUYERNAME>
      <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
      <VCHENTRYMODE>Accounting Invoice</VCHENTRYMODE>
      <ISINVOICE>Yes</ISINVOICE>
      {vn}
      {ref}
      <NARRATION>{escape(narration or "")}</NARRATION>
      {ledger_entries_xml}
    </VOUCHER>
    """


def purchase_voucher_invoice_mode(
    date: dt.date,
    supplier_ledger: str,
    purchase_ledger: str,
    taxable_value: float,
    tax_legs: list[tuple[str, float]],
    narration: str,
    ref: str | None = None,
    voucher_type: str = "Purchase",
) -> str:
    """Same Dr/Cr ledger effect as purchase_voucher(), posted in Tally's
    Accounting Invoice entry mode instead of plain Voucher mode."""
    total = taxable_value + sum(amt for _, amt in tax_legs)
    entries = _ledger_entry(purchase_ledger, taxable_value, True)
    for tax_ledger, amt in tax_legs:
        entries += _ledger_entry(tax_ledger, amt, True)
    bill_ref = ref or f"{voucher_type}-{_tdate(date)}"
    entries += _ledger_entry(supplier_ledger, -total, False, is_party_ledger=True, bill_ref=bill_ref)
    return _invoice_shell(voucher_type, date, narration, supplier_ledger, entries, reference=ref)


def sales_voucher(
    date: dt.date,
    customer_ledger: str,
    sales_ledger: str,
    taxable_value: float,
    tax_legs: list[tuple[str, float]],
    narration: str,
    ref: str | None = None,
) -> str:
    """One Sales voucher: Dr customer (receivable), Cr sales + tax."""
    total = taxable_value + sum(amt for _, amt in tax_legs)
    entries = _ledger_entry(customer_ledger, total, True, is_party_ledger=True)
    entries += _ledger_entry(sales_ledger, -taxable_value, False)
    for tax_ledger, amt in tax_legs:
        entries += _ledger_entry(tax_ledger, -amt, False)
    return _voucher_shell("Sales", date, narration, entries, reference=ref)


def sales_voucher_invoice_mode(
    date: dt.date,
    customer_ledger: str,
    sales_ledger: str,
    taxable_value: float,
    tax_legs: list[tuple[str, float]],
    narration: str,
    ref: str | None = None,
) -> str:
    """Same Dr/Cr ledger effect as sales_voucher(), posted in Tally's
    Accounting Invoice entry mode instead of plain Voucher mode."""
    total = taxable_value + sum(amt for _, amt in tax_legs)
    bill_ref = ref or f"Sales-{_tdate(date)}"
    entries = _ledger_entry(customer_ledger, total, True, is_party_ledger=True, bill_ref=bill_ref)
    entries += _ledger_entry(sales_ledger, -taxable_value, False)
    for tax_ledger, amt in tax_legs:
        entries += _ledger_entry(tax_ledger, -amt, False)
    return _invoice_shell("Sales", date, narration, customer_ledger, entries, reference=ref)
