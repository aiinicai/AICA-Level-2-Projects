"""Accounting engine: turns parsed input rows into balanced Voucher objects.

This module owns the double-entry logic for each voucher category:

    Sales     Party Dr  / Sales (or stock) Cr, Output GST Cr, Round Off Dr|Cr
    Purchase  Purchase (or stock) Dr, Input GST Dr, Round Off Dr|Cr / Supplier Cr
    Journal   as entered (each row Dr or Cr)
    Receipt   Bank Dr  / Party Cr
    Payment   Party/Expense Dr / Bank Cr

It is input-agnostic: it only needs ``ParsedRow``-like objects (``row`` + ``get``),
so future inputs (AI-extracted invoices, APIs) can reuse it unchanged.
"""
from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal
from typing import Any, Protocol

from app.accounting.gst import state_from_gstin
from app.accounting.models import (
    ZERO, InventoryLine, InvoiceLine, LedgerPosting, Side, ValidationIssue, Voucher, VoucherKind, q2,
)
from app.config.settings import AppConfig
from app.excel.template_spec import TemplateSpec


class RowLike(Protocol):
    row: int

    def get(self, key: str, default: Any = None) -> Any: ...


class MasterLookup(Protocol):
    def has(self, master_type: str) -> bool: ...
    def resolve(self, master_type: str, name: str) -> str | None: ...
    def get(self, master_type: str, name: str) -> dict[str, Any] | None: ...
    def is_under_group(self, ledger: str, groups: set[str]) -> bool | None: ...


class _Issues:
    def __init__(self) -> None:
        self.items: list[ValidationIssue] = []

    def error(self, message: str, row: int | None = None, column: str | None = None,
              voucher: str | None = None, code: str = "") -> None:
        self.items.append(ValidationIssue(severity="error", message=message, row=row, column=column,
                                          voucher=voucher, code=code))

    def warning(self, message: str, row: int | None = None, column: str | None = None,
                voucher: str | None = None, code: str = "") -> None:
        self.items.append(ValidationIssue(severity="warning", message=message, row=row, column=column,
                                          voucher=voucher, code=code))


