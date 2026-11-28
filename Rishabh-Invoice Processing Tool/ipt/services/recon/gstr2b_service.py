"""GSTR-2B uploads: one current file per return period; a replaced file is kept as history."""
from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

from sqlalchemy import func, select

from ipt.core import permissions as perms
from ipt.core.context import AppContext
from ipt.db.base import Database
from ipt.db.models import Company, FinancialYear, Gstr2bRecord, Gstr2bUpload
from ipt.services import audit_service, storage_service
from ipt.services.document_service import sha256_of
from ipt.services.recon.gstr2b_parser import Gstr2bFormatError, Parsed2B, parse_file


class Gstr2bError(Exception):
    pass


class NeedsReplace(Gstr2bError):
    """A current GSTR-2B already exists for the period: ask the user to confirm replacing it."""

    def __init__(self, period: str, existing_file: str):
        super().__init__(f"GSTR-2B for {period} is already loaded ({existing_file}). Replace it?")
        self.period, self.existing_file = period, existing_file


class NeedsGstinConfirm(Gstr2bError):
    """The file's GSTIN cannot be confirmed as this company's - the user must check the file first."""


def gstin_problem(parsed: Parsed2B, file_name: str, company_gstin: str | None) -> str:
    """Why this file may belong to another GSTIN, else ''. (A valid, different GSTIN is refused outright.)"""
    import re
    from ipt.core.gstin import validate_gstin
    own = (company_gstin or "").upper()
    if parsed.gstin_raw and not parsed.gstin and own:
        return (f"The file shows GSTIN '{parsed.gstin_raw}', which is not a valid GSTIN. This company's GSTIN is "
                f"{own}. Check that this is the right GSTR-2B.")
    for g in re.findall(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", file_name.upper()):
        if own and g != own and validate_gstin(g).valid:
            return (f"The file name contains GSTIN {g}, but this company's GSTIN is {own}. Check that this is the "
                    "right GSTR-2B.")
    return ""


class NeedsPeriod(Gstr2bError):
    """The file does not say which return period it is for."""


def period_label(period: str) -> str:
    y, m = period.split("-")
    return f"{date(int(y), int(m), 1):%b %Y}"


class Gstr2bService:
    def __init__(self, db: Database, data_root: Path, ctx: AppContext):
        self.db, self.data_root, self.ctx = db, data_root, ctx

    def _scope(self, s) -> tuple[Company, FinancialYear]:
        if not self.ctx.company_id or not self.ctx.fy_id:
            raise Gstr2bError("Select a company and financial year first")
        company, fy = s.get(Company, self.ctx.company_id), s.get(FinancialYear, self.ctx.fy_id)
        if company is None or fy is None or fy.company_id != company.id:
            raise Gstr2bError("The selected company / financial year is not valid")
        return company, fy

    def preview(self, path: Path) -> Parsed2B:
        """Read the file without saving anything (shown to the user before importing)."""
        try:
            return parse_file(Path(path))
        except Gstr2bFormatError as e:
            raise Gstr2bError(str(e)) from e

    def upload(self, path: Path, period: str | None = None, replace: bool = False,
               parsed: Parsed2B | None = None, gstin_confirmed: bool = False) -> Gstr2bUpload:
        perms.require(self.ctx.user.role if self.ctx.user else None, "gst.upload")
        path = Path(path)
        parsed = parsed or self.preview(path)
        period = period or parsed.period
        if not period:
            raise NeedsPeriod("This file does not show its return period. Choose the month it belongs to.")
        with self.db.session() as s:
            company, fy = self._scope(s)
            y, m = (int(x) for x in period.split("-"))
            if not (fy.start_date <= date(y, m, 1) <= fy.end_date):
                raise Gstr2bError(f"{period_label(period)} is outside the financial year {fy.label}")
            if parsed.gstin and company.gstin and parsed.gstin.upper() != company.gstin.upper():
                raise Gstr2bError(f"This GSTR-2B is for GSTIN {parsed.gstin}, but the company's GSTIN is "
                                  f"{company.gstin}")
            problem = gstin_problem(parsed, path.name, company.gstin)
            if problem and not gstin_confirmed:
                raise NeedsGstinConfirm(problem)
            digest = sha256_of(path)
            current = s.scalar(select(Gstr2bUpload).where(
                Gstr2bUpload.company_id == company.id, Gstr2bUpload.fy_id == fy.id, Gstr2bUpload.period == period,
                Gstr2bUpload.is_current.is_(True)))
            if current is not None and not replace:
                raise NeedsReplace(period, current.file_name)
            if current is not None:
                current.is_current = False
            up = Gstr2bUpload(company_id=company.id, fy_id=fy.id, period=period, file_name=path.name,
                              file_sha256=digest, source_format=parsed.source_format, return_gstin=parsed.gstin,
                              counts_json=json.dumps(parsed.counts()), skipped_json=json.dumps(parsed.skipped),
                              uploaded_by=self.ctx.user.username if self.ctx.user else "")
            s.add(up)
            s.flush()
            folder = storage_service.ensure_fy_folders(self.data_root, company.folder_name, fy.label) / "GSTR2B"
            target = folder / f"{period}_{up.id:04d}_{path.name}"
            shutil.copy2(path, target)
            up.stored_path = str(target.relative_to(self.data_root))
            for rec in parsed.records:
                s.add(Gstr2bRecord(upload_id=up.id, company_id=company.id, fy_id=fy.id, **rec))
            audit_service.record(s, self.ctx.user, "gstr2b.replace" if current else "gstr2b.upload", "gstr2b_upload",
                                 up.id, before={"file": current.file_name, "id": current.id} if current else None,
                                 after={"period": period, "file": path.name, "counts": parsed.counts(),
                                        "gstin_warning_accepted": problem or None},
                                 company_id=company.id)
            s.flush()
            return up

    def uploads(self, include_history: bool = False) -> list[Gstr2bUpload]:
        if not self.ctx.company_id or not self.ctx.fy_id:
            return []
        with self.db.session() as s:
            q = select(Gstr2bUpload).where(Gstr2bUpload.company_id == self.ctx.company_id,
                                           Gstr2bUpload.fy_id == self.ctx.fy_id)
            if not include_history:
                q = q.where(Gstr2bUpload.is_current.is_(True))
            return list(s.scalars(q.order_by(Gstr2bUpload.period, Gstr2bUpload.id.desc())))

    def records(self, upload_id: int | None = None, section: str | None = None) -> list[Gstr2bRecord]:
        """Records of one upload, or of every current upload of the FY."""
        if not self.ctx.company_id or not self.ctx.fy_id:
            return []
        with self.db.session() as s:
            q = select(Gstr2bRecord).where(Gstr2bRecord.company_id == self.ctx.company_id,
                                           Gstr2bRecord.fy_id == self.ctx.fy_id)
            if upload_id:
                q = q.where(Gstr2bRecord.upload_id == upload_id)
            else:
                cur = select(Gstr2bUpload.id).where(Gstr2bUpload.company_id == self.ctx.company_id,
                                                    Gstr2bUpload.fy_id == self.ctx.fy_id,
                                                    Gstr2bUpload.is_current.is_(True))
                q = q.where(Gstr2bRecord.upload_id.in_(cur))
            if section:
                q = q.where(Gstr2bRecord.section == section)
            return list(s.scalars(q.order_by(Gstr2bRecord.supplier_gstin, Gstr2bRecord.doc_date, Gstr2bRecord.id)))

    def record_count(self) -> int:
        with self.db.session() as s:
            cur = select(Gstr2bUpload.id).where(Gstr2bUpload.company_id == self.ctx.company_id,
                                                Gstr2bUpload.fy_id == self.ctx.fy_id, Gstr2bUpload.is_current.is_(True))
            return s.scalar(select(func.count()).select_from(Gstr2bRecord).where(Gstr2bRecord.upload_id.in_(cur))) or 0
