"""Layer 2 engagement. Build Prompt v2 §5.3."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.clauses.model import CarryForward
from app.db import Base
from app.models.enums import EngagementStatus, GoingConcern, OpinionType, ResponseSource


class Engagement(Base):
    __tablename__ = "engagement"
    __table_args__ = (UniqueConstraint("client_id", "fy_code", name="ux_engagement_client_fy"),)

    engagement_id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.client_id"))
    fy_code: Mapped[str] = mapped_column(String(9))
    fy_start: Mapped[date] = mapped_column(Date)
    fy_end: Mapped[date] = mapped_column(Date)

    # Pins the profile version in force at the reporting date, so a finalised
    # document keeps printing the master data it was signed with (§18.6).
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("client_profile.profile_id"), default=None
    )

    partner_id: Mapped[int | None] = mapped_column(ForeignKey("partner.partner_id"), default=None)
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("user.user_id"), default=None)

    opinion_type: Mapped[OpinionType | None] = mapped_column(
        Enum(OpinionType, native_enum=False), default=None
    )
    going_concern: Mapped[GoingConcern] = mapped_column(
        Enum(GoingConcern, native_enum=False), default=GoingConcern.NONE
    )

    appointment_date: Mapped[date | None] = mapped_column(Date, default=None)
    commencement_date: Mapped[date | None] = mapped_column(Date, default=None)
    expected_completion: Mapped[date | None] = mapped_column(Date, default=None)
    report_date: Mapped[date | None] = mapped_column(Date, default=None)
    place: Mapped[str] = mapped_column(String(120), default="")

    audit_fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    oope: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    gst_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)

    status: Mapped[EngagementStatus] = mapped_column(
        Enum(EngagementStatus, native_enum=False), default=EngagementStatus.NOT_STARTED
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    locked_by: Mapped[str] = mapped_column(String(200), default="")

    rolled_from: Mapped[int | None] = mapped_column(
        ForeignKey("engagement.engagement_id"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    responses: Mapped[list[EngagementResponse]] = relationship(back_populates="engagement")

    @property
    def is_locked(self) -> bool:
        return self.status in (EngagementStatus.FINALISED, EngagementStatus.ARCHIVED)


class FieldCatalog(Base):
    """Generated at startup from the YAML, never hand-maintained (§5.3).

    This is what makes acceptance criterion 12 possible: a new CARO clause is
    added by editing YAML, and the catalogue follows without a migration.
    """

    __tablename__ = "field_catalog"

    field_key: Mapped[str] = mapped_column(String(120), primary_key=True)
    document: Mapped[str] = mapped_column(String(60))
    clause_id: Mapped[str] = mapped_column(String(120), default="")
    clause_ref: Mapped[str] = mapped_column(String(200), default="")
    label: Mapped[str] = mapped_column(Text, default="")
    datatype: Mapped[str] = mapped_column(String(30))
    options_json: Mapped[str] = mapped_column(Text, default="[]")
    carry_forward: Mapped[CarryForward] = mapped_column(
        Enum(CarryForward, native_enum=False), default=CarryForward.PROMPT
    )
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[date | None] = mapped_column(Date, default=None)
    effective_to: Mapped[date | None] = mapped_column(Date, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class EngagementResponse(Base):
    """EAV. Deliberate (§5.3): the questionnaire changes with every amendment,
    and fixed columns would force a migration each year."""

    __tablename__ = "engagement_response"

    engagement_id: Mapped[int] = mapped_column(
        ForeignKey("engagement.engagement_id"), primary_key=True
    )
    field_key: Mapped[str] = mapped_column(ForeignKey("field_catalog.field_key"), primary_key=True)

    # Typed columns, not one stringly-typed value (§12, §19).
    value_text: Mapped[str | None] = mapped_column(Text, default=None)
    value_num: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    value_date: Mapped[date | None] = mapped_column(Date, default=None)

    source: Mapped[ResponseSource] = mapped_column(
        Enum(ResponseSource, native_enum=False), default=ResponseSource.USER
    )
    # The distinction between "same as last year" and "verified for the
    # current year" (§6.2). Export is blocked while a prompt-policy answer
    # remains unreviewed.
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[str] = mapped_column(String(200), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    wp_reference: Mapped[str] = mapped_column(String(120), default="")
    updated_by: Mapped[str] = mapped_column(String(200), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    engagement: Mapped[Engagement] = relationship(back_populates="responses")


class _ChildRecord(Base):
    """Shared shape for every repeating block (§3.2, §5.3)."""

    __abstract__ = True

    row_index: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[ResponseSource] = mapped_column(
        Enum(ResponseSource, native_enum=False), default=ResponseSource.USER
    )
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)


class Litigation(_ChildRecord):
    __tablename__ = "litigation"

    litigation_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    forum: Mapped[str] = mapped_column(String(250))
    case_number: Mapped[str] = mapped_column(String(120), default="")
    nature: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    period: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(30), default="pending")
    mgmt_assessment: Mapped[str] = mapped_column(Text, default="")


class StatutoryDue(_ChildRecord):
    __tablename__ = "statutory_due"

    statutory_due_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    statute: Mapped[str] = mapped_column(String(200))
    nature: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    period: Mapped[str] = mapped_column(String(60), default="")
    forum: Mapped[str] = mapped_column(String(250), default="")
    amount_paid: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)


class IfcDeficiency(_ChildRecord):
    __tablename__ = "ifc_deficiency"

    deficiency_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    title: Mapped[str] = mapped_column(String(250))
    process: Mapped[str] = mapped_column(String(200), default="")
    control: Mapped[str] = mapped_column(Text, default="")
    nature: Mapped[str] = mapped_column(Text, default="")
    risk: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(40), default="")
    management_response: Mapped[str] = mapped_column(Text, default="")
    auditor_assessment: Mapped[str] = mapped_column(Text, default="")
    remediation_status: Mapped[str] = mapped_column(String(40), default="")


class BoardMeeting(_ChildRecord):
    __tablename__ = "board_meeting"

    meeting_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    meeting_date: Mapped[date] = mapped_column(Date)
    directors_present: Mapped[int] = mapped_column(Integer, default=0)
    total_directors: Mapped[int] = mapped_column(Integer, default=0)
    # Typed rather than computed from the two counts above. It is the firm's
    # own column and a meeting can legitimately show a figure that simple
    # division does not give -- leave of absence, a director appointed
    # mid-meeting -- so the Board's Report prints what the minutes say.
    attendance_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)


class Mgt9BusinessActivity(_ChildRecord):
    """MGT-9 Part II. Activities contributing 10% or more of turnover."""

    __tablename__ = "mgt9_business_activity"

    activity_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    activity_name: Mapped[str] = mapped_column(Text, default="")
    nic_code: Mapped[str] = mapped_column(String(20), default="")
    turnover_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)


class Mgt9Shareholding(_ChildRecord):
    """MGT-9 Part IV(A). Category-wise shareholding."""

    __tablename__ = "mgt9_shareholding"

    shareholding_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    category: Mapped[str] = mapped_column(Text, default="")
    shares_begin: Mapped[str] = mapped_column(String(60), default="")
    shares_end: Mapped[str] = mapped_column(String(60), default="")


class Mgt9PromoterHolding(_ChildRecord):
    """MGT-9 Part IV(B). Shareholding of promoters, and of the top ten."""

    __tablename__ = "mgt9_promoter_holding"

    holding_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    shareholder_name: Mapped[str] = mapped_column(Text, default="")
    shares_begin: Mapped[int] = mapped_column(Integer, default=0)
    pct_begin: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    shares_end: Mapped[int] = mapped_column(Integer, default=0)
    pct_end: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)


class Mgt9DirectorHolding(_ChildRecord):
    """MGT-9 Part IV(E). Shareholding of directors and key managerial personnel."""

    __tablename__ = "mgt9_director_holding"

    holding_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    person_name: Mapped[str] = mapped_column(Text, default="")
    shares_begin: Mapped[str] = mapped_column(String(60), default="")
    change: Mapped[str] = mapped_column(Text, default="")
    shares_end: Mapped[str] = mapped_column(String(60), default="")


class Mgt9Indebtedness(_ChildRecord):
    """MGT-9 Part V. Indebtedness including interest accrued but not due."""

    __tablename__ = "mgt9_indebtedness"

    indebtedness_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    particulars: Mapped[str] = mapped_column(Text, default="")
    secured: Mapped[str] = mapped_column(String(60), default="")
    unsecured: Mapped[str] = mapped_column(String(60), default="")
    deposits: Mapped[str] = mapped_column(String(60), default="")
    total: Mapped[str] = mapped_column(String(60), default="")


class PoshComplaint(_ChildRecord):
    """Complaints under the POSH Act, where any arose in the year.

    Only collected for the 'complaints received' answer: the nil case states
    its three particulars in words, which cannot be left half-filled the way a
    table of zeros can.
    """

    __tablename__ = "posh_complaint"

    complaint_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    particulars: Mapped[str] = mapped_column(Text, default="")
    number: Mapped[int] = mapped_column(Integer, default=0)


class DirectorChange(_ChildRecord):
    """Appointments and cessations falling in the financial year.

    Computed from the director register, never typed (§18.8).
    """

    __tablename__ = "director_change"

    change_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    director_id: Mapped[int] = mapped_column(ForeignKey("director.director_id"))
    change_type: Mapped[str] = mapped_column(String(20))
    effective_date: Mapped[date] = mapped_column(Date)


# --------------------------------------------------------------------------
# Repeating blocks added with the Phase 2 clause authoring.
#
# Every one of these backs a `repeating_block` declared in `content/`. They
# were missing: the clauses were authored with tables and nothing stored the
# rows, so the workspace raised `KeyError` for any document containing one.
# `tests/test_repeating_blocks.py` now fails if a declared entity has no
# model, or if a model is missing a column the YAML names.
#
# Column types follow the YAML datatype: text -> String, longtext -> Text,
# select -> String, amount -> Numeric, date -> Date. Amounts are Numeric and
# dates are Date so that §12's Indian grouping and §19's "never store a
# formatted string" hold for child rows too, not just for answers.
# --------------------------------------------------------------------------


class KeyAuditMatter(_ChildRecord):
    """SA 701. Applies where the `kam` flag is true."""

    __tablename__ = "key_audit_matter"

    matter_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    matter: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text, default="")


class UncorrectedMisstatement(_ChildRecord):
    """SA 450 para 14 — the schedule attached to the representation letter."""

    __tablename__ = "uncorrected_misstatement"

    misstatement_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    description: Mapped[str] = mapped_column(Text)
    financial_statement_line: Mapped[str] = mapped_column(String(250), default="")
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    effect: Mapped[str] = mapped_column(String(250), default="")


class FinancialSummary(_ChildRecord):
    """Rule 8(5)(i) — the Board's Report financial highlights."""

    __tablename__ = "financial_summary"

    summary_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    particulars: Mapped[str] = mapped_column(String(250))
    current_year: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    previous_year: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)


