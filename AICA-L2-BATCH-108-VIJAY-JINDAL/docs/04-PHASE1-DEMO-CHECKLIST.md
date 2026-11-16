# 4. Phase 1 – what was built, what was tested, how you check it

## Built
- Architecture, page map, collection map, decisions list (docs 01–02).
- `shared/`: typed models for core candidate + occupation sub-profiles, restricted identity, compensation, official DRA (separate from
  portal certificates), vacancies, applications (internal notes separated), training, question bank, attempts, certificates, consents,
  referrals, staff roles, CMS, institutes, audit logs. All 36 States/UTs with Hindi/Punjabi names and PIN checks.
  Business rules: registration validation, random IDs, DRA review reset, apply rules (duplicate/closed/IST closing date/disabled/
  certification flag), server-side exam scoring and retake rules, referral attribution & abuse rules, staff permission and
  field-level export filtering, profile completeness, certificate eligibility.
- `firestore.rules`, `storage.rules`, indexes, hosting security headers.
- `functions/`: config with Secret Manager parameters, redacting logger, audit writer, `completeRegistration` (written, not yet executed).
- `web/`: React PWA shell with all public pages, EN/HI/PA switcher, honest "not connected" notices, mobile-number validation, manifest, service worker, icons.
- CI pipeline (`.github/workflows/ci.yml`), seed/bootstrap/geo-import scripts.

## Actually tested here (by me)
| Test | Result |
|---|---|
| 32 automated tests of shared business rules (freshers, DRA candidates, incomplete profiles, repeat applications, certificate replacement, referral attribution, roles, unauthorized export, scoring tampering, closed vacancies, disabled accounts, forged certificate ID format) | ✅ 32/32 pass |
| TypeScript strict type check of `shared/` | ✅ pass |
| Syntax check of all website, functions and rules-test files | ✅ no syntax errors |
| One real bug found and fixed by the tests (retake waiting period could be skipped) | ✅ fixed |
| **Fix 1.1 (after first CI run):** Cloud Functions build failed – `registration.ts` read `reason` from a referral decision that may not have one | ✅ fixed; offline type check of functions + website (with stand-in Firebase/React type stubs) now passes, and it re-detects the original error when re-inserted |

## Fix 1.1 changes (CI run #1 failed at "Build Cloud Functions")
- `functions/src/registration.ts` – referral result handling rewritten (also now counts rejected referrals in aggregate).
- `shared/src/domain/referral.ts` – simpler `ReferralDecision` result type.
- `functions/package.json` – runs as an ES module (matches shared code, safe on Node 20) + `@types/node`.
- `web/package.json` – plain type check before build; `web/src/pages/Login.tsx` – explicit event type.
- `firestore.rules` – helper renamed `has()` → `hasGrant()` to avoid confusion with built-in methods.

## NOT yet tested (and why)
- Website build, Cloud Functions build, Firestore rules tests: my sandbox has no internet to download React/Firebase packages or the emulator.
  **They run automatically in GitHub Actions after Part A step 8.** Until that run is green, treat them as unverified.
- Phone OTP, App Check, email, backups: need your Firebase project (Parts B–C) – Phase 2/7/8.

## Your Phase 1 demonstration checklist
1. ☐ Read `02-DECISIONS-NEEDED.md` and reply with D1–D9.
2. ☐ Do Part A of `03-OWNER-SETUP-STEPS.md`; confirm the **Actions → CI** run is green.
3. ☐ In the CI run, click **Shared logic - unit tests** – you should see `# pass 32` and `# fail 0`.
4. ☐ Click **Security rules tests** – every line should start with `ok`.
5. ☐ Do Parts B and C (staging project + budget alert). Send me only the project ID.
