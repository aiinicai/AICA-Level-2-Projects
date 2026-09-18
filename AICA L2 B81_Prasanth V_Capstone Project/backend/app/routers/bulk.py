import io
import zipfile
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from PIL import Image, ImageDraw, ImageFont

from ..database import get_db
from ..models import Asset, Company, User, DuplicateOverride, AuditLog
from ..schemas import BulkValidationSummary, BulkGenerateRequest, AssetOut
from ..auth import get_current_user
from ..services.excel_service import generate_excel_template, parse_and_validate_excel
from ..services.sequence_service import generate_next_asset_id
from ..services.barcode_service import generate_barcode_image, generate_qr_image

router = APIRouter(prefix="/api/bulk", tags=["Bulk Operations"])

@router.get("/template")
def download_template():
    """
    Downloads the standard Excel bulk upload template.
    """
    stream = generate_excel_template()
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Asset_Upload_Template.xlsx"}
    )

@router.post("/validate", response_model=BulkValidationSummary)
async def validate_excel_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls") or file.filename.endswith(".csv")):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel (.xlsx) file.")

    content = await file.read()
    try:
        validation_result = parse_and_validate_excel(content, db)
        return validation_result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading Excel file: {str(e)}")

@router.post("/generate")
def generate_bulk_assets(
    payload: BulkGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    created_assets = []
    overrides_count = 0

    for row in payload.rows:
        # Determine company
        company = None
        if row.company_id:
            company = db.query(Company).filter(Company.id == row.company_id).first()
        elif row.company_name:
            company = db.query(Company).filter(
                (Company.name.ilike(row.company_name.strip())) | (Company.short_name.ilike(row.company_name.strip()))
            ).first()

        if not company:
            company = db.query(Company).first()

        if not company:
            continue

        target_asset_id = (row.asset_id or "").strip()
        if not target_asset_id:
            target_asset_id = generate_next_asset_id(db, company.id)

        # Check existing duplicate
        existing = db.query(Asset).filter(
            Asset.company_id == company.id,
            Asset.asset_id == target_asset_id
        ).first()

        is_ovr = False
        ovr_reason = row.override_reason

        if existing:
            if not ovr_reason:
                # Skip un-overridden duplicates
                continue
            is_ovr = True
            overrides_count += 1

        asset = Asset(
            company_id=company.id,
            asset_id=target_asset_id,
            asset_type=row.asset_type or "FIXED_ASSET",
            description=row.description or "Bulk Asset",
            location=row.location,
            sap_number=row.sap_number,
            serial_number=row.serial_number,
            department=row.department,
            cost_centre=row.cost_centre,
            custodian=row.custodian,
            purchase_date=row.purchase_date,
            code_type=row.code_type or "BARCODE",
            status="GENERATED",
            print_count=0,
            is_override=is_ovr,
            override_reason=ovr_reason,
            created_by=current_user.id
        )
        db.add(asset)
        db.flush()

        if is_ovr:
            db.add(DuplicateOverride(
                asset_id=asset.id,
                duplicate_asset_id=target_asset_id,
                company_id=company.id,
                user_id=current_user.id,
                justification_reason=ovr_reason,
                ip_address=request.client.host if request.client else "127.0.0.1"
            ))

        created_assets.append({
            "id": asset.id,
            "asset_id": asset.asset_id,
            "company_name": company.name,
            "description": asset.description
        })

    db.commit()

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="BULK_GENERATE",
        entity_type="ASSET",
        entity_id=f"Count: {len(created_assets)}",
        details=f"Generated {len(created_assets)} asset tags in bulk ({overrides_count} duplicate overrides)",
        result="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "count": len(created_assets),
        "overrides_count": overrides_count,
        "assets": created_assets
    }

@router.post("/download-zip")
def download_bulk_zip(asset_ids: List[int], db: Session = Depends(get_db)):
    """
    Creates a ZIP file containing high-resolution PNGs named with their respective Asset IDs.
    """
    assets = db.query(Asset).filter(Asset.id.in_(asset_ids)).all()
    if not assets:
        raise HTTPException(status_code=404, detail="No assets found for the provided IDs")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for asset in assets:
            width, height = 827, 413
            img = Image.new("RGBA", (width, height), "white")
            draw = ImageDraw.Draw(img)
            draw.rectangle([(2, 2), (width - 3, height - 3)], outline="#334155", width=3)

            try:
                font_header = ImageFont.truetype("arial.ttf", 26)
                font_bold = ImageFont.truetype("arialbd.ttf", 22)
                font_id = ImageFont.truetype("arialbd.ttf", 24)
            except Exception:
                font_header = ImageFont.load_default()
                font_bold = ImageFont.load_default()
                font_id = ImageFont.load_default()

            company_name = (asset.company.name if asset.company else "CORPORATE ASSET").upper()
            draw.text((width // 2, 35), company_name[:40], fill="#0F172A", font=font_header, anchor="mm")
            draw.line([(25, 60), (width - 25, 60)], fill="#CBD5E1", width=2)

            sap = asset.sap_number or "-"
            desc_txt = (asset.description or "").upper()
            loc = (asset.location or "-").upper()

            if "QR" in asset.code_type.upper():
                draw.text((35, 90), f"SAP NO       :  {sap}", fill="#1E293B", font=font_bold)
                draw.text((35, 140), f"DESCRIPTION :  {desc_txt[:25]}", fill="#1E293B", font=font_bold)
                draw.text((35, 190), f"LOCATION    :  {loc[:25]}", fill="#1E293B", font=font_bold)
                draw.text((35, 340), f"Asset ID: {asset.asset_id}", fill="#0F172A", font=font_id)

                qr_img = generate_qr_image(asset.asset_id, box_size=8, border=2)
                qr_img = qr_img.resize((240, 240))
                img.paste(qr_img, (width - 280, 85))
            else:
                draw.text((35, 80), f"SAP NO       :  {sap}", fill="#1E293B", font=font_bold)
                draw.text((35, 125), f"DESCRIPTION :  {desc_txt[:35]}", fill="#1E293B", font=font_bold)
                draw.text((35, 170), f"LOCATION    :  {loc[:35]}", fill="#1E293B", font=font_bold)
                draw.line([(25, 215), (width - 25, 215)], fill="#E2E8F0", width=2)

                bc_img = generate_barcode_image(asset.asset_id)
                bc_img = bc_img.resize((width - 120, 110))
                img.paste(bc_img, (60, 230))
                draw.text((width // 2, 375), asset.asset_id, fill="#0F172A", font=font_id, anchor="mm")

            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            safe_name = f"{asset.asset_id}.png".replace("/", "_").replace("\\", "_")
            zip_file.writestr(safe_name, img_bytes.getvalue())

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=Asset_Tags_Batch.zip"}
    )
