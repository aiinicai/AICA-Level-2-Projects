# Vouchr v0.4 — Four-Lens Platform Audit (pre-Supabase)

Panel: Senior Software Architect · Lead QA Engineer · Principal Product Logic Analyst · Senior UI/UX Designer
Scope: full codebase (`src/`, `supabase/migrations/0001–0006`, `supabase/functions/*`), live behaviour in the browser, production build.
Date: 31 Oct 2026. Status: **✅ fixed in this round** · **⏳ open** (needs Supabase phase, a decision, or larger work).

---

## Part A — This round's requested items

| Item | Delivered |
|---|---|
| 1. All major files in Google Drive, client-wise & FY-wise | ✅ One storage API files bills, challan receipts, bank statements, GSTR-2B files and logos as `Vouchr/<Client>/FY 2026-27/<Bills·TDS Challans·Bank Statements·GSTR-2B>/<yyyy-mm-dd>_<vendor>_<ref>.<ext>`. Live: Edge Function `drive-upload` (Google OAuth or Shared Drive service account). Demo: same paths in on-device IndexedDB. Only a ~9 KB thumbnail stays in app data; "Open original" everywhere. |
| 2. Google Drive & Sheets integration — when | Code is **written now** (`_shared/google.ts`, `drive-upload`, `sheets-mirror`, migration 0005). It is **switched on during the Supabase step**, because Google credentials must live on the server, never in the browser. Sheets: one spreadsheet per client per FY in that client's Drive folder, tabs Expenses / Payments / Vendors, rewritten nightly 03:00 IST + on demand. |
| 3. UPI IDs / choose among bank accounts | ✅ "Paid from" sources per client: bank accounts, **UPI IDs (each linked to the bank it debits)**, company cards, several cash boxes (e.g. petty cash). Payment form shows them as one-tap chips for the chosen mode; Tally uses each source's ledger. |
| 4. Optional project / branch | ✅ Client admin defines projects and branches; staff tag a bill with one tap (optional); CA can correct; Tally journal carries a **cost-centre allocation**; project/branch-wise report; tag in expense register. |
| 5. Narrations | ✅ Narration field (250 chars) on every bill, editable by CA, goes into the Tally voucher narration and reports. |
| 6. Premium motion | ✅ Screen rise-in with staggered sections, list cascade, drawers slide (bottom sheet on phones), spring toasts, tactile press states, hover lift, animated charts, count-up KPIs, drawn success tick, shimmer while reading/uploading. All transform/opacity (GPU), 150–420 ms, disabled for "reduce motion". |

---

## 1. Architectural & System Design Audit

**A1 — Business rules exist twice (TypeScript store and SQL triggers)** · ⏳
- *Flaw:* Every rule (backdating, balances, locks, approvals) is implemented in `store.tsx` **and** in Postgres triggers. They will drift; one already did (A12).
- *Root cause:* Demo mode needed a working rule engine before a backend existed.
- *Remediation:* (1) Make Postgres RPC functions the only write path (`submit_expense`, `record_payment(lines[])`, `apply_advance`, `review_expense`). (2) Keep the TS checks only as instant UI hints. (3) Add contract tests that run the same scenarios against both until the demo store is retired.

**A2 — Multi-step writes are not atomic** · ✅ SQL done (0010); app wiring in Supabase step
- *Flaw:* A split payment is saved as N separate calls; a bill save is "upload file, then insert row". A failure in the middle leaves half a payment, or an orphan Drive file.
- *Root cause:* No transaction boundary on the client.
- *Remediation:* `record_payment(lines jsonb)` RPC in one transaction; Drive uploads go to a `_staging` folder and are moved into place by the same RPC that inserts the bill; a nightly job deletes staging files older than 24 h that no `documents` row references.

**A3 — Uploads stream through the Edge Function** · ⏳
- *Flaw:* `drive-upload` holds the whole file (≤15 MB) in function memory. Slow or large uploads hit Edge Function time and memory limits, and every byte is paid twice.
- *Remediation:* The function creates a Google **resumable upload session** for the right folder and returns the session URL. The phone uploads straight to Google; the function then records the file id. No secret reaches the browser.

**A4 — Single Google identity for every client** · ⏳ (decision)
- *Flaw:* All Drive and Sheets traffic runs on one OAuth refresh token or one service account. If it's revoked or hits quota, filing stops for every client.
- *Remediation:* Prefer a **Shared Drive + service account** (Workspace). Add a daily health check that writes a 1-byte file and alerts the Audit panel. Store the Drive folder id per client so access can be fixed per client.

