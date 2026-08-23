# AssetTrace

Fixed Asset Verification & QR Code Management — implements both the [design dossier](../..) baseline and the SAP Integration Addendum (Rev 2): SAP is the system of record for financial/asset-master data; this portal is the system of record for physical verification, QR identification, and reporting.

Built with Next.js (App Router, Server Actions), Prisma + SQLite, NextAuth (credentials/JWT), `qrcode` + `html5-qrcode` + `pdf-lib` (bulk QR labels), `exceljs` (SAP import/export), and `sharp` for photo compression.

## Setup

```bash
npm install
npm run db:push    # create the SQLite schema
npm run db:seed    # load demo data — see accounts below
npm run dev
```

Run the unit tests (core SAP-import validation, mismatch detection, location scoping, CSV/QR helpers — 30 tests, no database needed) with:

```bash
npm run test
```

Open http://localhost:3000.

## Demo accounts

Password for all: `Passw0rd!`

| Role | Email | Scope |
|---|---|---|
| Admin | `admin@assettrace.demo` | Everything |
| Location Head | `locationhead@assettrace.demo` | Mumbai and everything beneath it |
| Verifier | `verifier@assettrace.demo` | Assigned campaigns |
| Read-only | `viewer@assettrace.demo` | View only |

## What's implemented

**Baseline (v1):** asset register, location hierarchy, QR generate/scan/reprint, scan-to-verify workflow, photo pipeline (client resize → server `sharp` → WebP + thumbnail), verification campaigns, exceptions, append-only audit log, CSV reports, role dashboards.

**SAP Integration Addendum (Rev 2):**
- **SAP Import** (`/sap-import`) — upload `.xlsx`/`.csv`, validates column *structure* (10 standard + 15 custom columns, all required to exist) independently of cell *values* (all optional/nullable); preview shows new/existing/blank/invalid/duplicate counts before commit; upserts by Asset Number without ever touching verification history (`src/lib/sapImport.ts`, `src/actions/sapImport.ts`).
- **SAP data governance** — `SapAssetData` is a separate table, 1:1 with `Asset`, read-only everywhere in the UI; `updateAsset` rejects any write to an SAP-linked asset's identity fields server-side, independent of what the UI renders (`src/actions/assets.ts`).
- **Split Asset Details** — "SAP Fixed Asset Register Data 🔒" vs. "Physical Verification Data" as two visually distinct sections, exactly as specified.
- **SAP-vs-physical comparison** (`/mismatches`) — location, serial number (verifier-observed vs. SAP), and condition mismatches flagged automatically, never auto-resolved.
- **Location Head role** — scoped via `LocationHeadAssignment` + a `fullPath`-prefix check (`src/lib/locationScope.ts`); every scoped page/action re-filters server-side, never trusting the client.
- **SAP Export** (`/sap-export`) — select verified records, validate, generate an `.xlsx` from an admin-configurable template (`/sap-export-template`); files are stored outside `public/` and served only through an authenticated route handler, since they carry NBV/GBV.
- **Bulk QR generation** (`/qr/bulk`) — filter by SAP Asset Class / location / "no QR yet", multi-select, generates one print-ready PDF via `pdf-lib` (`src/lib/qrPdf.ts`).
- **SAP custom fields** (`/sap-custom-fields`) — 15 fixed slots, admin-configurable display labels, never hard-coded.
- Import/export history, audit trail entries for every SAP-related action.

## Not yet built (Phase 2, per the addendum)

Direct SAP API/RFC/OData connector (file upload remains the interface), a full transformation/rule engine for export mapping beyond field-to-column, true background-job infrastructure for bulk QR/import at 50k+ scale (current implementation runs synchronously — see ADD11 scoping note), multi-level Location Head delegation, offline verification/sync, SSO.

## Database

SQLite for zero-config local dev (`prisma/dev.db`). The schema (`prisma/schema.prisma`) is provider-agnostic enough to move to Postgres for a real deployment — change the `datasource` block and re-run `prisma db push`.

## Full design reference

The complete requirements, architecture, ERD, API design, roadmap, and the SAP Integration Addendum this build follows live in the [AssetTrace design dossier](https://claude.ai/code/artifact/0ec103fd-d985-4d17-97ec-a3125ee0d938).
