# Local verification

Verified on Windows with Python 3.14.6 on 21 September 2026.

- 40 automated tests passed across the full 37-test run and the subsequent
  11-test targeted run (including 3 added reference-validation checks). They cover
  extraction/OCR, evidence formats, live-search contracts, strategy gates,
  critical review, invented-reference rejection and stale-record handling.
- Tesseract 5.4.0.20240606 installed; English (`eng`) and orientation (`osd`) data available.
- Searchable and mixed-PDF extraction, encrypted/corrupt/oversized-file rejection,
  all-chunk coverage, source checks, and relative/conflicting deadline handling passed.
- Streamlit sample, editor persistence, draft-style regeneration, undo, failure
  preservation and clearing passed.
- Word content matches edited text; subject formatting and margins checked.
- Dependency consistency and Python compilation passed.
- Browser reviewed at the in-app viewport. The sample results and deadline are
  visible, the copy button reports success, and a real scanned upload reaches the
  expected API-configuration message after successful text extraction.

Live provider calls are **not verified**: no API credential was available.
Provider and web-search tests use mocks. Set a valid key and account-supported model in `.env`
and use the fictional PDF before processing confidential notices.

The modern blue/gold/yellow/grey/maroon layout and seven-stage workflow have been
implemented. The offline demo deliberately supplies no fabricated legal sources.

Word output was verified structurally, not rendered in Microsoft Word or
LibreOffice. Review final letter pagination in Word before filing.

`requirements-tested-windows.txt` records the exact tested environment (including
test dependencies). Use `requirements.txt` for a normal portable installation.
