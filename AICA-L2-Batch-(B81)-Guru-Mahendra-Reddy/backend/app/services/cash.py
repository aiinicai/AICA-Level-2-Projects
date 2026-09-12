"""Cash position, availability, and the books-vs-bank confidence check.

The confidence check is the reason the banner exists: if books and bank
disagree by more than the tolerance, every headline number on every tab is
marked indicative rather than quietly presented as fact.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func

from app.models import BankAccount, BankBalanceHistory, Facility, LedgerEntry
from app.services.common import (
    Ctx, Figure, Status, fmt_inr, months_back, month_end, safe_div, trace,
)


def bank_accounts(ctx: Ctx) -> list[BankAccount]:
    return (ctx.db.query(BankAccount)
            .filter(BankAccount.entity_id.in_(ctx.entity_ids))
            .order_by(BankAccount.sort_order, BankAccount.id).all())


def position(ctx: Ctx) -> dict:
    """The three availability tiles plus the books/bank reconciliation."""
    accounts = bank_accounts(ctx)
    total = sum(a.balance for a in accounts)
    restricted = sum(a.balance for a in accounts if a.is_restricted)
    available = total - restricted
    books = sum(a.books_balance for a in accounts)

    undrawn = (ctx.db.query(func.sum(Facility.sanctioned - Facility.drawn))
               .filter(Facility.entity_id.in_(ctx.entity_ids),
                       Facility.is_active.is_(True)).scalar() or 0.0)

    diff = books - total
    diff_pct = abs(safe_div(diff, total, 0.0) or 0.0) * 100

    from app.config import settings
    if abs(diff) <= settings.BOOKS_BANK_AMBER:
        diff_status = Status.GREEN
    elif abs(diff) <= settings.BOOKS_BANK_RED:
        diff_status = Status.AMBER
    else:
        diff_status = Status.RED

    # Bank concentration (SPEC 3A)
    by_bank: dict[str, float] = {}
    for a in accounts:
        by_bank[a.institution] = by_bank.get(a.institution, 0.0) + a.balance
    top_bank, top_amt = max(by_bank.items(), key=lambda kv: kv[1]) if by_bank else ("—", 0.0)
    conc = (safe_div(top_amt, total, 0.0) or 0.0) * 100

    return {
        "total": total,
        "available": available,
        "restricted": restricted,
        "undrawn_credit": undrawn,
        "books_position": books,
        "bank_position": total,
        "difference": diff,
        "difference_pct": round(diff_pct, 2),
        "difference_status": diff_status,
        "concentration": {
            "top_institution": top_bank,
            "amount": top_amt,
            "pct": round(conc, 1),
            "threshold_pct": round(settings.BANK_CONCENTRATION_THRESHOLD * 100, 0),
            "flagged": conc > settings.BANK_CONCENTRATION_THRESHOLD * 100,
            "note": (f"{conc:.0f}% of cash sits with {top_bank}."
                     if by_bank else "No bank accounts on record."),
        },
        "as_on": ctx.as_on.isoformat(),
    }


def confidence(ctx: Ctx) -> dict:
    """Drives the amber/grey bar under the top strip, and the grey dot that
    every headline number carries while it is showing. No silent staleness."""
    from app.config import settings
    from app.models import SyncRun

    pos = position(ctx)
    reasons: list[str] = []
    level = "High"

    if pos["difference_status"] == Status.RED:
        level = "Low"
        reasons.append(f"Bank difference {fmt_inr(abs(pos['difference']))} unexplained.")
    elif pos["difference_status"] == Status.AMBER:
        level = "Medium"
        reasons.append(f"Bank difference {fmt_inr(abs(pos['difference']))} unexplained.")

    last_ok = (ctx.db.query(SyncRun)
               .filter(SyncRun.entity_id.in_(ctx.entity_ids), SyncRun.status == "success")
               .order_by(SyncRun.started_at.desc()).first())
    if last_ok is None:
        level = "Low"
        reasons.append("No successful accounting sync on record.")
    else:
        hours = (ctx.entity.last_data_update or last_ok.started_at) and \
                (last_ok.started_at is not None)
        stale_hours = None
        if last_ok.started_at:
            delta = (ctx.today - last_ok.started_at.date()).days * 24
            stale_hours = delta
        if stale_hours is not None and stale_hours > 48:
            level = "Low" if level == "Medium" else level
            reasons.append(f"Accounting data last synced {stale_hours} hours ago.")

    if ctx.entity.books_closed_upto and ctx.entity.books_closed_upto < ctx.as_on:
        level = "Medium" if level == "High" else level
        reasons.append(f"Books are open after {ctx.entity.books_closed_upto:%d-%b-%y}.")

    return {
        "level": level,
        "show_banner": level != "High",
        "reasons": reasons,
        "message": (" ".join(reasons) + " Treat runway figures as indicative."
                    if reasons else "Books and bank agree. Figures are reliable."),
        "books_status": ("Closed for month" if ctx.entity.books_closed_upto
                         and ctx.entity.books_closed_upto >= ctx.as_on else "Open"),
        "last_data_update": (ctx.entity.last_data_update.isoformat()
                             if ctx.entity.last_data_update else None),
    }


def monthly_cash_history(ctx: Ctx, months: int = 12) -> list[dict]:
    """Month-end closing cash for the trend chart."""
    starts = months_back(ctx.as_on, months)
    ends = [month_end(s) for s in starts]
    rows = (ctx.db.query(BankBalanceHistory.as_on,
                         func.sum(BankBalanceHistory.balance),
                         func.sum(BankBalanceHistory.books_balance))
            .filter(BankBalanceHistory.entity_id.in_(ctx.entity_ids),
                    BankBalanceHistory.as_on.in_(ends))
            .group_by(BankBalanceHistory.as_on)
            .order_by(BankBalanceHistory.as_on).all())
    by_date = {r[0]: (r[1], r[2]) for r in rows}
    out = []
    for e in ends:
        bal, books = by_date.get(e, (None, None))
        out.append({"month": e.replace(day=1).isoformat(), "as_on": e.isoformat(),
                    "closing_cash": bal, "books_cash": books, "actual": True})
    return out


def weekly_cash_history(ctx: Ctx, weeks: int = 13) -> list[dict]:
    """Actual weekly closing cash, reconstructed from the ledger. Used for the
    left half of the Tab 1 chart and for forecast-accuracy scoring."""
    from app.services.common import week_start

    end = week_start(ctx.as_on)
    start = end - timedelta(weeks=weeks - 1)

    opening_row = (ctx.db.query(func.sum(BankBalanceHistory.balance))
                   .filter(BankBalanceHistory.entity_id.in_(ctx.entity_ids),
                           BankBalanceHistory.as_on < start)
                   .group_by(BankBalanceHistory.as_on)
                   .order_by(BankBalanceHistory.as_on.desc()).first())
    running = float(opening_row[0]) if opening_row else 0.0

    moves = (ctx.db.query(LedgerEntry.txn_date, func.sum(LedgerEntry.cash_amount))
             .filter(LedgerEntry.entity_id.in_(ctx.entity_ids),
                     LedgerEntry.txn_date >= start, LedgerEntry.txn_date <= ctx.as_on)
             .group_by(LedgerEntry.txn_date).all())
    by_day = {d: float(v or 0.0) for d, v in moves}

    out, cur = [], start
    while cur <= end:
        wk_end = min(cur + timedelta(days=6), ctx.as_on)
        moved = sum(v for d, v in by_day.items() if cur <= d <= wk_end)
        opening = running
        running += moved
        out.append({"week_start": cur.isoformat(), "week_end": wk_end.isoformat(),
                    "opening": round(opening, 2), "net": round(moved, 2),
                    "closing": round(running, 2), "actual": True})
        cur += timedelta(days=7)
    return out


def cash_available_figure(ctx: Ctx) -> Figure:
    pos = position(ctx)
    conf = confidence(ctx)
    return Figure(
        label="Cash Available",
        value=pos["available"],
        unit="inr",
        basis="Unrestricted bank and cash balances only, per the bank position",
        as_on=ctx.as_on,
        status=Status.GREEN if pos["available"] >= ctx.floor else Status.RED,
        sub_line=(f"Restricted {fmt_inr(pos['restricted'])} · "
                  f"Undrawn credit {fmt_inr(pos['undrawn_credit'])}"),
        trace=trace("bank_accounts", entity_id=ctx.entity.id, as_on=ctx.as_on),
        confident=conf["level"] == "High",
    )
