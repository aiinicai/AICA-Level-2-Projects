# UAE VAT working paper rules — Version 9

Reviewed against FTA-hosted material on 29 October 2026. The system applies decimal AED calculations and mathematical rounding to fils. It does not connect to FTA, store portal credentials, submit returns, pay tax or transmit structured e-invoices.

## Implemented calculation and controls

- Final invoices feed the output register automatically. Explicit invoice review classifies standard-rated (5%), zero-rated, exempt or out-of-scope supplies and records tax point, supply date and the relevant supplier establishment Emirate. Classification never changes posted money. The user confirms earlier payments and continuous-supply rules. Draft invoices are excluded.
- Standard output is allocated to the seven Emirate rows of VAT201 Box 1. Zero-rated and exempt values feed Boxes 4 and 5. Out-of-scope values remain in the register and are excluded from those return boxes. Net credit-note amounts and VAT reduce their original classification by credit effective date. Write-offs do not automatically claim VAT bad-debt relief.
- Manual, evidenced working-paper entries cover non-invoice supplies, tourist refunds, reverse-charge outputs, imports, import adjustments, eligible standard input tax and eligible reverse-charge input tax. Entries contain taxable amount, VAT, signed VAT adjustment, reference and reason. Duplicate entry references and obvious overclaims/rate mismatches are rejected. Recoverable input VAT can be less than the VAT incurred; the operator must apply blocked-cost, attribution, apportionment and recovery-period rules. It is not guessed from missing purchase records.
- Output VAT due is the sum of output VAT and output adjustments. Recoverable input VAT is the sum of eligible input VAT and input adjustments. Net liability is the difference. Negative amounts are a recoverable period position; prior credits/refunds and payments are not automatically applied.
- The user enters the FTA-assigned period. Overlap is prevented. Base due date is end + 28 calendar days. A different portal/holiday deadline needs evidence; no national-holiday calendar is guessed. The operator reviews relevant invoice deadlines (ordinary tax invoice issuance within 14 days, subject to applicable rules/exceptions).
- Finance Administrator or System Administrator review is required before recording a filing. Completeness, eligibility and warning declarations are required. Source changes invalidate review. Actual portal filing is manual. A local filing requires a closed period, actual past/current filing date, acknowledgement and evidence.
- Filed snapshots are immutable. Later source changes are flagged in the filed report without changing the recorded period amounts. Correction/voluntary-disclosure decisions remain with the authorized filer and the applicable FTA process.

## Primary sources

1. [FTA VAT legislation index](https://tax.gov.ae/en/legislation/vat.aspx).
2. [FTA-hosted Executive Regulation consolidated September 2026](https://tax.gov.ae/Datafolder/Files/Legislation/2026/Law-No-8-of-2017-and-its-amendments--09-2026.pdf), especially Articles 59–64. The document includes provisions with later effective dates; future apportionment provisions are not applied early by this module.
3. [FTA filing and payment guidance](https://tax.gov.ae/en/content/filing.vat.returns.and.making.payments.aspx).
4. [FTA VAT201 EmaraTax user manual](https://tax.gov.ae/DownloadOpenTextFile?fileUrl=en/VAT_VAT_Guides/Process_Final_VAT_return/Process_Final_VAT_return_EN.pdf), used for portal navigation and VAT201 output/input box layout.
5. [FTA Decision 17 of 2026 — employee-expense input tax recovery](https://tax.gov.ae/Datafolder/Files/Pdf/2026/legislation/FTA%20Decision%20No.%2017%20of%202026%20on%20the%20Cases%20and%20Conditions%20for%20the%20Recovery%20of%20Input%20Tax%20Incurred%20on%20Employee%20Expenses%20-%20Publishing.pdf). Input-eligibility decisions must consider the applicable evidence and conditions; the system does not treat all employee costs as deductible or all as blocked.

## Scope of the tax invoice PDF

Printed AED documents contain the particulars for the supported single-line service invoice: supplier/customer identity and address, relevant TRNs, sequential number, issue and supply dates, description, quantity, unit price, discount, tax rate, VAT and gross amount. The supplier/customer snapshots are retained after review. This does not implement a UAE ASP/e-invoice exchange, foreign currency conversion, special-sector place-of-supply determination, automatic input apportionment or statutory tax-credit-note PDF generation. Review those obligations separately before real filing.
