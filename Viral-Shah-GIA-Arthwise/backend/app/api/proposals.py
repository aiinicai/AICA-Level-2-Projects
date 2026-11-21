import os
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user, require_role, verify_proposal_access
from backend.app.core.config import get_case_dir, settings
from backend.app.models.models import Proposal, Client, Entity, DocumentChecklistItem, AuditLog, User
from backend.app.schemas.schemas import (
    ProposalCreate, ProposalResponse, ProposalStatusUpdate, ProposalRequirementsUpdate
)
from backend.app.core.naming import generate_proposal_code

router = APIRouter(prefix="/proposals", tags=["Proposals Pipeline"])

DEFAULT_CHECKLIST_TEMPLATE = [
    {"name": "Complete Financial Statements FY 2023-24 (AY 2024-25)", "cat": "financial_statements", "period": "FY 2023-24", "remarks": "Audited Balance Sheet, P&L, Notes, Audit Report"},
    {"name": "Complete Financial Statements FY 2024-25 (AY 2025-26)", "cat": "financial_statements", "period": "FY 2024-25", "remarks": "Audited or Management Signed Provisional"},
    {"name": "Complete Financial Statements FY 2025-26 (AY 2026-27)", "cat": "financial_statements", "period": "FY 2025-26", "remarks": "Provisional / Estimated Figures"},
    {"name": "ITR Acknowledgement & Tax Computations (3 Years)", "cat": "itr", "period": "AY 24-25, 25-26, 26-27", "remarks": "e-Filing acknowledgment with barcode"},
    {"name": "Borrower Entity PAN & Proprietor/Partner/Director PANs", "cat": "kyc", "period": "Permanent", "remarks": "All key promoters & co-applicants"},
    {"name": "GST Registration Certificates (All Active GSTINs)", "cat": "gst", "period": "Current", "remarks": "Required if business entity is registered"},
    {"name": "GST Returns GSTR-3B & GSTR-1 (April 2025 to Date)", "cat": "gst", "period": "Apr 2025 - Present", "remarks": "Month/Quarter turnover reconciliation"},
    {"name": "CIBIL / Commercial Credit Bureau Reports", "cat": "cibil", "period": "Latest (<30 Days)", "remarks": "Borrower & Guarantors with consent"},
    {"name": "Consolidated EMI Obligation Sheet", "cat": "emi_sheet", "period": "Current Month", "remarks": "Reconciled with bank debits & loan statements"},
    {"name": "Running CC / OD Sanction & Renewal Letters", "cat": "sanction_letter", "period": "Current Sanction", "remarks": "Limits, Drawing Power, interest & validity"},
    {"name": "Debtors Ageing Analysis (31-Mar-2025 & 31-Mar-2026)", "cat": "debtors_ageing", "period": "31-Mar-25 / 31-Mar-26", "remarks": "Ageing buckets: <90, 91-180, >180 days"},
    {"name": "Operative Bank Statements (Last 12 Months)", "cat": "bank_statement", "period": "Rolling 12 Months", "remarks": "All CC, OD & Current accounts with zero unverified debits"},
    {"name": "Key Executed Purchase Orders & Customer Contracts", "cat": "purchase_orders", "period": "Active Contracts", "remarks": "For working capital / project viability proof"},
    {"name": "Property Chain Deeds & Collateral Valuation Reports", "cat": "property", "period": "Title Validity", "remarks": "Applicable for secured term loans and LAP"}
]

@router.get("", response_model=List[ProposalResponse])
def get_proposals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Proposal).join(Client, Proposal.client_id == Client.id).filter(Client.is_deleted == False)
    if current_user.role == "client":
        proposals = query.filter(Proposal.client_id == current_user.client_id).order_by(Proposal.created_at.desc()).all()
    else:
        proposals = query.order_by(Proposal.created_at.desc()).all()
    return proposals

@router.post("", response_model=ProposalResponse)
def create_proposal(
    prop_in: ProposalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    client = db.query(Client).filter(Client.id == prop_in.client_id, Client.is_deleted == False).first()
    if not client:
        raise HTTPException(status_code=400, detail="Cannot create proposal: Customer profile is deleted or not found")

    code = generate_proposal_code(client.primary_contact_name, db)
    new_proposal = Proposal(
        proposal_code=code,
        client_id=prop_in.client_id,
        entity_id=prop_in.entity_id,
        product_type=prop_in.product_type,
        requested_amount=prop_in.requested_amount,
        tenure_months=prop_in.tenure_months,
        purpose=prop_in.purpose,
        target_rate=prop_in.target_rate,
        status="lead",
        assigned_analyst_id=current_user.id
    )
    db.add(new_proposal)
    db.commit()
    db.refresh(new_proposal)
    
    # Ensure dedicated case-wise backend folder is created on disk
    get_case_dir(new_proposal.proposal_code)
    
    # Pre-populate primary document checklist items
    for item in DEFAULT_CHECKLIST_TEMPLATE:
        chk = DocumentChecklistItem(
            proposal_id=new_proposal.id,
            document_name=item["name"],
            category=item["cat"],
            is_applicable=True,
            is_received=False,
            period_required=item["period"],
            verification_status="requested",
            remarks=item["remarks"]
        )
        db.add(chk)
    db.commit()
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        client_id=new_proposal.client_id,
        proposal_id=new_proposal.id,
        action="CREATE",
        resource_type="proposal",
        resource_id=new_proposal.id,
        details_json=f"Created proposal {code} for {prop_in.product_type}"
    )
    db.add(audit)
    db.commit()
    
    return new_proposal

