from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class RoleSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class UserSchema(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    role_id: int
    branch_id: Optional[int] = None
    role: Optional[RoleSchema] = None

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSchema
