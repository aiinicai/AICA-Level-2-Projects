"""Document upload and AI agreement reader APIs."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.base import get_db
from ..db.models import Document, ExtractionRun, User
from ..engine.decimal_utils import to_jsonable
from ..services.extraction_service import (confirm_extraction, delete_extraction, delete_unused_extractions, preview_dir,
                                           remove_files, save_document, start_extraction)
from ..services.lease_service import ServiceError, company_of, lease_dict
from .deps import current_user, require

router = APIRouter(prefix="/api", tags=["documents"])

ALLOWED = (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".docx", ".txt")


@router.post("/extractions")
async def create_extraction(file: UploadFile = File(...), mode: Optional[str] = Form(None), allow_cloud: bool = Form(False),
                            force_ocr: bool = Form(False), db: Session = Depends(get_db), user: User = Depends(require("ai.use"))):
    if not file.filename.lower().endswith(ALLOWED):
        raise HTTPException(400, f"Unsupported file type. Allowed: {', '.join(ALLOWED)}")
    data = await file.read()
    if len(data) > 60 * 1024 * 1024:
        raise HTTPException(400, "File exceeds 60 MB")
    comp = company_of(db)
    doc = save_document(db, comp, data, file.filename, user, doc_type="Lease agreement")
    stored = Path(doc.stored_path)
    try:
        run = start_extraction(db, comp, doc, user, mode, allow_cloud, force_ocr)
    except (PermissionError, ValueError) as exc:
        db.rollback()
        # the refused upload must not leave a copy of the agreement on disk (unless an earlier upload uses the same file)
        if db.scalar(select(Document.id).where(Document.stored_path == str(stored))) is None:
            remove_files([stored])
        raise HTTPException(400, str(exc))
    return {"extraction_id": run.id, "document_id": doc.id, "status": run.status}


@router.get("/extraction-schema")
def extraction_schema(user: User = Depends(current_user)):
    """Field catalogue used by the review screen (labels, groups, types, choices, Ind AS references)."""
    from ..docintel.schema import FIELDS
    return [{"key": f.key, "label": f.label, "type": f.type, "group": f.group, "choices": list(f.choices),
             "essential": f.essential, "ind_as_ref": f.ind_as_ref, "description": f.description} for f in FIELDS]


@router.get("/extractions")
def list_extractions(db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    rows = db.scalars(select(ExtractionRun).order_by(ExtractionRun.id.desc()).limit(100)).all()
    out = []
    for r in rows:
        d = db.get(Document, r.document_id)
        res = r.result or {}
        out.append({"id": r.id, "document_id": r.document_id, "filename": d.filename if d else "", "status": r.status,
                    "engine": r.engine, "model": r.model, "created_at": r.created_at, "lease_id": r.lease_id,
                    "missing": len(res.get("missing_essentials") or []), "flags": len(res.get("flags") or [])})
    return to_jsonable(out)


@router.get("/extractions/{run_id}")
def get_extraction(run_id: int, db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    r = db.get(ExtractionRun, run_id)
    if r is None:
        raise HTTPException(404)
    return to_jsonable({"id": r.id, "document_id": r.document_id, "status": r.status, "engine": r.engine, "model": r.model,
                        "result": r.result, "lease_id": r.lease_id, "created_at": r.created_at})


@router.delete("/extractions/{run_id}")
def delete_read(run_id: int, db: Session = Depends(get_db), user: User = Depends(require("document.delete"))):
    """Administrator: delete an agreement read that was not used to create a lease (with its uploaded copy)."""
    r = db.get(ExtractionRun, run_id)
    if r is None:
        raise HTTPException(404, "Agreement read not found")
    files = delete_extraction(db, r, user)
    db.commit()
    remove_files(files)
    return {"deleted": 1}


@router.post("/extractions/delete-unused")
def delete_unused_reads(db: Session = Depends(get_db), user: User = Depends(require("document.delete"))):
    """Administrator: delete every finished agreement read that was not used to create a lease."""
    n, files = delete_unused_extractions(db, user)
    db.commit()
    remove_files(files)
    return {"deleted": n}


@router.post("/extractions/{run_id}/confirm")
def confirm(run_id: int, payload: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(require("lease.write"))):
    r = db.get(ExtractionRun, run_id)
    if r is None or r.status != "Completed":
        raise HTTPException(400, "Extraction not completed")
    try:
        lease = confirm_extraction(db, company_of(db), r, user, payload)
    except ServiceError as exc:
        db.rollback()
        raise HTTPException(exc.status, {"message": exc.message, "issues": exc.issues})
    db.commit()
    return lease_dict(db, lease)


@router.get("/documents/{doc_id}/file")
def doc_file(doc_id: int, db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    d = db.get(Document, doc_id)
    if d is None or not Path(d.stored_path).exists():
        raise HTTPException(404)
    return FileResponse(d.stored_path, filename=d.filename, media_type=d.mime or "application/octet-stream")


@router.get("/documents/{doc_id}/pages/{n}.png")
def page_png(doc_id: int, n: int, db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    p = preview_dir(doc_id) / f"page_{n}.png"
    if not p.exists():
        raise HTTPException(404, "No preview for this page")
    return FileResponse(p, media_type="image/png")


@router.get("/documents/{doc_id}/pages/{n}.txt")
def page_txt(doc_id: int, n: int, db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    p = preview_dir(doc_id) / f"page_{n}.txt"
    if not p.exists():
        raise HTTPException(404)
    return Response(p.read_text(encoding="utf-8"), media_type="text/plain; charset=utf-8")
