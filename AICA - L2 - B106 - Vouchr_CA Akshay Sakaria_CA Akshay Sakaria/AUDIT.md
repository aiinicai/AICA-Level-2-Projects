# Vouchr v0.3 — Audit Report (pre-Supabase)

Date: 31 Oct 2026 · Covers your round-3 points 1–11. Previous rounds: v0.1 build, v0.2 audit (kept in git history once the repo exists).
Status keys: ✅ done & tested · 🟡 done in app, needs backend/vendor to go live · ⛔ needs your input

## 1. Your round-3 points

| # | Point | Result |
|---|---|---|
| 1 | Snap/upload challans, auto-fill everywhere | ✅ **Challan receipts**: PDF read on-device (pdf.js) or photo via on-device OCR (tesseract.js) → BSR, challan no., deposit date, amount, CIN, ITNS, TAN. Built and tested against a **real e-Pay Tax receipt**. ✅ **Bills as PDF**: text layer read + e-invoice QR inside PDF. ✅ **Photos**: QR → AI OCR (when connected) → free on-device OCR fallback. ✅ **Bank statement CSV** → payments matched to bills. ✅ **Bulk upload inbox**. ✅ GSTIN → state & IGST/CGST auto. |
| 2 | Hindi on the entire platform | ✅ Every screen, menu, alert, error message, toast, date and month name. **An automated test now fails the build if any screen text lacks Hindi** (≈600 strings). Live sweep of all 19 screens: no English left except tax acronyms, data and names. |
| 3–4 | Learn from Zoho / QuickBooks (UX + function) | ✅ See §2. Researched: Zoho Books multi-bill & partial payments, vendor advances, bulk pay; Zoho Expense duplicate detection & policies; QuickBooks pay-bills, vendor credits, bank-feed matching (community docs). |
| 5 | Coverage of all original points | ✅ See §4 |
| 6, 8 | Audit logic & UI/UX | ✅ See §3 (12 defects found by testing and fixed) |
| 7, 11 | GitHub / PyPI research, enhancements | ✅ pdf.js, tesseract.js, invoice2data approach (PyPI), open-source 2B parser layout, Tally SDK conventions. All approved enhancements built (§2). |
| 9 | Live tests with dummy data | ✅ See §5 |
| 10 | Paid in several modes, on several days, partly | ✅ See §2 "Payments" |

## 2. What was built this round

**Payments (point 10, Zoho Books / QuickBooks model)**
- One payment can settle **several bills**; one bill can be paid in **many parts, modes and dates**.
- Modes: Cash · UPI · Bank transfer · Cheque · Card, each non-cash payment tied to a **client bank account** (mapped to its Tally ledger).
- **Vendor advances**: extra money is kept as an advance and can be **applied to later bills**.
- **Pay bills**: tick several bills of a vendor → one drawer, "Pay all in full", per-bill amounts, "+ Add another payment (other mode or date)" — lines are spread oldest-bill-first.
- **Cancel a wrong payment** (admins, before Tally posting, reason kept in audit).
- Flags: cash above the daily limit (live warning before saving), paid before bill date, backdated.
- Tally: Payment vouchers use the vendor's Tally ledger and the actual bank/cash ledger; narration lists the bills and any advance.

**Payables (QuickBooks/Zoho)**
- Bill status: Unpaid · Partially paid · Overdue · Paid. **Vendor credit days** (default per client) → due dates.
- **Ageing** buckets (not due, 1–30, 31–60, 61–90, 90+), on Dues, MIS and as a report.
- **Vendor statement** report (bills, payments, advances, running balance). Payment register now shows mode, account, bills settled, flags.
- WhatsApp reminder link for overdue bills (free, no API).

**Auto-fill & intake**
- Inbox: upload up to 25 files at once → drafts → "Complete & submit". Duplicate files skipped (also within the same batch).
- Bank statement: CSV from net banking → each debit matched by vendor name, bill number in narration, or exact amount; already-recorded debits are recognised and skipped.
- Challans: snap/upload → fields filled; wrong challan type (ITNS ≠ 281) and impossible dates are flagged.

**Controls (Zoho Expense ideas)**
- **Look-alike bills** (same vendor + date + amount, even with a different bill no.) → "Same bill / Different bill"; CA sees the confirmation.
- Bills above a client-set amount require a "what was it for" note.
- Client settings: credit days, cash limit, note limit, cash ledger, bank accounts.

## 3. Defects found during this round's testing — all fixed

