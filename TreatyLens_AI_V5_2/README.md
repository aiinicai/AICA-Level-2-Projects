# TreatyLens AI V5.1 — Revised DTAA library + reset confirmation

## Run on Windows

1. Extract the ZIP into a new folder.
2. Close any older TreatyLens Python console/instance using port 8765.
3. Double-click `START_TreatyLens.bat`.
4. Open `http://127.0.0.1:8765` in Chrome or Edge; press Ctrl+Shift+R if you previously opened an older version.

Python 3.10+ is required. No extra libraries or API key are required to run the application.

## What's new

- **87 countries and 362 treaty-rate entries** from the supplied revised workbook (DTAA Rates).
- Of those, **23 entries have no numerical rate cap** in the workbook. They remain unresolved rather than being treated as zero percent.
- Sheet 2 recipient-type options and Sheet 3 domestic-rate/surcharge/cess/remittance data have been refreshed from the revised workbook.
- Comparison page and evidence viewer show the new country selections, article numbers, workbook rates and source treaty passages.
- After `Print / PDF`, `Send email to CA Harshal Fifadra` or `Save HTML report`, the app asks **Do you want to reset the details?**. `OK` clears the form and result; `Cancel` returns to the existing assessment outcome.
- A pre-existing form-reset JavaScript bug (form control masking native `reset()`) has been fixed.

## Important limitations

- The revised workbook has **no PDF page-number or filename column**. Evidence appears with article number, source text and workbook row; page references display **Not provided in revised workbook**. We have not invented page numbers.
- Source rates are **workbook reference figures** and have not been independently verified against treaty protocols, amendments, MLI conditions or changes in legislation.
- Some rate rows are conditional. The engine uses matching recipient categories only when a single record matches; ambiguous/no numeric rate returns `Pending` rather than guessing.
- Treating every missing No-PE declaration as requiring domestic-law withholding and the NIL business-profits-clause branch are *prototype-specific user-requested assumptions*, not reliable conclusions of Indian tax law. Seek tax professional review before filing or remittance.
- The gross-up calculation remains the requested formula. Tax-inclusive vs tax-exclusive meaning and actual contract clauses must be reviewed.
- A browser cannot confirm that a PDF was actually printed/saved, an HTML file finished saving, or that an external email was sent. The confirmation appears when print flow exits or after a download/email composer is launched. The email is only drafted; PDF/supporting documents must be attached manually.
- The email recipient address was not provided; the default email client opens with a blank To field and the suggested subject/body.

## Contents

- `index.html`: integrated web UI
- `server.py`: localhost Python server
- `tax_engine.py`: workbook-driven conditional calculation engine
- `rates_database.json`: regenerated database from revised workbook
- `reference_workbook.xlsx`: original revised workbook, unchanged
- `test_v51.py`: engine and API regression tests

## Test instructions

Run `python -m unittest -v test_v51.py` in this folder.

Tests completed in the build environment: 17 Python/API tests passed. Browser fixture tests passed for 87-country display, assessment, HTML save reset Yes/No and print reset No. Browser live localhost navigation is blocked by the development environment, so full localhost end-to-end Windows testing is still recommended.


## V5.2 UI update
- Sidebar jurisdiction count is now dynamically taken from `/api/data` instead of hard-coded 20.
- Removed Overview > Project coverage panel, including the metrics and explanatory banner.
- Removed the footer shown with that panel.
- All tax calculations and backend data are unchanged from V5.1.
