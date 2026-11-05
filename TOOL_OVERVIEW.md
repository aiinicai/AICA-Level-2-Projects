# Tool Overview

A short technical and functional summary for the reviewer.

## 1. Purpose

Before a bulk payment is released, every beneficiary line should be checked against approved vendor records. Vendor Name Matching automates that check and leaves an auditable result file.

## 2. How a payment file is checked

```
Payment file (.xlsx)                Unique Vendor Master (.xlsx)
        |                                      |
        |  clean account number + IFSC         |  same cleaning, build lookup
        v                                      v
   look up the key  ------------------>  names registered for that key
        |
        |  key not found                -> Not Matched: account and IFSC not in master
        |  key found, name differs      -> Not Matched: name differs, master name shown
        |  key found, name agrees       -> Matched
        v
 copy of payment file + Status + Remarks (green or red) saved with a time stamp
```

**Why bank details are searched first.** The risk worth catching is a correct vendor name paired with the wrong bank account. Searching by account and IFSC first, and then verifying the name, catches that case. Searching by name first would not.

### Cleaning rules

| Field | Rule |
|---|---|
| Account number, IFSC | Trimmed, upper case, only letters and digits kept |
| Vendor name | Upper case, punctuation removed, "&" read as "and", "Private" read as "Pvt", "Limited" read as "Ltd" |
| Account numbers in Excel | Read as text so leading zeros and long numbers are preserved |

### Result wording

| Remark | Meaning |
|---|---|
| Account, IFSC and name agree with master | Matched |
| Account number and IFSC not found in master | No vendor has this bank account |
| Name differs from master. Master name: ... | Bank account is known but belongs to a different vendor |
| Beneficiary account number / IFSC code / account name is blank | Required data missing |

## 3. Vendor master management

The master can be edited inside the tool, so users do not need to open Excel.

| Capability | Behaviour |
|---|---|
| Admin passkey | Needed to open the editor. Set on first use. Stored as a PBKDF2-SHA256 salted hash (200,000 rounds), never as text. Three wrong attempts lock the editor for 60 seconds |
| Add, edit, delete, search, paste | Direct editing in a table. Ctrl+V pastes rows copied from Excel |
| Duplicate prevention | The same account number and IFSC cannot appear twice, even with different spacing, case or vendor name. Duplicates are highlighted in red and Save Master is refused until they are fixed |
| Bulk upload | Columns are matched by header name, not position. Choose Add to Existing or Replace. Duplicates, name conflicts and incomplete rows are skipped and reported. Nothing changes until Save Master |
| Download | Exports the master (including unsaved edits) to a formatted Excel file |
| Backups | The previous master is copied to `Master_Backups` before every save. The latest 20 are kept |

## 3b. Print Verified PDF

The **Print Verified PDF** button produces a print copy of the payment file, but only when it is safe to release.

| Rule | Behaviour |
|---|---|
| Gate | Every line must be Matched. One Not Matched line blocks printing and no PDF is created |
| Re-verification | The original file and the current master are read again when the button is clicked, using the same rule as the main check, so a master change after the first check is respected |
| Content | All original columns and rows, exactly as uploaded. Only the table is printed: no heading, extra column or footer. A4 landscape (297 x 210 mm), column headings repeat on every page. A Total row sums the Amount column (a non numeric amount blocks printing, so a wrong total is never shown) |
| Safety | The original payment file is never changed. The PDF is saved as `<name>_Verified_<date_time>.pdf` in the working folder |

## 4. Design choices

| Choice | Reason |
|---|---|
| Single Python file | Easy to review, run from IDLE and share |
| PyQt5 | Professional desktop interface without a browser |
| openpyxl | Reads and writes Excel while preserving the original formatting |
| reportlab | Writes the verified PDF with the landscape page size fixed inside the file, so it is landscape on every computer. The page size is read back after writing and the PDF is rejected if it is not landscape |
| Auto install of libraries | A reviewer can run the file without separate setup |
| Output saved as a new file | The original payment file is never altered, and each run is a separate record |
| Working folder setting | `C:\Day 5` by default. The environment variable `VENDOR_MATCH_FOLDER` overrides it, which the demo and tests use |

## 5. Quality checks

- 43 automated tests, all passing (`python tests/test_vendor_name_matching.py`).
- Demo data with the correct answer written down for every row in `sample_data/EXPECTED_RESULTS.md`, checked independently of the tool.
- The tests work only in a temporary folder and stop with a safety message if the tool points anywhere else, so a real working folder is never touched.

## 6. Limitations and possible next steps

| Limitation | Possible improvement |
|---|---|
| .xlsx only, first sheet, headers in row 1 | Support CSV and a header row selector |
| Strict name matching | Optional fuzzy suggestions shown as "Review", never as "Matched" |
| Passkey protects the editor only | Excel file permissions, or a shared database with user roles |
| Passkey lockout resets when the tool restarts | Persist the lockout state |
| Single master | Multiple masters, one per entity or company |