| Found by | Defect | Fix |
|---|---|---|
| Live test | After applying an advance, the pay drawer kept the old amount → would have created a false second advance | Amounts resync after the advance |
| Live test | Same file uploaded twice in one batch created two drafts | Batch-level duplicate check |
| Live test | Challan receipt for **self-assessment tax (ITNS 280)** accepted as TDS | Warning shown |
| Live test | Challan dated 2024 could be booked to Aug 2026 TDS | Blocked (app + DB) |
| Live test | Cash-limit breach only flagged after saving | Live warning before saving |
| Live test | Demo bills without a vendor record broke bank matching | Every bill has a vendor; seed fixed |
| Unit test | Invoice reader guessed a vendor name from non-invoice text | Name only guessed when invoice fields exist |
| Hindi sweep | Dates/months stayed English ("Sept") | Dates follow the language |
| Hindi sweep | Expense head names, status words, Lock/Edit/Activate etc. English | Translated |
| Hindi sweep | "Overdue" Hindi label wrapped on phones | Shortened |
| UX review | Empty ageing tiles took 3 rows on phones | Only non-zero buckets shown |
| UX review | "1 days overdue" | Singular handled |
| Code review | `recordPayment` returned a value built inside a React state updater (could be empty) | Built before the update |

## 4. Original requirements — status now

| # | Requirement | Status |
|---|---|---|
| 1 | Invoice photo capture | ✅ camera, gallery, PDF, bulk inbox |
| 2 | OCR | ✅ free on-device (QR, PDF text, tesseract) · 🟡 AI OCR when key is set |
| 3 | Super admin / admin / sub-users | ✅ demo · 🟡 real login with Supabase |
| 4 | Auto expense head | ✅ |
| 5 | Auto TDS | ✅ incl. yearly-limit catch-up · ⛔ rates need CA sign-off |
| 6 | Vendors + GSTIN check | ✅ free checks + manual portal status · 🟡 live API |
| 7 | Cash/bank + date | ✅ 5 modes, accounts, split, partial, advances |
| 8 | HSN | ✅ captured, HSN summary report |
| 9 | Discount | ✅ |
| 10 | FY storage, Sheets, 2A/2B reco | ✅ reco engine + upload · 🟡 Sheets mirror, GSP fetch |
| 11 | MIS | ✅ incl. ageing, modes, advances |
| 12 | Tally by 25th / Sheets | ✅ XML with journals + payments, 25th alert · 🟡 bridge (phase 2) |
| 13 | Alerts (GST reco, TDS, challans, >30 days) | ✅ in-app (credit-terms aware) · 🟡 push/email |
| 14 | Form 140 | 🟡 working CSV · ⛔ needs official FVU spec |
| 15 | PAN validity | ✅ free + manual · 🟡 live API |
| 16 | RCM | ✅ |
| 17/20/21 | Simple for laymen | ✅ |
| 18 | Client logo | ✅ |
| 22 | Past dates admin-only | ✅ |
| 23 | PWA | ✅ · 🟡 offline sync queue with backend |
| + | Quarterly compliance watch, audit panel, shared APIs | ✅ / 🟡 server side |

## 5. Tests

- **Unit tests: 49 passing.** New: split/multi-bill allocation, advances, bill status & ageing, real challan receipt text, invoice text, date formats, bank CSV parsing (quotes, Indian amounts, footers), bank matching, Tally payment vouchers with ledgers, Hindi completeness & placeholder consistency.
- **Live (browser, dummy data):** Hindi sweep of 19 screens; advance + bank transfer + backdated cash on one bill; ₹12,000 cash → flagged and audited; bank CSV with UPI/NEFT/cheque/duplicate/interest/footer rows; real challan PDF read in-browser (4/4 fields) + ITNS/date guards; bulk inbox with a duplicate; draft completion; look-alike confirmation.
- **Production build sweep:** CA (English, 19 screens), client admin (Hindi, 17), staff (Hindi, 13) — 0 crashes, 0 errors, all restricted pages redirect, no tax terms on staff screens.
- **Not tested live:** clicking file downloads (Tally XML / CSV); on-device photo OCR accuracy on real bill photos (needs your sample photos); push/email (backend).

## 6. Research sources used
Zoho Books multi-payment & bulk payment help; Zoho Expense duplicate detection & policies; QuickBooks community/Bill.com docs on pay-bills & vendor credits; invoice2data (PyPI) template approach; tesseract.js (GitHub); pdf.js; ICAI sample e-Pay challan receipt; taxguru / hostbooks on CIN & BSR.
Not confirmed: the Income-tax Act 2025 section replacing the ₹10,000 cash limit (old s.40A(3)) — limit is configurable and marked for CA confirmation.

## 7. Needs your input (⛔)
1. A real GSTR-2B JSON, 3–5 real bill photos/PDFs and one real TDS (ITNS 281) challan receipt — to measure reading accuracy on your clients' documents.
2. Form 140 RPU/FVU specification.
3. CA sign-off: TDS rates, RCM rates, 17(5) list, the cash limit under the 2025 Act, TDS rounding.
4. Vendor choices: GSP, PAN verification, AI OCR.

## 8. Considered and not built (outside the original goal)
Mileage/per-diem and employee reimbursement reports (Zoho Expense) — this tool records business bills, not employee claims. Multi-currency. Purchase orders. Say if you want any of them.
