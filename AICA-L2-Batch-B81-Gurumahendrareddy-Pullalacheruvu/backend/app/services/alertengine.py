"""TAB 11 + 12C — the alert engine.

Ten rules, each evaluated against the same calculation engine the screens use,
so an alert can never say something the tab contradicts.

Delivery rules the CFO asked for are enforced here rather than in the sender:
cooldown, quiet hours, recipients, and escalation after N hours without
acknowledgement.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.config import settings
from app.models import Alert, AlertDelivery, AlertRule, RuleCode, Severity, User
from app.services.common import Ctx, fmt_date, fmt_inr, fmt_pct

IST = ZoneInfo("Asia/Kolkata")


# ---------------------------------------------------------------------------
# Rule evaluation — each returns None (not firing) or a dict describing the hit
# ---------------------------------------------------------------------------
def _runway_below(ctx: Ctx, rule: AlertRule) -> dict | None:
    from app.services.runway import runway_summary
    s = runway_summary(ctx)
    m = s["current"]["months"]
    if m is None or m >= rule.threshold:
        return None
    return {
        "title": f"Runway has fallen to {m:.1f} months",
        "message": (f"Runway on the current run-rate is {m:.1f} months against a "
                    f"{rule.threshold:.0f}-month threshold. Cash-out date is "
                    f"{fmt_date_str(s['current']['cashout_date'])}."
                    + (" The fundraise trigger date has already passed."
                       if s["fundraise_trigger_passed"] else "")),
        "value": round(m, 1), "unit": "months", "at_stake": 0.0, "link": "/runway-burn",
    }


def _cash_below(ctx: Ctx, rule: AlertRule) -> dict | None:
    from app.services.cash import position
    avail = position(ctx)["available"]
    if avail >= rule.threshold:
        return None
    return {
        "title": f"Available cash is {fmt_inr(avail)}",
        "message": (f"Freely available cash is {fmt_inr(avail)}, below the "
                    f"{fmt_inr(rule.threshold)} floor set in Setup."),
        "value": avail, "unit": "inr", "at_stake": rule.threshold - avail, "link": "/liquidity",
    }


def _statutory_unfunded(ctx: Ctx, rule: AlertRule) -> dict | None:
    from app.services.payables import statutory
    rows = [r for r in statutory(ctx)["rows"]
            if r["gap"] > 0 and 0 <= r["days_to_due"] <= rule.threshold]
    if not rows:
        return None
    worst = max(rows, key=lambda r: r["gap"])
    total_gap = sum(r["gap"] for r in rows)
    return {
        "title": (f"{worst['head']} of {fmt_inr(worst['amount'])} due "
                  f"{fmt_date_str(worst['due_date'])} is {fmt_inr(worst['gap'])} short"),
        "message": (f"{len(rows)} statutory due(s) inside {rule.threshold:.0f} days have no cash "
                    f"fully earmarked. Total gap {fmt_inr(total_gap)}. Statutory dues are "
                    f"first-charge and carry penal interest."),
        "value": worst["days_to_due"], "unit": "days", "at_stake": total_gap,
        "link": "/money-out?sub=statutory",
    }


def _payables_exceed_receivables(ctx: Ctx, rule: AlertRule) -> dict | None:
    from app.services.payables import obligations
    from app.services.receivables import summary
    due = obligations(ctx, horizon_days=30)["tiles"]["due_next_30d"]
    weighted = summary(ctx)["weighted_next_30d"]
    if not weighted or due / weighted <= rule.threshold:
        return None
    ratio = due / weighted
    return {
        "title": "Payables due exceed weighted collectible",
        "message": (f"{fmt_inr(due)} falls due in the next 30 days against "
                    f"{fmt_inr(weighted)} of weighted collectible — a ratio of {ratio:.2f}x."),
        "value": round(ratio, 2), "unit": "ratio", "at_stake": due - weighted,
        "link": "/money-out",
    }


def _plan_variance(ctx: Ctx, rule: AlertRule) -> dict | None:
    from app.services.variance import plan_vs_actual
    pv = plan_vs_actual(ctx)
    pct = pv["tiles"].get("this_month_variance_pct")
    if pct is None or abs(pct) <= rule.threshold:
        return None
    plan = pv["plan"]
    return {
        "title": f"Cash variance is {abs(pct):.1f}% {'behind' if pct < 0 else 'ahead of'} plan",
        "message": (f"Actual cash for the month differs from "
                    f"{plan['name'] if plan else 'the active plan'} "
                    f"{plan['version'] if plan else ''} by "
                    f"{fmt_inr(pv['tiles']['this_month_variance'])} ({abs(pct):.1f}%)."),
        "value": round(abs(pct), 1), "unit": "pct",
        "at_stake": abs(pv["tiles"]["this_month_variance"] or 0),
        "link": "/plan-vs-actual",
    }


def _client_concentration(ctx: Ctx, rule: AlertRule) -> dict | None:
    from app.services.receivables import concentration
    c = concentration(ctx)
    if not c["top5_receivables"]:
        return None
    top = c["top5_receivables"][0]
    if top["pct"] <= rule.threshold:
        return None
    return {
        "title": f"{top['client']} is {top['pct']:.1f}% of receivables",
        "message": (f"A single client accounts for {top['pct']:.1f}% of total receivables "
                    f"({fmt_inr(top['amount'])}) against a {rule.threshold:.0f}% threshold. "
                    + (c["impact"]["sentence"] if c.get("impact") else "")),
        "value": top["pct"], "unit": "pct", "at_stake": top["amount"], "link": "/money-in",
    }


def _covenant_headroom(ctx: Ctx, rule: AlertRule) -> dict | None:
    from app.services.capital import covenants
    rows = [r for r in covenants(ctx)["rows"]
            if r["headroom_pct"] is not None and r["headroom_pct"] < rule.threshold]
    if not rows:
        return None
    worst = min(rows, key=lambda r: r["headroom_pct"])
    return {
        "title": f"{worst['name']} — headroom down to {worst['headroom_pct']:.1f}%",
        "message": (f"Currently {worst['current_display']} against a required "
                    f"{worst['operator']} {worst['required_display']}. Headroom "
                    f"{worst['headroom_pct']:.1f}%, below the {rule.threshold:.0f}% warning "
                    f"level. Next test {fmt_date_str(worst['test_date'])}."),
        "value": worst["headroom_pct"], "unit": "pct", "at_stake": 0.0,
        "link": "/capital-debt",
    }


def _books_bank(ctx: Ctx, rule: AlertRule) -> dict | None:
    from app.services.cash import position
    p = position(ctx)
    diff = abs(p["difference"])
    if diff <= rule.threshold:
        return None
    return {
        "title": f"Books and bank differ by {fmt_inr(diff)}",
        "message": (f"Unreconciled difference of {fmt_inr(diff)} ({p['difference_pct']:.2f}%) "
                    f"between the books position and the bank position as at "
                    f"{fmt_date(ctx.as_on)}. Runway figures are indicative until this clears."),
        "value": diff, "unit": "inr", "at_stake": diff, "link": "/setup?layer=sources",
    }


def _data_stale(ctx: Ctx, rule: AlertRule) -> dict | None:
    from app.models import SyncRun
    last = (ctx.db.query(SyncRun)
            .filter(SyncRun.entity_id.in_(ctx.entity_ids), SyncRun.status == "success")
            .order_by(SyncRun.started_at.desc()).first())
    if not last:
        hours = 9999.0
    else:
        hours = (datetime.combine(ctx.today, datetime.min.time())
                 - last.started_at.replace(tzinfo=None)).total_seconds() / 3600
    if hours <= rule.threshold:
        return None
    return {
        "title": f"Accounting sync last succeeded {hours:.0f} hours ago",
        "message": (f"No successful sync in {hours:.0f} hours against a "
                    f"{rule.threshold:.0f}-hour threshold. Figures may be stale."),
        "value": round(hours, 0), "unit": "hours", "at_stake": 0.0,
        "link": "/setup?layer=sources",
    }


def _cashout_moved(ctx: Ctx, rule: AlertRule) -> dict | None:
    """Compares the current cash-out date against the one stated in the most
    recent board pack — the last figure that was actually put in writing."""
    from datetime import date as _date
    from app.models import BoardPack
    from app.services.runway import runway_summary

    prior = (ctx.db.query(BoardPack)
             .filter(BoardPack.entity_id.in_(ctx.entity_ids),
                     BoardPack.cashout_stated.isnot(None))
             .order_by(BoardPack.generated_on.desc()).first())
    if not prior:
        return None
    s = runway_summary(ctx)
    if not s["current"]["cashout_date"]:
        return None
    now = _date.fromisoformat(s["current"]["cashout_date"])
    moved = (now - prior.cashout_stated).days
    if abs(moved) <= rule.threshold:
        return None
    return {
        "title": f"Cash-out date moved {abs(moved)} days "
                 f"{'earlier' if moved < 0 else 'later'}",
        "message": (f"Cash-out date moved from {fmt_date(prior.cashout_stated)} (as stated in "
                    f"the pack of {prior.generated_on:%d-%b-%y}) to {fmt_date(now)} — "
                    f"{abs(moved)} days {'earlier' if moved < 0 else 'later'}."),
        "value": abs(moved), "unit": "days", "at_stake": 0.0, "link": "/",
    }


EVALUATORS = {
    RuleCode.RUNWAY_BELOW: _runway_below,
    RuleCode.CASH_BELOW: _cash_below,
    RuleCode.STATUTORY_UNFUNDED: _statutory_unfunded,
    RuleCode.PAYABLES_EXCEED_RECEIVABLES: _payables_exceed_receivables,
    RuleCode.PLAN_VARIANCE: _plan_variance,
    RuleCode.CLIENT_CONCENTRATION: _client_concentration,
    RuleCode.COVENANT_HEADROOM: _covenant_headroom,
    RuleCode.BOOKS_BANK_DIFF: _books_bank,
    RuleCode.DATA_STALE: _data_stale,
    RuleCode.CASHOUT_MOVED: _cashout_moved,
}


def fmt_date_str(iso: str | None) -> str:
    from datetime import date as _date
    return fmt_date(_date.fromisoformat(iso)) if iso else "—"


# ---------------------------------------------------------------------------
# Delivery gates
# ---------------------------------------------------------------------------
def in_quiet_hours(rule: AlertRule, now: datetime | None = None) -> bool:
    now = (now or datetime.now(timezone.utc)).astimezone(IST)
    s, e = rule.quiet_hours_start, rule.quiet_hours_end
    if s == e:
        return False
    if s < e:
        return s <= now.hour < e
    return now.hour >= s or now.hour < e      # window wraps midnight


def in_cooldown(rule: AlertRule, now: datetime | None = None) -> bool:
    if not rule.last_fired_at or not rule.cooldown_hours:
        return False
    now = now or datetime.now(timezone.utc)
    elapsed = (now.replace(tzinfo=None) - rule.last_fired_at.replace(tzinfo=None))
    return elapsed < timedelta(hours=rule.cooldown_hours)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
def evaluate_rules(ctx: Ctx, dry_run: bool = False,
                   ignore_gates: bool = False) -> dict:
    """Evaluate every enabled rule. Returns what fired, what was suppressed and
    why — the 'why' matters as much as the firing."""
    from app.adapters.notifier import send

    now = datetime.now(timezone.utc)
    fired, suppressed = [], []

    rules = (ctx.db.query(AlertRule)
             .filter(AlertRule.entity_id.in_(ctx.entity_ids),
                     AlertRule.enabled.is_(True)).all())

    for rule in rules:
        fn = EVALUATORS.get(rule.code)
        if not fn:
            continue
        try:
            hit = fn(ctx, rule)
        except Exception as e:                       # a broken rule must not
            suppressed.append({"rule": rule.name,    # take the whole run down
                               "reason": f"evaluation failed: {e}"})
            continue
        if not hit:
            continue

        if not ignore_gates and in_cooldown(rule, now):
            suppressed.append({"rule": rule.name, "title": hit["title"],
                               "reason": f"cooldown — last fired "
                                         f"{rule.last_fired_at:%d-%b %H:%M}"})
            continue

        # Don't raise a duplicate of an alert that is already open
        existing = (ctx.db.query(Alert)
                    .filter(Alert.entity_id == ctx.entity.id,
                            Alert.rule_code == rule.code,
                            Alert.status.in_(["active", "acknowledged", "snoozed"]))
                    .first())
        if existing and not ignore_gates:
            suppressed.append({"rule": rule.name, "title": hit["title"],
                               "reason": "an alert for this rule is already open"})
            continue

        if dry_run:
            fired.append({"rule": rule.name, "code": rule.code, **hit, "delivered": False})
            continue

        alert = Alert(entity_id=ctx.entity.id, rule_id=rule.id, rule_code=rule.code,
                      severity=rule.severity, title=hit["title"], message=hit["message"],
                      triggered_on=now.replace(tzinfo=None),
                      trigger_value=hit["value"], threshold_value=rule.threshold,
                      value_unit=hit["unit"], amount_at_stake=hit.get("at_stake", 0.0),
                      deep_link=hit.get("link"), status="active")
        ctx.db.add(alert)
        ctx.db.flush()
        rule.last_fired_at = now.replace(tzinfo=None)

        quiet = in_quiet_hours(rule, now) and not ignore_gates
        deliveries = []
        if quiet:
            suppressed.append({"rule": rule.name, "title": hit["title"],
                               "reason": f"quiet hours {rule.quiet_hours_start:02d}:00–"
                                         f"{rule.quiet_hours_end:02d}:00 IST — the alert is "
                                         f"recorded and will be sent after quiet hours"})
        else:
            deliveries = send(ctx, alert, rule)

        fired.append({"rule": rule.name, "code": rule.code, "alert_id": alert.id,
                      **hit, "delivered": bool(deliveries), "held_for_quiet_hours": quiet,
                      "channels": [d["channel"] for d in deliveries]})

    if not dry_run:
        ctx.db.commit()

    return {"fired": fired, "suppressed": suppressed,
            "evaluated": len(rules),
            "run_at": now.isoformat(),
            "dry_run": dry_run}


def escalate_due(ctx: Ctx) -> list[dict]:
    """Alerts that have gone unacknowledged past their rule's escalation window."""
    from app.adapters.notifier import send

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    out = []
    rows = (ctx.db.query(Alert, AlertRule)
            .join(AlertRule, AlertRule.id == Alert.rule_id)
            .filter(Alert.entity_id.in_(ctx.entity_ids),
                    Alert.status == "active",
                    Alert.escalated_on.is_(None),
                    AlertRule.escalate_after_hours > 0).all())
    for alert, rule in rows:
        age = (now - alert.triggered_on).total_seconds() / 3600
        if age < rule.escalate_after_hours:
            continue
        alert.escalated_on = now
        send(ctx, alert, rule, escalation=True)
        out.append({"alert_id": alert.id, "title": alert.title,
                    "hours_unacknowledged": round(age, 1)})
    ctx.db.commit()
    return out


