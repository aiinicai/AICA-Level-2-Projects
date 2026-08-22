# User Manual

1. Create or open a project with client, FY and notice details.
2. Import GSTR-2A/generic Excel, PDF, or pasted GSTINs. Invalid GSTINs are excluded and shown under Exceptions; duplicate invoice occurrences aggregate under one GSTIN.
3. Save each client's GST Portal login ID and password under **Projects > Edit Project / GST Login**. These credentials are encrypted locally.
4. On **Verify GSTINs**, click **Start Automatic Verification**. Login ID, password and GSTIN are entered automatically. When the GST Portal shows CAPTCHA in Edge, type it in the CAPTCHA box on the software screen and click **Submit CAPTCHA & Continue**.
5. The app continues automatically, captures data, selects the project FY, saves the evidence PDF and moves to the next GSTIN. Use **Retry Selected Now** after any interruption.
6. Review the active client's Results tabs, export branded reports, and create an integrity-tested ZIP backup.

Each project is isolated. Changing the active client/project changes the dashboard, imports, queue, results and reports. FY choices run from FY 2017-18 through the ongoing FY.

Important: GSTR-3B filing does not establish invoice-level payment or ITC eligibility. Verify with invoices, books, GSTR-2A/2B, supplier confirmations and applicable law.

## Manual acceptance testing

- One GSTIN; duplicates pasted; same GSTIN in 100 invoices and multiple files.
- GSTR-2A/generic Excel, searchable/scanned PDF, invalid GSTIN.
- Monthly, quarterly and frequency-change cases; active/cancelled/suspended status.
- Missing/delayed returns; invalid CAPTCHA; timeout; browser restart; manual fallback.
- Excel/PDF export, short evidence filename/hash, backup/restore, clean Windows 10/11 EXE test.

Desi Fintax — CA Anooj Sushil Goenka | M: 9833049094 | WA: 9028593321
