# Changelog

## [1.0.1] - 2026-08-30
### Fixed (UAT Defect)
- Fixed a hardcoded UI block preventing users from navigating to "Bank Profiles".
- Implemented a "Create Profile From Statement" workflow fallback when generic normalization fails to resolve a transaction table.
- Passed job context cleanly into the visual builder so users can easily configure coordinate layouts for unknown banks.
- Added final submission branding and author contact details.

## [1.0.0] - 2026-08-30
### Added (Stage 10 - Production Capstone Readiness)
- Final Capstone packaging, deployment, diagnostics, and backup/restore.

## [0.9.0] - 2026-08-30
### Added (Stage 9 — Local OCR Support)
- Local OCR support for scanned and mixed digital/scanned PDF statements using `rapidocr-onnxruntime`.
- Automatic per-page scan detection with configurable word-count threshold (`ocr.limited_text_word_threshold`).
- OCR word bounding box extraction mapped to PDF coordinate space via `pypdfium2` rendering.
- OCR confidence scoring (0-100) per word with configurable minimum confidence filtering.
- Cooperative OCR cancellation endpoint (`POST /ocr/<job_id>/cancel`) using per-job `threading.Event`.
- Per-page failure handling with overall `OCR_PARTIAL` status for partially successful jobs.
- Retry failed pages endpoint (`POST /ocr/<job_id>/retry-failed`) — re-runs OCR only on failed pages.
- Max-page limit guard (`ocr.max_pages`) that rejects jobs exceeding configured page count without starting a worker.
- Thread-safe per-job locking for all OCR operations (trigger, cancel, retry, status).
- Stale `OCR_RUNNING` detection and recovery to `OCR_INTERRUPTED` on server restart.
- `ocr_confidence` property alias on `RawWord` for standardized confidence access (float 0-100).
- Effective extraction generation that merges OCR pages into the original digital extraction.
- DB schema migration v9 with OCR status tracking columns.
- Dependencies added: `rapidocr-onnxruntime==1.2.3`, `pypdfium2==5.13.0`.
- OCR configuration section in `config.ini`.
- Comprehensive Stage 9 test suite (~40 new tests).
- Offline runtime verification documentation in README.
- OCR coordinate conversion documentation in README.
- Python version compatibility documentation (3.12+, tested on 3.13.5).

## [0.8.0] - 2026-08-30
### Added
- Stage 8 Professional Excel Export via `openpyxl`.
- High-quality exported `.xlsx` workbook containing Transactions, Summary, Exceptions, and Audit Trail sheets.
- Dynamic source selection: exports the verified Reviewed Statement if present, seamlessly falling back to the machine normalized state.
- Ensures validation consistency by explicitly checking and refreshing stale validations against the current review revision before export.
- Spreadsheet anti-injection security implemented (prepends `'` to dangerous symbols `=+-@`).
- Exact `Decimal` financial values mapped to numeric Excel cells; `None` explicit mapped to blank cells.
- Safe automated filename generation (preventing overwrites via timestamp incrementation).
- Masked sensitive account data and clean formatting using native Excel tables and freeze-panes.

## [0.7.0] - 2026-08-30
### Added
- Stage 7 Advanced Review and Corrections workflow.
- Exception-first review UI for resolving validation anomalies.
- Side-by-side PDF source viewer with semantic coordinate highlighting.
- Exact Decimal financial inline editing and structural corrections (merge, split, non-transaction).
- Immutable machine baseline with a safe cloned `reviewed_statement.json`.
- Strict job-local Correction Audit Trail logging before/after states.
- Optimistic concurrency to prevent stale browser overwrites (Review Revision).
- Automatic full Stage 5 revalidation upon every correction.
- Deterministic Profile Suggestion rules based on repeated correction types.
- Strict isolation of sensitive financial review data from global application logs.

## [0.6.0] - 2026-08-29
### Added
- Stage 6 Bank Profile Engine.
- Reusable local bank/layout profiles stored as JSON.
- Deterministic profile matching using heuristic score.
- Profile manager for versioned saves, atomic writes, backups, import/export.
- Visual profile builder over PDF preview for bounding boxes and column dividers.
- Coordinate-based extractor that integrates securely with Stage 4 Normalizer and Stage 5 Validator.
- Zero client transactions, account numbers, or passwords saved in profile JSON.
- Schema v6 SQLite migration for tracking profile usage.

## [0.5.0] - 2026-08-29
### Added
- Stage 5 Validation and Exception Engine.
- Implemented `ValidationService` for exact `Decimal` transaction arithmetic balancing.
- Added statement-level total credits/debits closing balance reconciliation.
- Introduced `ConfidenceService` with transparent heuristic review scores (0-100).
- Created `ExceptionService` for deterministic anomaly categorization (e.g., `BALANCE_MISMATCH`, `NO_DEBIT_OR_CREDIT`).
- Implemented `validation_routes.py` with clean HTML diagnostic templates (`validation_summary.html`, `exceptions.html`).
- Performed v5 SQLite migration to persist aggregate validation job statuses.
- Maintained 100% precision audit rules (zero financial `float` usage, zero `REAL` columns).

## [0.4.0] - 2026-08-29
### Added
- Stage 4 Bank Detection and Transaction Normalization.
- Bank detector for deterministic name signatures.
- Standard Library parsing for dates (`date_utils.py`) and exact Decimal amounts (`amount_utils.py`).
- Generic metadata extraction (statement period, masked account number, IFSC).
- `TransactionNormalizer` resolving multiline narrations, table headers, footers, and CR/DR types.
- Saved normalizations remain as local JSON, averting SQLite bloat.
- Normalization Summary and Transactions Preview UI added.
### Known Limitations
- Verified Bank Profiles, OCR, Exception Engine, and Excel Export remain unimplemented (scheduled for future stages).

## [0.3.0] - 2026-08-29
### Added
- Stage 3 Digital PDF Extraction Foundation.
- Integrated `pdfplumber` for text and word coordinate extraction.
- Developed a `BaseExtractor` abstraction to normalize extraction output without coupling to a specific PDF engine.
- Diagnostic extraction classification to flag purely digital text, limited text, or scanned files (to prepare for future OCR).
- `ExtractionResult` and raw models to standardize job parsing.
- Extracted artifacts (word level geometries and raw text strings) are safely dumped to local temporary JSON.
- Diagnostic interface added to the preview page to let users visually verify the text layer and candidate tables.
### Known Limitations
- Transaction extraction, OCR, and bank profiles are NOT implemented yet. Table candidate logic remains fully generic.

## [0.2.0] - 2026-08-29
### Added
- Stage 2 PDF Intake and Preview.
- Added pypdf dependency for safe local metadata extraction.
- Local PDF upload endpoint with extension and limit validation.
- SQLite migration to track upload jobs (sha256, page_count, encrypted flag).
- PDF encryption check and local password entry workflow.
- Secure local PDF storage and serving.
- Official Mozilla PDF.js integration for in-browser local preview.
- File integrity checks (SHA-256) and temporary cleanup logic.
- Comprehensive test suite for hashing, validation, encryption, and routing.
### Known Limitations
- Transaction extraction, OCR, and bank profiles are NOT implemented yet (starts in Stage 3).

## [0.1.0] - 2026-08-29
### Added
- Stage 0 and Stage 1 implemented.
- Flask application factory structure.
- Windows batch launcher and Python launcher.
- SQLite database foundation and migrations.
- `config.ini` parsing and logging setup.
- Professional application shell (HTML, CSS, JS).
- Pytest test suite.
