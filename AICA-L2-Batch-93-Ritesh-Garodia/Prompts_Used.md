# AI Prompts Used — Compliance Tracker Capstone Project

This project was built conversationally with Claude (Anthropic), inside the
Claude Code / Cowork environment, using its file, spreadsheet, PDF and n8n
workflow-building tools. Below are the prompts (in order) that shaped the
build, condensed to their operative content.

## 1. Initial project brief
> "GST due date, income tax due date, TDS due date, and all labor code due
> date have to be picked up from the file. Second, from those files, an
> email will go to the respective user two days in advance. Third, if the
> user does not pay the tax and key in the amount in the Excel file, the
> second reminder will go one day in advance to the user with CC to his or
> her supervisor. Fourth, if the user again does not do the same, a third
> and final reminder will go on the final date to the user, his supervisor,
> and the head of department. Fifth, this reminder will go every day till
> the time the user key in the amount and mark the task as completed... the
> frequency of the mail will depend upon the periodicity of the task...
> Also, a dashboard would be prepared for the head of the function... At the
> end of the month, a PDF report would be generated... There would be
> another file, a trial balance, which will be uploaded by the user. The
> actual payment should be compared to the balance in the trial balance...
> and difference, if any, should be reported as a variance."

This single prompt defined the full scope: due-date extraction, 3-stage
escalation, department-scoped dashboard, month-end PDF report, and
trial-balance variance check.

## 2. Clarifying questions (asked by Claude, answered by the user)
- Technology stack → **Python + Excel**, with the automation piece later
  changed to **n8n** (see prompt 4).
- Dashboard access model → **Streamlit web app**, later simplified to a
  **view toggle** for the demo (see prompt 7).
- Email delivery → **SMTP**, later rebuilt as an **n8n Gmail node** workflow.
- Source due-date file → user attached `Compliance Tracker.xlsx` (Direct Tax
  + GST sections) via the linked-computer folder.
- Labour Code / Payroll list (missing from the source file) → *"add to list
  as per [the standard set]... include LWF code also. make it like i can
  keep on adding list in future"* → built as an extensible **Task
  Templates** sheet.

## 3. ICAI capstone fit check
> "Will it also involve workflow?" / "Will it qualify as ICAI A1 level 2
> capstone?"

Prompted Claude to research the actual AICA Level 2 capstone rubric (via web
search) and map the deliverables onto ICAI's stated requirements (project
summary, prompts, examples, executables, video walkthrough).

## 4. Switch to n8n for the automation
> "n8n visual workflow" (chosen over a Python script) — *"Build the actual
> automation as a visual drag-and-drop n8n workflow... easier to demo and
> explain in a capstone presentation."*

## 5. PPT for the video walkthrough
> "Once u make the project, I can record the video. You share me PPT for me
> to explain steps." / "It also ask me to upload the project on YouTube or
> git hub. Will you be able to do" → clarified Claude builds the deck and
> can push code to GitHub, but cannot record the video itself.

## 6. Privacy constraint on published data
> "Since i wd be publishing the file. i dont want to put real person other
> than me. i will add my two email id only" → *"yes and for user use
> riteshgarodia@yahoo.com"* (Supervisor/HOD = garodia1.ritesh@gmail.com).

This drove a rebuild of the Users / Task Templates / Task Instances sheets
and the n8n workflow's sample data to use only the two real, owned email
addresses — no third-party names or emails anywhere in the published file.

## 7. Save-to-folder + dashboard login simplification
> "also save all file in that folder only" → every deliverable written back
> to the user's linked `Capstone Project` folder via the device bridge, in
> addition to being sent in-chat.
> "go for [a simple view toggle] now, but pls mention in PPT that on live
> deployment will use email based login for authorization" → dashboard built
> with a View selector (User / HOD), documented as a stand-in for real
> email-based login.

## 8. Live multi-user data source
> "where will user key in the details.. will google sheet in my pc and
> accessible to all users" → identified that the local Excel file and the
> Google Sheet n8n reads were two disconnected copies, with nowhere
> consistent for multi-user data entry.
> "yes pls do" → made the Google Sheet the single live source of truth:
> edit access via Google Sheets' own Share/Editor permissions (restricted
> to specific invited users), and the dashboard reading a separate
> "Publish to web" read-only CSV link, so viewing needs no login.

## 9. Dashboard usability — reports on demand
> "in dashboard there is no button to download the report" / "instead of
> uploading by user, let it pick from google sheet" → added one-click
> "Download PDF report" (month-end report) and "Download Variance Report"
> buttons to the dashboard sidebar, both built from the live Google Sheet
> data instead of requiring a separate script run or a manual file upload.

## Build prompts issued internally (by Claude, to its own tools)
- xlsx-skill-guided Python/openpyxl script generating the 6-sheet
  `Compliance_Master.xlsx` (ReadMe, Task Templates, Users, Task Instances,
  Trial Balance, Variance Report), with a due-date-pattern mini-language so
  new compliance types can be added without code changes.
- n8n Workflow SDK code (validated via `validate_workflow`, deployed via
  `create_workflow_from_code`) for the 9-node "Compliance Reminder &
  Escalation Workflow".
- reportlab-based `generate_monthly_report.py` for the month-end PDF.
- pandas-based `generate_variance_report.py` for the GL-wise trial balance
  comparison.
- Streamlit `dashboard.py` for the Due/Completed/Overdue view.
- Slides-type Artifact deck (`Compliance Tracker Capstone Walkthrough`) with
  full speaker notes, generated as the presentation for this video.
