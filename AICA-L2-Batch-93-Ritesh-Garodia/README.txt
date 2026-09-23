ICAI AICA Level 2 Capstone Project
Tax & Labour-Code Compliance Tracker
Ritesh Garodia — garodia1.ritesh@gmail.com

CONTENTS
--------
Project_Summary.pdf      - overview, architecture, deliverables, known simplifications
Prompts_Used.md          - the AI prompts used to build this project
Examples/                - sample input/output files
  Compliance_Report_2026-09.pdf   - real generated month-end report
  Sample_Trial_Balance.xlsx        - sample trial balance input
  Sample_Variance_Report.xlsx      - sample variance output from that trial balance
Executables/              - the working system
  Compliance_Master.xlsx           - master tracker (open in Excel)
  n8n_workflow_export.json         - the n8n workflow (Import from File in n8n)
  dashboard.py + requirements.txt  - Streamlit dashboard
  generate_monthly_report.py       - month-end PDF report generator
  generate_variance_report.py      - trial balance variance checker

HOW TO RUN
----------
1. Master tracker: open Executables/Compliance_Master.xlsx in Excel.
2. n8n workflow: in n8n, Workflows > Import from File > select
   n8n_workflow_export.json. Connect your own Google Sheets + Gmail
   credentials, then point the two Google Sheets nodes at a Google Sheet
   copy of Compliance_Master.xlsx's "Task Instances" sheet.
   (A live copy of this workflow is also deployed at:
   https://riteshgarodia.app.n8n.cloud/workflow/W1uFTzEuOpdAGGg0)
3. Dashboard: from Executables/, run
       pip install -r requirements.txt
       streamlit run dashboard.py
   (Compliance_Master.xlsx must be in the same folder, used as a fallback.)
   For live multi-user data, import Compliance_Master.xlsx into a Google
   Sheet, restrict edit access via Share to specific Editors, then use
   File > Share > Publish to web on the "Task Instances" tab (and
   optionally a "Trial Balance" tab) to get read-only CSV links. Paste
   those into SHEET_CSV_URL / TB_SHEET_CSV_URL at the top of dashboard.py.
   The dashboard sidebar also has one-click downloads for the month-end
   PDF report and the trial-balance Variance Report, generated live from
   whichever data source is configured - no separate scripts needed.
4. Month-end report (standalone alternative to the dashboard's own button):
       python generate_monthly_report.py 2026-09
5. Variance check (standalone alternative to the dashboard's own button):
       python generate_variance_report.py ../Examples/Sample_Trial_Balance.xlsx

PRESENTATION
------------
The slide deck used for the video walkthrough (with full speaker notes) is
published at: https://claude.ai/artifact/X4VHQtBGwV7WaQk8KfWQQ5

VIDEO
-----
The required face+screen video walkthrough is recorded separately by the
submitter and uploaded unlisted to YouTube/Drive, per the AICA Level 2
capstone submission format. Not included in this ZIP.
