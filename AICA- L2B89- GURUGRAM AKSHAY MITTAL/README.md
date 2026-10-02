# BRMCo Accounting Hub: AICA Level 2 Capstone Project

**Participant:** CA Akshay Mittal, B R Maheswari & Co LLP
**Course:** AI for Chartered Accountants (AICA), Level 2
**Project:** an AI-built **Excel-to-Tally Accounting Automation Tool**

## What it does

In most CA offices, clients send sales, purchase and bank data in Excel, and staff re-type it into Tally voucher by voucher. BRMCo Accounting Hub removes that re-typing:

1. **Download a template.** A structured Excel template, with drop-downs of your real Tally ledgers.
2. **Upload the filled file.** Every entry is checked automatically:
   - dates within the financial year
   - ledgers exist in Tally
   - GSTIN format and checksum
   - CGST+SGST versus IGST
   - tax equals taxable value × rate
   - invoice totals
   - Debit = Credit
   - duplicates

   Problems are reported **by row and column in plain English**.
3. **Preview.** Each voucher is shown as a Dr/Cr entry. Nothing is posted until a person confirms.
4. **Post to TallyPrime.** One click. Tally's own reply is shown for every voucher.
5. **Import History and Audit Log** record every step.

It covers **Sales, Purchase, Journal, Bank Receipt and Bank Payment** vouchers. It also offers reviewed **ledger creation** in Tally and a **Demo Mode** that simulates Tally, so it can be tried safely.

## How it was built

The application was built through **prompt-driven development with an AI coding assistant** (Claude by Anthropic). A 37-section master prompt set out the role, scope, accounting rules, architecture and constraints. The application was then refined over several iterations based on testing against a live TallyPrime. The prompts are in [`02_Prompt_Files`](02_Prompt_Files).

**Technology:** Python (FastAPI), HTML/JavaScript, SQLite, openpyxl, TallyPrime XML interface.
**Quality:** 65 automated tests pass. See [`05_Supporting_Documents/05_Automated_Test_Results.txt`](05_Supporting_Documents/05_Automated_Test_Results.txt).

## Folder guide

| Folder | Contents |
|---|---|
| [`01_Project_Summary`](01_Project_Summary) | Project Summary Document (Word) |
| [`02_Prompt_Files`](02_Prompt_Files) | Master build prompt, and a log of the iterative prompts |
| [`03_Example_Files`](03_Example_Files) | Blank templates, sample Excel inputs, generated Tally XML, and a worked-example walkthrough |
| [`04_Executable_Files`](04_Executable_Files) | Full source code with one-click launchers (`start_local.bat`) and `00_HOW_TO_RUN.txt` |
| [`05_Supporting_Documents`](05_Supporting_Documents) | Architecture, API reference, user guides, test results, presentation script |

## Quick start

1. Install **Python 3.12** from python.org, and tick *Add python.exe to PATH*.
2. Copy `04_Executable_Files` to a short path, for example `C:\BRMCo`.
3. Double-click `brmco-accounting-local\start_local.bat`.

The browser opens **http://127.0.0.1:8000** in Demo Mode, and nothing is posted to Tally. Open **Sales → Download filled sample → Upload & Validate → Confirm & Post**.

*All data in this repository is illustrative sample data. No client data is included.*
