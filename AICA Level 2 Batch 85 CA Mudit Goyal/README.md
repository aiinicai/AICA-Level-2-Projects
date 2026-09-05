# MGSG Lite — Invoicing & Attendance

A capstone submission: a working subset of the MGSG Office Management System,
covering **GST invoicing** and **staff attendance**, behind a login, installable
as a **PWA**.

It is built on the same stack as the full product and reuses its patterns and
code — the punch state machine, the GST computation, the JWT session handling,
the display-formatting rules — reduced to what two modules actually need.

This folder is self-contained. It has its own database, its own dependencies and
its own ports, and it is excluded from the parent repository's version control,
so nothing here can affect the production MGSG codebase.

---

## What it does

### Invoicing

- Raise a GST invoice against a customer typed in at billing time — this subset
  has no clients or tasks module, so the customer's name, GSTIN, address and
  place of supply live on the invoice itself.
- Any number of line items, each with description, HSN/SAC code, quantity and
  rate; the taxable value is the sum of the lines.
- **CGST + SGST** (intra-state, the combined rate split in half), **IGST**
  (inter-state, the whole rate), or **no GST**. Rates of 5 / 12 / 18 / 28%.
- Automatic invoice numbers, serial within the Indian financial year and issued
  atomically: `MGSG/26-27/0007`.
- Lifecycle: **Draft → Issued → Part paid → Paid**, plus **Cancelled**. Status
  follows the money rather than being set by hand.
- Record and remove payments (bank / UPI / cheque / cash), with the outstanding
  balance and status recalculated from the receipts each time.
- Download a formatted **PDF invoice**.
- Search by number, client or GSTIN; filter by status; live totals for billed,
  collected and outstanding.

Rules the module enforces, because they are the ones that corrupt a ledger when
they are missing:

| Rule | Why |
|---|---|
| An invoice with payments cannot be edited | Correcting a billed value is a credit note, not an edit |
| An invoice with payments cannot be cancelled or deleted | Cash received against it is already in the ledger |
| A payment cannot exceed the outstanding balance | An over-receipt is a typing slip far more often than a real advance |
| A draft cannot take a payment | Money against a bill that was never issued has nothing to settle |
| Cancelling keeps the row and its number | The number series must have no unexplained gaps |

### Attendance

- **Check in / check out from a phone**, as many times a day as the day
  actually has — someone who leaves for lunch and returns punches four times,
  not two. Each tap is its own record.
- The server decides whether a tap is an IN or an OUT from what is already on
  file, so a retry on a weak signal cannot corrupt the day.
- A second tap within a minute is refused as a stutter.
- Hours worked are the sum of the completed IN→OUT intervals, so a lunch break
  is never counted and the figure never runs ahead of the clock.
- Location is captured with each punch when the browser will give it, and the
  punch still records when it will not.
- Personal month view; **whole-firm daily register** for an admin, with CSV
  export and the ability to mark a day by hand (leave, half day, WFH) without
  disturbing the punches behind it.

### Administration & settings

Admin-only, and gated on the API as well as in the navigation:

- **Staff** — add a person (their record and their login are created together),
  edit name, phone, designation, joining date and role, deactivate or
  reactivate, reset a password. The email is the sign-in name and is fixed once
  the record exists.
- **Firm profile** — the name, address, GSTIN, email and phone printed as the
  letterhead on every invoice PDF.
- **Invoicing defaults** — the invoice number prefix, the default tax type and
  GST rate, and the payment terms in days that set a new invoice's due date.
  These are only a starting point: each invoice keeps the rates it was raised
  with, and changing a default never re-rates a bill that already exists. The
  same is true of the prefix — numbers already issued keep the prefix they were
  printed with.

Available to everyone:

- **My account** — change your own password.

### Access

- Email + password sign-in, JWT sessions, bcrypt-hashed passwords.
- Two roles: **ADMIN** and **STAFF**. Staff see their own attendance, the
  invoicing module and their own account settings; admins additionally get the
  firm-wide register, staff management and the firm and invoicing settings.
- A deactivated account stops working on its **next request**, not at token
  expiry.

### PWA

Installable to a home screen, with an app manifest, maskable icons, an offline
page, and a service worker that caches the app shell and falls back to a recent
cached response for API reads — which is the point on a phone with a weak
signal.

---

## Stack

