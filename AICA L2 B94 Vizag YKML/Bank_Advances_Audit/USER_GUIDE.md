# Bank Advances Audit - User Guide

## 1. Start the demo
Extract the package. Run install.bat once, then run.bat.
Audit setup -> Load fictional demo files -> keep 2026-09-30 -> Run audit.
Expected: 8 accounts, 7 borrowers, 18 findings, outstanding 4,650,000 INR;
6 high-priority accounts, exposure 3,550,000 INR; 1 incomplete-history account.
All 8 accounts initially need coverage review. Multiple findings do not multiply exposure.

## 2. Inputs and settings
Use the five blank CSV templates. Excel can open CSV; XLSX uses the first sheet with
headings in row 1 and values, not formulas. Dates: YYYY-MM-DD. Money: non-negative INR,
maximum two decimal places. Identifiers/source_ref are required; account IDs link inputs.
Only one branch is allowed per run. Supporting files may have headings only when unavailable;
missing records remain coverage limitations rather than clean results.

| Input | Important contents/assumptions |
|---|---|
| accounts | Account/borrower IDs, branch, CC/OD/TL, opening date, snapshot outstanding/sanction/DP, review date, margins, creditor method, bank classification |
| daily | One calendar-day row: day-end balance, credits, interest debit and effective sanction/DP |
| stocks | Statement date, stock/receivable totals, ineligible amounts, creditors and reference |
| dues | Due dates/amounts and cumulative payments allocated to each due as of audit date |
| documents | Document type, Available/Missing/Not applicable, valid-until date, reference, remarks |

Native CBS mapping, invoice-level debtor ageing and receipt appropriation are not implemented.
Preparers determine eligibility/exclusions. bank_dp must be a comparable capped amount.
This OD method assumes stock/receivable backing; other collateral-based ODs are outside scope.
The JSON controls day thresholds, tolerance and document lists. Check them against actual
sanctions/bank policy and applicable current rules. Defaults are illustrative, not certified
regulatory instructions. Changed settings require a new run; save the session first.

## 3. Inspect Calculations
Choose Drawing power, Conduct, Term dues or Accounts. Scroll the table horizontally as needed.

### DP worked example: CC001
Stock 1,000,000 - ineligible 100,000 = eligible 900,000.
Deduct creditors 200,000 before margin -> base 700,000.
Apply stock margin 25% -> stock DP 525,000.
Receivables 400,000 - ineligible 100,000 = eligible 300,000.
Apply receivables margin 40% -> receivables DP 180,000.
Total 705,000; sanction cap 1,000,000 -> capped DP 705,000.

After margin instead gives stock DP 900,000 x 75% - 200,000 = 475,000 and total 655,000.
Select the method required by sanction; neither is universally prescribed by the app.
CC002: bank DP 900,000 vs recomputed 705,000 gives difference 195,000. Outstanding
850,000 exceeds recomputed availability by 145,000. The statement is 122 days old:
obtain current evidence before treating the calculated DP as current availability.

### Conduct
The default 90-day window is July 3 through September 30, inclusive.
CC003 has 90/90 dates in excess of the lower daily sanction/DP.
CC004 has 30/90 dates: full-window conduct conclusions cannot be reached.
OD005 has zero credits and interest debits 9,000 in the supplied complete window.
Gross credit totals do not establish provenance or evergreening. Include non-business
dates; duplicate dates are rejected. Daily limits, not today's single DP, drive the test.

### Term dues
TL006: unpaid 110,000 due June 30, aged 92 calendar days, exceeding the illustrative
review-day setting. TL007: unpaid 22,000, oldest due age 15 days. TL008: September due
fully paid; October due is future and excluded. Independently verify schedule completeness,
allocations, concessions and applicable classification treatment.

## 4. Review findings
In Findings & review select a row. Read the immutable condition, source references and
evidence request. Scroll down to reviewer fields. Enter reviewer, state, disposition,
evidence assessment, branch response, auditor conclusion and recommended action.
Add proposed reporting wording when applicable. Click Save finding decision before changing rows.

