-- Migration: Add support for multiple OneDrive connections
-- Date: 2026-01-24
-- Description: Allow users to connect multiple OneDrive accounts with individual base paths

-- Create onedrive_connections table
CREATE TABLE IF NOT EXISTS onedrive_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    account_name TEXT NOT NULL, -- Friendly name like "Personal OneDrive", "Work OneDrive"
    account_email TEXT, -- Microsoft account email
    refresh_token TEXT NOT NULL,
    base_folder_path TEXT DEFAULT '/',
    is_active BOOLEAN DEFAULT FALSE, -- Which connection is currently active
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_onedrive_connections_user_id ON onedrive_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_onedrive_connections_active ON onedrive_connections(user_id, is_active);

-- Add comments
COMMENT ON TABLE onedrive_connections IS 'Stores multiple OneDrive connections per user';
COMMENT ON COLUMN onedrive_connections.account_name IS 'User-friendly name for the connection (e.g., "Work OneDrive")';
COMMENT ON COLUMN onedrive_connections.account_email IS 'Microsoft account email address';
COMMENT ON COLUMN onedrive_connections.refresh_token IS 'OAuth refresh token for this OneDrive account';
COMMENT ON COLUMN onedrive_connections.base_folder_path IS 'Base folder path for this OneDrive connection';
COMMENT ON COLUMN onedrive_connections.is_active IS 'Whether this is the currently active connection';

-- Migrate existing OneDrive connections from profiles table
INSERT INTO onedrive_connections (user_id, account_name, refresh_token, base_folder_path, is_active)
SELECT
    id as user_id,
    'Primary OneDrive' as account_name,
    onedrive_refresh_token as refresh_token,
    COALESCE(onedrive_base_path, '/') as base_folder_path,
    TRUE as is_active
FROM profiles
WHERE onedrive_refresh_token IS NOT NULL AND onedrive_refresh_token != '';

-- Add RLS policies
ALTER TABLE onedrive_connections ENABLE ROW LEVEL SECURITY;

-- Users can only see their own connections
CREATE POLICY "Users can view own OneDrive connections"
    ON onedrive_connections FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own connections
CREATE POLICY "Users can insert own OneDrive connections"
    ON onedrive_connections FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own connections
CREATE POLICY "Users can update own OneDrive connections"
    ON onedrive_connections FOR UPDATE
    USING (auth.uid() = user_id);

-- Users can delete their own connections
CREATE POLICY "Users can delete own OneDrive connections"
    ON onedrive_connections FOR DELETE
    USING (auth.uid() = user_id);
