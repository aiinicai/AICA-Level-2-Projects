# Quarterly Billing & Invoice Automation System (MVP)

A streamlined, full-stack prototype that automates client quarterly billing based on file processing delivery logs, customer email confirmations, automated tax invoice PDF generation, email dispatch, and audit compliance logging.

---

## 🚀 Key Features

1. **Client Master Management**: Add, edit, view, and activate/deactivate clients with individual rates per file, GSTIN, and contact details.
2. **Delivery Log Excel Upload**: Ingest monthly file counts from Excel files with row-level validation (Client Code check, Month check, file count, amount, duplicate checking) and 1-click test data loader.
3. **Quarterly Billing Calculator**: Dynamically aggregate delivery logs by Financial Year and Quarter (Q1: Apr-Jun, Q2: Jul-Sep, etc.), calculating Subtotal, Tax (18% GST), and Grand Total.
4. **Automated Client Confirmation Email**: Generates formatted breakdown emails requesting `CONFIRMED` reply.
5. **Simulation & Automation Engine**: Simulate client email confirmations to automatically trigger:
   - Recording client approval in SQLite
   - Generating sequential Tax Invoice PDF (`INV-YYYY-XXXX`)
   - Dispatching invoice email with attached PDF
   - Writing full audit trail
6. **PDF Tax Invoice Generation**: High-fidelity vector PDF generation storing files in `public/invoices/`.
7. **Email Preview / Outbox**: Complete visibility of sent and simulated emails in Demo Mode without requiring real SMTP.
8. **Compliance Audit Trail**: Chronological event tracking filterable by client, date, and action.
9. **Simple Role-based Authentication**: Admin and User roles with 1-click demo logins.

---

## 🔑 Demo Login Credentials

- **Admin Account**:
  - Username: `admin`
  - Password: `admin123`
  - Access: Full configuration, recalculation, settings, and billing triggers.

- **User Account**:
  - Username: `demo`
  - Password: `demo123`
  - Access: Operational viewing and confirmation simulations.

---

## 🛠️ Local Development & Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Copy the env template and fill in real SMTP details (see "Real Email
#    Dispatch" below) - or leave DEMO_EMAIL_MODE=true to keep simulating.
cp .env.example .env

# 3. Run the frontend only (emails stay simulated in the Email Outbox)
npm run dev

#    ...or run the frontend AND the mail server together (needed for real sending)
npm run dev:all

# 4. Open in your browser
http://localhost:3000
```

---

## 📧 Real Email Dispatch

By default this app simulates every email — nothing leaves your machine, and
sent/attempted mail just shows up in **Email Preview / Outbox**. To have it
actually send:

1. Fill in `.env` (based on `.env.example`) with real SMTP credentials. The
   defaults are wired for Gmail SMTP using `soumitrabanerjee2001@gmail.com`
   as the sender — for Gmail you must generate a 16-character **App
   Password** (Google Account → Security → 2-Step Verification → App
   Passwords) and put that in `SMTP_PASS`, not your normal Gmail password.
2. Set `DEMO_EMAIL_MODE=false` in `.env`.
3. Start both processes with `npm run dev:all` (or `npm run server` in one
   terminal and `npm run dev` in another). The frontend calls
   `POST /api/send-email`, which Vite proxies to the small Express +
   Nodemailer server in `server/index.mjs`, which does the actual SMTP send.
4. In the app's **Settings** screen, turn **Demo Mode** off — this flips the
   same `demoMode` flag the backend reads, so the "Send Confirmation Emails"
   and "Simulate Client Confirmation → dispatch invoice" actions now hit real
   SMTP instead of just recording a `SIMULATED` entry.

Every attempt (`SENT`, `SIMULATED`, or `FAILED`) is still logged to the Email
Outbox and Audit Trail either way, so the workflow is fully auditable in both
modes.

Seeded client mailboxes (replace with your own in **Clients** or in
`src/lib/services/systemService.ts` → `DEFAULT_CLIENTS`):
- ABC Limited → `casoumitrabanerjee2001@gmail.com`
- XYZ Limited → `soumitrabanerjeetraining@gmail.com`
- Global Tech Solutions → `soumitrabanerjeetraining2026@gmail.com`

Demo login accounts (`admin` / `demo`) keep their original placeholder
`@example.com` addresses — those are login identities only, not email
recipients, and are unaffected by SMTP configuration.

---

## 📥 Real Client Reply Detection

By default, "the client confirmed" is triggered manually — someone reads the
client's reply and clicks **Simulate Client Confirmation**. With Demo Mode
off, the **Confirmations** screen also checks the real inbox for an actual
reply, automatically:

- Every 25 seconds while the Confirmations screen is open, or on demand via
  the **Check for Replies Now** button.
- For each client still `PENDING_CONFIRMATION`, it looks ONLY for unseen
  mail from that exact client's address (never a broad inbox scan).
- If the reply contains the word `CONFIRMED`, it triggers the same
  automation as the manual button: invoice generated, invoice email sent.
- If it contains `REJECT` / `REJECTED`, the billing is marked rejected with
  the reply text recorded as the reason.
- Anything else from that address is left untouched and unseen.

This needs IMAP access to the same Gmail account used for sending: in
Gmail, go to **Settings → See all settings → Forwarding and POP/IMAP →
enable IMAP**, then set `IMAP_HOST` / `IMAP_PORT` in `.env` (defaults to
Gmail's `imap.gmail.com:993`, reusing the same `SMTP_USER` / `SMTP_PASS`
App Password already configured above).

---

## 🧪 Complete Step-by-Step Demonstration Workflow

Follow these steps to demonstrate the complete end-to-end automation:

1. **Login**: Sign in with `admin` / `admin123` (or use the 1-click demo button).
2. **Clients**: Navigate to **Clients** to inspect seeded clients:
   - `ABC001`: ABC Limited (₹5.00/file, casoumitrabanerjee2001@gmail.com)
   - `XYZ001`: XYZ Limited (₹7.00/file, soumitrabanerjeetraining@gmail.com)
   - `GTS001`: Global Tech Solutions (₹6.00/file, soumitrabanerjeetraining2026@gmail.com)
3. **Upload Delivery Log**:
   - Navigate to **Delivery Logs**.
   - Click **"1-Click Load Sample Data"** or upload your own `.xlsx` file (sample template download available).
   - Review validation status and click **"Import Records"**.
4. **Billing**:
   - Go to **Billing** and select **Q1 FY 2026-27**.
   - Review calculated monthly breakdowns (April, May, June), Total Files, Rate, Subtotal, and 18% GST.
   - Click **"Send Confirmation Emails"**.
5. **Email Preview**:
   - Switch to **Email Preview** to view the dispatched quarterly confirmation request email.
6. **Confirmations**:
   - Go to **Confirmations** and find the client in `Awaiting Confirmation`.
   - Click **"Simulate Client Confirmation"**.
7. **Automated Invoicing & Dispatch**:
   - System automatically marks billing as confirmed, generates invoice `INV-2026-0001`, renders the PDF, and dispatches the invoice email!
   - Click **Download PDF** to inspect the tax invoice.
8. **Audit Trail**:
   - Go to **Audit Trail** to see the timestamped chain of custody from upload through invoice dispatch.

---

## 📦 Production Build & Deployment

```bash
# Build the production bundle
npm run build

# Preview production build locally
npm run preview
```

