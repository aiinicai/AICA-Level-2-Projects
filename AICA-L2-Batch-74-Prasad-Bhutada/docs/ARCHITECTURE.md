# Architecture Overview

## Technology Stack & Rationale

| Layer | Choice | Why |
|---|---|---|
| Backend runtime | Node.js + Express + TypeScript | Excellent DOCX/OOXML ecosystem (docxtemplater, mammoth, pizzip), runs as a lightweight Windows service, easy for a small office IT setup to maintain, strong typing for reliability. |
| Database | SQLite (via Prisma ORM) | Per spec: "lightweight database suitable for LAN deployment... prefer SQLite." Zero-admin (single file), trivially backed up, ACID-safe for the concurrency levels of a small office (a handful of simultaneous staff), and Prisma gives a normalized, migration-tracked schema that scales to Postgres later with almost no code change if the office ever outgrows SQLite. |
| ORM / schema sync | Prisma | Type-safe queries, a single declarative `schema.prisma` as source of truth, auto-generated client — removes an entire class of SQL-injection and typo bugs. Deployment uses `prisma db push` (declarative sync, no migration-history files to manage) rather than versioned migration files — appropriate for a single SQLite file with one deployment target, not a multi-environment team pipeline; see the note below. |
| DOCX manipulation | docxtemplater + PizZip | Industry-standard OOXML templating engine. Operates at the XML run level, so replacing a placeholder's text preserves that run's `<w:rPr>` (font/size/bold/italic/underline/color/highlight) automatically — no custom formatting-copy code needed. Also exposes `getFullText()` per XML part (body/header/footer), which we use for reliable placeholder *detection* that already matches what the *generation* engine can resolve. |
| DOCX → HTML preview | Mammoth | Produces clean, Word-like HTML from DOCX for the centre preview panel without needing Word or LibreOffice running per-request. |
| DOCX → PDF | LibreOffice headless (`soffice --convert-to pdf`) | Best practically-achievable fidelity for tables/headers/footers/pagination without a paid Office-interop or Aspose license. Abstracted behind a `pdfEngine` setting so a licensed engine can be swapped in later with no code changes elsewhere. |
| Frontend | React + TypeScript + Vite + Tailwind | Fast dev/build cycle, component reuse across the three-panel layouts the spec repeatedly asks for, Tailwind gives consistent spacing/typography with a light/dark theme via a single `dark` class toggle. |
| Excel import/export | ExcelJS | Reads/writes real .xlsx (not CSV), needed for Client Master bulk import/export and History export. |
| Backup | node-cron + adm-zip | Scheduled job zips the SQLite file + templates folder on a configurable cron expression. |

## Why this is a monolith-with-modules, not microservices

A CA office LAN deployment has a handful of concurrent users on one physical server (or one staff PC acting as server). Microservices would add operational complexity (multiple processes, service discovery, more failure points) with zero benefit at this scale. Instead, the backend is organized as **feature modules** inside one Express app (`src/modules/templates`, `src/modules/clients`, `src/modules/generation`, etc.), each with its own `service.ts` (business logic), `controller.ts` (HTTP handlers), and `routes.ts` (Express router). This gives clean separation of concerns and easy unit-testing of services in isolation, while keeping deployment to "one Node process + one static frontend build."

## Single-process deployment (frontend served by the backend)

For deployment, the Express backend also serves the built React frontend as static files (`backend/src/server.ts`, populated by `setup.bat` copying `frontend/dist` into `backend/public`), with a catch-all route falling back to `index.html` for client-side routes. This means:

- **One process, one port, one address** (`http://localhost:4000`) for a non-technical person to run and remember — not two separate servers that need to be told how to find each other.
- The frontend's API calls are always same-origin relative requests (`/api/...`), so there is no build-time "what's the backend's URL" configuration to get wrong — the earlier version of this project required a `VITE_API_BASE_URL` baked in at frontend build time, and a missing/mismatched value there produced a blank white page with no visible error, which was a real support burden for a non-technical deployer. `VITE_API_BASE_URL` still exists as an escape hatch (`frontend/.env.example`) for someone who deliberately wants to split the two across machines, but it is no longer required for the default setup.
- Source code is still organized as two separate `frontend/` and `backend/` projects (clean separation, independent tooling, independently testable) — it's only the *deployment output* that gets merged into one running process, not the source.

