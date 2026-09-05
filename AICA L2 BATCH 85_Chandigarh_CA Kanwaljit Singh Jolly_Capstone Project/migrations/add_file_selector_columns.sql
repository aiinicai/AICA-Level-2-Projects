-- Migration: Add FileSelector columns to agents table
-- Date: 2026-01-24
-- Description: Add client_file_paths and reference_file_paths columns to support FileSelector component

-- Add client_file_paths column (array of OneDrive file paths)
ALTER TABLE agents
ADD COLUMN IF NOT EXISTS client_file_paths TEXT[] DEFAULT '{}';

-- Add reference_file_paths column (JSONB object with categorized file paths)
ALTER TABLE agents
ADD COLUMN IF NOT EXISTS reference_file_paths JSONB DEFAULT NULL;

-- Add comments for documentation
COMMENT ON COLUMN agents.client_file_paths IS 'Array of OneDrive file paths selected for client folder files';
COMMENT ON COLUMN agents.reference_file_paths IS 'JSONB object containing categorized reference file paths: {example_inputs: [], example_outputs: [], quality_standards: [], reference_docs: []}';

-- Verify the columns were added
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'agents'
AND column_name IN ('client_file_paths', 'reference_file_paths', 'kb_file_paths')
ORDER BY column_name;
