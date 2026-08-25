from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.import_batch import ImportBatch
from app.models.user import Role, User
from app.services.permission_service import (
    default_permissions,
    effective_permissions,
    module_catalog,
    normalize_permissions,
)

router = APIRouter(prefix="/api/users", tags=["User Administration"])


def _other_active_admin_count(db: Session, exclude_user_id: int) -> int:
    return (
        db.query(User)
        .filter(User.id != exclude_user_id, User.is_active == True)
        .join(Role)
        .filter(Role.name == "Administrator")
        .count()
    )


def _user_payload(user: User) -> Dict[str, Any]:
    role_name = user.role.name if user.role else ""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": bool(user.is_active),
        "role_id": user.role_id,
        "role_name": role_name,
        "branch_id": user.branch_id,
        "branch_name": user.branch.name if user.branch else None,
        "permissions": effective_permissions(user),
    }


@router.get("/catalog")
def permission_catalog(user: User = Depends(require_admin)):
    return {
        "modules": module_catalog(),
        "actions": [
            {"key": "view", "label": "View"},
            {"key": "enter", "label": "Add / import"},
            {"key": "edit_saved", "label": "Edit after save"},
        ],
        "role_defaults": {
            "Administrator": default_permissions("Administrator"),
            "Accounts Manager": default_permissions("Accounts Manager"),
            "Branch User": default_permissions("Branch User"),
            "Viewer": default_permissions("Viewer"),
        },
    }


@router.get("")
def list_users(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    rows = db.query(User).order_by(User.full_name.asc()).all()
    return [_user_payload(u) for u in rows]


@router.post("")
def create_user(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    email = str(payload.get("email") or "").strip().lower()
    name = str(payload.get("full_name") or "").strip()
    password = str(payload.get("password") or "")
    role_id = int(payload.get("role_id") or 0)
    if not email or not name or not password or not role_id:
        raise HTTPException(status_code=400, detail="Name, email, password and role are required.")
    if len(password) < 5:
        raise HTTPException(status_code=400, detail="Password must be at least 5 characters.")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="That email is already in use.")
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail="Role not found.")
    new_user = User(
        email=email,
        full_name=name,
        hashed_password=get_password_hash(password),
        role_id=role.id,
        branch_id=payload.get("branch_id") or None,
        is_active=bool(payload.get("is_active", True)),
        permissions=normalize_permissions(payload.get("permissions"), role.name),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return _user_payload(new_user)


@router.put("/{user_id}")
def update_user(
    user_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    email = str(payload.get("email") or target.email).strip().lower()
    clash = db.query(User).filter(User.email == email, User.id != user_id).first()
    if clash:
        raise HTTPException(status_code=400, detail="That email is already in use.")
    role_id = int(payload.get("role_id") or target.role_id)
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail="Role not found.")
    if target.role and target.role.name == "Administrator" and role.name != "Administrator":
        if _other_active_admin_count(db, target.id) == 0:
            raise HTTPException(status_code=400, detail="Keep at least one active Administrator.")
    if target.id == admin.id and payload.get("is_active") is False:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own login.")
    target.email = email
    target.full_name = str(payload.get("full_name") or target.full_name).strip()
    target.role_id = role.id
    target.branch_id = payload.get("branch_id") or None
    if "is_active" in payload:
        target.is_active = bool(payload.get("is_active"))
    if payload.get("password"):
        if len(str(payload["password"])) < 5:
            raise HTTPException(status_code=400, detail="Password must be at least 5 characters.")
        target.hashed_password = get_password_hash(str(payload["password"]))
    if "permissions" in payload:
        target.permissions = normalize_permissions(payload.get("permissions"), role.name)
    db.commit()
    db.refresh(target)
    return _user_payload(target)


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own login.")
    if target.role and target.role.name == "Administrator":
        if _other_active_admin_count(db, target.id) == 0:
            raise HTTPException(status_code=400, detail="Keep at least one active Administrator.")
    db.query(AuditLog).filter(AuditLog.user_id == target.id).update(
        {AuditLog.user_id: None}, synchronize_session=False
    )
    db.query(ImportBatch).filter(ImportBatch.uploaded_by_id == target.id).update(
        {ImportBatch.uploaded_by_id: None}, synchronize_session=False
    )
    db.expire(target)
    db.delete(target)
    db.commit()
    return {"ok": True, "deleted_id": user_id}
