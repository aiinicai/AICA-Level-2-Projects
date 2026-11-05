# Vendor Name Matching

A desktop tool that checks the bank details in a payment file against an approved vendor master before the payment is released. It answers one question for every payment line: **does this account number and IFSC code really belong to the vendor named on the payment?**

Built by **Ritesh Dedhia**, Chartered Accountant, as a capstone project for the AICA Level 2 programme.

![Main window showing results](docs/images/main_window_results.png)

## The problem

Payment files prepared for RTGS or NEFT are checked by eye against vendor records. This is slow, and it misses the most dangerous error: a payment where the bank account is valid but belongs to a different party. Typical causes are a typing mistake, a changed bank account that was never verified, or a fraudulent instruction.

## What the tool does

1. Loads a payment file (.xlsx) chosen by the user.
2. Looks up each row in the **Unique Vendor Master** using **Beneficiary Account Number + IFSC Code**.
3. Confirms that the **Beneficiary Account Name** agrees with the vendor registered against that account.
4. Writes **Status** (`Matched` or `Not Matched`) and **Remarks** (the reason) into a copy of the payment file, shaded green or red.
5. Never changes the original file. Every run saves a new time stamped file.
6. **Print Verified PDF:** creates a PDF of the payment file with all its original columns on landscape pages, but only if every line is Matched. If any line is Not Matched, printing is refused.

## Features

| Area | Feature |
|---|---|
| Matching | Bank details are searched first, then the name is verified, so a valid account under the wrong name is caught |
| Matching | Tolerates spacing, hyphens, upper or lower case, "&" and "and", "Private Limited" and "Pvt Ltd" |
| Matching | Account numbers are read as text, so leading zeros are never lost |
| Results | Summary cards, colour coded table and a reason for every failure |
| Printing | **Print Verified PDF** is allowed only when every line is Matched, re-checks the master at click time and includes all original columns |
| Vendor master | Edit inside the tool: add, change, delete, search, paste from Excel |
| Vendor master | **Bulk upload** from Excel (add to existing, or replace) and **download** to Excel |
| Vendor master | **Duplicate entries are not allowed**: the same account and IFSC cannot be saved twice |
| Security | Editing the master needs an **admin passkey** (stored only as a salted hash) with lockout after three wrong attempts |
| Safety | Automatic backup of the master before every save |
| Setup | Installs its own libraries on first run, no manual setup needed |

Printing is allowed only for a fully matched file. This is the PDF made from `Payment_Demo_AllMatched.xlsx`:

![Verified PDF page](docs/images/verified_pdf_page.png)

![Vendor master editor with a duplicate flagged](docs/images/master_editor_duplicate.png)

## Quick start

**Requirements:** Python 3.8 or newer (IDLE is enough) and an internet connection for the first run only.

### Option 1: run the guided demo (recommended for review)

```
python prepare_demo.py --launch
```

This creates a separate `demo_workspace` folder, copies in the fictional demo data and opens the tool on it. Your real working folder is not touched. When the editor asks for a passkey for the first time, you can use `Demo@1234`.

### Option 2: run the tool directly

Open `Vendor_Name_Matching.py` in IDLE and press **F5**, or run:

```
python Vendor_Name_Matching.py
```

By default the tool uses the folder `C:\Day 5` on Windows (and `~/Day 5` on other systems) for the vendor master and the output files. To use another folder, set the environment variable `VENDOR_MATCH_FOLDER` before starting.

### If a library is missing

The tool installs PyQt5, openpyxl and reportlab by itself. If that fails, run this single line:

```
pip install PyQt5 openpyxl reportlab
```

## Demo and test data

All data is **fictional**. See [`sample_data/EXPECTED_RESULTS.md`](sample_data/EXPECTED_RESULTS.md) for the correct answer to every row.

| File | Expected result |
|---|---|
| `Payment_Demo_Mixed.xlsx` | 12 rows: 5 Matched, 7 Not Matched (covers every scenario) |
| `Payment_Demo_AllMatched.xlsx` | 5 rows: 5 Matched |
| `Payment_Demo_NewVendors.xlsx` | 3 Not Matched before the bulk upload, 3 Matched after it |
| `Sample_Verified_Output.pdf` | What the Print Verified PDF button produces for `Payment_Demo_AllMatched.xlsx` |
| `Bulk_Upload_Demo.xlsx` | 3 added, 2 duplicates, 1 name conflict and 1 incomplete row skipped |

## Automated tests

43 tests cover the cleaning rules, header handling, matching, backups, passkey, duplicate prevention, bulk upload, download, the editor window and the Print Verified PDF rules. They run without a screen and work only inside a temporary folder. A built-in safety check stops them if the tool ever points anywhere else, so real vendor masters, passkeys and backups (for example in `C:\Day 5`) are never touched.

```
python tests/test_vendor_name_matching.py
```

In IDLE, open the test file and press **F5**. The test file finds the tool automatically, whether it is saved in the `tests` folder or next to `Vendor_Name_Matching.py`, and it builds the demo data itself if the `sample_data` folder is missing.

## Project structure

```
Ritesh-Dedhia-Vendor-Name-Matching/
  README.md                       this file
  Vendor_Name_Matching.py         the application (single file)
  requirements.txt                libraries (PyQt5, openpyxl)
  prepare_demo.py                 builds a clean demo folder, optional launch
  sample_data/                    fictional master, payment files, bulk upload file, expected results
  tests/                          automated test suite
  docs/
    TOOL_OVERVIEW.md              how the tool works (for the reviewer)
    USER_GUIDE.md                 step by step usage
    DEMO_SCRIPT.md                timed script for presenting and recording the demo
    Capstone_Presentation.pptx    5 slide presentation
    images/                       screenshots
```

## Documentation

- [Tool overview](docs/TOOL_OVERVIEW.md)
- [User guide](docs/USER_GUIDE.md)
- [Demo script](docs/DEMO_SCRIPT.md)
- [Presentation](docs/Capstone_Presentation.pptx)

## Limitations

- Excel `.xlsx` files only, with headers in row 1 and data from row 2. Only the first sheet is read.
- Name matching is strict after normalisation. A near match such as "Sharma Traders" and "Sharma Trading Co" is deliberately reported as Not Matched, because payments should not pass on a guess.
- The admin passkey protects the editor inside the tool. It does not encrypt the Excel file, so folder permissions should also restrict who can change the master file.
- The tool supports one vendor master at a time.

## Author

Ritesh Dedhia, Chartered Accountant. Capstone project for AICA Level 2.
