# Vouchr — DPDP Act 2023 / DPDP Rules 2025: what's built and why

*My reading of the law, from the Act and the Gazette text of the Rules (MeitY copy). This is not legal advice. Have the firm's counsel confirm it, especially the roles in §2.*

## 1. Timeline
- **Rules published:** Gazette, 13/14 Nov 2025.
- **Notice, consent and rights duties** (Rules 3, 5–16): apply **18 months later — about mid-May 2027**.
- **Consent Manager rules:** apply 1 year after publication.

Vouchr is ready ahead of time.

## 2. Who is who (proposed)
| Data | Data Principal | Fiduciary / processor |
|---|---|---|
| App user accounts (staff, client admins, CA staff) | Each person | CA firm (runs Vouchr) |
| Client's records (vendor names, PAN, phone; employees) | Those individuals | **Client** = fiduciary; **CA firm** = processor under the engagement contract (s.8(2)) |
| Google Drive, Google Gemini, database host | — | Sub-processors |

## 3. Your instructions vs the law — what was built
| You asked | What the law says | What Vouchr does |
|---|---|---|
| Consent "by default" at sign-on | s.6(1): consent must be "free, specific, informed, unconditional and unambiguous with a **clear affirmative action**". A pre-ticked or assumed consent does not meet this. | Consent **is required at sign-on** — the app cannot be used without it — but by an explicit tick + **I agree**. Nothing is pre-ticked. |
| Staff sign-in = the client's overall consent | Consent belongs to the individual whose data it is. A staff member cannot consent for the company or for vendors. A company is not a Data Principal. | Each person consents for their own data. The **company's acceptance** is a separate record: the client admin ticks the company terms at first sign-on, **or** the CA firm records it from the signed engagement letter. Once on record, it covers the company — staff never repeat it. |
| Consent perpetual until the engagement ends | s.6(4): the right to **withdraw at any time**, "with the ease of doing so being comparable" to giving it. | Consent is **valid until the engagement end date** (stored per client), unless withdrawn earlier. Withdrawal is one tap + confirm in Privacy & consent. Records the law requires stay (s.6(6), s.8(7)), e.g. GST books for 72 months from the annual-return due date (CGST s.36). |

## 4. Built
**Sign-on consent screen**
- Standalone notice in English/Hindi (s.5(3)) covering Rule 3's minimum contents:
  - itemised personal data;
  - purposes;
  - how to withdraw, exercise rights and complain to the Board.
- Age 18+ confirmation (children's data needs verifiable parental consent — Rule 10).
- AI as a **separate optional** choice.
- Company terms for client admins.
- The notice is versioned; a new version asks again.

**Privacy & consent page**
- Shows the consent and its date.
- Switch AI on/off.
- Withdraw own consent; withdraw company consent (blocks the whole company).
- Rights requests (summary, correction, erasure, nomination, grievance) with a **90-day due date** (Rules).
- Download my data (JSON).
- CA firm controls:
  - privacy contact (s.8(9));
  - engagement end dates;
  - record acceptance from the engagement letter;
  - close requests.

**AI follows consent**
- AI runs only if the user opted in and the company has not switched it off.
- Checked in the app **and** in the server function.

**Notices where data enters or leaves**
- Login.
- Add expense: bills; voice ("Vouchr does not keep the audio").
- Inbox.
- Excel import.
- Vendor form.
- Add user.
- Reports and TDS exports.
- Every AI panel.

**Records**
- Consents are never deleted — the firm must be able to prove notice and consent (s.6(10)).
- Withdrawal only stamps the record.
- Every action is in the audit log. Database: `0008_dpdp_consent.sql`.

## 5. Still needed from the firm
1. Enter the **privacy contact** (name, e-mail, phone) in Privacy & consent. Until then the notice says "contact details to be added by the firm".
2. Have counsel review the notice text (`src/data/privacyNotice.ts`), the company terms and [ENGAGEMENT-AI-CLAUSE.md](ENGAGEMENT-AI-CLAUSE.md).
3. For each client, record the engagement letter reference and the engagement end date.
4. Not built yet, and needed before go-live:
   - **Breach intimation process** (Rule 7: tell affected people and the Board without delay). This is an office procedure plus a template.
   - **Security-log retention of at least 1 year** (Rule 6, Rule 8(3)). Supabase log settings, to be done when the backend goes live.
