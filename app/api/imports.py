from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import date
from app.core.database import get_db
from app.core.dependencies import require_accounts_or_admin, require_any_staff
from app.services.permission_service import assert_write, require_module
from app.services import import_service, cash_service
from app.services.image_ocr_service import parse_image_to_dict, parse_images_to_merged_dict
from app.models.user import User
from app.models.import_batch import ImportBatch, ImportErrorLog
from app.models.daily_sales import DailySale
from app.models.payment_channel import PaymentChannel
from app.models.ocr_audit import OCRAuditLog
from app.core.config import BASE_DIR

router = APIRouter(prefix="/api/imports", tags=["Import Pipeline"])

import logging
logger = logging.getLogger("api_imports")


@router.get("/ai-ocr-status")
def ai_ocr_status(user: User = Depends(require_any_staff)):
    from app.services.ai_vision_ocr import ai_ocr_configured
    return {"configured": ai_ocr_configured()}


@router.post("/ai-ocr-key")
def save_ai_ocr_key(
    payload: Dict[str, Any] = Body(...),
    user: User = Depends(require_accounts_or_admin),
):
    """Store Gemini key locally. Used only for day-book photo reading."""
    key = str(payload.get("key") or "").strip()
    if len(key) < 20:
        raise HTTPException(status_code=400, detail="That does not look like a Gemini API key.")
    dest = BASE_DIR / "data" / "gemini_key.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(key, encoding="utf-8")
    return {"ok": True}

@router.post("/preview-image")
async def preview_image_ocr(
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    require_module(user, "daybook", "enter")
    uploads: List[UploadFile] = []
    for item in (files or []):
        if item and item.filename:
            uploads.append(item)
    if file and file.filename and not any(u.filename == file.filename for u in uploads):
        uploads.insert(0, file)
    if not uploads:
        raise HTTPException(status_code=400, detail="Upload 1 to 5 photos of the same day.")
    if len(uploads) > 5:
        raise HTTPException(status_code=400, detail="Upload at most 5 photos for the same day.")

    items = []
    for upload in uploads:
        items.append((await upload.read(), upload.filename or "register.jpg"))
    names = ", ".join(name for _, name in items)
    try:
        if len(items) == 1:
            extracted = parse_image_to_dict(items[0][0], items[0][1])
        else:
            extracted = parse_images_to_merged_dict(items)

        if extracted.get("status") == "ERROR":
            logger.error("Image parsing error for %s: %s", names, extracted.get("error_detail"))
            return extracted

        try:
            slim_rows = []
            for row in (extracted.get("parsed_rows") or []):
                slim = dict(row)
                slim.pop("row_crop_b64", None)
                slim.pop("description_crop_b64", None)
                slim_rows.append(slim)
            audit_log = OCRAuditLog(
                filename=names or "register.jpg",
                original_image_b64=(extracted.get("image_b64") or "")[:200000],
                preprocessed_image_b64=(extracted.get("preprocessed_image_b64") or "")[:200000],
                amount_crop_b64=extracted.get("amount_crop_b64"),
                raw_ocr_response=extracted.get("raw_ocr_response"),
                parsed_rows=slim_rows,
                field_mapping=extracted.get("fields"),
                extraction_trace=extracted.get("extraction_trace"),
                handwritten_total=extracted.get("handwritten_total"),
                calculated_total=extracted.get("calculated_total", 0.0),
                total_difference=extracted.get("total_difference", 0.0)
            )
            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)
            extracted["audit_id"] = audit_log.id
        except Exception as audit_exc:
            logger.warning("OCR audit log save skipped: %s", audit_exc)
            db.rollback()
            extracted["audit_id"] = None

        return extracted
    except Exception as e:
        logger.exception("IMAGE PROCESSING PIPELINE FAILURE on file %s", names)
        return {
            "status": "ERROR",
            "error_detail": str(e),
            "filename": names,
            "file_size": sum(len(content) for content, _ in items),
            "last_step": "ONLINE AI VISION OCR"
        }

