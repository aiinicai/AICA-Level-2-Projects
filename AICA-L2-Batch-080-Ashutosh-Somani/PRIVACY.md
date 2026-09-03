# Privacy Policy - Bank Statement Converter

## Local First Architecture
Bank Statement Converter is designed as a **Local First** application. This means:
- All processing, extraction, normalization, and review happens strictly on your local machine.
- Bank statement PDFs are never uploaded to any remote server or cloud service.
- The application binds only to `127.0.0.1` (localhost), ensuring it is not accessible from the external network.

## OCR Processing
- Optical Character Recognition (OCR) for scanned PDFs is performed completely offline using `rapidocr-onnxruntime`.
- No cloud OCR APIs (like Google Cloud Vision or AWS Textract) are used.
- The OCR models are stored locally on your machine.

## Telemetry and AI
- No external AI services (like OpenAI, Anthropic, Gemini) are used.
- No usage telemetry, tracking, or crash analytics are sent to the developer.

## Data Storage and Logs
- Your parsed transactions are stored in a local SQLite database (`data/bank_converter.db`).
- Application logs (`logs/`) rotate locally and are intentionally filtered to exclude sensitive text, OCR output, passwords, and private financial values.
- Generated Excel workbooks remain locally in the `output/` directory.

## Data Deletion
- Because the application is fully local, you control your data.
- Deleting the `data/`, `output/`, and `temp/` directories permanently purges all processed statements and extraction records.
