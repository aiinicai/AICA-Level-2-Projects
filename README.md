# Loan Annexure Generator

A browser-based tool for tax auditors that prepares the **unsecured loan annexures** of the tax audit report:

| Period | Act | Form | Clauses |
|---|---|---|---|
| Financial Year 2025-26 | Income-tax Act, 1961 | Form 3CD | 31(a) loans taken (s.269SS), 31(c) repayments (s.269T) |
| Tax Year 2026-27 onwards | Income-tax Act, 2025 | Form 26 | 45(a) loans taken (s.185(1)), 45(d) repayments (s.188(1)) |

Load loan ledgers from **Excel, CSV, PDF or Tally**, in any layout. The tool finds the fields it needs and applies the Rs 20,000 limit rules. It works out each lender's maximum outstanding and whether the loan was squared up, assigns the nature codes (A–L) and flags possible violations. The report is consolidated year-wise per lender and downloads in the e-filing utility's annexure format, along with a working paper.

## Features

- **No input template:** reads Tally Ledger Vouchers / Group Vouchers exports, printed ledgers (text PDFs), multi-ledger files and multi-page PDFs.
- **Field detection:** columns are mapped automatically. You can review and change the mapping, and it is remembered per file layout.
- **Control checks:**
  - Per-ledger balance check (opening + credits − debits = closing in the source).
  - List of skipped lines (totals, carried-forward lines, page headers).
  - Duplicate entries across files.
- **Rules:**
  - Threshold test: amount ≥ limit, or amount + balance outstanding ≥ limit.
  - Maximum amount outstanding during the year; squared up (Yes/No).
  - Excluded lenders: banks, co-operative banks, Government, Government companies, statutory corporations and similar (configurable).
  - Interest and TDS journals excluded by default (listed separately).
  - Nature codes A–L as per Note 1 to Clause 31 (Notification 23/2025).
  - Code L (31(a)) and code K (31(c)) default to "Account payee cheque".
- **Optional fields:** PAN, Aadhaar and address can be left blank.
- **Outputs:**
  - `Annexure_31a.xlsx` / `Annexure_31c.xlsx`, or `Annexure_45a.xlsx` / `Annexure_45d.xlsx`, filled into the official template. Headers, dropdowns and cell formats are preserved.
  - A working paper workbook with sheets for: settings, party summary, transaction detail, exclusions, possible violations, reconciliation and an audit trail of manual edits.

## Use it

1. Open `index.html` in a modern browser (Chrome, Edge or Firefox), or host it with GitHub Pages (below).
2. **Step 1:** choose the year and enter the client details and options.
3. **Step 2:** drop the ledger files, or click **Load sample data** to try it out.
4. **Step 3:** confirm the column mapping, tick the loan ledgers and set each lender's category.
5. **Step 4:** review the possible violations, the items to review and the excluded entries.
6. **Step 5:** edit the rows if needed, then download the annexures and the working paper.

The annexures download as `.xlsx`, which is the same format as the utility's template. If your utility only accepts `.xls`, rename the extension.

## Host on GitHub Pages

1. Push this repository to GitHub.
2. Go to **Settings → Pages → Build and deployment**.
3. Choose **Deploy from a branch**, then the `main` branch and the `/ (root)` folder, and click **Save**.
4. After a minute the app is live at `https://<your-username>.github.io/<repository-name>/`.

## Privacy

All reading, calculation and file generation happens **inside your browser**. Ledger data is not uploaded anywhere. The page loads three open-source libraries from public CDNs: JSZip (cdnjs), SheetJS (jsDelivr) and PDF.js (jsDelivr). It also loads fonts from Google Fonts.

## Limitations

- **Tally MCP:** the direct Tally connection works only when the app runs inside the Claude desktop app, on the computer running Tally Prime and its MCP server. In a normal browser, export the ledgers from Tally to Excel or PDF instead.
- **Scanned PDFs:** image-only PDFs need OCR and cannot be read.
- **Form 26:** this mode uses the Form 3CD column layout with Form 26 titles. Verify the layout and the limits under sections 185/188 with the notified Form 26 e-filing utility before filing.
- **Professional judgement:** the output supports, and does not replace, the auditor's judgement. Review the flagged items, journal entries (codes E–J) and "assumed" account payee entries against the vouchers and bank statements.

## Repository structure

```
index.html            The complete app (HTML, CSS, JS; annexure templates embedded)
templates/
  Annexure_31a.xls    E-filing utility template – Clause 31(a)
  Annexure_31c.xls    E-filing utility template – Clause 31(c)
README.md
```
