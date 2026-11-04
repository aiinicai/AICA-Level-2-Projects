# Vouchr (working name) — Expense Recorder & Tracker PWA

Snap a bill → staff confirm amount → CA firm reviews tax fields → monthly Tally/Sheets posting.

## Run it locally
```
npm install
npm run dev        # http://localhost:5173 — demo mode, data stays in this browser
npm test           # unit tests for GSTIN/PAN, TDS/RCM/17(5) engine, Tally XML, e-invoice QR
npm run build      # production PWA in dist/
```

> v0.2: full requirement-by-requirement audit, fixes and live test results are in **AUDIT.md**.

## What works today (v0.1 table — see AUDIT.md for the current status)
| Area | Status |
|---|---|
| Staff snap / type flow, bilingual EN/HI, bill-total entry, discount, cash/bank + date | Working |
| e-Invoice QR auto-fill from photo (free, on-device) | Working |
| Duplicate block (same vendor + bill no., or same photo) | Working |
| Past-dated entries admin-only; backdated payments allowed + flagged | Working (UI) + enforced in DB triggers |
| Month lock (admin locks, CA unlocks) | Working |
| Auto expense head, TDS (Sec 393 masters), RCM, 17(5) suggestions | Working — masters **unverified** |
| CA review queue, tax masters with verify sign-off | Working |
| MIS dashboard, dues, alerts (30-day, ITC 180-day, TDS due, GST reco) | Working (in-app) |
| Tally XML export (Journal vouchers) | Working — test-import on a copy of each company first |
| Compliance watch (quarterly) | UI demo + server function written; needs Supabase |
| Audit & health panel (health, errors, audit trail, shared APIs) | Working on demo data |

## Not built yet (needs your inputs / accounts)
- Supabase project + wiring the app to it (schema is ready in `supabase/migrations`).
- Real sign-in (email OTP), staff invites.
- Google Drive image upload & Google Sheets mirror (needs a Google Cloud service account).
- AI OCR Edge Function (needs provider choice + key).
- GSP 2A/2B fetch, GSTIN & PAN live verification (need vendor selection & quotes).
- Push & email delivery.
- Form 140 FVU-ready file (needs current official RPU/FVU spec) — CSV working sheet exists.
- Tally bridge agent (phase 2).

## Layout
- `src/lib` — pure, tested logic (validators, rules engine, Tally XML, QR, alerts)
- `src/data` — types, masters (tax tables), demo seed, store
- `src/pages` — screens; `src/ui` — shell & shared components
- `supabase/migrations` — tables, RLS per client/role, audit triggers, business-rule triggers
- `supabase/functions/compliance-watch` — quarterly official-page change detector

## Renaming
"Vouchr" is used by a Canadian fintech (Vouchr Ltd). Rename in `src/brand.ts`, `vite.config.ts` (manifest) and `index.html`.
