from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app import company_manager, database, models, seed_data

router = APIRouter(prefix="/api/companies", tags=["Multi-Company Management & Security"])

class CompanyPublic(BaseModel):
    id: str
    company_name: str
    legal_name: str
    trn: str
    company_address: str
    currency: str
    currency_symbol: str
    phone: str
    email: str
    is_active: bool
    created_at: Optional[str] = None

class CreateCompanyRequest(BaseModel):
    company_name: str
    trn: str
    pin: str  # 4 digits
    company_address: Optional[str] = "Dubai, UAE"
    currency: Optional[str] = "AED"
    currency_symbol: Optional[str] = "AED"
    phone: Optional[str] = ""
    email: Optional[str] = ""

class SwitchCompanyRequest(BaseModel):
    company_id: str
    pin: str

class UpdateCompanyRequest(BaseModel):
    company_id: str
    company_name: str
    trn: str
    company_address: str
    currency: str
    currency_symbol: str
    phone: Optional[str] = ""
    email: Optional[str] = ""
    new_pin: Optional[str] = None

class DeleteCompanyRequest(BaseModel):
    pin: str

@router.get("", response_model=List[CompanyPublic])
def list_companies():
    companies = company_manager.load_companies()
    res = []
    for c in companies:
        res.append(CompanyPublic(
            id=c["id"],
            company_name=c["company_name"],
            legal_name=c.get("legal_name", c["company_name"]),
            trn=c.get("trn", ""),
            company_address=c.get("company_address", ""),
            currency=c.get("currency", "AED"),
            currency_symbol=c.get("currency_symbol", "AED"),
            phone=c.get("phone", ""),
            email=c.get("email", ""),
            is_active=c.get("is_active", False),
            created_at=c.get("created_at")
        ))
    return res

@router.get("/active", response_model=CompanyPublic)
def get_active_company():
    c = company_manager.get_active_company()
    return CompanyPublic(
        id=c["id"],
        company_name=c["company_name"],
        legal_name=c.get("legal_name", c["company_name"]),
        trn=c.get("trn", ""),
        company_address=c.get("company_address", ""),
        currency=c.get("currency", "AED"),
        currency_symbol=c.get("currency_symbol", "AED"),
        phone=c.get("phone", ""),
        email=c.get("email", ""),
        is_active=c.get("is_active", True),
        created_at=c.get("created_at")
    )

@router.post("/create", response_model=CompanyPublic)
def create_company(req: CreateCompanyRequest):
    if len(req.pin.strip()) != 4 or not req.pin.strip().isdigit():
        raise HTTPException(status_code=400, detail="Security PIN must be exactly 4 numeric digits (e.g. 1234).")
    
    try:
        new_comp = company_manager.create_new_company(
            company_name=req.company_name,
            trn=req.trn,
            pin=req.pin,
            company_address=req.company_address or "Dubai, UAE",
            currency=req.currency or "AED",
            currency_symbol=req.currency_symbol or "AED",
            phone=req.phone or "",
            email=req.email or ""
        )
        
        # Initialize SQLite database for this company
        db_path = new_comp["db_file"]
        sm = database.get_sessionmaker_for_path(db_path)
        db: Session = sm()
        try:
            # Seed clean standard COA with $0.00 balances and company settings
            seed_data.init_clean_database(db, force_reset=True)
            # Update company setting inside the company's DB
            cs = db.query(models.CompanySetting).first()
            if cs:
                cs.company_name = req.company_name.strip()
                cs.company_trn = req.trn.strip()
                cs.company_address = req.company_address.strip()
                cs.currency = req.currency.strip()
                cs.currency_symbol = req.currency_symbol.strip()
                cs.phone = req.phone.strip()
                cs.email = req.email.strip()
                db.commit()
        finally:
            db.close()
            
        return CompanyPublic(
            id=new_comp["id"],
            company_name=new_comp["company_name"],
            legal_name=new_comp["legal_name"],
            trn=new_comp["trn"],
            company_address=new_comp["company_address"],
            currency=new_comp["currency"],
            currency_symbol=new_comp["currency_symbol"],
            phone=new_comp["phone"],
            email=new_comp["email"],
            is_active=True,
            created_at=new_comp["created_at"]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify-pin")
def verify_pin(req: SwitchCompanyRequest):
    valid = company_manager.verify_company_pin(req.company_id, req.pin)
    if not valid:
        raise HTTPException(status_code=401, detail="Incorrect 4-digit security PIN for this company.")
    return {"valid": True, "message": "PIN verified successfully"}

@router.post("/switch", response_model=CompanyPublic)
def switch_company(req: SwitchCompanyRequest):
    try:
        active = company_manager.set_active_company(req.company_id, req.pin)
        return CompanyPublic(
            id=active["id"],
            company_name=active["company_name"],
            legal_name=active.get("legal_name", active["company_name"]),
            trn=active.get("trn", ""),
            company_address=active.get("company_address", ""),
            currency=active.get("currency", "AED"),
            currency_symbol=active.get("currency_symbol", "AED"),
            phone=active.get("phone", ""),
            email=active.get("email", ""),
            is_active=True,
            created_at=active.get("created_at")
        )
    except ValueError as ve:
        raise HTTPException(status_code=401, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/update", response_model=CompanyPublic)
def update_company(req: UpdateCompanyRequest, db: Session = Depends(database.get_db)):
    try:
        updated = company_manager.update_company_profile(
            company_id=req.company_id,
            company_name=req.company_name,
            trn=req.trn,
            company_address=req.company_address,
            currency=req.currency,
            currency_symbol=req.currency_symbol,
            phone=req.phone or "",
            email=req.email or "",
            new_pin=req.new_pin
        )
        
        # Also sync to CompanySetting in current DB
        cs = db.query(models.CompanySetting).first()
        if cs:
            cs.company_name = req.company_name.strip()
            cs.company_trn = req.trn.strip()
            cs.company_address = req.company_address.strip()
            cs.currency = req.currency.strip()
            cs.currency_symbol = req.currency_symbol.strip()
            cs.phone = (req.phone or "").strip()
            cs.email = (req.email or "").strip()
            db.commit()
            
        return CompanyPublic(
            id=updated["id"],
            company_name=updated["company_name"],
            legal_name=updated["legal_name"],
            trn=updated["trn"],
            company_address=updated["company_address"],
            currency=updated["currency"],
            currency_symbol=updated["currency_symbol"],
            phone=updated["phone"],
            email=updated["email"],
            is_active=updated.get("is_active", True),
            created_at=updated.get("created_at")
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{company_id}")
def delete_company_endpoint(company_id: str, req: DeleteCompanyRequest):
    try:
        return company_manager.delete_company(company_id, req.pin)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{company_id}/delete")
def delete_company_post(company_id: str, req: DeleteCompanyRequest):
    try:
        return company_manager.delete_company(company_id, req.pin)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

