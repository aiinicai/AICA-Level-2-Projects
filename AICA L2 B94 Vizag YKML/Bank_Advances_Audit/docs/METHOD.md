# Audit method, assumptions and boundaries

## Scope
This is a working-paper prototype for one branch's supplied CC, stock-backed OD and
term-loan facilities. It is not an automatic RBI classification/provisioning engine.
Agricultural, project-finance, restructured and other special treatments are outside
scope. A complete bank audit covers many additional areas.
The user selects an audit date; account snapshots and payment allocations must be as
of that date. Inputs use our normalized CSV/XLSX templates, not native CBS formats.
The app cannot establish that the supplied accounts form the complete branch population.
Account coverage review is required even for accounts without generated findings.

## Criteria governance
The JSON profile supplies illustrative day settings, tolerance and document requirements.
Verify these against the bank type, audit period, sanction terms, bank policy and current
applicable instructions. Default 90-day settings are screening assumptions, not a complete
current IRAC framework. Screens never change bank_classification or assign SMA/NPA.
A policy change requires a new run and prevents restoration under the old session signature.

## Drawing power
Eligible stock = stock_total - stock_ineligible.
Eligible receivables = receivables_total - receivables_ineligible.
The preparer determines eligibility and debtor ageing; invoice-level ageing is not computed.
Before margin: stock DP = max(0, eligible stock - trade creditors) x (1 - stock margin/100).
After margin: stock DP = max(0, eligible stock x (1 - stock margin/100) - trade creditors).
Receivables DP = eligible receivables x (1 - receivables margin/100).
Round each component to paise, HALF_UP; their sum is uncapped DP.
Capped audit DP = min(snapshot sanctioned limit, uncapped DP).
The bank_dp input must be comparable capped availability at the audit date. Other sanction
methodologies and non-stock-backed ODs require a different calculation and are outside scope.
Use the latest supplied stock statement on/before audit date. A stale statement's result
is historical, not proof of current eligibility. Snapshot excess is not continuous excess.
A DP discrepancy alone is not an established accounting misstatement.

## Daily CC/OD conduct
Inclusive window: audit date minus (window_days - 1), through audit date.
Require one row per calendar date, including non-business days, for a full-window screen.
Recently opened accounts or missing dates produce insufficient-history findings.
Compare closing_balance > min(that day's sanctioned_limit, drawing_power); equality is
not excess. Full-window continuous excess requires every date and excess on every date.
A missing date breaks the observed trailing consecutive sequence. With complete history,
zero credits and credits below interest debits are separate screens. Partial totals are
shown but do not support full-window credit screens. Effective historical limits are
supplied assertions, not reconstructed from sanctions. A final daily balance is compared
with the snapshot where the audit-day record exists. Gross credits do not establish
receipt provenance, appropriation, circular movement, evergreening or fraud.

## Term-loan dues
Unpaid = (principal_due - principal_paid) + (interest_due - interest_paid).
Payments are cumulative allocations supplied as of the audit date. Future due dates are
excluded; age is calendar-day difference. The aged screen uses strictly MORE THAN the
configured term_overdue_review_days (default 90). This is not a universal regulatory
classification/day-end processing decision. Receipt allocation, schedule completeness,
concessions, moratoria and restructuring are not independently reconstructed.

## Borrower relationships, documents and sanctions
A full-window conduct/aged-dues flag creates a borrower-level review on all supplied
facilities sharing borrower_id. Classification is never automatically propagated.
Other branches or omitted facilities remain unknown.
Passed sanction review dates trigger follow-up, not automatic NPA classification.
The illustrative document checklist comes from the JSON. At least one Available,
non-expired record can satisfy a document type; Insurance also needs a validity date.
Validity through the audit date is treated as in date. Required Not applicable records
still need review. Policy coverage, insured amounts, charge perfection, title, signatures,
enforceability and document authenticity are not validated.

## Reviews and closing
Reviewed requires reviewer, evidence assessment, conclusion, action and final disposition.
Potential reporting point additionally requires proposed wording. Management response
remains an unverified assertion. The generated condition is preserved after review.
Reviewed means documentation completed, not remediation executed or all risk eliminated.
Account coverage is independent of finding review. Closing always retains final auditor
responsibility. High/Medium/Low are qualitative priorities, not regulatory risk ratings.
Exposure totals count supplied accounts once, rather than adding repeated issue amounts.

## AI and persistence
Optional AI uses selected-account summaries, finding, policy, document register and review
text. It is not full raw-history analysis or retrieval over authenticated legal sources.
Prompts request facts with IDs, contradictions, evidence gaps and unapproved observations.
No model response changes decisions, classification or provisions. Manual external drafts
have an explicit unverified-provenance label. Preview before sending: borrower/account IDs,
financial figures and branch/reviewer notes are included. API key is memory-only. Requests
set store=false, which is not a zero-retention guarantee. API access/charges are separate.
API tests used mocks, not a live request.
Sessions check input hashes, audit date and policy; even innocent source re-saves can
change hashes. Sessions are editable, unencrypted JSON; event history is not tamper-proof.
No multi-user approval or secure document repository exists. Submit fictional data only.

## Background sources
RBI April 1, 2025 Master Circular, historical conceptual background only:
https://rbi.org.in/scripts/NotificationUser.aspx?Id=12822
This citation/profile does not verify all instructions effective for a 2026 audit.
Obtain applicable current directions and bank policies before professional use.
OpenAI Responses contract:
https://developers.openai.com/api/docs/guides/migrate-to-responses
