import json
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user, require_role, verify_proposal_access
from backend.app.models.models import CMAProject, Proposal, User, AuditLog, ExtractedData
from backend.app.schemas.schemas import CMAProjectSave, CMAProjectResponse
from backend.app.services.cma_service import generate_default_cma, validate_cma_balance

router = APIRouter(prefix="/proposals/{proposal_id}/cma", tags=["CMA Workspace"])

@router.get("", response_model=CMAProjectResponse)
def get_or_create_cma(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    cma = db.query(CMAProject).filter(CMAProject.proposal_id == proposal_id).first()
    
    if not cma:
        # Check if proposal has extracted revenue from operations to anchor base year FY 2024-25
        base_rev = Decimal("50000000.00")
        extracted_rev = db.query(ExtractedData).filter(
            ExtractedData.proposal_id == proposal_id,
            ExtractedData.metric_name == "revenue_from_operations"
        ).first()
        if extracted_rev and extracted_rev.normalized_value:
            base_rev = Decimal(str(extracted_rev.normalized_value))

        # Initialize balanced model starting from base year FY 2024-25
        default_data = generate_default_cma(
            base_turnover_fy25=base_rev,
            requested_cc_limit=proposal.requested_amount,
            requested_term_loan=proposal.requested_amount * Decimal("0.5")
        )
        cma = CMAProject(
            proposal_id=proposal_id,
            base_year="FY 2024-25",
            data_json=json.dumps(default_data),
            is_reconciled=True,
            balance_sheet_diff=Decimal("0.00"),
            cash_flow_diff=Decimal("0.00")
        )
        db.add(cma)
        db.commit()
        db.refresh(cma)
        
    data = json.loads(cma.data_json)
    return {
        "id": cma.id,
        "proposal_id": cma.proposal_id,
        "base_year": cma.base_year,
        "data": data,
        "is_reconciled": cma.is_reconciled,
        "balance_sheet_diff": cma.balance_sheet_diff,
        "cash_flow_diff": cma.cash_flow_diff,
        "created_at": cma.created_at,
        "updated_at": cma.updated_at
    }

@router.put("", response_model=CMAProjectResponse)
def save_cma(
    proposal_id: str,
    cma_in: CMAProjectSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst", "reviewer"]))
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    cma = db.query(CMAProject).filter(CMAProject.proposal_id == proposal_id).first()
    
    # Mathematical validation: Assets must equal Liabilities
    validation = validate_cma_balance(cma_in.data)
    
    if not cma:
        cma = CMAProject(
            proposal_id=proposal_id,
            base_year=cma_in.base_year,
            data_json=json.dumps(cma_in.data),
            is_reconciled=validation["is_reconciled"],
            balance_sheet_diff=Decimal(str(validation["max_discrepancy"])),
            cash_flow_diff=Decimal("0.00")
        )
        db.add(cma)
    else:
        cma.base_year = cma_in.base_year
        cma.data_json = json.dumps(cma_in.data)
        cma.is_reconciled = validation["is_reconciled"]
        cma.balance_sheet_diff = Decimal(str(validation["max_discrepancy"]))
        
    db.commit()
    db.refresh(cma)
    
    audit = AuditLog(
        user_id=current_user.id,
        client_id=proposal.client_id,
        proposal_id=proposal.id,
        action="SAVE_CMA",
        resource_type="cma_project",
        resource_id=cma.id,
        details_json=f"Saved CMA. Reconciled: {validation['is_reconciled']}, Max Diff: ₹ {validation['max_discrepancy']:.2f}"
    )
    db.add(audit)
    db.commit()
    
    return {
        "id": cma.id,
        "proposal_id": cma.proposal_id,
        "base_year": cma.base_year,
        "data": cma_in.data,
        "is_reconciled": cma.is_reconciled,
        "balance_sheet_diff": cma.balance_sheet_diff,
        "cash_flow_diff": cma.cash_flow_diff,
        "created_at": cma.created_at,
        "updated_at": cma.updated_at
    }
