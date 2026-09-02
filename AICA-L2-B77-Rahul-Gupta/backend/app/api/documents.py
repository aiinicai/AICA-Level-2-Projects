"""Document upload, processing, financial review/approval and locking."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import (
    AuditLog, Document, DocumentPage, ExtractionResult, FinancialLineItem,
    ValuationCase, VerificationResult,
)
from ..schemas import ApproveValueRequest
from ..services.document.extractor import normalise_period_label, sha256_of
from ..services.document.pipeline import process_document
from ..services.financial.canonical import METRIC_LABELS
from ..services.financial.store import load_financial_data
from ..services.financial.validation import validate_all

router = APIRouter()

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
}
ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls"}


def _case_or_404(db: Session, case_id: str) -> ValuationCase:
    case = db.get(ValuationCase, case_id)
    if case is None:
        raise HTTPException(404, "Valuation case not found")
    return case


@router.post("/api/valuations/{case_id}/documents", status_code=201)
async def upload_document(case_id: str, file: UploadFile = File(...),
                          fiscal_year_label: str = Form(""),
                          db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    settings = get_settings()

    ext = Path(file.filename or "upload").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: PDF, XLSX, XLS")
    if file.content_type and file.content_type not in ALLOWED_TYPES and ext == ".pdf":
        raise HTTPException(400, f"Unexpected MIME type {file.content_type}")

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(400, f"File exceeds {settings.max_upload_mb}MB limit")
    if not content:
        raise HTTPException(400, "Empty file")

    doc_id = uuid.uuid4().hex
    stored = f"{doc_id}{ext}"  # random internal name — never the user's filename
    dest = Path(settings.upload_dir) / stored
    dest.write_bytes(content)

    safe_name = re.sub(r"[^\w.\- ()]", "_", file.filename or "upload")[:290]
    # The label is a client-side guess from the filename. Accept it only if it
    # normalises to a real fiscal year — an invalid one ("FY2024-20") would become
    # an extra phantom period sitting alongside the periods read off the statement.
    fy_label = normalise_period_label(fiscal_year_label) or "" if fiscal_year_label else ""
    doc = Document(
        id=doc_id, case_id=case.id, original_filename=safe_name,
        stored_filename=stored, mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(content), sha256=sha256_of(dest),
        fiscal_year_label=fy_label, status="uploaded",
    )
    db.add(doc)
    db.add(AuditLog(case_id=case.id, action="document_uploaded",
                    detail={"document_id": doc_id, "filename": safe_name,
                            "size": len(content)}))
    db.commit()
    return _doc_out(doc)


def _doc_out(d: Document) -> dict:
    return {"id": d.id, "original_filename": d.original_filename,
            "fiscal_year_label": d.fiscal_year_label, "mime_type": d.mime_type,
            "size_bytes": d.size_bytes, "sha256": d.sha256, "status": d.status,
            "page_count": d.page_count, "has_native_text": bool(d.has_native_text),
            "error": d.error, "uploaded_at": d.uploaded_at.isoformat()}


@router.get("/api/valuations/{case_id}/documents")
def list_documents(case_id: str, db: Session = Depends(get_db)):
    rows = db.execute(select(Document).where(Document.case_id == case_id)
                      .order_by(Document.uploaded_at)).scalars().all()
    return [_doc_out(d) for d in rows]


@router.post("/api/documents/{doc_id}/process")
def process(doc_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    case = _case_or_404(db, doc.case_id)
    if case.financials_locked:
        raise HTTPException(409, "Financials are locked — unlock before reprocessing")
    try:
        result = process_document(db, doc)
    except FileNotFoundError:
        raise HTTPException(500, "Stored file is missing")
    except Exception as e:
        raise HTTPException(422, f"Processing failed: {e}")
    return {"document": _doc_out(doc), "result": result}


@router.get("/api/documents/{doc_id}")
def get_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    pages = db.execute(select(DocumentPage).where(DocumentPage.document_id == doc_id)
                       .order_by(DocumentPage.page_number)).scalars().all()
    return {**_doc_out(doc),
            "pages": [{"page_number": p.page_number, "statement_type": p.statement_type,
                       "is_candidate": bool(p.is_candidate),
                       "has_render": bool(p.rendered_png), "dpi": p.dpi}
                      for p in pages]}


@router.get("/api/documents/{doc_id}/pages/{page_number}/image")
def page_image(doc_id: str, page_number: int, db: Session = Depends(get_db)):
    page = db.execute(select(DocumentPage).where(
        DocumentPage.document_id == doc_id,
        DocumentPage.page_number == page_number)).scalars().first()
    if page is None or not page.rendered_png or not Path(page.rendered_png).exists():
        raise HTTPException(404, "Rendered page not available")
    return FileResponse(page.rendered_png, media_type="image/png")


# ---------------------------------------------------------------------------
# Financials review
# ---------------------------------------------------------------------------

@router.get("/api/valuations/{case_id}/financials")
def get_financials(case_id: str, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    items = db.execute(select(FinancialLineItem).where(
        FinancialLineItem.case_id == case_id)).scalars().all()
    data, periods = load_financial_data(db, case_id)

    grouped: dict[str, list] = {"pnl": [], "balance_sheet": [], "cash_flow": []}
    for it in items:
        grouped.setdefault(it.statement, []).append({
            "id": it.id, "metric": it.metric,
            "label": METRIC_LABELS.get(it.metric, it.metric),
            "period_label": it.period_label,
            "python_value": it.python_value,
            "ai_visual_value": it.ai_visual_value,
            "approved_value": it.approved_value,
            "original_label": it.original_label,
            "original_display": it.original_display,
            "unit": it.unit,
            "source_document_id": it.source_document_id,
            "source_page": it.source_page,
            "verification_status": it.verification_status,
            "confidence": it.confidence,
            "review_note": it.review_note,
        })

    statuses = [it.verification_status for it in items]
    validation = validate_all(data, periods) if periods else {"checks": [], "ok": True,
                                                              "passed": 0, "failed": 0,
                                                              "skipped": 0}
    docs = db.execute(select(Document).where(Document.case_id == case_id)).scalars().all()
    return {
        "locked": bool(case.financials_locked),
        "periods": periods,
        "items": grouped,
        "counts": {
            "total": len(items),
            "verified": statuses.count("verified"),
            "needs_review": statuses.count("needs_review"),
            "low_confidence": statuses.count("low_confidence"),
            "unverified": statuses.count("unverified"),
        },
        "validation": validation,
        "documents": [_doc_out(d) for d in docs],
        "extraction_counts": {
            "raw_items": len(db.execute(select(ExtractionResult).where(
                ExtractionResult.case_id == case_id)).scalars().all()),
            "verifications": len(db.execute(select(VerificationResult).where(
                VerificationResult.case_id == case_id)).scalars().all()),
        },
    }


@router.post("/api/valuations/{case_id}/financials/approve")
def approve_values(case_id: str, body: ApproveValueRequest, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    if case.financials_locked:
        raise HTTPException(409, "Financials are locked")

    if body.approve_all:
        items = db.execute(select(FinancialLineItem).where(
            FinancialLineItem.case_id == case_id)).scalars().all()
        n = 0
        for it in items:
            if it.approved_value is not None:
                continue
            candidate = it.python_value if body.source != "ai" else (
                it.ai_visual_value if it.ai_visual_value is not None else it.python_value)
            if candidate is None:
                continue
            it.approved_value = candidate
            it.approved_by = "Arjun Demo"
            if it.verification_status == "unverified":
                it.verification_status = "verified"
            n += 1
        db.add(AuditLog(case_id=case_id, action="financials_bulk_approved",
                        detail={"count": n, "source": body.source}))
        db.commit()
        return {"approved": n}

    if not body.item_id:
        raise HTTPException(400, "item_id required unless approve_all")
    it = db.get(FinancialLineItem, body.item_id)
    if it is None or it.case_id != case_id:
        raise HTTPException(404, "Line item not found")
    if body.approved_value is None:
        raise HTTPException(400, "approved_value required")
    it.approved_value = body.approved_value
    it.review_note = body.note
    it.verification_status = "verified"
    it.approved_by = "Arjun Demo"
    db.add(AuditLog(case_id=case_id, action="manual_correction",
                    detail={"item": it.metric, "period": it.period_label,
                            "value": body.approved_value, "note": body.note}))
    db.commit()
    return {"ok": True}


@router.post("/api/valuations/{case_id}/financials/lock")
def lock_financials(case_id: str, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    items = db.execute(select(FinancialLineItem).where(
        FinancialLineItem.case_id == case_id)).scalars().all()
    if not items:
        raise HTTPException(400, "No financial data to lock")
    pending = [i for i in items if i.verification_status == "needs_review"
               and i.approved_value is None]
    if pending:
        raise HTTPException(409,
                            f"{len(pending)} item(s) still need review before locking")
    for it in items:
        if it.approved_value is None and it.python_value is not None:
            it.approved_value = it.python_value
    case.financials_locked = 1
    case.status = "interview"
    for d in db.execute(select(Document).where(Document.case_id == case_id)).scalars():
        if d.status in ("awaiting_review", "verified"):
            d.status = "locked"
    db.add(AuditLog(case_id=case_id, action="financials_locked",
                    detail={"items": len(items)}))
    db.commit()
    return {"locked": True}


@router.post("/api/valuations/{case_id}/financials/unlock")
def unlock_financials(case_id: str, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    case.financials_locked = 0
    db.add(AuditLog(case_id=case_id, action="financials_unlocked", detail={}))
    db.commit()
    return {"locked": False}
