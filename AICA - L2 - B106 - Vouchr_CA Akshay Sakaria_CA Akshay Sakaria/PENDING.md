# Vouchr — what is pending (3 Nov 2026)

**Build work: everything is done except the Supabase step**, which waits for your go-ahead (see SUPABASE-SETUP.md).
What remains below is either the Supabase step, or a decision or account that only you can provide.

## A. Supabase step (waiting for your go-ahead)
- Create the project, apply migrations 0001–0014, deploy 8 functions, set the secrets, schedule the jobs (SUPABASE-SETUP.md).
- Connect the app's data layer to the database. Today all data is kept in one browser. This is the largest piece; contract tests come with it.
- Then check on the live system what can only be checked there:
  - push and e-mail delivery;
  - Drive upload and cleanup;
  - WhatsApp with Meta;
  - the Supabase security advisor;
  - auto-approval run on the server (it needs the bill risk check moved into server code);
  - Drive sharing with client admins (drive-share).

## B. Needs your decision, account or document (cannot be built without it)
| # | Item | Why it matters |
|---|---|---|
| 1 | **Google Drive for the firm** (Shared Drive + service account, or the firm account's OAuth) | Bills are filed there |
| 2 | **Gemini billing** (paid tier) before any real client bill | Free-tier content may be used by Google; rule-change search needs billing |
| 3 | **WhatsApp Business setup** (WHATSAPP-SETUP.md) | Automatic WhatsApp intake |
| 4 | **GSP, GSTIN and PAN verification vendors.** Building these without a chosen vendor's API documentation would mean guessing its API. Manual 2B upload and CA-set status work meanwhile. | 2B auto-fetch; PAN operative/inoperative status decides the higher TDS rate. Confirm Protean's terms allow a CA firm to verify for clients. |
| 5 | **E-mail account for alerts** (SMTP of any provider) and VAPID keys for phone alerts | The code is built; it needs the firm's account |
| 6 | **IRP public key** pasted in Privacy & consent → firm settings, from the official e-invoice portal | Until then QR codes are read but marked "signature not checked" |
| 7 | **Privacy contact**, **counsel review** of the notice, clauses and BREACH-PROCEDURE.md, and the **engagement letter reference + end date** for each client | DPDP obligations |
| 8 | **CA sign-off of the 7 TDS rates** marked unverified in Tax masters | Rates must come from the Act |
| 12 | **CA confirmation of the new GST rules:** time of supply for reverse charge (s.13(3) services / s.12(3) goods), the 180-day ITC reversal (s.16(2) second proviso), and credit notes reducing ITC | The registers follow the Act as I read it; nothing is filed from them without the CA |
| 13 | **Whether to switch on auto-approval** for any client (off by default), and its limits | It removes the CA review for the bills it approves |
| 14 | **Whether client admins should see their Drive folder** (off by default) | It gives them view access to all filed documents of their company |
| 9 | **CA call on TDS-on-advance edge cases.** An advance deducted under one section, applied to a bill of another, is carried (so no double deduction) but **marked for the CA**. | Rate and return entry may need correcting |
| 10 | **Real samples:** a GSTR-2B JSON, an ITNS-281 challan, the Form 140 file spec | To validate reco, challan reading and the TDS return |
| 11 | **Product name.** "Vouchr" clashes with Vouchr Ltd (Canada). | Rename before going public |

## C. Not verified (needs a real device, person or paid service)
- **Voice entry** with a real microphone.
- **Real low-end Android phones.**
- **A screen-reader pass** (TalkBack / NVDA).
- **Cost per real bill.** Measured only on test bills (about $0.002 each).
- **Lighthouse, 3 Nov 2026:** measured only on the sign-in screen of the demo build (mobile, simulated throttling): Performance 93, Accessibility 100, Best Practices 100. FCP 2.4 s, LCP 2.8 s, TBT 10 ms, CLS 0. Pages behind sign-in were not measured.

## D6. Done — 3 Nov 2026 (third round: older AUDIT-v0.4 items)
- **Credit and debit notes from vendors (F4):**
  - recorded against a bill, or at vendor level and linked later;
  - change the bill's balance and the ITC;
  - checks: no note above the bill value, none dated before the bill, no duplicate number in the FY, matching tax type;
  - a bill with TDS is marked "CA to check";
  - matched with GSTR-2B **CDNR** (credit and debit notes);
  - Tally: a supplier's credit note posts as a **Debit Note** voucher (enable that voucher type in Tally), a debit note as a Journal;
  - database: migration 0012, which also makes the payment checks count notes.
- **GST registers (B6, B7):**
  - **reverse-charge GST by the month it is due:**
    - services (s.13(3)): the earlier of the payment date and the day after 60 days;
    - goods (s.12(3)): the day after 30 days, marked "receipt date not recorded";
    - part payments are split;
  - **ITC 180-day register:** reverse only the part unpaid on day 180, re-claim after payment; the CA records both (migration 0013).
- **Review queue (B10):**
  - **auto-approval of low-risk bills**, OFF by default and set by the CA only. Every condition must hold, the tax treatment is copied from the vendor's approved bills, and a sample still goes to the CA;
  - waiting days, oldest first, reviewer assignment, and a list of bills approved by the rule.
- **Security fix (migration 0014):** users could insert a bill already marked "approved" and skip the CA review. Now refused.
- **Drive folder for client admins (B8):** CA switch, plus the `drive-share` function (view only, removed on deactivation).
- **Bank statements (F5):**
  - one Amount column with a Dr/Cr column, or with a sign;
  - **Excel .xlsx**;
  - a one-time column mapping screen, remembered per bank account.
- **Photos:**
  - **HEIC** from iPhones is kept as the bill file when the browser can't open it, with the iPhone setting tip (F6);
  - **Cancel reading** plus a 45-second limit (F7);
  - **look-alike photo warning** at capture against the last 90 days (F8).
- **On-device reader is self-hosted (A7):** no public CDN; about 7 MB, not in the install, cached on first use or with "Download now (Wi-Fi)". The PDF worker is out of the install too.
- **Phones and keyboard:**
  - wide admin tables turn into cards on phones (U1);
  - arrow keys work in every chip group (U6);
  - a labelled language switch on More and the staff home (U7);
  - the staff bottom bar shows Inbox instead of a second Alerts (U10);
  - the last browser `prompt` (cancel payment) is replaced by the in-app sheet (U5).
- **Year-end close (B11):**
  - checklist: blockers vs warnings to acknowledge;
  - carry-forward sheet: open bills, advances, unused advance TDS, unlinked notes;
  - closing locks the 12 months (migration 0014).
- **Small existing bugs fixed:**
  - PAN/GSTIN status options had no value, so Hindi text would have been saved as the status;
  - an untranslated banner on the vendor form;
  - Cancel pressed while the reader was starting was ignored.
- **Checks:** 188 unit tests and 33 database checks pass; production build is clean. In the app I tried:
  - a credit note on a bill (balance and ITC move);
  - GST registers on a phone width (cards, no sideways scroll);
  - the review queue;
  - the FY close page;
  - self-hosted reading of a test image, plus Cancel and the time limit.
- **Not tried live:** auto-approval through the capture screen (rule covered by 13 tests), the bank column screen with a real bank file, and a real HEIC photo.

## D5. Done — 3 Nov 2026 (second round)
- **Offline outbox.** In live mode, a file picked while offline, or whose upload fails on the network or the server, is kept on the phone and sent automatically when back online (at start, on reconnect, every 2 minutes). The app shows how many are waiting. Tested in the browser: kept after a failed try, sent on retry, record re-pointed to the Drive file.
- **Atomic saves (migration 0010).**
  - A split payment saves all its lines in one transaction (`record_payment`), or none of them. TDS on the advance is worked out there from the tax masters, not trusted from the phone.
  - `apply_advance` carries the advance's TDS credit.
  - A bill and its document are saved together (`save_bill_document`).
  - An upload that never gets a record is moved to Drive trash after 24 hours (`drive-cleanup` function).
  - Users can no longer insert payments directly or edit a saved payment's amount.
- **Log retention (DPDP Rules).** Audit, system and WhatsApp logs can't be changed, and can't be deleted before one year.
- **WhatsApp number check by one-time code.** The person sends "VERIFY 123456" from their own WhatsApp. "Yes, this is my number" is gone.
  - 15-minute validity, 5 tries, only a hash is stored.
  - The webhook checks the code; the database stops anyone marking a number confirmed by hand.
- **Alerts by phone and e-mail (migration 0011, `alerts-dispatch`).**
  - Same rules as the app: TDS due/overdue (bill TDS and advance TDS by month), bills overdue, ITC at 180 days.
  - Each alert is sent once per stage.
  - Uses standard Web Push and SMTP, with no third-party provider chosen.
  - The Alerts page says plainly when a channel isn't available yet; the old line claiming alerts were already "sent as push and email" was untrue in live mode and is removed.
- **E-invoice QR signature check.** RS256 check against the IRP key the CA saves. Results:
  - **verified**;
  - **does NOT match** (a high-risk flag on the bill);
  - **not checked** (no key saved; never assumed genuine).
- **DPDP breach procedure.** BREACH-PROCEDURE.md, and an in-app "Breach notices (Rule 7)" card for the CA firm.
  - It lays out the person notice (English and Hindi), the Board's first notice and the 72-hour report.
  - It shows the 72-hour deadline. Blanks stay "[to be filled]".
  - I checked the rule text against dpdpa.com. It is reported to apply from 13 May 2027; confirm in the Gazette.
- **Hindi** for system messages, job errors, audit action names and flags, and TDS-master source notes. Audit details stay exactly as recorded.
- **Advance TDS under a different section from the bill** is marked "CA to check" on the payment and in the TDS register.
- **Existing database bugs found by running the migrations on a real Postgres (PGlite), and fixed:**
  - 0001: the audit trigger failed on every vendor and TDS-rate insert;
  - 0005: an invalid unique constraint, and a view using a column that doesn't exist;
  - 0006: a client admin couldn't add a vendor;
  - 0003: WhatsApp drafts with no amount yet were refused;
  - the aggregator/9(5) bill fields were missing from the database.
- **Scheduled functions** `compliance-watch` and `sheets-mirror` now refuse callers without the cron secret. Before, anyone with the app's public key could trigger them.
- **`npm run test:db`** runs 23 database checks on all migrations. Unit tests: 142 passing.

## D4. Done — TDS on advances and CA-only controls (3 Nov 2026)
- **TDS on advances (s.393: due at credit or payment, whichever is earlier).**
  - When part of a payment is kept as an advance, the pay screen suggests TDS:
    - the section comes from the vendor's earlier bills;
    - the higher rate applies when the PAN is missing or inoperative;
    - the single-payment and yearly limits are checked against bills plus advances.
  - The user decides; nothing is deducted without the tick. Example: ₹99,000 paid at 1% means TDS of ₹1,000 and ₹1,00,000 credited to the vendor.
  - When the advance is applied to a bill, the TDS already deducted counts against the bill, so it is never deducted twice.
- **Challan month follows the law.** An advance paid before the bill puts its TDS in the payment month. An advance paid after the bill leaves the bill's TDS in the bill's month.
- **TDS register and Form 140 working sheet** list advance rows with an "Advance" tag. Challan alerts use the same list.
- **Tally.** The advance payment voucher includes the TDS line (vendor Dr cash + TDS, bank Cr, TDS payable Cr). The bill voucher posts only the TDS still due.
- **Posted bills are blocked.** A TDS-deducted advance can't be applied to a bill already in Tally with its own TDS; the CA adjusts that in Tally.
- **CA-only controls.** Client admins see the cash limit, the note limit and vendor PAN/GSTIN status as read-only ("Set by your CA"). The store enforces the same rule as database guard 0006. Only the CA firm sees the backdate window.
- **Removed a dead call** to a server function (`ocr-extract`) that never existed. Photo reading is: QR → on-device OCR → AI (when agreed).
- **Not verified:** these TDS rules should be confirmed by the CA, especially an advance deducted under one section (e.g. contractor) that is later adjusted against a bill of another section (e.g. professional fees).

## D3. Done — duplicate bills and bilingual confirmations (2 Nov 2026)
- **Duplicate check now recognises the vendor three ways:** the same vendor record, the same GSTIN, or the same name. So "KULKARNI ASSOCIATES LLP" is caught as Kulkarni Associates.
- **Bill numbers are compared as people write them:** INV-0045 = inv/45 = INV 045 = INV45. Different numbers never merge: KA/2/6164 ≠ KA/26/164.
- **Same bill number in the next financial year = a new bill** (GST invoice serials are unique per financial year).
- The "looks like a bill already recorded" check uses the same vendor rule. The Bill risk check uses the same bill-number rule.
- All browser pop-ups (sign out, delete draft, lock month, withdraw consent) are replaced by an in-app sheet in English or Hindi. Cancel is the safe default, and Escape cancels.

## D2. Done — travel-portal and section 9(5) bills (2 Nov 2026)
- **New fields on a bill:**
  - **Charges without GST on this bill**: fare collected for an airline or IRCTC, reimbursements. Recorded exactly as printed; GST is split only from the rest.
  - **GST paid by the app (section 9(5))**, with the operator's GSTIN.
- **Detected automatically** from PDFs and photos, and by AI. A non-GST amount is accepted only when the arithmetic agrees. On your invoices: MakeMyTrip flight ₹2,715 ✓, rail ₹1,460.40 ✓, Uber and Zomato receipts flagged 9(5) ✓, no false detections.
- **The form now follows the tax type printed on the bill** (CGST+SGST vs IGST) instead of guessing from the states.
- **9(5) bills:**
  - no reverse charge;
  - risk check flags input credit claimed on them (17(5) check);
  - "GST without GSTIN" is not raised when the app paid the tax.
- **Updated to understand the non-GST part:** Tally voucher (posted to the expense ledger, still balances), CA approval check, Excel import (3 new columns with sample rows), AI truth checks.
- **The law is contested in places.** Whether a travel agent may charge GST only on its fee (Rule 33 vs Rule 32(3) for air tickets) is debated, so Vouchr records the bill as printed and takes no legal position.
- **Unconfirmed:** a report that the 57th GST Council (Oct 2026) recommended unblocking some 17(5) items is not confirmed. The app still uses the CA-maintained 17(5) masters.

## D. Done in this round
- **WhatsApp bill intake:**
  - server function: signature check, de-duplication, consent check, Drive filing, draft, bilingual reply;
  - number add/confirm and the "via WhatsApp" badge;
  - demo simulator;
  - privacy notice v2 (everyone re-consents).
- **Vendor master:** automatic creation already existed. It now matches by GSTIN first, so name spelling differences don't create duplicate vendors.
- **On-device reading, tested on your 7 invoices.** All 5 PDFs now read fully (total, vendor, bill no., date, HSN, e-invoice IRN). Fixed:
  - totals were taken from the wrong row (Tally e-invoice, Flipkart);
  - bill numbers in two-row tables were missed (MakeMyTrip, Tally);
  - the seller hidden in "Invoice issued by…" (Uber);
  - photo GSTIN misreads, which are now repaired only when the check digit passes.
- **Inbox no longer hangs** if the PDF QR scan stalls (10-second limit).
- **Design audit** (every screen, 3 roles, English and Hindi, desktop / 375 px / 320 px):
  - fixed the broken Flags/Status cells (Review queue, Vendors);
  - Review queue shows risk flags;
  - chart labels no longer overlap;
  - dates stay on one line;
  - the Expenses page title now matches the menu;
  - one ₹K/₹L/₹Cr format;
  - labels added to 7 unlabelled fields.
  - No page overflow or clipped text found at any width.
