# Audit Findings Tracker

**AICA Level 2 Capstone Project** | Author: *<SHALABH AGRAWAL, CA>* | 

A web tracker that follows up outstanding **internal and external audit findings** across 14 departments until Internal Audit verifies that they are closed. The audit team records the findings, department owners respond every quarter (every month for High-risk items), and a dashboard shows ageing, open vs closed, and where management and the auditor disagree.

Built with Python and Streamlit, with the help of Claude (see `01_Prompt`).

> **All data in this project is dummy data** marked `[SAMPLE]`. No real audit, client or personal information is included.

## Video demonstration

Video link (YouTube unlisted / Google Drive): https://drive.google.com/file/d/1SfricPTOQ4wjsWigUYnkxIfH1JasoNAK/view?usp=drive_link

## What the system does

| Area | What it does |
| --- | --- |
| Findings register | Imports the audit team's Excel file (14 agreed columns). Add and edit findings. Duplicate serial numbers and bad rows are rejected with a clear message. |
| Roles | **Audit Admin** (everything), **Department Owner** (2 users for each of the 14 departments; can edit only management status, management response and revised target date for their own department), **Management** (view only). |
| Follow-up rounds | Quarterly for all unclosed findings; monthly for unclosed High-risk findings. Each round creates one record per finding with: date, management status, management response, revised target date, **auditor status** and auditor remarks. |
| Status definitions | **Open**: no action started or no response. **Ongoing**: started or partly done, not fully in place. **Closed**: fully implemented with evidence (for the auditor: also verified). |
| Auditor vs management | The auditor's status is the official one. Findings where management says *Closed* but the auditor does not are listed separately. |
| E-mail | Round-opening e-mail to each department's two users. **Reminder 7 days after the response due date** (copy to the audit team). Optional escalation to the department head (off by default). Works in 4 modes: log only, Gmail, any SMTP, Microsoft 365 (Graph). |
| Dashboard | Totals, closure rate, ageing (not yet due, 1-30, 31-60, 61-90, over 90 days) against the original and the revised target date, breakdown by department / risk / source / year, trend by round, Excel export. |
| Control | Original target date is sealed. Every change is saved in an audit trail (who, when, old value, new value). Passwords are stored hashed. |

## Folder contents

| Folder | Contents |
| --- | --- |
| `01_Prompt` | The final build prompt given to Claude, and the log of how the prompt was developed |
| `02_System_Design` | System design: data model, roles, workflow, status and ageing rules, the two variants |
| `03_Code` | `app.py` (the whole application), `requirements.txt`, settings example, automatic tests |
| `04_Test_Data` | Dummy Excel files for the import test, test users, and the script that creates them |
| `05_Test_Plan_and_Evidence` | Test plan, automatic test results, and screenshots |

## How to run it (Windows, step by step)

1. Install Python 3.10 or later from python.org. During installation, **tick "Add Python to PATH"**.
2. Open **Command Prompt**. Go to the code folder, for example:
   `cd C:\Users\YourName\Downloads\AICA-L2-Audit-Findings-Tracker\03_Code`
3. Install the needed packages (once): `pip install -r requirements.txt`
4. Start the app: `streamlit run app.py`
5. Your browser opens at `http://localhost:8501`.
6. Sign in as **Audit Admin**, password **Test@123** (dummy password for the dummy test users).
7. Open **Import and sample data** and click **Load sample data** (584 dummy findings, 3 past rounds, 1 current round).

Test users: `Audit Admin`, `Management`, and two users for every department: `Credit 1`, `Credit 2`, `Risk 1`, `Risk 2`, `Branch 1 1`, `Branch 1 2`, ..., `Compliance, Recovery and Legal 1`, `Compliance, Recovery and Legal 2`, and so on (all in `04_Test_Data/sample_users.csv`).

The app creates a small database file `audit_tracker.db` next to `app.py` the first time it runs. Delete that file to start again from nothing.

## How to test it

* **Automatic tests (15):** in the `03_Code` folder run `python tests/test_core.py`. All should print `PASS`. Result of the last run: `05_Test_Plan_and_Evidence/automatic_test_results.txt`.
* **Screen-by-screen tests:** follow `05_Test_Plan_and_Evidence/test_plan.md` using the files in `04_Test_Data`.

## The two variants (same code, different settings)

| | Variant A: Gmail test | Variant B: Microsoft 365 intranet |
| --- | --- | --- |
| Where it runs | Own computer, or Streamlit Community Cloud | Internal server, opened by an intranet link |
| Database | Local SQLite file, or **Supabase** (set `DATABASE_URL`) | SQLite, or SQL Server / PostgreSQL chosen by IT |
| E-mail | `EMAIL_MODE=gmail` with a Gmail app password | `EMAIL_MODE=graph` (Microsoft Graph) or `smtp` (company relay) |
| Sign-in | User name and password inside the app | Same now; company single sign-in later, arranged with IT |

All settings are in `03_Code/secrets.toml.example`. To use them, open Command Prompt in the `03_Code` folder and run:

```
mkdir .streamlit
copy secrets.toml.example .streamlit\secrets.toml
```

Then open `.streamlit\secrets.toml` in Notepad, remove the `#` in front of the lines you need and fill them in. Restart the app. **Never upload `secrets.toml`.** (Without this file the app simply runs with safe defaults: local database, e-mail only logged.)

## Verified and not yet verified

* Verified: the application logic (login, permissions, import checks, rounds, ageing, 7-day reminder rule, e-mail logging, exports, sample data) by 15 automatic tests, and every screen opens and runs with the dummy data.
* To be verified by the user on their own computer: the look of the Streamlit screens, a real Gmail send, a real Supabase connection. Microsoft 365 / Graph sending needs IT clearance and is written but not yet tried.

## Known limits of this version

* Evidence files are stored inside the database (up to 5 MB each).
* The reminder and escalation e-mails go out when the Audit Admin clicks **Send reminders now**. A daily automatic run needs a scheduled task (Windows Task Scheduler or similar), to be set up with IT for Variant B.
* Single sign-in with company accounts (Microsoft Entra ID) is planned for Variant B, not built.
