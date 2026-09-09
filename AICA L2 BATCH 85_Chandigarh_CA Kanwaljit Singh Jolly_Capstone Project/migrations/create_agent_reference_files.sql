-- Migration: Create agent_reference_files table and storage bucket
-- Purpose: Allow users to upload reference/example files for agents

-- Create agent_reference_files table
CREATE TABLE IF NOT EXISTS agent_reference_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  file_name TEXT NOT NULL,
  file_type TEXT NOT NULL CHECK (file_type IN ('example_input', 'example_output', 'quality_standard', 'reference_doc')),
  storage_path TEXT NOT NULL,
  file_size INTEGER,
  uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  CONSTRAINT unique_agent_file_name UNIQUE(agent_id, file_name)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_reference_files_agent_id ON agent_reference_files(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_reference_files_user_id ON agent_reference_files(user_id);

-- Enable Row Level Security
ALTER TABLE agent_reference_files ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can view their own reference files
CREATE POLICY "Users can view their own reference files"
  ON agent_reference_files FOR SELECT
  USING (user_id = auth.uid());

-- RLS Policy: Users can insert their own reference files
CREATE POLICY "Users can insert their own reference files"
  ON agent_reference_files FOR INSERT
  WITH CHECK (user_id = auth.uid());

-- RLS Policy: Users can delete their own reference files
CREATE POLICY "Users can delete their own reference files"
  ON agent_reference_files FOR DELETE
  USING (user_id = auth.uid());

-- Note: Create storage bucket 'agent-reference-files' via Supabase Dashboard
-- Bucket settings:
--   - Public: false
--   - File size limit: 10 MB (10485760 bytes)
--   - Allowed MIME types: text/plain, text/csv, application/pdf,
--     application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,
--     application/vnd.ms-excel,
--     application/vnd.openxmlformats-officedocument.wordprocessingml.document

-- Storage RLS policies (run these after creating the bucket):
-- CREATE POLICY "Users can upload their reference files"
--   ON storage.objects FOR INSERT
--   TO authenticated
--   WITH CHECK (bucket_id = 'agent-reference-files' AND (storage.foldername(name))[1] = auth.uid()::text);

-- CREATE POLICY "Users can view their reference files"
--   ON storage.objects FOR SELECT
--   TO authenticated
--   USING (bucket_id = 'agent-reference-files' AND (storage.foldername(name))[1] = auth.uid()::text);

-- CREATE POLICY "Users can delete their reference files"
--   ON storage.objects FOR DELETE
--   TO authenticated
--   USING (bucket_id = 'agent-reference-files' AND (storage.foldername(name))[1] = auth.uid()::text);
