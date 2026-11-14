# Development process from the master prompt

## 1. Establish requirements and acceptance boundaries

Start with `SALES360_Codex_Master_Prompt.md`, `prompts/02-REQUIREMENT-AMENDMENTS.md`. Separate implemented requirements from outstanding integrations, OCR, security/performance audits and specialist tax acceptance. Keep implementation status tied to actual test evidence.

## 2. Establish the local architecture

Use `apps/web` for the React interface; `apps/api` for authenticated APIs and financial workflows; `src/domain` for arithmetic/validation; `apps/api/schema.sql` for PostgreSQL migrations; `scripts/render_pdf.py` for PDFs; and `installer/windows/SALES360.py` for protected offline runtime lifecycle. Do not expect a Python launcher alone to replace the other components.

## 3. Implement identity, company and permissions

On empty local data, enroll the first Administrator, register the recovery address and accounting period, then assign user tiers, duties and module work areas. Keep server-side company/role checks and record Administrator overrides. Test signed-out recovery without exposing credentials in source or logs.

## 4. Implement master data and import

Use the supplied customer/e-invoice fields and nine-column SOA format. Preview before posting; preserve source cells, validate dates/amounts and controls, present the customer/project match plan and commit transactionally. Test retry/duplicate protection. Current 0.9.1 supports 101 statement sheets; the two bundled files also work within the older 100-sheet cap.

## 5. Implement billing, collections and reports

Assess cumulative payment certificates, route approvals, issue supported final invoices and record receipts/allocations. Reconcile gross invoices less collections/adjustments to customer and project balances and report controls. Keep draft amounts out of final receivables. Generate and inspect PDF/Excel output.

## 6. Add VAT working papers and manual review

Link final-invoice tax facts; allow supported input-credit entries and signed adjustments; reconcile the period and review snapshot; retain filed acknowledgements and period/total reports. Keep real portal filing and tax-policy acceptance explicit. The FTA button opens a website; the app does not transmit a return or pay tax.

## 7. Prepare the offline runtime

Download SDK/runtimes and libraries on the build PC. Compile TypeScript and the self-contained .NET host. Stage embedded Python, PostgreSQL, local web assets, templates, icons, guides and notices. Hash the bundle. The installed program should not fetch libraries or request API keys.

## 8. Package Windows installation

Use NSIS to compile the application installer and complete prerequisite wrapper. Offer an optional desktop icon and protect unrelated destination files. Test a fresh installation and an upgrade, startup, menu navigation, shutdown, backup and recovery using synthetic data. Client-PC acceptance and code signing remain distinct delivery checks.

## 9. Reproduce and test the source handover

Run Prepare-BuildTools.bat, Build-Windows.bat and Test-Evaluation.bat from a separate checkout. Validate source archive contents and file sizes. Keep local test databases, caches and generated EXEs out of Git. Record actual checks and keep private test results outside the source upload.

## 10. Submit for evaluation

Upload the extracted source tree using Git/GitHub Desktop or browser batches, not the original development workspace. The evaluator rebuilds the installer locally. Include the prompts' provenance, current scope, known gaps, source hashes, test commands and build/usage guides. Version and publish binaries separately only when the owner authorizes it.
