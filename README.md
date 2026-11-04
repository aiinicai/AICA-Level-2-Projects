# GXVAN — GST Purchase Register, 2A/2B Reconciliation & Smart PDF Suite
*a product of Vantage* · © 2026 Vantage Tax Consulting LLP

GXVAN is an **offline** desktop tool (Windows first; also runs on macOS and Linux) for Vantage Tax Consulting LLP. It covers three modules:

| Module | What it does |
|---|---|
| **A · PR Builder** | Reads the client's document dump (text PDFs, scanned PDFs, photos and multi-invoice PDFs). It extracts the GST particulars with a confidence score per field, validates them (GSTIN mod-36 checksum, arithmetic, IGST vs CGST+SGST) and matches the documents to the client PR. It then classifies each line (vendor type, goods/services, tax treatment, ITC eligibility, foreign VAT, RCM), runs a compliance checklist and opens a three-pane review screen. The output is a **Finalised PR** with the GSTR-2B columns first. |
| **B · Reconciliation** | Parses GSTR-2B (portal Excel **and** JSON) and GSTR-2A, then reconciles them with the Finalised PR or a client PR. It runs multiple passes: exact, fuzzy, PAN-level, imports (IMPG), CDN, amendments (B2BA/CDNRA) and cross-period. Results go to an interactive grid, an Excel report and a one-page PDF on the firm letterhead. |
| **C · PDF & Image toolkit** | 16 PDF tools plus the Smart Invoice Reader: merge, split, extract, page numbers, rearrange, PDF↔images, password (AES-256), rotate, compress, watermark, **true** smart redaction, compare, Bates numbering, sanitize, OCR and letterhead. |

**Confidentiality.** The app makes no network calls at runtime. The only time it touches the network is the one-time `pip install`. There is no telemetry and no cloud OCR. Source files are never modified, and every output is written, with a timestamped name, to a folder you choose.

---

## 1. Run it from IDLE

1. Open `GXVAN.py` in IDLE.
2. Press **F5**.

On the first run, the bootstrap block installs any missing libraries with pip, using `python -m pip install --upgrade <pkg>` and retrying with `--user` if that fails. It then starts the app.

- If a **required** package still cannot be installed, the app prints the exact pip command below and stops gracefully. It does not use `sys.exit`, so IDLE stays alive.
- The launcher reuses an existing `QApplication`. All paths are resolved from the script folder, and unhandled UI errors show a friendly dialog and are logged to `logs/gxvan.log`.

### One-line manual install

The same line is available in the app under **Help → Manual install**, with a Copy button:

```bash
pip install PyQt6 pandas numpy openpyxl xlsxwriter PyMuPDF reportlab Pillow rapidfuzz python-dateutil qrcode rapidocr-onnxruntime
```

> **Python version and OCR.** RapidOCR depends on `onnxruntime`, which publishes wheels for **Python 3.10 to 3.13**. On a newer Python (for example 3.15) the OCR package cannot install. The app still runs and reads text PDFs at full accuracy, but scanned pages and photos cannot be read. GXVAN remembers the failed install, so it does not retry on every launch. **For full OCR, use Python 3.12 or 3.13.**

Nothing else is needed: no Tesseract, Poppler, Ghostscript, Java or MS Office. PyQt5 is used automatically if PyQt6 cannot be installed.

## 2. Folder layout

```
GXVAN/
  GXVAN.py            launcher + bootstrap (run this in IDLE)
  config.py           APP_NAME (change to "GXPVAN" here), colours, tolerances, statutory parameters, paths
  requirements.txt    same packages as the pip line (checked by tests/test_packaging.py)
  GXVAN.spec          PyInstaller build
  core/  gst_rules.py extraction.py ocr_engine.py pr_builder.py reconciliation.py pdf_tools.py
         excel_writer.py project_store.py
  ui/    qt.py theme.py widgets.py main_window.py dashboard.py pr_builder_page.py reco_page.py
         mapping_dialog.py pdf_pages/{base,tools}.py
  dummy_data/  dataset.py render.py generate_dummy_data.py answer_key.xlsx output/
  tests/       test_gstin.py test_extraction.py test_reco.py test_end_to_end.py test_pdf_tools.py
               test_packaging.py test_ui_smoke.py
  docs/screens/  screenshots of every page (python docs/make_screens.py --demo)
  logs/          gxvan.log
```

## 3. Workflow walkthrough

**Dashboard.** This page shows KPI tiles, quick-start actions and recent projects.
![Dashboard](docs/screens/home.png)

