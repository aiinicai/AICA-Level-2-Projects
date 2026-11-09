from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user, require_role, verify_proposal_access
from backend.app.models.models import FinancialEvaluation, Proposal, User, AuditLog, ExistingFacility
from backend.app.schemas.schemas import (
    FinancialEvaluationInput, FinancialEvaluationResponse,
    ExistingFacilityCreate, ExistingFacilityResponse
)
from backend.app.services.financial_calculator import (
    calculate_emi,
    calculate_foir_eligibility,
    calculate_ltv_eligibility,
    calculate_dscr,
    calculate_dscr_eligibility,
    calculate_interest_coverage,
    calculate_working_capital_days,
    calculate_balance_sheet_ratios,
    resolve_limiting_factor_and_eligibility,
    round_inr,
    PRELIMINARY_ASSESSMENT_DISCLAIMER
)

router = APIRouter(prefix="/proposals/{proposal_id}/evaluation", tags=["Financial Evaluation Engine"])

@router.post("", response_model=FinancialEvaluationResponse)
def run_financial_evaluation(
    proposal_id: str,
    eval_in: FinancialEvaluationInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst", "reviewer"]))
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    
    # 1. Proposed EMI calculation
    proposed_emi = calculate_emi(
        principal=proposal.requested_amount,
        annual_rate_pct=eval_in.interest_rate,
        tenure_months=eval_in.tenure_months
    )
    
    # 2. FOIR & FOIR Eligibility
    foir_eligible, available_emi, current_foir = calculate_foir_eligibility(
        monthly_income=eval_in.monthly_income_or_cash_accrual,
        existing_monthly_emi=eval_in.total_existing_emi,
        max_foir_pct=eval_in.max_foir_pct,
        interest_rate_pct=eval_in.interest_rate,
        tenure_months=eval_in.tenure_months
    )
    
    # Total FOIR with requested loan
    total_new_emi = eval_in.total_existing_emi + proposed_emi
    observed_foir_pct = float(round((total_new_emi / eval_in.monthly_income_or_cash_accrual) * Decimal("100"), 2)) if eval_in.monthly_income_or_cash_accrual > 0 else 0.0

    # 3. Collateral LTV Eligibility
    is_secured = proposal.product_type not in ["business_loan_unsecured"]
    ltv_eligible = calculate_ltv_eligibility(
        collateral_market_value=eval_in.assessed_collateral_value,
        max_ltv_pct=eval_in.max_ltv_pct
    )
    observed_ltv_pct = float(round((proposal.requested_amount / eval_in.assessed_collateral_value) * Decimal("100"), 2)) if eval_in.assessed_collateral_value > 0 else 0.0

    # 4. DSCR & ICR
    annual_principal = proposed_emi * Decimal("12") + eval_in.existing_term_debt_repayment
    observed_dscr = calculate_dscr(
        pat=eval_in.pat,
        depreciation=eval_in.depreciation,
        finance_costs=eval_in.finance_costs,
        principal_repayments=annual_principal
    )
    
    dscr_eligible = calculate_dscr_eligibility(
        pat=eval_in.pat,
        depreciation=eval_in.depreciation,
        finance_costs=eval_in.finance_costs,
        existing_principal_repayments=eval_in.existing_term_debt_repayment,
        target_dscr=eval_in.min_dscr_target,
        interest_rate_pct=eval_in.interest_rate,
        tenure_months=eval_in.tenure_months
    )
    
    observed_icr = calculate_interest_coverage(
        ebitda=eval_in.ebitda,
        finance_costs=eval_in.finance_costs
    )

    # 5. Ratios & Working Capital Cycle
    bs_ratios = calculate_balance_sheet_ratios(
        current_assets=eval_in.current_assets,
        current_liabilities=eval_in.current_liabilities,
        inventory=eval_in.inventory,
        total_debt=eval_in.total_outside_liabilities - eval_in.current_liabilities,
        tangible_net_worth=eval_in.tangible_net_worth,
        total_outside_liabilities=eval_in.total_outside_liabilities
    )
    
    wc_days = calculate_working_capital_days(
        debtors=eval_in.sundry_debtors,
        creditors=eval_in.sundry_creditors,
        inventory=eval_in.inventory,
        turnover=eval_in.turnover,
        cogs=eval_in.cogs,
        purchases=eval_in.total_purchases
    )

    # 6. Limiting Constraint Resolution
    preliminary_amount, limiting_factor = resolve_limiting_factor_and_eligibility(
        product_type=proposal.product_type,
        requested_amount=proposal.requested_amount,
        foir_eligible=foir_eligible,
        ltv_eligible=ltv_eligible,
        dscr_eligible=dscr_eligible,
        is_secured=is_secured
    )

    # 7. Persist snapshot
    evaluation_record = FinancialEvaluation(
        proposal_id=proposal_id,
        version=1,
        monthly_income_or_cash_accrual=eval_in.monthly_income_or_cash_accrual,
        total_existing_emi=eval_in.total_existing_emi,
        proposed_emi=proposed_emi,
        foir_pct=observed_foir_pct,
        assessed_collateral_value=eval_in.assessed_collateral_value,
        ltv_pct=observed_ltv_pct,
        dscr=observed_dscr,
        icr=observed_icr,
        current_ratio=bs_ratios["current_ratio"],
        quick_ratio=bs_ratios["quick_ratio"],
        debt_equity_ratio=bs_ratios["debt_equity_ratio"],
        tol_tnw_ratio=bs_ratios["tol_tnw_ratio"],
        debtor_days=wc_days["debtor_days"],
        inventory_days=wc_days["inventory_days"],
        creditor_days=wc_days["creditor_days"],
        eligible_loan_foir=foir_eligible,
        eligible_loan_ltv=ltv_eligible,
        eligible_loan_dscr=dscr_eligible,
        preliminary_eligible_amount=preliminary_amount,
        limiting_factor=limiting_factor,
        is_snapshot=True
    )
    db.add(evaluation_record)
    db.commit()

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        client_id=proposal.client_id,
        proposal_id=proposal.id,
        action="EVALUATION_COMPLETED",
        resource_type="financial_evaluation",
        resource_id=evaluation_record.id,
        details_json=f"Eligibility: ₹ {preliminary_amount:,.2f} (Constrained by: {limiting_factor})"
    )
    db.add(audit)
    db.commit()

    return {
        "proposal_id": proposal_id,
        "requested_amount": proposal.requested_amount,
        "proposed_emi": proposed_emi,
        "foir_pct": observed_foir_pct,
        "ltv_pct": observed_ltv_pct,
        "dscr": observed_dscr,
        "icr": observed_icr,
        "current_ratio": bs_ratios["current_ratio"],
        "quick_ratio": bs_ratios["quick_ratio"],
        "debt_equity_ratio": bs_ratios["debt_equity_ratio"],
        "tol_tnw_ratio": bs_ratios["tol_tnw_ratio"],
        "debtor_days": wc_days["debtor_days"],
        "inventory_days": wc_days["inventory_days"],
        "creditor_days": wc_days["creditor_days"],
        "net_working_capital_cycle_days": wc_days["net_working_capital_cycle_days"],
        "eligible_loan_foir": foir_eligible,
        "eligible_loan_ltv": ltv_eligible,
        "eligible_loan_dscr": dscr_eligible,
        "preliminary_eligible_amount": preliminary_amount,
        "limiting_factor": limiting_factor,
        "disclaimer": PRELIMINARY_ASSESSMENT_DISCLAIMER
    }

