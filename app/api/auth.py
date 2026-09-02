from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.schemas.user import TokenResponse, UserSchema, LoginRequest
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login")
def login_for_access_token(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    login_id = str(login_data.email or "").strip().lower()
    aliases = {
        "admin@restaurant.com": "admin",
        "branch@restaurant.com": "noida",
        "noida@restaurant.com": "noida",
    }
    lookup_ids = [login_id]
    if login_id in aliases:
        lookup_ids.append(aliases[login_id])
    user = db.query(User).filter(User.email.in_(lookup_ids)).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")

    access_token = create_access_token(data={"sub": user.email, "role": user.role.name})
    
    # Set HTTP-only Cookie
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=86400,
        samesite="lax"
    )

    log_action(db, "LOGIN", "User", user.id, None, {"email": user.email}, user=user, ip_address=request.client.host)

    from app.services.permission_service import effective_permissions
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.name,
            "branch_id": user.branch_id,
            "permissions": effective_permissions(user),
        }
    }

@router.post("/logout")
def logout(response: Response, db: Session = Depends(get_db)):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}
