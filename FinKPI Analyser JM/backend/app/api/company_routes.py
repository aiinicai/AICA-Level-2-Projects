from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import CompanyModel, UserModel
from ..schemas import CompanyCreate, APIResponse
from ..auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/companies", tags=["Company"])

@router.get("", response_model=APIResponse)
def list_companies(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    companies = db.query(CompanyModel).all()
    res = [
        {
            "id": c.id,
            "company_code": c.company_code,
            "company_name": c.company_name,
            "industry": c.industry,
            "currency": c.currency,
            "currency_unit": c.currency_unit,
            "fiscal_year_start": c.fiscal_year_start,
            "shares_outstanding": c.shares_outstanding,
            "headcount": c.headcount,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in companies
    ]
    return APIResponse(success=True, statusCode=200, message="Companies retrieved successfully", data=res)

@router.post("", response_model=APIResponse)
def create_company(req: CompanyCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(require_role(["admin", "analyst"]))):
    existing = db.query(CompanyModel).filter(CompanyModel.company_code == req.company_code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Company with code '{req.company_code}' already exists")

    company = CompanyModel(
        company_code=req.company_code,
        company_name=req.company_name,
        industry=req.industry or "Manufacturing",
        currency=req.currency or "USD",
        currency_unit=req.currency_unit or "thousands",
        fiscal_year_start=req.fiscal_year_start or 1,
        shares_outstanding=req.shares_outstanding or 1000000.0,
        headcount=req.headcount or 500
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    return APIResponse(
        success=True,
        statusCode=201,
        message="Company created successfully",
        data={"id": company.id, "company_code": company.company_code, "company_name": company.company_name}
    )

@router.put("/{id}", response_model=APIResponse)
def update_company(id: str, req: CompanyCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(require_role(["admin", "analyst"]))):
    company = db.query(CompanyModel).filter(CompanyModel.id == id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.company_name = req.company_name
    company.industry = req.industry or company.industry
    company.currency = req.currency or company.currency
    company.currency_unit = req.currency_unit or company.currency_unit
    company.shares_outstanding = req.shares_outstanding or company.shares_outstanding
    company.headcount = req.headcount or company.headcount

    db.commit()
    return APIResponse(success=True, statusCode=200, message="Company updated successfully", data={"id": id})

@router.delete("/{id}", response_model=APIResponse)
def delete_company(id: str, db: Session = Depends(get_db), current_user: UserModel = Depends(require_role(["admin"]))):
    company = db.query(CompanyModel).filter(CompanyModel.id == id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    db.delete(company)
    db.commit()
    return APIResponse(success=True, statusCode=200, message="Company deleted successfully")
