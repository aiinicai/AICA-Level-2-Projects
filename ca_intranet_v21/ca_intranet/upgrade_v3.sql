-- ============================================================
-- CA FIRM INTRANET — DATABASE UPGRADE v1/v2 → v3
-- Compatible with MySQL 5.7+ and MariaDB 10.2+
-- 
-- HOW TO RUN:
-- 1. Open http://localhost/phpmyadmin
-- 2. Click on ca_intranet database (left sidebar)
-- 3. Click SQL tab at top
-- 4. Paste this entire file and click Go
-- ============================================================

USE ca_intranet;

-- ── STEP 1: CREATE NEW TABLES ─────────────────────────────

CREATE TABLE IF NOT EXISTS app_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    updated_by INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gst_return_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    return_name VARCHAR(50) NOT NULL,
    periodicity ENUM('Monthly','Quarterly','Annually','Event-based') NOT NULL DEFAULT 'Monthly',
    description VARCHAR(200),
    is_active TINYINT(1) DEFAULT 1,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tds_return_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    form_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(200),
    is_active TINYINT(1) DEFAULT 1,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ptax_register (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    pt_type ENUM('PTEC','PTRC') NOT NULL,
    financial_year VARCHAR(10) NOT NULL,
    period VARCHAR(20) NOT NULL,
    due_date DATE,
    amount DECIMAL(10,2) DEFAULT 0,
    payment_date DATE,
    challan_no VARCHAR(50),
    filed_date DATE,
    acknowledgement_no VARCHAR(50),
    prepared_by INT,
    prepared_date DATE,
    status ENUM('Pending','Under Preparation','Ready to File','Filed','On Hold','Not Applicable') DEFAULT 'Pending',
    remarks TEXT,
    assigned_to INT,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

-- ── STEP 2: ADD NEW COLUMNS TO CLIENTS TABLE ─────────────
-- Using stored procedure to safely add columns only if missing
-- (works on MySQL 5.7 which does not support ADD COLUMN IF NOT EXISTS)

DROP PROCEDURE IF EXISTS add_column_if_missing;

DELIMITER $$
CREATE PROCEDURE add_column_if_missing(
    IN tbl VARCHAR(64),
    IN col VARCHAR(64),
    IN col_def TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = tbl
          AND COLUMN_NAME  = col
    ) THEN
        SET @sql = CONCAT('ALTER TABLE `', tbl, '` ADD COLUMN `', col, '` ', col_def);
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$
DELIMITER ;

-- clients table new columns
CALL add_column_if_missing('clients', 'contacts',         'TEXT AFTER constitution_subtype');
CALL add_column_if_missing('clients', 'tds_form_types',   'TEXT AFTER tan');
CALL add_column_if_missing('clients', 'ptec_applicable',  'TINYINT(1) DEFAULT 0 AFTER itr_applicable');
CALL add_column_if_missing('clients', 'ptec_no',          'VARCHAR(30) AFTER ptec_applicable');
CALL add_column_if_missing('clients', 'ptrc_applicable',  'TINYINT(1) DEFAULT 0 AFTER ptec_no');
CALL add_column_if_missing('clients', 'ptrc_no',          'VARCHAR(30) AFTER ptrc_applicable');
CALL add_column_if_missing('clients', 'ptrc_periodicity', "ENUM('Monthly','Annual') DEFAULT 'Monthly' AFTER ptrc_no");

-- gst_returns table new columns
CALL add_column_if_missing('gst_returns', 'return_type_id', 'INT NULL AFTER return_type');
CALL add_column_if_missing('gst_returns', 'periodicity',    "VARCHAR(20) DEFAULT 'Monthly' AFTER return_type_id");

-- ── STEP 3: UPDATE GST STATUS ENUM ───────────────────────

ALTER TABLE gst_returns MODIFY COLUMN status
    ENUM('Pending Data','Data Received','Challan Sent','No Challan Due','Challan Paid',
         'Under Preparation','Under Review','Ready to File','Filed','On Hold','Not Applicable')
    DEFAULT 'Pending Data';

-- ── STEP 4: REMOVE COLUMNS NO LONGER NEEDED ──────────────
-- (only if they exist — safe to skip if already removed)

CALL add_column_if_missing('clients', 'gst_reg_date', 'DATE NULL');  -- keep for now, just not shown in UI

-- ── STEP 5: SEED NEW TABLE DATA ──────────────────────────

INSERT IGNORE INTO app_settings (setting_key, setting_value) VALUES
    ('firm_name',    'Your Firm Name'),
    ('firm_address', ''),
    ('firm_phone',   ''),
    ('firm_email',   ''),
    ('firm_gstin',   ''),
    ('firm_pan',     ''),
    ('app_version',  '1.0');

INSERT IGNORE INTO gst_return_types (return_name, periodicity, description, sort_order) VALUES
    ('GSTR-1',   'Monthly',    'Outward Supplies (Monthly)',       1),
    ('GSTR-1',   'Quarterly',  'Outward Supplies QRMP',           2),
    ('GSTR-3B',  'Monthly',    'Summary Return (Monthly)',         3),
    ('GSTR-3B',  'Quarterly',  'Summary Return QRMP',             4),
    ('GSTR-9',   'Annually',   'Annual Return',                    5),
    ('GSTR-9C',  'Annually',   'Reconciliation Statement',         6),
    ('CMP-08',   'Quarterly',  'Composition Tax Payment',          7),
    ('GSTR-4',   'Annually',   'Composition Annual Return',        8),
    ('GSTR-1A',  'Monthly',    'Amendment to GSTR-1',              9),
    ('GSTR-7',   'Monthly',    'TDS under GST',                   10),
    ('GSTR-8',   'Monthly',    'TCS under GST',                   11);

INSERT IGNORE INTO tds_return_types (form_name, description, sort_order) VALUES
    ('24Q',  'TDS on Salary',                      1),
    ('26Q',  'TDS on Non-Salary Resident',         2),
    ('27Q',  'TDS on Non-Resident Payments',       3),
    ('27EQ', 'TCS Return',                         4),
    ('SFT',  'Statement of Financial Transactions',5),
    ('26QB', 'TDS on Property Purchase',           6),
    ('26QC', 'TDS on Rent',                        7),
    ('26QD', 'TDS on Contractor Payments',         8);

-- ── STEP 6: CLEANUP ──────────────────────────────────────

DROP PROCEDURE IF EXISTS add_column_if_missing;

-- ── DONE ─────────────────────────────────────────────────

SELECT 'SUCCESS: Upgrade to v3 complete!' AS Result;
SELECT 
    COLUMN_NAME AS 'New Column',
    DATA_TYPE   AS 'Type',
    IS_NULLABLE AS 'Nullable'
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME   = 'clients'
  AND COLUMN_NAME IN ('contacts','tds_form_types','ptec_applicable','ptec_no','ptrc_applicable','ptrc_no','ptrc_periodicity')
ORDER BY ORDINAL_POSITION;

-- ── FIX: Set gst_applicable=0 for clients with no GSTIN saved ──
-- Run this after reimport if needed
-- UPDATE clients SET gst_applicable=0 WHERE (gstin_list IS NULL OR gstin_list='') AND gst_applicable=1;

-- ── CHECK: See which clients have GST flag but no GSTIN ──────────
-- SELECT id, client_code, client_name, pan, gst_applicable, gstin_list 
-- FROM clients WHERE gst_applicable=1 AND (gstin_list IS NULL OR gstin_list='[]' OR gstin_list='');

-- ============================================================
-- REFUND TRACKING (add to itr_returns)
-- Run if upgrading from a version before refund tab was added
-- ============================================================
ALTER TABLE itr_returns
  ADD COLUMN IF NOT EXISTS refund_status ENUM('Pending','Received','Partially Received','Adjusted','Not Applicable') DEFAULT 'Pending' AFTER refund,
  ADD COLUMN IF NOT EXISTS refund_received_date DATE NULL AFTER refund_status,
  ADD COLUMN IF NOT EXISTS refund_received_amount DECIMAL(15,2) NULL AFTER refund_received_date,
  ADD COLUMN IF NOT EXISTS refund_intimation_no VARCHAR(50) NULL AFTER refund_received_amount;
