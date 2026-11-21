from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import hash_password
from backend.app.core.dependencies import get_current_user, require_role
from backend.app.models.models import AuditLog, User
from backend.app.schemas.schemas import UserCreate, UserResponse, PasswordResetRequest

router = APIRouter(prefix="/admin", tags=["Administration, Audit & Integrations"])

@router.get("/audit-logs")
def get_audit_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    results = []
    for log in logs:
        results.append({
            "id": log.id,
            "user_email": log.user.email if log.user else "System",
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details_json,
            "created_at": log.created_at
        })
    return results

@router.get("/integrations")
def get_integrations_status(
    current_user: User = Depends(require_role(["admin", "analyst", "reviewer"]))
):
    """
    Returns integration status per regulatory and architectural guidelines.
    Third-party APIs are kept explicitly disabled until verified credentials,
    bilateral agreements, and borrower DPDP consent are configured.
    """
    return {
        "pan_gstin_verification": {
            "status": "SANDBOX_MOCK",
            "provider": "Authorized GSP / Protean e-Gov",
            "enabled": settings.ENABLE_GST_API,
            "notes": "Format regex validation active locally. Live API disabled until GSP credentials configured."
        },
        "credit_bureau": {
            "status": "SANDBOX_MOCK",
            "provider": "TransUnion CIBIL / Experian Direct",
            "enabled": settings.ENABLE_BUREAU_API,
            "notes": "Manual bureau report upload active. Live bureau inquiry requires signed client consent."
        },
        "account_aggregator": {
            "status": "SANDBOX_MOCK",
            "provider": "RBI Regulated NBFC-AA (Setu / Finvu)",
            "enabled": settings.ENABLE_BANK_AA_API,
            "notes": "Bank statement PDF/Excel extraction active locally. Direct consent pulls require AA onboarding."
        },
        "cloud_ai_ocr": {
            "status": "DISABLED",
            "provider": settings.CLOUD_AI_PROVIDER,
            "enabled": settings.ENABLE_CLOUD_AI_OCR,
            "notes": "Disabled by default per Indian DPDP privacy policy. Local pdfplumber & openpyxl active."
        }
    }

# ==============================================================================
# User Management & Governance (Strictly Administrator Only)
# ==============================================================================

@router.get("/users", response_model=List[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    List all platform users with roles and status. Restricted strictly to Administrator.
    """
    return db.query(User).order_by(User.created_at.asc()).all()


@router.post("/users", response_model=UserResponse)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Create a new platform user. Restricted strictly to Administrator.
    """
    clean_email = user_data.email.strip().lower()
    existing = db.query(User).filter(User.email.ilike(clean_email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{clean_email}' is already registered."
        )

    if len(user_data.password.strip()) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least 6 characters."
        )

    valid_roles = ["analyst", "reviewer", "admin", "client"]
    if user_data.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{user_data.role}'. Allowed roles: {valid_roles}"
        )

    new_user = User(
        email=clean_email,
        hashed_password=hash_password(user_data.password.strip()),
        full_name=user_data.full_name.strip(),
        role=user_data.role,
        client_id=user_data.client_id,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    audit = AuditLog(
        user_id=current_user.id,
        action="CREATE_USER",
        resource_type="user",
        resource_id=new_user.id,
        details_json=f"Created user '{new_user.email}' (role: {new_user.role}) by Admin '{current_user.email}'"
    )
    db.add(audit)
    db.commit()

    return new_user


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: str,
    req: PasswordResetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Reset a user's password. Restricted strictly to Administrator.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    new_pwd = req.new_password.strip()
    if len(new_pwd) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must contain at least 6 characters."
        )

    target_user.hashed_password = hash_password(new_pwd)

    audit = AuditLog(
        user_id=current_user.id,
        action="RESET_PASSWORD",
        resource_type="user",
        resource_id=target_user.id,
        details_json=f"Password reset for user '{target_user.email}' by Admin '{current_user.email}'"
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "message": f"Password for {target_user.email} successfully updated.",
        "user_id": target_user.id,
        "email": target_user.email
    }


@router.patch("/users/{user_id}/toggle-active", response_model=UserResponse)
def toggle_user_active(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Activate or deactivate a user account. Restricted strictly to Administrator.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own account."
        )

    target_user.is_active = not target_user.is_active

    audit = AuditLog(
        user_id=current_user.id,
        action="TOGGLE_USER_STATUS",
        resource_type="user",
        resource_id=target_user.id,
        details_json=f"User '{target_user.email}' active status set to {target_user.is_active} by Admin '{current_user.email}'"
    )
    db.add(audit)
    db.commit()
    db.refresh(target_user)

    return target_user
