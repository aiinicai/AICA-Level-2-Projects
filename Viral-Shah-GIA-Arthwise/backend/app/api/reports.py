import os
import json
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.app.core.config import settings, get_case_dir
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user, verify_proposal_access
from backend.app.models.models import Proposal, CMAProject, FinancialEvaluation, Entity, Client, User, AuditLog
from backend.app.services.report_generator import ReportGeneratorService
from backend.app.services.cma_service import generate_default_cma

router = APIRouter(prefix="/proposals/{proposal_id}/reports", tags=["Project Reports & Exports"])

def _build_proposal_dossier_data(proposal: Proposal, db: Session) -> dict:
    entity = db.query(Entity).filter(Entity.id == proposal.entity_id).first()
    client = db.query(Client).filter(Client.id == proposal.client_id).first()
    latest_eval = db.query(FinancialEvaluation).filter(
        FinancialEvaluation.proposal_id == proposal.id
    ).order_by(FinancialEvaluation.created_at.desc()).first()

    return {
        "proposal_code": proposal.proposal_code,
        "borrower_name": entity.legal_name if entity else (client.primary_contact_name if client else "Borrower"),
        "constitution": entity.constitution if entity else "Private Limited",
        "pan_masked": entity.pan_masked if entity else "AAB*****M",
        "incorporation_date": entity.date_of_incorporation if entity else "2020-08-15",
        "product_type": proposal.product_type,
        "requested_amount": float(proposal.requested_amount),
        "tenure_months": proposal.tenure_months,
        "purpose": proposal.purpose or "Working Capital requirements & business expansion",
        "target_rate": proposal.target_rate,
        "preliminary_eligible_amount": float(latest_eval.preliminary_eligible_amount) if latest_eval else float(proposal.requested_amount),
        "limiting_factor": latest_eval.limiting_factor if latest_eval else "Debt Service Capacity (DSCR)",
        "current_ratio": latest_eval.current_ratio if latest_eval else 1.45,
        "dscr": latest_eval.dscr if latest_eval else 1.48,
        "foir_pct": latest_eval.foir_pct if latest_eval else 48.5,
        "tol_tnw_ratio": latest_eval.tol_tnw_ratio if latest_eval else 2.10,
        "debtor_days": latest_eval.debtor_days if latest_eval else 65
    }

@router.get("/cma-excel")
def export_cma_excel(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    cma = db.query(CMAProject).filter(CMAProject.proposal_id == proposal_id).first()
    
    if cma and cma.data_json:
        cma_data = json.loads(cma.data_json)
    else:
        cma_data = generate_default_cma(
            base_turnover_fy24=Decimal("45000000.00"),
            requested_cc_limit=proposal.requested_amount,
            requested_term_loan=proposal.requested_amount * Decimal("0.5")
        )

    case_dir = get_case_dir(proposal.proposal_code)
    out_file = os.path.join(case_dir, f"CMA_{proposal.proposal_code}.xlsx")
    ReportGeneratorService.generate_cma_excel(cma_data, out_file, proposal.proposal_code)
    
    audit = AuditLog(
        user_id=current_user.id,
        client_id=proposal.client_id,
        proposal_id=proposal.id,
        action="EXPORT_EXCEL",
        resource_type="cma_report",
        resource_id=proposal.id,
        details_json="Exported 9-Year CMA Statement Excel"
    )
    db.add(audit)
    db.commit()

    return FileResponse(
        path=out_file,
        filename=f"CMA_Statement_{proposal.proposal_code}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.get("/dpr-word")
def export_dpr_word(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    dossier = _build_proposal_dossier_data(proposal, db)
    
    case_dir = get_case_dir(proposal.proposal_code)
    out_file = os.path.join(case_dir, f"DPR_{proposal.proposal_code}.docx")
    ReportGeneratorService.generate_dpr_word(dossier, out_file)
    
    audit = AuditLog(
        user_id=current_user.id,
        client_id=proposal.client_id,
        proposal_id=proposal.id,
        action="EXPORT_WORD",
        resource_type="dpr_report",
        resource_id=proposal.id,
        details_json="Exported Detailed Project Report (Word)"
    )
    db.add(audit)
    db.commit()

    return FileResponse(
        path=out_file,
        filename=f"Project_Report_{proposal.proposal_code}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@router.get("/bank-pdf")
def export_bank_pdf(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    dossier = _build_proposal_dossier_data(proposal, db)
    
    case_dir = get_case_dir(proposal.proposal_code)
    out_file = os.path.join(case_dir, f"Memorandum_{proposal.proposal_code}.pdf")
    ReportGeneratorService.generate_bank_pdf(dossier, out_file)
    
    audit = AuditLog(
        user_id=current_user.id,
        client_id=proposal.client_id,
        proposal_id=proposal.id,
        action="EXPORT_PDF",
        resource_type="bank_pdf_memorandum",
        resource_id=proposal.id,
        details_json="Exported Bank Credit Appraisal Memorandum PDF"
    )
    db.add(audit)
    db.commit()

    return FileResponse(
        path=out_file,
        filename=f"Bank_Submission_{proposal.proposal_code}.pdf",
        media_type="application/pdf"
    )
