# 5. Security & privacy design (DPDP-oriented – final legal review required)

## Controls in place from Phase 1
- Default-deny Firestore/Storage rules; privileged work only in Cloud Functions (Admin SDK).
- Staff access requires role claim + `staff_active` + **MFA in the current session** (enforced in rules, not just UI).
- Owner admin only: create/disable staff, assign roles, grant `export.csv`, `identity.restricted`, `compensation`.
- Candidates only reach their own docs; forged IDs/URLs fail rules (tests in `tests/rules`).
- Application IDs are deterministic (`vacancy_uid`) → no duplicates; created only by function → closed vacancies enforced server-side.
- Exams scored only on the server using stored choice permutations; answer keys unreadable by candidates.
- Certificates only via function after eligibility check; IDs unguessable; public verification = single lookup, consented, minimal.
- Official DRA data and portal training certificates are separate models/collections.
- Changing DRA number or file resets review to `pending` and issuer verification to `not_checked`.
- Uploads: candidate write-only `incoming/` area with type/size limits → function checks and moves to private path; staff get
  short-lived signed links via audited function; no public document URLs anywhere.
- No Aadhaar, banking, caste, religion, marital status fields. PAN optional, restricted, encrypted server-side, masked in UI.
- Phone duplicates detected via HMAC hash (secret key in Secret Manager).
- Logger redacts phone/PAN/DOB/address/email/secret-like keys; audit logs store internal IDs only.
- Consent ledger is append-only, versioned, timestamped; recruitment contact, marketing, WhatsApp, employer sharing, AI processing and
  public certificate verification are separate purposes.
- Functions region asia-south1; Firestore/Storage in asia-south1.
- Hosting headers: HSTS, nosniff, frame deny, referrer policy, permissions policy. Service worker never caches API/personal data.

## Planned controls (later phases – not yet done)
- App Check enforcement on Firestore/Storage/Functions; SMS region policy India-only; daily SMS cap; resend delay 60s; per-IP limits (Phase 2).
- Data rights workflow: correction, account closure, deletion with retention exceptions (Phase 3/8).
- AI: consent gate, field minimisation (no PAN/DOB/phone/address/certificates), output diff with per-change approval, usage caps, key only in Secret Manager (Phase 4).
- Export: field-level, owner-approved, logged with column list and row count, CSV formula-injection protection (Phase 5).
- Backups: daily scheduled Firestore export to a separate locked bucket in asia-south1, Storage object versioning + soft delete,
  **documented restore test into a scratch project with evidence** (Phase 8).
- Load test of public pages and key functions on staging; accessibility audit (WCAG 2.1 AA); external human security review (Phase 8).

## Not production-ready until
All CI tests green · rules tests green · restore test evidence recorded · legal review of notice/consents/retention · human security review signed off · owner written approval to open registration.
