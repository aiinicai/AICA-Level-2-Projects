"""TAB 11 + 12C — alert rules, fired alerts, delivery records."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import Provenance, utcnow


class Severity:
    RED = "Red"        # act this week
    AMBER = "Amber"    # watch
    GREY = "Grey"      # data incomplete
    ALL = [RED, AMBER, GREY]


class RuleCode:
    """The ten rules the CFO asked for, by code."""
    RUNWAY_BELOW = "runway_below_months"
    CASH_BELOW = "cash_below_amount"
    STATUTORY_UNFUNDED = "statutory_unfunded_within_days"
    PAYABLES_EXCEED_RECEIVABLES = "payables_exceed_receivables_due"
    PLAN_VARIANCE = "plan_variance_above_pct"
    CLIENT_CONCENTRATION = "client_above_pct_of_receivables"
    COVENANT_HEADROOM = "covenant_headroom_below_pct"
    BOOKS_BANK_DIFF = "books_bank_difference_above"
    DATA_STALE = "data_not_updated_for_hours"
    CASHOUT_MOVED = "cashout_moved_more_than_days"
    ALL = [RUNWAY_BELOW, CASH_BELOW, STATUTORY_UNFUNDED, PAYABLES_EXCEED_RECEIVABLES,
           PLAN_VARIANCE, CLIENT_CONCENTRATION, COVENANT_HEADROOM, BOOKS_BANK_DIFF,
           DATA_STALE, CASHOUT_MOVED]


class AlertRule(Base, Provenance):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    threshold_unit: Mapped[str] = mapped_column(String(24), default="number", nullable=False)  # months|inr|pct|hours|days
    severity: Mapped[str] = mapped_column(String(12), default=Severity.AMBER, nullable=False)
    channels: Mapped[str] = mapped_column(String(80), default="sms", nullable=False)      # csv
    cooldown_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    quiet_hours_start: Mapped[int] = mapped_column(Integer, default=22, nullable=False)        # IST hour
    quiet_hours_end: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    recipients: Mapped[str] = mapped_column(Text, default="", nullable=False)                  # csv of user ids/phones
    escalate_after_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)      # 0 = never
    escalate_to: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_fired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("alert_rules.id"), index=True, nullable=True)
    rule_code: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(12), default=Severity.AMBER, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_on: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True, nullable=False)
    trigger_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_unit: Mapped[str | None] = mapped_column(String(24), nullable=True)
    amount_at_stake: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    deep_link: Mapped[str | None] = mapped_column(String(200), nullable=True)   # e.g. /money-out?tab=statutory

    # active | acknowledged | snoozed | resolved | muted
    status: Mapped[str] = mapped_column(String(24), default="active", index=True, nullable=False)
    acknowledged_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    acknowledged_on: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    action_taken: Mapped[str | None] = mapped_column(Text, nullable=True)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_on: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    escalated_on: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AlertDelivery(Base):
    __tablename__ = "alert_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), index=True, nullable=False)
    channel: Mapped[str] = mapped_column(String(24), nullable=False)      # sms | email | console
    recipient: Mapped[str] = mapped_column(String(200), nullable=False)
    sent_on: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
