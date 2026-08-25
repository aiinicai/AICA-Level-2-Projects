from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def get_current_user_from_cookie_or_header(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[User]:
    # Check cookie first, then auth header
    jwt_token = request.cookies.get("access_token") or token
    if not jwt_token:
        return None
    
    if jwt_token.startswith("Bearer "):
        jwt_token = jwt_token[7:]

    payload = decode_access_token(jwt_token)
    if not payload:
        return None

    email: str = payload.get("sub")
    if not email:
        return None

    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    return user

def require_current_user(
    user: Optional[User] = Depends(get_current_user_from_cookie_or_header)
) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(require_current_user)) -> User:
        if user.role.name not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{user.role.name}' does not have sufficient permission for this action."
            )
        return user

# Helper dependency instances
require_admin = RoleChecker(["Administrator"])
require_accounts_or_admin = RoleChecker(["Administrator", "Accounts Manager"])
require_any_staff = RoleChecker(["Administrator", "Accounts Manager", "Branch User", "Viewer"])
