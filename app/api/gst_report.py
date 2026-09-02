from datetime import date
from typing import Optional, Union

from fastapi import APIRouter, Body, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_any_staff
from app.models.user import User
from app.services.gst_report_service import (
    _find_input,
    generate_b2cs_csv,
    generate_hsn_b2cs_csv,
    generate_pdf_gst_report,
    generate_table14_eco_csv,
    get_gst_payable_report,
    save_gst_adjustments,
)
from app.services.permission_service import assert_write, require_module

router = APIRouter(prefix="/api/gst-report", tags=["GST Payable Report"])


def parse_int_param(val: Optional[Union[int, str]]) -> Optional[int]:
    if val is None:
        return None
    text = str(val).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def parse_date_param(val: Optional[Union[date, str]]) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    text = str(val).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


@router.get("")
def gst_payable_report(
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff),
):
    require_module(user, "gst_report", "view")
    return get_gst_payable_report(
        db, parse_int_param(branch_id), parse_date_param(start_date), parse_date_param(end_date)
    )


@router.post("/adjustments")
def save_gst_report_adjustments(
    branch_id: Optional[int] = Body(None),
    start_date: date = Body(...),
    end_date: date = Body(...),
    mode: str = Body("less"),
    cash: float = Body(0.0),
    card_qr: float = Body(0.0),
    dineout: float = Body(0.0),
    zomato: float = Body(0.0),
    swiggy: float = Body(0.0),
    available_balance: float = Body(0.0),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff),
):
    existing = _find_input(db, branch_id, start_date, end_date)
    assert_write(user, "gst_report", bool(existing))
    return save_gst_adjustments(
        db, branch_id, start_date, end_date, mode, cash, card_qr, dineout, zomato, swiggy, available_balance
    )


@router.get("/export/pdf")
def export_gst_pdf(
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff),
):
    require_module(user, "gst_report", "view")
    payload = generate_pdf_gst_report(
        db, parse_int_param(branch_id), parse_date_param(start_date), parse_date_param(end_date)
    )
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=GST_Payable_Report.pdf"},
    )


@router.get("/export/b2cs")
def export_gst_b2cs_csv(
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff),
):
    require_module(user, "gst_report", "view")
    payload, filename = generate_b2cs_csv(
        db, parse_int_param(branch_id), parse_date_param(start_date), parse_date_param(end_date)
    )
    return Response(
        content=payload,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/hsn-b2cs")
def export_gst_hsn_b2cs_csv(
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff),
):
    require_module(user, "gst_report", "view")
    payload, filename = generate_hsn_b2cs_csv(
        db, parse_int_param(branch_id), parse_date_param(start_date), parse_date_param(end_date)
    )
    return Response(
        content=payload,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/table14")
def export_gst_table14_eco_csv(
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff),
):
    require_module(user, "gst_report", "view")
    payload, filename = generate_table14_eco_csv(
        db, parse_int_param(branch_id), parse_date_param(start_date), parse_date_param(end_date)
    )
    return Response(
        content=payload,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
