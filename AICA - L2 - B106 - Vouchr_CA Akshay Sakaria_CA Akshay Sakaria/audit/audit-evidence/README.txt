EXPENSE TRACKER / VOUCHR AUDIT EVIDENCE — 3 November 2026

Read Expense-Tracker-Audit.html for the complete assessment, findings, limitations,
recommendations, enhancement backlog, remediation order and acceptance gates.
The original project at C:/Users/Geeta/Desktop/Expense Tracker tool was not changed.
All execution used an isolated working copy without .env.local credentials.

BASELINE VALIDATION
Node v24.18.0 / Windows PowerShell. Existing locked dependencies were used.
  npm.cmd test -- --reporter=verbose      188 tests / 16 files pass
  npm.cmd run test:db                   14 migrations / 33 checks pass
  npm.cmd run build                     TypeScript + Vite + PWA pass
  npm.cmd audit --json                  28 vulnerable package entries
  npm.cmd audit --omit=dev --json        12 vulnerable package entries
Audit exit status 1 reports advisories; it is not a failed installation.
Advisory counts include development/optional chains and are not exploit counts.
The first sandbox attempt was blocked by esbuild metadata access. Final logs are
from the approved isolated-copy executions; this was not a project defect.

ADDITIONAL DEFECT REPRODUCTIONS — NOT ACCEPTANCE TESTS
adversarial-audit.mjs: copy into supabase/tests/ in a separate project copy and run
  node supabase/tests/adversarial-audit.mjs
from the project root. It creates fresh in-memory PGlite, applies all migrations,
simulates auth.uid and grants authenticated CRUD as in the project's test setup.
Each case rolls back. There is no connection to production or external services.
22 unsafe acceptances and 1 rejected Excel-source contract case were observed.
The vulnerable boolean is a harness outcome marker; examine each named scenario.
Actual deployed grants and gateway/Auth behavior were not inspected.

audit-regressions.test.ts: place in src/lib/ of an isolated copy and run
  npx.cmd vitest run src/lib/audit-regressions.test.ts --reporter=verbose
It exercises pure functions and the real store with a controlled React-hooks
harness. Ten assertions document faulty current outcomes. It is not browser E2E.
Dates/fixtures reflect 3 November 2026; freeze the clock to that date when replaying
later. When correcting defects, replace expectations with the intended invariant.
Do not add these reproduction assertions unchanged as a green release gate.

SCOPE / SAFETY
No live Supabase, Google, Gemini, WhatsApp, SMTP, push or Tally action was tested.
No real client data, credentials, .env.local, private AI runtime logs, dependencies,
binary OCR models or generated app bundles are included.
Browser visual validation is incomplete: the isolated tab failed to attach and
automatic approval review rejected a screenshot of an unrelated Google sign-in.
No Google account screenshot was captured.

REGISTER / MANIFEST
findings.csv / findings.json: all 48 findings, severity, evidence status, source
line references, impact, remediation and acceptance criteria.
project-inventory.json: 166 non-generated files with SHA-256 at audit time.
These are checksums, not source copies. Third-party source was not exhaustively
reviewed. Source anchors were validated against the original project.
evidence-checksums.json: checksums of the attached evidence files, excluding itself.
report-verification.json: machine checks of report structure, filter behavior,
source references, and original-to-isolated-copy file identity.

LIMITS
This is technical due diligence with targeted synthetic reproductions, not a legal
or tax certification, a deployed penetration test, real-device/UI certification,
or a guarantee that every defect was found. The report distinguishes reproduced
behavior, source-confirmed risks and external consequences not executed.
