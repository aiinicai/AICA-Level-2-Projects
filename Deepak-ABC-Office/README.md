# ABC Chartered Accountants — Offline Office Management Tool

## Submitted by
Deepak CA  
GitHub username: Deepakdeepu714

## Project purpose
An offline office management application for a Chartered Accountant firm.
It helps manage staff assignments, timesheets, office updates and reports.

## Main features
- Administrator, manager and staff access.
- Employee, client, work-type and periodicity masters.
- Assignment allocation, due dates, status updates and review comments.
- Dashboard filters for staff, status and approaching or overdue targets.
- Timesheets against assigned work, with start and end times.
- Billable and non-billable classification.
- Idle-time recording.
- Staff-wise and client-wise reports for selected periods.
- Word and PDF report downloads.
- Office communications and updates.
- Local SQLite storage and database backups.

## Technology
- Python backend.
- SQLite database.
- HTML, CSS and JavaScript interface.
- Bundled Windows Python runtime.
- python-docx and ReportLab for reports.

## How to run
1. Download and extract the complete project folder on a Windows computer.
2. Keep all application files and folders together.
3. Double-click ABC_Office.exe.
4. The application opens in a browser on the same computer.
5. On first launch, create the owner administrator account.
6. Store the owner recovery key safely.

No separate Python installation is required.
Normal local operation does not require an internet connection.

## Data storage
Office data is stored locally in the application's data folder.
Each separate installation has its own database.
Office data, passwords and recovery keys are not included in this submission.

## Office network use
Start_Office_Server.bat provides an optional office LAN mode.
Staff must connect to the same host installation to share one database.

## Included files
- ABC_Office.exe: Windows launcher.
- app/: Application source and interface.
- runtime/: Bundled Python and supporting libraries.
- source/: Launcher source and build information.
- licenses/: Third-party licence information.
- START_HERE.html and README.txt: Detailed instructions.
- Run_Self_Test.bat: Application self-tests.

## Version
1.0.1
