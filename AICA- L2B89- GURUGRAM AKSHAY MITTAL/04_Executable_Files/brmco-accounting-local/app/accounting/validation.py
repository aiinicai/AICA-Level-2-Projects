"""Business validation of assembled vouchers.

Runs after the accounting engine and before anything is shown as "ready to
post". Any ``error`` blocks posting; ``warning`` is shown for review.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Protocol

from app.accounting.models import ZERO, ValidationIssue, Voucher, VoucherKind, q2
from app.accounting.services import MasterLookup
from app.config.settings import AppConfig

BANK_GROUPS = {"bank accounts", "bank od a/c", "bank occ a/c", "cash-in-hand"}


class PostedVoucherLookup(Protocol):
    def find_exact(self, company: str, keys: list[str]) -> dict[str, dict[str, Any]]: ...
    def find_fuzzy(self, company: str, keys: list[str]) -> dict[str, dict[str, Any]]: ...


def history_company_key(config: AppConfig) -> str:
    return (config.tally_company_name or config.company_name or "__ACTIVE__").strip().upper()


def exact_history_key(config: AppConfig, v: Voucher) -> str | None:
    key = v.exact_key()
    return f"{config.financial_year}|{key}" if key else None


class VoucherValidator:
    def __init__(self, config: AppConfig, masters: MasterLookup, posted: PostedVoucherLookup,
                 today: date | None = None) -> None:
        self.config = config
        self.masters = masters
        self.posted = posted
        self.today = today or date.today()
        self.issues: list[ValidationIssue] = []

    def _add(self, severity: str, message: str, v: Voucher | None = None, row: int | None = None,
             column: str | None = None, code: str = "") -> None:
        self.issues.append(ValidationIssue(
            severity=severity, message=message, voucher=v.label if v else None,
            row=row if row is not None else (v.first_row if v else None), column=column, code=code))

    def validate(self, vouchers: list[Voucher]) -> list[ValidationIssue]:
        self._check_masters_available()
        if vouchers and self.masters.has("voucher_type"):
            vt = self.config.voucher_type_for(vouchers[0].kind)
            if self.masters.resolve("voucher_type", vt) is None:
                self._add("error", f'Voucher type "{vt}" does not exist in Tally. Set the correct name in Settings.',
                          column="Settings: Voucher Type", code="master.voucher_type")
        for v in vouchers:
            self._check_dates(v)
            if v.kind in (VoucherKind.SALES, VoucherKind.PURCHASE):
                self._check_gst(v)
            self._check_ledgers(v)
            self._check_balance(v)
        self._check_duplicates(vouchers)
        return self.issues

    # ---------------------------------------------------------------- dates
    def _check_dates(self, v: Voucher) -> None:
        start = date(self.config.fy_start_year, 4, 1)
        end = date(self.config.fy_start_year + 1, 3, 31)
        if not (start <= v.date <= end):
            self._add("error", f"Voucher Date {v.date:%d-%m-%Y} is outside financial year "
                               f"{self.config.financial_year} ({start:%d-%m-%Y} to {end:%d-%m-%Y}).",
                      v, column="Voucher Date", code="date.fy")
        if v.date > self.today:
            self._add("warning", f"Voucher Date {v.date:%d-%m-%Y} is in the future.", v, column="Voucher Date",
                      code="date.future")
        if v.reference_date and v.reference_date > v.date:
            self._add("error", f"Supplier Invoice Date {v.reference_date:%d-%m-%Y} is after the Voucher Date.",
                      v, column="Invoice Date", code="date.order")
        for p in v.postings:
            if p.instrument_date and abs((p.instrument_date - v.date).days) > 90:
                self._add("warning", f"Instrument Date {p.instrument_date:%d-%m-%Y} is more than 90 days from "
                                     "the Voucher Date.", v, column="Instrument Date", code="date.instrument")

    # ---------------------------------------------------------------- GST
    def _check_gst(self, v: Voucher) -> None:
        sales = v.kind == VoucherKind.SALES
        tol = self.config.tax_tolerance
        company_state = self.config.company_state or None
        supplier_state = company_state if sales else v.party_state
        intra: bool | None = None
        if supplier_state and v.place_of_supply:
            intra = supplier_state == v.place_of_supply
        elif sales and not company_state:
            self._add("warning", "Company State is not set in Settings, so CGST/SGST vs IGST could not be checked.",
                      v, code="gst.company_state")

        for line in v.lines:
            has_local = bool(line.cgst_amount or line.sgst_amount or line.cgst_rate or line.sgst_rate)
            has_igst = bool(line.igst_amount or line.igst_rate)
            if has_local and has_igst:
                self._add("error", "A line cannot have both CGST/SGST and IGST.", v, line.row, "IGST Amount",
                          "gst.mixed")
                continue
            if line.cgst_rate != line.sgst_rate:
                self._add("error", f"CGST Rate {line.cgst_rate.normalize()}% and SGST Rate "
                                   f"{line.sgst_rate.normalize()}% must be equal.", v, line.row, "SGST Rate",
                          "gst.cgst_sgst")
            elif abs(line.cgst_amount - line.sgst_amount) > tol:
                self._add("error", f"CGST Amount {line.cgst_amount} and SGST Amount {line.sgst_amount} "
                                   "should be equal.", v, line.row, "SGST Amount", "gst.cgst_sgst")
            if intra is True and has_igst:
                self._add("error", f"Intra-state supply ({supplier_state} to {v.place_of_supply}) must use "
                                   "CGST + SGST, not IGST.", v, line.row, "IGST Amount", "gst.intra")
            if intra is False and has_local:
                self._add("error", f"Inter-state supply ({supplier_state} to {v.place_of_supply}) must use "
                                   "IGST, not CGST + SGST.", v, line.row, "CGST Amount", "gst.inter")
            if v.reverse_charge and line.tax_total:
                self._add("error", "Reverse charge invoice: leave tax columns blank. RCM tax is not charged on "
                                   "the invoice (book RCM liability separately).", v, line.row, "CGST Amount",
                          "gst.rcm")

        if sales and v.party_gstin and v.party_state and v.place_of_supply and v.party_state != v.place_of_supply:
            self._add("warning", f"Place of Supply {v.place_of_supply} differs from the customer's state "
                                 f"{v.party_state}. Check this is intended.", v, column="Place of Supply",
                      code="gst.pos")

        if v.invoice_total is not None:
            diff = q2(v.invoice_total - v.computed_invoice_total)
            if diff:
                hint = ""
                if abs(diff) < 1:
                    hint = f" If the difference is rounding, set Round Off = {q2(v.round_off + diff)}."
                self._add("error", f"Invoice Total {v.invoice_total} does not match Taxable + Taxes + Round Off "
                                   f"= {v.computed_invoice_total}.{hint}", v, column="Invoice Total",
                          code="calc.total")
        if abs(v.round_off) >= 1:
            self._add("warning", f"Round Off {v.round_off} is 1.00 or more.", v, column="Round Off",
                      code="calc.round_off")

    # ---------------------------------------------------------------- ledgers & masters
    def _masters_required(self) -> bool:
        return self.config.require_master_sync and not self.config.demo_mode

    def _check_masters_available(self) -> None:
        if self.masters.has("ledger"):
            return
        if self._masters_required():
            self._add("error", "Tally masters have not been synced for this company, so ledgers cannot be "
                               "verified. Open Tally > Master Sync and sync masters first.", code="master.nosync")
        else:
            self._add("warning", "Tally masters are not synced; ledger names were NOT verified.",
                      code="master.nosync")

    def _check_ledgers(self, v: Voucher) -> None:
        if not self.masters.has("ledger"):
            return
        seen: set[tuple[str, int | None]] = set()

        def resolve(name: str, row: int | None, column: str | None) -> str:
            canonical = self.masters.resolve("ledger", name)
            if canonical is None and (name.lower(), row) not in seen:
                seen.add((name.lower(), row))
                where = "" if not (column or "").startswith("Settings") else " Update it in Settings or create it in Tally."
                self._add("error", f'Ledger "{name}" does not exist in Tally master data.{where}', v, row, column,
                          "master.ledger")
            return canonical or name

        for p in v.postings:
            p.ledger = resolve(p.ledger, p.source_row, p.source_column)
            if p.role == "bank":
                under = self.masters.is_under_group(p.ledger, BANK_GROUPS)
                if under is False:
                    self._add("warning", f'"{p.ledger}" is not under Bank Accounts / Cash-in-Hand in Tally.',
                              v, p.source_row, p.source_column, "master.bank_group")
        for inv in v.inventory:
            inv.ledger = resolve(inv.ledger, inv.source_row, "Sales Ledger" if v.kind == VoucherKind.SALES
                                 else "Purchase/Expense Ledger")
            if not inv.unit:
                self._add("error", f'Unit is required for stock item "{inv.stock_item}".', v, inv.source_row,
                          "Unit", "master.unit")
            elif self.masters.has("unit"):
                unit = self.masters.resolve("unit", inv.unit)
                if unit is None:
                    self._add("error", f'Unit "{inv.unit}" does not exist in Tally.', v, inv.source_row, "Unit",
                              "master.unit")
                else:
                    inv.unit = unit
        if v.party_ledger:
            v.party_ledger = next((p.ledger for p in v.postings if p.is_party), v.party_ledger)
        for line in v.lines:
            if line.quantity and line.description and not line.is_stock_item and self.masters.has("stock_item"):
                self._add("warning", f'"{line.description}" is not a Tally stock item; it will be posted as an '
                                     "accounting line (quantity not recorded in Tally).", v, line.row,
                          "Item/Description", "master.stock_item")

    # ---------------------------------------------------------------- balance
    def _check_balance(self, v: Voucher) -> None:
        dr, cr = v.total_debit, v.total_credit
        if dr != cr:
            self._add("error", f"Voucher is not balanced: Total Debit {dr} vs Total Credit {cr} "
                               f"(difference {q2(dr - cr)}). It will not be posted.", v,
                      column="Debit" if v.kind == VoucherKind.JOURNAL else None, code="balance")
        elif dr <= ZERO:
            self._add("error", "Voucher total must be greater than zero.", v, code="balance.zero")
        if v.kind == VoucherKind.JOURNAL:
            sides = {p.side for p in v.postings}
            if len(v.postings) < 2 or len(sides) < 2:
                self._add("error", "A journal needs at least one debit and one credit line.", v, code="jv.lines")
        party_amounts = [p.amount for p in v.postings if p.is_party]
        if any(a <= 0 for a in party_amounts):
            self._add("error", "Party amount works out to zero or negative. Check the amounts and round off.", v,
                      code="balance.party")

    # ---------------------------------------------------------------- duplicates
    def _check_duplicates(self, vouchers: list[Voucher]) -> None:
        exact_seen: dict[str, Voucher] = {}
        fuzzy_seen: dict[str, Voucher] = {}
        for v in vouchers:
            key = v.exact_key()
            if key:
                if key in exact_seen:
                    other = exact_seen[key]
                    self._add("warning" if v.kind in (VoucherKind.RECEIPT, VoucherKind.PAYMENT) else "error",
                              f"Possible duplicate of row {other.first_row} in this file "
                              f"(same {self._key_desc(v)}).", v, code="dup.file")
                else:
                    exact_seen[key] = v
            fkey = v.fuzzy_key()
            if fkey in fuzzy_seen and key is None:
                self._add("warning", f"Same date, party and amount as row {fuzzy_seen[fkey].first_row}. "
                                     "Check it is not a duplicate.", v, code="dup.file_fuzzy")
            fuzzy_seen.setdefault(fkey, v)

        company = history_company_key(self.config)
        exact_keys = {exact_history_key(self.config, v): v for v in vouchers if v.exact_key()}
        found = self.posted.find_exact(company, [k for k in exact_keys if k])
        for k, rec in found.items():
            v = exact_keys[k]
            self._add("error", f"Already posted to Tally on {str(rec['posted_at'])[:10]} "
                               f"({self._key_desc(v)} {rec.get('voucher_label') or ''}). Remove it from the file "
                               "or delete it in Tally first.", v, code="dup.history")
        fuzzy = {v.fuzzy_key(): v for v in vouchers}
        for k, rec in self.posted.find_fuzzy(company, list(fuzzy)).items():
            v = fuzzy[k]
            if exact_history_key(self.config, v) in found:
                continue
            self._add("warning", f"A voucher with the same date, party and amount was posted on "
                                 f"{str(rec['posted_at'])[:10]} ({rec.get('voucher_label') or 'no number'}). "
                                 "Check it is not a duplicate.", v, code="dup.history_fuzzy")

    @staticmethod
    def _key_desc(v: Voucher) -> str:
        return {
            VoucherKind.SALES: "invoice number",
            VoucherKind.PURCHASE: "supplier + invoice number",
            VoucherKind.JOURNAL: "date + reference number",
            VoucherKind.RECEIPT: "bank + instrument/UTR",
            VoucherKind.PAYMENT: "bank + instrument/UTR",
        }[v.kind]


def summarise(issues: list[ValidationIssue]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for i in issues:
        counts[i.severity] += 1
    return {"errors": counts["error"], "warnings": counts["warning"]}
