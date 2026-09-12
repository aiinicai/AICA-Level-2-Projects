"""The daily Tally pull.

Deliberately a plain asyncio loop rather than a job framework. The application
is local-first and single-process, and a scheduler that needs its own broker to
poll one local port would be a worse answer than the problem.

What it will not do is pretend. If the machine was asleep at 08:00, the sync
did not happen; this does not quietly run it at 11:00 and stamp it as the
08:00 one. It runs, records the attempt honestly, and the status banner tells
whoever signs in how old the data actually is.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from app.database import SessionLocal
from app.models import Entity, SyncRun, SyncSchedule

log = logging.getLogger("cashrunway.sync")

CHECK_EVERY_SECONDS = 60


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _due(s: SyncSchedule, now: datetime) -> bool:
    """Due if today's slot has passed and we have not attempted since it."""
    if not s.enabled:
        return False
    slot = now.replace(hour=s.hour, minute=s.minute, second=0, microsecond=0)
    if now < slot:
        return False
    return s.last_attempt is None or s.last_attempt < slot


def run_one(db, entity: Entity, schedule: SyncSchedule, triggered_by: str) -> dict:
    """Pull and normalise for one entity. Records the run either way."""
    from app.adapters import normalizer
    from app.adapters.tally import (
        TallyClient, TallyError, fetch_bills_outstanding, fetch_ledgers,
        fetch_vouchers,
    )

    run = SyncRun(entity_id=entity.id, source="tally",
                  triggered_by=triggered_by, status="running")
    db.add(run)
    db.flush()
    schedule.last_attempt = _now()

    today = date.today()
    since = today - timedelta(days=schedule.lookback_days)
    client = TallyClient()
    try:
        led = normalizer.normalise_ledgers(
            db, entity, fetch_ledgers(client, entity.tally_company))
        vou = normalizer.normalise_vouchers(
            db, entity, fetch_vouchers(client, since, today, entity.tally_company))
        bills = (fetch_bills_outstanding(client, today, entity.tally_company, True)
                 + fetch_bills_outstanding(client, today, entity.tally_company, False))
        bil = normalizer.normalise_bills(db, entity, bills, today)

        records = (led["accounts_created"] + vou["entries_created"]
                   + bil["invoices_created"] + bil["bills_created"])
        awaiting = led.get("new_ledgers_awaiting_review", [])
        run.status = "partial" if awaiting else "success"
        run.records = records
        run.message = (f"{len(awaiting)} new ledger(s) since the last review need "
                       f"mapping: {', '.join(awaiting[:8])}"
                       f"{'…' if len(awaiting) > 8 else ''}") if awaiting else None
        run.finished_at = _now()
        entity.last_data_update = run.finished_at
        schedule.last_success = run.finished_at
        schedule.consecutive_failures = 0
        db.commit()
        log.info("Tally sync %s for %s — %s record(s).", run.status, entity.name, records)
        return {"status": run.status, "records": records, "message": run.message}

    except TallyError as e:
        run.status = "failed"
        run.message = str(e)
        run.finished_at = _now()
        schedule.consecutive_failures += 1
        db.commit()
        # Loud on purpose. A connector that quietly stops working is the worst
        # kind of data problem, and a WARNING in a log nobody reads is quiet.
        log.error("Tally sync FAILED for %s (%d in a row): %s",
                  entity.name, schedule.consecutive_failures, e)
        return {"status": "failed", "message": str(e)}


async def daily_sync_loop() -> None:
    """Check once a minute whether any entity's daily slot has come round."""
    while True:
        try:
            db = SessionLocal()
            try:
                now = _now()
                for s in db.query(SyncSchedule).filter(SyncSchedule.enabled.is_(True)).all():
                    if not _due(s, now):
                        continue
                    entity = db.get(Entity, s.entity_id)
                    if not entity or not entity.tally_company:
                        continue
                    log.info("Daily Tally sync due for %s.", entity.name)
                    run_one(db, entity, s, triggered_by="Daily schedule")
            finally:
                db.close()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("The sync scheduler hit an error; it will try again.")
        await asyncio.sleep(CHECK_EVERY_SECONDS)