class VoucherAssembler:
    def __init__(self, spec: TemplateSpec, config: AppConfig, masters: MasterLookup) -> None:
        self.spec = spec
        self.config = config
        self.masters = masters
        self.issues = _Issues()

    # ------------------------------------------------------------------ public
    def assemble(self, rows: list[RowLike]) -> tuple[list[Voucher], list[ValidationIssue]]:
        vouchers: list[Voucher] = []
        for group in self._group(rows):
            voucher = self._build(group)
            if voucher is not None:
                vouchers.append(voucher)
        return vouchers, self.issues.items

    # ------------------------------------------------------------------ grouping
    def _group(self, rows: list[RowLike]) -> list[list[RowLike]]:
        if not self.spec.group_by:
            return [[r] for r in rows]
        groups: "OrderedDict[tuple, list[RowLike]]" = OrderedDict()
        last_key: tuple | None = None
        for r in rows:
            key_values = [r.get(k) for k in self.spec.group_by]
            if all(v is None for v in key_values) and last_key is not None:
                # continuation row: key columns left blank -> belongs to previous voucher
                groups[last_key].append(r)
                continue
            raw = getattr(r, "raw", None) or {}
            missing = [self.spec.header(k) for k, v in zip(self.spec.group_by, key_values) if v is None]
            unparsed = [k for k, v in zip(self.spec.group_by, key_values) if v is None and raw.get(k) not in (None, "")]
            if missing:
                if not unparsed:  # a cell that failed parsing has already been reported
                    self.issues.error(f"{', '.join(missing)} is required to identify the voucher.", r.row,
                                      missing[0], code="row.required")
                last_key = None
                continue
            key = tuple(str(v).strip().upper() if isinstance(v, str) else v for v in key_values)
            if key in groups and last_key != key:
                self.issues.warning(
                    f"Rows for {' / '.join(str(v) for v in key_values)} are not together; they were combined "
                    f"with row {groups[key][0].row}. Check this is one voucher and not a duplicate.",
                    r.row, self.spec.header(self.spec.group_by[-1]), code="dup.split")
            groups.setdefault(key, []).append(r)
            last_key = key
        return list(groups.values())

    def _voucher_value(self, group: list[RowLike], key: str, label: str) -> Any:
        """Voucher-level value: first non-blank; later rows must match or be blank."""
        value, first_row = None, None
        for r in group:
            v = r.get(key)
            if v is None:
                continue
            if value is None:
                value, first_row = v, r.row
            elif (v.strip().lower() if isinstance(v, str) else v) != \
                    (value.strip().lower() if isinstance(value, str) else value):
                self.issues.error(
                    f'{self.spec.header(key)} "{v}" differs from "{value}" on row {first_row} of the same voucher.',
                    r.row, self.spec.header(key), label, code="row.inconsistent")
        return value

    def _require(self, group: list[RowLike], key: str, label: str) -> Any:
        v = self._voucher_value(group, key, label)
        # A cell that failed parsing is already reported; don't also call it "missing".
        had_raw = any((getattr(r, "raw", None) or {}).get(key) not in (None, "") for r in group)
        if v is None and not had_raw:
            self.issues.error(f"{self.spec.header(key)} is required.", group[0].row, self.spec.header(key), label,
                              code="row.required")
        return v

    # ------------------------------------------------------------------ dispatch
    def _build(self, group: list[RowLike]) -> Voucher | None:
        kind = self.spec.kind
        if kind in (VoucherKind.SALES, VoucherKind.PURCHASE):
            return self._build_invoice(group)
        if kind == VoucherKind.JOURNAL:
            return self._build_journal(group)
        return self._build_bank(group[0])

    # ------------------------------------------------------------------ sales / purchase
    def _build_invoice(self, group: list[RowLike]) -> Voucher | None:
        sales = self.spec.kind == VoucherKind.SALES
        cfg = self.config
        number = self._voucher_value(group, "invoice_number", "")
        label = str(number or f"Row {group[0].row}")
        party_key, gstin_key, state_key, ledger_key = (
            ("customer_ledger", "customer_gstin", "customer_state", "sales_ledger") if sales
            else ("supplier_ledger", "supplier_gstin", "supplier_state", "purchase_ledger"))

        v_date = self._require(group, "voucher_date", label)
        party = self._require(group, party_key, label)
        pos = self._require(group, "place_of_supply", label)
        inv_date = None if sales else self._require(group, "invoice_date", label)
        gstin = self._voucher_value(group, gstin_key, label)
        state = self._voucher_value(group, state_key, label)
        rcm = bool(self._voucher_value(group, "reverse_charge", label) or False)
        round_off = self._voucher_value(group, "round_off", label) or ZERO
        stated_total = self._voucher_value(group, "invoice_total", label)
        narration = self._voucher_value(group, "narration", label) or ""

        if gstin:
            gst_state = state_from_gstin(gstin)
            if state and gst_state and state != gst_state:
                self.issues.error(f'{self.spec.header(state_key)} "{state}" does not match GSTIN state "{gst_state}".',
                                  group[0].row, self.spec.header(state_key), label, code="gst.state")
            state = state or gst_state

        lines: list[InvoiceLine] = []
        for r in group:
            line = self._build_line(r, ledger_key, label)
            if line is not None:
                lines.append(line)
        if v_date is None or party is None or not lines or len(lines) != len(group):
            return None

        voucher = Voucher(
            kind=self.spec.kind, date=v_date,
            voucher_number=str(number) if sales else None,
            reference=None if sales else str(number),
            reference_date=inv_date,
            party_ledger=party, party_gstin=gstin, party_state=state, place_of_supply=pos,
            reverse_charge=rcm, narration=narration, lines=lines, round_off=q2(round_off),
            invoice_total=q2(stated_total) if stated_total is not None else None,
            rows=[r.row for r in group],
        )
        if stated_total is None:
            self.issues.warning(f"Invoice Total not given; computed as {voucher.computed_invoice_total}.",
                                group[0].row, "Invoice Total", label, code="calc.total")
        self._post_invoice(voucher)
        return voucher

    def _build_line(self, r: RowLike, ledger_key: str, label: str) -> InvoiceLine | None:
        tol = self.config.tax_tolerance
        ledger = r.get(ledger_key)
        if ledger is None:
            self.issues.error(f"{self.spec.header(ledger_key)} is required.", r.row, self.spec.header(ledger_key),
                              label, code="row.required")
            return None
        qty, rate = r.get("quantity"), r.get("rate")
        discount = r.get("discount") or ZERO
        taxable = r.get("taxable_value")
        if taxable is None:
            if qty is not None and rate is not None:
                taxable = q2(qty * rate - discount)
                self.issues.warning(f"Taxable Value computed as {taxable} (Quantity x Rate - Discount).",
                                    r.row, "Taxable Value", label, code="calc.taxable")
            else:
                self.issues.error("Taxable Value is required (or enter Quantity and Rate).", r.row,
                                  "Taxable Value", label, code="row.required")
                return None
        elif qty is not None and rate is not None:
            expected = q2(qty * rate - discount)
            if abs(expected - taxable) > tol:
                self.issues.error(f"Taxable Value {taxable} does not match Quantity x Rate - Discount = {expected}.",
                                  r.row, "Taxable Value", label, code="calc.taxable")
        if taxable <= 0:
            self.issues.error("Taxable Value must be greater than zero.", r.row, "Taxable Value", label,
                              code="num.positive")

        amounts: dict[str, Decimal] = {}
        rates: dict[str, Decimal] = {}
        for tax in ("cgst", "sgst", "igst", "cess"):
            t_rate, t_amt = r.get(f"{tax}_rate"), r.get(f"{tax}_amount")
            header = f"{tax.upper() if tax != 'cess' else 'Cess'} Amount"
            if t_amt is None and t_rate:
                t_amt = q2(taxable * t_rate / 100)
                self.issues.warning(f"{header} computed as {t_amt}.", r.row, header, label, code="calc.tax")
            if t_amt and not t_rate:
                self.issues.error(f"{header} is entered but the rate is blank or zero.", r.row,
                                  header.replace("Amount", "Rate"), label, code="gst.rate")
            elif t_amt is not None and t_rate:
                expected = q2(taxable * t_rate / 100)
                if abs(expected - t_amt) > tol:
                    self.issues.error(f"{header} {t_amt} does not match {t_rate.normalize()}% of {taxable} = {expected}.",
                                      r.row, header, label, code="gst.amount")
            amounts[tax] = q2(t_amt or ZERO)
            rates[tax] = t_rate or ZERO

        description = r.get("item_description")
        stock_name = None
        if description and qty and self.masters.has("stock_item"):
            stock_name = self.masters.resolve("stock_item", description)
        itc = r.get("itc_eligibility", "Eligible")

        return InvoiceLine(
            row=r.row, ledger=ledger, description=stock_name or description, hsn=r.get("hsn_sac"),
            quantity=qty, unit=r.get("unit"), rate=rate, discount=discount, taxable_value=q2(taxable),
            cgst_rate=rates["cgst"], cgst_amount=amounts["cgst"], sgst_rate=rates["sgst"], sgst_amount=amounts["sgst"],
            igst_rate=rates["igst"], igst_amount=amounts["igst"], cess_rate=rates["cess"], cess_amount=amounts["cess"],
            itc_eligible=(itc != "Ineligible"), is_stock_item=stock_name is not None,
        )

    def _post_invoice(self, v: Voucher) -> None:
        sales = v.kind == VoucherKind.SALES
        cfg = self.config
        item_side = Side.CR if sales else Side.DR
        ledger_header = "Sales Ledger" if sales else "Purchase/Expense Ledger"
        postings: list[LedgerPosting] = []
        inventory: list[InventoryLine] = []

        by_ledger: "OrderedDict[str, tuple[Decimal, int]]" = OrderedDict()
        for line in v.lines:
            if line.is_stock_item:
                unit = line.unit or (self.masters.get("stock_item", line.description or "") or {}).get("unit") or ""
                inventory.append(InventoryLine(
                    stock_item=line.description or "", ledger=line.ledger, side=item_side,
                    quantity=line.quantity or ZERO, unit=unit, rate=line.rate or ZERO, discount=line.discount,
                    amount=line.taxable_value, hsn=line.hsn, source_row=line.row))
            else:
                amt, row = by_ledger.get(line.ledger, (ZERO, line.row))
                by_ledger[line.ledger] = (amt + line.taxable_value, row)
            if not sales and not line.itc_eligible and line.tax_total:
                amt, row = by_ledger.get(line.ledger, (ZERO, line.row))
                by_ledger[line.ledger] = (amt + line.tax_total, row)

        for ledger, (amount, row) in by_ledger.items():
            postings.append(LedgerPosting(ledger=ledger, side=item_side, amount=q2(amount),
                                          role="income" if sales else "expense",
                                          source_row=row, source_column=ledger_header))

        prefix = "output" if sales else "input"
        for tax in ("cgst", "sgst", "igst", "cess"):
            lines = v.lines if sales else [l for l in v.lines if l.itc_eligible]
            amount = q2(sum((getattr(l, f"{tax}_amount") for l in lines), ZERO))
            if amount:
                field_name = f"{prefix}_{tax}_ledger"
                postings.append(LedgerPosting(
                    ledger=getattr(cfg, field_name), side=item_side, amount=amount, role="tax",
                    source_column=f"Settings: {field_name.replace('_', ' ').title()}"))

        if v.round_off:
            # Positive round-off increases the invoice total.
            ro_side = item_side if v.round_off > 0 else (Side.DR if sales else Side.CR)
            postings.append(LedgerPosting(ledger=cfg.round_off_ledger, side=ro_side, amount=abs(v.round_off),
                                          role="round_off", source_column="Settings: Round Off Ledger"))

        v.postings = postings
        v.inventory = inventory
        # Party balances the voucher.
        diff = q2(v.total_credit - v.total_debit) if sales else q2(v.total_debit - v.total_credit)
        party_side = Side.DR if sales else Side.CR
        v.postings.insert(0, LedgerPosting(
            ledger=v.party_ledger or "", side=party_side, amount=diff, role="party", is_party=True,
            bill_name=v.voucher_number if sales else v.reference, bill_type="New Ref",
            source_row=v.first_row, source_column="Customer Ledger" if sales else "Supplier Ledger"))

    # ------------------------------------------------------------------ journal
    def _build_journal(self, group: list[RowLike]) -> Voucher | None:
        ref = self._voucher_value(group, "reference_number", "")
        label = str(ref or f"Row {group[0].row}")
        v_date = self._require(group, "voucher_date", label)
        narration = self._voucher_value(group, "narration", label) or ""
        postings: list[LedgerPosting] = []
        ok = True
        for r in group:
            ledger, dr, cr = r.get("ledger"), r.get("debit"), r.get("credit")
            if ledger is None:
                self.issues.error("Ledger is required.", r.row, "Ledger", label, code="row.required")
                ok = False
                continue
            dr = dr or ZERO
            cr = cr or ZERO
            if dr and cr:
                self.issues.error("Enter either Debit or Credit on a row, not both.", r.row, "Debit", label,
                                  code="jv.both")
                ok = False
                continue
            if not dr and not cr:
                self.issues.error("Enter a Debit or Credit amount.", r.row, "Debit", label, code="jv.none")
                ok = False
                continue
            postings.append(LedgerPosting(
                ledger=ledger, side=Side.DR if dr else Side.CR, amount=q2(dr or cr), role="journal",
                cost_centre=r.get("cost_centre"), source_row=r.row, source_column="Ledger"))
        if v_date is None or not ok:
            return None
        return Voucher(kind=VoucherKind.JOURNAL, date=v_date, reference=str(ref), narration=narration,
                       postings=postings, rows=[r.row for r in group])

    # ------------------------------------------------------------------ bank
    def _build_bank(self, r: RowLike) -> Voucher | None:
        receipt = self.spec.kind == VoucherKind.RECEIPT
        label = str(r.get("reference_number") or r.get("instrument_number") or f"Row {r.row}")
        party_header = "Party Ledger" if receipt else "Party/Expense Ledger"
        missing = False
        for key in ("voucher_date", "bank_ledger", "party_ledger", "amount"):
            if r.get(key) is None:
                self.issues.error(f"{self.spec.header(key)} is required.", r.row, self.spec.header(key), label,
                                  code="row.required")
                missing = True
        if missing:
            return None
        amount = q2(r.get("amount"))
        if amount <= 0:
            self.issues.error("Amount must be greater than zero.", r.row, "Amount", label, code="num.positive")
            return None
        ref = r.get("reference_number")
        bank = LedgerPosting(
            ledger=r.get("bank_ledger"), side=Side.DR if receipt else Side.CR, amount=amount, role="bank",
            instrument_number=r.get("instrument_number"), instrument_date=r.get("instrument_date"),
            source_row=r.row, source_column="Bank Ledger")
        party = LedgerPosting(
            ledger=r.get("party_ledger"), side=Side.CR if receipt else Side.DR, amount=amount, role="party",
            is_party=True, bill_name=ref, bill_type="Agst Ref" if ref else "On Account",
            source_row=r.row, source_column=party_header)
        return Voucher(
            kind=self.spec.kind, date=r.get("voucher_date"), reference=ref, party_ledger=party.ledger,
            narration=r.get("narration") or "", postings=[bank, party] if receipt else [party, bank], rows=[r.row])
