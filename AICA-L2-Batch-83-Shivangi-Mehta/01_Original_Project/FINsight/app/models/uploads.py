"""
UploadedFile, DataMapping — Blueprint Section 2, D.4/D.5. Schema only;
the actual upload/mapping workflow (safe file handling, synonym
suggestion) is Stage 6/7.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    __table_args__ = (
        Index("ix_uploaded_files_engagement", "engagement_id"),
        # Duplicate-upload detection is a named purpose of checksum
        # (Blueprint D.4) — enforcing it structurally, scoped per
        # engagement (the same file legitimately re-uploaded to a
        # DIFFERENT engagement is not a duplicate). NULL checksums never
        # collide with each other under SQLite's UNIQUE semantics, so
        # this is safe before a checksum is computed.
        UniqueConstraint("engagement_id", "checksum", name="uq_uploaded_files_engagement_checksum"),
    )

    file_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.engagement_id"))
    # Enum: TB / GL / JE / SALES / PURCHASE / BANK / AR / AP / FIXED_ASSETS / GST / TDS / PRIOR_YEAR / OTHER
    file_type: Mapped[str] = mapped_column()
    original_filename: Mapped[str] = mapped_column()
    stored_path: Mapped[str] = mapped_column()
    row_count: Mapped[int | None] = mapped_column(default=None)
    # Enum: UPLOADED / MAPPED / VALIDATED / ERROR
    upload_status: Mapped[str] = mapped_column(default="UPLOADED")
    uploaded_at: Mapped[str] = mapped_column()
    checksum: Mapped[str | None] = mapped_column(default=None)  # SHA-256, duplicate-upload detection

    mappings: Mapped[list["DataMapping"]] = relationship(back_populates="file", cascade="all, delete-orphan")


class DataMapping(Base):
    __tablename__ = "data_mappings"
    __table_args__ = (
        # A source column should map to exactly one target field per file
        # — a second mapping for the same source column would be
        # ambiguous for the rule engines reading it.
        UniqueConstraint("file_id", "source_column", name="uq_data_mappings_file_source_column"),
    )

    mapping_id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("uploaded_files.file_id"))
    source_column: Mapped[str] = mapped_column()
    target_field: Mapped[str] = mapped_column()  # canonical FinSight field, e.g. transaction_date
    confidence_score: Mapped[float | None] = mapped_column(default=None)  # 0-1
    # Never auto-applied downstream unless True (Blueprint Section 8).
    is_user_confirmed: Mapped[bool] = mapped_column(default=False)
    confirmed_at: Mapped[str | None] = mapped_column(default=None)

    file: Mapped["UploadedFile"] = relationship(back_populates="mappings")
