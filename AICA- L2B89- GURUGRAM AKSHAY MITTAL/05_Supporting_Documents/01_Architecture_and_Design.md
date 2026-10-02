# BRMCo Accounting Hub — Architecture (Phase 1)

## 1. Overall architecture

Two independent source-code projects that communicate only over HTTP(S):

```
CLIENT COMPUTER                                         BRMCo SERVER / CLOUD
─────────────────────────────────────────────           ───────────────────────────
Browser ──► BRMCo Local Host  http://127.0.0.1:8000     BRMCo Server Host  :8001 (HTTPS in prod)
             ├─ Web UI (frontend/)                        ├─ GET /health, GET /version
             ├─ Excel engine (app/excel)                  ├─ /api/v1/auth      (Phase 5)
             ├─ Accounting engine (app/accounting)        ├─ /api/v1/ai        (Phase 4)
             ├─ Validation (app/accounting/validation)    ├─ /api/v1/clients   (Phase 5)
             ├─ Tally adapter (app/tally)                 ├─ repositories  → MongoDB (Phase 5)
             ├─ Import history + audit (SQLite)           └─ secrets: AI key, DB URI (server only)
             └─ Server client (app/server_client) ── HTTPS ──►
                      │
                      ▼  XML over HTTP, localhost:9000
                  TallyPrime
```

The Server Host never reaches TallyPrime. The Local Host never reaches AI providers or databases directly.

## 2. Local Host responsibilities

- Serve the browser UI on `127.0.0.1` only.
- Generate Excel templates with dropdowns and validation, then read and validate uploaded files.
- Convert rows into balanced **Voucher** objects (double entry, GST, round off).
- Validate them: dates and financial year, GST, ledgers against the Tally master cache, balance, duplicates.
- Show a preview. Nothing is posted without explicit confirmation.
- Generate Tally XML, post it to local TallyPrime, and parse Tally's actual response.
- Keep import history, the audit log, cached masters and settings in SQLite.
- Provide demo mode (simulated Tally).
- Call the Server Host for `/health` and `/version` now, and for more services later.

## 3. Server Host responsibilities

- **Phase 1:** a stable API contract (`/health`, `/version` with `min_local_version` and a `features` map), placeholder modules, a repository abstraction, and secret-safe config and logging.
- **Later:** authentication and device tokens, client registry, central settings, the AI invoice-extraction proxy, MongoDB, and licensing.

## 4. Folder structure

```
brmco-accounting-local/
  app/
    main.py                  app factory, error handlers, static UI
    container.py             wires repositories + services
    api/                     routes.py (dashboard, settings, batches, server), sales.py, purchase.py,
                             journal.py, bank.py, tally.py, history.py, voucher_router.py (shared)
    accounting/              models.py (Voucher, LedgerPosting, InvoiceLine…), services.py (engine),
                             validation.py (business rules), gst.py (states, GSTIN, rates)
    excel/                   template_spec.py (single source of truth), generator.py, reader.py,
                             validator.py (cell parsing), samples.py
    tally/                   xml_generator.py (one builder per voucher type), client.py (real + demo),
                             response_parser.py, masters.py (sync + cached lookup)
    database/                database.py, models.py (schema), repositories.py (all SQL)
    services/                import_service.py (workflow), tally_service.py, settings_service.py,
                             audit_service.py, errors.py
    server_client/client.py  Server Host client
    config/                  settings.py (EnvSettings + AppConfig), logging_config.py
  frontend/                  index.html, css/app.css, js/api.js, js/app.js
  templates/  samples/  scripts/  tests/  docs/

brmco-accounting-server/
  app/
    main.py
    api/                     health.py, version.py, auth.py, ai.py, users.py, clients.py, settings.py
    services/                auth_service.py, ai_service.py, client_service.py
    repositories/            base.py, memory.py, factory.py
    config/                  settings.py, logging_config.py
  tests/
```

Changes from the brief:
- There are separate receipt and payment templates. Their ledger columns differ ("Party Ledger" vs "Party/Expense Ledger").
- `services/` and `container.py` were added to the Local Host so the API layer stays thin.

## 5. Data flow

```
Excel (.xlsx)
  │ excel/reader.py        file checks: real xlsx, template id, version, columns
  ▼
Raw rows
  │ excel/validator.py     cell parsing: dates, numbers, GSTIN, states, rates, Yes/No
  ▼
Parsed rows
  │ accounting/services.py group rows → vouchers; compute Dr/Cr postings
  ▼
Voucher objects  ◄── the pivot. Future inputs (AI extraction, APIs) produce these too
  │ accounting/validation.py  FY, GST, masters, balance, duplicates
  ▼
Batch stored in SQLite (status validated | invalid)
  │ UI preview → user confirms
  ▼
tally/xml_generator.py  (Sales/Purchase/Journal/Receipt/Payment builders)
  │ tally/client.py  POST, one voucher per request
  ▼
TallyPrime → response → tally/response_parser.py → SUCCESS | PARTIAL | FAILED
  ▼
import_history + posted_vouchers + audit_log
```

Excel code never builds XML, and XML code never reads Excel. Both meet only at the `Voucher` model.

## 6. Local ↔ Server API contract

| Call | Response (200) | Local Host use |
|---|---|---|
| `GET {SERVER_BASE_URL}/health` | `{"status":"ok","application":"BRMCo Accounting Hub Server","version":"1.0.0","time":"…","components":{"repository":"memory"}}` | Online/offline badge |
| `GET {SERVER_BASE_URL}/version` | `{"status":"ok","application":…,"version":"1.0.0","api_version":"v1","min_local_version":"1.0.0","environment":"development","features":{"auth":false,"ai_invoice_extraction":false,…}}` | Compatibility check; feature flags turn on future UI features |