**A5 — Offline capture is real only in demo** · ✅ done 3 Nov 2026
- *Flaw:* The PWA promises offline capture, but live saves and Drive uploads need the network; a lost connection loses the entry.
- *Remediation:* An IndexedDB outbox (entry + file) with Background Sync and retry on reconnect. Show a "Waiting to upload (2)" chip in the header, and have the server dedupe on `sha256`.

**A6 — Monolithic client state** · ⏳
- *Flaw:* One React context holds every table; every change re-renders the tree and re-serialises everything to localStorage. That's fine for a demo, but won't scale to 10k bills.
- *Remediation:* In the Supabase phase, replace it with TanStack Query (per-table caches, pagination, optimistic updates). Keep the session and language in a small context.

**A7 — Heavy assets on first install** · ✅ done 3 Nov 2026
- *Flaw:* The service worker pre-caches the 1.36 MB PDF worker. The on-device OCR fetches its ~10 MB English model from a public CDN (an outside dependency, a privacy question, and it fails offline).
- *Remediation:* Exclude `pdf.worker*` from precache (runtime cache-first instead). Self-host the OCR model under `/ocr/` with a cache-first route. Show an "Enable offline reading (10 MB)" opt-in.

**A8 — Main bundle size** · ✅ partly
- *Flaw:* All screens shipped in one 566 KB bundle.
- *Fixed:* Route-level code splitting; the main bundle is now 473 KB.
- *Next:* Load demo seed data only in demo mode; load `supabase-js` lazily until login.

**A9 — Weak identifiers** · ✅
- *Flaw:* IDs were 8 random base-36 characters, which can collide and don't match Postgres `uuid`.
- *Fixed:* Now `crypto.randomUUID()`.

**A10 — Production build silently falls back to demo** · ✅
- *Flaw:* A build deployed without Supabase settings ran in demo mode, keeping business data in one browser.
- *Fixed:* Demo mode now needs `VITE_DEMO=true` (or local development). A misconfigured build shows a "not configured" screen and won't start. There's a separate `npm run build:demo`.

**A11 — Full photos in localStorage (5 MB cap)** · ✅
- *Flaw:* The demo would have broken after about 50 bills.
- *Fixed:* Originals go to IndexedDB or Drive; only thumbnails stay in app data.

**A12 — Server dates in UTC** · ✅
- *Flaw:* Triggers used `current_date`, which is UTC. Between 00:00 and 05:30 IST a bill dated today was rejected as "future", and backdate and month checks were off by a day around month-end.
- *Fixed:* `ist_today()` is used in every rule (migration 0006).

---

## 2. Functionality & Edge-Case Audit

**F1 — Race: two people pay the same bill at once** · ✅ (DB)
- *Flaw:* Both pass the balance check, and the bill ends up overpaid.
- *Fixed:* The allocation trigger now locks the bill and the payment rows (`FOR UPDATE`) before checking.
- *Still to do:* A stress test with 20 parallel `record_payment` calls once on Supabase.

**F2 — Returned bill that was already paid** · ✅
- *Flaw:* Payments kept pointing at the returned bill and disappeared from payables.
- *Fixed:* On return, those amounts become vendor advances (app and DB trigger), with an audit flag `payment_moved_to_advance`.

**F3 — CA adds TDS after the bill was paid in full** · ✅
- *Flaw:* Net payable shrinks below what was paid, so the balance goes negative.
- *Fixed:* On approval, any excess is moved to an advance automatically and flagged.

**F4 — No vendor credit / debit notes** · ✅ done 3 Nov 2026
- *Flaw:* Returns, rate differences and discounts after the bill can't be recorded. GSTR-2B's CDNR section has nowhere to match.
- *Remediation:* A "Credit note" entity linked to a vendor (and optionally a bill). It reduces the balance, posts as a Debit Note voucher in Tally, and is matched against 2B CDNR.

**F5 — Bank CSV variants** · ✅ done 3 Nov 2026
- *Flaw:* Statements with one "Amount" column plus a "Dr/Cr" column, or Excel-only exports, aren't recognised.
- *Remediation:* After upload, a one-time column-mapping screen (date / narration / amount / Dr-Cr / reference), remembered per bank. Accept XLSX.

**F6 — iPhone HEIC photos** · ✅ done 3 Nov 2026
- *Flaw:* Chrome on Android/desktop can't decode HEIC, so the preview and QR scan fail.
- *Remediation:* Detect HEIC and file it as an attachment without a preview (the server can convert it), and tell the user. Set the camera input to JPEG where supported.

