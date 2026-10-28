# greytHR Payroll Reconciliation Tool: test report and bug fixes

## Version 2.1 changes (14 Oct 2026)

**1. Indian number format.** Every amount in the workbook and on screen now uses Indian grouping, for example 4,81,68,536 and -28,04,386.
- Positive amounts use an Excel crore/lakh number format.
- Excel number formats cannot also cover negative lakhs and crores, so negative amounts get the same grouping, in red, through conditional-formatting rules.
- This works without depending on the Windows region setting.

**2. Dashboard (new first sheet) for top management.**
- **Overall result.**
- **Seven key assertions**, each marked ✔/✘ with its evidence:
  - closing pay agrees with the register to the rupee;
  - every rupee of movement is explained;
  - headcount is explained;
  - each employee's pay adds up;
  - totals agree with greytHR's grand-total row;
  - no duplicate or invalid records;
  - the figures agree with an independent recalculation.
- **Key figures** for both months: headcount, gross, deductions, net, averages, TDS, PF, bonus and one-time payments, arrears.
- **Key ratios:**
  - deductions, take-home, TDS, PF and one-time payments as % of gross;
  - gross growth;
  - attrition and hiring rates;
  - % of employees whose pay changed.
- **"What moved gross payroll"**, a table with each driver's amount and % of opening gross (the bar chart was removed in v2.1.1 because it was incomplete).
- **The five largest individual movements.**
- **Items for attention.**

All figures are formulas linked to the detailed sheets.

**3. Saved pay registers.**
- Registers you upload are kept, per client, in a "Payroll Register Library" folder next to `app.py` when you run a reconciliation. An exact copy is stored, and the same file is never stored twice.
- A **📂 Saved** button next to each file chooser lists that client's saved registers, newest first.
- A "Manage saved registers" panel lists everything stored and can delete a saved copy.
- A saved file that has been changed on disk is refused.

**Tests:** 36 of 36 passed. Six tests were added for the dashboard values, Indian formatting, month sorting and the library (save, de-duplicate, read, delete, tamper check). The screen was tested end to end: upload, save, open a fresh session, pick both months from 📂 Saved, run, download.

Everything below is the version 2.0 report.

---

# Version 2.0: test report and bug fixes

Tested on 13 Oct 2026 against the supplied files:
- `Salary Statement-August 2026.xls`
- `Salary Statement-September 26.xls`

Both are genuine Excel 97–2003 files, and neither was modified.

## 1. Result on the supplied files

| | August 2026 | September 2026 |
|---|---|---|
| Employees (excluding the grand-total row) | 187 | 194 |
| GROSS (sum of employees = greytHR grand-total row) | 5,09,42,601 | 4,81,68,536 |
| Total deductions (positive) | 1,12,36,493 | 1,03,57,111 |
| NET PAY (sum of employees = greytHR grand-total row) | 3,97,06,108 | 3,78,11,425 |

**Source data checks** (zero tolerance, every employee, both months):
- Earning components = GROSS for 381 of 381 employee-months.
- Deduction components = −TOTAL DEDUCTIONS for 381 of 381.
- GROSS − deductions = NET PAY for 381 of 381.
- Every amount column agrees with the greytHR grand-total row: 36 columns in August, 34 in September.
- No duplicate IDs, no invalid amounts and no blank amounts.

The source data is internally consistent. Every failure the old app reported came from the app, not from the data.

**Headcount:** 187 + 9 joiners − 2 leavers = 194. Difference 0.
- Joiners: 8873, 8951, 8978, 8980, 8990, 8991, 8992, 9000, 9011.
- Leavers: 1548, 2739.

**Gross bridge**

| Line | ₹ |
|---|---|
| August gross | 5,09,42,601 |
| Add: joiners | 11,37,925 |
| Less: leavers | −28,04,386 |
| Add: continuing employees (185) | −11,07,604 |
| **Calculated September gross** | **4,81,68,536** |
| Actual September gross | 4,81,68,536 |
| **Difference** | **0** |

The continuing employees' change of −11,07,604 breaks down as follows. The unexplained remainder is 0.

| Category | ₹ |
|---|---|
| Regular salary: structure change | 20,790.53 |
| Regular salary: paid-days impact | 3,935.47 |
| Arrears | −84,204 |
| Bonus / one-time | −8,79,241 |
| Reimbursement / variable | −1,68,885 |

