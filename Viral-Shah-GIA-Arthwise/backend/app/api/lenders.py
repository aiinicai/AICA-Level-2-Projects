import json
from typing import List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user, verify_proposal_access
from backend.app.models.models import Lender, LenderPolicy, Proposal, FinancialEvaluation, Entity, Promoter, User
from backend.app.schemas.schemas import LenderPolicyResponse, PolicyFitEvaluation
from backend.app.services.lender_service import SEED_LENDERS, evaluate_lender_policy_fit

router = APIRouter(prefix="/lenders", tags=["Lender Policies & Matching"])

def seed_lenders_if_empty(db: Session):
    count = db.query(Lender).count()
    if count == 0:
        for seed in SEED_LENDERS:
            lender = Lender(
                code=seed["code"],
                name=seed["name"],
                category=seed["category"]
            )
            db.add(lender)
            db.commit()
            db.refresh(lender)
            
            for p in seed["policies"]:
                policy = LenderPolicy(
                    lender_id=lender.id,
                    product_type=p["product_type"],
                    policy_name=p["policy_name"],
                    min_loan=p["min_loan"],
                    max_loan=p["max_loan"],
                    max_foir=p["max_foir"],
                    max_ltv=p["max_ltv"],
                    min_dscr=p["min_dscr"],
                    min_icr=p["min_icr"],
                    min_cibil=p["min_cibil"],
                    min_vintage_years=p["min_vintage_years"],
                    min_turnover=p["min_turnover"],
                    benchmark_rate=p["benchmark_rate"],
                    required_docs_json=json.dumps(p["required_docs"])
                )
                db.add(policy)
        db.commit()

@router.get("/policies", response_model=List[LenderPolicyResponse])
def get_all_policies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    seed_lenders_if_empty(db)
    policies = db.query(LenderPolicy).filter(LenderPolicy.is_active == True).all()
    results = []
    for pol in policies:
        results.append({
            "id": pol.id,
            "lender_id": pol.lender_id,
            "lender_code": pol.lender.code,
            "lender_name": pol.lender.name,
            "lender_category": pol.lender.category,
            "product_type": pol.product_type,
            "policy_name": pol.policy_name,
            "min_loan": pol.min_loan,
            "max_loan": pol.max_loan,
            "max_foir": pol.max_foir,
            "max_ltv": pol.max_ltv,
            "min_dscr": pol.min_dscr,
            "min_icr": pol.min_icr,
            "min_cibil": pol.min_cibil,
            "min_vintage_years": pol.min_vintage_years,
            "min_turnover": pol.min_turnover,
            "benchmark_rate": pol.benchmark_rate,
            "required_docs": json.loads(pol.required_docs_json) if pol.required_docs_json else [],
            "is_active": pol.is_active
        })
    return results

@router.get("/compare/{proposal_id}", response_model=List[PolicyFitEvaluation])
def compare_lender_policies_for_proposal(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    seed_lenders_if_empty(db)
    
    # Get latest evaluation snapshot if exists
    latest_eval = db.query(FinancialEvaluation).filter(
        FinancialEvaluation.proposal_id == proposal_id
    ).order_by(FinancialEvaluation.created_at.desc()).first()
    
    # Get promoter cibil score
    entity = db.query(Entity).filter(Entity.id == proposal.entity_id).first()
    cibil_score = None
    if entity and entity.promoters:
        scores = [p.cibil_score for p in entity.promoters if p.cibil_score is not None]
        if scores:
            cibil_score = min(scores) # Conservative lowest score of promoters
            
    borrower_profile = {
        "requested_amount": float(proposal.requested_amount),
        "tenure_months": proposal.tenure_months,
        "monthly_income": float(latest_eval.monthly_income_or_cash_accrual) if latest_eval else 250000.0,
        "existing_emi": float(latest_eval.total_existing_emi) if latest_eval else 35000.0,
        "collateral_value": float(latest_eval.assessed_collateral_value) if latest_eval else 15000000.0,
        "cibil_score": cibil_score or 725,
        "vintage_years": 4.5,
        "turnover": 45000000.0,
        "dscr": float(latest_eval.dscr) if latest_eval else 1.45
    }
    
    # Fetch policies matching product
    policies = db.query(LenderPolicy).filter(
        LenderPolicy.is_active == True,
        LenderPolicy.product_type == proposal.product_type
    ).all()
    
    # If no exact product policy match found, test against relevant SME/Credit policies
    if not policies:
        policies = db.query(LenderPolicy).filter(LenderPolicy.is_active == True).all()

    evaluations = []
    for pol in policies:
        policy_dict = {
            "lender_code": pol.lender.code,
            "lender_name": pol.lender.name,
            "product_type": pol.product_type,
            "policy_name": pol.policy_name,
            "min_loan": pol.min_loan,
            "max_loan": pol.max_loan,
            "max_foir": pol.max_foir,
            "max_ltv": pol.max_ltv,
            "min_dscr": pol.min_dscr,
            "min_icr": pol.min_icr,
            "min_cibil": pol.min_cibil,
            "min_vintage_years": pol.min_vintage_years,
            "min_turnover": pol.min_turnover,
            "benchmark_rate": pol.benchmark_rate,
            "required_docs": json.loads(pol.required_docs_json) if pol.required_docs_json else []
        }
        res = evaluate_lender_policy_fit(policy_dict, borrower_profile)
        evaluations.append({
            "lender_id": pol.lender_id,
            "lender_code": res["lender_code"],
            "lender_name": res["lender_name"],
            "product_type": res["product_type"],
            "fit_status": res["fit_status"],
            "max_eligible_amount": res["max_eligible_amount"],
            "benchmark_rate": res["benchmark_rate"],
            "deviations": res["deviations"],
            "missing_inputs": res["missing_inputs"],
            "notes": f"Illustrative comparison against {pol.policy_name} underwriting standards."
        })
        
    return evaluations
