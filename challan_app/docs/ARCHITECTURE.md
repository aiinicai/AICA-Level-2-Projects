# Architecture and technology stack

## Recommendation
**Python 3 + Flask, SQLAlchemy, SQLite (WAL) by default, PostgreSQL as the upgrade path, served by Waitress, used from any browser.**

| Choice | Why |
|---|---|
| Web app, one server, browsers as clients | Nothing to install on user PCs; one copy of data; easy updates. |
| Flask + Jinja templates | Small, readable, easy for your IT team to maintain; no JavaScript build chain (the few scripts are plain JS). |
| SQLAlchemy | Same code runs on SQLite or PostgreSQL - set `DATABASE_URL` to switch. |
| SQLite in WAL mode, **file on the server's local disk** | Zero administration, one file to back up. Safe for ~20-50 occasional writers because every number is assigned inside a database transaction (writes are serialised, readers never block). The database file is **never** opened from a shared drive - users only reach it through the web app. |
| PostgreSQL (optional) | Choose it if you expect heavy simultaneous use, need DB-level backups/replication, or IT already runs it. Install `psycopg2-binary`, set `DATABASE_URL=postgresql://user:pass@host/challans`, run `flask init-db`. No code change. |
| Waitress | Pure-Python production server that works on Windows without extra software. |
| openpyxl | Excel import/export without Excel installed on the server. |
| Browser print / "Save as PDF" | Challan layout is HTML+CSS (A4, 3 copies, watermark). No PDF library to maintain; the same page prints or saves to PDF. |

## How the hard requirements are met
* **Gap-free, duplicate-free numbers, safe under simultaneous saves:** the number is taken from a `counters` row *inside the same transaction that saves the challan*. The UPDATE locks the counter until commit, so two users are serialised, and a failed save rolls the counter back (no gaps). A unique index on `challans.number` is the second safety net. Verified by a 12-thread test.
* **Numbers only on final save:** challans start as drafts with no number; "Issue" assigns it.
* **Financial-year restart:** counters are keyed `TYPE|FY` (e.g. `MRC|2026-27`).
* **Issued challans never change under you:** consignor and consignee details are snapshotted at issue; vendor master edits don't alter old challans.
* **Audit trail:** every create/edit/issue/print/e-way/receipt/cancel/login/import is written to `audit_log` with user and time (Admin > Audit log, and per-challan History).
* **Security:** hashed passwords, forced first-login change, CSRF token on every POST, role checks on the server, session timeout (10 h).

## Roles
| Role | Can |
|---|---|
| Requester | Create vendors, create/issue/print challans, update e-way bills, record receipts, update ERP codes, edit own drafts. |
| Approver | Everything a requester can, plus cancel challans, close corrective actions, edit vendors, upload vendor Excel. |
| Admin | Everything, plus users, plants/GSTINs, numbering format, editing issued challans, MRC to ERP vendors, historical challan upload. |

## Scaling / limits
SQLite is fine for this workload (hundreds of challans a month). Move to PostgreSQL if you ever see "database is locked" delays or want more than ~50 concurrent users.
