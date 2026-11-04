# User guide

## 1. Run a fictional example

Extract the ZIP, run `install.bat` once, then `run.bat`. Load `01_salary_new_zero.json`. Its annual salary is Rs 12,75,000 with no other income. The computed new-regime taxable income is Rs 12,00,000 and its tax after rebate is zero. The old-regime tax is Rs 1,87,200. Pending evidence keeps the result conditional.

## 2. Enter annual income and claims

Use a short case reference rather than personal identifiers. Enter age at 31 March 2026. Salary includes regular pension but not family pension, and is before standard deduction. Savings and deposit amounts must be interest, not balances. Put only normal-rate income in Other.

HRA received is already part of salary; do not add it twice. Enter actual rent for the corresponding period and HRA salary (basic, eligible DA and turnover commission). Metro means Mumbai, Delhi, Kolkata or Chennai. The application takes the least of the three statutory amounts. HRA salary plus HRA received cannot exceed gross salary. Varying salary, rent or location during the year requires separate period computation and is outside the annual-input shortcut.

80C/80CCC/80CCD(1): enter only independently eligible contributions after any individual contribution/salary limits. Combined allowance is capped at Rs 1,50,000. The separate NPS field is eligible 80CCD(1B), capped at Rs 50,000; do not reuse contributions already in 80C.

80D: enter independently eligible amounts after checking payment modes and policy/member eligibility. The preventive-health-checkup sublimit of Rs 5,000 across claims must already be applied; this application does not split checkups, insurance and medical expenditure. Senior medical expenditure requires the applicable no-insurance conditions. Caps are applied for self/family and parents; mark qualifying senior status accurately. The taxpayer's own age of 60+ automatically gives the self/family senior cap. These flags cannot establish legal eligibility on their own.

Self-occupied loan: enter eligible interest, not principal. Rs 2 lakh needs qualifying acquisition/construction, loan/date/completion conditions and interest certificate. Otherwise choose Rs 30,000 where legally eligible. Do not enter let-out property or assume both rent/HRA and a housing claim are automatically permissible. A loss requiring carry-forward is blocked. New-regime housing loss setoff is not allowed here.

Credits are verified TDS/TCS/advance/self-assessment tax. Credits do not change which regime has the lower tax. Positive balance is indicative payable and negative balance indicative refund; interest/fees/reliefs are excluded.

## 3. Complete the eligibility tab

The first four gates must be true for a computation. Do not tick them simply to bypass a blocker. Check income completeness, evidence and election separately. A form flag only suggests ITR-1 as a candidate; confirm all portal rules. Readiness is a list of pending steps, not a statutory filing-obligation assessment.

## 4. Calculate and review

Both regimes show exemptions, salary income, property setoff, GTI, aggregate Chapter VI-A allowance, rounded taxable income, slab tax, rebate, marginal relief, cess, tax and credit balance. Chapter VI-A buckets are individually capped first, then the total is restricted to GTI. Excess amounts do not create negative taxable income.

Hypothetical scenarios fill available 80C and/or additional-NPS caps and show the incremental contribution and old-regime tax reduction. They do not prove eligibility. FY 2025–26 has ended: these scenarios do not authorise backdated investments or new claims in that year.

Open `02_hra_old_advantage.json`: old tax Rs 2,02,800; new tax Rs 2,95,100; difference Rs 92,300. This shows why a selector should calculate both regimes instead of always favouring the new one. Review the sample's HRA and housing assumptions.

Open `03_marginal_relief.json`: new taxable income Rs 12,10,000, slab tax Rs 61,500, marginal relief Rs 51,500 and final tax including cess Rs 10,400. Open example 05 to demonstrate a blocked unsupported case.

## 5. Optional AI explanation

Click Preview AI prompt. Read the exact anonymous figures and pending checks. Either Copy prompt into an AI tool and replace the prompt preview with the returned draft, or supply an API key and a model available to your account and click Generate AI draft. Approve sending the previewed data only if appropriate. API use is optional and may incur charges. No model is preselected, and no API key is written into profiles or reports. Changing financial facts discards an old draft on recalculation; an in-flight response is discarded if facts changed.

AI text is unapproved even if persuasive. Check every figure and claim. The model cannot change the engine. The key is held in the running application's memory; close the application after use.

## 6. Export the working paper

Enter reviewer, chosen regime (`Old`, `New` or `Pending`), and reasons/evidence references. Choosing Old requires confirmed old-regime election. If evidence or filing legality is uncertain, use Pending. Export Excel. It contains eight sheets: Comparison, Slabs, Claims, Scenarios, Inputs, Review, AI draft and Notes. Pending checks remain visible even if a reviewer selects a regime. This does not mark the return as ready to file.

Save profile stores financial inputs/checklist answers for reopening; it does not store the API key, AI text or reviewer notes. Export Excel to preserve the review record. Recalculate after any changes; changing input invalidates the prior decision and draft. Export a fresh workbook rather than annotating an obsolete calculation.

## 7. Complete actual filing separately

Review portal prefill against Form 16, AIS/TIS, 26AS and certificates; confirm form, election, deadlines and omitted interest/fees/reliefs. Upload nothing from this application as a portal return. Complete filing and e-verification through the official system after professional review.
