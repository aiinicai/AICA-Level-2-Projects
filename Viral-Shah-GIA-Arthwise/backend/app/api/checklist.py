from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user, require_role, verify_proposal_access
from backend.app.models.models import DocumentChecklistItem, User, AuditLog
from backend.app.schemas.schemas import ChecklistItemResponse, ChecklistItemUpdate

router = APIRouter(prefix="/proposals/{proposal_id}/checklist", tags=["Primary Document Checklist"])

@router.get("", response_model=List[ChecklistItemResponse])
def get_proposal_checklist(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_proposal_access(proposal_id, current_user, db)
    items = db.query(DocumentChecklistItem).filter(
        DocumentChecklistItem.proposal_id == proposal_id
    ).all()
    return items

@router.patch("/{item_id}", response_model=ChecklistItemResponse)
def update_checklist_item(
    proposal_id: str,
    item_id: str,
    item_in: ChecklistItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst", "reviewer"]))
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    item = db.query(DocumentChecklistItem).filter(
        DocumentChecklistItem.id == item_id,
        DocumentChecklistItem.proposal_id == proposal_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")
        
    # Validation rule: If marked not applicable, require reason
    if item_in.is_applicable is False and not item_in.na_reason and not item.na_reason:
        raise HTTPException(
            status_code=400,
            detail="Mandatory requirement: A justification reason must be specified when marking a standard requirement as Not Applicable."
        )
        
    if item_in.is_applicable is not None:
        item.is_applicable = item_in.is_applicable
    if item_in.na_reason is not None:
        item.na_reason = item_in.na_reason
    if item_in.is_received is not None:
        item.is_received = item_in.is_received
    if item_in.period_required is not None:
        item.period_required = item_in.period_required
    if item_in.verification_status is not None:
        item.verification_status = item_in.verification_status
    if item_in.missing_details is not None:
        item.missing_details = item_in.missing_details
    if item_in.remarks is not None:
        item.remarks = item_in.remarks
        
    db.commit()
    db.refresh(item)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        client_id=proposal.client_id,
        proposal_id=proposal.id,
        action="UPDATE_CHECKLIST",
        resource_type="checklist_item",
        resource_id=item.id,
        details_json=f"Updated status for '{item.document_name}' to {item.verification_status}"
    )
    db.add(audit)
    db.commit()
    
    return item
