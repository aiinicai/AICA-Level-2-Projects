# GSTwithNihal Redaction Tool

**Project:** AICA - L2B106 - Vasai - GSTwithNihal Redaction Tool  
**Submission:** GSTwithNihal Redaction Tool  
**Contributor account:** nihalchandjain

A Python PDF redaction application for preparing tax and professional documents for sharing. It combines pattern detection, label/layout rules, document-wide matching, and a user-supplied names list. A PyQt6 desktop interface supports batch processing and manual review; a command-line interface is also included.

## Features implemented in source

- Configurable detection categories for personal and business names, addresses, PAN, GSTIN/UIN, Aadhaar and other identifiers, contact details, financial fields, demographics, and digital identifiers.
- Optional Tesseract OCR for scans and image regions.
- Rules intended to preserve case-law citations, statutory text, officer details, and quoted passages. These exceptions can intentionally leave names or other information visible.
- PyMuPDF redaction annotations are applied to remove selected text and image pixels. Vector line art is preserved by the implementation; complete visual-content sanitisation is not established.
- Review window with manual selections and boxes, metadata-cleanup attempts, leftover-pattern checks, and a CSV report of filenames, pages, categories, and counts.

These are source-observed capabilities, not a claim that every category is reliably detected.

## Requirements and setup

Python 3 with support for the listed packages. The reviewed source uses modern type annotations; Python 3.10+ is a practical starting point, but a full version compatibility matrix has not been tested. Windows is the primary apparent target; other platforms have not been validated.

Use a separate environment and install dependencies:

```text
python -m venv .venv
.venv\Scripts\activate
python -m pip install pymupdf PyQt6 pytesseract pillow
```

Dependency versions were not pinned in the original project. OCR also requires Tesseract and suitable language data. The app includes automatic dependency and OCR setup; first launch may install software and access the internet, including GitHub-hosted OCR resources. Even --no-ocr is parsed after startup setup, so it does not guarantee a network-free launch. No installers or downloads were run during this review.

## Usage

Launch the interface:

```text
python gstwithnihal_redaction_tool.py
```

Add PDFs, choose categories and preservation options, optionally supply names, choose an output folder, process, and review each output before sharing.

Command-line examples:

```text
python gstwithnihal_redaction_tool.py input.pdf -o output --no-ocr
python gstwithnihal_redaction_tool.py input.pdf -o output --names names.txt
```

The names file contains one entry per line. OCR is enabled by default when available. Use a separate output folder. Output names normally use _redacted; a CSV named redaction_report.csv is written to the output location. Password-protected PDFs must first be unlocked using an authorised workflow. Existing outputs and reports should be backed up before rerunning.

## Privacy and limitations

The reviewed PDF processing function operates on local files; startup has network-capable installation paths. This is not an independently verified offline-only application. Automated rules and OCR may miss sensitive text or redact useful content. Preservation rules may retain sensitive names in protected contexts. Pattern-based leftover checks cannot certify that a document is safe. Metadata cleanup catches and suppresses some failures. Review visible content, searchable text, images, annotations, attachments, and metadata before disclosure.

## Review validation

On 6 November 2026, a synthetic one-page PDF was processed through process_pdf with OCR disabled and without invoking main or installers. A sample PAN and email were absent from the saved file's extracted text, ordinary text remained, and a rendered page showed the intended black redactions. No processing error or warning was returned. This limited test does not validate OCR, the GUI, every category, malformed PDFs, or all embedded content.

## Files in this review package

- gstwithnihal_redaction_tool.py: unchanged source from the supplied ZIP.
- README.md: this documentation.
- requirements.txt: unpinned package names derived from source.
- .gitignore: proposed local/generated-file exclusions.

Original PDFs, redacted PDFs, CSV, image, video, and upload guide are deliberately absent from this proposed source-only package. They remain in the original archive. No synthetic sample is bundled with this package.

## Licence

The archive contains no project licence. Rights to distribute the source, embedded branding, and dependency combinations require confirmation. No licence is invented or granted by this README.
