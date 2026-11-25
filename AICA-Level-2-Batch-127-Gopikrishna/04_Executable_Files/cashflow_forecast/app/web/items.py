"""Item rows with their Action drop-down (hold / defer / re-date / reduce / exclude / flags).

Used by the lot-grid drill-down and the PDC list. Every action goes through services.overrides,
which validates, keeps history and audits.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.forecast import Forecast, ItemOut
from app.engine.lots import add_months
from app.models import ApprovalStatus, Override, SourceType

WAITING = " Waiting for approval: the forecast does not use it until an Approver approves it."
from app.services import overrides as OV

ACTION_LABELS = {
    "hold": "Hold cheque", "defer": "Defer to lot", "redate": "Re-date", "reduce": "Reduce amount",
    "exclude": "Exclude", "risk_adjusted": "Flag risk-adjusted", "bill_discounted": "Flag bill discounted",
}
STATUS_LABELS = {"active": "Active", "excluded": "Excluded", "bill_discounted": "Bill discounted",
                 "risk_excluded": "Risk-adjusted (excluded in this scenario)", "beyond_horizon": "After the horizon",
                 "paid": "Paid", "other_currency": "Not OMR"}
HOLD_REASONS = ["Await delivery note", "Vendor dispute", "Quality issue", "Cash planning", "Await GRN / invoice",
                "Vendor agreed to later date"]


def actions_for(i: ItemOut) -> list[str]:
    acts = ["defer", "redate", "reduce", "exclude"]
    if i.direction == "outflow" and i.source == "vendor_pdc":
        acts.insert(0, "hold")
    if i.direction == "inflow":
        acts += ["risk_adjusted", "bill_discounted"]
    return acts


def active_overrides(db: Session, keys: list[tuple[str, str]] | None = None) -> dict[tuple[str, str], list[Override]]:
    """Active changes plus changes still waiting for approval, per item."""
    waiting = (Override.approval_status == ApprovalStatus.PENDING) & Override.revoked_at.is_(None)
    q = select(Override).where(Override.is_active | waiting).order_by(Override.id)
    out: dict[tuple[str, str], list[Override]] = {}
    want = set(keys) if keys is not None else None
    for o in db.scalars(q):
        k = (o.source_type.value, o.source_key)
        if want is None or k in want:
            out.setdefault(k, []).append(o)
    return out


def suggestions(fc: Forecast, i: ItemOut) -> list[tuple[str, date]]:
    """Quick picks for the next honouring date."""
    base = max(i.eff_date, fc.as_of)
    picks = [(f"+{fc.settings.hold_default_days} days", i.item.planned_date + timedelta(days=fc.settings.hold_default_days))]
    if fc.settings.hold_default_days != 10:
        picks.append(("+10 days", base + timedelta(days=10)))
    nxt = next((lt for lt in fc.fc_lots if lt.start > base), None)
    if nxt:
        picks.append((f"Next lot ({nxt.start:%d-%b})", nxt.start))
        after = next((lt for lt in fc.fc_lots if lt.start > nxt.start), None)
        if after:
            picks.append((f"Lot after ({after.start:%d-%b})", after.start))
    picks.append((f"Next month ({add_months(base, 1):%d-%b})", add_months(base, 1)))
    seen, out = set(), []
    for label, d in picks:
        if d > i.item.planned_date and d not in seen:
            seen.add(d)
            out.append((label, d))
    return out


def find_item(fc: Forecast, source: str, key: str) -> ItemOut | None:
    return next((i for i in fc.items if i.source == source and i.key == key), None)


def _date(v: str) -> date | None:
    return date.fromisoformat(v) if v else None


def apply_action(db: Session, form: dict, user_id: int) -> str:
    """Apply one action from a form. Returns a short confirmation; raises OV.OverrideError."""
    src, key, act = form.get("source", ""), form.get("key", ""), form.get("action", "")
    try:
        SourceType(src)
    except ValueError:
        raise OV.OverrideError("unknown source")
    reason = (form.get("reason") or "").strip()[:500]
    try:
        if act == "hold":
            o = OV.hold_cheque(db, key, honour_date=_date(form.get("new_date", "")), amount=form.get("amount") or None,
                               open_ended=bool(form.get("open_ended")), reason=reason, user_id=user_id)
            waiting = o.approval_status == ApprovalStatus.PENDING
            return (("Hold requested until " if waiting else "Held until ") + (f"{o.new_date:%d-%b-%Y}" if o.new_date else "further notice (open-ended)")
                    + (f", {o.new_amount:,.3f}" if o.new_amount else ", full amount") + "."
                    + (WAITING if waiting else ""))
        if act == "release":
            OV.release_hold(db, key, user_id)
            return "Hold released: the cheque is honoured on its own date."
        if act == "reset":
            n = 0
            for o in active_overrides(db, [(src, key)]).get((src, key), []):
                OV.revoke(db, o.id, user_id, reason or "back to as imported")
                n += 1
            return f"Back to as imported ({n} change(s) revoked)."
        if act == "revoke":
            o = db.get(Override, int(form.get("override_id") or 0))
            if o is None or (o.source_type.value, o.source_key) != (src, key):
                raise OV.OverrideError("change not found")
            OV.revoke(db, o.id, user_id, reason or "revoked")
            return f"{ACTION_LABELS.get(o.action.value, o.action.value)} revoked."
        if act in ("defer", "redate", "reduce", "exclude", "risk_adjusted", "bill_discounted"):
            o = OV.set_override(db, src, key, act, new_date=_date(form.get("new_date", "")),
                                target_lot_start=_date(form.get("lot_start", "")),
                                new_amount=form.get("amount") or None, reason=reason, user_id=user_id)
            if o.approval_status == ApprovalStatus.PENDING:
                return f"{ACTION_LABELS[act]} requested." + WAITING
            return f"{ACTION_LABELS[act]} saved."
    except ValueError as exc:            # bad date / amount text
        if isinstance(exc, OV.OverrideError):
            raise
        raise OV.OverrideError(str(exc))
    raise OV.OverrideError(f"unknown action '{act}'")
