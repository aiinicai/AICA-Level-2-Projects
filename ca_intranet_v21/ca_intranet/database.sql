-- ============================================================
-- CA FIRM INTRANET v3 - DATABASE SCHEMA
-- Run this on a fresh database OR run the ALTER statements
-- at the bottom to upgrade from v1/v2
-- ============================================================

CREATE DATABASE IF NOT EXISTS ca_intranet CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ca_intranet;

-- ------------------------------------------------------------
-- APP SETTINGS (firm name, preferences)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    updated_by INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- USERS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin','partner','supervisor','staff') NOT NULL DEFAULT 'staff',
    email VARCHAR(100),
    mobile VARCHAR(15),
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- GST RETURN TYPES (user-configurable)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gst_return_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    return_name VARCHAR(50) NOT NULL UNIQUE,
    periodicity ENUM('Monthly','Quarterly','Annually','Event-based') NOT NULL DEFAULT 'Monthly',
    description VARCHAR(200),
    is_active TINYINT(1) DEFAULT 1,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- TDS RETURN TYPES (user-configurable)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tds_return_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    form_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(200),
    is_active TINYINT(1) DEFAULT 1,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- CLIENT MASTER
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_code VARCHAR(20) NOT NULL UNIQUE,
    client_name VARCHAR(200) NOT NULL,
    pan VARCHAR(10) NOT NULL UNIQUE,
    constitution ENUM('Individual','HUF','Firm/LLP','Company','AOP','BOI','Trust','Government','Local Authority','Artificial Juridical Person','Other') NOT NULL,
    constitution_subtype VARCHAR(50),
    -- Contact persons (JSON array: [{name, mobile, email, role}])
    contacts TEXT COMMENT 'JSON: [{name,mobile,email,designation}]',
    address TEXT,
    -- GST
    gst_applicable TINYINT(1) DEFAULT 0,
    gstin_list TEXT COMMENT 'JSON: [{gstin, state, reg_date, return_type, effective_from}]',
    gst_reg_date DATE,
    gst_return_type VARCHAR(20) DEFAULT 'Monthly',
    -- TDS
    tds_applicable TINYINT(1) DEFAULT 0,
    tan VARCHAR(10),
    tds_reg_date DATE,
    tds_form_types TEXT COMMENT 'JSON array of selected form type IDs',
    -- Income Tax
    itr_applicable TINYINT(1) DEFAULT 1,
    group_id INT COMMENT 'Client Group - FK to client_groups',
    -- Professional Tax
    ptec_applicable TINYINT(1) DEFAULT 0,
    ptec_no VARCHAR(30),
    ptrc_applicable TINYINT(1) DEFAULT 0,
    ptrc_no VARCHAR(30),
    ptrc_periodicity ENUM('Monthly','Annual') DEFAULT 'Monthly',
    -- ROC
    roc_applicable TINYINT(1) DEFAULT 0,
    cin VARCHAR(25),
    din_list TEXT COMMENT 'JSON: [{name, din}]',
    date_of_incorporation DATE,
    company_type ENUM('Private Limited','Public Limited','OPC','LLP','Section 8','Other'),
    agm_date DATE,
    -- Assignment
    partner_id INT,
    supervisor_id INT,
    status ENUM('Active','Inactive') DEFAULT 'Active',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (partner_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (supervisor_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- GST RETURN REGISTER
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gst_returns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    gstin VARCHAR(20) NOT NULL,
    return_period VARCHAR(20) NOT NULL,
    financial_year VARCHAR(10) NOT NULL,
    return_type_id INT COMMENT 'FK to gst_return_types',
    return_type VARCHAR(50) NOT NULL,
    periodicity VARCHAR(20) DEFAULT 'Monthly',
    due_date DATE COMMENT 'Statutory Due Date - editable case-by-case for govt extensions',
    trigger_date DATE COMMENT 'Date work should be triggered/started',
    target_date DATE COMMENT 'Internal target date to complete before statutory due date',
    due_date_overridden TINYINT(1) DEFAULT 0 COMMENT '1 if statutory due date was manually changed from system default',
    data_received_date DATE,
    data_received_from VARCHAR(100),
    data_receipt_mode ENUM('Email','WhatsApp','Physical','Portal','Other'),
    working_prepared_by INT,
    working_prepared_date DATE,
    working_reviewed_by INT,
    working_reviewed_date DATE,
    cgst_liability DECIMAL(15,2) DEFAULT 0,
    sgst_liability DECIMAL(15,2) DEFAULT 0,
    igst_liability DECIMAL(15,2) DEFAULT 0,
    cess_liability DECIMAL(15,2) DEFAULT 0,
    total_liability DECIMAL(15,2) GENERATED ALWAYS AS (cgst_liability+sgst_liability+igst_liability+cess_liability) STORED,
    payment_date DATE,
    challan_no VARCHAR(50),
    filed_date DATE,
    arn VARCHAR(50),
    late_fee DECIMAL(10,2) DEFAULT 0,
    interest DECIMAL(10,2) DEFAULT 0,
    status ENUM('Pending Data','Data Received','Challan Sent','No Challan Due','Challan Paid','Under Preparation','Under Review','Ready to File','Filed','On Hold','Not Applicable') DEFAULT 'Pending Data',
    remarks TEXT,
    assigned_to INT,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (working_prepared_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (working_reviewed_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- ETDS RETURN REGISTER
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS etds_returns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    tan VARCHAR(10) NOT NULL,
    financial_year VARCHAR(10) NOT NULL,
    quarter ENUM('Q1','Q2','Q3','Q4') NOT NULL,
    form_type VARCHAR(20) NOT NULL,
    due_date_return DATE COMMENT 'Statutory Due Date - editable case-by-case for govt extensions',
    trigger_date DATE COMMENT 'Date work should be triggered/started',
    target_date DATE COMMENT 'Internal target date to complete before statutory due date',
    due_date_overridden TINYINT(1) DEFAULT 0 COMMENT '1 if statutory due date was manually changed from system default',
    form16a_due_date DATE COMMENT 'Auto = statutory due date + 15 days',
    form16a_downloaded_date DATE,
    form16a_status ENUM('Pending','Downloaded','Not Applicable') DEFAULT 'Pending',
    total_tds_deducted DECIMAL(15,2) DEFAULT 0,
    total_tds_deposited DECIMAL(15,2) DEFAULT 0,
    return_prepared_by INT,
    return_prepared_date DATE,
    return_reviewed_by INT,
    return_reviewed_date DATE,
    return_filed_date DATE,
    prn VARCHAR(50),
    correction_filed TINYINT(1) DEFAULT 0,
    correction_date DATE,
    correction_prn VARCHAR(50),
    status ENUM('Pending Data','Data Received','Working Done','Challan Sent','No Challan Due','Challan Paid',
                'Return Prepared','Filed','Form 16A Pending','Form 16A Downloaded','On Hold','Not Applicable') DEFAULT 'Pending Data',
    remarks TEXT,
    assigned_to INT,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (return_prepared_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (return_reviewed_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- PROFESSIONAL TAX REGISTER (PTEC + PTRC combined)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ptax_register (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    pt_type ENUM('PTEC','PTRC') NOT NULL,
    financial_year VARCHAR(10) NOT NULL,
    period VARCHAR(20) NOT NULL COMMENT 'e.g. Apr-2025 or 2025-26',
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
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (prepared_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- ROC COMPLIANCE REGISTER
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roc_compliances (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    financial_year VARCHAR(10) NOT NULL,
    form_type ENUM(
        'MGT-7','MGT-7A','AOC-4','AOC-4 XBRL','ADT-1',
        'DIR-3 KYC','DIR-3 KYC Web','DPT-3','MSME-1',
        'MGT-14','INC-20A','BEN-2','PAS-3','SH-7',
        'CHG-1','CHG-4','LLP-11','LLP-8','Form 8 LLP','Other'
    ) NOT NULL,
    form_description VARCHAR(200),
    due_date DATE,
    due_date_basis VARCHAR(200),
    documents_received_date DATE,
    prepared_by INT,
    prepared_date DATE,
    reviewed_by INT,
    reviewed_date DATE,
    filed_date DATE,
    srn VARCHAR(50),
    challan_amount DECIMAL(10,2) DEFAULT 0,
    late_fee DECIMAL(10,2) DEFAULT 0,
    status ENUM('Not Started','Documents Pending','Under Preparation','Under Review','Ready to File','Filed','On Hold','Not Applicable') DEFAULT 'Not Started',
    remarks TEXT,
    assigned_to INT,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (prepared_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- AUDIT LOG
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    module VARCHAR(50),
    record_id INT,
    action ENUM('CREATE','UPDATE','DELETE','LOGIN','LOGOUT','EXPORT','IMPORT'),
    old_values TEXT,
    new_values TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- DEFAULT SEED DATA
-- ------------------------------------------------------------
INSERT INTO users (name, username, password, role, email) VALUES
('Administrator', 'admin', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'admin', 'admin@firm.local'),
('Senior Partner', 'partner1', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'partner', ''),
('Supervisor One', 'supervisor1', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'supervisor', ''),
('Staff Member One', 'staff1', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'staff', '');
-- Default password: password

INSERT INTO app_settings (setting_key, setting_value) VALUES
('firm_name', 'Your Firm Name'),
('firm_address', ''),
('firm_phone', ''),
('firm_email', ''),
('firm_gstin', ''),
('firm_pan', '');

-- GST Return Types (default set - user can add/edit more)
INSERT INTO gst_return_types (return_name, periodicity, description, sort_order) VALUES
('GSTR-1',   'Monthly',    'Outward Supplies (Monthly)', 1),
('GSTR-1',   'Quarterly',  'Outward Supplies (QRMP)',    2),
('GSTR-3B',  'Monthly',    'Summary Return (Monthly)',   3),
('GSTR-3B',  'Quarterly',  'Summary Return (QRMP)',      4),
('GSTR-9',   'Annually',   'Annual Return',              5),
('GSTR-9C',  'Annually',   'Reconciliation Statement',   6),
('CMP-08',   'Quarterly',  'Composition Tax Payment',    7),
('GSTR-4',   'Annually',   'Composition Annual Return',  8),
('GSTR-1A',  'Monthly',    'Amendment to GSTR-1',        9),
('GSTR-7',   'Monthly',    'TDS under GST',              10),
('GSTR-8',   'Monthly',    'TCS under GST',              11);

-- TDS Return Types
INSERT INTO tds_return_types (form_name, description, sort_order) VALUES
('24Q',  'TDS on Salary',               1),
('26Q',  'TDS on Non-Salary (Resident)',2),
('27Q',  'TDS on Non-Resident Payments',3),
('27EQ', 'TCS Return',                  4),
('SFT',  'Statement of Financial Transactions', 5),
('26QB', 'TDS on Property Purchase',    6),
('26QC', 'TDS on Rent',                 7),
('26QD', 'TDS on Contractor Payments',  8);

-- ============================================================
-- UPGRADE SCRIPT (run only if upgrading from v1/v2)
-- Safe to skip if doing fresh install
-- ============================================================
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS contacts TEXT AFTER constitution_subtype;
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS ptec_applicable TINYINT(1) DEFAULT 0;
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS ptec_no VARCHAR(30);
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS ptrc_applicable TINYINT(1) DEFAULT 0;
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS ptrc_no VARCHAR(30);
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS ptrc_periodicity ENUM('Monthly','Annual') DEFAULT 'Monthly';
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS tds_form_types TEXT;
-- ALTER TABLE gst_returns ADD COLUMN IF NOT EXISTS return_type_id INT;
-- ALTER TABLE gst_returns ADD COLUMN IF NOT EXISTS periodicity VARCHAR(20) DEFAULT 'Monthly';

-- ------------------------------------------------------------
-- CLIENT GROUPS (for IT Return register grouping)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS client_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_name VARCHAR(150) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- IT RETURN REGISTER
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS itr_returns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    financial_year VARCHAR(10) NOT NULL,
    ca_partner_id INT COMMENT 'CA Looking After - partner in charge',
    group_id INT COMMENT 'Client Group',
    return_category ENUM('ITR','Audit') NOT NULL DEFAULT 'ITR',
    data_received_on DATE,
    accounting_done_by INT,
    accounting_started_on DATE,
    accounting_na TINYINT(1) DEFAULT 0 COMMENT '1 if accounting not applicable',
    accounting_status ENUM('NA','WIP','Pending for Client Inputs','Pending for Verification - Supervisor','Pending for Verification - Partner','Done') DEFAULT 'NA',
    itr_prepared_by INT,
    itr_prepared TINYINT(1) DEFAULT NULL COMMENT 'maps Yes/No/NA via itr_prepared_status',
    itr_prepared_status ENUM('Yes','No','NA') DEFAULT 'No',
    itr_verified_by INT,
    itr_uploaded_status ENUM('Yes','Ready','WIP') DEFAULT 'WIP',
    itr_ack VARCHAR(30),
    filed_date DATE COMMENT 'auto-derived from last 6 digits of ITR ACK (ddmmyy)',
    e_verified ENUM('Yes','No','Pending') DEFAULT 'Pending',
    itr_form_no VARCHAR(10) COMMENT 'e.g. 1,2,3,4,5,6,7 or custom text',
    gti DECIMAL(15,2) DEFAULT NULL COMMENT 'Gross Total Income - can be negative',
    sa_tax DECIMAL(15,2) DEFAULT NULL COMMENT 'Self Assessment Tax - positive only',
    refund DECIMAL(15,2) DEFAULT NULL COMMENT 'Refund amount - positive only',
    refund_status ENUM('Pending','Received','Partially Received','Adjusted','Not Applicable') DEFAULT 'Pending',
    refund_received_date DATE NULL,
    refund_received_amount DECIMAL(15,2) NULL,
    refund_intimation_no VARCHAR(50) NULL,
    bank_validated ENUM('Yes','No') DEFAULT 'No',
    remarks TEXT,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (ca_partner_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (accounting_done_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (itr_prepared_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (itr_verified_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);
