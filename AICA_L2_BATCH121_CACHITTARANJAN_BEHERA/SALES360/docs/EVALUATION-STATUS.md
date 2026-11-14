# Evaluation scope and evidence

Source version: **0.9.1**, prepared for handover on **31 October 2026** (Asia/Dubai). This is the Version 9 core plus support for 101 SOA statement sheets in a workbook. No database/schema migration beyond schema 9 is introduced by that compatibility change.

## Implemented scope

- First-owner Administrator enrollment, company profile/accounting period, user tiers/duties/work areas and local account recovery.
- Customer master and supplied-format Excel SOA import; reviewed automatic customer/project matching and creation; historical invoices, collections and duplicate prevention.
- Project billing/certificates, approval workflow, final invoice records, receivables, receipts/allocations and bounded financial corrections.
- Reports and Excel/PDF exports for supported analyses.
- VAT period working papers linked to final invoices; reviewed input credits, signed manual adjustments, review/filing acknowledgement records and filed-return reporting; tax invoice PDFs for supported treatments.
- Offline Windows launcher, bundled runtimes, optional desktop icon, backup/restore and diagnostics/repair helpers.

## Material limits

- Full original master-spec acceptance is incomplete. Review the consolidated master prompt at the repository root.
- Tally/Zoho/other ERP adapters and external posting are not connected. Outlook/Microsoft 365 live delivery is not an offline feature.
- OCR extraction is unavailable. A contract upload is not a guarantee of malware clearance; configure/validate an actual scanner.
- No automatic FTA submission, payment, accredited ASP transmission or independent tax certification. VAT treatments/input eligibility and statutory/e-invoicing obligations require finance review before real use.
- No independent security audit, load/performance benchmark or universal fresh-client-PC certification is claimed. Unsigned installer; no code-signing identity was supplied.
- Local data/key recovery is constrained by Windows DPAPI identity/machine protection. Do not assume a copied database/backup automatically migrates to another PC.
- A .py launcher does not replace the React, .NET and PostgreSQL application stack.

## Verification scope

The reduced package retains the supported local build scripts, domain tests and 101-customer import test. Historical evidence, archived tests and duplicate release notes were removed to meet the file-count requirement. No source module required by the supported build was intentionally removed.

The earlier full source package passed a local cache-based installer build, domain/VAT tests and all 101 customer balance checks. The reduced source is rechecked separately. Download availability and independent fresh-PC, security and performance certification remain separate acceptance checks.
