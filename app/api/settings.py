from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_admin, require_any_staff
from app.services import master_service
from app.models.setting import ApplicationSetting

router = APIRouter(prefix="/api/settings", tags=["Application Settings"])

@router.get("")
def get_all_settings(
    db: Session = Depends(get_db),
    user=Depends(require_any_staff)
):
    settings = db.query(ApplicationSetting).all()
    return settings

@router.post("")
def update_setting(
    key: str = Body(...),
    value: str = Body(...),
    description: str = Body(None),
    db: Session = Depends(get_db),
    user=Depends(require_admin)
):
    return master_service.set_setting(db, key, value, description, current_user=user)