Identical to the main MGSG application:

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, React Router 6, Tailwind CSS, Create React App |
| Backend | Node 20+, Express 4, TypeScript |
| Database | PostgreSQL via Prisma 5 |
| Auth | JWT (HS256) + bcrypt |
| PDF | jsPDF + jspdf-autotable |

---

## Running it

**Prerequisites:** Node 20 or newer, and a PostgreSQL server you can reach.

```bash
cd capstone/server
cp .env.example .env          # then point DATABASE_URL at your Postgres
npm install
npx prisma db push            # creates the schema (and the database)
npm run db:seed               # demo staff, a fortnight of attendance, 4 invoices
npm run dev                   # API on http://localhost:5100
```

In a second terminal:

```bash
cd capstone/client
cp .env.example .env          # sets the port to 3100
npm install
npm start                     # app on http://localhost:3100
```

### Demo logins

Password for all three: `Capstone@2026`

| Email | Role |
|---|---|
| `admin@capstone.local` | ADMIN |
| `anita@capstone.local` | STAFF |
| `rahul@capstone.local` | STAFF |

---

## Tests

```bash
cd capstone/server
npm test
```

137 checks. The suite boots the real Express app against the real database and
drives it over HTTP exactly as the browser does — no mocks and no direct
database calls to set state up. It covers authentication and token handling,
both role gates, GST arithmetic on all three tax types, invoice numbering,
input validation, the full invoice lifecycle, payment settlement and reversal,
list totals and filters, the punch state machine including the lunch-break case
and the double-tap guard, the registers, staff administration, settings
(including that a changed prefix reaches newly issued numbers and leaves
existing ones alone), self-service password change, and the dashboard.

Everything it creates is namespaced to the run and deleted afterwards, so it is
safe to run against the seeded demo database.

```bash
npx tsc --noEmit              # server type check
cd ../client && npx tsc --noEmit && CI=true npx react-scripts build
```

---

## Layout

```
capstone/
├── server/
│   ├── prisma/
│   │   ├── schema.prisma          10 models — users, staff, invoicing,
│   │   │                          attendance, settings
│   │   └── seed.ts                idempotent demo data
│   └── src/
│       ├── index.ts               Express app, CORS, security headers, health
│       ├── lib/
│       │   ├── prisma.ts
│       │   ├── dates.ts           IST day handling, financial year
│       │   ├── money.ts           GST computation, 2-decimal rounding
│       │   └── settings.ts        the singleton settings row
│       ├── middleware/auth.ts     JWT verification, role gates
│       ├── controllers/           auth · staff · invoice · attendance ·
│       │                          dashboard · settings
│       ├── routes/
│       └── scripts/apiTest.ts     the end-to-end suite
└── client/
    ├── public/                    manifest, service worker, offline page, icons
    └── src/
        ├── api/index.ts           typed API client
        ├── contexts/              AuthContext · SettingsContext
        ├── components/            Layout · Modal · InvoiceForm · StatusBadge
        ├── pages/                 Login · Dashboard · Invoices · Attendance ·
        │                          AttendanceRegister · Staff · Settings
        └── utils/                 format · invoicePdf · errorMessage
```

---

## What was deliberately left out

The full MGSG system also carries clients, tasks, timesheets, credit notes,
receivables and ageing, TDS tracking, bank reconciliation, retainer schedules,
payroll, leave, reimbursements, litigation, tickets, chat, document management,
email automation and multi-tenancy. None of it is here.

Two consequences are visible in the code and are design decisions rather than
gaps:

- **Customer details are typed onto each invoice.** With no clients module there
  is nothing to point a foreign key at, so the invoice carries the details it
  needs to be a valid tax invoice on its own.
- **There is no tenant scoping.** The production system scopes every row by
  tenant in three layers; a single-firm submission has one tenant and does not
  need any of them. Settings are a single row for the same reason — one firm,
  so `Settings` has a fixed id of 1 and every read and write is an upsert
  against it.

---

## Formatting conventions

Carried over from the parent project's `CLAUDE.md`, because a submission that
shows money and dates inconsistently reads as unfinished:

- Amounts on screen are rounded to the nearest rupee, with no decimals — ₹1,234
- Amounts in PDFs carry two decimals — ₹1,234.50
- Dates read `dd-MMM-yy` everywhere — 19-May-26
- Values are stored precisely in the database; rounding happens only on display
