"""Reset one company's working data (admin only).

A full backup is made first; the company, its financial years, users, the audit trail and backups stay, and
nothing is ever sent to Tally. Groups:
- invoices:  uploaded files (and OCR / Claude case files), extraction history, invoices, items, checks,
             Tally import history
- gstr2b:    GSTR-2B uploads and records
- purchases: purchase-register loads, records and rejected rows
- recon:     reconciliation runs, rows and ITC review
- setup:     Master Mapping rules, supplier masters, learned supplier layouts, cached Tally masters,
             purchase-register templates, reconciliation settings  (off unless asked for)
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import delete, select

from ipt.core import permissions as perms
from ipt.db.models import (Company, Document, ExtractionResult, Gstr2bRecord, Gstr2bUpload, Invoice, InvoiceItem,
                           ItcAnalysis, MappingRule, PrTemplate, PurchaseRegisterRecord, PurchaseRegisterReject,
                           PurchaseRegisterUpload, ReconRow, ReconRun, ReconSetting, Supplier, SupplierLayout,
                           TallyImport, TallyMaster, ValidationResult)
from ipt.services import audit_service

GROUPS = {
    "invoices": "Invoices: uploaded bills, extracted invoices, review data, Tally import history",
    "gstr2b": "GSTR-2B uploads",
    "purchases": "Purchase register (Excel loads and Tally fetches)",
    "recon": "Reconciliation results and ITC review",
    "setup": "Setup: Master Mapping, supplier masters, learned supplier layouts, cached Tally ledgers/items",
}
DEFAULT = ("invoices", "gstr2b", "purchases", "recon")


class ResetError(Exception):
    pass


@dataclass
class ResetResult:
    backup_file: str = ""
    counts: dict = field(default_factory=dict)
    files_removed: int = 0


class ResetService:
    def __init__(self, db, data_root: Path, ctx, backups):
        self.db, self.data_root, self.ctx, self.backups = db, Path(data_root), ctx, backups

    def summary(self, company_id: int) -> dict[str, int]:
        """How many records each group holds now (shown before the user confirms)."""
        with self.db.session() as s:
            def n(model, *where):
                return len(s.scalars(select(model.id).where(*where)).all())
            c = company_id
            return {"invoices": n(Invoice, Invoice.company_id == c) + n(Document, Document.company_id == c),
                    "gstr2b": n(Gstr2bRecord, Gstr2bRecord.company_id == c),
                    "purchases": n(PurchaseRegisterRecord, PurchaseRegisterRecord.company_id == c),
                    "recon": n(ReconRow, ReconRow.company_id == c) + n(ItcAnalysis, ItcAnalysis.company_id == c),
                    "setup": n(MappingRule, MappingRule.company_id == c) + n(Supplier, Supplier.company_id == c)
                    + n(SupplierLayout, SupplierLayout.company_id == c)}

    def reset(self, company_id: int, groups, confirm_name: str, progress=None) -> ResetResult:
        perms.require(self.ctx.user.role if self.ctx.user else None, "company.reset")
        groups = [g for g in groups if g in GROUPS]
        if not groups:
            raise ResetError("Choose what to reset")
        with self.db.session() as s:
            company = s.get(Company, company_id)
            if company is None:
                raise ResetError("Company not found")
            if confirm_name.strip().lower() != company.name.strip().lower():
                raise ResetError("The company name typed does not match – nothing was deleted")
            name = company.name
        if progress:
            progress("Making a full backup first")
        try:
            backup = self.backups.create("before-reset", progress=progress)
        except Exception as e:  # noqa: BLE001 - never delete without a backup
            raise ResetError(f"Backup failed, so nothing was deleted: {e}") from e
        res = ResetResult(backup_file=Path(backup.path).name)
        c = company_id
        files: list[Path] = []
        with self.db.session() as s:
            def gone(model, *where):
                ids = list(s.scalars(select(model.id).where(*where)))
                if ids:
                    s.execute(delete(model).where(model.id.in_(ids)))
                res.counts[model.__tablename__] = res.counts.get(model.__tablename__, 0) + len(ids)
                return ids

            if "recon" in groups or "gstr2b" in groups or "purchases" in groups:
                # reconciliation rows point at 2B / register records: they go whenever either side goes
                runs = list(s.scalars(select(ReconRun.id).where(ReconRun.company_id == c)))
                gone(ReconRow, ReconRow.company_id == c)
                if runs:
                    gone(ReconRun, ReconRun.id.in_(runs))
            if "recon" in groups:
                gone(ItcAnalysis, ItcAnalysis.company_id == c)
            if "gstr2b" in groups:
                for u in s.scalars(select(Gstr2bUpload).where(Gstr2bUpload.company_id == c)):
                    if u.stored_path:
                        files.append(self.data_root / u.stored_path)
                gone(Gstr2bRecord, Gstr2bRecord.company_id == c)
                gone(Gstr2bUpload, Gstr2bUpload.company_id == c)
            if "purchases" in groups:
                ups = list(s.scalars(select(PurchaseRegisterUpload.id).where(PurchaseRegisterUpload.company_id == c)))
                if ups:
                    gone(PurchaseRegisterReject, PurchaseRegisterReject.upload_id.in_(ups))
                gone(PurchaseRegisterRecord, PurchaseRegisterRecord.company_id == c)
                gone(PurchaseRegisterUpload, PurchaseRegisterUpload.company_id == c)
            if "invoices" in groups:
                inv_ids = list(s.scalars(select(Invoice.id).where(Invoice.company_id == c)))
                if inv_ids:
                    gone(InvoiceItem, InvoiceItem.invoice_id.in_(inv_ids))
                    gone(ValidationResult, ValidationResult.invoice_id.in_(inv_ids))
                gone(TallyImport, TallyImport.company_id == c)
                gone(Invoice, Invoice.company_id == c)
                docs = list(s.scalars(select(Document).where(Document.company_id == c)))
                for d in docs:
                    if d.stored_path:
                        p = self.data_root / d.stored_path
                        files += [p, Path(str(p) + ".ocr.json")]
                if docs:
                    gone(ExtractionResult, ExtractionResult.document_id.in_([d.id for d in docs]))
                gone(Document, Document.company_id == c)
                for case in self._claude_cases(set(inv_ids)):
                    shutil.rmtree(case, ignore_errors=True)
            if "setup" in groups:
                gone(SupplierLayout, SupplierLayout.company_id == c)
                gone(MappingRule, MappingRule.company_id == c)
                if "invoices" in groups:
                    gone(Supplier, Supplier.company_id == c)
                else:                                    # invoices still point at suppliers: unlink first
                    for inv in s.scalars(select(Invoice).where(Invoice.company_id == c)):
                        inv.supplier_id = None
                    gone(Supplier, Supplier.company_id == c)
                gone(TallyMaster, TallyMaster.company_id == c)
                gone(PrTemplate, PrTemplate.company_id == c)
                gone(ReconSetting, ReconSetting.company_id == c)
            audit_service.record(s, self.ctx.user, "company.reset", "company", c,
                                 after={"groups": groups, "deleted": res.counts, "backup": res.backup_file},
                                 remark=f"Reset of {name}", company_id=c)
        for f in files:                                   # files only after the database change succeeded
            try:
                if f.is_file():
                    f.unlink()
                    res.files_removed += 1
            except OSError:
                pass
        return res

    def _claude_cases(self, invoice_ids: set[int]) -> list[Path]:
        q = self.data_root / "claude_queue"
        out = []
        for base in (q, q / "done"):
            if base.exists():
                for d in base.glob("inv-*"):
                    try:
                        if int(d.name.split("-", 1)[1]) in invoice_ids:
                            out.append(d)
                    except ValueError:
                        pass
        return out
