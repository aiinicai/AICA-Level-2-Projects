# 1. Architecture (Phase 1)

## 1.1 Picture in one minute

```
 Candidate phone / PC (PWA, English/Hindi/Punjabi)          Staff laptop (MFA required)
            |                                                        |
            v                                                        v
 +--------------------- Firebase Hosting (HTTPS, security headers) ---------------------+
 |                React + TypeScript + Tailwind single-page app                         |
 +---------------------------------------------------------------------------------------+
     |  App Check (reCAPTCHA Enterprise)  |                     |
     v                                     v                     v
 Firebase Auth                  Cloud Firestore            Cloud Storage (private)
 - Candidates: phone OTP        - rules = least privilege   - incoming/{uid}/...  (candidate write-only)
 - Staff: email + MFA           - public / private /        - private/candidates/... (no client writes)
 - custom claims = role           restricted collections    - training/, public/
                                     ^                         ^
                                     | Admin SDK               |
                         Cloud Functions (asia-south1, Mumbai) – ALL privileged work:
                         registration & IDs, referral attribution, DRA updates & review, applications,
                         exam start/score, certificates, staff roles, exports, signed download links,
                         contact form email, AI resume (Gemini), scheduled backups & reminders
                                     |
                         Secret Manager (PHONE_HASH_KEY, GEMINI_API_KEY, SMTP_PASSWORD)
                         Cloud Logging (redacted)   Budgets & alerts   Scheduled Firestore exports
```

**Golden rule:** the browser is never trusted for anything important. It cannot create applications, scores,
certificates, referral credits, roles or review decisions – only Cloud Functions can.

## 1.2 Repository layout

| Folder | What it is |
|---|---|
| `shared/` | Typed data models + business rules used by both website and server (validation, IDs, scoring, referral, permissions). Fully unit-tested. |
| `web/` | The website / installable app (React, TypeScript, Tailwind, PWA). |
| `functions/` | Cloud Functions (server code with privileges). |
| `firestore.rules`, `storage.rules`, `firestore.indexes.json` | Database and file security + query indexes. |
| `tests/rules/` | Security-rules tests (forged IDs, tampering, roles) run against the Firebase emulator. |
| `scripts/` | Seed default settings, import districts, make the owner an admin. |
| `docs/` | These documents. |

## 1.3 Pages

**Public:** Home · Jobs · Build Resume · Free Training · DRA Exam Preparation · Training Institutes · About · FAQs · Contact · Privacy · Terms · Login/Register · Certificate verification (`/verify/{id}`).

**Candidate (after login):** My Dashboard (profile progress, next step) · My Profile (step-by-step wizard: Basic → Location → DRA → Education & Experience → Job Preferences → Photo/CV) · My Resume (templates, edit, preview, PDF, optional AI suggestions) · My Applications · My Training (courses, progress, bookmarks, quizzes, certificates) · Refer a Friend (link, QR, WhatsApp share, count) · Privacy & Account (consents, download/correct data, close account).

**Staff (MFA, role-based):** Dashboard (incomplete profiles, document reviews, applications, follow-ups, referrals, vacancies, placements) · Candidates (indexed search & filters, paginated) · Candidate detail (field groups shown per permission; restricted views audited) · Document review queue · Vacancies (create/edit/publish/close/archive) · Applications pipeline (stages, assignment, follow-ups, interviews, notes) · Training CMS (courses, modules, lessons, question bank, assessments, cohorts, enrollment links) · Institutes · Site CMS (banners, FAQs, pages, announcements, reference lists, contact details, maintenance mode) · Referral & campaign reports · Exports (permissioned, logged) · Staff & roles (owner admin only) · AI settings (owner admin only) · Audit log.

## 1.4 Main Firestore collections

| Collection | Who can read | Who writes |
|---|---|---|
| `candidates/{uid}` core profile | candidate; staff with `profile.basic` | function creates; candidate edits allowed fields only |
| `candidates/{uid}/restricted/identity` (father, DOB, addresses, masked PAN) | candidate; `identity.restricted` | candidate (PAN via function only, encrypted) |
| `candidates/{uid}/restricted/compensation` | candidate; `compensation` | candidate |
| `candidates/{uid}/occupations/{collections\|chartered_accountant…}` | candidate; `profile.basic` | candidate |
| `candidates/{uid}/dra/current` (OFFICIAL DRA) | candidate; staff | functions only (auto-resets review on change) |
| `candidates/{uid}/resumes/*` | candidate; staff | candidate |
| `candidates/{uid}/consents/*` | candidate; owner | candidate append-only |
| `vacancies/*` | public if published; staff | `vacancies.manage` |
| `applications/{vacancyId_uid}` | that candidate; recruiters | functions only |
| `applications_internal/*` (+`events`) | recruiters only (never candidates) | recruiters; events append-only |
| `courses/*/modules/*/lessons/*`, `assessments/*` | public/signed-in if published | `training.manage` |
| `question_bank/*` (answer keys) | `training.manage` only | `training.manage` |
| `enrollments/{uid_course}` | that candidate; training staff | candidate (progress/bookmarks) |
| `attempts/*` | that candidate; training staff | functions only (server scoring) |
| `certificates/*` (PORTAL training awards) | that candidate; training staff | functions only |
| `certificate_verification/{id}` | anyone, single lookup, no listing | functions, only with consent |
| `referral_codes`, `phone_index`, `candidate_ids`, `candidates_private_hash` | nobody (server only) | functions |
| `referral_stats/{uid}` | that candidate (counts only) | functions |
| `referral_attributions/*` | `referrals.report` | functions |
| `institutes/*`, `cms_public/*`, `reference/*`, `geo_districts/*` | public | `cms.manage` |
| `settings_private/*` (no secrets) | owner admin | owner admin |
| `staff/*`, `audit_logs/*`, `exports/*`, `contact_messages/*`, `ai_usage/*`, `data_requests/*` | owner admin | functions |

**Future readiness:** new occupations (e.g. Chartered Accountants) = new `occupations/{key}` sub-profile + reference lists; core
schema, applications and training are unchanged. Employer access later = new role with scoped, consent-checked views (not in release one).
iPhone app later = same backend; PWA works on iPhone Safari today ("Add to Home Screen").

## 1.5 Search at nationwide scale
Never download the candidate database to the browser. Staff search uses Firestore indexed queries (state, role, DRA status,
completeness, `searchTokens` array for name/city prefix), cursor pagination (25 per page), and server-side phone search via a
function (hash lookup, audited, requires `contact.phone`). If free-text search becomes essential at large scale, add a managed search
service (e.g. Typesense/Algolia/Vertex AI Search) fed by a function with **only non-sensitive fields** – a separate decision.
