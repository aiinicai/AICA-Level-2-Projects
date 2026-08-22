# Litigation Tracker — Full-Stack Web Application

A full-stack React + Express + SQLite application for direct-tax litigation/proceeding management.

## Technology stack

- Frontend: React 18+, Vite, Recharts, Lucide React
- Backend: Node.js 22+, Express
- Database: SQLite using Node's built-in `node:sqlite`
- Authentication: server-side sessions with HttpOnly cookies
- Passwords: bcrypt hashing on the server
- Security middleware: Helmet + authentication rate limiting
- Data protection: role/tenant authorization enforced by the API
- Exports: CSV / Excel generated in the browser from API-fetched data

## Run locally

1. Install Node.js 22+.
2. Open this folder in Command Prompt / PowerShell.
3. Run:

```bash
npm install
npm run dev
```

4. Open http://localhost:5173

The browser uses the Vite proxy for `/api` calls and the Express API uses SQLite at `data/litigation.db`.

For a one-click Windows demo, run `run_app.bat`.

## Demo accounts

Admin: `admin` / `Admin@123`

Group user: `sharma_user` / `User@123`

Demo credentials are seeded by the server only. Do not use them in a production deployment.

## Security / privacy architecture

- No browser `localStorage` is used as the source of truth for application data.
- No case data is sent to an AI service.
- Password verification happens on the backend.
- Passwords are stored as bcrypt hashes, never as plaintext.
- Session identifiers are random and stored server-side as SHA-256 hashes; the browser receives only an HttpOnly, SameSite cookie.
- Admin-only operations are enforced server-side.
- Group users receive only their own group's groups/companies/proceedings from the API.
- Group users can update remarks only for proceedings belonging to their own group.
- Audit tables record authentication events and proceeding field changes.
- SQLite uses WAL mode and foreign-key constraints.
- Production deployment should use HTTPS, a managed secret, automated backups, key rotation, and an environment-specific database location.

## Important production note

This version is a proper full-stack academic project, but real tax/legal workloads should still be deployed behind HTTPS with secure server hosting, encrypted backups, restricted database access, monitoring, and an organization-approved security/privacy policy.

## Suggested project viva explanation

Request flow:

`React UI -> REST API (Express) -> Authorization -> SQLite -> Audit Log`

Login flow:

`User credentials -> POST /api/auth/login -> bcrypt verification -> server session -> HttpOnly cookie`

Data flow:

`Dashboard/Proceedings -> GET /api/bootstrap -> server-side group filter -> React state`

Mutation flow:

`React action -> PUT /api/proceedings/state or PUT /api/admin/state -> permission check -> SQLite transaction -> audit history -> refreshed API state`


## Security remediation

The Excel export dependency is pinned through npm overrides to `@keep-lts/xlsx`, a security-maintained drop-in fork of `xlsx` that backports fixes for the prototype-pollution and ReDoS advisories reported by `npm audit`. The application does not upload spreadsheet files to third-party services.

After replacing the project folder, run:

```cmd
npm install
npm audit
npm run dev
```

## Dashboard terminology update
The dashboard is intentionally framed around Direct Tax Proceedings rather than portfolio/investment terminology. Key sections include proceedings summary, assessment year-wise proceedings and demand, litigation progression by stage, status of proceedings, hearing calendar, overdue/statutory action items, demand monitoring, and nature of proceedings.


## Latest fixes
- Added a **Relevant Section** column beside Nature of Proceeding in the Proceedings register.
- Added Relevant Section directly after Nature of Proceeding in the Add/Edit Proceeding form.
- Added explicit **Demand classification** (Raised/Estimated).
- Added **Demand / Order or Estimate reference**, **Demand / Estimate date**, and conditional **Basis of estimated demand** fields.
- Dashboard demand metrics now separate **Raised demand** and **Estimated demand** and label the combined figure as **Tax demand tracked** rather than implying all estimated amounts are statutory outstanding demand.
- Demand details are included in CSV/Excel export and displayed in the Proceedings register.
