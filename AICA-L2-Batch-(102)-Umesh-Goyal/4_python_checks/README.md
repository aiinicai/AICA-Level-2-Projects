# 4. Python checks

Short scripts written to learn and to check an SCN without sending it anywhere. Standard Python plus three libraries.

```
py -m pip install pypdf pymupdf pytesseract pillow
```

| Script | Job | Input |
|--------|-----|-------|
| `check_scn.py` | **The main script.** Reads the JSON made in AI Studio and (A) works out the section 73 / 74 / 74A windows for every financial year and the reply date, (B) re-does the arithmetic of the year-wise table: quantity x rate, tax on value against the rate named in the notice, the implied rate compared across the years, column sums against the printed Total row, issue amounts against the column sums, (C) confirms that every figure of the JSON is actually present in the notice text. Saves `check_result_<scn no>.txt` | `scn_output.json` in this folder (IDLE, F5, nothing to type). Optional: the notice PDF or `_ocr.txt` placed in the folder |
| `json_to_cases_csv.py` | Adds the reply due date and the hearing date from the same JSON to `cases.csv` (columns client, matter, last_date, status), the file a daily reminder workflow can read | JSON file and CSV path |
| `ocr_scanned_pdf.py` | Only for a scanned notice: PDF to OCR text (`_ocr.txt`) and header fields. Needs the Tesseract program (Windows default `C:\Program Files\Tesseract-OCR\tesseract.exe`) | PDF path |
| `extract_header.py` | Cross-check without AI: header fields read straight from a PDF with a text layer | PDF path, or none for a file chooser |
| `scn_common.py` | Shared helpers: GSTR-9 due-date table, date and number handling, the checks | - |

Run from this folder, for example `py check_scn.py`. Expected results are in `../5_samples/expected_output`.
`../5_samples/scn_output_example.json` is a hand-made stand-in for the AI Studio output of the fictional SCN; use your
own AI Studio output for a real run.

## What was learned while building them

* **The first regex hit is often wrong.** A notice mentions several sections, dates and years. The scripts keep every
  candidate and pick the section by counting; the SCN date may appear only in the digital-signature stamp.
* **A table can reach the script in two shapes.** OCR gives one line per row; `pypdf` gives one cell per line. The
  table parser handles both. With Tesseract's default layout a table came out column by column; `--psm 4` keeps the
  rows together.
* **OCR cannot be trusted for identifiers.** The sample GSTIN came out with letters in place of zeros and an
  extra character. The script shows the raw text under "verify" and does not invent a value.
* **Arithmetic catches what the eye misses.** A dropped or misread digit shows up as a MISMATCH or NOT FOUND.

## What `check_scn.py` can and cannot do

* It works on the JSON keys of the system instruction. The table check knows the columns `quantity`, `rate`, `value`,
  `tax_forward_charge`, `royalty_paid`, `tax_rcm`; any numeric column is also added and compared with the Total row.
* The rate used for the "expected tax" comes from the percentage written in `issue_1_description` /
  `issue_2_description`. Where none is written, the script shows only the implied rate and compares the years with each other.
* A notice whose demand is not a year-wise table (for example an ITC mismatch computed invoice by invoice) is not
  recomputed; the limitation part and the figure-found-in-the-notice part still work.
* "All figures found in the notice" proves the AI copied a number that exists; it does not prove it sits against the right
  year. The arithmetic and your own reading of the notice cover that.
* A BARRED line is counted as a problem only for the section the notice invokes.
Limitation dates use the standard GSTR-9 due dates; verify extensions under section 168A before relying on any date.
