USE ca_intranet;

ALTER TABLE gst_returns MODIFY COLUMN return_type VARCHAR(50) NOT NULL DEFAULT '';

ALTER TABLE gst_returns MODIFY COLUMN periodicity VARCHAR(20) NOT NULL DEFAULT 'Monthly';

ALTER TABLE gst_returns MODIFY COLUMN status ENUM('Pending Data','Data Received','Challan Sent','No Challan Due','Challan Paid','Under Preparation','Under Review','Ready to File','Filed','On Hold','Not Applicable') DEFAULT 'Pending Data';

ALTER TABLE gst_returns MODIFY COLUMN data_receipt_mode ENUM('Email','WhatsApp','Physical','Portal','Other') NULL DEFAULT NULL;

ALTER TABLE gst_returns ADD COLUMN IF NOT EXISTS trigger_date DATE NULL;
ALTER TABLE gst_returns ADD COLUMN IF NOT EXISTS target_date DATE NULL;
ALTER TABLE gst_returns ADD COLUMN IF NOT EXISTS due_date_overridden TINYINT(1) DEFAULT 0;
ALTER TABLE gst_returns ADD COLUMN IF NOT EXISTS data_received_from VARCHAR(100) NULL;
ALTER TABLE gst_returns ADD COLUMN IF NOT EXISTS return_type_id INT NULL;

SELECT 'Done' AS Result;
