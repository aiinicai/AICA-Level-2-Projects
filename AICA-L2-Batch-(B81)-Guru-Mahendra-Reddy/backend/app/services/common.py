"""Shared helpers for the calculation engine.

Two ideas run through everything here:

1.  **Basis, always.** Every figure the engine returns is wrapped with the
    period it covers, the as-on date, and a one-line description of how it was
    worked out, because SPEC principle 4 says a number without its basis is
    not usable.
2.  **Traceability.** Anything the CFO can click has a `trace` descriptor —
    the query the drill-down endpoint replays to show the entries behind it.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from typing import Any

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.models import Entity

LAKH = 100_000.0
CRORE = 10_000_000.0


# ---------------------------------------------------------------------------
# Money formatting (backend side — used in narrative text and alert messages;
# the frontend has its own matching formatter for display)
# ---------------------------------------------------------------------------
def fmt_inr(amount: float | None, decimals: int = 2) -> str:
    """₹ 4,25,00,000 → '₹ 4.25 Cr'. Indian convention, never 'M' or 'K'."""
    if amount is None:
        return "—"
    sign = "-" if amount < 0 else ""
    a = abs(float(amount))
    if a >= CRORE:
        return f"{sign}₹ {a / CRORE:,.{decimals}f} Cr"
    if a >= LAKH:
        return f"{sign}₹ {a / LAKH:,.{decimals}f} L"
    return f"{sign}₹ {a:,.0f}"


def fmt_date(d: date | None) -> str:
    """DD-Mmm-YY, per the spec's format convention."""
    return d.strftime("%d-%b-%y") if d else "—"


def fmt_pct(v: float | None, decimals: int = 1) -> str:
    return "—" if v is None else f"{v:,.{decimals}f}%"


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------
def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def month_end(d: date) -> date:
    return month_start(d) + relativedelta(months=1) - timedelta(days=1)


def months_back(as_on: date, n: int) -> list[date]:
    """The n month-starts ending with the month of `as_on`, oldest first."""
    base = month_start(as_on)
    return [base - relativedelta(months=i) for i in range(n - 1, -1, -1)]


def week_start(d: date) -> date:
    """Monday of the week containing d."""
    return d - timedelta(days=d.weekday())


def weeks_forward(start: date, n: int) -> list[tuple[date, date]]:
    ws = week_start(start)
    return [(ws + timedelta(weeks=i), ws + timedelta(weeks=i, days=6)) for i in range(n)]


def days_between(a: date, b: date) -> int:
    return (b - a).days


def safe_div(num: float, den: float, default: float | None = None) -> float | None:
    return default if not den else num / den


# ---------------------------------------------------------------------------
# Status colour — SPEC principle 5: colour means one thing only
# ---------------------------------------------------------------------------
class Status:
    RED = "Red"        # act this week
    AMBER = "Amber"    # watch
    GREEN = "Green"    # within tolerance
    GREY = "Grey"      # data incomplete, don't rely on it


def status_from_thresholds(value: float | None, green_at: float, amber_at: float,
                           higher_is_better: bool = True) -> str:
    """Map a value to a colour. Returns Grey when the value is unknown, which
    is a real answer rather than an optimistic default."""
    if value is None:
        return Status.GREY
    if higher_is_better:
        if value >= green_at:
            return Status.GREEN
        return Status.AMBER if value >= amber_at else Status.RED
    if value <= green_at:
        return Status.GREEN
    return Status.AMBER if value <= amber_at else Status.RED


# ---------------------------------------------------------------------------
# The wrapper every figure travels in
# ---------------------------------------------------------------------------
@dataclass
class Figure:
    """A number plus everything needed to defend it."""
    label: str
    value: float | None
    unit: str = "inr"                    # inr | months | days | pct | ratio | score | count
    basis: str = ""                      # "Net burn, 3-month average, normalised"
    as_on: date | None = None
    status: str = Status.GREEN
    sub_line: str | None = None
    trace: dict[str, Any] | None = None  # what the drill-down should query
    confident: bool = True               # False renders the grey staleness dot

    def to_dict(self) -> dict:
        d = asdict(self)
        d["as_on"] = self.as_on.isoformat() if self.as_on else None
        d["display"] = self.display
        return d

    @property
    def display(self) -> str:
        if self.value is None:
            return "—"
        if self.unit == "inr":
            return fmt_inr(self.value)
        if self.unit == "months":
            return f"{self.value:,.1f} months"
        if self.unit == "days":
            return f"{self.value:,.0f} days"
        if self.unit == "pct":
            return fmt_pct(self.value)
        if self.unit == "ratio":
            return f"{self.value:,.2f}x"
        if self.unit in ("score", "count"):
            return f"{self.value:,.0f}"
        return f"{self.value:,.2f}"


def trace(kind: str, **kwargs) -> dict[str, Any]:
    """Descriptor the /api/trace endpoint replays to list the entries behind a
    figure. Keeping it as data means the frontend never builds a query."""
    payload = {"kind": kind}
    payload.update({k: (v.isoformat() if isinstance(v, date) else v)
                    for k, v in kwargs.items() if v is not None})
    return payload


# ---------------------------------------------------------------------------
# Per-request context
# ---------------------------------------------------------------------------
@dataclass
class Ctx:
    """Built once per request. Holds the entity, the as-on date, and the small
    number of figures nearly every service needs."""
    db: Session
    entity: Entity
    as_on: date
    today: date = field(default_factory=date.today)

    # Consolidated view sums the operating entities.
    member_ids: list[int] = field(default_factory=list)

    @property
    def entity_ids(self) -> list[int]:
        return self.member_ids or [self.entity.id]

    @property
    def floor(self) -> float:
        return float(self.entity.min_cash_floor or 0.0)


def build_ctx(db: Session, entity_id: int, as_on: date | None = None,
              today: date | None = None) -> Ctx:
    from app.seed.dataset import AS_ON as SEED_AS_ON, TODAY as SEED_TODAY

    entity = db.get(Entity, entity_id)
    if entity is None:
        raise ValueError(f"Entity {entity_id} not found")

    member_ids: list[int] = []
    if entity.is_consolidated:
        member_ids = [e.id for e in db.query(Entity)
                      .filter(Entity.is_consolidated.is_(False)).all()]

    # The demonstration dataset is anchored to a fixed date so the story stays
    # stable. A live Tally-backed install uses the real clock.
    resolved_today = today or SEED_TODAY
    resolved_as_on = as_on or entity.books_closed_upto or SEED_AS_ON
    return Ctx(db=db, entity=entity, as_on=resolved_as_on,
               today=resolved_today, member_ids=member_ids)