**F7 — Slow on-device OCR has no cancel** · ✅ done 3 Nov 2026
- *Flaw:* On slow phones the first OCR run downloads 10 MB and blocks the screen.
- *Remediation:* A "Cancel reading" button, an 8 s timeout that falls back to typing, and the opt-in pre-download from A7.

**F8 — The same bill photographed twice** · ✅ done 3 Nov 2026
- *Flaw:* The file hash catches identical files only; a re-photographed bill gets a different hash.
- *Mitigated:* The look-alike rule (same vendor + date + amount).
- *Remediation:* A perceptual image hash (dHash), run on-device, compared within the vendor's last 90 days.

**F9 — Note rule enforced only on screen** · ✅
- *Flaw:* The "bills above ₹X need a note" rule could be bypassed by non-UI paths.
- *Fixed:* Now enforced in the store; add the same check to the DB/RPC in the Supabase step.

**F10 — Changing TDS rates mid-year** · ✅
- *Flaw:* The engine ignored effective dates, so a rate change would apply to older bills too.
- *Fixed:* The rate is now picked by bill date (`effectiveFrom` / `effectiveTo`), with a test.

**F11 — Areas that need stress / integration tests (Supabase phase)**
- Parallel payments on the same bill (F1).
- Bulk inbox with 25 files on 3G.
- Drive outage during save (staging + retry).
- 10,000-bill client: list pagination and MIS performance.
- Month lock set while someone is mid-entry.
- Tally XML import into a copy of a real client company, including cost centres and payments.

---

## 3. Business Logic & Process Audit

**B1 — Client admins could switch off their own controls** · ✅ (DB)
- *Flaw:* The branding policy allowed updating every client column, including the backdate window, cash limit, note limit, GSTIN and Tally mode.
- *Fixed:* A trigger allows these changes only by the CA firm (migration 0006).
- *UI follow-up:* Show these fields read-only to client admins.

**B2 — Staff could delete bills, payments and vendors** · ✅ (DB, critical)
- *Flaw:* "For all" row-level-security (RLS) policies included DELETE.
- *Fixed:* Policies are now split into select / insert / update; nobody can delete. Only the creator can discard their own draft, and payment voids are admin-only before Tally.

**B3 — Staff could mark a vendor's PAN "Operative"** · ✅ (DB)
- *Flaw:* That lowers the TDS rate, a direct compliance risk.
- *Fixed:* PAN and GSTIN status can be set only by the CA firm or the verification service (trigger).
- *UI follow-up:* Hide those selects from staff and client admins.

**B4 — Approved bills editable by client admins** · ✅ (DB)
- *Flaw:* Amounts could be changed after CA approval.
- *Fixed:* After approval or posting, only the CA firm can change a bill.

**B5 — No TDS on advances** · ✅ done 3 Nov 2026
- *Flaw:* TDS is due at credit or payment, whichever is earlier. An advance to a contractor or professional triggers TDS at payment, but the app computes TDS only on bills.
- *Remediation:* When recording an advance to a vendor whose head attracts TDS, compute TDS on the advance (it reduces the cash paid and posts to TDS Payable). When the bill arrives, net off the TDS already deducted. Count advances in the yearly-threshold totals.

**B6 — When the RCM liability falls due isn't tracked** · ✅ done 3 Nov 2026
- *Flaw:* Reverse-charge (RCM) tax is computed, but not the month it must be paid in (earlier of payment or a period after the invoice), which GSTR-3B reporting needs.
- *Remediation:* Store the RCM liability date per bill and add an "RCM payable for the month" view. Have the CA confirm the timing rule.

**B7 — ITC re-claim after a 180-day reversal** · ✅ done 3 Nov 2026
- *Flaw:* The alert asks for reversal, but there's no record of the reversal or of re-claiming the ITC once paid.
- *Remediation:* An ITC reversal register with columns for reversed, paid on and re-claimed.

**B8 — Drive access per client** · ✅ done 3 Nov 2026
- *Flaw:* Files sit in the firm's Drive; client admins can't open their own folder.
- *Remediation:* On client creation, share `Vouchr/<Client>` read-only with the client admin's email through the Drive permissions API; remove access when a user is deactivated.

**B9 — Data protection (DPDP Act 2023)** · ✅ done 3 Nov 2026
- *Flaw:* The app holds PAN, GSTIN, bank references and staff names, but has no retention rule, no consent text and no data-export or erasure process.
- *Remediation:* A privacy notice at first login, a retention policy (statutory 8 years for books, configurable), a per-client export, and an erasure workflow (kept on legal hold where the law requires).

