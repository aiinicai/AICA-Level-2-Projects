# BOQ Export – TallyPrime TDL for project-wise BOQ analysis

A customised Tally Definition Language (TDL) add-on that consolidates, for a
selected project (cost centre) and period, the direct expense postings and
the item-wise material purchases recorded in TallyPrime into structured
reports that export to Excel for Bill of Quantities (BOQ) analysis.

Companion to the write-up *From Fragmented Data to Intelligent Audit
Analytics: Leveraging AI-Assisted TDL Development in Tally for Automated BOQ
Analysis*.

| | |
|---|---|
| File | `BOQ-Export.tdl` |
| Tally version | Tested on TallyPrime 7.2 (October 2026) |
| Reference | *TDL Reference Manual*, Tally Solutions, April 2017 |
| Development | AI-assisted (Claude); each build tested in TallyPrime before acceptance |

## 1. Purpose

In project-based businesses the BOQ lists each activity with quantity, rate
and amount. Comparing it with actual cost requires two kinds of data that
Tally keeps in different reports:

* direct expenses posted through Payment, Journal and Contra vouchers with a
  cost centre allocation, and
* material purchased through item-mode purchase invoices, where each stock
  item line carries a cost centre allocation.

This add-on reads both from the vouchers in one pass and presents them as a
single dataset for the chosen cost centre.

Material is identified through the cost centre allocation on each purchase
item line, not through Godowns. Where a client tracks material by Godown, a
separate variant is required.

## 2. Reports

Both reports are under **Gateway of Tally › BOQ Export**. Each opens empty;
select a cost centre and, if required, a period, then export.

**BOQ Summary – by Ledger.** One line per ledger with Debit, Credit and Net
Cost, sorted by amount, in three sections:

| Section | Content |
|---|---|
| A. Direct cost postings | Ledgers under Purchase Accounts, Direct Expenses and Indirect Expenses, posted directly to the cost centre |
| B. Item-wise purchases | Stock item lines allocated to the cost centre |
| Total cost (A + B) | |
| C. Party and other balances (memo) | Other ledgers allocated to the cost centre, excluding debtors, tax accounts and nil balances. A debit balance indicates an unsettled advance on the job. Not included in the total. |

**BOQ Detail – Voucher wise.** The same three sections voucher by voucher,
with date, voucher type and number, ledger, stock item, quantity, rate, cost
centre, debit, credit and narration. Section totals agree with the Summary.

Sub-cost centres are included when a parent cost centre is selected.
Cancelled and optional vouchers are excluded.

## 3. Installation

1. Copy `BOQ-Export.tdl` to the Tally machine.
2. In TallyPrime open Help › TDL & Add-On and add the file, or add
   `TDL = <path>\BOQ-Export.tdl` to `Tally.ini`.
3. Restart Tally. Remove any earlier copy of the add-on first to avoid
   duplicate menu items.

Cost centres must be enabled in the company and allocated on the relevant
ledgers.

## 4. Workflow for BOQ analysis

1. Open the Summary, select the project's cost centre and period, and export
   to Excel. Export the Detail as well where voucher-level support is needed.
2. Map each ledger and stock item to its BOQ activity (carpentry, painting,
   electrical and so on). The narration in the Detail usually indicates the
   activity.
3. Aggregate actual cost by activity and compare with the BOQ amount to
   arrive at profit and profit percentage.
4. Reconcile the allocated total to the Summary's total cost, and the
   Summary to Tally's own Cost Centre Break-up.

The add-on consolidates the data. Allocation to BOQ activities remains an
audit judgement and should be documented.

## 5. Maintenance

Classification rules are system formulas at the top of the file and can be
edited without changing the report structure:

| Formula | Rule |
|---|---|
| `BOQIsCost` | Purchase Accounts, Direct Expenses, Indirect Expenses (sub-groups included) – Section A |
| `BOQIsIncome` | Sales Accounts, Indirect Incomes – excluded from Section A |
| `BOQIsTax` | Duties & Taxes – excluded from Section C |
| `BOQIsOtherLed` | All other ledgers with a non-nil balance – Section C |
| `BOQVchLive` | Excludes cancelled and optional vouchers |

Group names are Tally's default names; amend them if the client has renamed
groups. Column widths are the `Width` attribute of the heading (`BOQ H …`)
and data (`BOQ F …`) fields.

## 6. Limitations

* The cost centre index used to read a single cost centre quickly
  (`Type : Vouchers : Cost Centre`) comes from Tally's default TDL rather
  than the 2017 manual and should be re-verified after a Tally upgrade.
* Selecting all cost centres reads every voucher and is slow on large
  companies; narrow the period first.
* Amounts without a cost centre allocation are not reported.
* The Detail report prints small because of its width. PDF format is
  preferred for the Summary and Excel format for the Detail.

## 7. AI-assisted development

Claude was used as an AI-assisted development tool to formulate the
reporting logic, structure the TDL code and build a report suited to BOQ
analysis. The resulting TDL generates a detailed report of the expense
postings and item-wise material information associated with a project.

The solution was developed in five stages:

1. **Understanding the audit workflow.** The information needed for BOQ
   analysis was identified, together with how expenses and material
   consumption are recorded in Tally: Cost Centre reports for expenses and
   inventory records for project-wise material.
2. **Defining the output.** The requirements were translated into one
   structured report combining both kinds of information, so that separate
   exports are no longer needed and allocation to BOQ activities is easier.
3. **AI-assisted coding.** Claude assisted in developing the TDL from these
   requirements: the report structure, the data fields, the retrieval logic
   across report definitions, collections, objects, fields and functions,
   and the tabular layout.
4. **Generating the consolidated report.** The TDL produces a single view of
   the project's expense and item-wise material details, exported from one
   report instead of several.
5. **Review and validation.** The output was checked against Tally's
   standard reports and the underlying vouchers for completeness, correct
   classification of expenses, accuracy of material details, absence of
   duplicates and agreement of totals. This validation is essential before
   the report is relied upon for audit purposes.

## 8. Conclusion

Preparing a BOQ analysis from Tally has traditionally meant exporting cost
centre and inventory reports separately and combining them in Excel, a
process repeated whenever the client's records change. This add-on brings
the project's direct expenses and item-wise material purchases into a single
set of reports for the selected cost centre and period, so that the
analysis starts from one consistent dataset and can be regenerated at any
time.

The add-on consolidates the data; it does not allocate costs to BOQ
activities. That step, together with reconciliation of the reported totals
to Tally's standard reports, remains the auditor's responsibility.
