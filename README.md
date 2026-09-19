# Trial Balance Review & Audit Exception Analyzer
## Tkinter desktop edition — small ICAI capstone project

This version replaces Streamlit with **Tkinter**. It opens a desktop window; there is no browser, web server or login. Application logic and interface remain in one file, `app.py`. This is an educational demonstration, not an ICAI-issued or certified product.

**Exceptions are indicators requiring professional review, not conclusions of accounting error or fraud.**

## Problem Statement

Manual initial review of a Trial Balance can make repeated names, unusual signs and significant balances difficult to identify consistently. A small desktop tool can apply transparent screening rules and generate a review workbook for the audit team.

## Objective

Open a standardized Excel Trial Balance, validate the input, calculate a summary, identify seven types of review exceptions, filter them and save an Excel report. Keep the application suitable for a 5–10 minute demonstration.

## Features

- Open `.xlsx` using a native file-selection dialog; validate all six required columns.
- Save Sample Excel Format: a fictional 24-ledger workbook covering every requested exception.
- Dashboard: Total Ledgers, Total Exceptions, High-Value Items, Negative Balances and Unusual Balances.
- Summary: period debit/credit totals, signed difference and largest-magnitude closing balance, displayed with its sign.
- Seven exception checks, with configurable materiality/review threshold, round-figure multiple and group-level expected nature.
- Tabs for exceptions and uploaded Trial Balance; horizontal/vertical scrollbars; double-click for full remarks.
- Dropdown filters by Exception Type and Ledger Group; select one value per filter or All.
- Download Audit Exception Report opens a native **Save As** dialog; no browser download is involved.
- Export includes the filtered report, full report, summary, settings and applied accounting rules.
- Changing settings disables export until Analyze / Refresh is clicked, to avoid saving a stale report with new settings.

## Technology Used

Python + Tkinter/ttk + Pandas + OpenPyXL, plus Python standard-library utilities. No external API, AI service, database, scraping, OCR, login system or ML.

Tkinter requires a Python installation with Tcl/Tk support. The standard Windows Python installer can include it; it is not installed using `pip install tkinter`. The requirements file contains only Pandas and OpenPyXL. The optional EXE build recipe uses PyInstaller as an additional build-only tool; it is not required to run the source application.

## Project Structure

```text
trial_balance_analyzer_tkinter/
    app.py
    requirements.txt
    sample_trial_balance.xlsx
    README.md
    run_windows.bat
    build_exe_windows.bat
    test_cases.py
    test_cases.csv
    test_results.csv
    test_results.xlsx
    TEST_RESULTS.md
    sample_audit_exception_report.xlsx
    testing_data/
        valid_24_ledgers.xlsx
        missing_credit_column.xlsx
        empty_workbook.xlsx
        headers_only.xlsx
        zero_byte.xlsx
        invalid_numeric.xlsx
        blank_closing_balance.xlsx
```

The test runner is not an application module. There are no separate business-logic modules or web configuration files.

## Installation — Windows laptop

1. Install Python 3.11 or 3.12 with **Tcl/Tk support**. Enable PATH integration in the installer, if offered.
2. Extract this ZIP to a normal folder. Do not run files from inside the ZIP.
3. Open the folder containing `app.py` and `requirements.txt`.
4. Click the File Explorer address bar, type `cmd`, and press Enter.
5. Run these commands one at a time:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Internet is needed for initial package installation; the application itself makes no network requests.

Verify Tkinter installation, if needed:

```bat
python -m tkinter
```

This should open a small Tk demonstration window. Close that window before continuing. If it fails, repair/reinstall Python with Tcl/Tk support rather than trying to install Tkinter with pip.

## How to Run

With the virtual environment activated:

```bat
python app.py
```

Or double-click `run_windows.bat` after the first-time setup. The launcher uses the project's `.venv` if present. **Do not use the previous `streamlit run app.py` command for this version.**

Close the desktop window to stop the application. No local browser address or server port is used. After setup, the source version runs offline.

macOS/Linux: use a Python installation with Tk support, create a virtual environment, activate with `source .venv/bin/activate`, install requirements and use `python app.py`. Linux may require your distribution's separate Tk package and a working graphical desktop session. Windows EXE packaging is not used for macOS/Linux.

### Use the application

1. Click **Save Sample Excel Format** and choose a folder, or use the supplied sample workbook.
2. Click **Open Trial Balance (.xlsx)** and select the sample. Analysis runs automatically.
3. Review the dashboard and summary. The exceptions table contains one row per flag.
4. Change the threshold or round multiple, then click **Analyze / Refresh**. Enter plain numbers such as `500000`, not comma-formatted text.
5. To change accounting rules: click **Expected Nature Rules**, select a group row, select Debit/Credit/Ignore, click **Set Nature**, then **Apply Rules**. Equivalent group spellings are kept consistent. Cancel discards changes.
6. Choose a type/group filter. Filters combine with AND; All means no restriction. Each new analysis resets filters to All.
7. Double-click an exception to read its complete remarks.
8. Click **Download Audit Exception Report**, choose a destination and save. This is a normal desktop Save As dialog.

