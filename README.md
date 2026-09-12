# HSNexus – GST Invoice Extractor

*Developed by Jayanth V Bhat*

Scans a folder of invoice PDFs (including all sub-folders), extracts HSN/SAC
line items, and exports the results to Excel.

## Run it

Double-click **`Run App.bat`**.

That's it — the first time, it creates the Python environment and installs
everything it needs (takes a minute or two); every time after that, it just
starts the app straight away and opens your browser to it automatically.
Leave that window open while you use the app; closing it (or pressing Ctrl+C
in it) stops the server.

Enter the full path to the folder containing your invoices (e.g.
`C:\Invoices\2026`) and click **Scan Folder** — the app walks that folder and
every sub-folder for `.pdf` files. Results are shown in a preview table and
also saved as an `.xlsx` file in the `output/` folder; click **Download
Excel** to save it.

### OCR for scanned invoices

Some invoices are scans/photos saved as PDF, with no selectable text. Reading
those requires the **Tesseract OCR** engine (a separate program, not a pip
package) — download and run the Windows installer from
[UB Mannheim's Tesseract builds](https://github.com/UB-Mannheim/tesseract/wiki)
and keep the default install path. `Run App.bat` finds it there automatically;
no other setup needed. If you installed it somewhere else, set an environment
variable before launching:
```powershell
$env:TESSERACT_CMD = "C:\path\to\tesseract.exe"
```
Without Tesseract installed, scanned invoices are still processed but flagged
with "Tesseract OCR is not installed" in **Extraction Notes** instead of
crashing.

<details>
<summary>Running it manually instead (without the .bat file)</summary>

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```
Then open http://127.0.0.1:5000 in a browser yourself.
</details>

## Output columns

| Column | Notes |
|---|---|
| Invoice Number | Parsed from a line containing "Invoice No/Number/#" |
| PDF File Name | |
| HSN/SAC Code | One row per code found in the invoice's line-item table |
| Vendor Name | Best-guess: first company name (…Ltd/LLP/Pvt Ltd/etc.) before the "Customer/Bill To" section |
| GSTIN of Vendor | First 15-char GSTIN found before the "Customer/Bill To" section |
| Taxable Value | Per HSN/SAC line |
| Tax | CGST+SGST+IGST (or a generic tax column) per HSN/SAC line |
| Folder Path | Folder the PDF was found in |
| Extraction Notes | Flags rows that need manual review (e.g. no table detected) |

## How extraction works (and its limits)

Invoice layouts vary a lot, so this uses heuristics rather than a fixed
template (see `extractor.py`):

- Tables are located by finding a header cell containing "HSN" or "SAC".
  Two-row headers (e.g. "CGST" then "% / Amount" on the next row) are merged
  automatically.
- Vendor details are assumed to sit above the first "Customer / Bill To /
  Buyer" label on the page, which matches the typical letterhead-then-billing
  layout.
- If no table can be parsed at all (scanned image, unusual layout, etc.), a
  best-effort text scan is used and the row is flagged in **Extraction
  Notes** so it can be checked manually.
- Pages with no embedded text (scanned/photographed invoices) are detected
  automatically and run through Tesseract OCR to recover text, which then
  goes through the same best-effort scan above. OCR'd rows are always
  flagged in **Extraction Notes** for manual verification, since OCR
  accuracy depends heavily on scan quality.

Given the range of formats these invoices come in, treat rows flagged in
**Extraction Notes** as needing a manual check rather than fully trusting
every row blindly, especially for unusual or scanned invoice formats.
