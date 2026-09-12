import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Company, User, AuditLog, Asset
from ..schemas import CompanyOut, CompanyCreate, CompanyUpdate
from ..auth import get_current_user, require_admin
from ..config import LOGOS_DIR
from ..services.sequence_service import generate_next_asset_id

router = APIRouter(prefix="/api/companies", tags=["Companies"])

@router.get("", response_model=List[CompanyOut])
def get_companies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Company).order_by(Company.name.asc()).all()

@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.post("", response_model=CompanyOut)
def create_company(
    company_in: CompanyCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    existing = db.query(Company).filter(Company.short_name == company_in.short_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Company short name already exists")

    company = Company(
        **company_in.model_dump(),
        created_by=admin_user.id
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    # Audit log
    audit = AuditLog(
        user_id=admin_user.id,
        action="CREATE_COMPANY",
        entity_type="COMPANY",
        entity_id=str(company.id),
        details=f"Created company {company.name} (Prefix: {company.asset_id_prefix})",
        result="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    db.commit()

    return company

@router.put("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: int,
    company_in: CompanyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = company_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(company, field, val)

    db.commit()
    db.refresh(company)

    audit = AuditLog(
        user_id=admin_user.id,
        action="UPDATE_COMPANY",
        entity_type="COMPANY",
        entity_id=str(company.id),
        details=f"Updated company {company.name}",
        result="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    db.commit()

    return company

@router.post("/{company_id}/logo", response_model=CompanyOut)
async def upload_company_logo(
    company_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "png"
    if ext not in ["png", "jpg", "jpeg", "svg"]:
        raise HTTPException(status_code=400, detail="Unsupported image format. Allowed: PNG, JPG, JPEG, SVG")

    filename = f"company_{company.id}_logo.{ext}"
    file_path = LOGOS_DIR / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    company.logo_path = f"/uploads/logos/{filename}"
    db.commit()
    db.refresh(company)

    audit = AuditLog(
        user_id=admin_user.id,
        action="UPLOAD_LOGO",
        entity_type="COMPANY",
        entity_id=str(company.id),
        details=f"Uploaded logo for company {company.name}",
        result="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    db.commit()

    return company

@router.get("/{company_id}/next-asset-id")
def get_next_id(company_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    prefix = company.asset_id_prefix or "FA"
    format_str = company.numbering_format or "{PREFIX}-{NUM:6}"
    next_num = max(company.current_number or 0, (company.starting_number or 1) - 1) + 1

    rendered = format_str.replace("{PREFIX}", prefix)\
                         .replace("{NUM:6}", f"{next_num:06d}")\
                         .replace("{NUM:5}", f"{next_num:05d}")\
                         .replace("{NUM:4}", f"{next_num:04d}")\
                         .replace("{NUM}", str(next_num))
    if rendered == format_str:
        rendered = f"{prefix}-{next_num:06d}"

    return {"next_asset_id": rendered, "current_number": company.current_number}
