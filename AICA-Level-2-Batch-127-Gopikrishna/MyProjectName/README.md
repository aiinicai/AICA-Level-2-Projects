# Fixed Asset Register (FAR)

A working Django web application for a public listed Indian company to
maintain its fixed asset register in line with the Companies Act 2013,
Ind AS, and CARO 2020 — built directly from the attached
"Fixed Asset Register Blueprint." Runs locally with zero setup (SQLite) or
on a server behind PostgreSQL + gunicorn.

## What's built

Every "Core" and "Mandatory" module from the blueprint is a real, working
feature, not a mockup:

- **Asset master & maker-checker** — every asset create/edit, capitalisation,
  disposal, and revaluation is routed through a two-step approval where the
  approver must be a different user from the requester (`assets/services/approvals.py`).
- **CWIP → capitalisation** — capital work-in-progress accumulates freight,
  duty, installation, and borrowing cost, then converts to a live Asset
  Master record on commissioning, generating its QR tag automatically.
- **Dual depreciation engine** (`assets/services/depreciation.py`) — Schedule
  II (SLM/WDV, 5% residual cap, mid-year proration by days-in-service) and
  Income Tax Act (block/WDV with the half-year-rate convention) run
  independently and post frozen, re-creatable snapshots per period.
- **QR generation & mobile scanning** — a QR is minted the moment an asset is
  capitalised; batch label PDFs print in bulk; a camera-based scan page
  (`/verification/scan/`) handles tag-confirm, verification, transfer,
  maintenance, and disposal-check scans through one code, geo-tags the
  device position, and raises a location-mismatch exception instead of
  silently overwriting the register — including the "scan of a disposed
  asset's tag" exception the blueprint calls out explicitly.
- **Location hierarchy & asset locator** — Site → Building → Floor →
  Room/Zone tree with live counts/value per node, and a "where is this
  asset" search.
- **Transfer, disposal, revaluation & impairment workflows** — custodian
  sign-off on transfers; disposal computes profit/loss on sale and flags a
  Section 180 "substantial part of an undertaking" review; revaluation
  captures the Registered Valuer and auto-flags the CARO 3(i)(d) 10%
  movement threshold; Ind AS 36 impairment checks post a loss against net
  book value.
- **Physical verification cycles** — rotational programme with a coverage %
  and a pending-assets worklist, feeding CARO 3(i)(b) evidence.
- **RBAC** — five Django groups (Data Entry, Verifier, Approver, Admin/CFO,
  Auditor read-only) with real model-level permissions
  (`accounts/management/commands/bootstrap_roles.py`).
- **Non-disableable audit trail** — every model that touches the books uses
  `django-simple-history`; historical rows are separate DB tables no
  application user can edit or turn off, satisfying Rule 3(1)'s "edit log
  that cannot be disabled."
- **Compliance report exports** — Schedule III PP&E note, Ind AS 16 para
  73(e) roll-forward, a CARO 3(i) evidence pack (records completeness %,
  verification coverage %, title-deed exceptions, revaluation register,
  Benami declaration), physical verification working papers, and an
  XBRL-ready CSV export for the AOC-4 PP&E note.
- **Bulk import/export** — a CSV template plus an importer for migrating an
  existing spreadsheet register without re-keying every asset.

### Deliberately out of scope for this build

Flagged as "Recommended" (not "Core"/"Mandatory") in the blueprint, or
dependent on company-specific systems this build can't assume:

- ERP/GL posting integration (SAP/Oracle/Tally) — the depreciation engine
  produces the journal-ready numbers; wiring the actual GL post is
  company-specific.
- SSO/MFA — Django's session auth is in place; swapping in the company's
  IdP (Azure AD, Okta, etc.) is a `django-allauth`/`django-mozilla-sso`
  style addition once you know which one.
- Multi-entity consolidated Ind AS notes — the schema already supports
  multiple `Entity` rows (subsidiaries); a consolidation rollup view across
  entities isn't built yet.
- A full signed XBRL instance document — the XBRL export here is a
  structured, tag-mapped CSV ready to hand to XBRL tagging software, not a
  filed instance document itself.

These are all straightforward to add on top of this codebase — the data
model already has the hooks (see `Entity`, `tax_block_code`, etc.).

## Quick start (local, SQLite, zero setup)

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py bootstrap_roles       # creates the 5 RBAC groups + permissions
python manage.py seed_reference_data   # seeds the Schedule II asset-class master
python manage.py createsuperuser       # your own admin login
python manage.py seed_demo_data        # OPTIONAL: sample entity/locations/users/assets

