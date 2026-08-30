# Architecture

Bank Statement Converter is a local-first Python/Flask web application designed for processing, reviewing, and exporting bank statements (Digital and Scanned) with total privacy.

## Core Pipeline (Stages 0-9)

1. **Intake (`pdf_intake_service.py`)**: Accepts PDF files. Encrypted files trigger a password prompt. Extracts text layout via `pdfplumber`.
2. **OCR Hybrid Flow (`ocr_service.py`)**: Identifies pages with low digital text. Routes scanned pages to `OcrEngineService` (powered by `rapidocr-onnxruntime`). Produces an `effective_extraction.json` overlay.
3. **Extraction & Normalization (`extraction_service.py`, `transaction_normalizer.py`)**: Maps coordinate bounding boxes to structured table candidates using Bank Profiles. Converts arbitrary formats into standardized `Date, Narration, Ref, Debit, Credit, Balance`.
4. **Validation (`validation_service.py`)**: Performs rigorous double-entry math validation across page boundaries. 
5. **Review (`review_service.py`)**: If validation flags anomalies or mismatches, the user can manually resolve them in the browser. Corrections are tracked immutably in `reviewed_statement.json`.
6. **Export (`export_service.py`, `excel_exporter.py`)**: Compiles the final valid statement into a structured XLSX using `openpyxl`.

## Data Model & Immutability

- **`raw_extraction.json`**: Pure machine output from digital intake. Never mutated.
- **`ocr_result.json`**: Output from the OCR engine. Never mutated.
- **`effective_extraction.json`**: Merged digital and OCR layout.
- **`normalized_statement.json`**: Structured parsed output.
- **`reviewed_statement.json`**: Tracks user corrections.

## Database Schema (v9)
Local SQLite tracks `jobs`, `profiles`, `profile_revisions`, and `job_exports`. Actual statement contents are kept on disk as JSON artifacts to avoid bloating the database and to maintain clear security bounds.

## Deployment Model (Stage 10)
Shipped as a source release. The `START_BANK_CONVERTER.bat` script handles bootstrap: detecting Python, generating a local `.venv`, running `pip install`, and spinning up the Flask server on `127.0.0.1`.
