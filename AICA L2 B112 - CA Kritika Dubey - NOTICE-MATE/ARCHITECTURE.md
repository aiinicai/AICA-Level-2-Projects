# NOTICE-MATE v3 — Architecture & Implementation Plan

## 1. Design goals

| Goal | How it is met |
|---|---|
| Local-first | All documents, extracted text, metadata and audit logs live under `NOTICEMATE_DATA_DIR` on the CA's machine. Nothing leaves the machine unless the user approves a specific AI submission. |
| Privacy by default | Local PII detection + redaction; AI gateway with preview → approve → send workflow; transmission blocked if redaction verification fails. |
| Professional safeguards | Legal-reference registry with verification status; tax computations always return workings + assumptions + exclusions; CA approval mandatory before export; every output watermarked as draft until approved. |
| Auditability | Append-only, hash-chained audit log that stores event metadata and content hashes, never document content. |
| Testability | All business logic lives in `noticemate/core` and `noticemate/services` (pure Python, stdlib `sqlite3`), independent of FastAPI and Streamlit. |

## 2. Layering

```
┌──────────────────────────────┐
│ Streamlit UI (frontend/app.py)│  HTTP + bearer token (localhost only)
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ FastAPI (noticemate/api)      │  auth, validation, size/type limits, error mapping
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Services (noticemate/services) — one module per feature       │
│  auth · cases · documents · extraction · classification ·     │
│  notice_parser · issues · evidence · reconciliation · taxlaw ·│
│  taxcalc · info_request · drafting · review · ai_gateway      │
└──────────────┬───────────────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Core (noticemate/core): config · db (sqlite3) · storage       │
│  (optional Fernet encryption) · audit (hash chain) · pii ·    │
│  security · errors · logging                                  │
└──────────────────────────────────────────────────────────────┘
```

## 3. Module map (requested modules → code)

| # | Module | Code |
|---|---|---|
| 1 | User access & local workspace | `services/auth.py`, `services/cases.py`, `core/storage.py` |
| 2 | Upload & extraction (PDF, DOCX, XLSX, scanned PDF via OCR) | `services/documents.py`, `services/extraction.py` |
| 3 | Classification & indexing | `services/classification.py` (+ FTS-style keyword index table) |
| 4 | Notice particulars & deadline | `services/notice_parser.py` |
| 5 | Issue-wise analysis | `services/issues.py` |
| 6 | Evidence mapping | `services/evidence.py` |
| 7 | Bank / cash book / ledger / FS analysis | `services/reconciliation.py` |
| 8 | Tax law & computation | `services/taxlaw.py`, `services/taxcalc.py`, `data/legal_registry.json`, `data/tax_rates.json` |
| 9 | Evidence-gap & client request | `services/info_request.py` |
| 10 | Draft reply & annexures | `services/drafting.py` |
| 11 | CA review, approval, export | `services/review.py` |
| 12 | Audit trail & case history | `core/audit.py`, `services/cases.py` (history) |
| — | AI provider gateway | `services/ai_gateway.py`, `services/ai_providers.py` |

## 4. Key workflows

### 4.1 AI submission (privacy gate)
1. User selects text (e.g. one notice issue) and a task.
2. `ai_gateway.prepare()` runs PII redaction (regex + case-party names), then **re-scans** the redacted text. Any residual hit → status `BLOCKED`, nothing can be sent.
3. The exact redacted payload (system prompt + user content) is stored as a *pending* submission and shown to the user with its SHA-256.
4. `ai_gateway.approve_and_send()` requires the same user, the matching payload hash and an explicit `confirm=True`. Only then is the provider called.
5. Audit log records: user, case, provider, model, payload hash, character count, PII counts — **not** the content. Pending payloads are deleted after send unless `NOTICEMATE_RETAIN_AI_PAYLOADS=true`.
6. AI output is stored labelled `AI_SUGGESTION – NOT A PROFESSIONAL OPINION` and is never merged into a draft automatically.

