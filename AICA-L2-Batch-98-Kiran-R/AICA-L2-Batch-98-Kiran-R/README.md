# EditLog Auditor

**ICAI AI Certificate Course Level 2, Batch 98 (Ernakulam), capstone project by CA Kiran R.**

*Did the audit trail really run all year?* A tool for reporting under Rule 11(g) of the Companies (Audit and Auditors) Rules, 2014, on TallyPrime books.

## The problem
From FY 2023-24 the company's accounting software must keep an edit log (audit trail) of every change, operating all year and not capable of being disabled (Rule 3(1) proviso, Companies (Accounts) Rules, 2014). The statutory auditor reports on it under Rule 11(g). TallyPrime shows the Edit Log only as a screen report, one voucher type and month at a time, and there is no standard working paper, so evidence differs from file to file.

## The solution
A local Streamlit app that runs on the same PC as TallyPrime, with six tabs:

1. **Settings**: company, year, books-finalised date, auditor name, thresholds.
2. **Input**: pulls vouchers from the open Tally company, then presses Tally's own Edit Log Summary keys and checks each export.
3. **Edit Log Findings**: ten tests (logging gaps, back-dating, deletions, generic user IDs and more).
4. **Guided audit**: ICAI Implementation Guide steps and 12 controls; every answer is a suggestion that counts only after the auditor confirms it, with a working paper behind each control.
5. **Reports**: Annexure A, draft Rule 11(g) wording and a suggested opinion, working papers, management representation letter.
6. **History**: save every check and reopen any company with its whole workspace.

## How it was built with AI
An AI coding assistant wrote the program. The author supplied the domain: the Rule 11(g) requirements from the ICAI Implementation Guide (Revised 2024), real Tally screens and export files, and tested each version, so every error became the next iteration. Automated checks run after every change.

## Guardrails
- Reads Tally and never changes it; never types a user name or password (the user logs in).
- Suggestions count only after the auditor confirms them.
- Every finding traces back to an Edit Log row in Annexure A.
- The opinion and the report stay the auditor's own judgement.
- This repository holds **dummy data only**; no client data.

## How to install (Windows, same PC as TallyPrime)
1. Download and unzip `EditLogAuditor_Setup.zip`.
2. Double-click `INSTALL.bat` (internet needed; Python is set up for you).
3. Open **EditLog Auditor** from the desktop icon. Open the company in Tally and log in yourself.

Try it without Tally: choose the **Sample data** option on the Input tab (files in `source/data`).

## Limits
- The Edit Log extraction presses Tally's keys, so it depends on Tally's screen layout.
- Tried on a small number of files so far; more testing is needed.
- Field-level old and new values need a sample from Tally's Differences screen.
- The tool prepares evidence and suggestions; the auditor decides.

## Contents
| Path | What it is |
| --- | --- |
| `EditLogAuditor_Setup.zip` | double-click installer package |
| `source/` | the app source code and dummy sample data |
| `docs/EditLog_Auditor_Slides.pdf` | capstone slides |
| `docs/Demo_Run_Sheet.md` | demo script |

## Notices
Tally and TallyPrime are trademarks of their respective owners. This project is independent and not affiliated with or endorsed by them. Not professional advice; the auditor remains responsible for the audit report.
