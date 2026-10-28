# UAE Corporate Tax Computation Assistant

A Windows-friendly Python desktop tool (PySide6) that reads a company's trial balance (TB) and general ledger (GL), asks clarifying questions, and prepares:

1. **Client computation workbook** - your supplied Excel template, populated (all figures in **AED**).
2. **Review workbook** - mapping, adjustment register, high-risk accounts, reconciliations, audit trail.
3. **Word tax-risk report** - observations, status of each item, open questions, rule sources.

> **Preliminary-review tool.** Output is a draft for a qualified person to review. Several tax rules are marked `UNVERIFIED`/`SECONDARY` in `ct_tool/config/rules.json` and must be checked against the official text. See `docs/KNOWN_LIMITATIONS.md` and `docs/TEST_RESULTS.md`.

## Principles built in
- Never invents data or tax rules; unknowns become open questions.
- **Proposed** and **Confirmed** adjustments are kept separate - only Confirmed items enter the computation.
- Elections and reliefs (realisation basis, Small Business Relief, QFZP, DTA relief, foreign tax credit...) are never applied automatically.
- Source files are never modified; every step is written to an audit trail.
- AI/online services are **not used**; no API keys are stored anywhere.
- All statements and the computation are in AED. Sheets that do not apply are omitted (and listed on the Assumptions / Summary sheet).

## Install

### Windows
1. Install Python 3.10+ from python.org (tick *Add python.exe to PATH*).
2. Unzip this folder, double-click **`setup_windows.bat`** (creates `.venv`, installs packages; once only).
3. Double-click **`run_app.bat`**.

*Optional - scanned PDFs:* install the Tesseract OCR program and add it to PATH. Excel/CSV and text-layer PDFs need nothing extra.

### macOS / Linux
```
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt        # or requirements-tested.txt for the exact tested versions
python run_app.py
```

## Operating instructions (GUI)
| Step | What you do |
|---|---|
| **1. Currency and FX** (asked first) | Choose the TB currency. AED: nothing more. USD: 3.6725 peg is pre-filled. Any other currency: enter AED-per-unit rates for the P&L, the closing balance sheet and equity, plus source and reason. Rates are never fetched online. A resulting translation difference needs your approval. |
| **2. Files** | Load the TB (xlsx/xls/csv/pdf), optionally the GL and prior-year TB. Check the preview, totals and warnings; confirm. |
| **3. Account mapping** | Review the proposed mapping (flagged accounts first); override where wrong. |
| **4. Questionnaire** | Answer entity, election, relief, loss, foreign-tax and related-party questions. Unanswered = open item. |
| **5. Risk review** | See flagged accounts / GL narrations by rule. |
| **6. Adjustments** | Each proposal is Proposed until you set Confirmed / Rejected (blocked items need an override note). The impact of pending items is shown separately. |
| **7. Computation and checks** | AED statements, tax computation, scenarios, reconciliation checks. |
| **8. Export** | Writes the workbooks, Word report and a `.ctproj` project file (save and reopen later). |

Menus: File (new/open/save), Help (known limitations, tax rules and verification status).

## Command line (same engine, no GUI)
```
python -m ct_tool.cli preview --tb path/TB.xlsx
python -m ct_tool.cli analyse --tb TB.xlsx --gl GL.xlsx --currency EUR ^
    --rate-pl 4.0 --rate-closing 4.2 --rate-equity 3.9 --rate-source "CBUAE ..." ^
    --approve-translation-difference --answers answers.json --decisions decisions.json --out output_dir
```
A non-peg currency without rates is refused. Without `--decisions`, nothing is confirmed.

## Your own template / letterhead
- Template: the bundled `templates/..._TEMPLATE.xlsx` is used by default; point to yours with the *Computation template* field on the Project / dashboard page (GUI) or `--settings-template`. Row structure is assumed to match the supplied template; changes made to it are logged on the Assumptions sheet.
- Letterhead: optional `.docx` used as the base of the Word report.

## Updating tax rules
Edit `ct_tool/config/rules.json` (parameters and per-rule `verification`, `source`, `date_checked`). Mapping/risk patterns: `mapping_rules.json`, `risk_rules.json`.

## Sample data and tests
`sample_data/generated/` holds synthetic TB/GL/PDF files (USD, EUR, AED); regenerate with `python sample_data/make_sample_data.py`.
`python -m pytest tests -q` runs 83 tests (needs LibreOffice `soffice` for the workbook-recalculation tests, and Tesseract for the OCR test).

`sample_data/format_tests/` has three more TB + GL pairs in **Tally-style**, **Oracle-style** and **ad-hoc Excel** layouts (see `READ_ME_FIRST.txt` there).

## Supported input layouts
Excel (.xlsx/.xls) and CSV TBs with: Debit/Credit columns, a single signed amount, an amount plus a Dr/Cr marker column, opening/period/closing columns, a heading spanning two rows, account code + name (or segmented codes such as Oracle `101.000.1000.0000.000`), and Tally-style group totals printed above ledgers (detected only when the printed Grand Total or debit = credit test shows double counting, then confirmed against the total). GLs: flat lists, or one block per ledger. Anything the reader cannot recognise is reported, never guessed - pick the header row and columns manually in the preview.

## Layout
`ct_tool/` extract.py (TB/GL/PDF/OCR) - fx.py - mapping.py - statements.py - risk.py - questionnaire.py - engine.py (tax computation) - excel_out.py / review_xlsx.py / word_out.py - service.py - cli.py - gui/.
