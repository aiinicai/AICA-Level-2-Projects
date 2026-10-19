from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/settings", tags=["Company Settings"])

@router.get("", response_model=schemas.CompanySettingResponse)
def get_company_setting(db: Session = Depends(get_db)):
    setting = db.query(models.CompanySetting).first()
    if not setting:
        setting = models.CompanySetting(
            company_name="Demo Business 48",
            company_trn="DEMO-TRN",
            company_address="Fictional Demo Address",
            currency="USD",
            currency_symbol="$",
            phone="DEMO-PHONE",
            email="demo@example.com"
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting

@router.post("", response_model=schemas.CompanySettingResponse)
def update_company_setting(update_in: schemas.CompanySettingUpdate, db: Session = Depends(get_db)):
    setting = db.query(models.CompanySetting).first()
    if not setting:
        setting = models.CompanySetting(**update_in.model_dump())
        db.add(setting)
    else:
        setting.company_name = update_in.company_name
        setting.company_trn = update_in.company_trn
        setting.company_address = update_in.company_address
        setting.currency = update_in.currency
        setting.currency_symbol = update_in.currency_symbol
        setting.phone = update_in.phone
        setting.email = update_in.email
    db.commit()
    db.refresh(setting)

    # Sync to active company in registry
    try:
        from app import company_manager
        active = company_manager.get_active_company()
        if active:
            company_manager.update_company_profile(
                company_id=active["id"],
                company_name=setting.company_name,
                trn=setting.company_trn,
                company_address=setting.company_address,
                currency=setting.currency,
                currency_symbol=setting.currency_symbol,
                phone=setting.phone or "",
                email=setting.email or ""
            )
    except Exception:
        pass

    return setting
