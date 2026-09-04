# DISCOM Audit Data Compiler — Python Backend + Desktop GUI

**Schema-free by design.** This tool does not assume any fixed set of columns (no
hard-coded "billedAmount", "consumerNo", etc.). It reads whatever columns each
Excel file actually has and compiles them as-is. This matters because real audit
data comes in different shapes — billing extracts, unbilled-consumer reports,
collection registers, meter-status reports — each with genuinely different columns,
and none of them should be forced into a billing-shaped mold.

## Core design rules

1. **Header row detection only checks row 1 or row 2** of each sheet — never deeper.
   Detection is purely structural (non-blank cell count, text-vs-numeric ratio),
   with no vocabulary of "expected" column names. If a file's real header is on
   row 3+, the user must set the header row manually via the spinner in Screen 1.
2. **No required fields, ever.** A file with no "amount collected" column (e.g. an
   unbilled-consumers report) compiles cleanly — that column simply doesn't exist
   for those rows. Nothing is rejected for "missing" a column the tool assumed it
   should have.
3. **Columns are aligned across files by EXACT name match only** (after trimming
   whitespace) — no fuzzy matching, no alias list. If two files use different
   names for what is conceptually the same field (e.g. `SC_NO` vs `CA_NUMBER`),
   they remain two separate columns in the compiled output. This is deliberate —
   the user explicitly chose this over fuzzy matching for predictability.
4. **Rows are only dropped if they are completely blank.** Otherwise every row
   from a source file survives into the compiled dataset. Individual cells that
   fail to parse as numbers in an otherwise-numeric column are kept as-is and
   logged as a warning, not silently zeroed or used to reject the row.
5. **Summaries and filters are fully dynamic.** The GUI's Summaries and Query
   Builder screens auto-detect numeric vs categorical columns from whatever the
   compiled data actually contains, and populate their dropdowns from that —
   there is no fixed list of "division" / "tariff category" fields anywhere.

## Config constants

`config/schema.py` contains only generic period-selector constants (month/year
lists for filenames) — deliberately no field schema, since the tool works on
whatever columns each file actually has.

## Modules -> Screens

| Module | Screen | What it does |
|---|---|---|
| `core/header_detect.py` | Screen 1 | Checks only row 1 vs row 2 of a sheet (non-blank cell density, text-vs-numeric ratio) and picks the more likely header row. No column-name vocabulary — purely structural. |
| `core/ingestion.py` | Screen 1 | `compile_divisions()` is the main entry point: reads each file (via `python-calamine`), applies the header row, keeps every column exactly as named (no schema, no required fields), coerces columns that are mostly numeric-looking, and concatenates files by exact column-name match. Returns a compiled DataFrame + structured load log (rows read, columns detected, warnings — never hard rejections for a "missing" column). |
| `core/export_engine.py` | Screen 2 | `export_as_excel_table()` writes a proper Excel **Table** object (via `xlsxwriter`) ready for one-click *Get Data → From Table/Range → Add to Data Model*. `export_as_csv()` is the faster alternative, also Data-Model-ready via *Get Data → From Text/CSV*. Per Option A, no pivot table is built here — that happens in Excel itself. |
| `core/summaries.py` | Screen 3 | Fully dynamic: `classify_columns()` inspects the compiled DataFrame's actual dtypes to find numeric vs categorical columns; `group_summary()` and `cross_tab_matrix()` take caller-chosen column names, not fixed fields. |
| `core/query_engine.py` | Screen 4 | Vectorized filter evaluation (boolean masks over whole columns) operating on whatever column names exist in the compiled data. |

## Performance notes (tested on 80,000 rows / 16 files, extrapolated to 24,00,000 rows/month)

- **Compile**: ~2.8s for 80K rows → **~1.4 min** at full scale (`python-calamine` read engine)
- **Excel Table export**: ~10.3s for 80K rows → **~5.2 min** at full scale (`xlsxwriter`; this is the largest remaining cost — inherent to writing 24 lakh rows × 22 columns as Excel XML)
- **CSV export**: ~0.8s for 80K rows → **~23s** at full scale — recommend this as the default export choice when the user doesn't specifically need a `.xlsx` Table
- **Summaries + filters**: negligible (<0.1s even at 80K rows, since these are fully vectorized)

## Design history: why this became schema-free

