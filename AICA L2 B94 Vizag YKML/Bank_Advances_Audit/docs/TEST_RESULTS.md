# Verification performed - 15 October 2026

Environment: Python 3.12.14, Linux. CustomTkinter desktop module imported successfully
using CustomTkinter 5.2.2. Python module compilation passed.

`python -m unittest -v`: 25 behavioral tests passed.

Coverage includes:
- Fictional account/borrower/finding controls and distinct-account exposure totals.
- Before/after-margin creditor deduction, sanction capping and non-negative stock DP.
- Complete-window continuous excess; equality breaking continuity; missing day blocking
  a full-window conclusion; partial history not running full-window no-credit screens.
- Historical effective sanction/DP rather than snapshot limits; no-credit/interest shortfall.
- Term-loan partial payment allocations, future dues, paid dues and exact age boundary.
- Borrower cross-facility follow-up without changing bank classification.
- Insurance validity boundary and required Not applicable records remaining review points.
- Unknown accounts, duplicate daily dates and invalid policy settings rejected.
- Policy changes affecting checks; no-finding account still requiring coverage review.
- Required review fields/proposed reporting wording; session source/policy guards.
- Selected-account AI prompt scope, safe exports, HTML escaping and mocked API response.

## Baseline controls
| Measure | Expected |
|---|---:|
| Accounts | 8 |
| Borrowers | 7 |
| Supplied daily rows | 390 |
| Findings | 18 |
| Outstanding INR | 4,650,000 |
| High-priority accounts | 6 |
| High-priority unique-account exposure INR | 3,550,000 |
| Incomplete-history accounts | 1 |

The reproducible example output documents one CC002 finding and CC001 account coverage.
Its remaining counts are therefore 17 unresolved findings, 7 accounts pending coverage,
and 1 proposed reporting point. It is deliberately NOT a cleared audit.

## Not yet verified
Windows GUI layout/interaction, real CBS exports, actual bank populations/documents,
regulatory classification accuracy, provisioning, live API availability/output quality,
and Excel desktop visual layout. Excel export content/structure was checked programmatically.
No complete/current regulatory ruleset is implemented or certified. Behavioral test results
do not establish real-bank-data accuracy or professional compliance.

## Participant trial run
Run install.bat/run.bat; load demo; inspect all six tabs; save a finding and account
coverage assessment; export/open Excel/HTML; save/reload the original-input session;
try optional AI only if you have appropriate account access and authorization.
