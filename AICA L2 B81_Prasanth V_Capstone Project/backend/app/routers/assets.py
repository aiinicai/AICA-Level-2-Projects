import os
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func
from PIL import Image, ImageDraw, ImageFont

from ..database import get_db
from ..models import Asset, Company, User, DuplicateOverride, AuditLog
from ..schemas import (
    AssetCreate, AssetOut, DuplicateCheckRequest, DuplicateCheckResponse,
    DuplicateOverrideRequest, ReprintRequest
)
from ..auth import get_current_user
from ..config import BASE_DIR
from ..services.sequence_service import generate_next_asset_id
from ..services.barcode_service import generate_barcode_image, generate_qr_image, get_code_base64
from ..services.pdf_service import generate_single_label_pdf
from ..services.docx_service import generate_single_label_docx
from ..services.excel_service import export_assets_to_excel

router = APIRouter(prefix="/api/assets", tags=["Assets"])

@router.post("/check-duplicate", response_model=DuplicateCheckResponse)
def check_duplicate(
    payload: DuplicateCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    asset = db.query(Asset).filter(
        Asset.company_id == payload.company_id,
        Asset.asset_id == payload.asset_id.strip()
    ).first()

    if not asset:
        return {"is_duplicate": False, "existing_asset": None}

    return {
        "is_duplicate": True,
        "existing_asset": {
            "id": asset.id,
            "asset_id": asset.asset_id,
            "company_id": asset.company_id,
            "company_name": asset.company.name if asset.company else "N/A",
            "description": asset.description,
            "asset_type": asset.asset_type,
            "location": asset.location,
            "status": asset.status,
            "created_at": asset.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "created_by": asset.creator.full_name if asset.creator else "System"
        }
    }

@router.post("", response_model=AssetOut)
def create_asset(
    asset_in: AssetCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(Company.id == asset_in.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    target_asset_id = asset_in.asset_id.strip() if asset_in.asset_id else ""

    # If auto-generate requested
    if asset_in.auto_generate_id or not target_asset_id:
        target_asset_id = generate_next_asset_id(db, company.id)

    # Check duplicate
    existing = db.query(Asset).filter(
        Asset.company_id == company.id,
        Asset.asset_id == target_asset_id
    ).first()

    if existing:
        if not asset_in.is_override:
            # Audit log duplicate attempt
            audit = AuditLog(
                user_id=current_user.id,
                action="DUPLICATE_ATTEMPT",
                entity_type="ASSET",
                entity_id=target_asset_id,
                details=f"Attempted duplicate Asset ID {target_asset_id} for company {company.name}",
                result="BLOCKED",
                ip_address=request.client.host if request.client else "127.0.0.1"
            )
            db.add(audit)
            db.commit()
            raise HTTPException(
                status_code=400,
                detail=f"Duplicate Asset ID '{target_asset_id}' detected. An override justification is required."
            )
        else:
            if not asset_in.override_reason or len(asset_in.override_reason.strip()) < 5:
                raise HTTPException(status_code=400, detail="A mandatory justification comment of at least 5 characters is required for duplicate override.")

    # Create Asset record
    asset = Asset(
        company_id=company.id,
        asset_id=target_asset_id,
        asset_type=asset_in.asset_type,
        description=asset_in.description,
        location=asset_in.location,
        sap_number=asset_in.sap_number,
        serial_number=asset_in.serial_number,
        department=asset_in.department,
        cost_centre=asset_in.cost_centre,
        custodian=asset_in.custodian,
        purchase_date=asset_in.purchase_date,
        code_type=asset_in.code_type,
        status="GENERATED",
        print_count=0,
        is_override=asset_in.is_override,
        override_reason=asset_in.override_reason,
        created_by=current_user.id
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    # If this was an override, log to duplicate_overrides table
    if asset_in.is_override:
        ovr = DuplicateOverride(
            asset_id=asset.id,
            duplicate_asset_id=target_asset_id,
            company_id=company.id,
            user_id=current_user.id,
            justification_reason=asset_in.override_reason,
            ip_address=request.client.host if request.client else "127.0.0.1"
        )
        db.add(ovr)

    # Log action to audit
    audit = AuditLog(
        user_id=current_user.id,
        action="OVERRIDE_DUPLICATE" if asset_in.is_override else "GENERATE_TAG",
        entity_type="ASSET",
        entity_id=target_asset_id,
        details=f"{'Overridden duplicate' if asset_in.is_override else 'Generated'} Asset Tag {target_asset_id} ({asset.description})",
        result="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    db.commit()

    asset_out = AssetOut.model_validate(asset)
    asset_out.company_name = company.name
    asset_out.company_logo_path = company.logo_path
    return asset_out

@router.get("", response_model=List[AssetOut])
def get_assets(
    search: Optional[str] = None,
    company_id: Optional[int] = None,
    asset_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Asset)

    if company_id:
        query = query.filter(Asset.company_id == company_id)

    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)

    if status_filter:
        query = query.filter(Asset.status == status_filter)

    if search:
        s_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Asset.asset_id.ilike(s_term),
                Asset.sap_number.ilike(s_term),
                Asset.description.ilike(s_term),
                Asset.serial_number.ilike(s_term),
                Asset.location.ilike(s_term),
                Asset.custodian.ilike(s_term)
            )
        )

    assets = query.order_by(desc(Asset.created_at)).offset(skip).limit(limit).all()

    results = []
    for a in assets:
        out = AssetOut.model_validate(a)
        out.company_name = a.company.name if a.company else "N/A"
        out.company_logo_path = a.company.logo_path if a.company else None
        results.append(out)

    return results

@router.get("/export/excel")
def export_assets(
    company_id: Optional[int] = None,
    asset_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Asset)
    if company_id:
        query = query.filter(Asset.company_id == company_id)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)

    assets = query.order_by(desc(Asset.created_at)).all()
    excel_stream = export_assets_to_excel(assets)

    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Asset_Register_Export.xlsx"}
    )

