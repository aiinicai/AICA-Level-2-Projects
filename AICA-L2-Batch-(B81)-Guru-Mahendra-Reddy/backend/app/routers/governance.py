"""Setup › Board visibility — what the board sees, decided by the CFO."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import get_current_user, require_approver
from app.models import BoardVisibility, Pseudonym, Role, User, VisibilityRule
from app.routers.deps import get_ctx, log
from app.services import boardmask
from app.services.common import Ctx

router = APIRouter(prefix="/api/setup/board-visibility", tags=["setup"])


class RuleUpdate(BaseModel):
    rule_key: str
    visible: bool
    note: str | None = None


@router.get("")
def get_visibility(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    """The policy, plus what stays visible no matter what it is set to."""
    policy = boardmask.load_policy(ctx.db, ctx.entity_ids)
    rows = {r.rule_key: r for r in ctx.db.query(BoardVisibility).all()}

    board_count = (ctx.db.query(User)
                   .filter(User.role == Role.BOARD, User.is_active.is_(True)).count())
    masked_names = ctx.db.query(Pseudonym).count()

    return {
        "principle": ("Hide detail, never contradict. Every headline figure the "
                      "board sees is the same figure you see — what these "
                      "switches control is granularity. Wherever something is "
                      "withheld, the board's screen says so."),
        "board_accounts": board_count,
        "pseudonyms_allocated": masked_names,
        "editable": user.role in Role.APPROVERS,
        "rules": [{
            "key": key,
            "label": label,
            "description": desc,
            "visible": policy[key],
            "default": default,
            "always_visible": always,
            "set_by": rows[key].set_by if key in rows else None,
            "set_at": rows[key].set_at.isoformat() if key in rows else None,
            "note": rows[key].note if key in rows else None,
        } for key, label, desc, default, always in VisibilityRule.CATALOGUE],
    }


@router.put("")
def set_visibility(updates: list[RuleUpdate] = Body(...),
                   ctx: Ctx = Depends(get_ctx),
                   user: User = Depends(require_approver)):
    """Only an Admin or the CFO decides what the board sees."""
    known = set(VisibilityRule.DEFAULTS)
    changed = []
    for u in updates:
        if u.rule_key not in known:
            raise HTTPException(400, f"There is no visibility rule called '{u.rule_key}'.")
        row = (ctx.db.query(BoardVisibility)
               .filter(BoardVisibility.rule_key == u.rule_key).first())
        before = row.visible if row else VisibilityRule.DEFAULTS[u.rule_key]
        if row is None:
            row = BoardVisibility(rule_key=u.rule_key)
            ctx.db.add(row)
        row.visible = u.visible
        row.note = u.note
        row.set_by = user.name
        row.set_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if before != u.visible:
            changed.append((VisibilityRule.LABELS[u.rule_key], before, u.visible))

    for label, before, after in changed:
        log(ctx, user, "updated", "BoardVisibility",
            f"Board visibility — {label} turned {'on' if after else 'off'}.",
            object_id=label, before=str(before), after=str(after))
    ctx.db.commit()
    return {"updated": len(changed),
            "message": (f"{len(changed)} change(s) saved. They apply the next time a "
                        f"board member loads a screen." if changed
                        else "Nothing changed.")}


@router.get("/preview")
def preview(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    """What a board member would see on Money Coming In, with today's policy.

    A CFO should not have to sign in as the board to find out what they have
    just published.
    """
    from app.models import Customer, Invoice

    policy = boardmask.load_policy(ctx.db, ctx.entity_ids)
    rows = (ctx.db.query(Customer.name, Invoice.invoice_no, Invoice.outstanding,
                         Invoice.due_date)
            .join(Invoice, Invoice.customer_id == Customer.id)
            .filter(Invoice.entity_id.in_(ctx.entity_ids), Invoice.outstanding > 0)
            .order_by(Invoice.outstanding.desc()).limit(5).all())
    real = {"receivables": [{
        "customer": name, "invoice_no": no, "outstanding": out,
        "due_date": due.isoformat() if due else None,
        "trace": {"kind": "invoice", "invoice_no": no},
    } for name, no, out, due in rows]}

    pseudo = boardmask.Pseudonymiser(ctx.db, ctx.entity.id)
    scrub = boardmask.TextScrubber(
        ctx.db, ctx.entity_ids, pseudo,
        mask_clients=not policy[VisibilityRule.CLIENT_NAMES],
        mask_vendors=not policy[VisibilityRule.VENDOR_NAMES])
    masker = boardmask._Masker(policy, pseudo, scrub)
    shown = masker.walk(real)
    pseudo.commit()
    return {"as_the_board_sees_it": shown,
            "restricted": sorted(masker.restricted),
            "restricted_labels": [VisibilityRule.LABELS.get(r, r)
                                  for r in sorted(masker.restricted)]}
