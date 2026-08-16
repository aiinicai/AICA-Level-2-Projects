-- ============================================================
-- IT RETURN REGISTER — DATABASE UPGRADE
-- Run this in phpMyAdmin SQL tab (select ca_intranet database first)
-- Compatible with MySQL 5.7+ / MariaDB 10.2+
-- ============================================================

-- STEP 1: Create client_groups table
CREATE TABLE IF NOT EXISTS client_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_name VARCHAR(150) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- STEP 2: Add group_id column to clients table
-- (If this errors with "Duplicate column", that's fine — skip and continue)
ALTER TABLE clients ADD COLUMN group_id INT NULL;

-- STEP 3: Create itr_returns table
CREATE TABLE IF NOT EXISTS itr_returns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    financial_year VARCHAR(10) NOT NULL,
    ca_partner_id INT,
    group_id INT,
    return_category ENUM('ITR','Audit') NOT NULL DEFAULT 'ITR',
    data_received_on DATE,
    accounting_done_by INT,
    accounting_started_on DATE,
    accounting_na TINYINT(1) DEFAULT 0,
    accounting_status ENUM('NA','WIP','Pending for Client Inputs','Pending for Verification - Supervisor','Pending for Verification - Partner','Done') DEFAULT 'NA',
    itr_prepared_by INT,
    itr_prepared_status ENUM('Yes','No','NA') DEFAULT 'No',
    itr_verified_by INT,
    itr_uploaded_status ENUM('Yes','Ready','WIP') DEFAULT 'WIP',
    itr_ack VARCHAR(30),
    filed_date DATE,
    e_verified ENUM('Yes','No','Pending') DEFAULT 'Pending',
    itr_form_no VARCHAR(10),
    gti DECIMAL(15,2) DEFAULT NULL,
    sa_tax DECIMAL(15,2) DEFAULT NULL,
    refund DECIMAL(15,2) DEFAULT NULL,
    bank_validated ENUM('Yes','No') DEFAULT 'No',
    remarks TEXT,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

SELECT 'IT Return Register tables created successfully' AS Result;
