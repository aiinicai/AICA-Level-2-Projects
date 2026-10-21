# Demo sample files (all data is made up)

Demo supplier used in these files: **Demo Traders, GSTIN 33DEMOA1234B1ZD**, Tamil Nadu (state 33), Regular, Monthly.
Create this client on tab 2 of the app, then create the returns below. Delete the demo client when you finish.

| File | Use it in return | What it shows |
|---|---|---|
| 03_Demo_Master_Template_FILLED_Jul2026.xlsx | **July 2026** - tab 4, Upload Filled Template | The one-file Master Template, filled and clean (35 rows): B2B, B2CL, B2CS, exports, notes, advances, HSN, documents |
| 02_Demo_HSN_Report_WITH_WRONG_CODES.xlsx | **August 2026** - tab 5 | A billing-software HSN report. Warning: HSN 00000002 is a placeholder (MELAMET CREAM, SUHAGRA). Error: HSN 380 has 3 digits (HAND SANITIZER) |
| 07_Demo_GST_Output_Register.xlsx | **August 2026** - tab 5 (with file 02) | A date-wise output register: B2CS by rate, exempt sales and the document series (Table 13) |
| 01_Demo_Sales_Register_Sep2026.xlsx | **September 2026** - tab 5 | Normal sales register with deliberate problems (see below) |
| 04_Demo_Tax_Invoice_PDF-001.pdf | **September 2026** - tab 5 | A text PDF invoice, two items, extracted correctly |
| 05_Demo_Tax_Invoice_PDF-002_wrong_HSN.pdf | **September 2026** - tab 5 | A PDF invoice with HSN 00000002 (placeholder warning) |
| 06_Demo_SCANNED_Invoice_PDF-003.pdf | **September 2026** - tab 5 | A scanned (picture-only) invoice - needs OCR (Tesseract installed). Optional |

## Problems placed in 01_Demo_Sales_Register_Sep2026.xlsx
| Invoice | Problem | Message on tab 8 (Validation) |
|---|---|---|
| DEMO/008 Madurai Stores | GSTIN has a wrong check digit | Warning GSTIN_CHECKDIGIT |
| DEMO/009 Salem Pharma | HSN 00000002 | Warning HSN_PLACEHOLDER |
| DEMO/010 Trichy Agencies | HSN 392 (3 digits) | Error HSN_INVALID |
| DEMO/004 (appears twice) | Same line entered twice | Error TOTAL_MISMATCH |
| DEMO/005 | Missing number in the series | Info SEQ_GAP |
| DEMO/007 Bengaluru Buyer | Unregistered, other state, above 1 lakh | Classified as B2CL (tab 7) |
| DEMO/CN/001 | Credit note against DEMO/001 | Classified as CDNR (tab 7) |

After uploading, click **Approve all without errors** on tab 6 so that the lines flow into tabs 10, 11 and 15.
Do not upload files 01 and 02 into the same return (both feed the HSN table).

R Suresh & Associates, Chartered Accountants
