"""Create, change and revoke overrides (hold, defer, re-date, reduce, exclude, flags, recategorise).

Every change is audited. Changing an existing override (for example extending a hold) revokes the
active one and creates a new one, so the full history stays in the ``override`` table.
Approval (setting ``approver_enabled``)
- A new or changed override is stored *pending* and inactive. The forecast keeps using what was
  approved before (for example the current hold) until an Approver approves the change.
- Approve: the pending change becomes active and replaces the earlier one. Reject: it never applies.
- Nobody approves their own change. A newer pending change for the same item and action
  supersedes the older pending one; the person who made it (or an Admin) can withdraw it.
- Revoking / releasing / "back to as imported" applies at once: it returns the item to the ERP
  figures, which need no approval. Every step is audited.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.money import round_money
from app.engine.lots import add_months, build_lots, forecast_lots
from app.models import (ApprovalStatus, BatchStatus, Category, ImportBatch, LineItem, Override, OverrideAction,
                        SourceType)
from app.models.base import utcnow
from app.services.audit import audit
from app.services.settings_service import get_business_settings

INFLOW_ONLY = {OverrideAction.BILL_DISCOUNTED, OverrideAction.RISK_ADJUSTED}


class OverrideError(ValueError):
    pass


def current_item(db: Session, source_type: str, key: str) -> LineItem:
    li = db.scalar(select(LineItem).join(ImportBatch, ImportBatch.id == LineItem.batch_id)
                   .where(ImportBatch.status == BatchStatus.ACCEPTED,
                          LineItem.source_type == SourceType(source_type), LineItem.source_key == key))
    if li is None:
        raise OverrideError(f"{source_type} item '{key}' is not in the current data")
    return li


def active_override(db: Session, source_type: str, key: str, action: str) -> Override | None:
    return db.scalar(select(Override).where(Override.source_type == SourceType(source_type),
                                            Override.source_key == key, Override.action == OverrideAction(action),
                                            Override.is_active))


def _snapshot(o: Override | None) -> dict | None:
    if o is None:
        return None
    return {"id": o.id, "action": o.action.value, "new_date": o.new_date, "target_lot_start": o.target_lot_start,
            "new_amount": o.new_amount, "new_category_id": o.new_category_id, "reason": o.reason}


def is_open_pending(o: Override) -> bool:
    return (not o.is_active and o.approval_status == ApprovalStatus.PENDING and o.revoked_at is None)


def pending_override(db: Session, source_type: str, key: str, action: str) -> Override | None:
    return db.scalar(select(Override).where(Override.source_type == SourceType(source_type),
                                            Override.source_key == key, Override.action == OverrideAction(action),
                                            Override.is_active.is_(False),
                                            Override.approval_status == ApprovalStatus.PENDING,
                                            Override.revoked_at.is_(None)))


def revoke(db: Session, override_id: int, user_id: int | None = None, reason: str = "") -> Override:
    """Revoke an active override, or withdraw a change that is still waiting for approval."""
    o = db.get(Override, override_id)
    if o is None or not (o.is_active or is_open_pending(o)):
        raise OverrideError(f"override {override_id} is not active")
    pending = is_open_pending(o)
    o.is_active, o.revoked_by_id, o.revoked_at = False, user_id, utcnow()
    db.flush()
    audit(db, f"override.{'withdraw' if pending else 'revoke'}.{o.action.value}", "override",
          f"{o.source_type.value}:{o.source_key}", before=_snapshot(o), after={"reason": reason}, user_id=user_id)
    return o


def approve(db: Session, override_id: int, approver_id: int, comment: str = "") -> Override:
    o = db.get(Override, override_id)
    if o is None or not is_open_pending(o):
        raise OverrideError("this change is not waiting for approval")
    if o.created_by_id == approver_id:
        raise OverrideError("you cannot approve your own change")
    old = active_override(db, o.source_type.value, o.source_key, o.action.value)
    if old is not None:
        revoke(db, old.id, approver_id, reason=f"replaced by approved change #{o.id}")
    o.is_active, o.approval_status = True, ApprovalStatus.APPROVED
    o.approved_by_id, o.approved_at = approver_id, utcnow()
    db.flush()
    audit(db, f"override.approve.{o.action.value}", "override", f"{o.source_type.value}:{o.source_key}",
          before=_snapshot(old), after={**(_snapshot(o) or {}), "comment": comment.strip()}, user_id=approver_id)
    return o


def reject(db: Session, override_id: int, approver_id: int, comment: str = "") -> Override:
    o = db.get(Override, override_id)
    if o is None or not is_open_pending(o):
        raise OverrideError("this change is not waiting for approval")
    if o.created_by_id == approver_id:
        raise OverrideError("you cannot decide on your own change; withdraw it instead")
    if not comment.strip():
        raise OverrideError("give a reason for the rejection")
    o.approval_status, o.approved_by_id, o.approved_at = ApprovalStatus.REJECTED, approver_id, utcnow()
    o.reason = (o.reason + " " if o.reason else "") + f"[rejected: {comment.strip()[:300]}]"
    db.flush()
    audit(db, f"override.reject.{o.action.value}", "override", f"{o.source_type.value}:{o.source_key}",
          before=_snapshot(o), after={"comment": comment.strip()}, user_id=approver_id)
    return o


def set_override(db: Session, source_type: str, key: str, action: str, *, new_date: date | None = None,
                 target_lot_start: date | None = None, new_amount=None, new_category_id: int | None = None,
                 reason: str = "", user_id: int | None = None, as_of: date | None = None) -> Override:
    """Validate and store one override; an active one for the same key and action is replaced."""
    act = OverrideAction(action)
    li = current_item(db, source_type, key)
    s = get_business_settings(db)
    amount = None if new_amount is None or new_amount == "" else round_money(new_amount)

    if act in INFLOW_ONLY and li.direction.value != "inflow":
        raise OverrideError(f"{act.value} applies to collections only")
    if act == OverrideAction.HOLD:
        if li.direction.value != "outflow":
            raise OverrideError("only payments can be held")
        if amount is not None and not (0 < amount <= li.amount):
            raise OverrideError(f"hold amount must be more than 0 and at most {li.amount:,.3f}")
        if new_date is not None and new_date <= li.planned_date:
            raise OverrideError("the next honouring date must be after the cheque date "
                                f"({li.planned_date:%d-%b-%Y})")
    if act == OverrideAction.REDUCE:
        if amount is None or amount < 0 or amount > li.amount:
            raise OverrideError(f"reduced amount must be between 0 and {li.amount:,.3f}")
    if act == OverrideAction.REDATE and new_date is None:
        raise OverrideError("a new date is required")
    if act == OverrideAction.DEFER:
        if as_of is None:
            from app.engine.loader import resolve_as_of
            as_of = resolve_as_of(db)
        starts = [lt.start for lt in forecast_lots(build_lots(as_of, s))]
        if target_lot_start not in starts:
            raise OverrideError("choose one of the forecast lots: " + ", ".join(f"{d:%d-%b}" for d in starts))
    if act == OverrideAction.RECATEGORISE:
        cat = db.get(Category, new_category_id) if new_category_id else None
        if cat is None or cat.direction != li.direction:
            raise OverrideError(f"choose an active {li.direction.value} category")

    old = active_override(db, source_type, key, action)
    earlier = pending_override(db, source_type, key, action)
    if earlier is not None:                       # a newer request supersedes the one still waiting
        revoke(db, earlier.id, user_id, reason="superseded by a newer change")
    if s.approver_enabled:                        # waits for approval; the approved one stays in force
        o = Override(source_type=SourceType(source_type), source_key=key, action=act, new_date=new_date,
                     target_lot_start=target_lot_start, new_amount=amount, new_category_id=new_category_id,
                     reason=reason.strip(), created_by_id=user_id, is_active=False,
                     approval_status=ApprovalStatus.PENDING)
    else:
        if old is not None:
            revoke(db, old.id, user_id, reason="replaced")
        o = Override(source_type=SourceType(source_type), source_key=key, action=act, new_date=new_date,
                     target_lot_start=target_lot_start, new_amount=amount, new_category_id=new_category_id,
                     reason=reason.strip(), created_by_id=user_id, approval_status=ApprovalStatus.NOT_REQUIRED)
    db.add(o)
    db.flush()
    verb = "request" if s.approver_enabled else ("change" if old else "add")
    audit(db, f"override.{verb}.{act.value}", "override", f"{source_type}:{key}",
          before=_snapshot(old), after=_snapshot(o), user_id=user_id)
    return o


# ------------------------------------------------------------------ cheque holds
def hold_cheque(db: Session, key: str, *, honour_date: date | None, amount=None, reason: str = "",
                open_ended: bool = False, user_id: int | None = None) -> Override:
    """Put a vendor PDC on hold until ``honour_date`` (or open-ended). Calling it again extends / changes it."""
    if honour_date is None and not open_ended:
        raise OverrideError("enter the next honouring date, or tick open-ended")
    return set_override(db, "vendor_pdc", key, "hold", new_date=None if open_ended else honour_date,
                        new_amount=amount, reason=reason, user_id=user_id)


def release_hold(db: Session, key: str, user_id: int | None = None, reason: str = "released") -> Override:
    """Release the hold now (and withdraw any hold change still waiting for approval)."""
    found = [o for o in (active_override(db, "vendor_pdc", key, "hold"), pending_override(db, "vendor_pdc", key, "hold"))
             if o is not None]
    if not found:
        raise OverrideError(f"cheque '{key}' is not on hold")
    return [revoke(db, o.id, user_id, reason) for o in found][0]


@dataclass
class HonourSuggestions:
    default: date          # cheque date + hold_default_days
    plus_10: date
    next_lot: date | None
    next_month: date


def suggest_honour_dates(db: Session, cheque_date: date, as_of: date) -> HonourSuggestions:
    s = get_business_settings(db)
    base = max(cheque_date, as_of)
    lots = forecast_lots(build_lots(as_of, s))
    nxt = next((lt.start for lt in lots if lt.start > base), None)
    return HonourSuggestions(cheque_date + timedelta(days=s.hold_default_days), base + timedelta(days=10), nxt,
                             add_months(base, 1))


def to_decimal_or_none(v) -> Decimal | None:
    return None if v in (None, "") else round_money(v)
