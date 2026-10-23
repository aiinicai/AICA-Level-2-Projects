# Prompt log – how AI was used

Tool: Claude (Anthropic), Cowork mode. Period: 22–23 October 2026.
Each step lists the owner's instruction (summarised), what the AI produced, and the decision taken. Instructions are paraphrased from the conversation; outputs are in this repository.

| # | Owner's instruction (summary) | AI output | Decision / change by owner |
| --- | --- | --- | --- |
| 1 | Advise how to develop a task management tool for ~100 users across departments, with management review, hosted on the company server, piloted by Finance | Options compared (HTML, desktop app, Excel, web app); recommended Python/Django web app on company server; phased plan | Accepted web app approach |
| 2 | Server is Windows; in-house IT; working across two laptops through OneDrive | Windows Server hosting plan (Waitress + IIS, PostgreSQL or SQL Server, AD login); OneDrive/Git working rules; questions for IT | Accepted |
| 3 | Review existing Excel trackers (weekly payment schedule, daily task tracker) for ideas | Findings: payment planner is a multi-stage approval workflow; tracker fields; ~60 recurring reports; list of project documents | Split into two projects: company-wide task management (this repo) and a Finance-only payment planner / month-close app |
| 4 | Start with task management; also for ICAI Level 2 via GitHub; define the BRD using best practice for a manufacturing company with 10+ departments and 3–4 levels; admin configures; hierarchy-based access; HODs restricted; CEO and Finance see all; IT limited | BRD (19 sections, 3 diagrams), dummy org data (100 users, 15 units), clickable prototype | Chose fictitious company name; Claude Doc format |
| 5 | No option seen to assign a task or raise a request | "New task" and "Raise request" forms with role-based assignee lists | Accepted |
| 6 | Executives may raise tasks to peers or one level up, not further | Rule implemented; reviewer = doer's immediate senior | Extended to all levels L1–L4 |
| 7 | Allow Task or Request forms and a category dropdown | 15 categories with default form and proposed turnaround; Request closed by requester | Accepted |
| 8 | Capture the raised-on date in line items | Raised on / by in all lists and detail | Accepted |
| 9 | Should revised due dates be tracked without messy data? | Recommended: show original + current date only; revision log with reason dropdown and approver; 3rd revision needs HOD | Accepted and implemented |
| 10 | Doer column is redundant for Executives | Doer column shown only to users with reportees | Accepted |
| 11 | Test the logic on all screens and fix anything illogical | 12 issues found and fixed, incl. HOD vouching own department, CEO accepting other departments' requests, late extensions counted as on time | Accepted; open points listed |
| 12 | Count working days (6-day week, Sunday off) with an Admin-maintained company calendar; add column filters; CEO to see department-level summaries | Working-day engine and Admin "Working calendar"; filter row under column headings; Department Summary with drill-down | Accepted |
| 13 | Declines must carry a mandatory reason and be intimated; add filters on requests | Mandatory reason dialog (min. 10 characters) for decline, hold, rework, reopen, date-change rejection; request filters | Accepted |
| 14 | Dashboards for every level, not only department | My Dashboard (personal counts, breakdowns, K1/K2/K3/K5) and team section | Accepted |
| 15 | Rearrange the menu, starting with dashboards | Grouped menu: Overview → Management → Work → Administration; Team Dashboard separated | Accepted |
| 16 | Connect with GitHub | Repository folder prepared (this repo) | Owner uploads it to a private GitHub repository |

## Prompts planned for the build phase (BRD section 18)

P1 requirements check → P2 data model → P3 Django project setup → P4 hierarchy and access → P5 task lifecycle → P6 requests, recurring tasks, escalation → P7 KPI and review → P8 dashboards → P9 Windows Server deployment. The exact prompts are in `docs/BRD.md`, section 18. Each will be added here with its result as it is run.

## Human review

Every output above was reviewed by the project owner (CA and lawyer, Head – Finance & Legal). Policy items marked "proposed" in the BRD (KPI weights, escalation days, turnaround times) still need management approval.
