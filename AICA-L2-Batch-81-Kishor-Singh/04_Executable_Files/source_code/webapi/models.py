"""SQLAlchemy ORM models: users, documents, versions, approval actions, audit events.

Only metadata is stored here -- document *bytes* live on disk (or object
storage in a real deployment) under a path referenced by
``DocumentVersion.storage_path``; the database never holds file content,
matching the same principle the desktop app's SQLite database follows.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from webapi.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


class UserRole(str, enum.Enum):
    ADMIN = "Administrator"
    MAKER = "Maker"
    CHECKER = "Checker"
    APPROVER = "Approver"
    SIGNATORY = "Signatory"
    AUDITOR = "Auditor"
    CLIENT = "Client"


class DocumentStatus(str, enum.Enum):
    DRAFT = "Draft"
    PREPARED = "Prepared"
    IN_REVIEW = "In Review"
    CHANGES_REQUESTED = "Changes Requested"
    REJECTED = "Rejected"
    APPROVED = "Approved"
    SIGNING = "Signing"
    SIGNED = "Signed"
    VERIFIED = "Verified"
    RELEASED = "Released"
    ARCHIVED = "Archived"
    CANCELLED = "Cancelled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    documents_uploaded: Mapped[list["Document"]] = relationship(back_populates="uploaded_by", foreign_keys="Document.uploaded_by_id")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(500))
    client_name: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.DRAFT)
    uploaded_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    prepared_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    current_version_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    uploaded_by: Mapped["User"] = relationship(foreign_keys=[uploaded_by_id])
    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document", order_by="DocumentVersion.version_number")
    actions: Mapped[list["ApprovalAction"]] = relationship(back_populates="document", order_by="ApprovalAction.created_at")


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    filename: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(Text)  # local path or object-storage key -- never the bytes themselves
    uploaded_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped["Document"] = relationship(back_populates="versions", foreign_keys=[document_id])


class ApprovalAction(Base):
    __tablename__ = "approval_actions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50))  # e.g. "submit", "approve", "reject", "request_changes"
    from_status: Mapped[str] = mapped_column(String(50))
    to_status: Mapped[str] = mapped_column(String(50))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped["Document"] = relationship(back_populates="actions")
    actor: Mapped["User"] = relationship()


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    document_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    details: Mapped[str] = mapped_column(Text, default="")  # short JSON string; never document content