@router.get("/existing-loans", response_model=List[ExistingFacilityResponse])
def get_existing_loans(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    loans = db.query(ExistingFacility).filter(ExistingFacility.entity_id == proposal.entity_id).all()
    return loans

@router.post("/existing-loans", response_model=ExistingFacilityResponse)
def add_existing_loan(
    proposal_id: str,
    facility_in: ExistingFacilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    facility = ExistingFacility(
        entity_id=proposal.entity_id,
        lender_name=facility_in.lender_name,
        facility_type=facility_in.facility_type,
        sanctioned_limit=facility_in.sanctioned_limit,
        outstanding_balance=facility_in.outstanding_balance,
        interest_rate=facility_in.interest_rate,
        monthly_emi=facility_in.monthly_emi,
        residual_tenure_months=facility_in.residual_tenure_months,
        primary_security=facility_in.primary_security,
        collateral_security=facility_in.collateral_security,
        sanction_date=facility_in.sanction_date,
        renewal_date=facility_in.renewal_date
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        client_id=proposal.client_id,
        proposal_id=proposal.id,
        action="ADD_EXISTING_LOAN",
        resource_type="existing_facility",
        resource_id=facility.id,
        details_json=f"Added loan {facility.lender_name} ({facility.facility_type}): Outstanding ₹{facility.outstanding_balance}, EMI ₹{facility.monthly_emi}"
    )
    db.add(audit)
    db.commit()
    return facility

@router.delete("/existing-loans/{facility_id}")
def delete_existing_loan(
    proposal_id: str,
    facility_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    facility = db.query(ExistingFacility).filter(
        ExistingFacility.id == facility_id,
        ExistingFacility.entity_id == proposal.entity_id
    ).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Existing loan facility not found")
    db.delete(facility)
    db.commit()
    return {"status": "success", "message": "Existing loan removed"}
