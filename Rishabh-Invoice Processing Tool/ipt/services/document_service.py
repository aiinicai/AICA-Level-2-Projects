"""Uploaded documents: copy originals into the company/FY folder, hash,
count pages and detect duplicate files. Nothing is extracted here."""
from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from ipt.core import permissions as perms
from ipt.core.context import AppContext
from ipt.db.base import Database
from ipt.db.models import Company, Document, FinancialYear
from ipt.services import audit_service, storage_service

ALLOWED = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


class DocumentError(Exception):
    pass


@dataclass
class AddResult:
    added: list[Document]
    skipped: list[tuple[str, str]]  # (file name, reason)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_pages(path: Path) -> int:
    if path.suffix.lower() != ".pdf":
        return 1
    try:
        import pymupdf
        with pymupdf.open(path) as doc:
            return doc.page_count
    except Exception:  # unreadable PDFs are reported at extraction time
        return 0


def collect_files(paths: list[Path]) -> list[Path]:
    """Expand folders (recursively) and keep supported file types only."""
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            out += sorted(f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in ALLOWED)
        elif p.is_file():
            out.append(p)
    return out


class DocumentService:
    def __init__(self, db: Database, data_root: Path, ctx: AppContext):
        self.db = db
        self.data_root = data_root
        self.ctx = ctx

    def _scope(self, s) -> tuple[Company, FinancialYear]:
        if not self.ctx.company_id or not self.ctx.fy_id:
            raise DocumentError("Select a company and financial year first")
        company = s.get(Company, self.ctx.company_id)
        fy = s.get(FinancialYear, self.ctx.fy_id)
        if company is None or fy is None or fy.company_id != company.id:
            raise DocumentError("The selected company / financial year is not valid")
        if fy.is_locked:
            raise DocumentError(f"FY {fy.label} is locked. Unlock it in Company Settings to add documents.")
        return company, fy

    def absolute_path(self, doc: Document) -> Path:
        return self.data_root / doc.stored_path

    def add_files(self, paths: list[Path]) -> AddResult:
        perms.require(self.ctx.user.role if self.ctx.user else None, "invoice.process")
        result = AddResult([], [])
        with self.db.session() as s:
            company, fy = self._scope(s)
            folder = storage_service.ensure_fy_folders(self.data_root, company.folder_name, fy.label) / "Invoices"
            for src in collect_files([Path(p) for p in paths]):
                ext = src.suffix.lower()
                if ext not in ALLOWED:
                    result.skipped.append((src.name, "Unsupported file type (use PDF, JPG, JPEG or PNG)"))
                    continue
                if src.stat().st_size == 0:
                    result.skipped.append((src.name, "File is empty"))
                    continue
                digest = sha256_of(src)
                dup = s.scalar(select(Document).where(Document.company_id == company.id,
                                                      Document.sha256 == digest).order_by(Document.id))
                doc = Document(company_id=company.id, fy_id=fy.id, original_filename=src.name, stored_path="",
                               sha256=digest, size_bytes=src.stat().st_size, mime=ALLOWED[ext], status="queued",
                               duplicate_of_id=dup.id if dup else None)
                s.add(doc)
                s.flush()
                target = folder / f"{doc.id:06d}_{src.name}"
                shutil.copy2(src, target)
                doc.stored_path = str(target.relative_to(self.data_root))
                doc.pages = count_pages(target)
                audit_service.record(s, self.ctx.user, "document.upload", "document", doc.id,
                                     after={"file": src.name, "sha256": digest,
                                            "duplicate_of": doc.duplicate_of_id}, company_id=company.id)
                result.added.append(doc)
        return result

    def list_documents(self, statuses: tuple[str, ...] | None = None,
                       include_archived: bool = False) -> list[Document]:
        if not self.ctx.company_id or not self.ctx.fy_id:
            return []
        with self.db.session() as s:
            q = select(Document).where(Document.company_id == self.ctx.company_id,
                                       Document.fy_id == self.ctx.fy_id).order_by(Document.id.desc())
            if statuses:
                q = q.where(Document.status.in_(statuses))
            elif not include_archived:
                q = q.where(Document.status != "archived")
            return list(s.scalars(q))

    def get(self, doc_id: int) -> Document | None:
        with self.db.session() as s:
            d = s.get(Document, doc_id)
            if d and d.company_id != self.ctx.company_id:
                return None
            return d

    def remove(self, doc_ids: list[int]) -> tuple[int, int]:
        """Queue cleanup. A document without invoices is removed (its stored copy deleted; the user's original
        file is never touched). A document that already gave invoices is archived instead - hidden from the
        queue and never extracted again, while its invoices and the stored copy stay. Returns (removed,
        archived)."""
        perms.require(self.ctx.user.role if self.ctx.user else None, "invoice.process")
        from ipt.db.models import Invoice
        removed = archived = 0
        with self.db.session() as s:
            for did in doc_ids:
                d = s.get(Document, did)
                if d is None or d.company_id != self.ctx.company_id:
                    continue
                if s.scalar(select(Invoice.id).where(Invoice.document_id == d.id)):
                    before = d.status
                    d.status = "archived"
                    audit_service.record(s, self.ctx.user, "document.archive", "document", d.id,
                                         before={"file": d.original_filename, "status": before},
                                         company_id=d.company_id)
                    archived += 1
                    continue
                path = self.data_root / d.stored_path if d.stored_path else None
                audit_service.record(s, self.ctx.user, "document.remove", "document", d.id,
                                     before={"file": d.original_filename}, company_id=d.company_id)
                s.delete(d)
                if path and path.is_file():
                    path.unlink()
                removed += 1
        return removed, archived

    def set_status(self, doc_id: int, status: str, method: str = "", error: str = "") -> None:
        with self.db.session() as s:
            d = s.get(Document, doc_id)
            if d:
                d.status, d.error = status, error
                if method:
                    d.method = method
