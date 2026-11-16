# Single EXE, database and activation

Run `Smart Billing Manager.exe` in this folder. No Python installation is required. First launch can take several seconds as bundled libraries extract to a temporary directory.

The database defaults to `database/billing.json` beside the EXE. This file and `database/billing.json.bak` contain your invoice data. They must remain writable external files so changes survive closing the application. A single EXE contains all application code and libraries, not a read-only embedded database.

The active database path appears below the title. Click **Database Folder** to select a folder containing `billing.json`, or an empty folder. For an empty folder, choose **Yes** to copy your current database or **No** to start empty. Existing databases are opened without replacement. The selected path persists in `settings.json` beside the EXE. Embedded logo snapshots travel with saved invoices. Keep separate backups of older logo files if needed.

The original default path on this PC is:
`C:\Users\Administrator\Desktop\AICA LEVEL 2\Day 3\Billing Software\database\billing.json`

PDFs default to `invoices_pdf` beside the EXE, regardless of the database folder selected.

## Trial and keys

The 30-day trial runs from 3 November 2026 at 00:00 IST until 3 December 2026 at 00:00 IST. The top-right red countdown stays visible and updates every second. On expiry, billing controls are disabled, invoices are preserved, and **Activate** remains available.

`OWNER_ACTIVATION_KEYS.txt` contains **12 signed keys: 4 for 5 minutes, 4 for 1 day and 4 for 30 days**. Keep this file private; distribute only the EXE to customers. Click **Activate** and paste a key. Validity starts immediately and replaces the existing expiry (it does not add time to it). An expired key cannot be reused on that installation. A shorter key can shorten the current trial or activation; use 5-minute keys only for testing.

`license_state.json` beside the EXE stores activation expiry and used key IDs independently of the selected database. Changing the database does not restart the trial. Back up this file with the application. Gross backward clock changes are detected. This is offline local licensing: it cannot prevent a determined user editing/deleting local state, patching an EXE, or reusing a key on another installation. Globally single-use keys and strong anti-tamper enforcement require a license server or managed hardware.

The source `generate_keys.py` is an owner utility and is not bundled. It refuses to replace the existing verification key. The signing private key was not stored or included in the EXE.