### 4.2 Applicable law
`taxlaw.determine_applicable_law(assessment_year, notice_date, proceeding_type)`:
* AY 2026-27 and earlier (FY ending on/before 31-03-2026) → Income-tax Act, 1961, via the savings/transition provisions of the Income-tax Act, 2025 — flagged **REQUIRES CA VERIFICATION** of the specific savings clause for the proceeding.
* Tax Year 2026-27 onwards → Income-tax Act, 2025.
* A notice issued on/after 01-04-2026 for an earlier year raises an explicit transition flag (procedure vs. substantive law).
* Section equivalents in the 2025 Act are **not** hard-coded; the registry holds them only when a CA has entered and verified them.

### 4.3 Draft → review → export
* Drafts are versioned; each version has a content hash.
* Legal references render only if the registry entry is `VERIFIED`; otherwise a visible `[LEGAL REFERENCE – REQUIRES CA VERIFICATION]` placeholder is inserted.
* Annexures are generated only from documents actually uploaded *and* marked as annexures by the user.
* Approval requires role `CA`, every mandatory checklist item ticked, and is bound to the draft hash. Any edit creates a new version → approval no longer valid.
* Export (DOCX) is refused unless a valid approval exists. Unapproved previews carry a "DRAFT – NOT APPROVED" banner.

## 5. Data model (SQLite)
`users, sessions, cases, documents, doc_index, notices, issues, evidence_items, recon_runs, tax_computations, legal_refs (user overrides), info_requests, drafts, review_checklists, approvals, ai_submissions, audit_log`. Schema: `noticemate/core/schema.sql`.

## 6. Security controls
* Passwords: `hashlib.scrypt` (n=2^14, r=8, p=1) with per-user salt; lockout after 5 failures.
* Sessions: random 256-bit tokens; only SHA-256 stored; 8-hour expiry.
* Role-based access (ADMIN, CA, STAFF); case-level access checks on every endpoint.
* Uploads: extension allow-list, magic-byte check, 25 MB limit, filename sanitisation, path-traversal guard.
* Optional at-rest encryption of stored documents (Fernet key from env).
* API binds to 127.0.0.1 by default; CORS restricted to the Streamlit origin.
* Secrets only from environment / `.env` (never committed).
* Logs: structured, with PII scrubbing filter.

## 7. Known limitations (v1)
See README §"Limitations" — summarised: rule-based (not AI) extraction of notice particulars; OCR quality depends on scan quality and Tesseract; no marginal relief / interest u/s 234A-C computation; 2025 Act section mapping must be entered and verified by the CA; single-machine use only (no multi-user server hardening such as TLS termination).

## 8. v2 additions

| Module | Code | Notes |
|---|---|---|
| Migrations | `core/migrations.py` | Versioned, additive only; SQLite online backup before migrating an existing DB |
| Dashboard | `services/dashboard.py` | Live KPIs/alerts from DB; access-scoped |
| Structured analysis | `services/analysis.py` | 13 sections; LOCAL (rules) or AI (via gateway); basis tag on every finding; versioned; CA accept/reject |
| Extended reconciliation | `services/recon_extended.py` | Transaction matcher (ref → date+amount → window, party option), bank book vs ledger, sales vs bank, AIS/26AS vs books, debtors roll-forward |
| Party register | `services/parties.py` | Lenders / partner capital / customer advances; identity · creditworthiness · genuineness · source-of-source mapping; cash-mode flags |
| Legal research | `services/research.py` | Statutory / judicial / practical / AI-propositions kept separate; propositions UNVERIFIED until CA verifies with a source |
| Review workflow | `services/review.py` (extended) | Comments (block approval while open), reject / changes-requested, history, PDF export |
| Providers | `services/ai_providers.py` | Anthropic (unchanged), Gemini (optional), error classification, optional provider web search; `ai_gateway.test_connection` |
| API | `api/routers/v2_routes.py` | All v1 routes unchanged |
| UI | `frontend/app.py`, `frontend/ui.py`, `.streamlit/config.toml` | Themed dashboard, cases, 13-tab workspace, providers, registry, admin |
| Upgrade | `scripts/upgrade_from_v1.py`, `scripts/v1_manifest.json` | Hash-checked in-place upgrade that skips user-modified files and never touches `.env`/workspace |
| Tests | `tests/test_v2.py`, `tests/ui_harness.py`, `tests/test_ui_smoke.py` | Headless UI run against real services |
