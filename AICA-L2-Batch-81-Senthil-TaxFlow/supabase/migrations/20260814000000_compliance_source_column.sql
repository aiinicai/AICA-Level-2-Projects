-- Add a source column to compliance schedules to track where each compliance came from.
-- Values: TEMPLATE (generated from a compliance template), MANUAL (created via the form), IMPORT (bulk-uploaded via CSV).
ALTER TABLE compliance_schedules ADD COLUMN IF NOT EXISTS "source" TEXT NOT NULL DEFAULT 'MANUAL';

CREATE INDEX IF NOT EXISTS idx_schedules_source ON compliance_schedules("source");
