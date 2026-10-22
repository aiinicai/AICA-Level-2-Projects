CERTIFYFLOW & SARAL BRIDGE - PYTHON VERSION
===========================================
No Node.js, no npm, no internet needed (Python standard library only).

1. Install Python 3.8+ from python.org (tick "Add python.exe to PATH").
2. Extract this folder fully (don't run from inside the zip).
3. Double-click START_CERTIFYFLOW.bat

Tabs: Certificate Studio | Party Master | Approval Queue | Email Dispatch |
      Saral Invoicing | Settings

Your data is kept in data\app_storage.json (same file format as the old app,
so your existing parties/settings are already loaded). Word files are saved in
the Certificates folder.

EMAIL: leave the SMTP password empty to only simulate sending. For real emails
fill Settings -> SMTP (Gmail: smtp.gmail.com, port 587, and an "App password").

SARAL: like the original, the app generates the SQL voucher script for Saral
(copy it from the Saral Invoicing tab and run it in SQL Server). It does not
write into the Saral database by itself.
