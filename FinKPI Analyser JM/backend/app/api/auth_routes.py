from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import UserModel
from ..schemas import LoginRequest, TokenResponse, APIResponse
from ..auth import verify_password, hash_password, create_token, get_current_user
from ..config import config

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

@router.post("/login", response_model=APIResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.username == req.username).first()
    if not user:
        if req.username == config.DEMO_USER and req.password == config.DEMO_PASSWORD:
            user = UserModel(
                username=config.DEMO_USER,
                email="admin@finkpi.com",
                password_hash=hash_password(config.DEMO_PASSWORD),
                role="admin",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            raise HTTPException(status_code=401, detail="Invalid username or password")
    else:
        if not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token({"sub": user.username, "role": user.role})
    return APIResponse(
        success=True,
        statusCode=200,
        message="Authentication successful",
        data={
            "access_token": token,
            "token_type": "bearer",
            "role": user.role,
            "username": user.username
        }
    )

@router.post("/refresh", response_model=APIResponse)
def refresh(current_user: UserModel = Depends(get_current_user)):
    token = create_token({"sub": current_user.username, "role": current_user.role})
    return APIResponse(
        success=True,
        statusCode=200,
        message="Token refreshed successfully",
        data={"access_token": token, "token_type": "bearer", "role": current_user.role}
    )

@router.post("/logout", response_model=APIResponse)
def logout(current_user: UserModel = Depends(get_current_user)):
    return APIResponse(success=True, statusCode=200, message="Logged out successfully")
