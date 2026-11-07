# Setup and deployment notes

## For evaluators
Source inspection and automated tests do not require access to the author's live records. The demo URL is in the README. Do not request or share production account passwords.

## Independent development setup
1. Install a current Node.js version compatible with Vite and Bun (the repository includes `bun.lock`).
2. Open a terminal in this extracted project folder and run `bun install`.
3. Provision a separate Lovable Cloud backend. This archive does not provision one or copy existing accounts/data.
4. Copy `.env.example` to `.env` and configure the public connection values and matching server connection values for your own environment. In Lovable Cloud these are managed by the platform. Do not reuse the author's live backend.
5. Configure email/password authentication and the new deployment's confirmation and password-reset redirect URLs. Hosted authentication settings are not included in the archive.
6. Apply the database SQL to a fresh compatible backend in the exact order below, using authorised migration tooling. Have a developer review the scripts first.
7. Run `bun run dev` and open the localhost address printed by Vite.

The environment template contains variable names, not usable credentials. Private AI credentials belong only in the host's secure server configuration. A Lovable Cloud service-role key is not available for users to retrieve; do not attempt to copy one from the original deployment.

## Database script order
1. `supabase/migrations/20260817103134_341a4d88-4777-4d08-bb1e-0d7d84f0e447.sql` — initial schema, policies, workflows and starter data.
2. `supabase/migrations/20260817103147_d195aac8-7e73-4f5d-af96-2539c30932d7.sql` — function execution permissions.
3. `drizzle/migrations/0000_supplier_portal_access.sql` — supplier account mapping and scoped access.

These scripts are split across two historical migration folders. Do not run only one folder, blindly run schema push, or reapply the scripts to an existing database. The supplier-access script changes original read policies; all scripts are required. The included Drizzle schema/snapshot is not a substitute for the SQL workflow functions, policies and triggers. No fresh-database replay was performed for this export.

## Initial users and demonstration
The current signup trigger grants initial internal administrative roles to the first eligible internal registration; later internal registrations receive MAKER. Supplier registrations receive no internal roles and require an administrator to link an ACTIVE supplier record. Register the initial internal user in a controlled environment, review role assignment and use separate maker/approver accounts for demonstration. Do not open an unreviewed fresh backend to public registration.

Suggested demonstration: create/approve a supplier → create an LPO → approve with another user → receive goods → approve GRN → enter and review invoice → export GRN. Separate supplier-account testing is still needed.

## Tests
Run `bunx vitest run src/lib/*.test.ts`. The seven included test files cover spreadsheet mapping/export, CSV parsing, master validation, supply notices, install/offline guards and quotes. They are not full database or end-to-end workflow tests.

## Hosting and optional services
The server configuration targets Cloudflare-compatible deployment through TanStack Start. GitHub stores code; GitHub Pages alone does not host this full-stack application. `bun run build` is the provided production build command for a separately configured environment. No standalone build or deployment of this exported archive was verified.

AI Insights require an authorised Lovable AI server credential and available credits. Installing this source does not grant gateway access. Automatic supplier email sending is not implemented; sender-domain setup is a prerequisite for that future feature. Installation/share links currently point to the author's published URL; review them when deploying a separate copy.

## Security and data
The ZIP excludes `.env`, repository history, private platform metadata, account sessions, business records, dependency folders and generated build output. Review authentication, role grants, approved-document controls and remaining security findings before production use. Public installation icons and source SQL seed data are included.
