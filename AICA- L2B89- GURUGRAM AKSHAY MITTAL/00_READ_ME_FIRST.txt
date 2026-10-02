AICA LEVEL 2 - CAPSTONE PROJECT
BRMCo Accounting Hub - an AI-built Excel-to-Tally Accounting Automation Tool
Participant: CA Akshay Mittal, B R Maheswari & Co LLP
=============================================================================

WHAT THIS PROJECT IS
Client data prepared in Excel (sales, purchases, journals, bank receipts and
payments) is checked automatically for dates, ledgers, GST rules, arithmetic,
debit = credit and duplicates. It is shown as accounting entries for approval,
then posted directly into TallyPrime, with a full history and audit log.
Built through prompt-driven development with an AI coding assistant.

CONTENTS
01_Project_Summary\        Project Summary Document (Word) - start here
02_Prompt_Files\           01 Master build prompt
                           02 Iterative prompts log and prompting techniques used
03_Example_Files\          00 Worked-example walkthrough
                           A  Blank Excel templates (5)
                           B  Sample input Excel files (5)
                           C  Tally XML generated from the samples (5)
04_Executable_Files\       00_HOW_TO_RUN.txt
                           brmco-accounting-local\  main application + start_local.bat
                           brmco-accounting-server\ server component + start_server.bat
05_Supporting_Documents\   01 Architecture and design
                           02 API reference
                           03 User guide (Local Host)
                           04 Server Host guide
                           05 Automated test results (65 tests passed)
                           06 Presentation script (5 minutes)
                           07 Video recording checklist

QUICK START
Install Python 3.12 (python.org, tick "Add to PATH"), extract this ZIP to C:\BRMCo,
then double-click:
  04_Executable_Files\brmco-accounting-local\start_local.bat
The browser opens http://127.0.0.1:8000 in Demo Mode (nothing is posted to Tally).

PROJECT VIDEO: submitted separately via the ICAI Google Form (link in the Project Summary).