**Net bridge**

| Line | ₹ |
|---|---|
| August net | 3,97,06,108 |
| Add: joiners | 10,17,499 |
| Less: leavers | −22,72,182 |
| Add: continuing employees | −6,40,000 |
| **Calculated September net** | **3,78,11,425** |
| Actual September net | 3,78,11,425 |
| **Difference** | **0** |

The continuing employees' net change is the gross change of −11,07,604 less the change in deductions of −4,67,604. The deduction change splits by component: income tax −4,44,343, other deduction −38,691, VPF +19,998, and so on. The unexplained remainder is 0.

**Component level:**
- All 27 earning components and 8 deduction components reconcile from the August total to the September total with a difference of 0.
- Components in August only: GRATUITY, Excellence Award, SDM SDE Bonus, OTHER DEDUCTION.
- Components in September only: REFERRAL BONUS, Recognition Bonus.

**Exceptions (no threshold):**
- 133 of the 185 continuing employees have at least one non-zero movement, covering 223 component lines. All are listed.
- 52 employees have no movement at all and are correctly not listed.

**Review items raised. These are not failures.**
- **7945:** marked Left? = True in August with 1 paid day. Their Join Date changes from 05 Jan 2026 to 07 Sep 2026, so this looks like a re-hire under the same Employee No.
- **5821, 8621, 8706:** marked Left? = True in September, so they are expected to drop out in October.

**Overall: FULLY RECONCILED.**
- Every Excel formula was recalculated in LibreOffice and compared with the independent Python calculation. Every "Agrees?" cell reads Yes.
- There are 0 formula errors.

## 2. Automated tests: 30 of 30 passed

Run with `python -m pytest -v tests` from the app folder.

**Real files:**
- Column detection.
- Tracing the old ₹5,000 gap.
- Counts and matching.
- Employee-level checks.
- Bridges against figures computed separately with pandas.
- Continuing movements.
- New and missing components.
- Review items.
- `.xls` vs `.xlsx` (with 3 title rows added) vs `.csv` (amounts with commas) give identical results.
- Workbook formulas recalculate with no errors and all "Agrees?" cells read Yes.
- Source files unchanged.

**Synthetic cases:**
- A ₹0 difference passes.
- A ₹1 GROSS variance is reported and fails.
- A ₹0.01 net variance is reported and fails.
- A ₹1 movement is listed.
- An unchanged employee is not listed.
- Signed and positive deduction conventions.
- Joiners and leavers.
- New and removed components.
- Duplicate IDs are kept, flagged, and the bridge still ties.
- Invalid text amounts are flagged, never silently set to zero.
- Blank amounts are reported.
- Leading-zero and numeric IDs.
- Heading below title rows.
- Tampered grand-total row.
- Missing required column, with the found headings listed.
- Names are used when present and never invented.
- LOP split with no double counting.
- Same month labels are rejected.
- A failure shows as NOT RECONCILED in the workbook.

The Streamlit screen was also driven end to end in a browser: upload, Run, dashboard showing FULLY RECONCILED, workbook download.

## 3. Bugs found and fixed

Each item states what the old app did, the evidence from the supplied files, and the fix.

**1. The ₹5,000 "earnings below gross" (items A and B).**
The old rule treated any heading *containing* the letters "lop" or "days" as an attendance column. "PROFESSIONAL DEVE**LOP**MENT" and "PROFESSIONAL DEVELOPMENT Arrears" were therefore dropped from earnings.
- **Evidence:** for employee 1198 in August, GROSS is 4,69,343 and PROFESSIONAL DEVELOPMENT is 5,000. The old earnings sum was 4,64,343. All 267 earnings failures equal exactly the employees with that allowance (133 in August, 134 in September).
- **Fix:** information columns are now matched on the exact heading, never on part of a word. Every earning column is listed in the Data Checks "Column coverage" table.

**2. Deductions check compared positive components with negative TOTAL DEDUCTIONS (item C).**
It failed for every employee.
- **Fix:** the sign convention is detected per file (here, NEGATIVE), deductions are used as positive amounts, and the convention is documented on the Summary and Net sheets.

