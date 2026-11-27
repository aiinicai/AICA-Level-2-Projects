# Final build prompt (as given to Claude)

Act as a senior Python developer. Build the system below for a user who is a **Chartered Accountant, not a programmer**.

## 1. Purpose and scope

Build a web tracker that follows audit findings from each department until Internal Audit verifies closure. The audit team records findings, department owners respond, and a dashboard shows ageing and closure.

- Language and framework: Python with Streamlit.
- Scale: 14 departments, 28 department users, and about 30 to 50 findings per department (roughly 420 to 700 in total).
- Two variants share one codebase: a Gmail test version and a Microsoft 365 intranet version. Only the database, email and login settings differ.

## 2. Users and permissions

Department owners may edit only their management status, management response and revised target date. Everything else is sealed and entered by the audit team.

The 14 departments are Branch 1, Branch 2, Branch 3, Branch 4, Branch 5, Compliance, Recovery and Legal, Finance, HR, AQM, Marketing, IT, Risk, Credit and Corporate. Each has two users named after it, such as Credit 1 and Credit 2, or Risk 1 and Risk 2 (28 in total).

| Role | Who | Can do |
| --- | --- | --- |
| Audit Admin | Internal Audit team | Add and edit every field, import findings from Excel, set auditor status and remarks, close findings, open follow-up rounds, manage users |
| Department Owner | The two users of one department | See only their own department's findings. Edit only management status, management response and revised target date in the open round |
| Management | Senior management | View all findings and the dashboard. No editing |

- The original target date is locked after import. Each revised target date is saved with its date and the user who set it.
- Every change goes to an audit trail (who, when, old value, new value). Nothing is deleted.
- Login is by username and password with hashed passwords in the test variant, and company sign-in in production.
- Also create one Audit Admin test user and one Management test user.

## 3. Data model

Keep one record per finding and one record per finding per follow-up round, so the number of rounds is unlimited.

**Findings master** (entered by the audit team, imported from Excel, 14 columns in this order): Serial number, Year reported, In-house or external auditor, Quarter, Report name, Department, Observation (treated as the observation reference number), Heading of the observation, Detailed observation, Risk implication, Recommendation, Management response (initial), Risk level (High, Medium, Low), Original target date. Add a system ID for each finding.

**Follow-up record** (one per finding per round):

| Field | Edited by |
| --- | --- |
| Follow-up date | Audit team |
| Response due date | Audit team |
| Management status (Open, Ongoing, Closed) | Department owner |
| Management response as on that date | Department owner |
| Revised target date | Department owner |
| Auditor status (Open, Ongoing, Closed) | Audit team |
| Auditor remarks | Audit team |
| Evidence file | Attached with the management response |

**Status definitions** (the same three apply to management and to the auditor):

| Status | Definition |
| --- | --- |
| Open | No action has started, or no response was received by the follow-up date |
| Ongoing | Implementation has started or is partly done, with a revised date, but is not yet fully in place |
| Closed | The recommendation is fully implemented and evidence is on file. For the auditor status, Internal Audit has also verified it |

- A finding's current status is the auditor status in its latest round. The management status is shown beside it and never replaces it.
- Flag every finding where management says Closed and the auditor does not.
- Excel export also offers a wide layout: for each follow-up date, a block of Date, Management status, Management response and Auditor status.

## 4. Follow-up cycle and emails

Findings are followed up quarterly, and monthly while a High-risk finding is not yet Closed.

1. The Audit Admin opens a round by choosing the follow-up date and the response due date. A quarterly round includes all unclosed findings. A monthly round includes only unclosed High-risk findings.
2. The system emails the two users of each department a list of their pending findings, with a link to the tracker.
3. Department owners update their items before the response due date.
4. If a finding still has no update 7 days after the response due date, send one reminder email to both department users, copying the audit team.
5. The audit team reviews each response, sets the auditor status and remarks, and may close the finding.

Findings the auditor has Closed drop out of later rounds. Log every email sent (recipient, time, success or failure).

Open item: escalation to department heads after a missed reminder is not yet decided. Build it as a setting that is switched off by default.

## 5. Dashboard

The dashboard shows ageing and closure at a glance, always counted on the auditor status.

- Summary tiles: total findings, Open, Ongoing, Closed, overdue, and closure rate.
- Ageing of unclosed findings by days past the original target date: not yet due, 1 to 30, 31 to 60, 61 to 90, and over 90. A second view uses the latest revised target date so extensions are visible.
- Breakdowns by department, risk level, in-house vs external, and year reported.
- Open vs closed by follow-up round.
- A list of disagreements, where management says Closed and the auditor does not.
- Filters for department, risk, year, quarter and status, with Excel export of any view.
- Department owners see the same dashboard limited to their own department.

## 6. Sample test data

Seed the test version with dummy data so every screen can be tried before real findings are imported.

- Create 30 to 50 invented findings for each of the 14 departments, with mixed risk levels, years, and in-house and external sources.
- Spread the target dates so every ageing bucket has items.
- Give many findings two to four follow-up rounds, including some where management says Closed and the auditor disagrees.
- Make all text obviously fake. The admin gets a button to wipe sample data before the real import.
- Real import: the audit team uploads the Excel file, the system checks the 14 column names, reports row errors, and refuses duplicate serial numbers.

## 7. Variant A: Gmail test version

Build this first and test it on dummy data only, because it runs online.

- Hosting: Streamlit Community Cloud, or the user's own computer.
- Database: Supabase (hosted Postgres), so data survives restarts. Keys go in the app's secrets settings, never in the code.
- Email: Gmail SMTP using an app password from a test Gmail account.
- Scheduling: an admin button "Send reminders now", plus an optional daily scheduled job that calls the same function.
- Login: username and password, stored hashed.
- Evidence files: stored in Supabase storage.

## 8. Variant B: Microsoft 365 intranet version

Build this after IT clears the test version. It should need only settings changes, not new code.

- Hosting: the same Streamlit app on an internal server, reached through an intranet link. IT supplies the server, port and HTTPS.
- Database: SQLite to start, or SQL Server or PostgreSQL if IT prefers. The tables stay the same.
- Email: Microsoft Graph sending from a shared mailbox set up by IT, or the company SMTP relay. One setting chooses between them.
- Login: company sign-in through Microsoft Entra ID, arranged with IT, with username and password as a fallback.
- Scheduling: Windows Task Scheduler runs the daily reminder script.
- Evidence files: an internal shared folder.
- Also provide a short checklist of what to ask IT for.

## 9. How to deliver

The user is a Chartered Accountant, not a programmer, so give complete working code and plain instructions.

1. One main Python file (app.py), a requirements.txt, and one sample-data script only if needed. No other files unless unavoidable.
2. Numbered setup steps with exact commands and what to click, and every setting explained in plain words.
3. Build Variant A first. Make Variant B by changing settings, not code.
4. State any assumption before coding, instead of asking about details already given here.
5. End with a test checklist covering login by role, edit limits, a reminder email, the dashboard, and Excel import and export.
