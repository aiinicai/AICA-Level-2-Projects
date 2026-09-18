-- Migration: add workflow stage tracking to attachments
-- Run this in your Supabase SQL editor if the attachments table does not have the "stage" column.
ALTER TABLE "attachments" ADD COLUMN IF NOT EXISTS "stage" TEXT;
