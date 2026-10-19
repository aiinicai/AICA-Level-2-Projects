from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, crud

router = APIRouter(prefix="/api/budgets", tags=["Budget Control"])

@router.get("", response_model=List[schemas.BudgetResponse])
def get_budgets(fiscal_year: int = Query(2026), db: Session = Depends(get_db)):
    budgets = db.query(models.Budget).filter(models.Budget.fiscal_year == fiscal_year).all()
    results = []
    for b in budgets:
        metrics = crud.get_account_budget_metrics(db, b.account_code, fiscal_year)
        results.append(schemas.BudgetResponse(
            id=b.id,
            fiscal_year=b.fiscal_year,
            account_code=b.account_code,
            account_name=metrics["account_name"],
            department=b.department,
            annual_budget=b.annual_budget,
            pre_encumbrance=metrics["pre_encumbrance"],
            encumbrance=metrics["encumbrance"],
            actual_consumed=metrics["actual_consumed"],
            available_budget=metrics["available_budget"],
            utilization_percentage=metrics["utilization_percentage"],
            notes=b.notes
        ))
    return results

@router.post("", response_model=schemas.BudgetResponse)
def create_or_update_budget(budget_in: schemas.BudgetCreate, db: Session = Depends(get_db)):
    acc = db.query(models.Account).filter(models.Account.account_code == budget_in.account_code).first()
    if not acc:
        raise HTTPException(status_code=404, detail="GL Account code not found")

    existing = db.query(models.Budget).filter(
        models.Budget.account_code == budget_in.account_code,
        models.Budget.fiscal_year == budget_in.fiscal_year
    ).first()

    if existing:
        existing.department = budget_in.department
        existing.annual_budget = budget_in.annual_budget
        existing.notes = budget_in.notes
        db.commit()
        db.refresh(existing)
        target = existing
    else:
        new_b = models.Budget(**budget_in.model_dump())
        db.add(new_b)
        db.commit()
        db.refresh(new_b)
        target = new_b

    metrics = crud.get_account_budget_metrics(db, target.account_code, target.fiscal_year)
    return schemas.BudgetResponse(
        id=target.id,
        fiscal_year=target.fiscal_year,
        account_code=target.account_code,
        account_name=metrics["account_name"],
        department=target.department,
        annual_budget=target.annual_budget,
        pre_encumbrance=metrics["pre_encumbrance"],
        encumbrance=metrics["encumbrance"],
        actual_consumed=metrics["actual_consumed"],
        available_budget=metrics["available_budget"],
        utilization_percentage=metrics["utilization_percentage"],
        notes=target.notes
    )

@router.post("/check", response_model=schemas.BudgetCheckResponse)
def check_budget(req: schemas.BudgetCheckRequest, db: Session = Depends(get_db)):
    return crud.check_budget_availability(db, req.account_code, req.amount)
