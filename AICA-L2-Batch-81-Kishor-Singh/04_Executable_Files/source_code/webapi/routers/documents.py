"""Document upload, listing, and version management.

Uploading a new version while a document is anywhere past DRAFT resets its
status back to DRAFT -- an approval is tied to the exact version that was
reviewed, so a content change must invalidate it rather than silently
carrying the approval forward onto different bytes.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, selectinload

from webapi.database import get_db
from webapi.deps import get_current_user
from webapi.models import AuditEvent, Document, DocumentStatus, DocumentVersion, User
from webapi.schemas import DocumentOut
from webapi.storage import save_document_bytes
from webapi.workflow import content_change_resets_to_draft

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_document(
    title: str,
    client_name: str = "",
    file: UploadFile | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    document = Document(title=title, client_name=client_name, uploaded_by_id=current_user.id, status=DocumentStatus.DRAFT)
    db.add(document)
    db.flush()  # assign document.id before creating the version row

    if file is not None:
        content = await file.read()
        _add_version(db, document, content, file.filename or "document.pdf", current_user)

    db.commit()
    db.refresh(document)
    _log_audit(db, current_user.id, "document_created", document.id, {"title": title})
    return document


@router.post("/{document_id}/versions", response_model=DocumentOut)
async def upload_new_version(
    document_id: str, file: UploadFile, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")

    content = await file.read()
    _add_version(db, document, content, file.filename or "document.pdf", current_user)

    if content_change_resets_to_draft(document.status):
        old_status = document.status
        document.status = DocumentStatus.DRAFT
        document.prepared_by_id = None
        _log_audit(db, current_user.id, "content_changed_reset_to_draft", document.id, {"from_status": old_status.value})

    db.commit()
    db.refresh(document)
    return document


def _add_version(db: Session, document: Document, content: bytes, filename: str, actor: User) -> DocumentVersion:
    storage_path, sha256 = save_document_bytes(content)
    next_version_number = len(document.versions) + 1
    version = DocumentVersion(
        document_id=document.id, version_number=next_version_number, filename=filename,
        sha256=sha256, storage_path=storage_path, uploaded_by_id=actor.id,
    )
    db.add(version)
    db.flush()
    document.current_version_id = version.id
    return version


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), _current_user: User = Depends(get_current_user)) -> list[Document]:
    return db.query(Document).options(selectinload(Document.versions)).order_by(Document.updated_at.desc()).all()


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db), _current_user: User = Depends(get_current_user)) -> Document:
    document = db.query(Document).options(selectinload(Document.versions)).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return document


def _log_audit(db: Session, actor_id: str, action: str, document_id: str, details: dict) -> None:
    db.add(AuditEvent(actor_id=actor_id, action=action, document_id=document_id, details=json.dumps(details)))
    db.commit()