**3. Net check computed GROSS − (negative deductions) (item D).**
This added the deductions instead of subtracting them.
- **Fix:** Net = GROSS − deductions (positive), checked with zero tolerance.

**4. Leavers counted with the wrong sign (items E and F).**
The Gross sheet held leavers as −28,04,386 and the Summary formula subtracted that again, so leavers were *added* back.
- **Evidence:** the old "Gross Difference" was 56,09,578. That is 2 × 28,04,386 plus ₹806 of PROFESSIONAL DEVELOPMENT Arrears movement lost through bug 1.
- **Fix:** leavers appear once as a negative line and the bridge is a straight SUM.

**5. Net bridge sign error.**
The change in signed deductions (+4,67,604) was subtracted, so the net movement was wrong in the opposite direction.
- **Evidence:** the old "Net Difference" was −9,35,208, which is 2 × 4,67,604.
- **Fix:** the deduction change is worked out on positive amounts and broken down by component.

**6. Wrong employee names (item G).**
Names in the component tables were looked up by position in a list that had already been re-sorted. For example, employee 8839 was labelled "Employee 8768". Names were also invented ("Employee 1198") when the export had none.
- **Fix:** the export has no name column, so names are left blank and the sheets say "not in export". No names are made up.

**7. Join Date shown as "Department" (item G).**
When no department column existed, the first information column, Join Date, was used.
- **Fix:** each field keeps its own label: Join Date, Left?, Status, Days in month, Effective workdays, LOP. There is no Department column because the export doesn't have one.

**8. Thresholds removed.**
The ₹ and % threshold inputs and every use of them are gone. The old 0% setting also marked all 185 employees "major", including 52 with no movement at all.
- **Fix:** every non-zero movement is now listed and unchanged employees are not. The ₹1 tolerance in the old checks has also been removed.

**9. Silent zeros and overwrites.**
Invalid amounts became 0 without a message, and a repeated Employee No overwrote the earlier record.
- **Fix:** both are now reported as FAIL. Duplicates are kept and shown separately in the bridges.

**10. New and renamed components (item H).**
The Column Map listed only August's columns, so REFERRAL BONUS and Recognition Bonus never appeared.
- **Fix:** the column map covers both months, side by side, with how each column was classified. Components present in only one month are flagged.

**11. Classification by position only (item I).**
- **Fix:** columns are now classified by name lists first, with position only as a fallback, which is flagged "review".
- Arrears, bonus / one-time, reimbursement / variable and regular salary are separated.
- Paid-days impact is calculated from EMP EFFECTIVE WORKDAYS ÷ DAYS IN MONTH. The structure change is the remainder, so nothing is counted twice.

**12. Parser.**
- **Fix:** the heading row is now detected (up to row 30). The grand-total row is excluded and used as a cross-check. Rows without an Employee No are reported. Repeated headings are kept. The old app silently fell back to row 1 if the heading row wasn't found.

**13. Workbook formulas.**
The old Summary mixed formulas with hard-coded totals, and its Gross sheet had stray `=C1-C2` cells.
- **Fix:** every bridge line is now a formula linked to the detail sheets. Each line also carries a separate Python figure and an "Agrees?" check.

**14. Success message.**
The old app said "completed successfully" even when checks failed.
- **Fix:** the screen now shows FULLY RECONCILED or NOT FULLY RECONCILED from the actual results.

**15. Launcher.**
The old launcher didn't change to the app folder, relied on `pip` and `streamlit` being on PATH, reinstalled every run, ignored errors, and could stop at Streamlit's first-run e-mail question.
- **Fix:** all of these are fixed.

## 4. Limits to know

- **The workbook is calculated by Excel when it opens.** The library that writes it cannot store calculated values. If Excel opens it in Protected View, the formula cells look empty until you click **Enable Editing**. Excel may also ask to save changes when you close it; that is normal.
- **The paid-days split** is an analysis, not a greytHR figure. Pro-rated employees can show a few rupees or paise of "structure change" because of greytHR's rounding. For example, employee 5821 shows ₹0.40.
- **Category lists** (regular / one-time / variable) are at the top of `app.py`. Any new component not in the lists is placed by keyword and marked "review" on the Column Mapping sheet.
