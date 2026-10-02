"""SQLAlchemy 2.x models (brief §8). Schema is kept PostgreSQL-compatible:
no SQLite-only types; JSON columns use the generic JSON type."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text,
                        UniqueConstraint, create_engine, event)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, scoped_session, sessionmaker


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Database:
    engine = None
    session: scoped_session = None  # type: ignore[assignment]

    def init(self, url: str):
        kw: dict[str, Any] = {"future": True}
        if url.startswith("sqlite"):
            kw["connect_args"] = {"check_same_thread": False, "timeout": 30}
        self.engine = create_engine(url, **kw)
        if url.startswith("sqlite"):
            @event.listens_for(self.engine, "connect")
            def _pragmas(dbapi_conn, _):
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.execute("PRAGMA journal_mode=WAL")
                cur.execute("PRAGMA busy_timeout=30000")
                cur.close()
        self.session = scoped_session(sessionmaker(bind=self.engine, expire_on_commit=False))
        return self


db = Database()

ROLES = ["VIEWER", "PREPARER", "MANAGER", "PARTNER", "OWNER"]
STATUSES = ["NOT_STARTED", "IN_PROGRESS", "READY_FOR_REVIEW", "APPROVED_FOR_FILING", "FILED",
            "ROC_APPROVED", "RESUBMISSION_REQUIRED", "NOT_APPLICABLE", "WAIVED"]
CLOSED = {"FILED", "ROC_APPROVED", "NOT_APPLICABLE", "WAIVED"}


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(255))
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active_flag: Mapped[bool] = mapped_column("is_active", Boolean, default=True)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime)
    totp_secret_enc: Mapped[str | None] = mapped_column(String(255))
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Flask-Login protocol: the "id" in the cookie is the server-side session token
    session_token = None   # plain attribute, not a column

    @property
    def is_active(self) -> bool:
        return self.is_active_flag

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str | None:
        return self.session_token


class UserSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    mfa_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    user: Mapped[User] = relationship()


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    username: Mapped[str] = mapped_column(String(64))
    success: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(String(120))
    ip: Mapped[str | None] = mapped_column(String(64))


class Entity(Base):
    __tablename__ = "entities"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    entity_type: Mapped[str] = mapped_column(String(20))
    cin: Mapped[str | None] = mapped_column(String(21), unique=True)
    pan_enc: Mapped[str | None] = mapped_column(String(255))
    incorporation_date: Mapped[date] = mapped_column(Date)
    roc: Mapped[str | None] = mapped_column(String(60))
    registered_office: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(String(200))
    nominal_capital: Mapped[float] = mapped_column(Float, default=0)
    paid_up_capital: Mapped[float] = mapped_column(Float, default=0)
    llp_contribution: Mapped[float] = mapped_column(Float, default=0)
    has_share_capital: Mapped[bool] = mapped_column(Boolean, default=True)
    holding_of: Mapped[str | None] = mapped_column(String(200))
    subsidiary_of: Mapped[str | None] = mapped_column(String(200))
    is_holding: Mapped[bool] = mapped_column(Boolean, default=False)
    is_subsidiary: Mapped[bool] = mapped_column(Boolean, default=False)
    subsidiary_of_public: Mapped[bool] = mapped_column(Boolean, default=False)
    nbfc: Mapped[bool] = mapped_column(Boolean, default=False)
    hfc: Mapped[bool] = mapped_column(Boolean, default=False)
    banking: Mapped[bool] = mapped_column(Boolean, default=False)
    excluded_sector: Mapped[bool] = mapped_column(Boolean, default=False)
    government: Mapped[bool] = mapped_column(Boolean, default=False)
    special_act: Mapped[bool] = mapped_column(Boolean, default=False)
    listed_subsidiary: Mapped[bool] = mapped_column(Boolean, default=False)
    startup: Mapped[bool] = mapped_column(Boolean, default=False)
    single_director: Mapped[bool] = mapped_column(Boolean, default=False)
    ro_furnished_at_incorporation: Mapped[bool] = mapped_column(Boolean, default=True)
    llp_elect_longer_first_fy: Mapped[bool] = mapped_column(Boolean, default=False)
    ccfs_excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    rm_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    preparer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    engagement_start: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    rm: Mapped[User | None] = relationship(foreign_keys=[rm_id])
    preparer: Mapped[User | None] = relationship(foreign_keys=[preparer_id])


class Person(Base):
    __tablename__ = "persons"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    din: Mapped[str] = mapped_column(String(8), unique=True)
    din_allotment_date: Mapped[date] = mapped_column(Date)
    pan_enc: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(200))
    mobile: Mapped[str | None] = mapped_column(String(20))
    dsc_expiry: Mapped[date | None] = mapped_column(Date)
    din_status: Mapped[str] = mapped_column(String(20), default="APPROVED")
    last_annual_kyc_fy: Mapped[str | None] = mapped_column(String(12))
    kyc_override_first_due: Mapped[date | None] = mapped_column(Date)
    links: Mapped[list["EntityPerson"]] = relationship(back_populates="person")


class EntityPerson(Base):
    __tablename__ = "entity_persons"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"))
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"))
    designation: Mapped[str] = mapped_column(String(60), default="Director")
    appointed_on: Mapped[date | None] = mapped_column(Date)
    ceased_on: Mapped[date | None] = mapped_column(Date)
    entity: Mapped[Entity] = relationship()
    person: Mapped[Person] = relationship(back_populates="links")


class AnnualFacts(Base):
    __tablename__ = "annual_facts"
    __table_args__ = (UniqueConstraint("entity_id", "fy_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"))
    fy_key: Mapped[str] = mapped_column(String(12))
    paid_up_capital: Mapped[float | None] = mapped_column(Float)
    turnover: Mapped[float | None] = mapped_column(Float)
    net_worth: Mapped[float | None] = mapped_column(Float)
    net_profit: Mapped[float | None] = mapped_column(Float)
    bank_borrowings_at_fy_end: Mapped[float | None] = mapped_column(Float)
    bank_borrowings_max: Mapped[float | None] = mapped_column(Float)
    deposits_max: Mapped[float | None] = mapped_column(Float)
    deposits_outstanding_31mar: Mapped[bool | None] = mapped_column(Boolean)
    has_subs_assoc_jv: Mapped[bool | None] = mapped_column(Boolean)
    ind_as: Mapped[bool | None] = mapped_column(Boolean)
    cost_audit_applicable: Mapped[bool | None] = mapped_column(Boolean)
    csr_override: Mapped[bool | None] = mapped_column(Boolean)
    agm_date: Mapped[date | None] = mapped_column(Date)
    board_approval_date: Mapped[date | None] = mapped_column(Date)
    auditor_appointed_at_agm: Mapped[bool | None] = mapped_column(Boolean)
    isin_obtained_date: Mapped[date | None] = mapped_column(Date)
    llp_contribution: Mapped[float | None] = mapped_column(Float)


class PeriodFlag(Base):
    """Per-period yes/no facts that are not tied to the entity's FY row:
    MSME dues > 45 days per half-year, deposits outstanding at a 31 March."""
    __tablename__ = "period_flags"
    __table_args__ = (UniqueConstraint("entity_id", "period_key", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"))
    period_key: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(40))
    value: Mapped[bool] = mapped_column(Boolean)


class ClassificationDecision(Base):
    __tablename__ = "classification_decisions"
    __table_args__ = (UniqueConstraint("entity_id", "key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"))
    key: Mapped[str] = mapped_column(String(40))
    value: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text)
    decided_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"))
    person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id"))
    type: Mapped[str] = mapped_column(String(40))
    event_date: Mapped[date] = mapped_column(Date)
    reference: Mapped[str | None] = mapped_column(String(200))
    attrs: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Obligation(Base):
    __tablename__ = "obligations"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(160), unique=True)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"), index=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id"), index=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"))
    rule_code: Mapped[str] = mapped_column(String(40))
    period_key: Mapped[str] = mapped_column(String(40))
    form: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(200))
    law: Mapped[str] = mapped_column(Text, default="")
    fee_regime: Mapped[str] = mapped_column(String(20), default="NONE")
    anchor_type: Mapped[str] = mapped_column(String(30))
    anchor_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    provisional: Mapped[bool] = mapped_column(Boolean, default=False)
    facts_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_decision: Mapped[str | None] = mapped_column(String(40))
    pre_engagement: Mapped[bool] = mapped_column(Boolean, default=False)
    agm_not_held: Mapped[bool] = mapped_column(Boolean, default=False)
    interpretation: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="NOT_STARTED", index=True)
    status_reason: Mapped[str | None] = mapped_column(Text)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    ready_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    rule_version: Mapped[str] = mapped_column(String(40))
    rule_hash: Mapped[str] = mapped_column(String(64))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime)
    superseded_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    entity: Mapped[Entity | None] = relationship()
    person: Mapped[Person | None] = relationship()
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id])
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewer_id])


class Filing(Base):
    __tablename__ = "filings"
    id: Mapped[int] = mapped_column(primary_key=True)
    obligation_id: Mapped[int] = mapped_column(ForeignKey("obligations.id"))
    srn: Mapped[str] = mapped_column(String(40))
    filing_date: Mapped[date] = mapped_column(Date)
    normal_fee_paid: Mapped[float] = mapped_column(Float, default=0)
    additional_fee_paid: Mapped[float] = mapped_column(Float, default=0)
    delay_days: Mapped[int] = mapped_column(Integer, default=0)
    computed_fee_json: Mapped[dict] = mapped_column(JSON, default=dict)
    fee_mismatch: Mapped[bool] = mapped_column(Boolean, default=False)
    attachment_path: Mapped[str | None] = mapped_column(String(120))
    attachment_name: Mapped[str | None] = mapped_column(String(200))
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    obligation: Mapped[Obligation] = relationship()


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    obligation_id: Mapped[int | None] = mapped_column(ForeignKey("obligations.id"))
    kind: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    __table_args__ = (UniqueConstraint("user_id", "obligation_id", "kind"),)


class RuleVersion(Base):
    __tablename__ = "rule_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(40), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict] = mapped_column(JSON)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    published_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class RuleVerification(Base):
    __tablename__ = "rule_verifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    rule_code: Mapped[str] = mapped_column(String(40))
    rule_hash: Mapped[str] = mapped_column(String(64))
    verified_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    note: Mapped[str | None] = mapped_column(Text)
    verified_by: Mapped[User] = relationship()


class RegulatoryUpdate(Base):
    __tablename__ = "regulatory_updates"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(80))
    issued_on: Mapped[date] = mapped_column(Date)
    url: Mapped[str | None] = mapped_column(String(400))
    summary: Mapped[str] = mapped_column(Text)
    linked_rules: Mapped[list] = mapped_column(JSON, default=list)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)


class AuditLog(Base):
    """Append-only (DB triggers) and hash-chained. See app/audit.py."""
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[str] = mapped_column(String(32))            # ISO-8601 UTC, text so the hash is stable
    actor_id: Mapped[int | None] = mapped_column(Integer)
    actor_name: Mapped[str] = mapped_column(String(120))
    actor_role: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(40), index=True)
    object_type: Mapped[str] = mapped_column(String(40))
    object_id: Mapped[str | None] = mapped_column(String(160))
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True)
    before_json: Mapped[str | None] = mapped_column(Text)
    after_json: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    prev_hash: Mapped[str] = mapped_column(String(64))
    row_hash: Mapped[str] = mapped_column(String(64))


class Document(Base):
    """Entity documents (brief §7 entity page). Stored under instance/uploads with random names."""
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    original_name: Mapped[str] = mapped_column(String(200))
    stored_name: Mapped[str] = mapped_column(String(80))
    size: Mapped[int] = mapped_column(Integer)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    uploaded_by: Mapped[User] = relationship()


class AuditChainLock(Base):
    """Single-row table updated before each audit insert: takes the SQLite write
    lock so two transactions can never read the same prev_hash."""
    __tablename__ = "audit_chain_lock"
    id: Mapped[int] = mapped_column(primary_key=True)
    n: Mapped[int] = mapped_column(Integer, default=0)