## Database setup: `prisma db push`, not migration files

`setup.bat` runs `npx prisma db push` rather than `prisma migrate deploy`/`migrate dev`. This was a deliberate choice after an earlier version of this project shipped with fragile "try deploy, fall back to dev" branching logic in the batch script that silently failed to create any tables on a first-time install (the failure mode: `migrate deploy` succeeds trivially when no migrations directory exists yet, rather than erroring, so the fallback branch that would have actually created the schema never ran).

`db push` sidesteps this class of problem entirely: it declaratively syncs the live database to match `schema.prisma`, creating whatever's missing, and is safe to run unconditionally — first install or the hundredth update, no branching on "does a migrations folder already exist" required. The trade-off is that `db push` doesn't retain a reviewable migration history or support scripted down-migrations, which matters for a team shipping schema changes across staging/production environments — it does not matter for a single SQLite file on a single office server being kept in sync by a batch script. If this project ever grows into a multi-environment deployment, switching back to versioned `prisma migrate` files remains straightforward since the underlying schema/ORM layer is unchanged.

## Request flow for document generation (Modules 5–8)

1. Frontend posts selected `templateIds` to `POST /api/generation/merge-placeholders`.
2. `generation.service.ts` loads each template's `TemplatePlaceholder` rows, merges by placeholder name, and attaches which templates use each one (for the "Used in: ..." italic captions) plus any Client Master mapping.
3. User fills values (or clicks Auto Fill, which calls `/api/generation/autofill` and resolves each mapped field from `Client` + `ClientCustomValue`).
4. `POST /api/generation/generate` (multipart, so image placeholders can be uploaded as real files) runs `generateDocuments()`:
   - Re-validates every value server-side (never trusts client-side validation alone).
   - For each selected template, calls `generateDocx()` — a **fresh** in-memory render from the master template file; the master is opened read-only and a new file is written under the Generated Documents folder, named `<Document Name> - <Client Name>.docx`.
   - Optionally converts each to PDF via LibreOffice.
   - Records one `GenerationHistory` row with all template outputs and the placeholder values used (Module 10).
5. Frontend Step 3 offers individual downloads or a ZIP of everything in that batch.

## Data model highlights

- **EAV pattern for Client Master** (`ClientField` + `ClientCustomValue`): the six spec'd fields (name, address x2, type, mobile, email) are real columns for query speed; anything added later by an admin becomes a new `ClientField` row and is immediately available for placeholder mapping — satisfying "future client master fields should automatically become available for mapping" without any code or schema migration.
- **Recycle Bin** is a `status` flag (`Active`/`Deleted`) plus `deletedAt`, not a physical delete — nothing is destroyed until an admin explicitly manages storage.
- **Dependency check** before delete currently checks `GenerationHistoryTemplate` usage (has this template ever been used to generate a document for a client) and warns accordingly, while still allowing the delete (to Recycle Bin, which is reversible).
- **Settings** table is a generic key/value store; nothing in the app reads folder paths, the PDF engine choice, or the Template Management password from source code — see `docs/ADMIN_MANUAL.md`.

## Security model

- No login is required for everyday use (template browsing, document generation, client management) — per spec.
- Only "Manage Formats" (import/replace/rename/delete/restore templates, category management, Settings, Backup/Restore) requires the configurable password. Correct password issues a short-lived (4 hour) JWT scoped to `template-admin`; all mutating template/settings/backup routes require that token via `requireTemplateAdmin` middleware.
- Passwords are bcrypt-hashed, never stored or logged in plaintext.
- All error responses are sanitized (`AppError` + global error handler) — internal stack traces are logged to rotating Winston log files, never sent to the browser.

## Known limitations / documented trade-offs (see roadmap in README)

- Legacy `.doc` files must be converted to `.docx` before import (stated clearly in the UI/API error), since reliable placeholder detection and formatting-preserving replacement require the OOXML format.
- SmartArt diagram text and image alt-text are outside docxtemplater's text model and are not scanned for placeholders (ordinary text boxes and shapes *are* covered, since they're nested in the same XML part).
- Placeholder validation patterns (PAN/GSTIN/etc.) live in `validators.ts` as the source of truth; making them editable from the Settings UI (spec says "validation rules shall be configurable") is a straightforward next step — see README roadmap.
