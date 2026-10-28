# Test results

Run date: 2026-10-19. Environment: Linux, Python 3.13.16, LibreOffice 24.2.7.2 (headless), Tesseract installed, PySide6 6.12.0 (offscreen).

Command: `python -m pytest tests -q` -> **83 passed** (about 40 s).

| File | Tests | What is covered |
|---|---|---|
| test_extract.py | 9 | TB from xlsx/csv/PDF (table, text-layer by column position, scanned via OCR); sign handling; GL reconciles to TB; unbalanced TB reported; source files unchanged |
| test_fx_mapping.py | 9 | AED (no FX), USD peg, non-peg without rates refused, EUR manual rates + translation difference, rate effects; mapping rules, code-class inference, overrides, unmapped accounts |
| test_engine.py | 18 | Nothing counted until Confirmed; blocked/rejected/overridden items; 9% with AED 375,000 nil band; realisation-basis scopes and election conditions; exempt dividends; 75% loss cap; loss year; foreign tax credit gating and cap; SBR; QFZP; interest limitation proposal; scenarios |
| test_outputs.py | 16 | Excel formulas recalculated in LibreOffice equal the Python computation (USD scope A, loss, SBR, QFZP, EUR); inapplicable sheets omitted; no stale names/links; review workbook; Word report structure, wording and letterhead; project round trip; CLI |
| test_formats.py | 6 | Tally-style TB/GL (group sub-totals, party ledgers, ledger blocks), Oracle-style (segmented accounts, period columns, journal lines), ad-hoc Excel (Dr/Cr marker, text amounts, abbreviated GL headings); each reconciles to the same profit |
| test_marjan.py | 22 | Hand-calculated example (45-account AED TB with disallowed items): proposed vs confirmed, five variants, scope A election, recalculated Excel formulas, post-closing TB refused, CSV/number-format/header-row/damaged-file/file-name bugs found in the audit |
| test_gui_smoke.py | 3 | Full GUI flow headless (and choosing AED on the first page): FX gate, load files, analyse, decide, export |

Example reconciled result (synthetic USD, scope A, all adjustments confirmed): taxable income AED 14,897,496.25, tax AED 1,307,025 - Excel (recalculated) and Python agree.

Rendered pages of the client workbook and Word report were also inspected visually (LibreOffice -> PDF -> images).

## Audit (not part of the suite)
A scripted GUI run (Currency -> real file load in the worker thread -> mapping override -> questionnaire -> confirm adjustments -> export -> save -> new -> reopen -> change currency) was run with a Python exception hook and a Qt message handler: no exception or Qt warning after the fixes in docs/CHANGELOG.md. A 20-variant file-format stress run (CSV delimiters x number styles, text amounts, damaged files) read every valid variant exactly.

## Not tested
- A real Windows machine, the `.bat` scripts, or Excel desktop (formulas verified with LibreOffice only).
- Real Tally, Oracle or other system exports (the three layouts were written to imitate them from general knowledge; real exports vary by version and report options),
- Real client files, real GL PDFs, real or poor-quality scans (OCR tested on clean synthetic scans only).
- Large ledgers (performance), concurrency, accessibility.
- Correctness of the tax rules themselves: tests confirm the code applies the configured rules, not that the configured rules match current law (most are marked UNVERIFIED).
- The AI option does not exist in this version.
