import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db, engine
from ..models import User, SystemSettings, AuditLog
from ..schemas import UserOut, UserCreate, UserUpdate, SystemSettingsOut
from ..auth import get_current_user, require_admin, get_password_hash
from ..config import DATA_DIR, BACKUPS_DIR

router = APIRouter(prefix="/api/admin", tags=["Administration"])

# --- USER MANAGEMENT ---
@router.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):
    return db.query(User).order_by(User.full_name.asc()).all()

@router.post("/users", response_model=UserOut)
def create_user(
    user_in: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
        is_active=user_in.is_active
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    audit = AuditLog(
        user_id=admin_user.id,
        action="CREATE_USER",
        entity_type="USER",
        entity_id=str(new_user.id),
        details=f"Created user {new_user.email} (Role: {new_user.role})",
        result="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    db.commit()

    return new_user

@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if user_in.full_name is not None:
        target.full_name = user_in.full_name
    if user_in.role is not None:
        target.role = user_in.role
    if user_in.is_active is not None:
        target.is_active = user_in.is_active
    if user_in.password:
        target.password_hash = get_password_hash(user_in.password)

    db.commit()
    db.refresh(target)

    audit = AuditLog(
        user_id=admin_user.id,
        action="UPDATE_USER",
        entity_type="USER",
        entity_id=str(target.id),
        details=f"Updated user {target.email}",
        result="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    db.commit()

    return target

# --- SYSTEM SETTINGS ---
@router.get("/settings", response_model=SystemSettingsOut)
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    settings = db.query(SystemSettings).first()
    if not settings:
        settings = SystemSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@router.put("/settings", response_model=SystemSettingsOut)
def update_settings(
    payload: dict,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    settings = db.query(SystemSettings).first()
    if not settings:
        settings = SystemSettings()
        db.add(settings)

    for k, v in payload.items():
        if hasattr(settings, k):
            setattr(settings, k, v)

    db.commit()
    db.refresh(settings)
    return settings

# --- BACKUP & RESTORE ---
@router.get("/backup")
def backup_database(admin_user: User = Depends(require_admin)):
    """
    Creates a snapshot of the SQLite database and serves it as a downloadable file.
    """
    db_file = DATA_DIR / "asset_tagging.db"
    if not db_file.exists():
        raise HTTPException(status_code=404, detail="Database file not found")

    backup_name = f"backup_asset_tagging_{os.path.getmtime(db_file):.0f}.db"
    backup_path = BACKUPS_DIR / backup_name
    shutil.copy2(db_file, backup_path)

    return FileResponse(
        path=backup_path,
        media_type="application/octet-stream",
        filename="Asset_Tagging_Database_Backup.db"
    )

@router.post("/restore")
async def restore_database(
    file: UploadFile = File(...),
    admin_user: User = Depends(require_admin)
):
    """
    Restores the database from an uploaded .db backup file.
    """
    if not file.filename.endswith(".db"):
        raise HTTPException(status_code=400, detail="Invalid backup file. Must be a .db file.")

    db_file = DATA_DIR / "asset_tagging.db"
    temp_restore_path = BACKUPS_DIR / "temp_restore.db"

    with open(temp_restore_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Replace current db
    try:
        engine.dispose()
        shutil.copy2(temp_restore_path, db_file)
        if temp_restore_path.exists():
            os.remove(temp_restore_path)
        return {"success": True, "message": "Database restored successfully. Please refresh the page."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restore database: {str(e)}")