@router.get("/ocr-audit/{audit_id}")
def get_ocr_audit_log(
    audit_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    audit = db.query(OCRAuditLog).filter(OCRAuditLog.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="OCR audit record not found.")
    return audit

@router.post("/reprocess-row")
async def reprocess_single_row_endpoint(
    row_id: int = Body(...),
    y_top: int = Body(...),
    y_bottom: int = Body(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    require_module(user, "daybook", "enter")
    content = await file.read()
    try:
        import cv2
        import numpy as np
        from app.services.image_ocr_service import analyze_isolated_row_crop, classify_row_description
        
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file.")
            
        row_data = analyze_isolated_row_crop(img, row_id=row_id, y_top=y_top, y_bottom=y_bottom)
        cat, class_conf = classify_row_description(row_data["description_raw"])
        row_data["category"] = cat
        row_data["classification_confidence"] = class_conf
        return row_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/confirm-image-import")
def confirm_image_import(
    branch_id: int = Body(...),
    sale_date: date = Body(...),
    cash: float = Body(0.0),
    card_qr: float = Body(0.0),
    zomato: float = Body(0.0),
    swiggy: float = Body(0.0),
    dineout: float = Body(0.0),
    opening_balance: float = Body(0.0),
    site_expenses: float = Body(0.0),
    salary_advance: float = Body(0.0),
    salary_advance_splits: Optional[List[Dict[str, Any]]] = Body(None),
    closing_balance: Optional[float] = Body(None),
    audit_id: Optional[int] = Body(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    already = db.query(DailySale).filter(
        DailySale.branch_id == branch_id, DailySale.sale_date == sale_date
    ).first()
    assert_write(user, "daybook", bool(already))
    # 1. Save or update Daily Sales in Day Book
    channels = db.query(PaymentChannel).filter(PaymentChannel.is_active == True).all()
    channel_map = {c.code.upper(): c.id for c in channels}
    
    # Cash
    if "CASH" in channel_map:
        db.query(DailySale).filter(DailySale.branch_id == branch_id, DailySale.sale_date == sale_date, DailySale.payment_channel_id == channel_map["CASH"]).delete()
        db.add(DailySale(branch_id=branch_id, sale_date=sale_date, payment_channel_id=channel_map["CASH"], amount=cash))

    # Card / QR
    if "CARD_QR" in channel_map:
        db.query(DailySale).filter(DailySale.branch_id == branch_id, DailySale.sale_date == sale_date, DailySale.payment_channel_id == channel_map["CARD_QR"]).delete()
        db.add(DailySale(branch_id=branch_id, sale_date=sale_date, payment_channel_id=channel_map["CARD_QR"], amount=card_qr))

    # Zomato
    if "ZOMATO" in channel_map:
        db.query(DailySale).filter(DailySale.branch_id == branch_id, DailySale.sale_date == sale_date, DailySale.payment_channel_id == channel_map["ZOMATO"]).delete()
        db.add(DailySale(branch_id=branch_id, sale_date=sale_date, payment_channel_id=channel_map["ZOMATO"], amount=zomato))

    # Swiggy
    if "SWIGGY" in channel_map:
        db.query(DailySale).filter(DailySale.branch_id == branch_id, DailySale.sale_date == sale_date, DailySale.payment_channel_id == channel_map["SWIGGY"]).delete()
        db.add(DailySale(branch_id=branch_id, sale_date=sale_date, payment_channel_id=channel_map["SWIGGY"], amount=swiggy))

    # Dineout
    if "DINEOUT" in channel_map:
        db.query(DailySale).filter(DailySale.branch_id == branch_id, DailySale.sale_date == sale_date, DailySale.payment_channel_id == channel_map["DINEOUT"]).delete()
        db.add(DailySale(branch_id=branch_id, sale_date=sale_date, payment_channel_id=channel_map["DINEOUT"], amount=dineout))

    db.commit()

    # 2. Save or update Cash Reconciliation
    adv_1_5 = salary_advance if 1 <= sale_date.day <= 5 else 0.0
    adv_6_15 = salary_advance if 6 <= sale_date.day <= 15 else 0.0
    adv_16_31 = salary_advance if 16 <= sale_date.day <= 31 else 0.0

    rec = cash_service.create_or_update_cash_reconciliation(
        db=db,
        branch_id=branch_id,
        rec_date=sale_date,
        data={
            "opening_balance": opening_balance,
            "site_expenses_inv_rec": site_expenses,
            "advance_salary_1_5": adv_1_5,
            "advance_salary_6_15": adv_6_15,
            "advance_salary_16_31": adv_16_31,
            "actual_closing_balance": round(
                closing_balance if closing_balance is not None
                else (opening_balance + cash - site_expenses - salary_advance),
                2,
            ),
            "remarks": "Imported from register image photo"
        },
        user=user
    )

    from app.services.attendance_service import replace_salary_advances_for_date
    replace_salary_advances_for_date(db, branch_id, sale_date, salary_advance_splits or [])

    # 3. Update OCRAuditLog with final user-approved values
    final_dict = {
        "cash": cash,
        "card_qr": card_qr,
        "zomato": zomato,
        "swiggy": swiggy,
        "dineout": dineout,
        "opening_balance": opening_balance,
        "site_expenses": site_expenses,
        "salary_advance": salary_advance,
        "closing_balance": closing_balance
    }

    if audit_id:
        audit_rec = db.query(OCRAuditLog).filter(OCRAuditLog.id == audit_id).first()
        if audit_rec:
            audit_rec.final_saved_values = final_dict
            db.commit()

    # Log batch
    batch = ImportBatch(
        filename="Image_Register_Upload",
        file_type="IMAGE_REGISTER",
        source_name=f"Branch-{branch_id}",
        uploaded_by_id=user.id,
        total_rows=1,
        success_rows=1,
        status="COMPLETED"
    )
    db.add(batch)
    db.commit()

    cash_service.post_daybook_to_related_tabs(db, branch_id, sale_date, sale_date, user=user)

    return {"message": "Image sales & cash reconciliation saved successfully!", "date": sale_date.strftime("%Y-%m-%d"), "cash_rec_id": rec.id}

@router.post("/daily-sales")
async def upload_daily_sales(
    branch_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    assert_write(user, "daybook", False)
    content = await file.read()
    try:
        batch = import_service.process_daily_sales_import(
            db, content, file.filename, branch_id, user=user
        )
        return {
            "batch_id": batch.id,
            "status": batch.status,
            "total_rows": batch.total_rows,
            "success_rows": batch.success_rows,
            "failed_rows": batch.failed_rows,
            "duplicate_rows": batch.duplicate_rows
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bank-statement")
async def upload_bank_statement(
    bank_account: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    assert_write(user, "card_qr", False)
    content = await file.read()
    try:
        batch = import_service.process_bank_statement_import(
            db, content, file.filename, bank_account, user=user
        )
        from app.services import matching_engine
        match = matching_engine.run_card_qr_auto_matching(db, user=user)
        return {
            "batch_id": batch.id,
            "status": batch.status,
            "total_rows": batch.total_rows,
            "success_rows": batch.success_rows,
            "failed_rows": batch.failed_rows,
            "duplicate_rows": batch.duplicate_rows,
            "skipped_rows": getattr(batch, "_skipped_rows", 0),
            "import_mode": getattr(batch, "_import_mode", "BANK_STATEMENT"),
            "matched_count": match.get("matched_count", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/aggregator-settlement")
async def upload_aggregator_settlement(
    aggregator_id: int = Form(...),
    branch_id: int = Form(...),
    period_start_date: date = Form(...),
    period_end_date: date = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    assert_write(user, "aggregators", False)
    content = await file.read()
    try:
        batch, s_batch = import_service.process_aggregator_settlement_import(
            db, content, file.filename, aggregator_id, branch_id, period_start_date, period_end_date, user=user
        )
        return {
            "batch_id": batch.id,
            "settlement_batch_id": s_batch.id,
            "status": batch.status,
            "gross_sales": s_batch.gross_sales,
            "payout": s_batch.payout,
            "actual_difference": s_batch.actual_difference,
            "difference_adjustment": s_batch.difference_adjustment
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/batches")
def get_import_batches(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    batches = db.query(ImportBatch).order_by(ImportBatch.uploaded_at.desc()).limit(50).all()
    return batches

@router.get("/errors/{batch_id}")
def get_import_errors(
    batch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    errors = db.query(ImportErrorLog).filter(ImportErrorLog.import_batch_id == batch_id).all()
    return errors

@router.delete("/batch/{batch_id}")
def delete_import_batch_endpoint(
    batch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_accounts_or_admin)
):
    success = import_service.delete_import_batch(db, batch_id, user=user)
    if not success:
        raise HTTPException(status_code=404, detail="Import batch not found.")
    return {"message": f"Import batch {batch_id} deleted successfully!"}
