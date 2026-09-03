# Company OS

A working Python implementation of the "Company OS" plan (login/roles, prompt-to-action
calendar, attendance, leave, resignation lifecycle, Excel export, backup, audit log),
built as a FastAPI web app you run locally and your team reaches over the office LAN.

## What's implemented (Phases 0-4 of the roadmap)
- Login with 4 roles (CEO / Dept Admin / Manager / Employee), forced password change on first login
- CEO creates Dept Admins; Dept Admins create Managers/Employees in their own dept
- Prompt bar: type "Add task: submit report by Friday, high priority" and it's parsed and saved
  (also handles meetings, WFH/WFO/leave, pending actions, reminders, "mark X as done", resignations)
- Calendar with Free/Busy enforcement (server-side, not just UI) per the visibility matrix
- Attendance (WFO/WFH/Half-day/Leave), team snapshot for managers/admins/CEO
- Leave apply/approve/reject with role-scoped approvals
- Resignation → notice period → exit checklist, visible only to Manager+/CEO
- Reports: multi-sheet Excel export (Summary, Attendance, Tasks, Confidential Leave & Notice —
  the confidential sheet is only generated if the requester is permitted to see it)
- CEO-only: full DB backup button, audit log viewer
- 19-user demo org auto-seeded on first run (matches the plan doc), default password `Welcome@123`

**Not yet built** (Phase 5 "extras" from the plan — announcements, document repository, IT
asset register, notifications bell, org chart view): straightforward to add later on this same
codebase, kept out of the first cut to ship the core fast.

## Run it from source (development)
```
cd company_os
..\venv\Scripts\python run.py
```
Then open http://127.0.0.1:8000 — login as `EMP-0001` / `Welcome@123` (you, the CEO).
The console also prints your LAN address (e.g. `http://10.x.x.x:8000`) — that's the link
to give your team so everyone opens the same app from their own PC's browser.

Data lives in `company_os/data/company_os.db` (SQLite). Delete that file to reset to a
fresh demo org.

## Building the .exe
This is the easiest path for a non-Electron, Python-based app: **PyInstaller**, which bundles
the Python interpreter + all dependencies + your code into one `.exe`.

```
cd company_os
build_exe.bat
```
This produces `dist\CompanyOS.exe` (~25MB, single file, no install needed). Copy that one
file anywhere (a folder on your laptop, or a shared office PC/mini-PC later) and double-click
it to start the server — it prints the LAN URL to share, and creates its own `data\` and
`backups\` folders next to itself on first run.

To rebuild after code changes, just re-run `build_exe.bat`.

### Why "one .exe on my laptop" still needs the LAN step
Like the original plan explained: for many people to see one shared, live calendar, the data
has to be served from one machine everyone else's browser points at. Running `CompanyOS.exe`
*is* that server — you still only run one app; your laptop (while it's on) is also where the
shared data lives. No cloud, no internet required, everything stays on your office network.
Once the team grows, move the same .exe to a small always-on mini-PC and nothing else changes.

## About building this further with Antigravity
This is a completely standard FastAPI + SQLAlchemy + Jinja2 Python project (no unusual
tooling), so you can open the `company_os` folder directly in Antigravity (or any AI coding
tool/IDE) and keep extending it — e.g. "add the Announcements module from Section 1.3" or
"add a dark theme toggle". Key files to point it at:
- `app/models.py` — database tables
- `app/permissions.py` — the visibility-matrix rules (who sees what)
- `app/prompt_engine.py` — the natural-language parser
- `app/routers/*.py` — one file per module (calendar, attendance, leave, admin, reports, resignation)
- `app/templates/*.html` — the pages (Tailwind CSS via CDN, no build step)

## Notes
- Python's recursion limit is raised to 10000 in `app/database.py` (org-chart traversal /
  prompt parsing on a large team can nest deeper than the 1000 default) — already done.
- Passwords are bcrypt-hashed; sessions are signed cookies (secret auto-generated into
  `data/.session_secret` on first run — keep that file private).
- All visibility rules are enforced server-side in `app/permissions.py`, not just hidden in
  the UI, per the plan's security requirements.