Rules:
- `/health` and `/version` are permanent and unversioned. Everything else is `/api/v1/…`, and a breaking change means `/api/v2`.
- The Local Host sends `User-Agent: BRMCo-Local/<version>`. In Phase 5 it will add `Authorization: Bearer <device token>`, issued by `/api/v1/auth/device`.
- Any failure (DNS, refused, timeout, non-200, non-JSON) becomes `ServerStatus(reachable=false, message=…)`. The Local Host never crashes because the server is unavailable.
- Future AI flow (Phase 4): Local uploads the invoice → `POST /api/v1/ai/invoices/extract` → server calls the AI provider with its own key → structured invoice JSON → Local turns it into a `Voucher` → human review in the same preview screen → Tally.

## 7. Database design (Local SQLite)

| Table | Purpose |
|---|---|
| `app_metadata` | schema version |
| `app_settings` | key → JSON value (company, FY, Tally host/port, ledgers, server URL, demo) |
| `tally_masters` | (company, master_type, name_key) → name, parent, extra JSON (for example a stock item's unit) |
| `master_sync_log` | each sync attempt per type |
| `import_batches` | an uploaded file: status, counts, validated vouchers (JSON), issues (JSON), stored file, XML file |
| `import_history` | each posting attempt: company, FY, type, voucher numbers, Excel/XML names, record count, status, created/altered/ignored/errors, Tally response, per-voucher details, demo flag |
| `posted_vouchers` | vouchers Tally confirmed, with exact and fuzzy keys for duplicate detection |
| `audit_log` | time, action, company, voucher type, batch, details |

Masters are cached per Tally company key (`__DEMO__` for demo), so companies never mix.

Server: the `DocumentRepository` interface (get, list, upsert, delete) maps one-to-one onto MongoDB collections. There's an in-memory implementation now, and the backend is chosen with `REPOSITORY_BACKEND`.

## 8. Tally integration approach

- **Transport:** HTTP POST of XML to TallyPrime's built-in XML server (`http://host:port`, default 9000). The connect timeout is 5 s and the read timeout is configurable.
- **Connection test:** export the `Company` collection. The result lists the open companies and warns if the configured company isn't open.
- **Masters:** TDL collection exports for Ledger, Group, StockItem, Unit and VoucherType (name, parent, base unit).
- **Import:** `ENVELOPE/HEADER/TALLYREQUEST=Import Data`, `REPORTNAME=Vouchers`, and `SVCURRENTCOMPANY` when a company is configured.
  - Debit = `ISDEEMEDPOSITIVE Yes` with a negative `AMOUNT`. Credit = `No` with a positive amount.
  - Accounting-mode vouchers use `ALLLEDGERENTRIES.LIST`.
  - Sales and purchases with stock items use `Invoice Voucher View`, with `ALLINVENTORYENTRIES.LIST` + `ACCOUNTINGALLOCATIONS.LIST` and `LEDGERENTRIES.LIST` for the party, tax and round-off ledgers.
  - Party lines carry `BILLALLOCATIONS` (New Ref / Agst Ref), bank lines carry `BANKALLOCATIONS` (instrument/UTR), and journal lines carry `CATEGORYALLOCATIONS` / `COSTCENTREALLOCATIONS`.
- **Response:** parse `CREATED, ALTERED, IGNORED, ERRORS, EXCEPTIONS, LASTVCHID, LINEERROR`, after stripping illegal control characters. `SUCCESS` requires created + altered ≥ expected with zero errors and exceptions. An HTTP 200 alone is never success.
- **Voucher type names** are configurable (for example "Sales GST") and checked against the synced voucher types.
- **Posting one voucher per request** gives exact per-voucher results and accurate duplicate tracking.

**Before first live use:** import `samples/sample_*.xml` into a *test copy* of a company (Gateway → Import → Transactions) to confirm that your TallyPrime release and company features (GST, bill-wise, cost centres, godowns) accept the tags. If a feature needs extra tags, change only the relevant builder in `tally/xml_generator.py`.

## 9. Development sequence (as built)

1. Server skeleton: `/health`, `/version`, placeholders, repository interface, tests.
2. Local Host core: config, SQLite schema and repositories, logging, app factory, static UI, dashboard.
3. Sales: template spec → generator → reader → cell validator → accounting engine → business validation → preview.
4. Tally: XML builders, response parser, client, demo client, connection test, posting.
5. Purchase, Journal, Bank Receipt, Bank Payment on the same pipeline (spec plus engine branch plus XML builder).
6. Import history, audit log, master sync with cached lookup, duplicate detection.
7. Local ↔ Server link (`server_client`), dashboard badge, settings test button.
8. Samples, docs and the test suite. 52 local and 5 server tests pass.

## Extending in later phases

| Need | Where |
|---|---|
| New voucher type (Contra, Credit/Debit Note) | add a `VoucherKind`, `TemplateSpec`, engine branch in `accounting/services.py`, and XML builder |
| GSTR-1 JSON (Phase 3) | new `gst/` package that reads `Voucher` objects or Tally exports. No Excel/Tally coupling |
| AI extraction (Phase 4) | Server `/api/v1/ai`; Local maps the response → `Voucher` → existing validation and preview |
| Auth / multi-client (Phase 5) | Server `auth` + Mongo repositories; Local `server_client` adds a token header |
| Richer master sync (Phase 2) | extend `MASTER_COLLECTIONS` + `MasterRecord.extra` (GSTIN, state, bill-wise flag) |
