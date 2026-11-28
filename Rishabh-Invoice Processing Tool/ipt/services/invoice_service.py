"""Invoices: create from extraction, edit, validate, approve/reject, export.

Rules: values are only changed by the user (every edit is audited); an edited
field gets confidence 1.0 ("verified by user"); approval is blocked while
validation errors remain, unless an admin overrides with a remark.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ipt.core import permissions as perms
from ipt.core.context import AppContext
from ipt.core.gstin import normalize, validate_gstin
from ipt.core.money import to_decimal
from ipt.core.textnorm import normalize_invoice_no
from ipt.db.base import Database
from ipt.db.models import (Company, Document, FinancialYear, Invoice, InvoiceItem, Supplier, TallyMaster,
                           ValidationResult)
from ipt.services import audit_service
from ipt.services.validation_service import find_duplicates, store_findings, validate_invoice

log = logging.getLogger(__name__)

HEADER_FIELDS = ["doc_type", "supplier_name", "supplier_gstin", "supplier_pan", "supplier_address",
                 "supplier_state_code", "buyer_name", "buyer_gstin", "buyer_state_code", "invoice_no",
                 "invoice_date", "po_no", "original_invoice_ref", "eway_bill_no", "irn", "ack_no",
                 "place_of_supply", "reverse_charge", "currency", "exchange_rate", "taxable_total", "cgst", "sgst",
                 "igst", "cess", "freight", "packing", "other_charges", "round_off", "tds", "tcs", "invoice_total",
                 "amount_in_words"]
MONEY_FIELDS = {"taxable_total", "cgst", "sgst", "igst", "cess", "freight", "packing", "other_charges", "round_off",
                "tds", "tcs", "invoice_total"}
ITEM_FIELDS = ["description", "hsn_sac", "qty", "unit", "rate", "discount", "taxable_value", "gst_rate", "cgst",
               "sgst", "igst", "cess", "total"]
ITEM_NUMERIC = {"qty", "rate", "discount", "taxable_value", "gst_rate", "cgst", "sgst", "igst", "cess", "total"}
# quantities, rates and exchange rates keep more decimals than money (14.645 MT must stay 14.645)
PRECISION = {"qty": Decimal("0.001"), "rate": Decimal("0.0001"), "gst_rate": Decimal("0.001"),
             "exchange_rate": Decimal("0.000001")}
DOC_TYPES = ["tax_invoice", "bill_of_supply", "credit_note", "debit_note", "other"]
STATUSES = ["extracted", "needs_review", "validated", "approved", "rejected"]
REVIEW_THRESHOLD = 0.60


class InvoiceError(Exception):
    pass


def _jsonable(v):
    if isinstance(v, (Decimal, date)):
        return str(v)
    return v


def _snapshot(inv: Invoice) -> dict:
    return {k: _jsonable(getattr(inv, k)) for k in HEADER_FIELDS}


def _coerce(name: str, value, numeric: set[str]):
    if value == "" or value is None:
        return None
    if name in numeric or name == "exchange_rate":
        places = PRECISION.get(name)
        if places is None:
            d = to_decimal(value)
        else:
            try:
                d = Decimal(str(value).replace(",", "").replace("%", "").strip()).quantize(places)
            except ArithmeticError:
                d = None
        if d is None:
            raise InvoiceError(f"'{value}' is not a valid number for {name.replace('_', ' ')}")
        return d
    if name == "invoice_date" and isinstance(value, str):
        from ipt.core.textnorm import parse_date
        d = parse_date(value)
        if d is None:
            raise InvoiceError(f"'{value}' is not a valid date (use DD-MM-YYYY)")
        return d
    if name in ("supplier_gstin", "buyer_gstin"):
        return normalize(value) or None
    return value


class InvoiceService:
    def __init__(self, db: Database, data_root: Path, ctx: AppContext, settings=None):
        self.db = db
        self.data_root = data_root
        self.ctx = ctx
        self.settings = settings

    def tolerance(self) -> Decimal:
        raw = self.settings.get("rounding_tolerance", "1.00") if self.settings else "1.00"
        return to_decimal(raw) or Decimal("1.00")

    def _role(self):
        return self.ctx.user.role if self.ctx.user else None

    # ------------------------------------------------------------------ create
    def create_from_extraction(self, document_id: int, fields: dict, confidence: dict, items: list[dict],
                               item_confidence: float, pages: tuple[int, int] | None = None) -> int:
        with self.db.session() as s:
            doc = s.get(Document, document_id)
            if doc is None:
                raise InvoiceError("Document not found")
            inv = Invoice(company_id=doc.company_id, fy_id=doc.fy_id, document_id=doc.id, status="extracted",
                          page_from=pages[0] if pages else None, page_to=pages[1] if pages else None)
            for k in HEADER_FIELDS:
                if k in fields:
                    setattr(inv, k, fields[k])
            if inv.doc_type not in ("tax_invoice", "bill_of_supply", "credit_note", "debit_note"):
                inv.doc_type = "tax_invoice"          # every bill is a tax invoice unless it says otherwise
            inv.invoice_no_normalized = normalize_invoice_no(inv.invoice_no)
            if fields.get("remarks"):
                inv.remarks = fields["remarks"]
            conf = dict(confidence)
            conf["items"] = item_confidence
            inv.field_confidence_json = json.dumps(conf)
            for it in items:
                tax = it.get("tax_amount")
                row = InvoiceItem(**{k: it.get(k) for k in ["line_no"] + ITEM_FIELDS if k in it})
                # a single "GST amount" column is split by supply type only when it is unambiguous
                if tax is not None and row.cgst is None and row.sgst is None and row.igst is None:
                    sup = (inv.supplier_gstin or "")[:2] or inv.supplier_state_code
                    if sup and inv.place_of_supply and sup != inv.place_of_supply:
                        row.igst = tax
                    elif sup and inv.place_of_supply:
                        half = (tax / 2).quantize(Decimal("0.01"))
                        row.cgst, row.sgst = half, tax - half
                inv.items.append(row)
            known = self._known_supplier_name(s, inv.company_id, inv.supplier_gstin)
            if known:
                # the GSTIN matches a party already in Tally / the supplier master: use that exact name
                # (OCR names are often noisy) and the match also confirms an OCR-repaired GSTIN
                name, source = known
                inv.supplier_name = name
                conf["supplier_name"] = 0.95
                if str(conf.get("supplier_gstin_source", "PAN")).startswith("PAN"):
                    conf["supplier_gstin"] = max(conf.get("supplier_gstin", 0), 0.9)
                conf["supplier_name_source"] = source
                inv.field_confidence_json = json.dumps(conf)
            inv.supplier_id = self._upsert_supplier(s, inv)
            s.add(inv)
            s.flush()
            self._validate(s, inv)
            audit_service.record(s, self.ctx.user, "invoice.extract", "invoice", inv.id,
                                 after={"document": doc.original_filename, "invoice_no": inv.invoice_no},
                                 company_id=inv.company_id)
            return inv.id

    def known_gstins(self, company_id: int) -> dict[str, str]:
        """GSTIN -> name of suppliers already known for a company (Tally ledgers, supplier master)."""
        out: dict[str, str] = {}
        with self.db.session() as s:
            for sup in s.scalars(select(Supplier).where(Supplier.company_id == company_id)):
                if sup.gstin:
                    out[sup.gstin] = sup.tally_ledger_name or sup.name or ""
            for m in s.scalars(select(TallyMaster).where(TallyMaster.company_id == company_id,
                                                         TallyMaster.master_type == "ledger",
                                                         TallyMaster.gstin.is_not(None))):
                if m.gstin:
                    out[m.gstin] = m.name
        return out

    def _known_supplier_name(self, s, company_id: int, gstin: str | None) -> tuple[str, str] | None:
        """Name for a GSTIN from (1) a Tally ledger with that GSTIN, (2) the Tally ledger name the user set
        in the supplier master. None when the GSTIN is unknown or matches more than one Tally ledger."""
        if not gstin or not validate_gstin(gstin).valid:
            return None
        names = sorted({m.name for m in s.scalars(select(TallyMaster).where(
            TallyMaster.company_id == company_id, TallyMaster.master_type == "ledger", TallyMaster.gstin == gstin))})
        if len(names) == 1:
            return names[0], "Tally ledger"
        if len(names) > 1:
            return None
        sup = s.scalar(select(Supplier).where(Supplier.company_id == company_id, Supplier.gstin == gstin))
        if sup is not None and sup.tally_ledger_name:
            return sup.tally_ledger_name, "Supplier master"
        return None

    def _upsert_supplier(self, s, inv: Invoice) -> int | None:
        g = inv.supplier_gstin
        if not g or not validate_gstin(g).valid:
            return None
        sup = s.scalar(select(Supplier).where(Supplier.company_id == inv.company_id, Supplier.gstin == g))
        if sup is None:
            sup = Supplier(company_id=inv.company_id, gstin=g, name=inv.supplier_name or "", pan=g[2:12],
                           state_code=g[:2], address=inv.supplier_address or "")
            s.add(sup)
            s.flush()
        return sup.id

    # ------------------------------------------------------------------ read
    def list_invoices(self, status: str | None = None, text: str = "") -> list[Invoice]:
        if not self.ctx.company_id or not self.ctx.fy_id:
            return []
        with self.db.session() as s:
            q = (select(Invoice).where(Invoice.company_id == self.ctx.company_id, Invoice.fy_id == self.ctx.fy_id)
                 .options(selectinload(Invoice.items)).order_by(Invoice.id.desc()))
            if status:
                q = q.where(Invoice.status == status)
            rows = list(s.scalars(q))
        if text:
            t = text.lower()
            rows = [r for r in rows if t in f"{r.supplier_name} {r.supplier_gstin} {r.invoice_no}".lower()]
        return rows

    def get(self, invoice_id: int) -> Invoice | None:
        with self.db.session() as s:
            inv = s.scalar(select(Invoice).where(Invoice.id == invoice_id)
                           .options(selectinload(Invoice.items)))
            if inv and inv.company_id != self.ctx.company_id:
                return None
            return inv

    def findings(self, invoice_id: int) -> list[ValidationResult]:
        with self.db.session() as s:
            return list(s.scalars(select(ValidationResult).where(ValidationResult.invoice_id == invoice_id)
                                  .order_by(ValidationResult.severity, ValidationResult.id)))

    def confidence(self, inv: Invoice) -> dict:
        try:
            return json.loads(inv.field_confidence_json or "{}")
        except ValueError:
            return {}

    # ------------------------------------------------------------------ edit
    def _load_for_edit(self, s, invoice_id: int) -> Invoice:
        inv = s.scalar(select(Invoice).where(Invoice.id == invoice_id).options(selectinload(Invoice.items)))
        if inv is None or inv.company_id != self.ctx.company_id:
            raise InvoiceError("Invoice not found")
        fy = s.get(FinancialYear, inv.fy_id)
        if fy.is_locked:
            raise InvoiceError(f"FY {fy.label} is locked")
        if inv.status == "imported":
            raise InvoiceError("This invoice is already in Tally. Delete its voucher in Tally and use 'Check Tally / "
                               "import again' in Purchase Vouchers before editing it.")
        if inv.status == "approved":
            perms.require(self._role(), "invoice.approve")   # editing keeps the approval: approvers only
        return inv

    def update(self, invoice_id: int, header: dict, items: list[dict] | None = None) -> str:
        """Save edits. Returns the status afterwards. An approved invoice stays approved when the edited values
        pass every check; with an error it goes back to 'needs_review' (approve it again after fixing)."""
        perms.require(self._role(), "invoice.edit")
        with self.db.session() as s:
            inv = self._load_for_edit(s, invoice_id)
            was_approved = inv.status == "approved"
            before = _snapshot(inv)
            conf = self.confidence(inv)
            for k, v in header.items():
                if k not in HEADER_FIELDS:
                    continue
                new = _coerce(k, v, MONEY_FIELDS)
                if _jsonable(new) != before[k]:
                    setattr(inv, k, new)
                    conf[k] = 1.0
            inv.invoice_no_normalized = normalize_invoice_no(inv.invoice_no)
            if items is not None:
                old_items = [{k: _jsonable(getattr(i, k)) for k in ITEM_FIELDS} for i in inv.items]
                inv.items.clear()
                s.flush()
                for n, row in enumerate(items, start=1):
                    inv.items.append(InvoiceItem(line_no=n, **{k: _coerce(k, row.get(k), ITEM_NUMERIC)
                                                               for k in ITEM_FIELDS}))
                new_items = [{k: _jsonable(getattr(i, k)) for k in ITEM_FIELDS} for i in inv.items]
                if new_items != old_items:
                    conf["items"] = 1.0
            inv.field_confidence_json = json.dumps(conf)
            inv.supplier_id = self._upsert_supplier(s, inv) or inv.supplier_id
            findings = self._validate(s, inv)
            remark = ""
            if was_approved:
                errors = [f.message for f in findings if f.severity == "error"]
                if errors:
                    inv.status = "needs_review"
                    remark = "Approval removed – the edited values have errors: " + "; ".join(errors)[:300]
                else:
                    remark = "Approved invoice edited – still approved"
            after = _snapshot(inv)
            audit_service.record(s, self.ctx.user, "invoice.edit_approved" if was_approved else "invoice.edit",
                                 "invoice", inv.id, before, after, remark, company_id=inv.company_id)
            return inv.status

    def _validate(self, s, inv: Invoice) -> list:
        company = s.get(Company, inv.company_id)
        fy = s.get(FinancialYear, inv.fy_id)
        findings = validate_invoice(inv, company, fy, self.tolerance(), find_duplicates(s, inv))
        store_findings(s, inv.id, findings)
        if inv.status not in ("approved", "rejected"):
            conf = self.confidence(inv)
            low = [k for k, v in conf.items() if isinstance(v, (int, float)) and v < REVIEW_THRESHOLD]
            errors = [x for x in findings if x.severity == "error"]
            inv.status = "needs_review" if (errors or low) else "validated"
        return findings

    def revalidate(self, invoice_id: int) -> None:
        with self.db.session() as s:
            inv = s.scalar(select(Invoice).where(Invoice.id == invoice_id).options(selectinload(Invoice.items)))
            if inv is None or inv.company_id != self.ctx.company_id:
                raise InvoiceError("Invoice not found")
            self._validate(s, inv)

    def approve(self, invoice_id: int, override_remark: str = "") -> None:
        perms.require(self._role(), "invoice.approve")
        with self.db.session() as s:
            inv = self._load_for_edit(s, invoice_id)
            errors = [x for x in self._validate(s, inv) if x.severity == "error"]
            if errors:
                if not override_remark.strip():
                    raise InvoiceError(f"{len(errors)} validation error(s) remain. Fix them, or an admin can "
                                       f"approve with a remark.")
                perms.require(self._role(), "invoice.override")
            inv.status = "approved"
            if override_remark.strip():               # keep earlier remarks (e.g. Claude Code notes) and add this
                note = f"Approved by {self.ctx.user.username if self.ctx.user else '?'}: {override_remark.strip()}"
                inv.remarks = f"{inv.remarks}\n{note}" if inv.remarks else note
            self._learn_layout(s, inv)
            audit_service.record(s, self.ctx.user, "invoice.approve" if not errors else "invoice.approve_override",
                                 "invoice", inv.id, remark=override_remark, company_id=inv.company_id,
                                 after={"open_errors": [e.code for e in errors]})

    def _learn_layout(self, s, inv: Invoice) -> None:
        """Remember where this supplier prints its fields (scanned bills only). Never blocks approval."""
        from ipt.services.extraction import layouts
        try:
            doc = s.get(Document, inv.document_id) if inv.document_id else None
            if doc is not None and doc.stored_path:
                layouts.learn(s, inv, self.data_root / doc.stored_path)
        except Exception:  # noqa: BLE001 - learning is a convenience
            log.exception("Could not learn the layout of invoice %s", inv.id)

    def reject(self, invoice_id: int, remark: str) -> None:
        perms.require(self._role(), "invoice.approve")
        if not remark.strip():
            raise InvoiceError("A remark is required to reject an invoice")
        with self.db.session() as s:
            inv = s.get(Invoice, invoice_id)
            if inv is None or inv.company_id != self.ctx.company_id:
                raise InvoiceError("Invoice not found")
            before = inv.status
            inv.status, inv.remarks = "rejected", remark.strip()
            audit_service.record(s, self.ctx.user, "invoice.reject", "invoice", inv.id, {"status": before},
                                 {"status": "rejected"}, remark, company_id=inv.company_id)

    def reopen(self, invoice_id: int, remark: str) -> None:
        """Take an approved invoice back to review so it can be corrected (e.g. a missing quantity). Not for
        invoices already in Tally. Its mapping memory is kept; it must be approved again."""
        perms.require(self._role(), "invoice.approve")
        if not remark.strip():
            raise InvoiceError("Enter why the invoice is re-opened")
        with self.db.session() as s:
            inv = s.get(Invoice, invoice_id)
            if inv is None or inv.company_id != self.ctx.company_id:
                raise InvoiceError("Invoice not found")
            if inv.status == "imported":
                raise InvoiceError("This invoice is in Tally. Delete the voucher in Tally and use 'Check Tally / "
                                   "import again' first.")
            if inv.status not in ("approved", "rejected"):
                raise InvoiceError("Only approved or rejected invoices can be re-opened")
            before = inv.status
            inv.status = "needs_review"
            audit_service.record(s, self.ctx.user, "invoice.reopen", "invoice", inv.id, {"status": before},
                                 {"status": "needs_review"}, remark.strip(), company_id=inv.company_id)

    def delete(self, invoice_id: int) -> None:
        perms.require(self._role(), "invoice.delete")
        with self.db.session() as s:
            inv = s.get(Invoice, invoice_id)
            if inv is None or inv.company_id != self.ctx.company_id:
                raise InvoiceError("Invoice not found")
            if inv.status == "imported":
                raise InvoiceError(f"{inv.invoice_no or 'This invoice'} is already in Tally – delete its voucher in "
                                   "Tally and use 'Check Tally / import again' first.")
            if inv.status == "approved":
                perms.require(self._role(), "invoice.approve")   # removing an approved bill: approvers only
            snap = _snapshot(inv)
            doc = s.get(Document, inv.document_id) if inv.document_id else None
            s.delete(inv)
            s.flush()
            if doc:
                # queued again: a file with several invoices re-extracts only the pages that no longer
                # have an invoice (see ExtractionPipeline.run)
                doc.status = "queued"
            audit_service.record(s, self.ctx.user, "invoice.delete", "invoice", invoice_id, before=snap,
                                 company_id=self.ctx.company_id)

    def pages_with_invoices(self, document_id: int) -> set[int] | None:
        """First pages (1-based) of the invoices that exist for a file; None if an invoice has no page
        range (extracted before page tracking), which means the whole file is taken."""
        with self.db.session() as s:
            firsts = list(s.scalars(select(Invoice.page_from).where(Invoice.document_id == document_id)))
        if any(p is None for p in firsts):
            return None
        return set(firsts)

    def invoice_for_document(self, document_id: int) -> int | None:
        with self.db.session() as s:
            return s.scalar(select(Invoice.id).where(Invoice.document_id == document_id))

    # ------------------------------------------------------------------ suppliers
    def list_suppliers(self) -> list[tuple[Supplier, int, Decimal]]:
        if not self.ctx.company_id:
            return []
        with self.db.session() as s:
            sups = list(s.scalars(select(Supplier).where(Supplier.company_id == self.ctx.company_id)
                                  .order_by(Supplier.name)))
            out = []
            for sup in sups:
                invs = list(s.scalars(select(Invoice).where(Invoice.supplier_id == sup.id,
                                                            Invoice.status != "rejected")))
                out.append((sup, len(invs), sum((i.invoice_total or Decimal(0)) for i in invs)))
            return out

    def update_supplier(self, supplier_id: int, name: str, address: str, tally_ledger_name: str) -> None:
        perms.require(self._role(), "invoice.edit")
        with self.db.session() as s:
            sup = s.get(Supplier, supplier_id)
            if sup is None or sup.company_id != self.ctx.company_id:
                raise InvoiceError("Supplier not found")
            before = {"name": sup.name, "address": sup.address, "tally_ledger_name": sup.tally_ledger_name}
            sup.name, sup.address, sup.tally_ledger_name = name.strip(), address.strip(), tally_ledger_name.strip()
            audit_service.record(s, self.ctx.user, "supplier.edit", "supplier", sup.id, before,
                                 {"name": sup.name, "address": sup.address, "tally_ledger_name": sup.tally_ledger_name},
                                 company_id=sup.company_id)

    # ------------------------------------------------------------------ export
    def export_xlsx(self, invoice_ids: list[int], target: Path) -> Path:
        from openpyxl import Workbook
        from openpyxl.styles import Font
        perms.require(self._role(), "report.view")
        wb = Workbook()
        ws = wb.active
        ws.title = "Invoice Summary"
        head = ["IPT ID", "Status", "Doc type", "Supplier", "Supplier GSTIN", "Invoice no", "Invoice date",
                "Place of supply", "Reverse charge", "Taxable", "CGST", "SGST", "IGST", "Cess", "Freight", "Packing",
                "Other charges", "Round off", "TCS", "Invoice total", "Currency", "Exchange rate"]
        ws.append(head)
        ws2 = wb.create_sheet("Invoice Item Details")
        ws2.append(["IPT ID", "Invoice no", "Line", "Description", "HSN/SAC", "Qty", "Unit", "Rate", "Discount",
                    "Taxable", "GST %", "CGST", "SGST", "IGST", "Cess", "Total"])
        for wsx in (ws, ws2):
            for c in wsx[1]:
                c.font = Font(bold=True)
        f = lambda v: float(v) if isinstance(v, Decimal) else v  # noqa: E731
        for iid in invoice_ids:
            inv = self.get(iid)
            if inv is None:
                continue
            ws.append([inv.id, inv.status, inv.doc_type, inv.supplier_name, inv.supplier_gstin, inv.invoice_no,
                       inv.invoice_date, inv.place_of_supply,
                       None if inv.reverse_charge is None else ("Yes" if inv.reverse_charge else "No")]
                      + [f(getattr(inv, k)) for k in ("taxable_total", "cgst", "sgst", "igst", "cess", "freight",
                                                      "packing", "other_charges", "round_off", "tcs",
                                                      "invoice_total")]
                      + [inv.currency, f(inv.exchange_rate)])
            for it in inv.items:
                ws2.append([inv.id, inv.invoice_no, it.line_no, it.description, it.hsn_sac, f(it.qty), it.unit,
                            f(it.rate), f(it.discount), f(it.taxable_value), f(it.gst_rate), f(it.cgst), f(it.sgst),
                            f(it.igst), f(it.cess), f(it.total)])
        for wsx in (ws, ws2):
            for row in wsx.iter_rows(min_row=2):
                for c in row:
                    if isinstance(c.value, float):
                        c.number_format = "#,##,##0.00"
                    elif isinstance(c.value, date):
                        c.number_format = "DD-MM-YYYY"
            for col in wsx.columns:
                wsx.column_dimensions[col[0].column_letter].width = min(40, max(10, max(
                    len(str(c.value or "")) for c in col) + 2))
        target.parent.mkdir(parents=True, exist_ok=True)
        wb.save(target)
        return target
