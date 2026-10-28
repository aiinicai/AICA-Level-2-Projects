VERSION 1.0.1 - Windows backup file-lock fix

ABC CHARTERED ACCOUNTANTS - OFFLINE TEAM OFFICE

FIRST OPEN START_HERE.html FOR STEP-BY-STEP INSTRUCTIONS.

1. Extract this ENTIRE folder to Documents or another writable local folder.
2. Double-click ABC_Office.exe on a 64-bit Windows 10 or Windows 11 PC.
3. Your browser opens the local app. Create the first administrator and save the owner recovery key.
4. Create employee and client masters, then allocate assignments.
5. Staff log in, change temporary passwords, update allowed work statuses and enter time ranges.

No Python installation, pip install, Microsoft Word, Google Sheets, Supabase or internet is needed to run this package.
The browser is the local user interface; it is not a hosted website.
Keep app/ and runtime/ beside ABC_Office.exe. Do not run only the EXE from inside the ZIP.
Keep the server console running. Start_Local.bat provides the same app with a visible console.

SHARED OFFICE USE WITHOUT INTERNET
After initial administrator setup, close the running local server and start Start_Office_Server.bat on ONE office host PC.
Give staff the office network URL printed in that host console. They open that address in their browsers.
All staff then use the same central database. The host PC must stay on and be reachable over the office LAN.
Running separate copies on separate computers creates independent databases; these do not synchronise.

DATA AND BACKUPS
Saved data: data/office.sqlite3. A dated backup is made on server startup each new date.
Admins/Managers can download a complete database backup from the Backups tab.
Back up after first configuration and regularly during use. Keep a copy on another drive.
This package starts a fresh ABC database. Existing Google Sheets data is not automatically imported.
Offline password resets are handled by Admin/Manager, or by the owner's saved recovery key. No emails are sent.

CHECKS
Run Run_Self_Test.bat for built-in tests; they use temporary data only.
If the app fails to open, run Start_Local.bat and read the error in its console.
Source and build information are in source/BUILD_NOTES.txt.
The EXE was built for Windows x64; native Windows execution could not be tested in this Linux environment.

UPDATE FROM 1.0.0
Close the running office server. Extract the new ZIP separately, then replace only the app folder in your existing installation. Keep your existing data folder unchanged. The EXE and bundled runtime are unchanged.
