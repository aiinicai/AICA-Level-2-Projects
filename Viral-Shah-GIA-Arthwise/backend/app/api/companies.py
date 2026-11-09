import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user, require_role
from backend.app.models.models import CompanyProfile, AuditLog, User
from backend.app.schemas.schemas import (
    CompanyProfileCreate, CompanyProfileUpdate, CompanyProfileResponse
)

router = APIRouter(prefix="/companies", tags=["White-Labeling & Company Master"])

def seed_company_if_empty(db: Session):
    count = db.query(CompanyProfile).count()
    if count == 0:
        default_company = CompanyProfile(
            company_code="GIA",
            company_name="GIA Financial Advisory Services Private Limited",
            brand_name="GIA_Arthwise",
            tagline="Credit Appraisal, 9-Year CMA Projections & Bank Submission Suite",
            logo_data=None, # Stylized brand icon used by default
            primary_color="#1b2632",
            secondary_color="#a45139",
            website="https://giaarthwise.com",
            email="support@giaarthwise.com",
            phone=None,
            address=None,
            city="Vadodara",
            state="Gujarat",
            pin_code=None,
            pan=None,
            gstin=None,
            cin=None,
            is_active=True,
            is_default=True
        )
        db.add(default_company)
        db.commit()

@router.get("/active", response_model=CompanyProfileResponse)
def get_active_company(db: Session = Depends(get_db)):
    """
    Returns the currently active white-label company branding for the software.
    Used to dynamically brand headers, login screens, exports, and document footers.
    """
    active = db.query(CompanyProfile).filter(CompanyProfile.is_active == True).order_by(CompanyProfile.is_default.desc()).first()
    if not active:
        # Fallback to any company or seed
        seed_company_if_empty(db)
        active = db.query(CompanyProfile).first()
    return active

@router.get("", response_model=List[CompanyProfileResponse])
def list_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    List all created user companies / institutional tenants. Restricted to Administrator.
    """
    return db.query(CompanyProfile).order_by(CompanyProfile.created_at.desc()).all()

@router.post("", response_model=CompanyProfileResponse)
def create_company(
    company_in: CompanyProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Create a new user company / legal entity in the software with master creation and logo.
    Restricted to Administrator.
    """
    clean_code = company_in.company_code.strip().upper()
    existing = db.query(CompanyProfile).filter(CompanyProfile.company_code == clean_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company with code '{clean_code}' already exists."
        )

    new_comp = CompanyProfile(
        company_code=clean_code,
        company_name=company_in.company_name.strip(),
        brand_name=company_in.brand_name.strip(),
        tagline=company_in.tagline.strip() if company_in.tagline else None,
        logo_data=company_in.logo_data,
        primary_color=company_in.primary_color or "#1b2632",
        secondary_color=company_in.secondary_color or "#a45139",
        website=company_in.website,
        email=company_in.email,
        phone=company_in.phone,
        address=company_in.address,
        city=company_in.city,
        state=company_in.state,
        pin_code=company_in.pin_code,
        pan=company_in.pan,
        gstin=company_in.gstin,
        cin=company_in.cin,
        is_active=False,
        is_default=False
    )
    db.add(new_comp)
    db.commit()
    db.refresh(new_comp)

    audit = AuditLog(
        user_id=current_user.id,
        action="CREATE_COMPANY",
        resource_type="company",
        resource_id=new_comp.id,
        details_json=f"Created new white-label company '{new_comp.company_name}' ({new_comp.company_code})"
    )
    db.add(audit)
    db.commit()

    return new_comp

@router.put("/{company_id}", response_model=CompanyProfileResponse)
def update_company(
    company_id: str,
    update_in: CompanyProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Update company master information, branding colors, and logo. Restricted to Administrator.
    """
    comp = db.query(CompanyProfile).filter(CompanyProfile.id == company_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Company not found")

    for field, val in update_in.dict(exclude_unset=True).items():
        if val is not None:
            setattr(comp, field, val)

    audit = AuditLog(
        user_id=current_user.id,
        action="UPDATE_COMPANY",
        resource_type="company",
        resource_id=comp.id,
        details_json=f"Updated company details for '{comp.company_name}'"
    )
    db.add(audit)
    db.commit()
    db.refresh(comp)
    return comp

@router.post("/{company_id}/set-active", response_model=CompanyProfileResponse)
def set_active_company(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Set this company profile as the active white label across the entire platform.
    Restricted to Administrator.
    """
    comp = db.query(CompanyProfile).filter(CompanyProfile.id == company_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Company not found")

    # Set all others to is_active=False, is_default=False
    db.query(CompanyProfile).update({CompanyProfile.is_active: False, CompanyProfile.is_default: False})

    comp.is_active = True
    comp.is_default = True
    db.commit()
    db.refresh(comp)

    audit = AuditLog(
        user_id=current_user.id,
        action="ACTIVATE_COMPANY_WHITE_LABEL",
        resource_type="company",
        resource_id=comp.id,
        details_json=f"Set '{comp.company_name}' ({comp.brand_name}) as active white-label brand."
    )
    db.add(audit)
    db.commit()

    return comp

@router.post("/{company_id}/logo", response_model=CompanyProfileResponse)
async def upload_company_logo(
    company_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Upload corporate logo image for the company. Saves file and updates logo_data with relative path or data.
    Restricted to Administrator.
    """
    comp = db.query(CompanyProfile).filter(CompanyProfile.id == company_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Company not found")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".svg", ".webp"]:
        raise HTTPException(status_code=400, detail="Allowed logo formats: PNG, JPG, JPEG, SVG, WEBP")

    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    filename = f"logo_{comp.company_code.lower()}_{uuid.uuid4().hex[:6]}{ext}"
    dest_path = os.path.join(settings.STORAGE_DIR, filename)

    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    # Store accessible URL or relative path
    comp.logo_data = f"/api/v1/logos/{filename}"
    db.commit()
    db.refresh(comp)

    return comp
