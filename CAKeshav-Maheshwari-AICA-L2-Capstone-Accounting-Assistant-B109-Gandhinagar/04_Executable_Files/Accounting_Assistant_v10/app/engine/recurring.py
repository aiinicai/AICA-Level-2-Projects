"""Recurring entries (rent, salary, AMC, EMI...): a schedule, a due list and one-click vouchers."""
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import RecurringEntry
from .voucher import VLine, Voucher

STEP = {"monthly": 1, "quarterly": 3, "half-yearly": 6, "yearly": 12}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def _d(s: str) -> date:
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def on_day(year: int, month: int, day: int) -> date:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day if day < 31 else last, last))


def first_due(day: int, today: date | None = None) -> str:
    t = today or date.today()
    d = on_day(t.year, t.month, day)
    if d < t:
        y, m = (t.year + (t.month == 12), t.month % 12 + 1)
        d = on_day(y, m, day)
    return d.strftime("%Y%m%d")


def advance(rec: RecurringEntry) -> str:
    cur = _d(rec.next_due)
    m = cur.month - 1 + STEP.get(rec.frequency, 1)
    return on_day(cur.year + m // 12, m % 12 + 1, rec.day).strftime("%Y%m%d")


def due(session: Session, company_id: str, today: date | None = None, ahead_days: int = 0) -> list[RecurringEntry]:
    t = (today or date.today()).toordinal() + ahead_days
    lim = date.fromordinal(t).strftime("%Y%m%d")
    return [r for r in session.scalars(select(RecurringEntry).where(RecurringEntry.company_id == company_id,
                                                                   RecurringEntry.active.is_(True))
                                       .order_by(RecurringEntry.next_due))
            if r.next_due and r.next_due <= lim]


def narration(rec: RecurringEntry, on: str) -> str:
    d = _d(on)
    text = rec.narration or f"{rec.name} for {{month}} {{year}}"
    return text.replace("{month}", MONTHS[d.month - 1]).replace("{mon}", MONTHS[d.month - 1][:3]) \
        .replace("{year}", str(d.year)).replace("{period}", f"{MONTHS[d.month - 1][:3]}-{str(d.year)[2:]}")


def make_voucher(rec: RecurringEntry, on: str | None = None) -> Voucher:
    on = on or rec.next_due
    lines = [VLine(l["ledger"], Decimal(str(l["amount"])), bool(l["dr"]), "other", f"Recurring: {rec.name}", "green")
             for l in rec.lines or []]
    return Voucher(vtype=rec.voucher_type, base_type=rec.base_type, date=on, lines=lines,
                   narration=narration(rec, on))


def from_voucher(company_id: str, name: str, v: Voucher, frequency: str, day: int,
                 today: date | None = None) -> RecurringEntry:
    return RecurringEntry(company_id=company_id, name=name, voucher_type=v.vtype, base_type=v.base_type,
                          lines=[{"ledger": l.ledger, "dr": l.dr, "amount": str(l.amount)} for l in v.lines],
                          narration=v.narration, frequency=frequency, day=day, next_due=first_due(day, today))


def mark_posted(session: Session, rec: RecurringEntry, posted_on: str, amounts: dict[str, Decimal] | None = None):
    """Move to the next due date; 'last + editable': remember the amounts actually posted."""
    rec.last_posted = posted_on
    if amounts:
        rec.lines = [dict(l, amount=str(amounts.get(l["ledger"], Decimal(str(l["amount"]))))) for l in rec.lines]
    rec.next_due = advance(rec)
    session.commit()
