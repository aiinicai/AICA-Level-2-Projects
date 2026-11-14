# Easy AI Procura
## AICA Level 2 Project — Parveen Bajaj

**Purpose:** Help organisations approve supplier invoices only for goods ordered and actually received.

**Demonstration:** https://order-receive-pay.lovable.app

This is a source-code submission, not a preconfigured standalone installation or a backup of the live database. Existing accounts, passwords, sessions and business records are not included. The live demonstration may be an earlier published snapshot than the source in this ZIP.

## Business workflow

Approved supplier and item records → Local Purchase Order (LPO) → LPO approval → Goods Received Note (GRN) → GRN approval → Supplier invoice matching and approval.

The application records quantities, units of measurement, receipt conditions and invoice price differences. Maker–checker controls and approval history support accountability. It does not execute payments or establish regulatory certification.

## Included capabilities

- Supplier, department and item masters with controlled access.
- LPO, GRN and invoice entry, registers and approval screens.
- Excel/CSV supplier and item imports with column mapping and units.
- GRN Excel/CSV exports; accounting interoperability is file-based.
- Dashboards, graphs, AI procurement insights and daily motivational quotes.
- Supplier contact registration, administrator linking and supplier-scoped document viewing.
- Mobile/desktop installation and limited offline access to previously visited screens.
- Delivery-problem notices available for copying or opening in a mail application.

## Project explanation

Read `PROJECT-SUBMISSION.md` for ten evaluation points and the AI-assisted development journey. Read `SETUP.md` for installation prerequisites, migration order and limitations. Read `GITHUB-UPLOAD.md` for the supplied ICAI fork-and-pull-request workflow. `TEST-EVIDENCE.md` records the checks run for this export.

## Technology

React 19, TypeScript, TanStack Start/Router, Tailwind CSS, Lovable Cloud, ExcelJS, Recharts and Lovable AI. The application targets a Cloudflare-compatible server runtime; it is not a static HTML-only website.

## Source layout

- `src/routes/`: login, masters, documents, reports and supplier portal.
- `src/components/`: shared controls and procurement screens.
- `src/lib/`: spreadsheet exchange, validations, AI, installation and tests.
- `src/integrations/`: generated Cloud client/authentication integration.
- `public/`: app icons and installation manifest.
- `supabase/migrations/`: original database schema and function permissions.
- `drizzle/migrations/`: subsequent supplier-access migration.

## Known limitations

Automatic supplier emails require sender-domain setup and implementation. Populated supplier-portal end-to-end checks and a broader security review remain pending. There is no live QuickBooks/Tally/ERP integration, payment execution, Python/R service or full offline data-entry/synchronisation feature.

Do not use production procurement data until deployment, permissions and workflow controls have been independently reviewed. No private credentials are supplied. Dependency packages retain their own licences; this submission does not grant an additional project-wide open-source licence.
