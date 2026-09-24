"""Setup › Data sources — the Tally connection wizard, ledger mapping and
sync status.

Three things this file exists to make honest:

1. **Connecting is the easy half.** The wizard's real work is step 3, where
   every ledger Tally returns is shown with the app's guess beside it and a
   person either confirms or corrects it. A connector that guesses and moves on
   is how the numbers quietly go wrong.

2. **A failed sync must be louder than a successful one.** The dangerous state
   is not "sync failed" — it is "sync failed four days ago and the screen still
   shows numbers".

3. **Tally cannot push.** There is no webhook. A daily sync is this application
   polling at a set time, which only happens if it is running then. That is
   stated in the wizard rather than dressed up as automatic freshness.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func

from app.core.security import get_current_user, require_write
from app.models import (
    Account, BurnCategory, CostNature, Entity, LedgerMapping, SyncRun,
    SyncSchedule, User,
)
from app.routers.deps import get_ctx, log
from app.services.common import Ctx

router = APIRouter(prefix="/api/connect", tags=["setup"])

CLASSIFICATIONS = ["asset", "liability", "income", "expense", "equity"]
SUB_TYPES = ["bank", "cash", "receivable", "payable", "statutory", "loan", "other"]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Step 1 — is Tally reachable
# ---------------------------------------------------------------------------
@router.get("/tally/test")
def test_connection(host: str | None = None, port: int | None = None,
                    user: User = Depends(get_current_user)):
    """Ping Tally and say plainly what to fix when it does not answer."""
    from app.adapters.tally import TallyClient
    from app.config import settings

    client = TallyClient(host=host or settings.TALLY_HOST,
                         port=port or settings.TALLY_PORT)
    result = client.ping()
    result["checklist"] = [
        "Tally Prime is open on this machine or one on the same network.",
        "A company is loaded — Tally answers on the port but returns nothing "
        "when no company is open.",
        "F1 › Advanced Configuration › Enable ODBC/HTTP is set to Yes.",
        f"The port there matches {client.port}.",
        "No firewall rule is blocking that port.",
    ]
    return result


# ---------------------------------------------------------------------------
# Step 2 — which company
# ---------------------------------------------------------------------------
@router.post("/tally/company")
def choose_company(company: str = Body(..., embed=True),
                   ctx: Ctx = Depends(get_ctx), user: User = Depends(require_write)):
    before = ctx.entity.tally_company
    ctx.entity.tally_company = company
    log(ctx, user, "updated", "Entity",
        f"Tally company for {ctx.entity.name} set to '{company}'.",
        before=before, after=company)
    ctx.db.commit()
    return {"company": company}


# ---------------------------------------------------------------------------
# Step 3 — ledger mapping. The part that actually matters.
# ---------------------------------------------------------------------------
@router.post("/tally/scan")
def scan_ledgers(ctx: Ctx = Depends(get_ctx), user: User = Depends(require_write)):
    """Read the chart of accounts and record a guess for every ledger.

    Nothing is applied to the books here. This only populates the mapping table
    so a person can review it before any figure depends on it.
    """
    from app.adapters.normalizer import classify_category, classify_group
    from app.adapters.tally import TallyClient, TallyError, fetch_ledgers

    try:
        ledgers = fetch_ledgers(TallyClient(), ctx.entity.tally_company)
    except TallyError as e:
        raise HTTPException(502, str(e))

    existing = {m.ledger_name: m for m in ctx.db.query(LedgerMapping)
                .filter(LedgerMapping.entity_id == ctx.entity.id).all()}
    new = seen = 0
    for r in ledgers:
        name = r["name"]
        cls, sub, is_cash = classify_group(r.get("parent_group"))
        cat, nature, matched = (None, None, True)
        if cls == "expense":
            cat, nature, matched = classify_category(name, r.get("parent_group"))
        elif sub == "statutory":
            cat, nature = BurnCategory.STATUTORY, CostNature.VARIABLE

        m = existing.get(name)
        if m is None:
            m = LedgerMapping(entity_id=ctx.entity.id, ledger_name=name)
            ctx.db.add(m)
            new += 1
        else:
            seen += 1
        m.parent_group = r.get("parent_group")
        m.external_id = r.get("external_id") or m.external_id
        m.last_seen = _now()
        m.guessed_category = cat
        m.guess_matched = matched
        # A confirmed row is a person's decision — never overwritten by a guess.
        if not m.confirmed:
            m.classification, m.sub_type, m.is_cash = cls, sub, is_cash
            m.burn_category, m.cost_nature = cat, nature

    ctx.db.commit()
    pending = (ctx.db.query(LedgerMapping)
               .filter(LedgerMapping.entity_id == ctx.entity.id,
                       LedgerMapping.confirmed.is_(False),
                       LedgerMapping.ignored.is_(False)).count())
    return {"ledgers_found": len(ledgers), "new": new, "already_known": seen,
            "awaiting_confirmation": pending,
            "message": (f"{len(ledgers)} ledgers read. {pending} still need a person "
                        f"to confirm how they map." if pending
                        else f"{len(ledgers)} ledgers read, all already mapped.")}


@router.get("/tally/mapping")
def get_mapping(only: str = "all", ctx: Ctx = Depends(get_ctx),
                user: User = Depends(get_current_user)):
    """`only`: all | pending | unmatched | confirmed."""
    q = ctx.db.query(LedgerMapping).filter(LedgerMapping.entity_id == ctx.entity.id)
    if only == "pending":
        q = q.filter(LedgerMapping.confirmed.is_(False), LedgerMapping.ignored.is_(False))
    elif only == "unmatched":
        q = q.filter(LedgerMapping.guess_matched.is_(False))
    elif only == "confirmed":
        q = q.filter(LedgerMapping.confirmed.is_(True))

    rows = q.order_by(LedgerMapping.confirmed, LedgerMapping.guess_matched,
                      LedgerMapping.ledger_name).all()
    total = (ctx.db.query(func.count(LedgerMapping.id))
             .filter(LedgerMapping.entity_id == ctx.entity.id).scalar() or 0)
    confirmed = (ctx.db.query(func.count(LedgerMapping.id))
                 .filter(LedgerMapping.entity_id == ctx.entity.id,
                         LedgerMapping.confirmed.is_(True)).scalar() or 0)
    return {
        "total": total,
        "confirmed": confirmed,
        "pending": total - confirmed,
        "choices": {
            "classification": CLASSIFICATIONS,
            "sub_type": SUB_TYPES,
            "burn_category": BurnCategory.ALL if hasattr(BurnCategory, "ALL") else [],
            "cost_nature": [CostNature.FIXED, CostNature.VARIABLE, CostNature.DISCRETIONARY],
        },
        "rows": [{
            "id": m.id, "ledger_name": m.ledger_name, "parent_group": m.parent_group,
            "classification": m.classification, "sub_type": m.sub_type,
            "is_cash": m.is_cash, "burn_category": m.burn_category,
            "cost_nature": m.cost_nature,
            "guess_matched": m.guess_matched, "confirmed": m.confirmed,
            "ignored": m.ignored,
            "confirmed_by": m.confirmed_by,
            "first_seen": m.first_seen.isoformat() if m.first_seen else None,
            "note": m.note,
        } for m in rows],
    }


class MappingUpdate(BaseModel):
    id: int
    classification: str | None = None
    sub_type: str | None = None
    is_cash: bool | None = None
    burn_category: str | None = None
    cost_nature: str | None = None
    ignored: bool | None = None
    note: str | None = None
    confirmed: bool = True


@router.put("/tally/mapping")
def save_mapping(updates: list[MappingUpdate] = Body(...),
                 ctx: Ctx = Depends(get_ctx), user: User = Depends(require_write)):
    n = 0
    for u in updates:
        m = ctx.db.get(LedgerMapping, u.id)
        if not m or m.entity_id != ctx.entity.id:
            continue
        if u.classification is not None:
            if u.classification not in CLASSIFICATIONS:
                raise HTTPException(400, f"'{u.classification}' is not a classification.")
            m.classification = u.classification
        if u.sub_type is not None:
            if u.sub_type not in SUB_TYPES:
                raise HTTPException(400, f"'{u.sub_type}' is not a sub-type.")
            m.sub_type = u.sub_type
            m.is_cash = u.sub_type in ("bank", "cash")
        if u.is_cash is not None:
            m.is_cash = u.is_cash
        if u.burn_category is not None:
            m.burn_category = u.burn_category
        if u.cost_nature is not None:
            m.cost_nature = u.cost_nature
        if u.ignored is not None:
            m.ignored = u.ignored
        if u.note is not None:
            m.note = u.note
        m.confirmed = u.confirmed
        m.confirmed_by = user.name if u.confirmed else None
        m.confirmed_at = _now() if u.confirmed else None

        # Keep any account already created from this ledger in step with the
        # decision, so a correction takes effect without a re-sync.
        acc = (ctx.db.query(Account)
               .filter(Account.entity_id == ctx.entity.id,
                       Account.name == m.ledger_name).first())
        if acc:
            acc.classification = m.classification or acc.classification
            acc.sub_type = m.sub_type or acc.sub_type
            acc.is_cash = m.is_cash
            acc.burn_category = m.burn_category or acc.burn_category
            acc.cost_nature = m.cost_nature or acc.cost_nature
        n += 1

    log(ctx, user, "updated", "LedgerMapping",
        f"Confirmed the mapping for {n} Tally ledger(s).")
    ctx.db.commit()
    pending = (ctx.db.query(LedgerMapping)
               .filter(LedgerMapping.entity_id == ctx.entity.id,
                       LedgerMapping.confirmed.is_(False),
                       LedgerMapping.ignored.is_(False)).count())
    return {"saved": n, "still_pending": pending}


# ---------------------------------------------------------------------------
# Step 4 — schedule, and the caveat that comes with it
# ---------------------------------------------------------------------------
class ScheduleIn(BaseModel):
    enabled: bool = True
    hour: int = 8
    minute: int = 0
    lookback_days: int = 45
    stale_after_hours: int = 36


def _schedule_for(ctx: Ctx) -> SyncSchedule:
    s = (ctx.db.query(SyncSchedule)
         .filter(SyncSchedule.entity_id == ctx.entity.id).first())
    if s is None:
        s = SyncSchedule(entity_id=ctx.entity.id)
        ctx.db.add(s)
        ctx.db.flush()
    return s


@router.get("/schedule")
def get_schedule(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    s = _schedule_for(ctx)
    ctx.db.commit()
    return {
        "enabled": s.enabled, "hour": s.hour, "minute": s.minute,
        "lookback_days": s.lookback_days, "stale_after_hours": s.stale_after_hours,
        "last_attempt": s.last_attempt.isoformat() if s.last_attempt else None,
        "last_success": s.last_success.isoformat() if s.last_success else None,
        "consecutive_failures": s.consecutive_failures,
        "caveat": ("Tally cannot push data. A daily sync means this application "
                   "polls Tally at the time set here, which only happens if it is "
                   "running then. If the machine is off, the sync does not "
                   "silently catch up — the next screen you open will say the "
                   "data is stale."),
    }


@router.put("/schedule")
def set_schedule(body: ScheduleIn, ctx: Ctx = Depends(get_ctx),
                 user: User = Depends(require_write)):
    if not (0 <= body.hour <= 23 and 0 <= body.minute <= 59):
        raise HTTPException(400, "That is not a time of day.")
    s = _schedule_for(ctx)
    s.enabled, s.hour, s.minute = body.enabled, body.hour, body.minute
    s.lookback_days = max(1, body.lookback_days)
    s.stale_after_hours = max(1, body.stale_after_hours)
    s.updated_by = user.name
    log(ctx, user, "updated", "SyncSchedule",
        (f"Daily Tally sync {'on' if body.enabled else 'off'}"
         f"{f' at {body.hour:02d}:{body.minute:02d}' if body.enabled else ''}."))
    ctx.db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Sync status — read on every sign-in
# ---------------------------------------------------------------------------
@router.get("/status")
def sync_status(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    """What the banner after sign-in is built from.

    Severity is deliberately blunt. Stale data that still renders confidently
    is the failure mode this whole screen exists to prevent.
    """
    s = _schedule_for(ctx)
    ctx.db.commit()

    runs = (ctx.db.query(SyncRun)
            .filter(SyncRun.entity_id.in_(ctx.entity_ids))
            .order_by(SyncRun.started_at.desc()).limit(20).all())
    last = runs[0] if runs else None
    last_ok = next((r for r in runs if r.status in ("success", "partial")), None)
    pending = (ctx.db.query(LedgerMapping)
               .filter(LedgerMapping.entity_id == ctx.entity.id,
                       LedgerMapping.confirmed.is_(False),
                       LedgerMapping.ignored.is_(False)).count())

    configured = bool(ctx.entity.tally_company)
    age_h = None
    if last_ok:
        age_h = (_now() - last_ok.started_at).total_seconds() / 3600.0

    if not configured:
        level, headline = "grey", "Tally is not connected. Figures come from what has been entered by hand."
    elif last and last.status == "failed":
        level = "red"
        headline = (f"The last Tally sync failed"
                    f"{f' {_ago(last.started_at)}' if last.started_at else ''}. "
                    f"Figures on every screen are as at the last good sync.")
    elif age_h is None:
        level, headline = "amber", "Tally is configured but has never synced successfully."
    elif age_h > s.stale_after_hours:
        level = "red" if age_h > s.stale_after_hours * 2 else "amber"
        headline = (f"Tally data is {int(age_h)} hours old — older than the "
                    f"{s.stale_after_hours}-hour tolerance set in Setup.")
    elif last and last.status == "partial":
        level = "amber"
        headline = (f"Last sync completed with {pending} ledger(s) still unmapped. "
                    f"Anything they contain is sitting in Other.")
    else:
        level = "green"
        headline = f"Tally data is current — last synced {_ago(last_ok.started_at)}."

    return {
        "level": level,
        "headline": headline,
        "configured": configured,
        "company": ctx.entity.tally_company,
        "schedule": {"enabled": s.enabled, "at": f"{s.hour:02d}:{s.minute:02d}",
                     "stale_after_hours": s.stale_after_hours},
        "last_run": ({"status": last.status, "at": last.started_at.isoformat(),
                      "records": last.records, "message": last.message,
                      "triggered_by": last.triggered_by} if last else None),
        "last_success": last_ok.started_at.isoformat() if last_ok else None,
        "hours_since_success": round(age_h, 1) if age_h is not None else None,
        "unmapped_ledgers": pending,
        "consecutive_failures": s.consecutive_failures,
        "history": [{"status": r.status, "at": r.started_at.isoformat(),
                     "records": r.records, "message": r.message,
                     "triggered_by": r.triggered_by} for r in runs],
    }


def _ago(then: datetime | None) -> str:
    if not then:
        return "never"
    mins = (_now() - then).total_seconds() / 60
    if mins < 90:
        return f"{int(mins)} minutes ago"
    hours = mins / 60
    if hours < 36:
        return f"{int(hours)} hours ago"
    return f"{int(hours / 24)} days ago"
