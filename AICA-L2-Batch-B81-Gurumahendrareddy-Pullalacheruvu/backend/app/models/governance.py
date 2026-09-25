"""Who may see what.

The board gets a curated view, decided by the CFO or an Admin. The governing
rule is written into the design and not negotiable in the UI: **hide detail,
never contradict**. Every headline figure a board member sees is the same
figure the CFO sees. What can be withheld is granularity — names, individual
salaries, account numbers, drill-downs — and where something is withheld the
screen says so. Visible restriction reads as governance; silent omission reads
as concealment, and a board member who discovers the second will never trust
the tool again.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import utcnow


class VisibilityRule:
    """The switches a CFO can set. Keys are stable — they are stored."""

    CLIENT_NAMES = "client_names"
    VENDOR_NAMES = "vendor_names"
    INDIVIDUAL_SALARIES = "individual_salaries"
    BANK_ACCOUNT_NUMBERS = "bank_account_numbers"
    DRILLDOWNS = "drilldowns"
    UNTABLED_PLANS = "untabled_plans"
    COVENANT_HEADROOM = "covenant_headroom"
    ALERT_ROUTING = "alert_routing"
    ACTIVITY_LOG = "activity_log"
    MANUAL_REGISTER = "manual_register"
    SCENARIOS = "scenarios"

    # key, label, what it does, default_visible, what stays visible regardless
    CATALOGUE: list[tuple[str, str, str, bool, str]] = [
        (CLIENT_NAMES, "Client names",
         "Show which customer each receivable belongs to.", False,
         "Totals, ageing, concentration % and the largest-client exposure are "
         "always shown — only the name becomes 'Client A'."),
        (VENDOR_NAMES, "Vendor names",
         "Show which vendor each payable belongs to.", False,
         "Amounts, due dates and deferability are always shown."),
        (INDIVIDUAL_SALARIES, "Individual salaries",
         "Show per-person cost in the people and payroll views.", False,
         "Headcount, total payroll and cost per function are always shown."),
        (BANK_ACCOUNT_NUMBERS, "Bank account numbers",
         "Show full account numbers on the cash screens.", False,
         "Bank name, balance and any restriction are always shown."),
        (DRILLDOWNS, "Drill-down to entries",
         "Let the board click a figure through to the underlying entries.", False,
         "Every figure still carries its basis and as-on date."),
        (UNTABLED_PLANS, "Plans not yet tabled",
         "Show variance against plan versions the board has not seen.", False,
         "Variance against the last board-approved plan is always shown."),
        (COVENANT_HEADROOM, "Covenant headroom",
         "Show the computed headroom against each covenant test.", True,
         "Covenant status — pass, watch, breach — is always shown."),
        (ALERT_ROUTING, "Alert routing",
         "Show recipients, escalation paths and quiet hours.", False,
         "The alerts themselves, and whether anyone acted, are always shown."),
        (ACTIVITY_LOG, "Activity log",
         "Show who changed what and when.", False, ""),
        (MANUAL_REGISTER, "Manual entries register",
         "Show which figures are maintained by hand and by whom.", True,
         "Manually-sourced figures are flagged on screen either way."),
        (SCENARIOS, "Scenario levers",
         "Let the board move the levers and see the result.", True,
         "Nothing is saved — the board role cannot write."),
    ]

    LABELS = {k: label for k, label, *_ in CATALOGUE}
    DEFAULTS = {k: default for k, _, _, default, _ in CATALOGUE}


class BoardVisibility(Base):
    """One row per rule per entity. Absent row = the catalogue default."""

    __tablename__ = "board_visibility"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"), nullable=True)
    rule_key: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    set_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    set_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Pseudonym(Base):
    """A stable stand-in name, so masking is consistent across screens.

    "Client A" must be the same company on Money Coming In, in the board pack
    and in an alert. A hash would be consistent but unreadable; a per-screen
    sequence would be readable but contradictory. So the label is allocated
    once and stored.
    """

    __tablename__ = "pseudonyms"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(24), index=True, nullable=False)   # client|vendor|person
    real_name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(60), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
