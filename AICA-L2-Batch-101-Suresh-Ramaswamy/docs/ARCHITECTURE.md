# Architecture

```
Client files (xlsx / pdf)        Master Template (xlsx)
        |                                |
        v                                v
 app/extractors/                  app/gstr1.py  (read_master_template)
   excel_reader.py  register + invoice-per-sheet
   reports.py       HSN report, output register
   pdf_reader.py    text PDF + OCR
        |                                |
        +---------------> app/services.py <----------+
                    (extract, de-duplicate, store)
                               |
                  SQLite  (app/db.py): clients, returns, files,
                  lines, datasets, documents, audit trail
                               |
   app/classifier.py -> app/validation.py -> app/series.py (Table 13)
                               |
                  app/gstr1.py  build_tables / summarize / reconcile
                               |
         +---------------------+----------------------+
         v                     v                      v
   CSV files (Offline Tool)   GSTR-1 summary     app/annual.py
   app/exporters.py           + reconciliation   YTD, 3B/books, GSTR-9 sheet
                               |
                         app/ui.py  (Tkinter, 15 tabs)
```

* **Invoice lines** come from registers/PDFs and are reviewed by the user (tabs 6-7).
* **Datasets** hold already-summarised rows (B2CS by rate, HSN, exempt) from summary reports or the Master Template.
* `schemas/offline_tool_schema.json` holds the Offline Tool table headings and drop-down values (editable, provisional).
* Money is handled with `Decimal` throughout.

## Year upload and filed-return reconciliation (v2.4)

```
Folder / zip of the year ──> app/yearimport.py  scan (type + month of each file) -> preview -> import into each month
                                     |                       (Master Template, registers, reports, invoices)
                                     v
Filed GSTR-1 / 3B / 9 PDFs ──> app/returns.py   PDF text without the watermark (OCR for picture pages),
                                                 GSTR-1 / 3B / 9 readers, stored per client and FY
                                     |
                                     v
                              app/recon.py      books vs GSTR-1, GSTR-1 vs 3B (portal auto-fill rules),
                                                 3B tax declared / payable / paid, GSTR-9 vs returns and books,
                                                 likely reason and remedy for every difference
                                     |
                                     v
                              app/ui.py tab 15  Reconciliation + Filed returns tables, Excel export
```

* `tools/make_demo_returns.py` makes the made-up demo GSTR PDFs used in `sample_data/Demo_Year_FY2026-27`.