def performance(ctx: Ctx, days: int = 30) -> dict:
    """SPEC 11 — the honest panel. If most alerts are being ignored, the
    thresholds are wrong and the CFO wants to see that."""
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    rows = (ctx.db.query(Alert)
            .filter(Alert.entity_id.in_(ctx.entity_ids),
                    Alert.triggered_on >= since).all())
    sent = len(rows)
    acted = sum(1 for a in rows if a.action_taken or a.status == "resolved")
    muted = sum(1 for a in rows if a.status == "muted")
    ignored = sum(1 for a in rows if a.status == "active" and not a.acknowledged_by)

    acks = [(a.acknowledged_on - a.triggered_on).total_seconds() / 3600
            for a in rows if a.acknowledged_on]
    return {
        "window_days": days,
        "sent": sent, "acted_on": acted, "ignored": ignored, "muted": muted,
        "acted_pct": round(acted / sent * 100, 0) if sent else None,
        "median_hours_to_acknowledge": round(sorted(acks)[len(acks) // 2], 1) if acks else None,
        "verdict": (
            "No alerts in the window." if not sent else
            "Most alerts are being ignored — the thresholds are probably wrong."
            if ignored > sent * 0.5 else
            "Alerts are being acted on." if acted >= sent * 0.5 else
            "Mixed. Worth reviewing the thresholds that fire most often."),
    }
