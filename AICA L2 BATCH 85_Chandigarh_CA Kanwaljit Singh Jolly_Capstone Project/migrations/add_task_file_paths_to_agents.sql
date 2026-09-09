-- Migration: Add task_file_paths to agents table
-- Date: 2026-01-26
-- Description: Store selected task folder file paths for agent editing

ALTER TABLE agents
ADD COLUMN IF NOT EXISTS task_file_paths TEXT[] DEFAULT '{}';

COMMENT ON COLUMN agents.task_file_paths IS 'Array of OneDrive file paths selected for task folder files';

SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'agents'
AND column_name IN ('task_file_paths')
ORDER BY column_name;