On opening a different workbook, group rules reset to defaults for that workbook. If a new file is invalid, the prior valid data remains open and the error message states that explicitly.

### Input Format

Use the first worksheet, headers in row 1, with these exact names (column order may vary):

| Ledger Name | Group | Opening Balance | Debit | Credit | Closing Balance |
| --- | --- | ---: | ---: | ---: | ---: |
| Cash in Hand | Cash | 10000 | 40000 | 60000 | -10000 |

- Positive opening/closing = debit; negative = credit. Debit and Credit are non-negative **period movement totals**, not closing Dr/Cr columns.
- Use value-only cells, not formulas. Paste values before opening the file. Formulas in required columns are rejected.
- Numeric amounts may have up to two decimal places. Explicit `0` is required for zero amounts; blanks/NaN are not silently replaced with zero.
- Excel numeric currency formatting is fine; text such as `₹5,00,000`, `(1000)`, `100 Dr` is rejected. Plain numeric text such as `500000.00` is accepted.
- Missing headers, duplicate required headers, missing names/groups, invalid numbers, negative period debit/credit and non-finite values produce validation errors.
- Extra columns are ignored. Fully blank rows in the required columns are skipped. Header names are case-sensitive after trimming outer spaces.
- Remove total/subtotal rows, merged headings and decorative rows; they are not automatically identified.
- Only the first worksheet is read. At least one complete ledger row is required. File size limit: 10 MB. Individual amount limit: +/- INR 1,000,000,000,000.

### Exception Logic and Accounting Interpretation

| Check | Rule |
| --- | --- |
| Trial Balance Difference Identified | Total period Debit minus Credit is nonzero. One TB-level report row, group `[Overall TB]`, blank Closing Balance. |
| Negative Balance | Closing Balance < 0. This includes normal credit balances. |
| Duplicate Ledger Name | Repeated names after ignoring case and repeated/outer whitespace. Every occurrence is flagged. |
| High Value | Absolute closing balance strictly greater than the selected threshold (default 500000). Equality is excluded. |
| Round Figure Transaction – Review Required | Nonzero period Debit or Credit is an exact multiple of the configured amount (default 10000). One report row per ledger even if both sides qualify. |
| Zero Closing Balance | Closing is zero but Debit or Credit has movement. Dormant zero ledgers are excluded. |
| Unusual Balance – Review Required | Closing sign conflicts with the group's configured expected Debit/Credit nature. Zero is neutral. Ignore disables the group rule. |

Integer paise are used for comparisons, totals and multiples to avoid ordinary floating-point equality issues.

Default debit groups: Cash, Bank, Cash/Bank, Expense(s), Asset(s), Receivables. Default credit groups: Income, Sales, Liability/Liabilities, Equity, Payables. Matching normalizes case/whitespace but uses the entire group name. Unmapped groups default to Ignore. Customize overdrafts, contra accounts and other special classifications before interpreting results.

Important scope points:

- The input contains **ledger period totals**, not individual transactions. The requested round-figure label is retained, but individual voucher amounts cannot be established from the TB.
- Negative is not synonymous with unusual or incorrect; income, capital and liabilities often have credit-signed balances under the stated convention.
- The review threshold is not a full audit materiality determination.
- No opening-to-closing roll-forward reconciliation or separate closing-TB balance check is performed. Agreement of period Debit/Credit alone does not prove a correct TB.
- Highest Closing Balance means largest absolute value, displayed with its original sign; first source row wins a tie.
- Total Exceptions counts flags, not unique ledgers. Dashboard counts remain unfiltered; a ledger may contribute several flags.
- Remarks reference ledger-row numbers after blank rows are removed. Validation messages use actual Excel row numbers.

### Export Workbook

- **Exceptions**: five requested columns; current filtered rows.
- **All Exceptions**: complete unfiltered report.
- **Summary**: unfiltered metrics.
- **Settings**: source filename, thresholds, filters, sign convention and disclaimer.
- **Expected Nature**: applied group rules.

Empty reports still export with column headers. Formula-like text in exported ledger names remains literal text, not executable Excel formulas. The overall mismatch can be excluded by a group filter; clear filters to see it again.

## Testing

Run from the project folder:

```bat
python test_cases.py
```

The runner generates the fixtures, sample workbook, sample export, CSV test cases and Excel/CSV/Markdown results. It rewrites those generated files, not client workbooks. Tests 1–10 correspond to the original requested scenarios. Additional tests cover precision, strict threshold boundaries, formulas, filters, zero movement, empty reports, invalid settings and desktop controller safeguards.

**Delivered result: 37/37 core/controller tests PASS.**