**PR Builder, step 1: Setup.**
- Enter the client profile: GSTINs (multi-GSTIN is supported), state, return period, FY and the e-invoice flag.
- Choose the PR. Columns are auto-mapped by fuzzy header matching. Confirm or correct them in the mapping dialog and save the result as a template for that client.
- Drop the document folder, then click **Extract & build review**. This runs in the background with a progress bar and a Cancel button.

Tip: **Load demo client** fills everything in from the dummy data.
![Setup](docs/screens/pr_setup_demo.png)

**PR Builder, step 2: Review.** The screen has three panes:
- **Left:** the queue, with colour chips, filters and search.
- **Centre:** the document viewer, with zoom, page navigation and highlighted field locations.
- **Right:** the PR value next to the document value, with differences highlighted and a Doc/PR choice for each field. Below that are the editable classification, the compliance checklist (✓ ✗ ?) with statutory references, and the exceptions list.

Keyboard: **A** approves, **F** flags (choose a reason, add free text) and **↑/↓** moves through records. Every change is written to the SQLite audit trail.
![Review](docs/screens/pr_review.png)

**PR Builder, step 3: Export.** The Finalised PR workbook contains these sheets:
- `Finalised_PR`: the exact GSTR-2B columns first, then the system and review columns, with a hyperlink to each document.
- `Exceptions`
- `Missing_Documents`
- `Unbooked_Documents`
- `Summary`: totals, the GSTR-3B Table 4 ITC summary and the Table 3.1(d) RCM liability.
- `Audit_Trail`
- `Parameters`

The project file (`.gxvan`, SQLite) is saved automatically. **Send to Reconciliation** passes the records straight to Module B.

**Reconciliation.**
1. Load the 2B for the period, plus the optional previous and next month 2B and the 2A.
2. Reconcile.
3. Filter by category, search, drill down to the document, match or unmatch manually, and add remarks.
4. Export the Excel report or the PDF summary.

The Excel report has these sheets: Dashboard with native charts, Reco_Detail, one sheet per category, Vendor_Summary, Vendor_Followup (email-ready), ITC_Claim_Working and Parameters.
![Reconciliation](docs/screens/reco_results.png)

**PDF tools.** Every tool uses the same card layout: a file list with Add, Remove, ▲/▼, Clear and drag-and-drop; options; the output name; Choose where to save; the action button; a status line; and an Open folder link.
![Merge](docs/screens/merge_pdfs.png)

**Dark theme.** Use View → Toggle dark theme (Ctrl+D), or Settings.
![Dark](docs/screens/dark_theme.png)

Sample outputs produced from the dummy data are in `dummy_data/output/sample_outputs/`.

## 4. Dummy / test data

Use **Sidebar → Dummy Data**, or run `python -m dummy_data.generate_dummy_data`. The generator creates this fictitious test set:

- **Client:** *Demo Offshore Services Pvt Ltd*, GSTIN `27ZZZCD0001A1Z1`, period Oct-2026. Every PAN starts with `ZZ`, so it is obviously fictitious, but every GSTIN is checksum-valid.
- **25 domestic documents:**
  - 5 layouts.
  - 12 text PDFs, 8 scanned-look PDFs and 5 JPG/PNG photos.
  - One PDF contains 2 invoices.
  - 3 e-invoices carry an IRN and QR code.
  - HSN is missing on 2 documents.
  - One document is a Sec 17(5) catering bill.
  - The set includes inter-state invoices, a CN, a DN and a wrong-IGST invoice.
- **10 foreign invoices** (AED, SGD, GBP, EUR, USD and NOK), plus 4 Bills of Entry.
- **Client PR** with **20 planted errors**.
- **GSTR-2B** for Oct (Excel and JSON) and for Nov, plus **GSTR-2A**.
- **`answer_key.xlsx`** with these sheets: Planted_Errors, Expected_Reco, and the hidden sheets Doc_Truth and Files.

## 5. Tests and results

```bash
python -m pytest tests -q
```

| Environment | Result |
|---|---|
| Python 3.12 (with RapidOCR) | **122 passed**, 6 skipped. The skipped tests are Module A-only errors that have no Module B check. |
| Python 3.15 (no onnxruntime wheel) | **98 passed**, 30 skipped (OCR-dependent tests). |

**Extraction accuracy** against the answer key is measured by `python -m tests.accuracy`. It compares 13 fields: doc type, both GSTINs, invoice number and date, taxable value, IGST/CGST/SGST, total, HSN, currency and IRN.

| Document kind | Fields correct | Accuracy | Target |
|---|---|---|---|
| Text PDFs | 277 / 277 | **100.0%** | ≥ 95% |
| Scanned PDFs and photos (RapidOCR) | 178 / 178 | **100.0%** | ≥ 85% |

