from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..database import get_db
from ..models import Asset, Company, AuditLog, DuplicateOverride, User
from ..schemas import DashboardStats, CompanyStat
from ..auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_companies = db.query(func.count(Company.id)).filter(Company.is_active == True).scalar() or 0
    total_tags_generated = db.query(func.count(Asset.id)).scalar() or 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tags_generated_today = db.query(func.count(Asset.id)).filter(Asset.created_at >= today_start).scalar() or 0

    fixed_assets_count = db.query(func.count(Asset.id)).filter(Asset.asset_type == "FIXED_ASSET").scalar() or 0
    stock_assets_count = db.query(func.count(Asset.id)).filter(Asset.asset_type == "STOCK").scalar() or 0

    duplicate_attempts_count = db.query(func.count(AuditLog.id)).filter(AuditLog.action == "DUPLICATE_ATTEMPT").scalar() or 0
    duplicate_overrides_count = db.query(func.count(DuplicateOverride.id)).scalar() or 0

    # Recent activity
    recent_logs = db.query(AuditLog).order_by(desc(AuditLog.created_at)).limit(8).all()
    recent_activity = [
        {
            "id": log.id,
            "action": log.action,
            "details": log.details,
            "result": log.result,
            "time": log.created_at.strftime("%H:%M:%S, %d %b"),
            "user": log.user.full_name if log.user else "System"
        }
        for log in recent_logs
    ]

    return {
        "total_companies": total_companies,
        "total_tags_generated": total_tags_generated,
        "tags_generated_today": tags_generated_today,
        "fixed_assets_count": fixed_assets_count,
        "stock_assets_count": stock_assets_count,
        "duplicate_attempts_count": duplicate_attempts_count,
        "duplicate_overrides_count": duplicate_overrides_count,
        "recent_activity": recent_activity
    }

@router.get("/company-stats", response_model=List[CompanyStat])
def get_company_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    companies = db.query(Company).filter(Company.is_active == True).order_by(Company.name.asc()).all()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    stats = []
    for c in companies:
        total_tags = db.query(func.count(Asset.id)).filter(Asset.company_id == c.id).scalar() or 0
        fixed_count = db.query(func.count(Asset.id)).filter(Asset.company_id == c.id, Asset.asset_type == "FIXED_ASSET").scalar() or 0
        stock_count = db.query(func.count(Asset.id)).filter(Asset.company_id == c.id, Asset.asset_type == "STOCK").scalar() or 0
        tags_today = db.query(func.count(Asset.id)).filter(Asset.company_id == c.id, Asset.created_at >= today_start).scalar() or 0

        last_asset = db.query(Asset.asset_id).filter(Asset.company_id == c.id).order_by(desc(Asset.created_at)).first()
        last_id = last_asset[0] if last_asset else "None"

        stats.append({
            "company_id": c.id,
            "company_name": c.name,
            "short_name": c.short_name,
            "total_tags": total_tags,
            "fixed_assets": fixed_count,
            "stock_assets": stock_count,
            "tags_today": tags_today,
            "last_asset_id": last_id
        })

    return stats
