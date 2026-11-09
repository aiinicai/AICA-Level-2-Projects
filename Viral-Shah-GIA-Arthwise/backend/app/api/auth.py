from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import verify_password, hash_password, create_access_token
from backend.app.core.dependencies import get_current_user, require_role
from backend.app.models.models import User, AuditLog
from backend.app.schemas.schemas import UserLogin, UserCreate, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    identifier = credentials.email.strip().lower()
    # Match direct email or username prefix (e.g. 'analyst' or 'analyst@...')
    user = db.query(User).filter(
        (User.email.ilike(identifier)) |
        (User.email.ilike(f"{identifier}@%"))
    ).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is deactivated")
        
    access_token = create_access_token(data={"sub": user.id, "role": user.role, "client_id": user.client_id})
    
    # Audit log
    audit = AuditLog(
        user_id=user.id,
        client_id=user.client_id,
        action="LOGIN",
        resource_type="auth",
        resource_id=user.id,
        details_json="Successful login"
    )
    db.add(audit)
    db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/register", response_model=UserResponse)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        client_id=user_data.client_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user
