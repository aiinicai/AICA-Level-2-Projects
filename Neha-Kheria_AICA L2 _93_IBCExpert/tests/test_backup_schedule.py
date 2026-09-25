from datetime import datetime, timedelta, timezone

from app.core.time import FixedClock
from app.db.connection import connect
from app.db.migrate import migrate
from app.security.audit import AuditService
from app.services.backup import BackupService
from app.services.backup_schedule import BackupScheduleService

UTC = timezone.utc


def _services(tmp_path, now):
    db_path = tmp_path / "app.sqlite3"
    db = connect(db_path); migrate(db)
    master = bytes(range(32))
    audit = AuditService(db, bytes(reversed(range(32))))
    clock = FixedClock(now)
    backup = BackupService(db, db_path, tmp_path / "vault", tmp_path / "backups", master, audit, clock=clock)
    schedule = BackupScheduleService(db, backup, clock=clock)
    return db, backup, schedule, clock


def test_scheduled_backup_runs_when_due_and_persists_policy(tmp_path):
    now = datetime(2026, 9, 23, 3, 0, tzinfo=UTC)
    db, backup, schedule, clock = _services(tmp_path, now)
    initialized = schedule.run_if_due(default_retention=5)
    assert initialized["ran"] is False
    assert initialized["reason"] == "schedule_initialized"
    clock.value = now + timedelta(days=1, seconds=1)
    result = schedule.run_if_due(default_retention=5)
    assert result["ran"] is True
    policy = schedule.get_policy(default_retention=5)
    assert policy.last_run_at is not None
    assert policy.next_due_at is not None
    row = db.execute("SELECT backup_type,label,status FROM backups").fetchone()
    assert row["backup_type"] == "SCHEDULED"
    assert row["status"] == "VALID"
    assert "scheduled" in row["label"].lower()
    assert schedule.run_if_due(default_retention=5)["ran"] is False


def test_retention_deletes_only_old_scheduled_backups(tmp_path):
    now = datetime(2026, 9, 20, 3, 0, tzinfo=UTC)
    db, backup, schedule, clock = _services(tmp_path, now)
    backup.create("Keep manual", backup_type="MANUAL")
    for day in range(4):
        clock.value = now + timedelta(days=day)
        backup.create(f"Scheduled {day}", backup_type="SCHEDULED")
    deleted = schedule.apply_retention(2)
    assert deleted == 2
    assert db.execute("SELECT COUNT(*) FROM backups WHERE backup_type='MANUAL' AND status='VALID'").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM backups WHERE backup_type='SCHEDULED' AND status='VALID'").fetchone()[0] == 2
    assert db.execute("SELECT COUNT(*) FROM backups WHERE backup_type='SCHEDULED' AND status='DELETED'").fetchone()[0] == 2


def test_schedule_policy_validation_and_disable(tmp_path):
    now = datetime(2026, 9, 23, 3, 0, tzinfo=UTC)
    _, _, schedule, _ = _services(tmp_path, now)
    policy = schedule.update_policy(enabled=False, interval_days=7, retention=12)
    assert policy.enabled is False
    assert policy.interval_days == 7
    assert policy.retention == 12
    assert schedule.run_if_due()["ran"] is False