An earlier version of this tool assumed a fixed billing/collection schema
(`billedAmount`, `amountCollected`, etc. as "required fields") with fuzzy
column-name matching against a predefined alias list. That version rejected
100% of a real "Unbilled consumers" report — 559,481 rows — because the file
legitimately has no `amountCollected` column (nothing has been billed or
collected yet). Real audit data comes in many shapes (billing extracts,
unbilled reports, collection registers, meter-status reports) and forcing all
of them into one assumed shape was the wrong design. The tool was rebuilt
schema-free: no predefined fields, no fuzzy matching, no required-field
rejection — see the "Core design rules" section at the top of this file.

## Running the tests

```bash
pip install -r requirements.txt
python3 tests/make_sample_files.py   # generates 4 realistic messy sample division files
python3 tests/test_pipeline.py       # runs all 4 modules end-to-end and prints results
```

## Desktop GUI (PyQt6) — new since the backend-only version

A native desktop application (`gui/` folder + `main.py`) has been built on top of the
backend, styled to match the AI Studio-generated React UI's 4-screen layout (dark
sidebar, professional data-dense tables). This is **not** the React code — it's a
Python/PyQt6 recreation with the same screens, wired to the real backend modules
above (not mock data).

### Running on Windows — first time

1. Extract this project folder anywhere, e.g. `D:\DISCOM Project\discom_audit_tool\`
2. Double-click **`setup_first_time.bat`** — creates a virtual environment and installs
   everything needed, including PyQt6 and PyInstaller. Run this once.
3. To just try the app without building an exe: double-click **`run_app.bat`**
4. To build the standalone `.exe`: double-click **`build_exe.bat`**
   - Produces `dist\DISCOM_Audit_Compiler.exe` — a single ~100MB file
   - This file runs on **any** Windows machine, even one with no Python installed
   - Share `dist\DISCOM_Audit_Compiler.exe` (optionally alongside
     `Launch_DISCOM_Audit_Compiler.bat`) with teammates — they just need that one file

### What each .bat does

| File | Purpose |
|---|---|
| `setup_first_time.bat` | One-time setup: creates `venv`, installs `requirements.txt` + PyQt6 + PyInstaller |
| `run_app.bat` | Runs the app directly via Python (`python main.py`) — fastest way to test changes |
| `build_exe.bat` | Runs PyInstaller using `DISCOM_Audit_Compiler.spec`, outputs `dist\DISCOM_Audit_Compiler.exe` |
| `Launch_DISCOM_Audit_Compiler.bat` | For teammates who only have the `.exe` — a friendly double-click launcher with an error message if the exe is missing |

### GUI module map

| File | Screen |
|---|---|
| `gui/main_window.py` | Top-level window: sidebar + status bar + the 4 screens in a QStackedWidget |
| `gui/sidebar.py` | Left navigation; locks Screens 2-4 until Screen 1 compiles successfully |
| `gui/status_bar.py` | Bottom bar showing period / divisions compiled / row count / timestamp |
| `gui/screen_compile.py` | Screen 1: file upload, header-row override (row 1 or 2 only), Compile All, live load log with per-column detail |
| `gui/screen_export.py` | Screen 2: Excel Table / CSV format choice, filename, folder picker, live preview, Export Now |
| `gui/screen_summaries.py` | Screen 3: dynamic Group Summary / Cross-tab Matrix / Overall Totals — all built from dropdowns populated by the compiled data's actual columns |
| `gui/screen_query.py` | Screen 4: filter builder (field dropdown from actual columns), live results, export filtered list |
| `gui/settings_dialog.py` | Settings modal: firm name, DISCOM name, default ED rate, default DPS rate |
| `gui/app_state.py` | Shared state object every screen reads/writes (billing period, compiled DataFrame, load logs, settings) |
| `gui/styles.py` | Shared PyQt stylesheet matching the AI Studio dark/professional theme |

### Known limitations of the current GUI build

- Settings (firm name, ED rate, DPS rate) are **not persisted** between app runs yet — they reset to defaults each time you open the app. Wiring this to a small JSON config file saved next to the exe is a natural next step.
- Saved filter combinations aren't persisted between sessions yet — every filter is built fresh each time the app opens.
- The Query Builder's live preview caps at 500 rows for responsiveness; the **export** always uses the full filtered set regardless of preview size.
- No drag-and-drop onto the file drop zone yet — "Add Files" opens a standard file picker dialog instead. Functionally equivalent, just not drag-and-drop.
- Multi-sheet source files: `ingest_single_file()` currently reads only `sheet_name=0` (first sheet) — fine if files are single-sheet, but flag if any file has data split across multiple sheets.
