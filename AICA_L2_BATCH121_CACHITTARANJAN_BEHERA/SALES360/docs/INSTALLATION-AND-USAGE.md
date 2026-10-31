# Install and use SALES360

## Install the EXE you built

1. Build as described in BUILD-FROM-SOURCE.md. Copy the **Complete-Setup-unsigned.exe** from `output/releases` to the target Windows x64 PC.
2. Run setup. Select an empty dedicated program folder or a recognized existing SALES360 installation. Do not select a folder of unrelated documents.
3. Allow the bundled Microsoft C++ prerequisite if Windows requests installation permission. Core installed operation needs no internet or API key.
4. Choose whether to create a desktop icon on the final installation page.
5. Launch SALES360. A local browser page opens on `127.0.0.1`. This is a local application server; a browser window is its interface.

## First Administrator and company

On an empty data folder, use the first-time Administrator setup shown by the launcher. Choose your username/email and strong password, register the recovery email, create the company and set the accounting period. No shared default password is supplied. Complete legal name, registered address, TRN and other company fields before reviewing real documents.

Under Setting > USER management, the Administrator creates users and assigns Administrator, Super user or User tiers, duties and work areas. The Administrator can perform all implemented workflows, while business validations and company isolation still apply.

The default data path is `%LOCALAPPDATA%\SALES360\data`. Installing another copy of the executable does not automatically create another database. For evaluation use an explicit fresh folder:

```bat
Start-SALES360.bat --data-dir "C:\SALES360-Evaluation-Data" --port 5099
```

Use these commands from the installed/staged application folder, not the source root.

## Import the imaginary test records

1. Open Customers > Customer Statement of Accounts Import.
2. Import `examples/01-Import-Customers-001-to-100.xlsx`, then `examples/02-Import-Customer-101.xlsx`.
3. Review each preview and automatic customer/project master plan. Choose AED and **5% VAT included** in billed amounts; confirm posted historical invoices and source warnings and provide a reconciliation reference.
4. Commit each workbook once. On an empty test company expect 101 customers, 101 projects, 101 final invoices and 67 collection records.
5. Expected combined totals: net AED 806,724.75; VAT 40,336.36; gross 847,061.11; collections 420,560.46; outstanding 426,500.65. Do not import the matching PDF samples as additional invoices.
6. Fill any missing customer master fields manually. Review the imaginary contract fees before generating new certificates.

## Everyday workflow

Create/edit customers and projects; prepare payment certificates; submit for assigned reviews/approvals; review drafts and issue final invoices; record collections and allocations; reconcile receivables and statements. Analytics & Reports provides supported receivable, collection and VAT reports with Excel/PDF export. Theme, password, user roles and diagnostics/repair are in settings.

Statutory Compliance > VAT links final-invoice information into period working papers. Review invoice tax facts, add supported input credits and signed manual adjustments, review/reconcile the period, and export the working paper. The filing button opens the FTA portal. Actual portal login/submission requires internet and the user's FTA account; SALES360 does not submit or pay tax. A locally recorded filing acknowledgement is not independent FTA verification.

## Recovery, backup and stopping

Forgot password uses the registered recovery email as the account address. In offline mode recovery messages are stored in the protected local mailbox; no real external inbox is contacted. The installed Outlook recovery helper can open the local recovery message. Outlook does not create an internet-free email delivery service. Use the installed guide for the current recovery flow.

Use `Stop-SALES360.bat` to shut down the app and its database before maintenance. If using a custom data path, pass the same `--data-dir` argument to start, stop, backup and repair. The `.bat` files forward command-line arguments to the launcher.

Run `Backup-SALES360.bat --data-dir "C:\SALES360-Evaluation-Data"` for an encrypted local backup. Restore to a new empty folder and reconcile records before reuse; consult the installed guide. Current DPAPI protection ties local backup keys to the Windows account/machine. Copying a data folder or backup to another PC is not a supported automatic data migration.

Use `Repair-SALES360.bat` for diagnostics. Repair does not promise to correct every possible problem. Keep protected logs and backup data private; do not upload them to GitHub.
