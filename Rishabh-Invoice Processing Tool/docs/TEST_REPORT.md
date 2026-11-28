# Test report (v0.6.0)

## Automated tests
`run_tests.bat` (Windows) or `QT_QPA_PLATFORM=offscreen python -m pytest -q`: **116 passed** (Linux build box).
Previous Windows run (v0.4.2): 73/73 passed on the user's PC.

| Area | Tests |
| --- | --- |
| Login, users, permissions, companies/FY | test_auth, test_companies |
| Upload, OCR rules, extraction, validation, review | test_documents, test_extraction, test_ocr_rules, test_invoice_service |
| GSTIN check digit + OCR repair | test_gstin, test_ocr_rules |
| Tally: masters, mapping, voucher XML (party first), import, verify, re-check after delete | test_tally (fake Tally server) |
| GSTR-2B Excel/JSON parsing, upload/replace/history | test_gstr2b, test_recon_services |
| Purchase register Excel wizard + Tally Day Book parsing | test_recon_services |
| Reconciliation: every status and stage, ambiguity, three-way, manual link | test_recon_engine, test_recon_services |
| Reports, dashboard = export = purchase register totals, PDF/CSV/XLSX | test_reports |
| Backup, verify, tamper detection, staged restore, schedule | test_backup |
| Every page opens with data (offscreen) | test_ui_smoke |

## Real-world checks done
- TallyPrime (user's PC): connection, master sync, Day Book verification, voucher import into the test company
  Majisa Lime Product; ledger order fixed and verified via Tally (Input CGST 2,187.60 / SGST 2,187.59 /
  Round off 0.07, Dr = Cr = 91,879.07).
- OCR on the user's 9-bill phone scan: 6/63 fields → ~53/63 on Windows (59/63 on the build box), no wrong value
  above the review threshold except one invoice number (229 read as 2209).

## Performance (5,000 records per source, build box)
| Operation | Time |
| --- | --- |
| List 5,000 invoices | 0.15 s |
| Three-way reconciliation (15,000 records) | 0.86 s |
| Dashboard figures | 1.8 s |
| Supplier report | 0.06 s |
| 12-sheet workbook | 4.4 s |
| Backup | 0.2 s |

## Not yet verified (honest list)
- GSTR-2B Excel / JSON downloaded for the user's own GSTIN (parser follows the portal layout; needs one real file).
- Purchase register fetch from the user's TallyPrime.
- PyInstaller .exe and Inno Setup installer on Windows.
- Credit/debit note and reverse-charge voucher import into Tally (not built).
