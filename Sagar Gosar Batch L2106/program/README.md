# Agreement Compare 2.0

Offline tool that compares a **Word draft** (.docx) with the **executed copy** (scanned or text PDF, image, or .docx/.txt), highlights every
difference, classifies it (amount, date, percentage, period, legal-effect wording, clause added/deleted, names, blanks, OCR variance) with a
severity, and produces **Word and PDF reports** with the scan extract next to each difference. Everything runs on your computer.

## Start (Windows)
1. **Extract the whole zip** (right-click > Extract All). Do not run files from inside the zip.
2. Install **Python 3.10+** (tick "Add python.exe to PATH") and, for scanned PDFs, **Tesseract OCR** (https://github.com/UB-Mannheim/tesseract/wiki).
3. Double-click **`Run_Agreement_Compare_2026.bat`** (first start installs the libraries from `requirements.txt`).
   If it does not open, double-click `Diagnose_Agreement_Compare.bat` and send me `diagnose_log.txt`.

Other platforms: `pip install -r requirements.txt` then `python main.py`.

## Using it
1. **New comparison** – drop the Word draft and the executed PDF. For a scan, choose the pages to use (cover/stamp pages can be left out).
2. **Differences** – filter by severity, tick items as reviewed, see the highlighted scan next to each item. Rotate a page with the buttons above
   the scan if it was read upside-down (it is re-read and the comparison is refreshed).
3. **Redline** – whole agreement, deletions struck through, insertions underlined, probable OCR errors in amber.
4. **Align & edit** – manual control: merge/split/edit/ignore paragraphs, *Link* a draft paragraph with the executed paragraph(s), then
   *Re-compare with adjustments*. Sessions can be saved and loaded.
5. **Reports** – Word, PDF or both; CSV register for Excel.

## How it works (short)
* Pages with a text layer are read directly; scanned pages go through OCR: automatic upright detection (0/90/180/270), de-skew, removal of coloured
  ink (stamps/seals) while keeping black text, background flattening, ruling-line removal, then Tesseract.
* **Re-flow alignment** – the draft is the reference; unique word sequences anchor both documents, so paragraphs split wrongly by OCR, text crossing
  pages and stamp/registration text do not create false differences.
* Probable OCR misreadings (low confidence, not a word of the draft) are shown in the redline but not counted.

## Command line
`python main.py --cli samples/Draft_Agreement.docx samples/Executed_scan.pdf --out reports --export word,pdf`
(options: `--pages 2-4 --rotate 3:180 --upright --no-reflow --keep-stamps --redline --include-ocr --dpi 300 --lang eng`)

## Samples and tests
`samples/` holds a draft and three executed versions (text PDF, scan with a stamp across the text, scan with pages upside-down/sideways) with
ten seeded changes (`SEEDED_CHANGES.txt`). Regenerate with `python samples/make_samples.py`.
`python -m unittest discover -s tests -v` and `python main.py --selfcheck` verify the installation.

## Limits – please read
* OCR is never perfect: poor scans, handwriting and text hidden under opaque stamps cannot be read. Items marked *low OCR confidence* must be
  checked on the scan. Always verify against the signed original; this is a review aid, not legal advice.
* Tables are read paragraph by paragraph; two-column layouts are read top to bottom.
* Header/footer removal assumes running heads repeat on at least three pages.
