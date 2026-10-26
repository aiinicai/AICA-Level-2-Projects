# GST Reconciliation Tool

An offline, browser-based tool that reconciles GSTR-1, GSTR-3B and GSTR-2B returns against each other and against your Tally books. Drop in the returns, and it builds one formatted Excel working paper for audit and compliance work.

> Everything runs inside your browser on your own PC. No file, figure or client name is uploaded anywhere.

## What it does

- Reads GSTR-1, GSTR-3B and GSTR-2B downloads for any number of months at once, and works out the form, GSTIN and period of each file.
- Compares GSTR-1 with GSTR-3B (outward liability) and GSTR-2B with GSTR-3B (ITC) month by month, with a summary preview before you download anything.
- Reads the Tally Sales and Purchase Registers and fills the "As per books" columns month-wise.
- Warns when files from more than one GSTIN or financial year are mixed, or when the same month is supplied twice.
- Builds a multi-sheet Excel workbook in which every difference is a live formula.

## Requirements

- A Windows PC with PowerShell (built in). No Node.js, Python or installation needed.
- Chrome or Edge.
- The `lib/` folder kept next to `GST Tool.html`.

## Quick start

1. Download this repository (**Code → Download ZIP**) and extract it, or clone it.
2. Start the local server from the extracted folder. Right-click `serve.ps1` → **Run with PowerShell**, or run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\serve.ps1
   ```

3. Open **http://localhost:8971/** in Chrome or Edge.
4. Drop in your returns, or the sample files in [`sds/`](sds), then click **Generate comparison workbook**.

Close the PowerShell window to stop the server. To use another port, run `.\serve.ps1 -Port 8080`.

Open the tool through `serve.ps1` rather than double-clicking the HTML file. Browsers block pdf.js from loading its worker on a page opened straight from disk, so PDF returns would not be read.

## Supported files

| Return / export | Format | Where to get it |
|---|---|---|
| GSTR-1 | PDF, or JSON (portal or Winman; a ZIP of JSON files also works) | GST portal → Returns → GSTR-1 → Download |
| GSTR-3B | PDF, or JSON | GST portal → Returns → GSTR-3B → Download |
| GSTR-2B / GSTR-2B quarterly | XLSX | GST portal → Returns → GSTR-2B → Download Excel |
| Tally Sales Register | XLSX | Tally → Sales Register in columnar view → Export (Alt+E) → Excel |
| Tally Purchase Register | XLSX | Tally → Purchase Register in columnar view → Export (Alt+E) → Excel |

The tool reads the month from the portal file name first (for example `102025_…` is Oct-25), then from the return itself. If you rename a file, keep the `MMYYYY` part.

### Tally registers

Upload them with **+ Add Tally Sales / Purchase Register**, or drop them in the main box. The tool expects Tally's columnar register:

- a title row reading `Sales Register` or `Purchase Register`;
- a header row starting `Date`, `Particulars`, `Voucher Type`, `Voucher No.`;
- one column per ledger, one row per voucher.

Columns whose names contain IGST, CGST, SGST/UTGST or Cess are read as tax. All other ledger columns, except Round Off, TDS and TCS, make up the taxable value. Vouchers are grouped by the month of their date, and Credit Note, Debit Note and return vouchers are subtracted.

| Register | Fills |
|---|---|
| Sales Register | "1 vs 3B (Liability)", Table 1, "As per books" |
| Purchase Register | "2B vs 3B (ITC)", "ITC as per books" |

## Output workbook

| Sheet | Contents |
|---|---|
| Cover | GSTIN, periods covered, every file read, and points to check |
| 1 vs 3B (Liability) | GSTR-1 vs GSTR-3B for taxable, zero-rated, nil/exempt and reverse-charge supplies, with cumulative difference and books columns |
| 2B vs 3B (ITC) | GSTR-2B ITC vs GSTR-3B 4(A), reversals, net ITC, cumulative difference and books columns |
| GSTR-1 Table-wise | Each GSTR-1 table per month and the row it was taken from |
| GSTR-3B Table-wise | Tables 3.1, 3.1.1, 3.2, 4(A)–4(D) and 5.1 per month |
| 2B ITC Detail | GSTR-2B summary headings per month and net ITC |
| 2B Supplier Ledger | Every GSTR-2B document; credit notes negative and shaded, rejected or ineligible ITC in red |
| 2B Supplier Summary | ITC by supplier GSTIN |
| B2B Invoices, B2CS Summary, HSN Summary, CDN & Amendments | Added when GSTR-1 JSON is supplied; prior-year notes are flagged |
| 3B Challan 6.1 | Tax paid through ITC and in cash, interest and late fee, per month |
| GSTR-9 Draft | Annual GSTR-1, GSTR-3B and GSTR-2B figures laid out by GSTR-9 table, with editable draft columns |
| GSTR-9C Draft | Turnover and ITC reconciliation linked to the GSTR-9 draft |

Yellow cells are for books figures. Every difference column is a live Excel formula, so editing a figure recalculates the differences.

## Sample data

[`sds/`](sds) holds a complete fictional set for **Sample Traders Private Limited** (GSTIN 32AABCS1234F1Z5), October to December 2025:

- 3 × GSTR-1 (JSON), 3 × GSTR-3B (PDF), 3 × GSTR-2B (XLSX)
- Tally Sales Register and Purchase Register (XLSX)

Differences are planted on purpose, such as a cash sale missed in GSTR-3B and an invoice whose supplier hasn't filed. [`sds/README.txt`](sds/README.txt) lists each one with the expected totals. Upload all 11 files together.

## Demo

[`docs/GST Tool - 2 Minute Demo Script.docx`](docs) is a two-minute walkthrough script that uses the sample data.

## Repository layout

```
GST Tool.html   the tool (open it through serve.ps1)
serve.ps1       small local web server (PowerShell, localhost only)
lib/            pdf.js, SheetJS, ExcelJS and JSZip, loaded locally with no CDN
sds/            fictional sample returns and Tally registers
docs/           demo script
```

## Notes and limits

- Sales Register totals go into Table 1 only. Zero-rated and exempt sales in the register are not split out to Tables 2 and 3.
- Credit notes reduce the books figure only when they appear as vouchers in the uploaded register. Tally normally keeps them in a separate Credit Note register.
- Tally data for months not covered by the uploaded returns is ignored.
- GSTR-3B is filed in whole rupees while GSTR-1 carries paise, so small rounding differences are normal.
- The workbook is a working paper generated from the returns supplied. It is not a filed document and does not replace professional judgement.

## Privacy

- All processing happens in the browser. `serve.ps1` only listens on `localhost`.
- Never commit real client returns. The `.gitignore` blocks PDF, Excel, JSON and ZIP files everywhere except `sds/` and `docs/`.

## Third-party libraries

Bundled in `lib/` under their own licences:

| Library | Licence |
|---|---|
| [pdf.js](https://github.com/mozilla/pdf.js) 3.11.174 (Mozilla) | Apache-2.0 |
| [SheetJS Community Edition](https://sheetjs.com) 0.18.5 | Apache-2.0 |
| [ExcelJS](https://github.com/exceljs/exceljs) | MIT |
| [JSZip](https://stuk.github.io/jszip/) 3.10.1 | MIT or GPLv3 |
