# Developer Guide

## Architecture overview

```
tally_converter/
|-- backend/           FastAPI app, SQLite database, all business logic
|   |-- app/
|   |   |-- api/       HTTP endpoints (thin - delegate to services)
|   |   |-- database/  SQLAlchemy models
|   |   |-- schemas/   Pydantic request/response models
|   |   |-- services/  All actual business logic lives here
|   |   `-- utils/     Pure helper functions (dates, numbers, paths, security)
|   `-- tests/         pytest test suite
|-- frontend/          React + TypeScript + Vite + Tailwind SPA
|-- sample_data/        Synthetic test Excel files
|-- installer/          Inno Setup script
`-- TallyConverter.spec PyInstaller build spec
```

**Design principle**: API route handlers in `app/api/*.py` should stay
thin - validation, extraction, normalization, mapping, and XML
generation logic all live in `app/services/*.py` so they're testable
independent of FastAPI/HTTP.

## The never-invent-data principle, concretely

This is enforced at the `accounting_normalizer.normalize_row()` layer
(and its bank-statement counterpart `bank_parser.normalize_bank_row()`):
any field that can't be parsed is left `None` and a human-readable
reason is appended to `review_reasons`. The API layer
(`app/api/upload.py`) turns any non-empty `review_reasons` list into
`TransactionStatus.REVIEW_REQUIRED` rather than a default value.

If you add a new parser (e.g. a new file format), route its raw field
dict through `normalize_row()` rather than writing new
required-field-defaulting logic - that's how every other parser stays
consistent.

## Adding a new voucher type or changing ledger structure

All Tally XML generation lives in
`app/services/tally_xml_generator.py`. Each voucher type has its own
`generate_*()` method that:
1. builds a list of `LedgerEntry` (ledger name, amount, is_debit)
2. calls `build_voucher()`, which validates the debit/credit balance
   (raises `VoucherNotBalancedError` if unbalanced) and emits the
   `<VOUCHER>` XML element
3. gets wrapped into an `<ENVELOPE>` via `build_envelope()`

To add a new voucher type, follow the pattern of `generate_sales()` -
build your ledger entries, then call `self.build_voucher(...)`. Write
a test in `tests/test_tally_xml.py` asserting the resulting ledger
entries sum to zero (this is the balance invariant every voucher must
satisfy).

**Before trusting new XML output against real Tally data**, test it
against a TallyPrime sample/test company (Gateway of Tally &rarr;
Import Data) - see the warning in README.md. Field names/structure
that work in one TallyPrime version/configuration aren't guaranteed to
work in all of them.

## Ledger role mapping

Voucher generation needs to know which real Tally ledger to use for
roles like "the sales ledger" or "the CGST ledger." This is the
`LedgerMapping` table (`role_key` -> `tally_ledger_name`), managed via
`/api/mappings/ledger` and the Mappings screen. `app/api/tally.py`'s
`_resolve_ledger()` looks these up when building a voucher; if a
required role isn't mapped, the transaction is skipped (never
defaulted to a guessed ledger name) and reported back to the user.

## Parsers

| File | Handles |
|---|---|
| `excel_parser.py` | .xlsx/.xls, auto header detection + column aliasing |
| `csv_parser.py` | .csv, delimiter/encoding detection, reuses excel_parser's alias table |
| `pdf_parser.py` | .pdf - digital text extraction via pdfplumber, or routes scanned pages through OCR |
| `image_processor.py` | OpenCV preprocessing pipeline (resize/grayscale/denoise/threshold/deskew) |
| `ocr_engine.py` | pytesseract wrapper, confidence scoring |
| `invoice_extractor.py` | Regex-based field extraction from OCR/PDF text |
| `bank_parser.py` | **Deliberately separate** from excel_parser - a bank statement's "Description" column is a narration, not an invoice item description. Conflating the two alias tables caused real bugs during development (see inline comment in the file). |
| `document_classifier.py` | Heuristically routes a file to the invoice vs. bank-statement path |

## Running tests

```bash
cd backend
pytest tests -v
```

The test suite covers date parsing, number parsing, GST validation,
Tally XML generation (including balance-enforcement and XML-escaping),
the Excel parser (including a regression test against the real
`sample_data/sales.xlsx`), the accounting normalizer's
never-invent-data behavior, and the bank parser (including the
description/item_name regression mentioned above).

`build_windows.bat` runs the full suite and **aborts the build** if
any test fails - don't bypass this when cutting a release.

## Adding a new API endpoint

1. Add/extend a Pydantic schema in `app/schemas/`.
2. Add the route in the relevant `app/api/*.py` file (or create a new
   router file and register it in `app/main.py`).
3. Keep business logic in a service function, not inline in the route
   handler.
4. Add the corresponding call + TypeScript types in
   `frontend/src/services/api.ts` and `frontend/src/types/index.ts`.

## Frontend structure

- `src/services/api.ts` - single typed fetch wrapper for the entire
  backend API; add new calls here rather than calling `fetch()`
  directly from components.
- `src/types/index.ts` - TypeScript interfaces mirroring the backend
  Pydantic schemas. Keep these in sync manually (no codegen is wired
  up yet - a natural improvement would be generating these from
  FastAPI's OpenAPI schema).
- `src/pages/*.tsx` - one file per screen, matching the sidebar nav in
  `src/components/Layout.tsx`.
- `src/components/Badges.tsx` - shared small presentational components
  (status/confidence/validation-level badges, `Card`, `PageHeader`).

## Known follow-ups / not yet implemented

- `GET /api/import` returns batches from the *current* database but
  has no pagination/filtering UI beyond a flat list - fine for
  moderate volumes, worth revisiting if batch counts grow large.
- PDF bank statements are routed through the invoice-style regex
  extractor rather than a dedicated PDF-table-based bank parser (see
  the comment in `app/api/upload.py::_process_pdf`) - build this once
  you have real customer bank-statement PDFs to tune extraction
  against, rather than guessing at their layout in advance.
- The `frontend/src/types/index.ts` interfaces are hand-maintained;
  consider generating them from the FastAPI OpenAPI schema
  (`/openapi.json`) if the API surface grows significantly.
- No authentication/multi-user support - the app binds to
  127.0.0.1 only and is designed for single-user, single-machine use
  per the spec. If multi-user access is ever needed, this needs a real
  auth layer before considering binding beyond localhost.
