# Expense Recorder & Tracker — Scope v0.1 (draft for approval)

Status: decisions locked from MCQ rounds 1–4 (2026-10-31). Nothing built yet.

## 1. Operating model
- Operator: CA firm = **Super Admin** (runs platform, reviews all entries, does GST/TDS compliance).
- Each client = tenant with **Client Admin** + **Sub-users** (client staff, daily users).
- Review queue: **CA firm only** approves tax fields (head, TDS, RCM, HSN, ITC/17(5)).
- FY scope: **FY 2026-27 onward** only (Income-tax Act 2025, Section 393, Form 140).
- Languages: English + Hindi toggle.
- Branding: client logo + brand colour (login, header, reports).

## 2. Sub-user flow (the "never complicated" rule)
Snap → AI fills → user confirms amount/vendor → (optional) mark paid cash/bank + date → Save.
Sub-user never sees TDS sections, RCM, HSN, ITC fields. Target: < 30 seconds per invoice.

## 3. Date / permission rules
| Action | Sub-user | Client Admin | Super Admin |
|---|---|---|---|
| Add expense with past invoice-entry date | No | Yes | Yes |
| Mark payment (current or backdated date) | Yes — backdated is **flagged in audit** | Yes | Yes |
| Approve tax fields | No | No | Yes |
| Lock / unlock month | No | Lock | Lock + unlock |

> Interpretation to confirm: point 22 (past-date additions admin-only) applies to **expense entries**; backdated **payments** are allowed for sub-users but flagged.

## 4. Features in scope
Core (from brief): invoice photo capture; OCR; multi-tenant roles; auto expense head; auto TDS
section suggestion; vendor master with GSTIN + PAN validation; cash/bank payment + date; HSN tracking;
discount; FY-wise, client-wise storage; 2A/2B reco (monthly + yearly); MIS dashboard; Tally posting
by 25th of next month; alerts; Form 140 TDS reports; RCM applicability on non-GST invoices; client branding.

Approved additions: ITC 180-day reversal alert · Blocked credit 17(5) flag · e-Invoice QR scan ·
Duplicate invoice block · Audit trail · Offline capture · Month lock.

Not included (declined): MSME 43B(h) 45-day alert.

Added 2026-10-31 (user request):
- **Compliance watch (quarterly, automatic):** fetches official pages, detects changes, raises findings, flags unverified masters, quarterly checklist. Never auto-edits rates — CA approves changes.
- **Audit & health panel (super admin):** component health, scheduled jobs, error log, audit trail (backdated flags), shared-API usage & cache hits.
- **Shared paid APIs:** one account per provider for all clients; GSTIN/PAN results cached platform-wide; usage metered per client.
  Caveat: Protean OPV terms bar sharing PAN results with other entities — confirm with Protean before one shared registration.
- Error boundary: crashes show a recovery screen and are logged to the health panel.

Confirmed rule: past-dated **expense entries** admin-only; **backdated payments** allowed for sub-users, flagged in audit.

## 5. Architecture
- **Front end:** React PWA on **AWS Amplify** (camera, offline queue, push).
- **Database/auth/logic:** **Supabase** (Postgres + Row Level Security per tenant/role, Edge Functions, pg_cron). Stores data only — no images.
- **Files (invoice images/PDFs):** **Google Drive**, client-wise / FY-wise folders.
- **Mirror:** Supabase → **Google Sheets**, client-wise / FY-wise, auto-sync (for MIS/sharing; not source of truth).
- **OCR:** Vision AI — free tier first, paid when volume grows. e-Invoice QR decoded on-device first (free, exact).
- **2A/2B:** **GSP API auto-fetch** (paid; per-client OTP consent; consent can lapse/revoke → app alerts when re-auth needed). JSON upload kept as fallback.
- **GSTIN / PAN verification:** free checks first (format + checksum, PAN 4th-char type); paid API per check where free is unavailable. Vendor to be selected on quotes.
- **Tally:** connector interface with adapters → (1) monthly **XML file** import (phase 1); (2) **bridge agent** posting via Tally XML/HTTP (phase 2) — same agent designed to run beside **Tally hosted on AWS** in future. ODBC not used for posting (read-oriented).
- **n8n:** not required (Supabase Edge Functions + cron cover automation).
- **Alerts:** in-app + PWA push + email. GST reco, TDS payment (due date), TDS challan tracker, payments due > 30 days, ITC 180-day.
- **Tax rules:** TDS rates/thresholds, RCM list, 17(5) list, HSN master held as **editable master tables** (Super Admin), verified by CA — never hard-coded.

## 6. Running costs (to be quoted — no figures assumed)
GSP API (2A/2B + GSTIN search) · PAN verification API (Protean OPV ≈ ₹14,160/yr per official table, or per-check KYC vendor) ·
Vision AI beyond free tier · Supabase Pro if free limits/7-day pause become an issue · email beyond free tier.

## 7. Open items before build
1. GSP vendor selection (need quotes).
2. PAN verification route (Protean OPV vs per-check vendor).
3. Confirm Section 393 rate table with your CA team.
4. Confirm interpretation in §3.
5. Form 140 file format: final output must pass the official validation utility (FVU) — need the current NSDL/Protean RPU/FVU spec.
