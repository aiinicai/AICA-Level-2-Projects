# PracticeOS (Python edition): practice management for CAs & tax professionals

A complete server-rendered web app in **Python only**: Django 5, PostgreSQL, Tailwind (via CDN) and a little vanilla JS for drag-and-drop and live previews. No Node, no build step.

Multi-tenant (one workspace per firm) · roles: **Admin / Team member / Client** · CRM · tasks & recurring deadlines · documents · timesheets · invoicing.

## Quick start

```bash
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Option A: zero setup (SQLite file)
python manage.py migrate
python manage.py seed_demo            # optional demo data
python manage.py runserver            # http://localhost:8000

# Option B: PostgreSQL (recommended)
docker compose up -d
cp .env.example .env                  # then export the variables (or use your process manager)
export DATABASE_URL=postgres://postgres:postgres@localhost:5432/ca_practice
python manage.py migrate && python manage.py seed_demo && python manage.py runserver
```

Demo logins (after `seed_demo`), workspace **`demo`**, password `Password@123`:
`admin@demo.com` (admin) · `priya@demo.com` (team member) · `rao@client.demo` (client portal).
Or open `/signup/` and create your own firm.

```bash
python manage.py test                 # 62 tests (61 on SQLite + a Postgres-only concurrency test)
python manage.py generate_recurring_tasks   # run daily from cron / systemd timer / your scheduler
```

## Project layout

```
config/       settings, urls
core/         tenant middleware, role decorators, tenant-scoped forms, template filters, dashboard, portal, seed_demo
accounts/     Firm (tenant), User (3 roles), workspace login backend, signup, team management
crm/          Client, ClientService (CRM)
workflow/     Task, RecurringRule, recurrence engine (recurrence.py), Kanban board
documents/    Document (upload / link / physical location), private storage, authenticated downloads
billing/      TimeEntry, Invoice, InvoiceItem, Payment, InvoiceCounter + services.py (all money logic)
templates/    Tailwind templates (one folder per app)
tests/        recurrence, billing/money, tenant isolation, roles, CSRF, uploads, flows, Postgres concurrency
```

## How the requirements are met

**1 · Multi-tenant auth & onboarding.** `/signup/` creates the firm (name, type: Proprietary/Partnership/LLP/Company, size) and its first Admin in one transaction. The workspace address is suggested from the firm name, checked live for availability (reserved names blocked) and shown as `https://<name>.practiceos.app`. This is a **simulation**, no DNS is created. Login takes *workspace + email + password*, so the same email can exist in different firms. Roles: Admin (everything, plus team management), Team member (day-to-day work, own time only), Client (read-only portal: own invoices + documents the firm shared).

**2 · CRM.** Searchable client list, add/edit/archive/restore, PAN & GSTIN validation (format, normalised to upper-case, PAN unique per firm), per-client services with fee and billing frequency, and a detail page showing tasks, documents, invoices and outstanding balance.

**3 · Workflow & recurring deadlines.** Kanban board (To Do / In Progress / Review / Completed) with drag-and-drop, assignee, priority, due date, overdue flags and an "only my tasks" filter. *Recurring deadlines* (monthly GSTR-1/3B, TDS, PF/ESI, quarterly advance tax, annual ITR, 3CD, GSTR-9, or custom) create real tasks N days before each due date. The engine is idempotent (database constraint + `get_or_create`), clamps day 31 to short months, and catches up on missed periods. Run it daily with `generate_recurring_tasks` or press *Generate now*.

**4 · Documents.** Three kinds: **upload** (type- and size-checked, stored under a random name in a per-firm folder *outside* any served directory), **link** to Drive/SharePoint/DMS, and **physical location** (cabinet/shelf/box). Downloads go through an authenticated, tenant-checked view; clients can only fetch documents the firm explicitly marked as shared.

**5 · Time & billing.** Timesheets (hours + minutes, billable flag, optional task link, date range & client filters, per-client summary). Invoices from manual line items *or* by billing logged time (rate: entry → staff member → fallback), GST % per line, gap-free numbering `INV/2026-27/0001` per firm per financial year, part payments, automatic Pending → Paid, cancel (number retained; time released), printable invoice view.

## Security design

* **Tenant isolation:** `request.firm` comes from the logged-in user's record, never from the URL or form. Every object lookup goes through `firm_object_or_404`, so another firm's id is a 404. Every foreign-key dropdown is filtered to the firm (`TenantModelForm`), so a forged client/assignee id fails validation. Covered by tests.
* Roles enforced by decorators on every view; client logins are redirected to the portal; staff-only pages 403 for the wrong role; disabled users lose access on their next request.
* CSRF on every POST (logout included); login error messages don't reveal which workspaces/emails exist; 10 failed attempts per IP → 15-minute lockout; passwords validated and hashed by Django; session cookies httpOnly, HTTPS-only in production; the app refuses to start with the default secret key when `DJANGO_DEBUG=0`.
* Money uses `Decimal` end to end, rounded half-up to the paisa, and is always calculated server-side from line items.

## Before production

1. **Tailwind:** templates load Tailwind from its CDN, which is fine for an MVP but not for production. Compile a stylesheet (Tailwind CLI or `django-tailwind`) and serve it with WhiteNoise/your CDN.
2. **Serve with gunicorn** behind a TLS proxy; set `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`. HTTPS redirect, secure cookies and HSTS turn on automatically. Consider `SECURE_HSTS_INCLUDE_SUBDOMAINS/PRELOAD` once every subdomain is HTTPS.
3. **Real subdomains:** wildcard DNS + TLS, then resolve the tenant from the `Host` header instead of asking for the workspace at login.
4. **Invites:** a temporary password is shown once on screen. Replace with an emailed set-password link; add password reset and optional 2FA.
5. **Files:** move uploads to S3-compatible storage with encryption and virus scanning. You hold client PAN/GSTIN and financial records, so plan consent, retention, backups and audit logging for India's DPDP Act.
6. **GST invoicing:** one GST rate per line. No CGST/SGST/IGST split by place of supply, HSN/SAC codes or e-invoicing. Treat the invoice as a starting point and confirm requirements with your own advisor.
7. **Compliance calendar:** the preset due dates are editable defaults, not a live feed. Extensions and notifications change them, so verify against current CBDT / CBIC notices.
8. Postgres Row-Level Security as a second line of defence; structured logging; CI.

## Known limitations

* Editing a recurring rule's frequency/day doesn't recompute its next due date; delete and recreate it.
* Board cards are ordered by due date (no manual ordering within a column).
* No email/WhatsApp reminders yet: the scheduler only creates tasks.
