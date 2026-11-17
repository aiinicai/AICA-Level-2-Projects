# AICA's Task Manager — Phase 1

A Windows desktop task-management application for CA firms, built with Python's Tkinter GUI and SQLite database.

## Requirements
- Windows 10 or Windows 11
- Python 3.10 or later (Tkinter is included with the standard Windows Python installer)

## Run
1. Extract the ZIP file to a folder, e.g. `C:\AICA_Task_Manager`.
2. Install Python from https://www.python.org/downloads/ if it is not already installed. During setup, select **Add Python to PATH**.
3. Open Command Prompt in the extracted folder.
4. Run: `python app.py`

## Initial login
- Username: `admin`
- Password: `Admin@12345`

Change this initial password and create individual staff accounts immediately. Do not share the administrator account.

## Phase 1 functions
- Login with salted PBKDF2-HMAC-SHA256 password hashing
- Admin-only user creation, editing and deactivation
- Roles: Admin, Partner, Manager, Accountant, Paid Assistant, Article
- Dashboard: total, pending, in-progress, completed and overdue counts
- Task creation, assignment, editing and deletion (role-restricted)
- Task status and priority
- Client/entity name, description, start date and due date
- Search task register
- SQLite local database (`aica_tasks.db`) created automatically
- Basic task status history and activity log

## Role rules in this starter build
- Admin: user administration and full task access
- Partner: view, create, edit and delete all tasks
- Manager: view, create and edit all tasks
- Accountant / Paid Assistant / Article: view and update tasks assigned to them

## Important limitations
This is a Phase 1 starter application, not yet a production multi-user network system.
- The SQLite database is local to the computer. Multiple users on different computers do not share data.
- Notifications, email/WhatsApp alerts, file attachments, recurring tasks, advanced reports and AI features are planned for later phases.
- The default administrator password must be changed before real use.
- Back up `aica_tasks.db` regularly.
- For a shared office deployment, Phase 2 should introduce a central server/database and stronger operational controls.

## Suggested next phases
- Phase 2: enhanced task workflow, review/approval, attachments, reports and shared database.
- Phase 3: AI-assisted task assignment, priority recommendations, workload balancing and daily summaries.
- Phase 4: notifications, scheduled reminders, audit analytics and deployment packaging.
