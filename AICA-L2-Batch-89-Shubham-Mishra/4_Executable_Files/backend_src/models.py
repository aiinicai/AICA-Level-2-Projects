"""
SQLAlchemy models for the multi-tenant auth + firm-data layer.

Tenant = one CA firm's account. User = one login within a tenant, with a
role (Admin / Preparer / Reviewer / Approver). The first user of a tenant
(the one who signed up) is always is_tenant_admin=True; everyone else is
added by that admin from inside the app once logged in.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    firm_name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    users: Mapped[list["User"]] = relationship(back_populates="tenant")
    clients: Mapped[list["Client"]] = relationship(back_populates="tenant")


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"))
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="Admin")  # Admin / Preparer / Reviewer / Approver
    is_tenant_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending / approved / rejected
    approval_token: Mapped[str] = mapped_column(String, unique=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="users")


class Client(Base):
    """Mirrors the L1 app's localStorage client shape, scoped per tenant."""
    __tablename__ = "clients"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    entity: Mapped[str] = mapped_column(String, default="Individual")
    pan: Mapped[str] = mapped_column(String, default="")
    gstin: Mapped[str] = mapped_column(String, default="")
    cin: Mapped[str] = mapped_column(String, default="")
    contact: Mapped[str] = mapped_column(String, default="")
    mobile: Mapped[str] = mapped_column(String, default="")
    email: Mapped[str] = mapped_column(String, default="")
    address: Mapped[str] = mapped_column(Text, default="")
    state: Mapped[str] = mapped_column(String, default="Delhi")
    sez: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="clients")
