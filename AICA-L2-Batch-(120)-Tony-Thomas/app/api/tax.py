import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, crud

router = APIRouter(prefix="/api/tax", tags=["Taxation (VAT & Indirect Tax)"])

@router.get("/codes", response_model=List[schemas.TaxCodeResponse])
def get_tax_codes(db: Session = Depends(get_db)):
    return db.query(models.TaxCode).all()

@router.post("/codes", response_model=schemas.TaxCodeResponse)
def create_tax_code(code_in: schemas.TaxCodeCreate, db: Session = Depends(get_db)):
    existing = db.query(models.TaxCode).filter(models.TaxCode.code == code_in.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tax code already exists")
    tc = models.TaxCode(**code_in.model_dump())
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return tc

@router.get("/return-summary", response_model=schemas.TaxReturnReport)
def get_tax_return(
    from_date: Optional[datetime.date] = Query(None),
    to_date: Optional[datetime.date] = Query(None),
    db: Session = Depends(get_db)
):
    return crud.calculate_tax_return(db, from_date, to_date)
