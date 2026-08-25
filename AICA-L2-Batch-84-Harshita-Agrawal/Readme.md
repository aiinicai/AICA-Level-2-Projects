# Cash2Ledger — Bank Statement to TallyPrime Tool

Created by **CA Harshita Agrawal** (Membership No. 438122).

Cash2Ledger is an offline desktop application that helps accountants convert bank statements into reviewable, TallyPrime-ready accounting vouchers. It accepts PDF and Excel bank statements, lets the user select Tally ledgers, and generates XML files for import into TallyPrime.

## Submission Files

- `Cash2Ledger-Clean-2026-08-09.7z` — compact Windows application package (64.81 MB).
- `Cash2Ledger Project Summary.docx` — problem statement, solution overview, advantages and technology stack.
- `Cash2Ledger_Installation_TallyPrime_User_Guide.docx` — installation, TallyPrime configuration and operating instructions.

## How to Run

1. Extract `Cash2Ledger-Clean-2026-08-09.7z` using 7-Zip or another compatible archive tool.
2. Open the extracted `Cash2Ledger` folder.
3. Keep `Cash2Ledger.exe` and the `_internal` folder together.
4. Start `Cash2Ledger.exe`.
5. Open TallyPrime, configure local ODBC connectivity on port `9000`, and then select **Connect to Tally** in Cash2Ledger.

The application is designed for local/offline processing. Bank statements are processed on the user’s computer and are not sent to a cloud service.
