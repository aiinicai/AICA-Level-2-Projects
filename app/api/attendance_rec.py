from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_any_staff
from app.services.permission_service import assert_write, require_module
from app.models.attendance import AttendanceMark, BankAdvance, Employee
from app.models.import_batch import ImportBatch
from app.models.user import User
from app.services.attendance_ocr import extract_attendance_from_images
from app.services.attendance_service import (
    apply_attendance_upload,
    enforce_leave_quota,
    get_attendance_matrix,
    get_or_create_employee,
    list_staff,
    normalize_mark,
    update_staff,
    upload_changes_saved_marks,
    upsert_bank_advance,
    upsert_mark,
)

router = APIRouter(prefix="/api/attendance", tags=["Attendance Reconciliation"])


@router.get("/matrix")
def attendance_matrix(
    branch_id: int,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff),
):
    today = date.today()
    return get_attendance_matrix(db, branch_id, year or today.year, month or today.month)


@router.post("/preview")
async def preview_attendance_sheet(
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    user: User = Depends(require_any_staff),
):
    require_module(user, "attendance", "enter")
    uploads: List[UploadFile] = []
    for item in files or []:
        if item and item.filename:
            uploads.append(item)
    if file and file.filename and not any(u.filename == file.filename for u in uploads):
        uploads.insert(0, file)
    if not uploads:
        raise HTTPException(status_code=400, detail="Upload 1 to 5 attendance photos.")
    if len(uploads) > 5:
        raise HTTPException(status_code=400, detail="Upload at most 5 attendance photos.")
    items = []
    for upload in uploads:
        items.append((await upload.read(), upload.filename or "attendance.jpg"))
    return extract_attendance_from_images(items)


@router.post("/confirm")
def confirm_attendance_import(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff),
):
    branch_id = int(payload.get("branch_id") or 0)
    year = int(payload.get("year") or 0)
    month = int(payload.get("month") or 0)
    employees = payload.get("employees") or []
    if not branch_id or not year or not month:
        raise HTTPException(status_code=400, detail="Branch, year and month are required.")
    assert_write(
        user,
        "attendance",
        upload_changes_saved_marks(db, branch_id, year, month, employees),
    )
    result = apply_attendance_upload(db, branch_id, year, month, employees)
    batch = ImportBatch(
        filename=str(payload.get("filename") or "Attendance_Register"),
        file_type="ATTENDANCE_REGISTER",
        source_name=f"Branch-{branch_id}",
        uploaded_by_id=user.id,
        total_rows=len(employees),
        success_rows=result["marks_written"],
        status="COMPLETED",
    )
    db.add(batch)
    db.commit()
    result["message"] = (
        f"Saved {result['marks_written']} day mark(s). "
        f"{len(result['added_employees'])} new staff added."
        if result["added_employees"]
        else f"Saved {result['marks_written']} day mark(s)."
    )
    return result


@router.post("/mark")
def save_one_mark(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff),
):
    emp = db.query(Employee).filter(Employee.id == int(payload.get("employee_id") or 0)).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Staff member not found.")
    work_date = date.fromisoformat(str(payload.get("work_date")))
    existing_mark = (
        db.query(AttendanceMark)
        .filter(AttendanceMark.employee_id == emp.id, AttendanceMark.work_date == work_date)
        .first()
    )
    assert_write(user, "attendance", bool(existing_mark))
    raw_mark = payload.get("mark")
    if not str(raw_mark or "").strip():
        rec = (
            db.query(AttendanceMark)
            .filter(AttendanceMark.employee_id == emp.id, AttendanceMark.work_date == work_date)
            .first()
        )
        if rec:
            db.delete(rec)
            db.commit()
        return {"ok": True, "cleared": True}
    mark, err = enforce_leave_quota(db, emp, work_date, raw_mark, reject_extra=True)
    if err:
        raise HTTPException(status_code=400, detail=err)
    upsert_mark(db, emp, work_date, mark, raw_mark=str(raw_mark))
    db.commit()
    return {"ok": True, "mark": mark}


@router.post("/bank-advance")
def save_bank_advance(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff),
):
    emp = db.query(Employee).filter(Employee.id == int(payload.get("employee_id") or 0)).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Staff member not found.")
    year = int(payload.get("year") or 0)
    month = int(payload.get("month") or 0)
    if year < 2000 or month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Valid year and month are required.")
    existing = (
        db.query(BankAdvance)
        .filter(
            BankAdvance.employee_id == emp.id,
            BankAdvance.year == year,
            BankAdvance.month == month,
        )
        .first()
    )
    assert_write(user, "attendance", bool(existing))
    rec = upsert_bank_advance(db, emp, year, month, payload.get("amount") or 0)
    return {"ok": True, "employee_id": emp.id, "amount": rec.amount}


@router.get("/staff")
def get_staff_master(
    branch_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff),
):
    return list_staff(db, branch_id)


@router.put("/staff/{employee_id}")
def save_staff_master(
    employee_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff),
):
    assert_write(user, "attendance", True)
    emp = update_staff(db, employee_id, payload)
    if not emp:
        raise HTTPException(status_code=404, detail="Staff member not found.")
    return {"id": emp.id, "name": emp.name, "ok": True}


@router.post("/employee")
def add_employee_manual(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff),
):
    require_module(user, "attendance", "enter")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required.")
    emp, created = get_or_create_employee(
        db,
        int(payload.get("branch_id") or 0),
        name,
        rank=payload.get("rank"),
        team=payload.get("team"),
        seen_on=date.today(),
        monthly_salary=payload.get("monthly_salary"),
    )
    if payload.get("monthly_salary") is not None:
        emp.monthly_salary = float(payload.get("monthly_salary") or 0)
    db.commit()
    return {"id": emp.id, "name": emp.name, "created": created}
