# CA Task Mitra – workflow, compliance and billing automation for a CA firm

**ICAI AICA Level 2 – Individual Capstone Project**
Submitted by: **CA Subham Agrawal, Membership No. 315679**, AICA Level 2, **Batch 110, Bhubaneswar** (Subham Agrawal & Company, Bangomunda, Odisha).
Video walkthrough: *(add your YouTube unlisted link here)*

> All data in this project and its screenshots is **fictional**. No real client, personal or confidential data was entered into any AI tool, as the course requires.

## The problem
Many CA firms still run on registers, Excel, Google Sheets and WhatsApp. That causes: scattered tasks, missed deadlines, document chasing, no review trail, poor visibility for the owner, delayed billing, double entry into Tally, lost knowledge, staff dependency and slow adoption of any new system.

## The solution
CA Task Mitra is a desktop app (Python + SQLite, opened in a Chrome app window) that runs on the firm's own PC. Staff on the same Wi-Fi open it in a browser. No cloud, no subscription; data stays in the office.

- **Role based:** CA, Manager, Employee – each sees only what they need.
- **Modular:** 12 modules, each with sub-modules and an on/off switch (Admin → Module manager). A new module is one file.
- **CA stays in control:** nothing is sent to a client without CA approval; every action is in the audit trail.

| # | Module | What it does |
|---|--------|--------------|
| 1 | Work Management | Clients, services, assignments, checklists, documents, review and approval, dashboards |
| 2 | Employee Management | My work, workload, attendance, timesheets |
| 3 | Compliance | Compliance master, applicability, auto-generation of work, calendar, extensions, notices |
| 4 | Finance & Billing | Fee master, invoices, receipts, outstanding ageing, auto-billing when work is closed |
| 5 | AI Skills Library | The firm's reusable AI prompts, linked to services, launched in one click |
| 6 | Communication | "Documents insufficient" e-mail drafts, CA approval queue, announcements |
| 7 | Tally Integration | Invoices and receipts posted to TallyPrime; pending entries go with the next bill |
| 8 | Alerts (n8n) | Pending-list alerts to the CA via an n8n webhook (e-mail fallback) |
| 9 | AI Assistant | Morning briefing, plain-English task creation, checklist suggestions |
| 10 | Administration | Module manager, users, settings, audit trail, backup, CSV import/export, demo data |
| 11 | Client Portal | *Planned* |
| 12 | Document Vault | *Planned* |

## AI used to build it
See [AI_PROMPT_LOG.md](docs/AI_PROMPT_LOG.md). In short: ChatGPT for discussion and requirement thinking, Claude for design, coding, review and testing, Claude computer use to read the ChatGPT conversations, the Tally MCP from the course for Tally, and n8n for alerts. Every decision was reviewed and every screen tested by the author.

## Run it
1. Install Python 3.10+ (Windows). No other package is needed.
2. Double-click `run_windows.bat` (or `python run.py`). It opens as a Chrome app window.
3. First launch: create the firm and the CA login; tick "Load fictional demo data".
4. Demo logins afterwards: `manager`, `riya`, `amit`, `neha` – password `demo@123`.
5. Optional: `build_exe.bat` builds `CA-Task-Mitra.exe`; `make_shortcut.bat` adds a Desktop icon; `python make_share.py` builds a single shareable file.

More: [USER_GUIDE.md](docs/USER_GUIDE.md) · [ARCHITECTURE.md](docs/ARCHITECTURE.md) · [LIMITATIONS.md](docs/LIMITATIONS.md) · tests: `python tests/test_workflow.py` (57 automated checks).

## Screenshots
See the `docs/screenshots` folder: dashboard, module manager, bulk import, grouped assignments, bulk actions, new assignment, invoices, skills, e-mail approval, Tally queue, alerts, audit trail, employee dashboard.

## Add a new module
Create `modules/<key>.py` with `MANIFEST`, `SCHEMA` and a `Router R`; add it to `modules/__init__.py`; optionally add `web/modules/<key>.js`. No other file changes.

## Licence and use
Built by CA Subham Agrawal for the practice of his own firm, and submitted as the ICAI AICA Level 2 capstone project. CA Task Mitra is a prototype, provided as it is, without any warranty. Please contact me before reusing or distributing it.

## Before you use it for real
1. Start with dummy data, never with real client data.
2. Check every compliance due date yourself against the latest notifications.
3. Test the Tally, n8n and e-mail connections on your own setup. They were tested only with simulated servers (see [LIMITATIONS.md](docs/LIMITATIONS.md)).
4. Decide, as a professional, what client data goes into the app or into any AI tool, and keep regular backups.