python manage.py runserver
```

Open http://127.0.0.1:8000/ and log in. If you ran `seed_demo_data`, five
demo users exist — `data_entry1`, `verifier1`, `approver1`, `cfo1`,
`auditor1` — all with password `FarDemo@2026` (change immediately; this is
demo data, not something to ship to a real deployment).

## Server deployment (Docker + PostgreSQL)

```bash
cp .env.example .env
# edit .env: set DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DJANGO_DB_PASSWORD,
# DJANGO_SECURE_COOKIES=True once you're behind HTTPS, FAR_QR_BASE_URL to
# your real domain (this is what gets encoded into every QR tag).

docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

This runs PostgreSQL + gunicorn behind the `web` service on port 8000 —
put nginx or your load balancer's TLS termination in front of it. Run
`docker compose exec web python manage.py seed_reference_data` once to seed
the Schedule II class master (skip `seed_demo_data` in a real deployment).

### Deploying without Docker

Point `DJANGO_DB_ENGINE=postgresql` and the `DJANGO_DB_*` variables at a
real PostgreSQL instance in `.env`, then:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py bootstrap_roles
python manage.py seed_reference_data
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

Run gunicorn behind nginx/Apache for TLS and static-file serving in
production (whitenoise handles static files adequately for moderate
traffic if you'd rather not stand up nginx).

## Before you rely on this for a real filing

The blueprint this was built from says it plainly, and it's worth
repeating: **this is reference tooling, not legal advice.** Two things
specifically need sign-off from the company's statutory auditor / practising
company secretary before go-live:

1. **The Rule 3(1) audit-trail format** — confirm the auditor is satisfied
   that `django-simple-history`'s historical tables meet their evidentiary
   expectations, and lock down database-level access so no one can bypass
   the application and edit history tables directly (see "Hardening
   checklist" below).
2. **The Section 180 materiality threshold** — this build flags a disposal
   as needing board/shareholder review when its proceeds exceed 10% of
   total net PP&E (`disposal/views.py`, `SECTION_180_DEFAULT_THRESHOLD_PCT`).
   Section 180 doesn't set that number in law; replace it with the
   company's own delegation-of-authority policy figure.

## Architecture

```
far-app/
├── manage.py
├── config/            settings, root urls, dashboard view
├── accounts/           custom User, RBAC groups, seed/bootstrap commands
├── locations/          Entity, Location (Site→Building→Floor→Room tree)
├── assets/              AssetClass, Vendor, CapexRequisition, CWIP, Asset,
│                        ApprovalRequest, DepreciationRun + entries,
│                        RevaluationRecord, ImpairmentCheck, Document
│   └── services/        depreciation.py, qr.py, approvals.py
├── verification/        ScanEvent, VerificationCycle, PhysicalVerificationRecord,
│                        MaintenanceLog + the camera-scan page
├── transfers/           TransferRequest (custodian sign-off)
├── disposal/             DisposalRequest (profit/loss, Section 180 flag)
├── compliance/          FinancialYear, BenamiDeclaration
│   └── services/        reports.py (Schedule III / Ind AS 16 builders)
└── templates/            Bootstrap 5 UI, one folder per app
```

Every app that posts to the books (`assets`, `disposal`, `transfers`,
`verification`, `locations`) carries `simple_history.HistoricalRecords()`
on its models — that's the audit trail, and it's a separate table with no
UI path to edit or delete it.

## Hardening checklist before go-live

- [ ] Set a real `DJANGO_SECRET_KEY` and set `DJANGO_DEBUG=False`.
- [ ] Set `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` to your
      real domain(s) — don't ship the `*` default.
- [ ] Put this behind HTTPS and set `DJANGO_SECURE_COOKIES=True`.
- [ ] Change every demo/seed password immediately; delete `seed_demo_data`
      usage from any real deployment pipeline.
- [ ] Restrict database credentials so the application's DB user cannot
      `DROP`/`ALTER` the `*_historical*` tables — that's what makes the
      audit trail actually non-disableable rather than merely inconvenient
      to disable from the UI.
- [ ] Configure real backups with a documented RPO/RTO (blueprint §06) —
      this repo doesn't prescribe a backup tool since that's
      infrastructure-specific.
- [ ] Wire SSO/MFA if the company's IT access policy requires it for
      systems touching financial reporting (blueprint §06).
- [ ] Confirm the 8-year retention policy (Section 128) is met by your
      backup/archival strategy, not just by "nothing gets hard-deleted in
      the app" (which is already true — disposal archives, never deletes).
