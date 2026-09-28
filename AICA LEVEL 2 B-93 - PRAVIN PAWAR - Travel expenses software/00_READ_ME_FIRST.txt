ABC PRIVATE LIMITED - TRAVEL & EXPENSE MANAGEMENT APP (PWA)  -  Version 1.0
===========================================================================

QUICK START (Windows)
  1. Open folder  04_Executable_Application\ABC_Travel_Expense_App
  2. Double-click  Start_ABC_Travel_App.bat
     (If Node.js is missing it is installed automatically via winget - then run the file again.)
  3. Browser opens at http://localhost:8080
  4. Click "Sign Up" - the FIRST person to sign up becomes the ADMIN.
  5. Admin -> Employees -> add employees with email id and role.
     Only these email ids can sign up.
  6. Click "Install App" in the top menu bar to install it as an app.

  Demo with sample data: double-click Start_Demo_Mode.bat  ->  http://localhost:8081
  Login: admin@abc-demo.com  /  Demo@1234

  macOS: double-click Start_ABC_Travel_App.command     Linux: ./start_mac_linux.sh
  Requirement: Node.js 22 LTS or newer (https://nodejs.org). No other software needed.

CONTENTS
  01_Summary_Document\        Project summary (Word + PDF)
  02_Prompt_Files\            Original prompt, detailed build specification prompt, future-feature prompts
  03_Example_Files\           Sample bills, employee import CSV, demo database, export CSV,
                              walkthrough scenario, 26 screenshots
  04_Executable_Application\  The complete application with one-click launchers
  05_Supporting_Documents\    Workflow & ER diagrams, database schema, API reference,
                              Matrix of Authority, PWA install guide, deployment/HTTPS guide, test report

WORKFLOW
  Employee request -> Business Head -> Managing Director -> Travel Assistant (booking per
  Matrix of Authority) -> travel -> expense statement with bills -> Business Head -> HR Head
  -> Accountant (voucher & payment) -> Paid & Closed

MOBILE PHONES / SHARE LINK
  Double-click Start_Public_Link.bat -> it prints a secure https://....trycloudflare.com link.
  Share it; employees open it on their phone and tap "Install App" (iPhone: Share -> Add to Home Screen).
  Keep that window open and the PC on. The link changes on each restart (saved in PUBLIC_LINK.txt).
  Permanent address options: 05_Supporting_Documents\Deployment_and_HTTPS_Guide.md
