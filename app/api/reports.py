from fastapi import APIRouter, Depends, Response, Query
from sqlalchemy.orm import Session
from typing import Optional, Union
from datetime import date
from app.core.database import get_db
from app.core.dependencies import require_any_staff, require_admin
from app.services import report_service

router = APIRouter(prefix="/api/reports", tags=["Reports & Export"])


# ==============================================================================
# PARAMETER PARSER HELPERS (CONVERTS EMPTY STRINGS "" TO NONE)
# ==============================================================================
def parse_int_param(val: Optional[Union[int, str]]) -> Optional[int]:
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str:
        return None
    try:
        return int(val_str)
    except ValueError:
        return None

def parse_date_param(val: Optional[Union[date, str]]) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    val_str = str(val).strip()
    if not val_str:
        return None
    try:
        return date.fromisoformat(val_str)
    except ValueError:
        return None

def parse_str_param(val: Optional[str]) -> Optional[str]:
    if val is None:
        return None
    val_str = str(val).strip()
    return val_str if val_str else None


# ==============================================================================
# ANALYTICS DASHBOARD API
# ==============================================================================
@router.get("/analytics")
def get_analytics_data(
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_any_staff)
):
    b_id = parse_int_param(branch_id)
    s_dt = parse_date_param(start_date)
    e_dt = parse_date_param(end_date)
    return report_service.get_analytics_summary_data(db, b_id, s_dt, e_dt)


# ==============================================================================
# DAYBOOK EXPORTS (EXCEL & PDF)
# ==============================================================================
@router.get("/export/daybook")
@router.get("/export/daybook/excel")
def export_daybook_excel(
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_any_staff)
):
    b_id = parse_int_param(branch_id)
    s_dt = parse_date_param(start_date)
    e_dt = parse_date_param(end_date)
    xlsx_bytes = report_service.generate_excel_daybook_report(db, b_id, s_dt, e_dt)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Consolidated_Daybook_Report.xlsx"}
    )

@router.get("/export/daybook/pdf")
def export_daybook_pdf(
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_any_staff)
):
    b_id = parse_int_param(branch_id)
    s_dt = parse_date_param(start_date)
    e_dt = parse_date_param(end_date)
    pdf_bytes = report_service.generate_pdf_daybook_report(db, b_id, s_dt, e_dt)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=Consolidated_Daybook_Report.pdf"}
    )


# ==============================================================================
# CASH RECONCILIATION EXPORTS (EXCEL & PDF)
# ==============================================================================
@router.get("/export/cash-rec")
@router.get("/export/cash-rec/excel")
def export_cash_rec_excel(
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_any_staff)
):
    b_id = parse_int_param(branch_id)
    s_dt = parse_date_param(start_date)
    e_dt = parse_date_param(end_date)
    xlsx_bytes = report_service.generate_excel_cash_reconciliation_report(db, b_id, s_dt, e_dt)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Cash_Reconciliation_Report.xlsx"}
    )

@router.get("/export/cash-rec/pdf")
def export_cash_rec_pdf(
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_any_staff)
):
    b_id = parse_int_param(branch_id)
    s_dt = parse_date_param(start_date)
    e_dt = parse_date_param(end_date)
    pdf_bytes = report_service.generate_pdf_cash_reconciliation_report(db, b_id, s_dt, e_dt)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=Cash_Reconciliation_Report.pdf"}
    )


# ==============================================================================
# CARD / QR RECONCILIATION EXPORTS (EXCEL & PDF)
# ==============================================================================
@router.get("/export/card-qr")
@router.get("/export/card-qr/excel")
def export_card_qr_excel(
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_any_staff)
):
    b_id = parse_int_param(branch_id)
    s_dt = parse_date_param(start_date)
    e_dt = parse_date_param(end_date)
    st = parse_str_param(status)
    xlsx_bytes = report_service.generate_excel_card_qr_report(db, b_id, s_dt, e_dt, st)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Card_QR_Reconciliation_Report.xlsx"}
    )

@router.get("/export/card-qr/pdf")
def export_card_qr_pdf(
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_any_staff)
):
    b_id = parse_int_param(branch_id)
    s_dt = parse_date_param(start_date)
    e_dt = parse_date_param(end_date)
    st = parse_str_param(status)
    pdf_bytes = report_service.generate_pdf_card_qr_report(db, b_id, s_dt, e_dt, st)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=Card_QR_Reconciliation_Report.pdf"}
    )


# ==============================================================================
# AGGREGATOR EXPORTS (EXCEL & PDF)
# ==============================================================================
@router.get("/export/aggregator")
@router.get("/export/aggregator/excel")
def export_aggregator_excel(
    aggregator_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_any_staff)
):
    a_id = parse_int_param(aggregator_id)
    b_id = parse_int_param(branch_id)
    s_dt = parse_date_param(start_date)
    e_dt = parse_date_param(end_date)
    xlsx_bytes = report_service.generate_excel_aggregator_report(db, a_id, b_id, s_dt, e_dt)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Aggregator_Payout_Breakup_Report.xlsx"}
    )

@router.get("/export/aggregator/pdf")
def export_aggregator_pdf(
    aggregator_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_any_staff)
):
    a_id = parse_int_param(aggregator_id)
    b_id = parse_int_param(branch_id)
    s_dt = parse_date_param(start_date)
    e_dt = parse_date_param(end_date)
    pdf_bytes = report_service.generate_pdf_aggregator_report(db, a_id, b_id, s_dt, e_dt)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=Aggregator_Payout_Breakup_Report.pdf"}
    )


# ==============================================================================
# GST PAYABLE EXPORTS
# ==============================================================================
@router.get("/export/gst/pdf")
def export_gst_pdf(
    branch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_any_staff)
):
    from app.services.gst_report_service import generate_pdf_gst_report
    from app.services.permission_service import require_module
    require_module(user, "gst_report", "view")
    b_id = parse_int_param(branch_id)
    s_dt = parse_date_param(start_date)
    e_dt = parse_date_param(end_date)
    pdf_bytes = generate_pdf_gst_report(db, b_id, s_dt, e_dt)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=GST_Payable_Report.pdf"}
    )


# ==============================================================================
# ATTENDANCE EXPORTS
# ==============================================================================
@router.get("/export/attendance/pdf")
def export_attendance_pdf(
    branch_id: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_any_staff)
):
    b_id = parse_int_param(branch_id)
    y = parse_int_param(year)
    m = parse_int_param(month)
    s_dt = parse_date_param(start_date)
    if (not y or not m) and s_dt:
        y, m = s_dt.year, s_dt.month
    today = date.today()
    pdf_bytes = report_service.generate_pdf_attendance_report(
        db, b_id, y or today.year, m or today.month
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=Attendance_Report.pdf"}
    )


# ==============================================================================
# AUDIT LOG EXPORTS (EXCEL & PDF)
# ==============================================================================
@router.get("/export/audit")
@router.get("/export/audit/excel")
def export_audit_excel(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_admin)
):
    s_dt = parse_date_param(start_date)
    e_dt = parse_date_param(end_date)
    xlsx_bytes = report_service.generate_excel_audit_report(db, s_dt, e_dt)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Audit_Trail_Report.xlsx"}
    )

@router.get("/export/audit/pdf")
def export_audit_pdf(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_admin)
):
    s_dt = parse_date_param(start_date)
    e_dt = parse_date_param(end_date)
    pdf_bytes = report_service.generate_pdf_audit_report(db, s_dt, e_dt)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=Audit_Trail_Report.pdf"}
    )
