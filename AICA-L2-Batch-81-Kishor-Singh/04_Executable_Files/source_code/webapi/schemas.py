"""Pydantic request/response schemas for the API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from webapi.models import DocumentStatus, UserRole


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    full_name: str = ""
    password: str = Field(min_length=8)
    role: UserRole


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    client_name: str = ""


class DocumentVersionOut(BaseModel):
    id: str
    version_number: int
    filename: str
    sha256: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: str
    title: str
    client_name: str
    status: DocumentStatus
    uploaded_by_id: str
    prepared_by_id: str | None
    created_at: datetime
    updated_at: datetime
    versions: list[DocumentVersionOut] = []

    model_config = {"from_attributes": True}


class ApprovalActionRequest(BaseModel):
    action: str  # e.g. "submit_for_review", "approve", "reject", "request_changes"
    comment: str = ""


class ApprovalActionOut(BaseModel):
    id: str
    document_id: str
    actor_id: str
    action: str
    from_status: str
    to_status: str
    comment: str
    created_at: datetime

    model_config = {"from_attributes": True}
