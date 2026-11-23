# Prompts used in FirmFlow

## 1. Build prompt (AI-assisted development)

The first version was generated from this prompt and then improved through follow-up prompts.

> Build a single-file installable web app (HTML, CSS, JavaScript, PWA with manifest and service worker) called **FirmFlow** for an Indian Chartered Accountant firm. Use a navy and gold design, mobile first, with a bottom navigation bar: Home, Timer, Tasks, Clients, Reports.
>
> - **Home:** greeting, today's worked time against a daily goal shown as a progress ring, daily streak (days with at least 30 minutes logged), line of the day, due-soon task list with overdue tags, a "Plan my day" AI button and a quick-log box that understands plain text like "2.5h GSTR-3B for Sharma Traders".
> - **Timer:** pick client and task, start, pause and stop, billable checkbox, optional 50-minute focus block with a browser notification, today's entries, manual entry.
> - **Clients:** name, constitution, PAN and GSTIN with format validation (the PAN inside the GSTIN must match the PAN), monthly fee, engagement in charge, and services (GST monthly, TDS, ITR, tax audit, advance tax, ROC). When a client is saved, create statutory due-date tasks for the next 90 days: GSTR-1 on the 11th, GSTR-3B on the 20th, TDS payment on the 7th (30 April for March), quarterly TDS returns, advance tax instalments, ITR (31 July, or 31 October for audit cases), tax audit report on 30 September, AOC-4 and MGT-7.
> - **Tasks:** title, client, type, due date, assignee, status, priority, estimate. Filters for Open, Mine, Overdue and Done. Show the time spent against the estimate. Add an AI button to draft a client reminder email for documents.
> - **Reports:** week, month or all time. Hours, billable %, billable value (minutes × member charge-out rate), team ranks, client-wise time and value against the fee share for the period with an "under-recovered" flag, work-type split, last 7 days bars, an AI weekly review, CSV export and JSON backup.
> - **Team:** members with role and hourly rate, and switching between them.
> - **AI:** use the Google Gemini API with a key the user enters in Settings, stored only in localStorage. Mask client names (Client A, B...) before sending, never send PAN or GSTIN. If there is no key, or the call fails, fall back to rule-based logic so every feature still works.
> - Store everything in localStorage. Include a "Load demo firm" option with 4 team members, 5 clients and 14 days of time entries.

### Follow-up prompts used
- "Fix: the greeting should skip the 'CA' prefix in the name."
- "The weekly under-recovery check compares a part week with a full week fee. Use the share of the monthly fee for the days passed."
- "In the plan's push-to-tomorrow list, show the client name, because the same task title repeats for different clients."
- "Add document lists for accounting, payroll and statutory audit in the reminder email fallback."

## 2. Prompts the app sends to Gemini

**Plan my day**
> You are a work planner for an Indian Chartered Accountant firm. Today is {date}. The team member is a {role} with about {minutes} minutes of work time left today. Open tasks: {task list with client code, due date, days left, priority, estimate, status}. Make a short plan for today: pick the tasks that fit the time, in order. Put overdue and statutory items with late fees or interest (GST late fee, TDS interest u/s 201(1A), section 234E fee, 234A/B/C interest) first. Give one line per task with a time block and a one-line reason. Then add one line on what to push to tomorrow. Plain text, under 180 words.

**AI weekly review**
> You are the practice manager of an Indian CA firm. Review this week's time data and write a weekly review for the partner. {hours, billable share, value, team hours, work types, client-wise time / value / fee share, overdue tasks, non-billable hours}. Cover: 1) where time went, 2) clients where time value is well above fee (under-recovery) and what to do (re-price, scope letter), 3) staff balance, 4) overdue compliance risk, 5) three concrete actions for next week. Under 220 words.

**Draft client reminder**
> Write a short, polite email from {firm}, Chartered Accountants, to the client "[Client name]" asking for the documents and data needed for: "{task}" ({type}), due on {date}. List the usual documents an Indian CA needs for this work as bullets. Mention the late fee or interest risk in one line. Under 140 words.

The placeholder `[Client name]` is replaced with the real name only inside the browser, after the AI replies.
