# Office Manager (Desktop edition)

Practice-management software for a CA firm: clients, GST/ITR/TDS trackers, compliance calendar, tasks, billing and reports.
Runs on a Windows PC as a desktop app. Other staff on the same office network open it in their browser (or the same app).

## What is in this version
Login and roles (Super Admin, Partner, Manager, Employee) · clients with Excel import · GST / ITR / TDS trackers with bulk creation ·
compliance calendar · tasks (drag-and-drop board) · invoices, payments, PDF, email · 10 reports on screen / PDF / Excel / CSV, each with
your logo and CA details at the top · Settings (firm details, logo, email SMTP, backup).
**WhatsApp Manager** (no WhatsApp API, no fees): message clients and staff, bulk send, message templates, and auto reminders for pending GST/ITR/TDS work and unpaid invoices. It prepares each message and opens WhatsApp Web or the WhatsApp Desktop app with the text filled in; you press Send. Delivery cannot be confirmed, so history records "opened".
**Time-savers:** on the client form, Fetch fills name, address and PAN from the official GST portal (you type the captcha); PAN is taken from the GSTIN; pincode fills city and state (needs internet; state only when offline). Back button and Esc on every screen (Esc asks first), five colour themes per user, window opens to fit the screen.
**If something goes wrong:** the app writes details to `error.log` in the data folder (`%APPDATA%\AuditManager`). Send that file to your developer.
**Added in this round:** user permissions (Staff > User permissions), Activity Log menu, services master for invoices, Excel import of GST/ITR/TDS filings with sample templates, record counts on every grid and filter, choice of which firm details print on reports, theme buttons in Settings and My account, bulk email alongside WhatsApp with formatted templates, clickable/draggable fields and a due-date master, invoices by WhatsApp, and backup to a drive folder (manual or daily, with restore).
**Backup to Google Drive / OneDrive:** install their desktop app on the host PC and give its folder in Settings > Backup; the backup files then sync to the cloud by themselves.
**Added in the Office Manager round:** renamed to Office Manager (your data stays where it was); Due Date Master pre-loaded to 31 Mar 2027 and editable; scheduled emails; client portal logins (encrypted); time sheet and hour-based billing; registers and own-GST reports; Advocate mode with Matters & Hearings; backup on opening / closing; moving the data folder to another drive; Edit buttons on masters.
**Backups now include the key that unlocks saved passwords** (email password and client portal logins), so keep backup files private.
**Downloads in the desktop window:** PDF, Excel, CSV and backup files are saved to your Downloads folder and opened; a message at the bottom right shows where. In a normal browser they download the usual way.
**Automatic (event-based) messages:** WhatsApp & Email > Automatic (events). Emails go by themselves; WhatsApp messages are prepared in "WhatsApp ready to send".
**Help:** the Help menu inside the program explains every screen with pictures; the buttons to press are marked with red numbers. To refresh the pictures after changing a screen, run `python tools/make_help_pictures.py` (needs `pip install playwright` and Google Chrome).
**Not in this version yet:** audits, documents, client portal.

## Running it (any PC with Python 3.11+)
    pip install -r requirements.txt
    python run_desktop.py            # opens the app window
First start shows a setup page where you create the firm and the first administrator. There are no default passwords.
Data lives in `%APPDATA%\AuditManager` (set the `AUDIT_MANAGER_DATA` environment variable to move it).

## Office network (several staff)
1. Install and run the app on ONE PC (the host) and keep it switched on in office hours: `python run_desktop.py --server` (or `run_server.bat`).
2. The start-up message shows an address such as `http://192.168.1.10:8765`. Staff open that address in a browser.
3. The first time, Windows Firewall asks whether to allow the program on private networks: choose Allow.
4. Take a backup regularly: Settings > Backup. Keep copies off the host PC. To restore, close the app and replace `auditmanager.db`.
The app uses plain HTTP inside your office network. Do not expose the port to the internet.

## Making a Windows .exe (done once, on a Windows PC)
Install Python 3.11+, then double-click `build_windows.bat`. It runs the tests and creates `dist\OfficeManager\OfficeManager.exe`.
Copy that folder to any PC; no Python is needed there.

## Tests
    pip install -r requirements-dev.txt
    python -m pytest

## Known limits
- The window uses Microsoft Edge WebView2, which is built into current Windows 10/11.
- PDFs show "Rs." instead of the rupee sign unless a font with the symbol is available.
- Delivery of email depends on your SMTP provider; Gmail and Outlook need an app password.

## Starting over with a clean database (for a demo or a fresh install)
There is no in-app "reset" button on purpose, so client data can never be wiped by accident. To clear
everything and start from the setup screen again:
1. Close the app completely (and stop `run_server.bat` too, if you used it).
2. Open the data folder: press Windows+R, type `%APPDATA%\AuditManager`, press Enter (or the folder you
   moved data to via Settings > Data folder).
3. Optional but recommended: take a backup first (Settings > Backup, or just copy `auditmanager.db`
   somewhere safe) so you can restore today's data later if you need it.
4. Delete `auditmanager.db`, and `auditmanager.db-wal` / `auditmanager.db-shm` if present. Leave
   `location.txt`, `move_pending.txt` and `mail.key` alone unless you also want to forget saved passwords.
5. Start the app again (`python run_desktop.py` or the built `.exe`) — it will show the first-run setup
   screen to create a new firm and administrator.

Tip: if you reset often (e.g. between repeated demo recordings), keep a saved copy of a "clean"
`auditmanager.db` — taken right after setup, before adding real data — and copy it back in instead of
repeating setup each time.