@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    out = AssetOut.model_validate(asset)
    out.company_name = asset.company.name if asset.company else "N/A"
    out.company_logo_path = asset.company.logo_path if asset.company else None
    return out

@router.post("/{asset_id}/reprint", response_model=AssetOut)
def reprint_asset(
    asset_id: int,
    payload: ReprintRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.print_count += 1
    asset.status = "REPRINTED"
    db.commit()
    db.refresh(asset)

    # Audit log reprint
    audit = AuditLog(
        user_id=current_user.id,
        action="REPRINT_TAG",
        entity_type="ASSET",
        entity_id=asset.asset_id,
        details=f"Reprinted tag (Count: {asset.print_count}). Reason: {payload.reason}",
        result="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    db.commit()

    out = AssetOut.model_validate(asset)
    out.company_name = asset.company.name if asset.company else "N/A"
    out.company_logo_path = asset.company.logo_path if asset.company else None
    return out

@router.get("/{asset_id}/image")
def get_asset_image(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # High-resolution raster canvas rendering (827 x 413 px at 300 DPI for 70x35mm)
    width, height = 827, 413
    img = Image.new("RGBA", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Border
    draw.rectangle([(2, 2), (width - 3, height - 3)], outline="#334155", width=3)

    # Load default font
    try:
        font_header = ImageFont.truetype("arial.ttf", 26)
        font_bold = ImageFont.truetype("arialbd.ttf", 22)
        font_regular = ImageFont.truetype("arial.ttf", 22)
        font_id = ImageFont.truetype("arialbd.ttf", 24)
    except Exception:
        font_header = ImageFont.load_default()
        font_bold = ImageFont.load_default()
        font_regular = ImageFont.load_default()
        font_id = ImageFont.load_default()

    company_name = (asset.company.name if asset.company else "CORPORATE ASSET").upper()
    draw.text((width // 2, 35), company_name[:40], fill="#0F172A", font=font_header, anchor="mm")
    draw.line([(25, 60), (width - 25, 60)], fill="#CBD5E1", width=2)

    sap = asset.sap_number or "-"
    desc_txt = (asset.description or "").upper()
    loc = (asset.location or "-").upper()

    if "QR" in asset.code_type.upper():
        # Text left
        draw.text((35, 90), f"SAP NO       :  {sap}", fill="#1E293B", font=font_bold)
        draw.text((35, 140), f"DESCRIPTION :  {desc_txt[:25]}", fill="#1E293B", font=font_bold)
        draw.text((35, 190), f"LOCATION    :  {loc[:25]}", fill="#1E293B", font=font_bold)
        draw.text((35, 340), f"Asset ID: {asset.asset_id}", fill="#0F172A", font=font_id)

        # QR code right
        qr_img = generate_qr_image(asset.asset_id, box_size=8, border=2)
        qr_img = qr_img.resize((240, 240))
        img.paste(qr_img, (width - 280, 85))
    else:
        # Reference Barcode Layout
        draw.text((35, 80), f"SAP NO       :  {sap}", fill="#1E293B", font=font_bold)
        draw.text((35, 125), f"DESCRIPTION :  {desc_txt[:35]}", fill="#1E293B", font=font_bold)
        draw.text((35, 170), f"LOCATION    :  {loc[:35]}", fill="#1E293B", font=font_bold)
        draw.line([(25, 215), (width - 25, 215)], fill="#E2E8F0", width=2)

        # Barcode bottom
        bc_img = generate_barcode_image(asset.asset_id)
        bc_img = bc_img.resize((width - 120, 110))
        img.paste(bc_img, (60, 230))
        draw.text((width // 2, 375), asset.asset_id, fill="#0F172A", font=font_id, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    # Clean named file per requirement #22: FA-000001.png
    safe_filename = f"{asset.asset_id}.png".replace("/", "_").replace("\\", "_")

    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
    )

@router.get("/{asset_id}/pdf")
def get_asset_pdf(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset_dict = {
        "asset_id": asset.asset_id,
        "company_name": asset.company.name if asset.company else "CORPORATE ASSET",
        "sap_number": asset.sap_number,
        "description": asset.description,
        "location": asset.location,
        "code_type": asset.code_type
    }

    logo_full_path = None
    if asset.company and asset.company.logo_path:
        logo_full_path = os.path.join(BASE_DIR, asset.company.logo_path.lstrip("/"))

    pdf_buf = generate_single_label_pdf(asset_dict, width_mm=70.0, height_mm=35.0, logo_path=logo_full_path)
    safe_filename = f"{asset.asset_id}.pdf".replace("/", "_").replace("\\", "_")

    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
    )

@router.get("/{asset_id}/docx")
def get_asset_docx(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset_dict = {
        "asset_id": asset.asset_id,
        "company_name": asset.company.name if asset.company else "CORPORATE ASSET",
        "sap_number": asset.sap_number,
        "description": asset.description,
        "location": asset.location,
        "code_type": asset.code_type
    }

    docx_buf = generate_single_label_docx(asset_dict, width_mm=70.0, height_mm=35.0)
    safe_filename = f"{asset.asset_id}.docx".replace("/", "_").replace("\\", "_")

    return StreamingResponse(
        docx_buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
    )

@router.post("/preview-pdf")
def preview_single_pdf(payload: dict):
    asset_dict = {
        "asset_id": payload.get("asset_id", "FA-000001"),
        "company_name": payload.get("company_name", "REFERENCE COMPANY"),
        "sap_number": payload.get("sap_number"),
        "description": payload.get("description"),
        "location": payload.get("location"),
        "code_type": payload.get("code_type", "BARCODE")
    }
    width_mm = float(payload.get("width_mm", 70.0))
    height_mm = float(payload.get("height_mm", 35.0))
    pdf_buf = generate_single_label_pdf(asset_dict, width_mm=width_mm, height_mm=height_mm)
    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="preview.pdf"'}
    )

@router.post("/preview-docx")
def preview_single_docx(payload: dict):
    asset_dict = {
        "asset_id": payload.get("asset_id", "FA-000001"),
        "company_name": payload.get("company_name", "REFERENCE COMPANY"),
        "sap_number": payload.get("sap_number"),
        "description": payload.get("description"),
        "location": payload.get("location"),
        "code_type": payload.get("code_type", "BARCODE")
    }
    width_mm = float(payload.get("width_mm", 70.0))
    height_mm = float(payload.get("height_mm", 35.0))
    docx_buf = generate_single_label_docx(asset_dict, width_mm=width_mm, height_mm=height_mm)
    return StreamingResponse(
        docx_buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="tag_preview.docx"'}
    )