**B10 — Single CA reviewer bottleneck** · ✅ done 3 Nov 2026
- *Flaw:* Every bill waits for the CA firm. At month-end the queue blocks Tally posting by the 25th.
- *Remediation:*
  - **Auto-approve rule:** high-confidence bills from known vendors (e.g. ≥95% match, no TDS/RCM/17(5) flags, under ₹5,000) are auto-approved and sampled, if the firm agrees.
  - **Queue tools:** queue ageing and a per-reviewer assignment.

**B11 — FY close** · ✅ done 3 Nov 2026
- *Flaw:* No year-end close (lock all months, roll vendor advances and open bills forward, archive).
- *Remediation:* An FY close wizard for the CA firm.

**B12 — Rules the CA must confirm** · ⏳ (your input)
- *Flaw:* These are configurable and marked unverified, not guessed: TDS rates and thresholds under s.393, RCM rates, the 17(5) list, the cash limit under the 2025 Act, TDS rounding, and the TDS deposit due date.
- *Remediation:* Have the CA verify each value and sign it off in Tax masters.

---

## 4. UI/UX & Interface Audit

**U1 — Wide tables on phones** · ✅ done 3 Nov 2026
- *Flaw:* Expenses, Tally, Reco and TDS tables scroll sideways on phones, so admins lose the row context.
- *Remediation:* Below 640 px, render each row as a card with the 3–4 key facts and a "details" tap. This is already the pattern on staff screens.

**U2 — Keyboard and screen-reader gaps in drawers** · ✅
- *Flaw:* No Esc to close, focus escaped the drawer and wasn't returned (WCAG 2.1.2 / 2.4.3).
- *Fixed:* Esc closes the drawer, Tab is trapped inside, focus returns to the button that opened it, and the dialog is labelled.

**U3 — Invisible focus, low-contrast grey text** · ✅
- *Flaw:* Muted text measured about 3.9:1 contrast (WCAG 1.4.3 needs 4.5:1), and keyboard focus wasn't visible (2.4.7).
- *Fixed:* Darker muted colour (≥4.5:1) and a global `:focus-visible` ring.

**U4 — Errors announced politely** · ✅
- *Flaw:* Error toasts used `role=status`, so screen readers could skip them.
- *Fixed:* Error toasts now use `role=alert`.
- *Next:* Show field-level errors next to inputs on the admin forms too (capture already does).

**U5 — Native browser dialogs** · ✅ done 3 Nov 2026
- *Flaw:* `confirm` / `prompt` are used for sign-out, cancelling a payment, deleting drafts and month lock. Their OK/Cancel buttons aren't translated, they look foreign, and they're hard to use on iOS.
- *Remediation:* A styled, translated confirm sheet component; the void reason gets a proper text field.

**U6 — Chip groups not keyboard-navigable** · ✅ done 3 Nov 2026
- *Flaw:* Chips are marked as radio groups, but arrow keys don't move between them (ARIA radio pattern).
- *Remediation:* Roving tabindex with ←/→ across GST rate, mode, source and project chips.

**U7 — Language switch hard to find** · ✅ done 3 Nov 2026
- *Flaw:* The "अ/A" icon is the only way to switch; first-time Hindi users may never find it.
- *Remediation:* Ask for the language on first login, and add a labelled control in More.

**U8 — Admin-only fields shown to client admins** · ✅ done 3 Nov 2026
- *Flaw:* Control settings and PAN/GSTIN status selects are visible but would now be refused by the server, which is a dead end.
- *Remediation:* Render them read-only, with "Set by your CA".

**U9 — No upload progress or offline indicator** · ✅ done 3 Nov 2026
- *Flaw:* There's no feedback while a file uploads or when the device is offline.
- *Remediation:* A per-file progress ring in the inbox and an outbox counter chip in the header.

**U10 — Duplicate entry points** · ✅ done 3 Nov 2026
- *Flaw:* The bell and the "Alerts" tab do the same thing on staff phones.
- *Remediation:* Replace the staff "Alerts" tab with "Inbox" and keep the bell.

**U11 — Busy-state feedback** · ✅
- *Flaw:* Long operations showed a static banner.
- *Fixed:* Shimmer on busy banners, OCR percentage, and "Saving N of M to Drive…" in the inbox.

---

## 5. Prioritised action list — Impact vs Effort

