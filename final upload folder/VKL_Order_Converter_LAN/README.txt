================================================================================
   VKL CUSTOMER ORDER TO ERP CONVERTER - LAN SERVER GUIDE
================================================================================
Target Audience: Finance, Operations, and IT Administration Teams
System: Windows 64-bit (Windows 10, 11, or Windows Server 2016/2019/2022)

--------------------------------------------------------------------------------
1. QUICK START
--------------------------------------------------------------------------------
VKL_Order_Converter.exe is ALREADY BUILT and included. You do not need Go.
1. Extract this zip to any folder on the server PC (not inside a protected folder).
2. To try it first: double-click VKL_Order_Converter.exe, open the address it prints.
   (If Windows says "Windows protected your PC": More info > Run anyway.)
3. To change the program later, edit the source and double-click "build.bat"
   (this is the only step that needs Go from https://go.dev/dl/).

--------------------------------------------------------------------------------
2. HOW TO INSTALL (OR UPDATE) AS A WINDOWS BACKGROUND SERVICE
   TO UPDATE to a newer package: extract it and run install.bat as administrator again.
   It stops the old copy, replaces the program and restarts it. Your data folder is kept.
--------------------------------------------------------------------------------
1. Right-click "install.bat" and select "Run as administrator".
2. The installer automatically:
   - Copies files into C:\VKL_Order_Converter\
   - Adds a Windows Defender Firewall rule for port 8080 (Private and Domain networks)
   - Registers a Windows Scheduled Task "VKL Order Converter" that starts
     automatically with Windows as SYSTEM.
   - Starts the server immediately.
3. Once finished, it prints the exact URLs to share with your colleagues.

--------------------------------------------------------------------------------
3. THE URL TO GIVE COLLEAGUES
--------------------------------------------------------------------------------
Colleagues on the same office network (Ethernet or office Wi-Fi) can open
the converter simply by typing the URL in Google Chrome or Microsoft Edge:

   http://[SERVER-IP]:8080

Example:
   http://192.168.1.50:8080

Colleagues do NOT need to install anything on their computers.
Order processing occurs 100% privately in each colleague's browser session.
Customer order files are NEVER uploaded over the network.

--------------------------------------------------------------------------------
4. HOW TO CHANGE THE PORT OR SET A MASTER UPLOAD PIN
--------------------------------------------------------------------------------
Open "C:\VKL_Order_Converter\config.json" in Notepad:

   {
     "port": 8080,
     "pin": "1234",
     "dataDir": "data"
   }

- "port": Change from 8080 to any other available port (e.g. 9000).
- "pin": Leave empty ("") for open office use. If you enter a PIN (e.g. "1234"),
  users will be prompted for this PIN before they can upload or restore an
  ERP SKU Master. Regular order processing never requires a PIN.
- After saving config.json, restart the server task (see Section 7).

--------------------------------------------------------------------------------
5. WHERE DATA, BACKUPS, AND AUDIT LOGS ARE STORED
--------------------------------------------------------------------------------
All data is stored locally in "C:\VKL_Order_Converter\data\":

- master.json:
  The current shared ERP SKU master catalog.
- data\history\master_YYYYMMDD_HHMMSS.json:
  Automatic snapshot backup created every time a new master is uploaded.
  The server automatically retains the last 20 versions.
- data\audit.csv:
  Permanent audit log recording timestamp, colleague IP address, action,
  SKU count, and file name.
- logs\server.log:
  Server activity log, automatically rotated at 5 MB (keeps 5 backup logs).

--------------------------------------------------------------------------------
6. HOW TO RESTORE AN OLDER SKU MASTER
--------------------------------------------------------------------------------
METHOD A (Visual Admin Portal):
1. Open http://localhost:8080/admin in your browser.
2. Scroll to the "Master SKU Version History" table.
3. Click "Restore" next to the desired historical timestamp.

METHOD B (Manual File Copy):
1. Open C:\VKL_Order_Converter\data\history\
2. Choose the backup file you want (e.g. master_20261102_143000.json).
3. Copy it into C:\VKL_Order_Converter\data\ and rename it to "master.json".

--------------------------------------------------------------------------------
7. HOW TO UPDATE THE PROGRAM
--------------------------------------------------------------------------------
When a new software version is released:
1. Stop the current task: open cmd and run:
   schtasks /end /tn "VKL Order Converter"
2. Copy the new "VKL_Order_Converter.exe" into "C:\VKL_Order_Converter\".
3. Restart the task:
   schtasks /run /tn "VKL Order Converter"
Your data, SKU master, history, and configuration remain 100% intact.

--------------------------------------------------------------------------------
8. OFFICE NETWORK TIP: FIXED IP OR DHCP RESERVATION
--------------------------------------------------------------------------------
If your server computer reboots, the office router might assign it a new IP address.
To prevent colleagues' bookmarks from breaking:
- Ask your office IT administrator to assign a "DHCP Reservation" or
  "Static IP" to the server computer (e.g., 192.168.1.50).
- Alternatively, colleagues can access it using the computer name:
  http://[COMPUTER-NAME]:8080 (e.g. http://FINANCE-PC:8080).

--------------------------------------------------------------------------------
9. TWO-COMPUTER VERIFICATION TEST PLAN
--------------------------------------------------------------------------------
Follow this simple 4-step test plan using two office computers (PC A and PC B):

Step 1: Open the Application
- On PC A, open Chrome: http://[SERVER-IP]:8080
- On PC B, open Chrome: http://[SERVER-IP]:8080
- Both computers see the converter interface showing "Using built-in sample master".

Step 2: Upload SKU Master on PC A
- On PC A, click "ERP SKU Master" -> "Upload New Master".
- Upload your company's master file (e.g. "VKL_Master_Q4.csv").
- PC A displays a navy notification in bottom-right:
  "Master shared with all users (N SKUs)".

Step 3: Verify Instant Synchronization on PC B
- Go to PC B and refresh the page (F5).
- PC B immediately displays the blue status badge:
  "Using master uploaded earlier: VKL_Master_Q4.csv (N SKUs Loaded)".
- PC B now automatically converts orders using PC A's master without uploading anything!

Step 4: Verify Persistence Across Restarts
- On the server PC, restart the scheduled task or reboot the computer.
- Refresh the browser on PC B.
- The master remains active with the exact SKU count and filename.

================================================================================
For assistance or IT inquiries, contact your internal operations team.
================================================================================

--------------------------------------------------------------------------------
10. EMAIL BUTTONS: DRAFT IN CLASSIC OUTLOOK WITH THE EXCEL ATTACHED
--------------------------------------------------------------------------------
The "Email gross weight" buttons open a draft in CLASSIC Outlook (desktop) with
the Excel attached and the subject filled in. Recipients are added by the user.

One-time set-up on EACH PC that uses classic Outlook (no administrator needed):
1. Copy the folder "Outlook_Helper" to the PC (or run it from the zip).
2. Double-click install.bat. A message says "Installed".
3. Click an Email button in the converter. Chrome/Edge asks once to open
   "VKL Outlook Helper": tick "Always allow" and click Open.
4. Outlook opens a new draft with the Excel attached. Add recipients and send.

Notes:
- The generated Excel is held in server memory for 10 minutes so the helper can
  collect it, then discarded. Customer order files are never uploaded.
- Needs classic Outlook installed. New Outlook has no automation interface, so
  the helper shows a message and the page offers "Download the Excel instead".
- To remove: run uninstall.bat in the same folder.
- The server must be updated to this package (v4) for the buttons to work.
