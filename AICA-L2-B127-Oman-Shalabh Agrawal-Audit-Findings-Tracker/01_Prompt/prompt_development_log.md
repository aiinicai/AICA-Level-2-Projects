# How the prompt was developed

The final prompt (`final_build_prompt.md`) was not written in one go. It was built step by step in a conversation with Claude, first by brainstorming, then by fixing the data layout and rules. This log shows the steps.

## Step 1: The idea and the brainstorm

The requirement as first stated: develop audit tracking software, in Python, to follow up outstanding internal audit findings of various departments; send emails through Microsoft Outlook; show a dashboard with ageing analysis of outstanding and closed items; and let users enter a response every month on a date when the system triggers the request automatically.

Claude was asked only to suggest the key elements before anything was built. Result: findings register, monthly response cycle, ageing dashboard, roles, audit trail, Outlook e-mail options, and the technology choice (Python with Streamlit).

## Step 2: The input format and the status logic

The user fixed the Excel input with 14 columns (Serial number, Year reported, In-house or external auditor, Quarter, Report name, Department, Observation, Heading of the observation, Detailed observation, Risk implication, Recommendation, Management response, Risk level, Original target date).

Rules added at this step:

* For every follow-up date keep three fields: **status of the observation, management response as on that date, and the date itself.**
* Add one more column for the **auditor's own judgment** (Open / Closed / Ongoing), separate from management's.
* Write clear definitions of **Open, Closed and Ongoing**.

Claude proposed the definitions and a two-table design (findings master, one follow-up record per finding per round) with the current status always taken from the auditor.

## Step 3: Permissions, frequency and two variants

* Department owners enter updates; **only the management update and the target date are editable by them**; everything else is sealed and entered by the audit team.
* Follow-up **quarterly, and monthly for High-risk items**.
* Email system will be **Microsoft 365**, but testing will be on **Gmail**, so two variants were requested: (1) Microsoft 365 on the intranet, (2) Gmail test without intranet deployment, using Streamlit with a hosted database such as Supabase.

Claude recommended one codebase with swappable database and e-mail settings, so moving from test to intranet needs only a settings change.

## Step 4: Departments, users, reminders, volume

* 14 departments: Branch 1 to Branch 5, Compliance, Recovery and Legal, Finance, HR, AQM, Marketing, IT, Risk, Credit, Corporate.
* Two users per department, named after the department plus 1 and 2 (for example Credit 1, Credit 2).
* **Reminder e-mail one week after the response due date.**
* About 30 to 50 findings per department, which became the volume for the sample test data.

## Step 5: The prompt was written up

Claude consolidated all decisions into the final prompt, organised in nine sections: purpose, users and permissions, data model, follow-up cycle and e-mails, dashboard, sample test data, Variant A, Variant B, and delivery rules. Choices Claude made on its own, flagged for the user to confirm:

* "Observation" column treated as the observation reference number.
* Evidence attachment added (not in the original brief), attached together with the management response.
* Escalation to department heads left as a switch that is off by default, because the user had not decided it.

## Step 6: From prompt to working code

The final prompt was then used to build `app.py`, the test data and the tests in this folder. Differences between the prompt and the delivered code are listed in `02_System_Design/system_design.md` (section "Where the build differs from the prompt").
