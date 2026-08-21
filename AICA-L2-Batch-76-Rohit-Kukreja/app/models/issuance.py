"""Layer 3 issuance. Build Prompt v2 §5.4."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import DocumentStatus


class DocumentInstance(Base):
    """Immutable once written (§5.4, §18.6).

    `payload_json` freezes every input used, so reprinting a prior-year
    document reproduces it byte-identically from its own snapshot rather
    than from whatever the master data says today.
    """

    __tablename__ = "document_instance"
    __table_args__ = (
        UniqueConstraint(
            "engagement_id", "doc_type", "version_no", name="ux_document_instance_version"
        ),
    )

    doc_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    doc_type: Mapped[str] = mapped_column(String(60))
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    template_version: Mapped[str] = mapped_column(String(40))

    payload_json: Mapped[str] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(String(64))

    udin: Mapped[str | None] = mapped_column(String(18), default=None)
    generated_by: Mapped[str] = mapped_column(String(200), default="")
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    docx_path: Mapped[str] = mapped_column(String(500), default="")
    pdf_path: Mapped[str] = mapped_column(String(500), default="")

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False), default=DocumentStatus.DRAFT
    )
    revision_reason: Mapped[str] = mapped_column(Text, default="")


class UdinRegister(Base):
    __tablename__ = "udin_register"

    udin: Mapped[str] = mapped_column(String(18), primary_key=True)
    doc_id: Mapped[int] = mapped_column(ForeignKey("document_instance.doc_id"))
    partner_id: Mapped[int] = mapped_column(ForeignKey("partner.partner_id"))
    generated_on: Mapped[date] = mapped_column(Date)
    revoked_on: Mapped[date | None] = mapped_column(Date, default=None)
    revoke_reason: Mapped[str] = mapped_column(Text, default="")


class AuditLog(Base):
    """Written on every mutation. Not deletable through any UI path (§5.4).

    There is deliberately no ORM delete helper and no route that removes a
    row. The absence is the feature.
    """

    __tablename__ = "audit_log"

    log_id: Mapped[int] = mapped_column(primary_key=True)
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(60))
    action: Mapped[str] = mapped_column(String(40))
    field: Mapped[str] = mapped_column(String(120), default="")
    before_json: Mapped[str] = mapped_column(Text, default="")
    after_json: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    actor: Mapped[str] = mapped_column(String(200), default="")
    at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
