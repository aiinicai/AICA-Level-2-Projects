# Troubleshooting

| Problem | What to do |
| --- | --- |
| "Tesseract OCR is not installed" | Install Tesseract (docs/OCR_SETUP.md) or set its path in Settings & Backup. Digital PDFs work without it. |
| Scanned bills read poorly | Run `install_ocr_boost.bat` once (OpenCV). Scan at 300 dpi, straight, no shadows. Use the review screen for amber/red fields. |
| Tally: "connection refused" / not reachable | Tally must be running with port 9000 enabled (docs/TALLY_SETUP.md) and the company open. |
| Tally: "<company> is not open in Tally" | Open the company in Tally; the name in Company Settings must match exactly. |
| Import says "unverified" | Tally answered but IPT could not find the voucher again. Check the date/party in Tally, then XML Import → Re-check in Tally. |
| Voucher shows wrong ledgers in Tally | Fix the mapping (Master Mapping), delete the voucher in Tally (Alt+D), XML Import → Re-check (it becomes "deleted in Tally"), import again. |
| GSTR-2B upload: "outside the financial year" | Select the right financial year in the top bar first. |
| GSTR-2B upload: "GSTIN" error | The file is for another GSTIN than the selected company. |
| GSTR-2B Excel: "header row not found" | Use the Excel downloaded from the portal's GSTR-2B page without editing the sheets. Send the file to support if the portal layout changed. |
| Purchase register Excel: rows rejected | Purchase Register → select the import → Export rejected rows; fix and import again. |
| Reconciliation shows "2 possible matches" | Two documents qualify; IPT never guesses. Select the right rows → Manual match with a remark. |
| A page looks empty | Check the company and financial year in the top bar. |
| Logs | `IPT_DATA\logs\ipt.log` (no passwords are logged). |
| Something broke after an update | Settings & Backup → Restore the last backup, or copy back `ipt.before-migration-*.db`. |
