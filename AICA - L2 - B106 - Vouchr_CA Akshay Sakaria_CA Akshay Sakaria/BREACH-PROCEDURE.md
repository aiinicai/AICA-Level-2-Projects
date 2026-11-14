# Personal data breach — what to do (Vouchr)

**Law:** DPDP Act 2023, s.8(6), and DPDP Rules 2025, Rule 7.
- I checked the rule text on 3 Nov 2026 at [dpdpa.com — Rule 7](https://dpdpa.com/dpdparules/rule7.html).
- Rule 7 is reported to apply from **13 May 2027**. Confirm this date against the Gazette notification G.S.R. 846(E) dated 13 Nov 2025.
- **Counsel review is needed before first use.** This is a working procedure, not legal advice.

**No materiality threshold.** Every breach of personal data must be reported, however small it seems.

## Who does what
| Data | Data Fiduciary (must notify) | CA firm's role |
|---|---|---|
| The firm's own users (staff accounts, sign-in, consent records) | **CA firm** | Notifies directly |
| A client's records (vendors, PAN, phone numbers, employees) | **The client** | As processor: tell the client **at once**, with everything known, and help with its notices. Agree this in the engagement letter. |

## Steps
1. **Contain (first hour).** Revoke the leaked access:
   - sign the user out, disable the account;
   - rotate keys and secrets (Supabase service key, Google service account, WhatsApp token, Gemini key);
   - remove any public share link.

   Keep evidence; don't delete logs. Logs are kept for at least one year (migration 0010).
2. **Record the time the firm became aware.** The 72-hour clock for the detailed Board report starts here.
3. **Work out the facts:**
   - what happened;
   - which personal data, and how many people;
   - when and where;
   - the likely consequences.

   Do not guess. Write "not yet known" where that is the truth.
4. **Without delay, notify:**
   - **each affected person** (Rule 7(1)), through their app account or registered e-mail, phone or WhatsApp;
   - **the Data Protection Board** (Rule 7(2)(a)): nature, extent, timing, location, likely impact.

   For client data, the client sends these notices; the firm supports it.
5. **Within 72 hours**, send the **detailed report to the Board** (Rule 7(2)(b)), covering:
   - (i) an updated description;
   - (ii) causes;
   - (iii) mitigation;
   - (iv) findings about who caused it;
   - (v) steps to prevent it happening again;
   - (vi) a report on the notices sent to people.

   If 72 hours isn't enough, ask the Board in writing for more time **before** the deadline.
6. **Afterwards:** fix the cause, update this procedure, and keep the whole record (notices, dates, evidence).

## Templates
In the app: **Privacy & consent → Breach notices** (CA firm only).
- Type in the facts. The app lays out the three notices: the person (English and Hindi), the Board's first notice, and the Board's 72-hour report.
- It shows the 72-hour deadline.
- Anything left blank appears as "[to be filled]", so an incomplete notice can't go out unnoticed.
- The code is in `supabase/functions/_shared/breach.ts`.

## Not decided yet (your call)
- The Board's official reporting channel and format. Check the Board's website when Rule 7 takes effect.
- Who at the firm is on call for breaches. Add the name to the privacy contact on the Privacy page.
