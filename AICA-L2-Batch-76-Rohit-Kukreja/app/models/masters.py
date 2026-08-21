"""Layer 1 masters. Build Prompt v2 §5.1 and §5.2."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import CompanyType, Designation, Framework, KmpRole, Role


class Firm(Base):
    __tablename__ = "firm"

    firm_id: Mapped[int] = mapped_column(primary_key=True)
    firm_name: Mapped[str] = mapped_column(String(200))
    frn: Mapped[str] = mapped_column(String(10), unique=True)
    address: Mapped[str] = mapped_column(Text, default="")
    logo_path: Mapped[str] = mapped_column(String(400), default="")
    default_place: Mapped[str] = mapped_column(String(100), default="")

    # Document defaults (§5.1). Kept here so a firm can restyle output
    # without a code change.
    doc_font: Mapped[str] = mapped_column(String(60), default="Times New Roman")
    doc_font_size: Mapped[int] = mapped_column(default=10)
    doc_margin_mm: Mapped[str] = mapped_column(String(40), default="25,25,25,30")
    doc_header: Mapped[str] = mapped_column(Text, default="")
    doc_footer: Mapped[str] = mapped_column(Text, default="")
    doc_page_numbering: Mapped[bool] = mapped_column(Boolean, default=True)

    partners: Mapped[list[Partner]] = relationship(back_populates="firm")


class FieldDefault(Base):
    """The firm's standing answer to one clause question (decision 28).

    Set once at Admin -> Default Answers and applied to every engagement the
    firm creates afterwards, so a clean file does not have to be answered from
    scratch each year for each client.

    **Firm-scoped, not global.** Two firms sharing an installation are two
    practices with their own house positions, and `firm_id` is what stops one
    of them silently answering the other's reports.

    **Not a copy of the answer.** The answer lives on the engagement, in
    `engagement_response`, written when the engagement is created and marked
    `ResponseSource.DEFAULT`. This table is only the template. Editing it never
    reaches an engagement that already exists -- an audit file in progress must
    not change under the auditor because someone edited a settings screen.
    """

    __tablename__ = "field_default"

    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.firm_id"), primary_key=True)
    field_key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(String(120))
    updated_by: Mapped[str] = mapped_column(String(120), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Partner(Base):
    __tablename__ = "partner"

    partner_id: Mapped[int] = mapped_column(primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.firm_id"))
    partner_name: Mapped[str] = mapped_column(String(200))
    membership_no: Mapped[str] = mapped_column(String(10), unique=True)
    is_signing: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    firm: Mapped[Firm] = relationship(back_populates="partners")


class User(Base):
    __tablename__ = "user"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.firm_id"))
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, default=None)


class Client(Base):
    """Immutable identity. Never versioned (§5.1).

    Everything that can change over time lives on `client_profile`.
    """

    __tablename__ = "client"

    client_id: Mapped[int] = mapped_column(primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.firm_id"))
    client_code: Mapped[str] = mapped_column(String(30), unique=True)
    cin: Mapped[str] = mapped_column(String(21), unique=True)
    pan: Mapped[str] = mapped_column(String(10), default="")
    date_of_incorp: Mapped[date | None] = mapped_column(Date, default=None)

    # Who usually signs for this client (decision 67). Copied onto a new
    # engagement when the year is opened, and overridable there -- a year
    # signed by someone else still can be. Deliberately NOT on
    # `client_profile`: it is the firm's own assignment rather than a fact
    # about the company, no document prints it, and versioning it would open a
    # profile version every time a partner changed.
    default_partner_id: Mapped[int | None] = mapped_column(
        # Named, because SQLite alters tables by rebuilding them and an unnamed
        # constraint cannot be referred to in the rebuild.
        ForeignKey("partner.partner_id", name="fk_client_default_partner"),
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(200), default="")

    profiles: Mapped[list[ClientProfile]] = relationship(back_populates="client")
    directors: Mapped[list[Director]] = relationship(back_populates="client")
    kmps: Mapped[list[Kmp]] = relationship(back_populates="client")


class ClientProfile(Base):
    """Slowly Changing Dimension Type 2 (§5.1).

    The application must never UPDATE a current profile's business fields. A
    change closes the current row and inserts a new one — see
    `app.services.client.change_profile`, which is the only supported path.

    Why: a finalised FY 2024-25 document must keep printing the address that
    was in force when it was signed, even after the company moves.
    """

    __tablename__ = "client_profile"
    __table_args__ = (
        # One current row per client (§5.1). A partial unique index, so the
        # database refuses two current profiles even if a service-layer bug
        # tries. SQLite and PostgreSQL both honour the WHERE clause.
        Index(
            "ux_client_profile_current",
            "client_id",
            unique=True,
            sqlite_where=text("is_current = 1"),
            postgresql_where=text("is_current = true"),
        ),
    )

    profile_id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.client_id"))

    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date, default=None)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    # WHAT THIS TABLE HOLDS, AND WHY (decision 62, 20 Aug 2026).
    #
    # Only what a document prints or an applicability flag reads. Fifteen
    # columns went at that review because nothing read them: a corporate
    # address no letterhead used, a phone and an email nothing printed, a
    # free-text industry sitting beside the boolean that actually decides cost
    # records, a nature-of-business duplicating the Board's Report clause that
    # carries it, an `amounts_in` never wired to the formatter, the seven
    # figures that stopped driving anything when applicability became declared,
    # and the two public-company relationship flags that went with CARO's
    # inference.
    #
    # A field nobody reads is not free. It is asked for at onboarding, carried
    # into every later version of the profile, shown on screen, and eventually
    # believed -- and then someone corrects it and watches nothing move.
    company_name: Mapped[str] = mapped_column(String(250))
    registered_addr: Mapped[str] = mapped_column(Text, default="")
    website: Mapped[str] = mapped_column(String(255), default="")

    company_type: Mapped[CompanyType] = mapped_column(
        Enum(CompanyType, native_enum=False), default=CompanyType.PVT
    )
    framework: Mapped[Framework] = mapped_column(
        Enum(Framework, native_enum=False), default=Framework.IGAAP
    )

    # s.129(3) reaches associates and joint ventures, not subsidiaries alone.
    # Nullable on purpose: unrecorded must be distinguishable from "no", or
    # the applicability engine would answer a question nobody has asked.
    has_subsidiary: Mapped[bool | None] = mapped_column(Boolean, default=None)
    has_associate: Mapped[bool | None] = mapped_column(Boolean, default=None)
    has_joint_venture: Mapped[bool | None] = mapped_column(Boolean, default=None)

    # Rule 6 exemption from preparing consolidated financial statements.
    is_wholly_owned_or_unopposed_partially_owned: Mapped[bool] = mapped_column(
        Boolean, default=False
    )
    not_listed_or_in_process_of_listing: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_files_compliant_cfs: Mapped[bool] = mapped_column(Boolean, default=False)

    # Cost records are industry-driven, so no threshold can decide them.
    cost_records_industry: Mapped[bool | None] = mapped_column(Boolean, default=None)

    # Applicability flags, each paired with an override (§5.1, §7). The
    # computed value is authoritative unless *_override is set.
    caro: Mapped[bool] = mapped_column(Boolean, default=False)
    caro_override: Mapped[bool] = mapped_column(Boolean, default=False)
    ifc: Mapped[bool] = mapped_column(Boolean, default=False)
    ifc_override: Mapped[bool] = mapped_column(Boolean, default=False)
    s197: Mapped[bool] = mapped_column(Boolean, default=False)
    s197_override: Mapped[bool] = mapped_column(Boolean, default=False)
    csr: Mapped[bool] = mapped_column(Boolean, default=False)
    csr_override: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_records: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_records_override: Mapped[bool] = mapped_column(Boolean, default=False)
    internal_audit: Mapped[bool] = mapped_column(Boolean, default=False)
    internal_audit_override: Mapped[bool] = mapped_column(Boolean, default=False)
    kam: Mapped[bool] = mapped_column(Boolean, default=False)
    kam_override: Mapped[bool] = mapped_column(Boolean, default=False)
    # These three were declared in FLAGS but had no columns, so the override
    # screen silently could not reach them: `OVERRIDE_COLUMNS` is built by
    # `hasattr`, and a flag with no column simply dropped out of the list.
    # §7 promises every flag is overridable with a reason.
    secretarial_audit: Mapped[bool] = mapped_column(Boolean, default=False)
    secretarial_audit_override: Mapped[bool] = mapped_column(Boolean, default=False)
    abridged_board_report: Mapped[bool] = mapped_column(Boolean, default=False)
    abridged_board_report_override: Mapped[bool] = mapped_column(Boolean, default=False)
    cfs_required: Mapped[bool] = mapped_column(Boolean, default=False)
    cfs_required_override: Mapped[bool] = mapped_column(Boolean, default=False)

    changed_by: Mapped[str] = mapped_column(String(200), default="")
    change_reason: Mapped[str] = mapped_column(Text, default="")
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    client: Mapped[Client] = relationship(back_populates="profiles")


class Director(Base):
    """Directors are structured records with effective dates, never free text.

    §5.2 and §19 — the prototype stored them as free text, so the Directors'
    Report, the s.164(2) representation and the signature block could all
    disagree with each other.
    """

    __tablename__ = "director"

    director_id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.client_id"))
    name: Mapped[str] = mapped_column(String(200))
    din: Mapped[str] = mapped_column(String(8))
    designation: Mapped[Designation] = mapped_column(Enum(Designation, native_enum=False))
    appointment_date: Mapped[date] = mapped_column(Date)
    cessation_date: Mapped[date | None] = mapped_column(Date, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    client: Mapped[Client] = relationship(back_populates="directors")


class Kmp(Base):
    __tablename__ = "kmp"

    kmp_id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.client_id"))
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[KmpRole] = mapped_column(Enum(KmpRole, native_enum=False))
    pan: Mapped[str] = mapped_column(String(10), default="")
    appointment_date: Mapped[date] = mapped_column(Date)
    cessation_date: Mapped[date | None] = mapped_column(Date, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    client: Mapped[Client] = relationship(back_populates="kmps")


class Banker(Base):
    __tablename__ = "banker"

    banker_id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.client_id"))
    bank_name: Mapped[str] = mapped_column(String(200))
    branch: Mapped[str] = mapped_column(String(200), default="")
    facility_type: Mapped[str] = mapped_column(String(120), default="")
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, default=None)
