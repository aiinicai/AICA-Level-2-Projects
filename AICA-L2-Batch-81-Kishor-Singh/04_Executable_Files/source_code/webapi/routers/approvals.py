"""Workflow actions: submit, approve, reject, request changes, sign, verify, release, archive.

This is the single endpoint every state transition goes through, so
:mod:`webapi.workflow`'s role and separation-of-duties checks are enforced
in exactly one place -- there is no alternate path that mutates
``Document.status`` directly.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from webapi.database import get_db
from webapi.deps import get_current_user
from webapi.models import ApprovalAction, AuditEvent, Document, User
from webapi.schemas import ApprovalActionOut, ApprovalActionRequest, DocumentOut
from webapi.workflow import WorkflowError, apply_transition

router = APIRouter(prefix="/documents", tags=["approvals"])


def _last_actor_for_current_state(document: Document) -> str | None:
    """Who most recently transitioned the document into its current status --
    used to block that same person from approving/rejecting/requesting changes."""
    if not document.actions:
        return document.uploaded_by_id
    return document.actions[-1].actor_id


@router.post("/{document_id}/actions", response_model=DocumentOut)
def perform_action(
    document_id: str,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")

    last_actor_id = _last_actor_for_current_state(document)
    try:
        new_status = apply_transition(
            document.status, payload.action, current_user.role, current_user.id, last_actor_id
        )
    except WorkflowError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    old_status = document.status
    document.status = new_status
    if payload.action == "submit_for_review":
        document.prepared_by_id = current_user.id

    action_record = ApprovalAction(
        document_id=document.id, actor_id=current_user.id, action=payload.action,
        from_status=old_status.value, to_status=new_status.value, comment=payload.comment,
    )
    db.add(action_record)
    db.add(AuditEvent(
        actor_id=current_user.id, action=f"workflow_{payload.action}", document_id=document.id,
        details=json.dumps({"from": old_status.value, "to": new_status.value}),
    ))
    db.commit()
    db.refresh(document)
    return document


@router.get("/{document_id}/actions", response_model=list[ApprovalActionOut])
def list_actions(document_id: str, db: Session = Depends(get_db), _current_user: User = Depends(get_current_user)) -> list[ApprovalAction]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return document.actions