class ForexParticulars(_ChildRecord):
    """s.134(3)(m) — foreign exchange earned and used."""

    __tablename__ = "forex_particulars"

    forex_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    particulars: Mapped[str] = mapped_column(String(250))
    current_year: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    previous_year: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)


class Loan186(_ChildRecord):
    """s.134(3)(g) read with s.186 — loans, guarantees, security, investments."""

    __tablename__ = "loan_186"

    loan_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    party: Mapped[str] = mapped_column(String(250))
    nature: Mapped[str] = mapped_column(String(60), default="")
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    purpose: Mapped[str] = mapped_column(Text, default="")


class RelatedPartyContract(_ChildRecord):
    """Form AOC-2. Rule 8(2) prescribes the columns."""

    __tablename__ = "related_party_contract"

    contract_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    party: Mapped[str] = mapped_column(String(250))
    relationship: Mapped[str] = mapped_column(String(120), default="")
    contract_nature: Mapped[str] = mapped_column(Text, default="")
    duration: Mapped[str] = mapped_column(String(120), default="")
    salient_terms: Mapped[str] = mapped_column(Text, default="")
    approval_date: Mapped[date | None] = mapped_column(Date, default=None)
    advance_paid: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)


class SubsidiaryChange(_ChildRecord):
    """Rule 8(5)(iv) — companies which became or ceased to be subsidiaries,
    joint ventures or associates."""

    __tablename__ = "subsidiary_change"

    row_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    name: Mapped[str] = mapped_column(String(250))
    relationship: Mapped[str] = mapped_column(String(60), default="")
    change: Mapped[str] = mapped_column(String(40), default="")
    change_date: Mapped[date | None] = mapped_column(Date, default=None)


class DepositParticulars(_ChildRecord):
    """Rule 8(5)(v) — deposits covered under Chapter V."""

    __tablename__ = "deposit_particulars"

    row_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    particulars: Mapped[str] = mapped_column(String(250))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    remarks: Mapped[str] = mapped_column(Text, default="")


class EmployeeRemuneration(_ChildRecord):
    """s.197(12) read with Rule 5. Driven by the `s197` applicability flag."""

    __tablename__ = "employee_remuneration"

    row_id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.engagement_id"))
    name: Mapped[str] = mapped_column(String(200))
    designation: Mapped[str] = mapped_column(String(120), default="")
    remuneration: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    qualification: Mapped[str] = mapped_column(Text, default="")
    date_of_employment: Mapped[date | None] = mapped_column(Date, default=None)
