import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import LabelSize, Asset, Company, AuditLog, User
from ..schemas import LabelSizeOut, LabelSizeCreate, SheetLayoutConfig, DirectPrintJob
from ..auth import get_current_user
from ..config import BASE_DIR
from ..services.pdf_service import generate_sheet_pdf, generate_single_label_pdf
from ..services.docx_service import generate_sheet_docx
from ..services.printer_service import get_installed_printers, print_raw_or_pdf

router = APIRouter(prefix="/api/printing", tags=["Printing"])

@router.get("/label-sizes", response_model=List[LabelSizeOut])
def get_label_sizes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(LabelSize).order_by(LabelSize.is_preset.desc(), LabelSize.name.asc()).all()

@router.post("/label-sizes", response_model=LabelSizeOut)
def create_label_size(
    payload: LabelSizeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    size = LabelSize(**payload.model_dump())
    db.add(size)
    db.commit()
    db.refresh(size)
    return size

@router.get("/printers")
def list_printers(current_user: User = Depends(get_current_user)):
    return get_installed_printers()

@router.post("/calculate-sheet")
def calculate_sheet_layout(
    config: SheetLayoutConfig,
    item_count: int = Query(default=1, ge=1)
):
    """
    Intelligently computes the optimal layout matrix (cols x rows) on A4/A3 sheets.
    """
    page_dimensions = {
        "A4": {"w": 210.0, "h": 297.0},
        "A3": {"w": 297.0, "h": 420.0},
        "LETTER": {"w": 215.9, "h": 279.4}
    }
    dims = page_dimensions.get(config.page_size.upper(), page_dimensions["A4"])
    
    if config.orientation.upper() == "LANDSCAPE":
        page_w, page_h = dims["h"], dims["w"]
    else:
        page_w, page_h = dims["w"], dims["h"]

    usable_w = page_w - config.margin_left_mm - config.margin_right_mm
    usable_h = page_h - config.margin_top_mm - config.margin_bottom_mm

    cols = config.columns or max(1, int((usable_w + config.horizontal_gap_mm) / (config.label_width_mm + config.horizontal_gap_mm)))
    rows = config.rows or max(1, int((usable_h + config.vertical_gap_mm) / (config.label_height_mm + config.vertical_gap_mm)))

    labels_per_page = cols * rows
    estimated_pages = (item_count + labels_per_page - 1) // labels_per_page if labels_per_page > 0 else 1

    return {
        "page_size": config.page_size,
        "orientation": config.orientation,
        "page_dimensions_mm": {"width": page_w, "height": page_h},
        "label_dimensions_mm": {"width": config.label_width_mm, "height": config.label_height_mm},
        "columns": cols,
        "rows": rows,
        "labels_per_page": labels_per_page,
        "total_items": item_count,
        "estimated_pages": estimated_pages,
        "efficiency_score": f"{min(100, int((labels_per_page * config.label_width_mm * config.label_height_mm) / (usable_w * usable_h) * 100))}%"
    }

@router.post("/generate-sheet-pdf")
def generate_sheet(
    config: SheetLayoutConfig,
    asset_ids: List[int] = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    assets = db.query(Asset).filter(Asset.id.in_(asset_ids)).all()
    if not assets:
        raise HTTPException(status_code=404, detail="No assets selected")

    assets_data = []
    for a in assets:
        logo_full_path = None
        if a.company and a.company.logo_path:
            logo_full_path = os.path.join(BASE_DIR, a.company.logo_path.lstrip("/"))

        assets_data.append({
            "asset_id": a.asset_id,
            "company_name": a.company.name if a.company else "CORPORATE ASSET",
            "sap_number": a.sap_number,
            "description": a.description,
            "location": a.location,
            "code_type": a.code_type,
            "logo_path": logo_full_path
        })
        a.status = "PRINTED"
        a.print_count += 1

    db.commit()

    pdf_stream = generate_sheet_pdf(
        assets_data=assets_data,
        page_size_name=config.page_size,
        orientation=config.orientation,
        label_width_mm=config.label_width_mm,
        label_height_mm=config.label_height_mm,
        margin_top_mm=config.margin_top_mm,
        margin_bottom_mm=config.margin_bottom_mm,
        margin_left_mm=config.margin_left_mm,
        margin_right_mm=config.margin_right_mm,
        horizontal_gap_mm=config.horizontal_gap_mm,
        vertical_gap_mm=config.vertical_gap_mm,
        custom_cols=config.columns,
        custom_rows=config.rows
    )

    return StreamingResponse(
        pdf_stream,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Asset_Tags_Sheet.pdf"}
    )

@router.post("/generate-sheet-docx")
def generate_docx(
    config: SheetLayoutConfig,
    asset_ids: List[int] = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    assets = db.query(Asset).filter(Asset.id.in_(asset_ids)).all()
    if not assets:
        raise HTTPException(status_code=404, detail="No assets selected")

    assets_data = []
    for a in assets:
        assets_data.append({
            "asset_id": a.asset_id,
            "company_name": a.company.name if a.company else "CORPORATE ASSET",
            "sap_number": a.sap_number,
            "description": a.description,
            "location": a.location,
            "code_type": a.code_type
        })
        a.status = "PRINTED"
        a.print_count += 1

    db.commit()

    docx_stream = generate_sheet_docx(
        assets_data=assets_data,
        columns=config.columns or 2,
        rows_per_page=config.rows or 7,
        page_size=config.page_size
    )

    return StreamingResponse(
        docx_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=Asset_Tags_Sheet.docx"}
    )

@router.post("/direct-print")
def direct_label_print(
    job: DirectPrintJob,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    assets = db.query(Asset).filter(Asset.id.in_(job.asset_ids)).all()
    if not assets:
        raise HTTPException(status_code=404, detail="No assets found to print")

    label_size = None
    if job.label_size_id:
        label_size = db.query(LabelSize).filter(LabelSize.id == job.label_size_id).first()

    w_mm = label_size.width_mm if label_size else 70.0
    h_mm = label_size.height_mm if label_size else 35.0

    success_count = 0
    for a in assets:
        logo_full = None
        if a.company and a.company.logo_path:
            logo_full = os.path.join(BASE_DIR, a.company.logo_path.lstrip("/"))

        ast_data = {
            "asset_id": a.asset_id,
            "company_name": a.company.name if a.company else "CORPORATE ASSET",
            "sap_number": a.sap_number,
            "description": a.description,
            "location": a.location,
            "code_type": a.code_type
        }

        pdf_buf = generate_single_label_pdf(ast_data, width_mm=w_mm, height_mm=h_mm, logo_path=logo_full)
        pdf_bytes = pdf_buf.getvalue()

        for _ in range(job.copies):
            ok = print_raw_or_pdf(job.printer_name, pdf_bytes)
            if ok:
                success_count += 1

        a.status = "PRINTED"
        a.print_count += job.copies

    db.commit()

    audit = AuditLog(
        user_id=current_user.id,
        action="DIRECT_PRINT",
        entity_type="PRINTER",
        entity_id=job.printer_name,
        details=f"Sent {len(assets)} labels to printer '{job.printer_name}'",
        result="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "printer": job.printer_name,
        "jobs_sent": success_count,
        "assets_count": len(assets)
    }
