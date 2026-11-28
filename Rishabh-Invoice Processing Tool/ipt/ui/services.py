"""Container passed to every page: services + current context."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ipt.core.context import AppContext
from ipt.db.base import Database
from ipt.services.audit_service import AuditService
from ipt.services.auth_service import AuthService
from ipt.services.company_service import CompanyService
from ipt.services.backup_service import BackupService
from ipt.services.document_service import DocumentService
from ipt.services.export_service import ExportService
from ipt.services.invoice_service import InvoiceService
from ipt.services.reports_service import ReportService
from ipt.services.recon.gstr2b_service import Gstr2bService
from ipt.services.recon.purchase_register import PurchaseRegisterService
from ipt.services.recon.recon_service import ReconService
from ipt.services.settings_service import SettingsService
from ipt.services.tally.mapping import MappingService
from ipt.services.tally.service import ImportService, TallyService, VoucherService


@dataclass
class Services:
    db: Database
    data_root: Path
    ctx: AppContext
    auth: AuthService
    companies: CompanyService
    audit: AuditService
    settings: SettingsService
    documents: DocumentService
    invoices: InvoiceService
    tally: TallyService
    mapping: MappingService
    vouchers: VoucherService
    imports: ImportService
    gstr2b: Gstr2bService
    purchases: PurchaseRegisterService
    recon: ReconService
    reports: ReportService
    exports: ExportService
    backups: BackupService
    resets: object = None          # ResetService (set in build)

    @classmethod
    def build(cls, db: Database, data_root: Path) -> "Services":
        ctx = AppContext()
        settings = SettingsService(db)
        s = cls(db=db, data_root=data_root, ctx=ctx, auth=AuthService(db),
                   companies=CompanyService(db, data_root), audit=AuditService(db), settings=settings,
                   documents=DocumentService(db, data_root, ctx),
                   invoices=(inv := InvoiceService(db, data_root, ctx, settings)), tally=(ts := TallyService(db, ctx)),
                   mapping=(mp := MappingService(db, ctx)),
                   vouchers=(vs := VoucherService(db, ctx, mp, data_root)),
                   imports=ImportService(db, ctx, vs, ts, data_root),
                   gstr2b=Gstr2bService(db, data_root, ctx),
                   purchases=PurchaseRegisterService(db, data_root, ctx, ts),
                   recon=(rc := ReconService(db, ctx)),
                   reports=(rp := ReportService(db, ctx, rc)),
                   exports=ExportService(db, ctx, rp, inv, vs),
                   backups=BackupService(db, data_root, ctx, settings))
        from ipt.services.reset_service import ResetService
        s.resets = ResetService(db, data_root, ctx, s.backups)
        return s
