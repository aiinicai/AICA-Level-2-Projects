"""TAB 11 — Alerts, and the rule administration behind 12C."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import get_current_user, require_write
from app.models import Alert, AlertDelivery, AlertRule, RuleCode, Severity, User
from app.routers.deps import get_ctx, log
from app.services import alertengine
from app.services.common import Ctx

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _alert_dict(ctx: Ctx, a: Alert, deliveries: list[AlertDelivery]) -> dict:
    d = [x for x in deliveries if x.alert_id == a.id]
    ack_hours = None
    if a.acknowledged_on:
        ack_hours = round((a.acknowledged_on - a.triggered_on).total_seconds() / 3600, 1)
    return {
        "id": a.id, "rule_code": a.rule_code, "severity": a.severity,
        "title": a.title, "message": a.message,
        "triggered_on": a.triggered_on.isoformat(),
        "trigger_value": a.trigger_value, "threshold_value": a.threshold_value,
        "value_unit": a.value_unit, "amount_at_stake": a.amount_at_stake,
        "deep_link": a.deep_link, "status": a.status,
        "acknowledged_by": a.acknowledged_by,
        "acknowledged_on": a.acknowledged_on.isoformat() if a.acknowledged_on else None,
        "hours_to_acknowledge": ack_hours,
        "action_taken": a.action_taken,
        "snoozed_until": a.snoozed_until.isoformat() if a.snoozed_until else None,
        "resolved_on": a.resolved_on.isoformat() if a.resolved_on else None,
        "escalated_on": a.escalated_on.isoformat() if a.escalated_on else None,
        "deliveries": [{
            "channel": x.channel, "recipient": x.recipient,
            "sent_on": x.sent_on.isoformat(), "delivered": x.delivered,
            "read": x.read, "error": x.error,
        } for x in d],
    }


@router.get("")
def list_alerts(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    rows = (ctx.db.query(Alert)
            .filter(Alert.entity_id.in_(ctx.entity_ids))
            .order_by(Alert.triggered_on.desc()).all())
    ids = [a.id for a in rows]
    deliveries = (ctx.db.query(AlertDelivery)
                  .filter(AlertDelivery.alert_id.in_(ids)).all()) if ids else []

    active = [a for a in rows if a.status in ("active", "acknowledged", "snoozed")]
    history = [a for a in rows if a.status in ("resolved", "muted")]
    return {
        "active": [_alert_dict(ctx, a, deliveries) for a in active],
        "history": [_alert_dict(ctx, a, deliveries) for a in history],
        "performance": alertengine.performance(ctx, days=30),
        "severities": Severity.ALL,
    }


class AckIn(BaseModel):
    action_taken: str | None = None


@router.post("/{alert_id}/acknowledge")
def acknowledge(alert_id: int, payload: AckIn, ctx: Ctx = Depends(get_ctx),
                user: User = Depends(require_write)):
    a = ctx.db.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "Alert not found")
    a.status = "acknowledged"
    a.acknowledged_by = user.name
    a.acknowledged_on = datetime.now(timezone.utc).replace(tzinfo=None)
    a.action_taken = payload.action_taken
    log(ctx, user, "acknowledged", "Alert", f"Acknowledged '{a.title}'.", str(a.id))
    ctx.db.commit()
    return {"ok": True}


@router.post("/{alert_id}/resolve")
def resolve(alert_id: int, payload: AckIn, ctx: Ctx = Depends(get_ctx),
            user: User = Depends(require_write)):
    a = ctx.db.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "Alert not found")
    a.status = "resolved"
    a.resolved_on = datetime.now(timezone.utc).replace(tzinfo=None)
    if payload.action_taken:
        a.action_taken = payload.action_taken
    if not a.acknowledged_by:
        a.acknowledged_by = user.name
        a.acknowledged_on = a.resolved_on
    log(ctx, user, "resolved", "Alert", f"Resolved '{a.title}'.", str(a.id))
    ctx.db.commit()
    return {"ok": True}


@router.post("/{alert_id}/snooze")
def snooze(alert_id: int, hours: int = Body(24, embed=True),
           ctx: Ctx = Depends(get_ctx), user: User = Depends(require_write)):
    a = ctx.db.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "Alert not found")
    a.status = "snoozed"
    a.snoozed_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=hours)
    log(ctx, user, "snoozed", "Alert", f"Snoozed '{a.title}' for {hours}h.", str(a.id))
    ctx.db.commit()
    return {"ok": True, "snoozed_until": a.snoozed_until.isoformat()}


@router.post("/run")
def run_rules(dry_run: bool = Query(False), ctx: Ctx = Depends(get_ctx),
              user: User = Depends(require_write)):
    """Evaluate every rule now. `dry_run` shows what would fire without
    recording anything or sending a message."""
    result = alertengine.evaluate_rules(ctx, dry_run=dry_run)
    if not dry_run and result["fired"]:
        log(ctx, user, "ran", "AlertRules",
            f"Ran alert rules — {len(result['fired'])} fired, "
            f"{len(result['suppressed'])} suppressed.")
        ctx.db.commit()
    return result


@router.post("/escalate")
def escalate(ctx: Ctx = Depends(get_ctx), user: User = Depends(require_write)):
    return {"escalated": alertengine.escalate_due(ctx)}


# ---------------------------------------------------------------------------
# Rules (SPEC 12C)
# ---------------------------------------------------------------------------
class RuleIn(BaseModel):
    enabled: bool | None = None
    threshold: float | None = None
    severity: str | None = None
    channels: str | None = None
    cooldown_hours: int | None = Field(None, ge=0, le=720)
    quiet_hours_start: int | None = Field(None, ge=0, le=23)
    quiet_hours_end: int | None = Field(None, ge=0, le=23)
    recipients: str | None = None
    escalate_after_hours: int | None = Field(None, ge=0, le=168)
    escalate_to: str | None = None


@router.get("/rules")
def list_rules(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    rows = (ctx.db.query(AlertRule)
            .filter(AlertRule.entity_id.in_(ctx.entity_ids))
            .order_by(AlertRule.id).all())
    return {
        "rows": [{
            "id": r.id, "code": r.code, "name": r.name, "description": r.description,
            "enabled": r.enabled, "threshold": r.threshold,
            "threshold_unit": r.threshold_unit, "severity": r.severity,
            "channels": r.channels.split(",") if r.channels else [],
            "cooldown_hours": r.cooldown_hours,
            "quiet_hours_start": r.quiet_hours_start,
            "quiet_hours_end": r.quiet_hours_end,
            "recipients": r.recipients,
            "escalate_after_hours": r.escalate_after_hours,
            "escalate_to": r.escalate_to,
            "last_fired_at": r.last_fired_at.isoformat() if r.last_fired_at else None,
            "in_cooldown": alertengine.in_cooldown(r),
            "in_quiet_hours": alertengine.in_quiet_hours(r),
        } for r in rows],
        "codes": RuleCode.ALL,
        "severities": Severity.ALL,
        "channels": ["sms", "email"],
    }


@router.patch("/rules/{rule_id}")
def update_rule(rule_id: int, payload: RuleIn, ctx: Ctx = Depends(get_ctx),
                user: User = Depends(require_write)):
    r = ctx.db.get(AlertRule, rule_id)
    if not r:
        raise HTTPException(404, "Rule not found")
    changes = []
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        before = getattr(r, field)
        if before != value:
            changes.append(f"{field}: {before} → {value}")
            setattr(r, field, value)
    if changes:
        r.updated_by = user.name
        log(ctx, user, "updated", "AlertRule",
            f"Changed '{r.name}' — {'; '.join(changes)}.", str(r.id),
            before=None, after="; ".join(changes))
    ctx.db.commit()
    return {"ok": True, "changes": changes}


@router.post("/rules/test")
def test_delivery(to: str = Body(..., embed=True),
                  channel: str = Body("sms", embed=True),
                  ctx: Ctx = Depends(get_ctx), user: User = Depends(require_write)):
    from app.adapters.notifier import send_test
    result = send_test(ctx, to, channel)
    log(ctx, user, "tested", "AlertRule",
        f"Sent a test {channel} message to {to} — "
        f"{'delivered' if result['delivered'] else 'failed'}.")
    ctx.db.commit()
    return result
