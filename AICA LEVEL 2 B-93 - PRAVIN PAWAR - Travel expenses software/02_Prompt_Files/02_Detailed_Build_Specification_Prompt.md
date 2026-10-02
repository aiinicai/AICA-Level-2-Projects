# Detailed Build Specification Prompt – ABC Travel & Expense (reusable)

Use this prompt to rebuild or extend the application with any AI coding assistant or developer team.

---

**Role:** You are a senior full-stack developer building an internal corporate application.

**Build** a Travel & Expense Management Progressive Web App for **ABC Private Limited** (multinational; base currency INR).

## Technical constraints
- Backend: Node.js ≥ 22 using only built-in modules (`http`, `crypto`, `fs`, `node:sqlite`). No npm dependencies.
- Database: SQLite file `data/abc_travel.db`, schema auto-created on first run.
- Front-end: single-page app in plain HTML/CSS/JavaScript, hash routing, responsive (desktop, tablet, phone), light & dark themes.
- Charts drawn as inline SVG (no CDN), so the app works offline / on intranets.
- PWA: `manifest.webmanifest` (name, short_name, start_url, scope, display standalone, theme colour, 192/512/maskable icons, shortcuts, screenshots), service worker with offline app shell (network-only for API), `beforeinstallprompt` handling, an **Install App** button in the top menu bar, iOS "Add to Home Screen" instructions.
- One-click launchers: Windows `.bat` (auto-install Node LTS via winget), macOS `.command`, Linux `.sh`.

## Authentication & users
1. Login page with email id + password; Sign Up tab.
2. The first user to sign up becomes **Admin** automatically.
3. After that, sign-up is allowed only for email ids that the Admin has added as employees; everything else is refused.
4. Passwords: salted scrypt hash; session tokens (7-day expiry); lock after 5 failed attempts for 5 minutes.
5. Record every sign-up (success / rejected), login (success / failed / blocked), logout, password change/reset, employee add/edit and settings change in an `auth_logs` table with IP and device; Admin screen to view and filter it.
6. Admin: add/edit/deactivate employees, choose **Role from a drop-down** (Managing Director, Business Head, Sales Manager, Sales Executive, HR Head, Accountant, Travel Assistant, Finance Manager, Operations Manager, Employee, Admin + custom roles), department, grade, reporting Business Head, base city, admin flag; bulk CSV import; reset password.
7. Only Admin sees the company-wide employee dashboard / analytics / all requests.

## Pre-travel approval workflow
- Request fields: trip type (Domestic/International), from city, to city, departure & return dates (auto number of days), purpose, client, cost center, estimated flight / hotel / food / local conveyance / miscellaneous costs (auto total, "auto-fill from policy"), preferred airline & time, flight class, hotel category, travel advance.
- Advance planning policy (default 14 days): live indicator; late requests need justification and are flagged.
- Route: Employee → **Business Head** (reporting BH or any BH) → **Managing Director** → **Travel Assistant** books flight & hotel as per the **Matrix of Authority** (3/4/5 Star, flight class, max hotel rate, daily food DA, local conveyance) → **BOOKED**.
- Approvers can approve (optionally revising the approved budget), send back with comments, or reject.
- Employee can view and **edit pending requests** (draft, sent back, or pending BH before any action) and cancel before booking.
- BH's own request skips BH; MD's own request goes straight to booking; nobody approves their own request; Admin can act at any stage (logged as override).

## Post-travel expense statement
- Employee adds expense lines (date, category, description, vendor, bill no., currency + exchange rate, amount) and attaches bills (PDF/JPG/PNG/WEBP/HEIC ≤ 5 MB, camera capture on phones). Bills mandatory above a configurable limit.
- Route: **Business Head** (can edit approved amount per line with a note) → **HR Head** final approval → **Accountant** posts voucher (voucher no., GL code, cost center, payment mode, UTR, date), adjusts travel advance (net payable or recoverable) → **PAID & Closed**.
- Accountant can disburse travel advances after MD approval.

## Corporate features
In-app notifications for every step; approval queues per role (Pending Approvals / Booking Desk / Accounts Desk); workflow stepper and full audit trail; printable statement; CSV export; database backup download; policy page; configurable settings (policy numbers, roles, departments, expense categories, airlines, currencies, feature switches); editable Matrix of Authority; feature-suggestion board with voting (to add more features).

## Analytics dashboard (Admin)
Date filters; KPI tiles (spend, budgets, reimbursed, pending, average lead time, exceptions); charts: monthly spend, lead time vs average fare, employee-wise, destination-wise, airline-wise, expense category, department, workflow stage; exception report and employee summary table.

## Exception flags
Late booking, hotel above grade, hotel rate above limit, flight class above grade, long trip, claim over approved budget + tolerance, missing bills, food above DA, duplicate bill (same line or same file hash), expense dated outside trip, late claim, claim overdue.

## Deliverables
Source code, automated end-to-end test, demo data generator, summary document, prompts, examples (sample bills, CSV import, demo database, screenshots), supporting documents (workflow & ER diagrams, schema, API reference, PWA and deployment guides, test report) – packaged in one properly named ZIP.
