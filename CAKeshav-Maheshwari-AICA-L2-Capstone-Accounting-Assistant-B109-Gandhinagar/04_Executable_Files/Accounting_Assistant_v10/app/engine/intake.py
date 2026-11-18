"""Folder intake: find new invoice files, extract them, store results; move files after action."""
from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Company, Invoice as InvoiceRow
from ..extract import readers
from ..extract.pipeline import ExtractOptions, process

SUBFOLDERS = ("Posted", "Exceptions")


def new_files(session: Session, company: Company, folder: Path) -> list[tuple[Path, str]]:
    known = set(session.scalars(select(InvoiceRow.file_hash).where(InvoiceRow.company_id == company.id)))
    out = []
    for p in sorted(Path(folder).iterdir()):
        if p.is_file() and p.suffix.lower() in readers.SUPPORTED and not p.name.startswith("~$"):
            h = readers.file_hash(p)
            if h not in known:
                out.append((p, h))
                known.add(h)
    return out


def store(session: Session, company: Company, path: Path, file_hash: str, res) -> InvoiceRow:
    """Save one extraction result (or the exception it raised) as an invoice row."""
    if isinstance(res, Exception):
        row = InvoiceRow(company_id=company.id, file_hash=file_hash, file_path=str(path),
                         extraction={"_trail": [f"Could not read file: {res}"]}, validation={
                             "issues": [{"level": "error", "field": "file", "message": str(res)}],
                             "confidence": 0, "status": "red"}, confidence=0, status="review")
    else:
        row = InvoiceRow(company_id=company.id, file_hash=file_hash, file_path=str(path),
                         extraction={**res.invoice.to_json(), "_trail": res.trail,
                                     "_text": res.invoice.raw_text[:20000]},
                         extraction_source=res.invoice.source, validation=res.validation.to_json(),
                         confidence=res.validation.confidence, status="review")
    session.add(row)
    session.commit()
    return row


def ingest(session: Session, company: Company, path: Path, file_hash: str, opt: ExtractOptions,
           today: date | None = None) -> InvoiceRow:
    try:
        res = process(path, opt, today)
        row = InvoiceRow(company_id=company.id, file_hash=file_hash, file_path=str(path),
                         extraction={**res.invoice.to_json(), "_trail": res.trail,
                                     "_text": res.invoice.raw_text[:20000]},
                         extraction_source=res.invoice.source, validation=res.validation.to_json(),
                         confidence=res.validation.confidence, status="review")
    except Exception as e:
        row = InvoiceRow(company_id=company.id, file_hash=file_hash, file_path=str(path),
                         extraction={"_trail": [f"Could not read file: {e}"]}, validation={
                             "issues": [{"level": "error", "field": "file", "message": str(e)}],
                             "confidence": 0, "status": "red"}, confidence=0, status="exception")
    session.add(row)
    session.commit()
    return row


def reread(session: Session, row: InvoiceRow, opt: ExtractOptions, today: date | None = None) -> InvoiceRow:
    """Run extraction again on an unposted invoice (e.g. after an app update or a Gemini key was added)."""
    if row.status == "posted":
        return row
    res = process(Path(row.file_path), opt, today)
    row.extraction = {**res.invoice.to_json(), "_trail": res.trail, "_text": res.invoice.raw_text[:20000]}
    row.extraction_source = res.invoice.source
    row.validation = res.validation.to_json()
    row.confidence = res.validation.confidence
    row.status = "review" if row.status != "exception" else row.status
    session.commit()
    return row


def move_after(row: InvoiceRow, sub: str) -> None:
    """Move the source file into Posted/ or Exceptions/ next to it (never overwrite)."""
    src = Path(row.file_path)
    if not src.exists() or src.parent.name in SUBFOLDERS:
        return
    dest_dir = src.parent / sub
    dest_dir.mkdir(exist_ok=True)
    dest = dest_dir / src.name
    i = 1
    while dest.exists():
        dest = dest_dir / f"{src.stem} ({i}){src.suffix}"
        i += 1
    shutil.move(str(src), str(dest))
    row.file_path = str(dest)