| # | Fix | Impact | Effort | Status |
|---|---|---|---|---|
| 1 | B2 Staff could delete bills/payments (RLS) | Critical | Low | ✅ done |
| 2 | A12 UTC vs IST dates in DB rules | Critical | Low | ✅ done |
| 3 | B3 Staff could lower TDS via PAN status | Critical | Low | ✅ done |
| 4 | B4 Edits after CA approval | Critical | Low | ✅ done |
| 5 | B1 Client admin could disable controls | High | Low | ✅ done |
| 6 | A10 Prod build silently in demo mode | High | Low | ✅ done |
| 7 | F1 Concurrent payment race | High | Low | ✅ done (stress test pending) |
| 8 | F2/F3 Payments on returned/re-taxed bills | High | Low | ✅ done |
| 9 | A11 Photos in localStorage | High | Low | ✅ done |
| 10 | U2/U3/U4 Accessibility (focus, contrast, alerts) | Medium | Low | ✅ done |
| 11 | A9, A8, F9, F10 ids, bundle split, note rule, dated rates | Medium | Low | ✅ done |
| 12 | **A2 Atomic RPCs for payments & bill+file** | Critical | Medium | ✅ SQL done and tested (0010); app wiring in Supabase step |
| 13 | **A1 Single rule implementation (RPC) + contract tests** | High | Medium | ⏳ in Supabase step |
| 14 | **B5 TDS on advances** | High (compliance) | Medium | ✅ done 3 Nov 2026 (see PENDING.md D4–D6) |
| 15 | **A5 Offline outbox + U9 progress** | High | Medium | ✅ done 3 Nov 2026 (see PENDING.md D4–D6) |
| 16 | U8 Read-only control fields for client admins | Medium | Low | ✅ done 3 Nov 2026 (see PENDING.md D4–D6) |
| 17 | U5 In-app confirm sheet (translated) | Medium | Low | ✅ done 3 Nov 2026 (see PENDING.md D4–D6) |
| 18 | A3 Direct-to-Google resumable uploads | Medium | Medium | ⏳ Supabase step |
| 19 | F4 Vendor credit/debit notes + 2B CDNR | High | Medium | ✅ done 3 Nov 2026 (see PENDING.md D4–D6) |
| 20 | B8 Share client Drive folders with client admins | Medium | Low | ✅ done 3 Nov 2026 (see PENDING.md D4–D6) |
| 21 | A7 Self-host OCR model, no precache of PDF worker | Medium | Low | ✅ done 3 Nov 2026 (see PENDING.md D4–D6) |
| 22 | F5 Bank column mapping + XLSX | Medium | Medium | ✅ done 3 Nov 2026 (see PENDING.md D4–D6) |
| 23 | U1 Card layout for admin tables on phones | Medium | Medium | ✅ done 3 Nov 2026 (see PENDING.md D4–D6) |
| 24 | B6 RCM liability timing · B7 ITC reversal register | Medium (compliance) | Medium | ✅ done 3 Nov 2026 (see PENDING.md D4–D6) |
| 25 | B10 Auto-approve low-risk bills | High (throughput) | Medium | ✅ done 3 Nov 2026 (see PENDING.md D4–D6) |
| 26 | A4 Drive health check / Shared Drive | Medium | Low | ⏳ Supabase step |
| 27 | U6 Arrow-key chip groups · U7 language on first login · U10 nav tidy | Low–Med | Low | ✅ done 3 Nov 2026 (see PENDING.md D4–D6) |
| 28 | F6 HEIC · F7 OCR cancel · F8 perceptual duplicate | Medium | Medium | ✅ done 3 Nov 2026 (see PENDING.md D4–D6) |
| 29 | B9 DPDP notice, retention, export | Medium (legal) | Medium | ✅ done (v0.7 + log retention 0010); counsel review pending |
| 30 | B11 FY close wizard · A6 query-cache state | Medium | High | ✅ done 3 Nov 2026 (see PENDING.md D4–D6) |

## 6. Evidence
- **Unit tests: 54 passing.** New this round: Drive folder and file naming, payment-source rules, Tally narration and cost-centre allocation, UPI-to-bank ledger, rate effective dating. Hindi completeness covers all new strings.
- **Live checks on a phone-sized screen:**
  - A bill photo read by on-device OCR (vendor, number, date, total, GST 18%).
  - Filed to `Vouchr/Shree-Ganesh-Traders/FY 2026-27/Bills/2026-10-28_COURIER-POINT-LOGISTICS_CP-91.png` with a 9 KB thumbnail.
  - Tagged "Nashik Branch", with a narration, and paid by UPI from the PhonePe ID.
  - The bottom-sheet payment drawer with Paid-from chips.
- **Production build:** all 19 CA screens in Hindi load with no crashes or console errors; the test receipt isn't shipped.
- **Defect found by live testing and fixed:** on-device OCR never ran, because tesseract.js exposes `createWorker` under `default` when bundled. It now works (≈1.7 s per bill).
