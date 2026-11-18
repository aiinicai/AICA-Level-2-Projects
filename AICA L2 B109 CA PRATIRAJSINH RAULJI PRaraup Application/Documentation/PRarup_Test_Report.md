# PRarup 1.0 test report

Date: 2026-11-13. Host: Windows 11 x64, Python 3.15.2, PyQt6 6.12.0, SQLAlchemy 2.1.8, Jinja2 3.1.6, docxtpl 0.20.2, python-docx 1.2.0, PyInstaller 6.22.3.

## Automated verification
60 tests passed in 13.36 seconds in the final source run. Coverage includes existing navigation, database counts and transaction/backup regressions; v1-to-v2 database migration and record preservation; client CRUD/validation/prefill/deletion associations; history duplication/archive; custom template validation, bounded loops, package versions, enable/restore, supported DOCX import and rejection; tampered/traversal backup rejection; full workspace restoration and recovery copies; password salting/verification; 16 document generators and extractable DOCX/PDF outputs; three clean print styles; favorites; five/fifty-partner cases and 100% share rules; LLP designated-partner checks; stale-preview prevention and save/reopen/manual editing.

The Windows native Qt platform is used for font-dependent tests: offscreen mode exposed zero Windows system fonts on this host. File-header-only PDF checks were supplemented with text extraction and footer pagination checks.

## Packaged executable
The self-contained PRarup_v1.0.exe passed all 16 questionnaire → review → prepare → save → reopen → Word/PDF checks without PYTHONPATH. PDF text extraction and Page 1 of N were checked for every type. Packaged office checks passed client creation/prefill, template versions and disable/restore, consistent workspace backup/restoration, history archiving and password verification. Normal --smoke-test launch exited successfully. No adjacent _internal directory or external Python was used.

## Visual verification
UI screenshots inspected: library, Clients, template workshop, Settings, History, questionnaire and A4 preview. Representative legal output pages were inspected across serif/classic/modern style samples and LLP, rent, affidavit and authority layouts. The final illustrative sample uses Georgia, A4 margins, explicit headings and numbered footers. A sample DOCX was opened read-only in a dedicated hidden Microsoft Word instance and exported to PDF; all three final Word-rendered pages were inspected. The bundled LibreOffice renderer is unavailable on this host, so Word was used for that DOCX visual check. Native PDF and Word can paginate differently.

User and developer manuals were rendered and reviewed. Earlier layout issues corrected: theme-font overrides in Word, witness lines being mistaken for numbered headings, stranded PDF clause headings, tight paragraph spacing and offscreen missing-font output.

## Limits and remaining work
No physical printer output, separate clean Windows machine, Windows 10, Python 3.12 environment, signing/installer, independent accessibility review or large-office performance test was completed. Data remains unencrypted. Text-only DOCX template import does not preserve arbitrary tables/images/layout. Sixteen available templates do not cover every item in the original brief. Legal production approval, state-specific execution verification and remaining document types are still outstanding. No built-in template is legally certified.
