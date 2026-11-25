"""Daily snapshots: a frozen copy of the forecast grid per day and scenario.

Saving again on the same day replaces that day's snapshot. Snapshots feed the locked actual lots
and the bank tie-out (yesterday's forecast vs today's ERP balance).
"""
from __future__ import annotations

import hashlib
import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.forecast import Forecast
from app.models import Snapshot
from app.services.audit import audit


def save_snapshot(db: Session, fc: Forecast, user_id: int | None = None,
                  snapshot_date: date | None = None) -> Snapshot:
    snapshot_date = snapshot_date or date.today()
    grid = fc.to_dict()
    sha = hashlib.sha256(json.dumps(grid, sort_keys=True).encode()).hexdigest()
    snap = db.scalar(select(Snapshot).where(Snapshot.snapshot_date == snapshot_date,
                                            Snapshot.scenario_id == fc.scenario_id))
    replaced = snap is not None
    if snap is None:
        snap = Snapshot(snapshot_date=snapshot_date, scenario_id=fc.scenario_id)
        db.add(snap)
    snap.as_of_date, snap.grid, snap.content_sha256, snap.created_by_id = fc.as_of, grid, sha, user_id
    db.flush()
    audit(db, "snapshot.replace" if replaced else "snapshot.save", "snapshot", snap.id,
          after={"date": snapshot_date, "as_of": fc.as_of, "scenario": fc.scenario, "sha256": sha}, user_id=user_id)
    return snap
