"""Schema version 3: backup type/label metadata for safe scheduled-retention policy."""

VERSION = 3
NAME = "backup_schedule_metadata"

SQL = r"""
ALTER TABLE backups ADD COLUMN backup_type TEXT NOT NULL DEFAULT 'MANUAL'
    CHECK (backup_type IN ('MANUAL','SCHEDULED','PRE_RESTORE'));
ALTER TABLE backups ADD COLUMN label TEXT;
CREATE INDEX ix_backups_type_created ON backups(backup_type, created_at DESC);
"""
