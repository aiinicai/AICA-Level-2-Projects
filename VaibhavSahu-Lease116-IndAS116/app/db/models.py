"""ORM data model (normalised; versioned calculation runs; append-only audit trail).

Monetary values are stored as exact decimal TEXT (DecimalText) so that SQLite never
converts them to binary floating point.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, TypeDecorator,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class DecimalText(TypeDecorator):
    impl = String(48)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None or value == "":
            return None
        return str(Decimal(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return Decimal(value)


def now():
    return datetime.now()


# --------------------------------------------------------------------------- organisation & security
class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    framework: Mapped[str] = mapped_column(String(20), default="IND_AS_116")
    functional_currency: Mapped[str] = mapped_column(String(3), default="INR")
    fy_start_month: Mapped[int] = mapped_column(Integer, default=4)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Entity(Base):
    __tablename__ = "entities"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(200))
    functional_currency: Mapped[str] = mapped_column(String(3), default="INR")
    cin: Mapped[Optional[str]] = mapped_column(String(30))
    pan: Mapped[Optional[str]] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("company_id", "code"),)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    permissions: Mapped[list] = mapped_column(JSON, default=list)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[Optional[str]] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(300))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    all_entities: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    role: Mapped[Role] = relationship()


class UserEntityAccess(Base):
    __tablename__ = "user_entity_access"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"))
    __table_args__ = (UniqueConstraint("user_id", "entity_id"),)


# --------------------------------------------------------------------------- master data
class Counterparty(Base):
    __tablename__ = "counterparties"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(200))
    vendor_id: Mapped[Optional[str]] = mapped_column(String(40))
    related_party: Mapped[bool] = mapped_column(Boolean, default=False)
    contact_person: Mapped[Optional[str]] = mapped_column(String(120))
    email: Mapped[Optional[str]] = mapped_column(String(160))
    phone: Mapped[Optional[str]] = mapped_column(String(40))
    address: Mapped[Optional[str]] = mapped_column(Text)
    pan: Mapped[Optional[str]] = mapped_column(String(20))
    gstin: Mapped[Optional[str]] = mapped_column(String(20))


class AssetClass(Base):
    __tablename__ = "asset_classes"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(120))
    short_term_election: Mapped[bool] = mapped_column(Boolean, default=False)   # para 8
    non_lease_expedient: Mapped[bool] = mapped_column(Boolean, default=False)   # para 15
    default_useful_life_months: Mapped[Optional[int]] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("company_id", "code"),)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    description: Mapped[str] = mapped_column(Text)
    asset_class_id: Mapped[Optional[int]] = mapped_column(ForeignKey("asset_classes.id"))
    location: Mapped[Optional[str]] = mapped_column(String(250))
    identifier: Mapped[Optional[str]] = mapped_column(String(80))
    value_when_new = mapped_column(DecimalText)
    useful_life_months: Mapped[Optional[int]] = mapped_column(Integer)
    area_sqft = mapped_column(DecimalText)


# --------------------------------------------------------------------------- lease
class Lease(Base):
    __tablename__ = "leases"
    id: Mapped[int] = mapped_column(primary_key=True)
    lease_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True)
    role: Mapped[str] = mapped_column(String(10), default="LESSEE")            # LESSEE | LESSOR
    lease_type: Mapped[str] = mapped_column(String(20), default="STANDARD")    # STANDARD | SHORT_TERM | LOW_VALUE | SUBLEASE | SALE_LEASEBACK
    status: Mapped[str] = mapped_column(String(20), default="Draft", index=True)
    description: Mapped[str] = mapped_column(String(300), default="")
    asset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assets.id"))
    asset_class_id: Mapped[Optional[int]] = mapped_column(ForeignKey("asset_classes.id"))
    asset_description: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(String(250))
    business_unit: Mapped[Optional[str]] = mapped_column(String(80))
    cost_centre: Mapped[Optional[str]] = mapped_column(String(80))
    department: Mapped[Optional[str]] = mapped_column(String(80))
    project: Mapped[Optional[str]] = mapped_column(String(80))
    counterparty_id: Mapped[Optional[int]] = mapped_column(ForeignKey("counterparties.id"))
    contract_number: Mapped[Optional[str]] = mapped_column(String(80))
    contract_date: Mapped[Optional[date]] = mapped_column(Date)
    commencement_date: Mapped[Optional[date]] = mapped_column(Date)
    availability_date: Mapped[Optional[date]] = mapped_column(Date)
    contract_end: Mapped[Optional[date]] = mapped_column(Date)
    enforceable_end: Mapped[Optional[date]] = mapped_column(Date)
    enforceable_rationale: Mapped[Optional[str]] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    payment_frequency: Mapped[str] = mapped_column(String(15), default="MONTHLY")
    payment_timing: Mapped[str] = mapped_column(String(10), default="ADVANCE")
    discount_rate_pct = mapped_column(DecimalText)
    rate_basis: Mapped[str] = mapped_column(String(10), default="IBR")
    discount_rate_id: Mapped[Optional[int]] = mapped_column(ForeignKey("discount_rates.id"))
    rate_source: Mapped[Optional[str]] = mapped_column(Text)
    useful_life_end: Mapped[Optional[date]] = mapped_column(Date)
    ownership_transfers: Mapped[bool] = mapped_column(Boolean, default=False)
    non_lease_expedient: Mapped[Optional[bool]] = mapped_column(Boolean)      # None = follow asset class
    generator_config: Mapped[Optional[dict]] = mapped_column(JSON)
    policy_overrides: Mapped[Optional[dict]] = mapped_column(JSON)
    opening_balance: Mapped[Optional[dict]] = mapped_column(JSON)
    lessor_details: Mapped[Optional[dict]] = mapped_column(JSON)
    slb_details: Mapped[Optional[dict]] = mapped_column(JSON)
    sublease_details: Mapped[Optional[dict]] = mapped_column(JSON)
    exemption_details: Mapped[Optional[dict]] = mapped_column(JSON)
    tax_settings: Mapped[Optional[dict]] = mapped_column(JSON)
    head_lease_id: Mapped[Optional[int]] = mapped_column(ForeignKey("leases.id"))
    source_extraction_id: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    inputs_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)     # last change to calculation inputs
    prepared_by: Mapped[Optional[int]] = mapped_column(Integer)
    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer)
    approved_by: Mapped[Optional[int]] = mapped_column(Integer)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    entity: Mapped[Entity] = relationship()
    counterparty: Mapped[Optional[Counterparty]] = relationship()
    asset_class: Mapped[Optional[AssetClass]] = relationship()
    options: Mapped[list["LeaseOptionRow"]] = relationship(cascade="all, delete-orphan", order_by="LeaseOptionRow.id")
    payments: Mapped[list["PaymentScheduleRow"]] = relationship(cascade="all, delete-orphan", order_by="PaymentScheduleRow.line_no")
    costs: Mapped[list["LeaseCost"]] = relationship(cascade="all, delete-orphan")
    components: Mapped[list["LeaseComponent"]] = relationship(cascade="all, delete-orphan")
    deposits: Mapped[list["Deposit"]] = relationship(cascade="all, delete-orphan")
    restorations: Mapped[list["RestorationObligation"]] = relationship(cascade="all, delete-orphan")
    events: Mapped[list["LeaseEventRow"]] = relationship(cascade="all, delete-orphan", order_by="LeaseEventRow.effective_date")


class LeaseAssessment(Base):
    __tablename__ = "lease_assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    lease_id: Mapped[int] = mapped_column(ForeignKey("leases.id"), unique=True)
    identified_asset: Mapped[Optional[bool]] = mapped_column(Boolean)
    substitution_rights: Mapped[Optional[str]] = mapped_column(String(20))       # NONE | NOT_SUBSTANTIVE | SUBSTANTIVE
    economic_benefits: Mapped[Optional[bool]] = mapped_column(Boolean)
    directs_use: Mapped[Optional[bool]] = mapped_column(Boolean)
    contains_lease: Mapped[Optional[bool]] = mapped_column(Boolean)
    separate_components: Mapped[Optional[bool]] = mapped_column(Boolean)
    allocation_method: Mapped[Optional[str]] = mapped_column(String(60))
    exemption: Mapped[str] = mapped_column(String(15), default="NONE")          # NONE | SHORT_TERM | LOW_VALUE
    asset_value_when_new = mapped_column(DecimalText)
    benefits_on_own: Mapped[Optional[bool]] = mapped_column(Boolean)
    not_highly_dependent: Mapped[Optional[bool]] = mapped_column(Boolean)
    conclusion: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    assessed_by: Mapped[Optional[int]] = mapped_column(Integer)
    assessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class LeaseComponent(Base):
    __tablename__ = "lease_components"
    id: Mapped[int] = mapped_column(primary_key=True)
    lease_id: Mapped[int] = mapped_column(ForeignKey("leases.id"), index=True)
    component_type: Mapped[str] = mapped_column(String(15))   # LEASE | NON_LEASE
    description: Mapped[str] = mapped_column(String(200))
    standalone_price = mapped_column(DecimalText)
    allocated_amount = mapped_column(DecimalText)


class LeaseOptionRow(Base):
    __tablename__ = "lease_options"
    id: Mapped[int] = mapped_column(primary_key=True)
    lease_id: Mapped[int] = mapped_column(ForeignKey("leases.id"), index=True)
    kind: Mapped[str] = mapped_column(String(15))
    holder: Mapped[str] = mapped_column(String(10), default="LESSEE")
    exercise_date: Mapped[Optional[date]] = mapped_column(Date)
    extension_end_date: Mapped[Optional[date]] = mapped_column(Date)
    price = mapped_column(DecimalText)
    reasonably_certain: Mapped[Optional[bool]] = mapped_column(Boolean)
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(String(300))
    renewal_escalation_pct = mapped_column(DecimalText)
    approval_date: Mapped[Optional[date]] = mapped_column(Date)
    last_reassessment_date: Mapped[Optional[date]] = mapped_column(Date)


class PaymentScheduleRow(Base):
    __tablename__ = "payment_schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    lease_id: Mapped[int] = mapped_column(ForeignKey("leases.id"), index=True)
    line_no: Mapped[int] = mapped_column(Integer)
    payment_date: Mapped[date] = mapped_column(Date)
    period_start: Mapped[Optional[date]] = mapped_column(Date)
    period_end: Mapped[Optional[date]] = mapped_column(Date)
    lease_amount = mapped_column(DecimalText)
    non_lease_amount = mapped_column(DecimalText)
    category: Mapped[str] = mapped_column(String(25), default="FIXED")
    include_override: Mapped[Optional[bool]] = mapped_column(Boolean)
    override_reason: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(15), default="GENERATED")
    fx_rate = mapped_column(DecimalText)


class LeaseCost(Base):
    __tablename__ = "lease_costs"
    id: Mapped[int] = mapped_column(primary_key=True)
    lease_id: Mapped[int] = mapped_column(ForeignKey("leases.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))       # IDC | INCENTIVE | PREPAID | OTHER
    cost_date: Mapped[date] = mapped_column(Date)
    amount = mapped_column(DecimalText)
    description: Mapped[Optional[str]] = mapped_column(String(200))


class Deposit(Base):
    __tablename__ = "deposits"
    id: Mapped[int] = mapped_column(primary_key=True)
    lease_id: Mapped[int] = mapped_column(ForeignKey("leases.id"), index=True)
    amount = mapped_column(DecimalText)
    payment_date: Mapped[date] = mapped_column(Date)
    refund_date: Mapped[date] = mapped_column(Date)
    interest_bearing: Mapped[bool] = mapped_column(Boolean, default=False)
    contractual_rate_pct = mapped_column(DecimalText)
    market_rate_pct = mapped_column(DecimalText)
    treat_difference_as_prepaid_rent: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class RestorationObligation(Base):
    __tablename__ = "restoration_obligations"
    id: Mapped[int] = mapped_column(primary_key=True)
    lease_id: Mapped[int] = mapped_column(ForeignKey("leases.id"), index=True)
    estimated_cost = mapped_column(DecimalText)
    settlement_date: Mapped[date] = mapped_column(Date)
    discount_rate_pct = mapped_column(DecimalText)
    recognition_date: Mapped[Optional[date]] = mapped_column(Date)
    cost_is_current_price: Mapped[bool] = mapped_column(Boolean, default=False)
    inflation_pct = mapped_column(DecimalText)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class LeaseEventRow(Base):
    """Modifications, reassessments, terminations, impairment records and restoration revisions."""
    __tablename__ = "lease_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    lease_id: Mapped[int] = mapped_column(ForeignKey("leases.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(25))
    subtype: Mapped[Optional[str]] = mapped_column(String(25))
    effective_date: Mapped[date] = mapped_column(Date)
    description: Mapped[Optional[str]] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    result: Mapped[Optional[dict]] = mapped_column(JSON)
    prepared_by: Mapped[Optional[int]] = mapped_column(Integer)
    approved_by: Mapped[Optional[int]] = mapped_column(Integer)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class DiscountRate(Base):
    __tablename__ = "discount_rates"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entities.id"))
    scope: Mapped[str] = mapped_column(String(15), default="PORTFOLIO")    # SINGLE | PORTFOLIO | LEASE
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    tenor_from_months: Mapped[int] = mapped_column(Integer, default=0)
    tenor_to_months: Mapped[int] = mapped_column(Integer, default=600)
    rate_pct = mapped_column(DecimalText)
    rate_type: Mapped[str] = mapped_column(String(10), default="IBR")
    security: Mapped[Optional[str]] = mapped_column(String(80))
    source: Mapped[Optional[str]] = mapped_column(Text)
    methodology: Mapped[Optional[str]] = mapped_column(Text)
    effective_date: Mapped[date] = mapped_column(Date)
    documentation: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(15), default="Draft")
    approved_by: Mapped[Optional[int]] = mapped_column(Integer)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class FxRate(Base):
    __tablename__ = "fx_rates"
    id: Mapped[int] = mapped_column(primary_key=True)
    from_ccy: Mapped[str] = mapped_column(String(3))
    to_ccy: Mapped[str] = mapped_column(String(3))
    rate_date: Mapped[date] = mapped_column(Date)
    rate = mapped_column(DecimalText)
    rate_type: Mapped[str] = mapped_column(String(10), default="CLOSING")   # SPOT | AVERAGE | CLOSING
    source: Mapped[Optional[str]] = mapped_column(String(120))
    __table_args__ = (Index("ix_fx", "from_ccy", "to_ccy", "rate_date"),)


# --------------------------------------------------------------------------- calculations (immutable once approved)
class CalcRun(Base):
    __tablename__ = "calc_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    lease_id: Mapped[int] = mapped_column(ForeignKey("leases.id"), index=True)
    run_no: Mapped[int] = mapped_column(Integer)
    version_no: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    engine_version: Mapped[str] = mapped_column(String(20))
    inputs: Mapped[dict] = mapped_column(JSON)
    inputs_hash: Mapped[str] = mapped_column(String(64))
    summary: Mapped[dict] = mapped_column(JSON)
    created_by: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    approved_by: Mapped[Optional[int]] = mapped_column(Integer)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class LiabilitySchedule(Base):
    __tablename__ = "liability_schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    calc_run_id: Mapped[int] = mapped_column(ForeignKey("calc_runs.id", ondelete="CASCADE"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date, index=True)
    opening = mapped_column(DecimalText)
    additions = mapped_column(DecimalText)
    interest = mapped_column(DecimalText)
    payments = mapped_column(DecimalText)
    remeasurement = mapped_column(DecimalText)
    modification = mapped_column(DecimalText)
    derecognised = mapped_column(DecimalText)
    closing = mapped_column(DecimalText)
    current = mapped_column(DecimalText)
    non_current = mapped_column(DecimalText)


class RouSchedule(Base):
    __tablename__ = "rou_schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    calc_run_id: Mapped[int] = mapped_column(ForeignKey("calc_runs.id", ondelete="CASCADE"), index=True)
    period_end: Mapped[date] = mapped_column(Date, index=True)
    opening = mapped_column(DecimalText)
    additions = mapped_column(DecimalText)
    depreciation = mapped_column(DecimalText)
    impairment = mapped_column(DecimalText)
    remeasurement = mapped_column(DecimalText)
    modification = mapped_column(DecimalText)
    derecognised = mapped_column(DecimalText)
    closing = mapped_column(DecimalText)
    cost_close = mapped_column(DecimalText)
    accdep_close = mapped_column(DecimalText)
    accimp_close = mapped_column(DecimalText)


class PeriodBalance(Base):
    """Other per-period balances: P&L items, cash, provision, deposit, maturity, explainability detail."""
    __tablename__ = "period_balances"
    id: Mapped[int] = mapped_column(primary_key=True)
    calc_run_id: Mapped[int] = mapped_column(ForeignKey("calc_runs.id", ondelete="CASCADE"), index=True)
    period_end: Mapped[date] = mapped_column(Date, index=True)
    data: Mapped[dict] = mapped_column(JSON)


# --------------------------------------------------------------------------- journals & GL
class GLAccount(Base):
    __tablename__ = "gl_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(200))
    nature: Mapped[Optional[str]] = mapped_column(String(40))
    __table_args__ = (UniqueConstraint("company_id", "code"),)


class GLMapping(Base):
    __tablename__ = "gl_mappings"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    role: Mapped[str] = mapped_column(String(40), index=True)
    account_code: Mapped[str] = mapped_column(String(30))
    account_name: Mapped[Optional[str]] = mapped_column(String(200))
    entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entities.id"))
    asset_class_id: Mapped[Optional[int]] = mapped_column(ForeignKey("asset_classes.id"))
    cost_centre: Mapped[Optional[str]] = mapped_column(String(80))
    lease_type: Mapped[Optional[str]] = mapped_column(String(20))


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"))
    lease_id: Mapped[int] = mapped_column(ForeignKey("leases.id"), index=True)
    calc_run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("calc_runs.id"))
    je_number: Mapped[str] = mapped_column(String(40))
    je_date: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date, index=True)
    event: Mapped[str] = mapped_column(String(30))
    narration: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(15), default="Posted")
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    reference: Mapped[Optional[str]] = mapped_column(String(80))
    posted_by: Mapped[Optional[int]] = mapped_column(Integer)
    posted_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    lines: Mapped[list["JournalLine"]] = relationship(cascade="all, delete-orphan", order_by="JournalLine.line_no")


class JournalLine(Base):
    __tablename__ = "journal_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    journal_entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id", ondelete="CASCADE"), index=True)
    line_no: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(40))
    account_code: Mapped[str] = mapped_column(String(30))
    account_name: Mapped[str] = mapped_column(String(200))
    debit = mapped_column(DecimalText)
    credit = mapped_column(DecimalText)
    cost_centre: Mapped[Optional[str]] = mapped_column(String(80))


class GLBalance(Base):
    __tablename__ = "gl_balances"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entities.id"))
    account_code: Mapped[str] = mapped_column(String(30))
    as_of: Mapped[date] = mapped_column(Date)
    balance = mapped_column(DecimalText)            # debit positive
    lease_code: Mapped[Optional[str]] = mapped_column(String(30))
    source: Mapped[Optional[str]] = mapped_column(String(120))


class ReportingPeriod(Base):
    __tablename__ = "reporting_periods"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    period_end: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), default="Open")      # Open | Locked
    locked_by: Mapped[Optional[int]] = mapped_column(Integer)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    reopened_by: Mapped[Optional[int]] = mapped_column(Integer)
    reopened_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("company_id", "period_end"),)


# --------------------------------------------------------------------------- controls & documents
class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[int] = mapped_column(primary_key=True)
    object_type: Mapped[str] = mapped_column(String(30))
    object_id: Mapped[int] = mapped_column(Integer, index=True)
    action: Mapped[str] = mapped_column(String(20))
    from_status: Mapped[Optional[str]] = mapped_column(String(20))
    to_status: Mapped[Optional[str]] = mapped_column(String(20))
    user_id: Mapped[int] = mapped_column(Integer)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    lease_id: Mapped[Optional[int]] = mapped_column(ForeignKey("leases.id"), index=True)
    event_id: Mapped[Optional[int]] = mapped_column(ForeignKey("lease_events.id"))
    doc_type: Mapped[str] = mapped_column(String(40), default="Lease agreement")
    filename: Mapped[str] = mapped_column(String(260))
    stored_path: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    mime: Mapped[Optional[str]] = mapped_column(String(100))
    pages: Mapped[Optional[int]] = mapped_column(Integer)
    uploaded_by: Mapped[Optional[int]] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    engine: Mapped[str] = mapped_column(String(60))
    model: Mapped[Optional[str]] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="Completed")
    result: Mapped[dict] = mapped_column(JSON)
    confirmed_by: Mapped[Optional[int]] = mapped_column(Integer)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    lease_id: Mapped[Optional[int]] = mapped_column(Integer)


class DisclosureSnapshot(Base):
    __tablename__ = "disclosures"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entities.id"))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    framework: Mapped[str] = mapped_column(String(20))
    content: Mapped[dict] = mapped_column(JSON)
    generated_by: Mapped[Optional[int]] = mapped_column(Integer)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    status: Mapped[str] = mapped_column(String(15), default="Draft")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer)
    username: Mapped[Optional[str]] = mapped_column(String(60))
    action: Mapped[str] = mapped_column(String(40))
    object_type: Mapped[str] = mapped_column(String(30), index=True)
    object_id: Mapped[Optional[str]] = mapped_column(String(40), index=True)
    object_label: Mapped[Optional[str]] = mapped_column(String(80))
    field: Mapped[Optional[str]] = mapped_column(String(60))
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    document_id: Mapped[Optional[int]] = mapped_column(Integer)
    approval_status: Mapped[Optional[str]] = mapped_column(String(20))


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    template: Mapped[str] = mapped_column(String(30))
    filename: Mapped[str] = mapped_column(String(260))
    status: Mapped[str] = mapped_column(String(20), default="Validated")
    uploaded_by: Mapped[Optional[int]] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    rows_valid: Mapped[int] = mapped_column(Integer, default=0)
    rows_error: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    preview: Mapped[list] = mapped_column(JSON, default=list)
    payload: Mapped[list] = mapped_column(JSON, default=list)
    approved_by: Mapped[Optional[int]] = mapped_column(Integer)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    imported_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
