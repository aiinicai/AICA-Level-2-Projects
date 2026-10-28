# Paisa Pal — AI-Powered Family Financial, Document & Utilities Vault
## ICAI AICA Level-2 Capstone Project Submission

### 1. Executive Summary
Paisa Pal is a production-grade, local-first Personal Finance, Document & Household Utilities Management application built for Indian Chartered Accountants, tax professionals, and households. It operates with zero-cloud data persistence, strict DPDP Act 2023 privacy compliance, client-side WebCrypto encryption (AES-GCM 256-bit + PBKDF2), intelligent multi-sheet spreadsheet reconciliation, and automated local document parsing.

### 2. Capstone Upgrades & Core Modules
- Statutory Document Validity & Expiry Engine: Compliant with Passports Act 1967 (mandatory issue and expiry dates, 10-year validity rules, NEVER labeled "Permanent", flags missing expiry as "Expiry Date Required"), Motor Vehicles Act 1988 (driving licence validity), Insurance Act 1938 / IRDAI (separates policy coverage expiry from annual premium due date), and Income Tax Act Section 139A / Aadhaar Act 2016 (lifelong status with "No Prescribed Expiry").
- Dedicated Utilities Section: Full tracking for recurring household bills (electricity, water, broadband, gas, mobile, maintenance). Features provider, consumer number (text with leading zero preservation), billing period, due date, in-app alerts, configurable reminders, payment history, and partial payment accounting where partially paid bills remain outstanding until settled.
- Multi-Sheet Excel Import & Reconciliation Engine (Fixing the 41 vs 31 Discrepancy): Multi-class spreadsheet parser with an interactive Import Preview & Audit modal. Guarantees 100% row accounting: Total Source Rows (41) = Newly Imported (41) + Updated (0) + Skipped (0) + Rejected (0). Accurately routes to Investments (10), Identity Records (20), Insurance Policies (6), and Utilities (5). Never silently discards rows, preserves leading zeros, and provides downloadable CSV reconciliation audit reports.
- Clean Records Segregation: Two distinct sub-categories: Official Identity Documents (Passport, Driving Licence, PAN, Aadhaar) and Insurance Policies (Medical, Vehicle, Life, Accident). Isolates insurance premiums/sums insured so they NEVER contaminate investment net worth.
- DPDP-Compliant Privacy & Usability: Sensitive identifiers masked by default (•••• •••• 4819) with deliberate eye-reveal toggles. Zero real unredacted documents required. Uses 41 synthetic vector SVG specimens across 10 fictional persons.
- Safe Repeatable Migration: Reclassifies existing legacy data idempotently into Utilities, Insurance, and Investments with automatic pre-migration backup exports and zero duplicate creation.

### 3. Architecture & Tech Stack
- Frontend: React 19, TypeScript, Tailwind CSS, Lucide Icons
- Local Storage: IndexedDB (scanned receipts/vouchers) + LocalStorage (encrypted rows)
- Security: WebCrypto SHA-256 PIN hashing + PBKDF2 + AES-GCM vault encryption
- Spreadsheets: SheetJS (XLSX) multi-sheet parsing preserving cell formats
- Automated QA: 202 automated unit, statutory validity, and integration tests passing (100% pass rate)

### 4. Running the Project Locally
npm install
npm test
npm run dev

### 5. Live Applet Link
- Live Web Applet (Shared): https://ais-pre-fmrljjhfbcr77w27rsoewt-472756614252.asia-southeast1.run.app
- Development Applet: https://ais-dev-fmrljjhfbcr77w27rsoewt-472756614252.asia-southeast1.run.app

Developed for ICAI Certificate Course on AI (AICA Level 2).