Example for CC002:DP_DIFFERENCE:
| Field | Fictional demonstration entry |
|---|---|
| Reviewer | Demo auditor |
| State | Reviewed |
| Disposition | Potential reporting point |
| Evidence assessment | Fictional sanction/account source and ST02 show a difference; current statement and sanctioned method need corroboration. |
| Management response | Branch says revised DP workings and renewal evidence will be supplied. Unverified assertion. |
| Auditor conclusion | Supplied bank DP does not reconcile to selected calculation; stale data limits the current-period conclusion. |
| Recommended action | Obtain current statements, debtor ageing, DP working and creditor/margin terms; reperform before reporting. |
| Proposed reporting point | Reconcile DP to sanctioned methodology/current supporting statement; branch evidence pending. |

Reviewed means documentation completed, not bank remediation executed. Mandatory fields
cannot establish that a written conclusion is true. An amount screen is not an NPA decision.
The bank's input classification is never overwritten.

## 5. Borrower relationships
CC003 and TL007 share borrower B003. A conduct flag on CC003 creates a borrower review
on both supplied facilities. Obtain all facilities and the bank's rationale; classification
is not automatically propagated. Other branches or omitted facilities remain unknown.

## 6. Closing and account coverage
Closing & coverage shows unresolved findings/reporting points and coverage still pending.
Choose an account; enter reviewer and a population/evidence/policy assessment; click
Record account coverage. CC001 and TL008 need coverage even though neither has a finding.
Example: Fictional population, DP basis, complete supplied history and document register
reviewed; no exceptions under supplied screens. Independent completeness and authenticity
remain auditor responsibilities.
The closing banner stays pending while finding/coverage documentation is incomplete.
A documented status still requires final auditor approval and is not a bank audit opinion.

## 7. Optional AI
AI drafting -> select finding -> Preview / save evidence prompt. The pack contains
selected account/summarized workings, not the full raw transaction file.
Without API access, save the prompt, inspect it for sensitive data, use an authorized AI
tool manually, paste the response and Save pasted external AI draft. Provenance is marked
unverified; all draft text is unapproved.
With API access, enter your key/model, preview the current prompt and Generate unapproved
API draft. Confirm the exact sharing request. Separate access/charges apply; key is not saved.
The app sends identifiers, financial figures and notes, not automatically anonymized data.
No live API call was made during development. Drafts cannot change audit decisions or
bank classification. Evaluate every draft claim against evidence yourself.

## 8. Export and preserve
In Closing & coverage:
- Export Excel: overview, account coverage, findings, DP, conduct, dues, policy, source
  schedules, events, AI drafts and run metadata.
- Export HTML: open in browser; Print for PDF, preferably landscape for wide tables.
- Save session: writes applied reviews, source hashes, date and policy as JSON.
- Load session: first run the same original inputs/date/settings, then choose saved JSON.

Any byte change, changed date or policy prevents restoration. Keep original source copies.
Local JSON/events are editable and unencrypted, not a tamper-proof audit trail.

## 9. Troubleshooting
| Error | Action |
|---|---|
| No module named pip | From project folder: .venv\Scripts\python.exe -m ensurepip --upgrade |
| Missing customtkinter/openpyxl | .venv\Scripts\python.exe -m pip install -r requirements.txt |
| VS Code uses another Python | Select .venv\Scripts\python.exe |
| Unknown account/duplicate day | Correct IDs; use one daily row/account/calendar date |
| Missing headings | Use the supplied template for that schedule |
| Invalid dates/amounts | YYYY-MM-DD; non-negative money with <=2 decimals |
| Payments exceed due | Correct allocation; allocate excess elsewhere |
| Reviewed rejected | Complete reviewer/evidence/conclusion/action/disposition and reporting wording |
| Excel permission error | Close the workbook or choose a different filename |
| Session mismatch | Use original source files, audit date and policy |

## 10. Submission
Replace name/batch placeholders; complete a Windows workflow test and record the actual
application. Exclude .venv, __pycache__, secrets and real bank/customer data.
Explain which outputs are rule-based, which are optional AI drafts, and where auditor
judgment remains. Do not claim automatic RBI classification, provisions, document
verification, complete audit coverage or measured real-client accuracy.
