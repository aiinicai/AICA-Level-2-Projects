"""
Engagement, EntityProfile, Applicability.

Mirrors approved Blueprint Section 2: D.1 (engagements), D.2
(entity_profiles, money fields in paise per Correction #7), and Section
2.11 (applicability — system-suggested vs user-confirmed split per
Correction #9). Schema only — no engagement-creation workflow logic
(that is Stage 5).
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Engagement(Base):
    __tablename__ = "engagements"

    engagement_id: Mapped[int] = mapped_column(primary_key=True)
    entity_name: Mapped[str] = mapped_column()
    financial_year: Mapped[str] = mapped_column()
    # Enum (enforced at service layer, not DB level): DRAFT / IN_PROGRESS / COMPLETED / ARCHIVED
    status: Mapped[str] = mapped_column(default="DRAFT")
    created_at: Mapped[str] = mapped_column()
    updated_at: Mapped[str] = mapped_column()
    created_by: Mapped[str | None] = mapped_column(default=None)

    entity_profile: Mapped["EntityProfile"] = relationship(
        back_populates="engagement", uselist=False, cascade="all, delete-orphan"
    )
    applicability_rows: Mapped[list["Applicability"]] = relationship(
        back_populates="engagement", cascade="all, delete-orphan"
    )


class EntityProfile(Base):
    __tablename__ = "entity_profiles"
    __table_args__ = (
        # Structural 1:1 (Blueprint Section D.2: "One profile per
        # engagement") — enforced at the DB, not left to service-layer
        # discipline, since a duplicate profile would silently corrupt
        # the applicability engine's single source of truth.
        UniqueConstraint("engagement_id", name="uq_entity_profiles_engagement_id"),
    )

    profile_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.engagement_id"))
    entity_type: Mapped[str] = mapped_column()  # Company / LLP / Partnership / Proprietorship / Other
    industry: Mapped[str | None] = mapped_column(default=None)
    is_listed: Mapped[bool] = mapped_column(default=False)
    # Hard enum, never framework-agnostic (Blueprint Ambiguity #4): AS / IND_AS
    accounting_framework: Mapped[str] = mapped_column()
    # Stage 18 (explicitly approved before implementation — see the
    # Stage 18 schema-proposal exchange): one new nullable column. The
    # user's own plain-language answer to "Is this company required to
    # follow Ind AS?" (Yes/No; NULL = not yet answered). This is the
    # ONLY new input driving auto-detection — `accounting_framework`
    # itself is unchanged (still the one enum every rule/service already
    # reads) and is auto-set from this answer (True -> IND_AS, False ->
    # AS) UNLESS the professional explicitly sets `accounting_framework`
    # directly on the form, which always wins — see
    # app/engagement/validation.py::validate_entity_profile_form().
    ind_as_mandated: Mapped[bool | None] = mapped_column(default=None)
    turnover: Mapped[int | None] = mapped_column(default=None)  # paise
    is_gst_registered: Mapped[bool] = mapped_column(default=False)
    statutory_audit_applicable: Mapped[bool] = mapped_column(default=False)
    # Enum: APPLICABLE / NOT_APPLICABLE / REQUIRES_REVIEW
    tax_audit_status: Mapped[str] = mapped_column(default="REQUIRES_REVIEW")
    consolidated_fs_applicable: Mapped[bool] = mapped_column(default=False)
    prior_year_data_available: Mapped[bool] = mapped_column(default=False)
    overall_materiality: Mapped[int | None] = mapped_column(default=None)  # paise
    performance_materiality: Mapped[int | None] = mapped_column(default=None)  # paise
    clearly_trivial_threshold: Mapped[int | None] = mapped_column(default=None)  # paise

    engagement: Mapped["Engagement"] = relationship(back_populates="entity_profile")


class Applicability(Base):
    __tablename__ = "applicability"
    __table_args__ = (
        # One applicability row per (engagement, area) — a second row for
        # the same area would make "which one is current" ambiguous.
        UniqueConstraint("engagement_id", "area", name="uq_applicability_engagement_area"),
    )

    applicability_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.engagement_id"))
    area: Mapped[str] = mapped_column()  # e.g. "Ind AS", "Tax Audit Review", "SEBI/LODR"
    # System suggestion — always shown labeled as a suggestion, never a conclusion.
    system_suggested_status: Mapped[str] = mapped_column()  # YES / NO / REVIEW_REQUIRED
    system_suggested_reason: Mapped[str | None] = mapped_column(default=None)
    # User/professional confirmation — nullable until a reviewer acts.
    user_confirmed_status: Mapped[str | None] = mapped_column(default=None)  # APPLICABLE / NOT_APPLICABLE / REQUIRES_FURTHER_REVIEW
    user_confirmation_note: Mapped[str | None] = mapped_column(default=None)
    confirmed_by: Mapped[str | None] = mapped_column(default=None)
    confirmed_at: Mapped[str | None] = mapped_column(default=None)

    engagement: Mapped["Engagement"] = relationship(back_populates="applicability_rows")