- Tests 1–33 exercise actual Excel bytes, calculations, exports and syntax.
- Tests 34–37 use mocked dialogs/widgets to exercise stale-export prevention, invalid replacement files, save cancellation and simulated save errors. They are not live GUI tests.
- Environment: Linux; Python/Pandas/OpenPyXL versions are recorded in the Test Scope worksheet.
- **Live GUI NOT RUN:** the preparation environment lacks `libtk8.6.so`, so Tkinter cannot be imported successfully there. Rendered controls, actual native dialogs, clicks and window behavior need local verification.
- **Windows EXE NOT BUILT / NOT RUN.** No compiled executable is supplied.

`test_results.xlsx` contains the requested columns: Test No.; Test Scenario; Expected Result; Actual Result; Status – PASS/FAIL. The Test Scope worksheet prevents interpreting core PASS results as GUI or executable validation.

### Expected sample metrics at defaults

| Metric | Value |
| --- | ---: |
| Ledgers | 24 |
| Total Debit | 2,449,084.00 |
| Total Credit | 1,553,074.00 |
| Difference (Debit minus Credit) | +896,010.00 |
| Highest Closing Balance (largest magnitude, signed) | -900,000.00 |
| Total Exceptions | 27 |
| High-Value Items | 4 |
| Negative Balances | 7 |
| Unusual Balances | 4 |

Flags by type: mismatch 1, negative 7, duplicate 2, high value 4, round figure 8, zero closing 1, unusual 4.

### Required local desktop smoke test — NOT RUN here

1. Start with `python app.py`; verify the window fits your display and all buttons/tabs/scrollbars work.
2. Save the sample, reopen it and compare all metrics above.
3. Open missing-column, empty, zero-byte and invalid-numeric fixtures; verify clear error messages and no crash.
4. Change materiality to 750000; confirm export is disabled until refresh, then Plant and Machinery is not flagged High Value.
5. Restore 500000; change round multiple to 5000 and inspect results.
6. Set Expenses to Ignore; verify Travel Expense is no longer unusual. Restore Debit.
7. Filter High Value / Assets; only Plant and Machinery should appear. Clear Filters restores all rows.
8. Save the filtered report, open it in Excel and verify all five sheets and their scope.
9. Cancel file dialogs; try saving to an unavailable/locked destination; verify the app remains usable.
10. Open a second workbook and check rule/filter reset. Close the app normally. Repeat on the packaged EXE if you build it.

## Optional Windows EXE Build

**No `.exe` is included in this delivery.** Use the Python source first. A batch launcher is not an executable substitute.

The included `build_exe_windows.bat` is an **unverified build recipe**. On Windows with Python/Tcl/Tk and internet access, run:

```bat
build_exe_windows.bat
```

It creates a separate `.build_venv`, installs the application requirements and PyInstaller, then attempts a one-file windowed build. Intended result:

```text
dist\TrialBalanceAnalyzer.exe
```

PyInstaller is an additional build tool, not an application requirement. Its official documentation states it is not a cross-compiler: build Windows apps on Windows. Test the resulting executable on the intended laptop before presentation. Packaging can require version-specific hooks; no success is guaranteed by supplying a script. If debugging a packaged crash, rebuild with `--console` instead of `--windowed` to see diagnostic output. Follow your organization's policy for unsigned applications; do not bypass security controls.

If build-only tools are prohibited by the project rules, skip EXE packaging and run `python app.py` or `run_windows.bat`.

## Limitations

- Initial screening aid only; not an audit opinion, compliance engine, substitute for audit evidence, or proof of error/fraud.
- Simple group-level rules can produce false positives/negatives; professional judgment is essential.
- No voucher-level analysis, roll-forward reconciliation, multi-period comparison or independent validation of account classification.
- First worksheet, standardized signed balances and two-decimal INR amounts only.
- No persistence, review history, database, authentication or production security hardening. Store client files according to firm policy; demonstrate with dummy data.
- Designed for small workbooks; synchronous processing may make the window temporarily unresponsive for large files. Avoid huge/formatted-only worksheets.
- The source is small; a bundled executable includes Python and libraries and can be much larger.
- Live GUI and executable testing must be completed locally. Dependency ranges are not a frozen lockfile; record the versions used after your local smoke test.

## Future Scope

Possible future enhancements, not implemented: closing-balance roll-forward checks, separate Dr/Cr input mapping, ledger codes for duplicate detection, voucher-level round-figure review, prior-year comparison and reviewer notes. Keep these outside the current capstone scope.

## 5–10 Minute Demonstration

1. Explain scope and professional-review disclaimer (1 minute).
2. Open the sample and show the dashboard/mismatch (1 minute).
3. Show examples: negative Cash, duplicate Office Supplies, 750000 Plant and Machinery, unusual Travel Expense, and Clearing Account's zero closing balance with movement (2 minutes).
4. Adjust threshold and expected nature (1 minute).
5. Filter and export; show the Excel sheets (1–2 minutes).
6. Show missing-column/empty-file handling and test results (1–2 minutes).

## Technical documentation consulted

Official Python documentation: “tkinter — Python interface to Tcl/Tk” and “Tkinter dialogs”. Official PyInstaller Manual: platform/build requirements. No third-party service is called by the application.
