-- ============================================================
-- ADD TRIGGER / TARGET / STATUTORY DUE DATE COLUMNS
-- Run in phpMyAdmin SQL tab (select ca_intranet database first)
-- ============================================================

-- GST Returns: add trigger_date, target_date; rename due_date concept to statutory_due_date (keep due_date as-is for compatibility, it now means statutory)
ALTER TABLE gst_returns ADD COLUMN trigger_date DATE NULL AFTER due_date;
ALTER TABLE gst_returns ADD COLUMN target_date DATE NULL AFTER trigger_date;
ALTER TABLE gst_returns ADD COLUMN due_date_overridden TINYINT(1) DEFAULT 0 AFTER target_date;
-- due_date column now represents the Statutory Due Date (editable on case-by-case basis)

-- ETDS Returns: same three columns, plus Form 16A tracking
ALTER TABLE etds_returns ADD COLUMN trigger_date DATE NULL AFTER due_date_return;
ALTER TABLE etds_returns ADD COLUMN target_date DATE NULL AFTER trigger_date;
ALTER TABLE etds_returns ADD COLUMN due_date_overridden TINYINT(1) DEFAULT 0 AFTER target_date;
ALTER TABLE etds_returns ADD COLUMN form16a_due_date DATE NULL AFTER due_date_overridden;
ALTER TABLE etds_returns ADD COLUMN form16a_downloaded_date DATE NULL AFTER form16a_due_date;
ALTER TABLE etds_returns ADD COLUMN form16a_status ENUM('Pending','Downloaded','Not Applicable') DEFAULT 'Pending' AFTER form16a_downloaded_date;

-- Simplify ETDS status workflow to match the new GST-style flow
ALTER TABLE etds_returns MODIFY COLUMN status
    ENUM('Pending Data','Data Received','Working Done','Challan Sent','No Challan Due','Challan Paid',
         'Return Prepared','Filed','Form 16A Pending','Form 16A Downloaded','On Hold','Not Applicable')
    DEFAULT 'Pending Data';

SELECT 'Date columns and Form 16A tracking added successfully' AS Result;
