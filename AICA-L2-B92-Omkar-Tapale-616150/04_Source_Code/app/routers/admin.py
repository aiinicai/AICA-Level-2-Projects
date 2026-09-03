import os
import shutil
import datetime as dt
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db, DB_PATH, APP_ROOT
from .. import models, permissions
from ..auth import get_current_user, hash_password, log_audit, require_role
from ..main import templates

router = APIRouter()


@router.get("/admin")
def admin_page(request: Request, db: Session = Depends(get_db),
                user: models.User = Depends(require_role(models.ROLE_CEO, models.ROLE_DEPT_ADMIN))):
    users = permissions.visible_users_scope(db, user).order_by(models.User.employee_code).all()
    if permissions.is_ceo(user):
        departments = db.query(models.Department).all()
    else:
        departments = db.query(models.Department).filter(models.Department.id == user.department_id).all()
    return templates.TemplateResponse(request, "admin.html", {
        "request": request, "user": user, "users": users, "departments": departments,
        "roles": models.ROLES, "is_ceo": permissions.is_ceo(user),
    })


def _next_employee_code(db: Session) -> str:
    last = db.query(models.User).order_by(models.User.id.desc()).first()
    n = (last.id + 1) if last else 1
    return f"EMP-{n:04d}"


@router.post("/admin/users/create")
def create_user(name: str = Form(...), email: str = Form(None), role: str = Form(...),
                 department_id: int = Form(...), designation: str = Form(""),
                 manager_id: str = Form(None), date_of_joining: str = Form(...),
                 db: Session = Depends(get_db),
                 user: models.User = Depends(require_role(models.ROLE_CEO, models.ROLE_DEPT_ADMIN))):
    manager_id = int(manager_id) if manager_id and manager_id.strip() else None
    if permissions.is_dept_admin(user):
        if role == models.ROLE_CEO or role == models.ROLE_DEPT_ADMIN:
            role = models.ROLE_MANAGER  # dept admins cannot create other admins/CEO
        department_id = user.department_id  # scoped to own department

    new_user = models.User(
        employee_code=_next_employee_code(db), name=name, email=email or None,
        password_hash=hash_password("Welcome@123"), must_change_password=True,
        role=role, department_id=department_id, designation=designation,
        manager_id=manager_id or None, date_of_joining=dt.date.fromisoformat(date_of_joining),
    )
    db.add(new_user)
    db.commit()
    log_audit(db, user, "USER_CREATED", f"{new_user.employee_code} ({new_user.name}) created by {user.employee_code}")
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/users/{target_id}/deactivate")
def deactivate_user(target_id: int, db: Session = Depends(get_db),
                     user: models.User = Depends(require_role(models.ROLE_CEO, models.ROLE_DEPT_ADMIN))):
    target = db.query(models.User).get(target_id)
    if target and permissions.can_manage_user(user, target):
        target.is_active = not target.is_active
        db.commit()
        log_audit(db, user, "USER_TOGGLE_ACTIVE", f"{target.employee_code} active={target.is_active}")
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/users/{target_id}/reset-password")
def reset_password(target_id: int, db: Session = Depends(get_db),
                    user: models.User = Depends(require_role(models.ROLE_CEO, models.ROLE_DEPT_ADMIN))):
    target = db.query(models.User).get(target_id)
    if target and permissions.can_manage_user(user, target):
        target.password_hash = hash_password("Welcome@123")
        target.must_change_password = True
        db.commit()
        log_audit(db, user, "PASSWORD_RESET", f"Password reset for {target.employee_code} by {user.employee_code}")
    return RedirectResponse("/admin", status_code=303)


@router.get("/admin/audit-log")
def audit_log_page(request: Request, db: Session = Depends(get_db),
                    user: models.User = Depends(require_role(models.ROLE_CEO))):
    logs = db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc()).limit(500).all()
    return templates.TemplateResponse(request, "audit_log.html", {"request": request, "user": user, "logs": logs})


@router.post("/admin/backup")
def run_backup(db: Session = Depends(get_db), user: models.User = Depends(require_role(models.ROLE_CEO))):
    backups_dir = os.path.join(APP_ROOT, "backups")
    os.makedirs(backups_dir, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(backups_dir, f"company_os_backup_{stamp}.db")
    shutil.copy2(DB_PATH, dest)
    db.add(models.BackupLog(actor_id=user.id, file_path=dest))
    db.commit()
    log_audit(db, user, "FULL_BACKUP", f"Backup written to {dest}")
    return RedirectResponse("/admin/audit-log", status_code=303)
