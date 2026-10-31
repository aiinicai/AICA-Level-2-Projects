# Reconstructed requirement amendments

Source: user messages visible in the SALES360 development conversation. Reconstructed on 31 October 2026, Asia/Dubai. The order below follows the available conversation; dates of individual amendments were not supplied. This document records requests, **not a claim that every request is complete**.

1. Provide email/username signup, forgot-password recovery to the registered email and Administrator-assigned Administrator, Super user and User roles. Microsoft 365 / Outlook was selected for possible live email.
2. Deliver Python files, batch launchers and a Windows installer; install required libraries and make the installed core run offline without API keys.
3. Provide installation and usage guides, an optional desktop shortcut and a distinctive desktop icon; run, test, debug and rerun before delivery.
4. Keep company legal name, registered address, TRN, accounting/VAT/advance/retention inputs editable. Use imaginary details for tests.
5. First installation must allow a first system Administrator to create an ID/password. Administrator creates users and assigns duties and permitted work areas under settings.
6. Preserve existing features while reviewing financial imports, OCR, statutory documents, advanced permissions and independent security/performance checks. Use the supplied customer master/e-invoicing and statement-of-accounts formats.
7. Work in a separate Version 2 folder if needed. Pause/resume requests were made during development; they do not change the business specification.
8. Add Utility, Analytics & Reports and Setting menus. Utility should expose Tally offline, Zoho online and other ERP options. Add password change, user roles, repair/troubleshooting and black/blue/grey/pink themes.
9. Reports should cover receivable ageing, customer/project collections and outstanding, and date-range receivables; provide Excel/PDF export for supported reports.
10. Add Outlook opening/recovery helper behavior. Real mail delivery still requires an external configured service/network; an offline mailbox is not an actual external inbox.
11. Prepare an imaginary 100-customer database and matching statements in the supplied Excel formats for import testing.
12. Diagnose installer failures around nested setup, changing the destination and rejecting non-empty unrelated folders; retain data and test a clean/custom destination.
13. Prepare a PowerPoint description of development from the master prompt, and a fictional Design and Supervision contract for testing.
14. Version 7: revise first opening/signup, administrator recovery, USER management, customer data import, company creation and accounting-period assignment; deliver all source and installer files.
15. Investigate blank pages after menu navigation on another PC. Allow the system Administrator to perform all implemented tasks while preserving validations.
16. Version 8: make Customer Statement of Accounts Import visible; after reviewed import, automatically create/update linked customer and project masters. Leave missing customer fields editable manually.
17. Repair Excel content errors in the one-project and multiple-project sample SOA workbooks; validate the package before redelivery.
18. Version 9: add Statutory Compliance > VAT, UAE VAT calculations/review/filing records linked to final invoices, and reports of filed periods and amounts. Link the filing action to the FTA portal: https://eservices.tax.gov.ae/#/Logon. Generate five fictional tax invoices for tests.
19. Allow manually recorded input credits and signed adjustments to calculate the period's final VAT liability.
20. Prepare 101 imaginary customer statements in one workbook and 101 matching tax invoice PDFs in one ZIP. The original 100-sheet importer cap led to the 0.9.1 compatibility change.
21. After an upload error from a running version capped at 100 sheets, match the user's downloaded SOA template and provide two compatible files: 100 statements plus the remaining statement. Verify both imports and all balances.
22. Prepare a GitHub evaluation source package below browser size limits, including Python/batch/Markdown files, prompts, development steps, installation/usage guides and the files/instructions needed for the evaluator to build their own EXE.

The current implementation boundaries and external integration gaps are recorded in `../docs/EVALUATION-STATUS.md`. Do not interpret this requested scope as verified full compliance, universal absence of defects or an independent security/performance audit.
