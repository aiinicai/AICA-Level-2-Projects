# Bank Advances Audit and Exception Review Assistant

**Participant:** [Enter name]  
**Batch:** [Enter batch]  
**Course:** ICAI AICA Level 2  
**Version:** 1.0 - educational prototype

## Purpose
Prepare evidence-linked advances working papers: recalculate drawing power, review
historical account conduct, age unpaid scheduled dues, inspect sanction/document
exceptions and organize proposed observations. Optional AI drafts from a selected evidence
pack; the auditor retains classification, reporting and final approval responsibilities.

## Features
| Capability | Professional review value |
|---|---|
| Drawing-power bridge | Eligibility, creditor treatment, margins and sanction cap |
| CC/OD conduct | Historical daily effective limits and explicit calendar coverage |
| Repayment review | Age unpaid principal/interest allocations; exclude future dues |
| Borrower follow-up | Link supplied facilities without overwriting bank classification |
| Documents and sanctions | Missing/expired checklist items and review-date exceptions |
| Structured findings | Preserve condition, branch response, evidence and auditor conclusion |
| Account coverage | Require review even when no exception is generated |
| Closing reports | Distinct-account exposure and unresolved/reporting items |
| Optional AI | Exact prompt preview and unapproved observation drafts |

## Windows setup
1. Extract the ZIP completely into a new folder.
2. Open Bank_Advances_Audit; double-click install.bat.
3. Double-click run.bat.
4. Audit setup -> Load fictional demo files -> Run audit.

Python 3.10+ required; internet needed for initial dependency installation.
The installer includes ensurepip to repair missing pip. If needed, run in Command Prompt
from the project folder:

```bat
python -m venv .venv
.venv\Scripts\python.exe -m ensurepip --upgrade
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

Use your working python command. In VS Code select .venv\Scripts\python.exe.

## Demo controls
Audit date 2026-09-30; eight fictional facilities, seven borrowers, 390 daily rows.
Baseline: **18 findings**, outstanding **INR 4,650,000**, six high-priority accounts with
unique-account exposure **INR 3,550,000**, and one incomplete-history account.
These are test cases, not actual borrower risk determinations.
CC001 demonstrates DP of 705,000 before-margin creditor deduction versus 655,000 after
margin. CC002 compares bank DP 900,000 against historical recomputation 705,000.
CC003 triggers continuous excess; CC004 has only 30/90 daily dates, preventing full-window
clean conclusions. Follow [USER_GUIDE.md](USER_GUIDE.md) for the complete demonstration.

## Inputs and assumptions
Five CSV/XLSX files: accounts, daily, stocks, dues, documents. Use supplied templates;
XLSX uses first-sheet headings in row 1 and values, not formulas. One branch per run.
Scope: CC, stock-backed OD and TL. Native CBS import is not implemented.
The editable audit_policy.json contains illustrative screening criteria, not a maintained
RBI rules database. Read docs/METHOD.md before any professional interpretation.
No automatic NPA/SMA assignment, provisioning, fraud detection or audit opinion is provided.
Referenced documents and management assertions are not authenticated.

## Optional AI
Select a finding in AI drafting, preview its prompt, and either export it for manual use
in an authorized AI tool or request an in-app draft with your own OpenAI API key/model.
Separate API access/billing is needed. Keys are not saved. Financial data remains in
prompts, so review the contents before sharing. Drafts cannot approve findings.
The audit engine works locally without AI access. Its arithmetic/screens are rule-based.
The optional API path was tested with mock responses only; no live request was made.

## Validation
```bat
.venv\Scripts\python.exe -m unittest -v
.venv\Scripts\python.exe reproduce_demo.py
```
See docs/TEST_RESULTS.md for actual checks and remaining verification. Windows GUI and
live API need participant verification. No real-bank-data performance claims are made.

## Files and submission
- audit_engine.py: validation, calculations, screens, reviews and sessions.
- app.py: desktop workflow; reports.py: Excel/HTML/CSV exports.
- ai_review.py: optional API draft integration; test_audit.py: behavioural tests.
- sample_data/: fictional inputs and blank templates.
- example_output/: example working papers, prompt and report.

Replace name/batch here and in docs/PROJECT_SUMMARY.md. Copy the project under your
submission folder, excluding .venv, __pycache__, credentials and actual bank/customer
records. Keep source/subfolders together; recreate .venv after moving a working install.
Use the instructor's fork/pull-request procedure. Acceptance depends on their rubric.
