from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/api/audit", tags=["Audit Trail"])

@router.get("")
def get_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    user=Depends(require_admin)
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return logs
