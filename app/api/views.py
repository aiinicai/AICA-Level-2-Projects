from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.dependencies import get_current_user_from_cookie_or_header
from app.services import daybook_service, master_service
from app.models.daily_sales import DailySale
from app.models.cash_rec import CashReconciliation
from app.models.card_qr_rec import CardQrReconciliation
from app.models.settlement import SettlementBatch
from app.models.user import Role
from app.services.permission_service import effective_permissions, user_can

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["user_can"] = user_can
templates.env.globals["user_perms"] = effective_permissions

router = APIRouter(tags=["Web UI Views"])


def _require_page(user, module: str):
    if not user:
        return RedirectResponse(url="/login")
    if module != "dashboard" and not user_can(user, module, "view"):
        return RedirectResponse(url="/dashboard")
    return None

@router.get("/login")
def login_page(request: Request, user=Depends(get_current_user_from_cookie_or_header)):
    if user:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse(request=request, name="login.html")

@router.get("/")
@router.get("/dashboard")
def dashboard_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookie_or_header)):
    if not user:
        return RedirectResponse(url="/login")

    branches = master_service.get_branches(db, active_only=True)
    daybook_data = daybook_service.get_consolidated_daybook(db)
    totals = daybook_service.get_daybook_totals(daybook_data)

    # Reconciliations summary stats
    cash_diffs = db.query(CashReconciliation).filter(CashReconciliation.status == "DIFFERENCE").count()
    card_diffs = db.query(CardQrReconciliation).filter(CardQrReconciliation.status == "DIFFERENCE").count()
    online_diffs = db.query(SettlementBatch).filter(SettlementBatch.status == "DIFFERENCE").count()
    pending_card = db.query(CardQrReconciliation).filter(CardQrReconciliation.status == "PENDING").count()

    latest_cash_date = db.query(func.max(CashReconciliation.rec_date)).scalar()
    closing_balance = 0.0
    if latest_cash_date:
        closing_balance = db.query(func.coalesce(func.sum(CashReconciliation.actual_closing_balance), 0.0)).filter(
            CashReconciliation.rec_date == latest_cash_date
        ).scalar() or 0.0

    context = {
        "user": user,
        "branches": branches,
        "totals": totals,
        "cash_diffs": cash_diffs,
        "card_diffs": card_diffs,
        "online_diffs": online_diffs,
        "pending_card": pending_card,
        "closing_balance": closing_balance,
        "closing_date": latest_cash_date,
        "daybook_data": daybook_data[:10] # Top 10 recent rows
    }
    return templates.TemplateResponse(request=request, name="dashboard.html", context=context)

@router.get("/daybook")
def daybook_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookie_or_header)):
    blocked = _require_page(user, "daybook")
    if blocked:
        return blocked
    branches = master_service.get_branches(db, active_only=True)
    return templates.TemplateResponse(request=request, name="daybook.html", context={"user": user, "branches": branches})

@router.get("/cash-reconciliation")
def cash_rec_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookie_or_header)):
    blocked = _require_page(user, "cash_rec")
    if blocked:
        return blocked
    branches = master_service.get_branches(db, active_only=True)
    return templates.TemplateResponse(request=request, name="cash_rec.html", context={"user": user, "branches": branches})

@router.get("/card-qr-reconciliation")
def card_qr_rec_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookie_or_header)):
    blocked = _require_page(user, "card_qr")
    if blocked:
        return blocked
    branches = master_service.get_branches(db, active_only=True)
    return templates.TemplateResponse(request=request, name="card_qr_rec.html", context={"user": user, "branches": branches})

@router.get("/aggregator-reconciliation")
def aggregator_rec_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookie_or_header)):
    blocked = _require_page(user, "aggregators")
    if blocked:
        return blocked
    branches = master_service.get_branches(db, active_only=True)
    aggregators = master_service.get_aggregators(db, active_only=True)
    return templates.TemplateResponse(request=request, name="aggregator_rec.html", context={"user": user, "branches": branches, "aggregators": aggregators})

@router.get("/imports")
def imports_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookie_or_header)):
    if not user:
        return RedirectResponse(url="/login")
    return RedirectResponse(url="/daybook", status_code=302)

@router.get("/masters")
def masters_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookie_or_header)):
    if not user:
        return RedirectResponse(url="/login")
    branches = master_service.get_branches(db, active_only=True)
    return templates.TemplateResponse(request=request, name="masters.html", context={"user": user, "branches": branches})

@router.get("/reports")
def reports_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookie_or_header)):
    blocked = _require_page(user, "reports")
    if blocked:
        return blocked
    branches = master_service.get_branches(db, active_only=True)
    aggregators = master_service.get_aggregators(db, active_only=True)
    return templates.TemplateResponse(request=request, name="reports.html", context={"user": user, "branches": branches, "aggregators": aggregators})

@router.get("/gst-payable-report")
def gst_payable_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookie_or_header)):
    blocked = _require_page(user, "gst_report")
    if blocked:
        return blocked
    branches = master_service.get_branches(db, active_only=True)
    return templates.TemplateResponse(request=request, name="gst_report.html", context={"user": user, "branches": branches})

@router.get("/attendance-reconciliation")
def attendance_rec_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookie_or_header)):
    blocked = _require_page(user, "attendance")
    if blocked:
        return blocked
    branches = master_service.get_branches(db, active_only=True)
    return templates.TemplateResponse(request=request, name="attendance_rec.html", context={"user": user, "branches": branches})

@router.get("/audit")
def audit_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookie_or_header)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="audit.html", context={"user": user})

@router.get("/clients")
def clients_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookie_or_header)):
    if not user:
        return RedirectResponse(url="/login")
    if not user.role or user.role.name != "Administrator":
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse(request=request, name="clients.html", context={"user": user})

@router.get("/settings")
def settings_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookie_or_header)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="settings.html", context={"user": user})

@router.get("/users")
def users_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookie_or_header)):
    if not user:
        return RedirectResponse(url="/login")
    if not user.role or user.role.name != "Administrator":
        return RedirectResponse(url="/dashboard")
    branches = master_service.get_branches(db, active_only=True)
    roles = db.query(Role).order_by(Role.id.asc()).all()
    return templates.TemplateResponse(request=request, name="users.html", context={"user": user, "branches": branches, "roles": roles})