@router.get("/{proposal_id}", response_model=ProposalResponse)
def get_proposal(proposal_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    return proposal

@router.patch("/{proposal_id}/status", response_model=ProposalResponse)
def update_proposal_status(
    proposal_id: str,
    status_update: ProposalStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst", "reviewer"]))
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    old_status = proposal.status
    proposal.status = status_update.status
    if status_update.review_notes:
        proposal.review_notes = status_update.review_notes
        
    if current_user.role == "reviewer":
        proposal.assigned_reviewer_id = current_user.id
        
    db.commit()
    db.refresh(proposal)
    
    audit = AuditLog(
        user_id=current_user.id,
        client_id=proposal.client_id,
        proposal_id=proposal.id,
        action="UPDATE_STATUS",
        resource_type="proposal",
        resource_id=proposal.id,
        details_json=f"Status changed from {old_status} to {status_update.status}"
    )
    db.add(audit)
    db.commit()
    return proposal

@router.patch("/{proposal_id}/requirements", response_model=ProposalResponse)
@router.put("/{proposal_id}", response_model=ProposalResponse)
def update_proposal_requirements(
    proposal_id: str,
    req_update: ProposalRequirementsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    changes = []
    
    if req_update.product_type is not None and req_update.product_type != proposal.product_type:
        changes.append(f"Product: {proposal.product_type} -> {req_update.product_type}")
        proposal.product_type = req_update.product_type
        
    if req_update.requested_amount is not None and req_update.requested_amount != proposal.requested_amount:
        changes.append(f"Amount: ₹{proposal.requested_amount} -> ₹{req_update.requested_amount}")
        proposal.requested_amount = req_update.requested_amount
        
    if req_update.tenure_months is not None and req_update.tenure_months != proposal.tenure_months:
        changes.append(f"Tenure: {proposal.tenure_months}M -> {req_update.tenure_months}M")
        proposal.tenure_months = req_update.tenure_months
        
    if req_update.target_rate is not None and req_update.target_rate != proposal.target_rate:
        changes.append(f"Rate: {proposal.target_rate}% -> {req_update.target_rate}%")
        proposal.target_rate = req_update.target_rate
        
    if req_update.purpose is not None and req_update.purpose != proposal.purpose:
        changes.append(f"Purpose updated")
        proposal.purpose = req_update.purpose

    db.commit()
    db.refresh(proposal)

    if changes:
        audit = AuditLog(
            user_id=current_user.id,
            client_id=proposal.client_id,
            proposal_id=proposal.id,
            action="UPDATE_REQUIREMENTS",
            resource_type="proposal",
            resource_id=proposal.id,
            details_json=f"Updated loan requirements: {'; '.join(changes)}"
        )
        db.add(audit)
        db.commit()

    return proposal

@router.delete("/{proposal_id}")
def delete_proposal(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    proposal_code = proposal.proposal_code
    client_id = proposal.client_id

    # Clean up case folder if it exists
    case_folder = os.path.join(settings.CASES_DIR, proposal_code)
    if os.path.exists(case_folder):
        try:
            shutil.rmtree(case_folder)
        except Exception:
            pass

    # Record deletion audit log before deleting proposal
    audit = AuditLog(
        user_id=current_user.id,
        client_id=client_id,
        proposal_id=proposal_id,
        action="DELETE",
        resource_type="proposal",
        resource_id=proposal_id,
        details_json=f"Deleted proposal {proposal_code} and all associated artifacts"
    )
    db.add(audit)
    
    # Cascade delete in DB
    db.delete(proposal)
    db.commit()

    # If this was the customer's last remaining proposal, soft-delete the client profile
    if client_id:
        remaining_proposals = db.query(Proposal).filter(Proposal.client_id == client_id).count()
        if remaining_proposals == 0:
            client = db.query(Client).filter(Client.id == client_id).first()
            if client and not client.is_deleted:
                client.is_deleted = True
                cli_audit = AuditLog(
                    user_id=current_user.id,
                    client_id=client_id,
                    action="DELETE",
                    resource_type="client",
                    resource_id=client_id,
                    details_json=f"Customer {client.primary_contact_name} marked deleted as all linked proposals were deleted"
                )
                db.add(cli_audit)
                db.commit()
    
    return {"status": "success", "message": f"Proposal {proposal_code} deleted successfully"}
