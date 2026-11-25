# NOTICE-MATE

**A local-first workbench for organising Indian income-tax notice responses**  
ICAI AICA Level 2 Capstone · Batch 112  
**Submitted by:** CA Kritika Dubey  
**ICAI Membership No.:** 483431

NOTICE-MATE guides a CA through notice intake, document reading, issue-wise evidence mapping, reconciliation, research notes, drafting and review. It is a prototype and drafting aid; it is not an ICAI product, does not provide a final professional opinion, and does not submit anything to the Income-tax Department.

## What this project demonstrates

- A desktop-style Windows interface backed by a local application and database.
- Text extraction from PDF, Word, spreadsheets and images; scanned-PDF OCR depends on Tesseract and Poppler being installed.
- A guided case workflow with issue-wise evidence mapping, reconciliation, research notes, draft editing, approval and export.
- An optional retrieval-assisted AI drafting path. When configured, it uses relevant passages and case context; cloud requests require a redacted preview and explicit approval. No API key or model is bundled.
- Fictional examples for demonstrating the workflow. Never use the supplied fictional records as evidence for a real tax matter.

## Important current limitation

With AI disabled, the reply uses the record-based/template path. It can leave confirmation markers and may produce text that is too brief when records are not linked to a query. Do not present that output as a complete AI-generated reply. The AI path requires a separately configured model and has not been validated as a live service in this submission copy.

## Run on Windows

Requirements: Windows 10/11, Python 3.11 or newer, and internet access to install the listed Python packages. Scanned-document OCR additionally needs Tesseract OCR and Poppler.

1. Install Python and select **Add Python to PATH** in its installer.
2. In this folder, open PowerShell or Command Prompt and run:

   ```bat
   py -3.11 -m venv .venv
   .venv\Scripts\python -m pip install --upgrade pip
   .venv\Scripts\python -m pip install -r requirements.txt
   ```

3. Create your own local administrator account (the command asks you to set a password; do not share it):

   ```bat
   .venv\Scripts\python scripts\create_user.py --username YOUR_USERNAME --full-name "Your Name" --role ADMIN
   ```

4. Double-click `NOTICE-MATE.vbs` to start the app window. The first launch creates its local workspace. Closing the NOTICE-MATE window stops the app.
5. Sign in with the account you just created, then use only the fictional examples in `sample-files/` for a demo.

The app has no bundled API key. AI is off unless the operator configures a provider or a local model. See `docs/AI_PROMPT_AND_LIMITS.md` before enabling any AI provider.

`NOTICE-MATE.vbs` is a Windows launcher, not a standalone installer. Python and the dependencies above must be installed first.

## Safe demo material

- `sample-files/complex_future_faceless_test/` — fictional multi-issue notice and supporting records.
- `sample-files/single_issue_assessment_test/` — fictional single-loan example.
- `sample_data/` — fictional PQR Traders spreadsheets and notice variants.

The files are test inputs, not authentic notices or records. Names, identifiers, dates and amounts are fictional.

## Data and privacy

The app stores case files and extracted text locally in its `workspace/` directory. That runtime directory, local `.env`, generated exports and user records are deliberately not part of this capstone copy. Do not commit actual client files, database backups, API keys, passwords or screenshots containing personal information. Cloud AI, if separately configured, sends only the reviewed payload after explicit approval; verify provider terms before sending any data.

## Project materials

- `docs/PROJECT_SUMMARY.md` — problem, intended users, workflow and scope.
- `docs/AI_PROMPT_AND_LIMITS.md` — prompt design and AI safeguards.
- `docs/DEMO_RUNBOOK.md` — suggested fictional-data demonstration sequence.
- `sample-files/` and `sample_data/` — example inputs.
- `NOTICE-MATE.vbs`, `scripts/desktop_launcher.py`, and the Python source — runnable application files.

## Professional and legal notice

This is an educational prototype. A qualified professional must independently verify facts, evidence, deadlines and current law before relying on any draft. The software is not affiliated with or endorsed by ICAI or the Income-tax Department.
