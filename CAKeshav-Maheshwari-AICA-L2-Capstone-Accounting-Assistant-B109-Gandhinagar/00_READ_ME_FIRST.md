# READ ME FIRST — AICA Level 2 Capstone Project

**Participant:** CA Keshav Maheshwari, FCA (M. No. 159754), Maheshwari Keshav & Co., Ahmedabad\
**Course:** Certificate Course on AI for Chartered Accountants (AICA) — Level 2\
**Project:** Accounting Assistant for TallyPrime (v10)\
**Video link:** https://drive.google.com/drive/folders/1JPwGl8h6Zh-KefnrXyXTWG6FYehqyxFZ\

An offline yet intelligent Windows desktop app that sits beside TallyPrime. It learns from past entries and corrections, so a bank line or invoice handled before gets the same ledger automatically. It reads supplier invoices (optionally with Google Gemini, after masking), turns bank and credit-card statements into Tally entries by rules alone (banking never goes to AI — blocked in code), and checks the books for TDS / GST compliance gaps and red flags. Every entry is reviewed before it is posted.

## Contents of this ZIP

| Folder | What is inside |
| --- | --- |
| 01_Project_Summary_Document | The Project Summary Document (PDF and Word): problem, architecture, features, AICA learning applied, technology, libraries, security, testing, installation, limitations |
| 02_Prompt_Files | `01_Gemini_Invoice_Extraction_Prompt.md` — the AI prompt, model settings, self-check prompt and JSON schema used inside the app; `02_Gemini_Response_Schema.json`; `03_Development_Prompts.md` — the key prompts used to build the app with an AI coding agent |
| 03_Example_Files | `Aarohan_Infotech_Demo_Data` — a complete fictional company: Tally masters and 394 vouchers to import, 6 bank / card statements, 21 supplier invoices with planted errors, employee claims, GSTR-2B, the answer key (`6_Expected_Results`), a test guide and a 53-scenario checklist |
| 04_Executable_Files | `Accounting_Assistant_v10` — the application (source and one-click installer `Setup or update.bat`) |
| 05_Supporting_Documents | Master specification, automated test report (146 tests passing), screenshots, video script and storyboard |

## How to run (about 10 minutes)

1. **Requirements:** Windows 10 / 11, TallyPrime 4.x or later with XML server on port 9000 (F1 > Settings > Connectivity > Client/Server: *Both*, port 9000). Internet only for the first install.
2. Open `04_Executable_Files\Accounting_Assistant_v10` and double-click **`Setup or update.bat`**. It installs the official Python if missing, installs the libraries and creates the *Accounting Assistant* desktop icon. (If Windows says the file is blocked: right-click the ZIP > Properties > Unblock, then unzip again.)
3. In TallyPrime create **Aarohan Infotech Private Limited** — Gujarat, books from 01-04-2026, GSTIN 24AAHCA4821K1ZR, inventory on, **integrate accounts with inventory on**, bill-wise on. Import `03_Example_Files\Aarohan_Infotech_Demo_Data\1_Tally_Import` — masters first, then vouchers.
4. Start the app from the desktop icon. In the Setup wizard: test the Tally connection, tick the company, Sync, set the invoice folder to `3_Purchase_Invoices_Nov2026`.
5. Follow `00_READ_ME_FIRST_Test_Guide.docx` and `Test_Scenarios_Checklist.xlsx` in the demo data.

**No Gemini key is included.** Every module works without one; invoices are then read offline. A key can be added (and removed) in Setup.

**Why there is no .exe:** Windows Smart App Control blocks unsigned executables, so the app runs on the official, Microsoft-trusted Python through a desktop shortcut. A signed single-file installer is listed under future scope.

## Data note

All data in this submission is fictional. No real client data, credentials or API keys are included.
