-- ============================================================
-- FIX: gst_returns status ENUM — run this in phpMyAdmin
-- Fixes SQLSTATE[01000] 1265 "Data truncated for column status"
-- ============================================================

USE ca_intranet;

ALTER TABLE gst_returns MODIFY COLUMN status
  ENUM(
    'Pending Data',
    'Data Received',
    'Challan Sent',
    'No Challan Due',
    'Challan Paid',
    'Under Preparation',
    'Under Review',
    'Ready to File',
    'Filed',
    'On Hold',
    'Not Applicable'
  ) DEFAULT 'Pending Data';

SELECT 'gst_returns status ENUM fixed successfully' AS Result;
