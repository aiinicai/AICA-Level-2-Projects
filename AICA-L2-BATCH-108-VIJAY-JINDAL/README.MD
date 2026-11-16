# VRS Corporate Solutions – DRA Recruitment, Free Resume & Free Collection Training Portal

**Status: Phase 1 (architecture + foundations). NOT production-ready. Registration is closed by default. Do not collect real candidate data.**

Owner: start with `docs/03-OWNER-SETUP-STEPS.md` and `docs/02-DECISIONS-NEEDED.md`.

## Phase plan and status
| Phase | Scope | Status |
|---|---|---|
| 1 | Requirements review, architecture, data model, rules draft, shared business logic + tests, PWA shell | ✅ delivered (web/functions builds verified by CI only) |
| 2 | Screens + candidate registration (Phone OTP, App Check, resend delay, caps, completeRegistration, referral capture) | ⏳ next |
| 3 | Firebase security hardening + full profile wizard, uploads, DRA review, PAN, data-rights requests | ⏳ |
| 4 | Resume builder (4 templates, PDF, no AI needed) + optional Gemini with consent; referral page/QR/WhatsApp | ⏳ |
| 5 | Vacancies, applications, recruitment pipeline, dashboards, exports | ⏳ |
| 6 | Training CMS, enrollment, quizzes, server scoring, certificates, verification | ⏳ |
| 7 | Admin CMS, contact form email, reports, maintenance mode | ⏳ |
| 8 | Privacy/legal, accessibility, security review, backups + restore test, load test, pilot | ⏳ |
| 9 | Controlled production deployment (owner approval) | ⏳ |

## Developer commands
```bash
npm install
npm run typecheck:shared && npm run test:shared     # business-rule tests
npm run build:functions && npm run build:web
npx firebase-tools emulators:exec --project demo-vrs-rules --only firestore "npx tsx --test tests/rules/*.test.ts"
npm --workspace web run dev                          # local site at http://localhost:5173
```
Environment: copy `web/.env.example` to `web/.env.staging` (never commit). Secrets: `firebase functions:secrets:set PHONE_HASH_KEY` (typed by the owner/admin, never in code or chat).