> These figures are measured on the **synthetic** dummy documents that the regexes were tuned on. Real vendor invoices vary far more, so expect lower accuracy. Use the per-field confidence scores and the review screen.

**Planted errors.** All 20 are caught in Module A, and every one that applies to Module B (14) is caught there with the expected category. All 39 expected reconciliation categories match. This is asserted by `tests/test_end_to_end.py`.

## 6. Statutory parameters to verify before use

Every hard-coded statutory value carries a `# VERIFY against current law before release` comment in `config.py` or `core/gst_rules.py`. Most of them can be edited in **Settings**.

| Parameter | Default | Reference |
|---|---|---|
| ITC time limit (cut-off date, FY + 1) | 30 November | Sec 16(4) CGST Act |
| Payment to supplier within | 180 days | Sec 16(2) 2nd proviso, Rule 37 CGST Rules |
| Invoice number length | ≤ 16 characters | Rule 46(b) CGST Rules |
| E-invoice AATO threshold | ₹5 crore | Rule 48(4); Notfn 10/2023-CT |
| GSTR-3B due date (used for the 16(4) check) | 20th of the next month | Sec 39 / Rule 61 |
| Blocked credits keyword list | catering, food, motor vehicle, club, insurance, works contract, gifts … | Sec 17(5) CGST Act |
| RCM IGST rate on import of services | 18% (confirmable per record) | Sec 5(3) IGST Act; Notfn 10/2017-IT(R) |
| FX for valuation | user-maintained reference table | Rule 34 CGST Rules / CBIC notified rates |
| GST rate slabs | 0 to 40% list | Rate notifications (rationalised Sept 2025; the dummy data uses 12% and 28% only as the brief requested) |
| State codes | GST state code table | — |
| Dummy BoE duties (BCD 10%, SWS 10%, IGST 18%) | test values only | Customs Tariff |

The ITC logic is **advisory**. The tool flags and computes, and the reviewer decides. Every classification can be overridden, and every override is logged.

## 7. Known limitations

- **OCR needs Python 3.10 to 3.13**, because of the onnxruntime wheels. See §1.
- **Extraction is heuristic** (regex plus label proximity). It is tuned on 5 synthetic layouts. Unusual layouts, handwritten documents and multi-page line tables need manual review. Field highlighting is at line level.
- **QR decoding** of e-invoices only works when `opencv-python` happens to be installed; it is optional and not in the pip line. The IRN is still read from the printed text.
- **GSTN layouts change.** The 2A/2B parsers detect header rows and use `reco_column_map.json` aliases, and they ask you to confirm the mapping when headers are unknown. They were tested against the bundled portal-style dummy files, not live downloads.
- **Finalised PR vs raw PR.** Reconciling the *Finalised* PR uses the reviewer-accepted values, which default to the document values, so PR-only errors such as a wrong taxable value disappear. Reconcile the *client PR* to see the client's own booking errors.
- **Foreign-currency valuation** uses the PR FX rate and is checked against a user-maintained reference table. It does not use an official feed, because the app is offline.
- **Not used:** `pdfplumber` and `pypdf` from the original brief. PyMuPDF covers text-with-positions, merging, encryption and redaction, so they were left out to keep the dependency list (and the pip line) exactly matched to the imports.
- **PyQt5 fallback** is best-effort. The UI is developed and tested on PyQt6.

## 8. Make a desktop app (.exe on Windows, .app on Mac)

An exe has to be built **on the same kind of computer it will run on**: build on Windows for Windows and on a Mac for Mac. Use **Python 3.12 or 3.13** so OCR is included.

**Windows:** install Python 3.12 from python.org, then double-click **`build_windows.bat`**. It takes about 5–10 minutes. The result is `dist\GXVAN\GXVAN.exe`. Right-click it, choose **Send to → Desktop (create shortcut)**, and you have a desktop icon. To use GXVAN on another laptop, copy the whole `dist\GXVAN` folder (about 400 MB); that laptop does not need Python.

**Mac:** run `./build_mac.sh`. The result is `dist/GXVAN.app`. Drag it to Applications or the Dock. Because the app isn't signed, the first time you must right-click it and choose **Open**.

The build scripts swap `opencv-python` for `opencv-python-headless`. The normal OpenCV ships its own Qt libraries, which clash with PyQt6 and make the exe hang at start-up. In the packaged app, user data (settings, templates and logs) goes to `~/GXVAN_Data`. If a build ever hangs on start-up, run it with the environment variable `GXVAN_DEBUG=20` to print where it is stuck.
