# Rule register and scope decisions

Rules checked against Income Tax Department sources on 16 October 2026. Version 1 fixes AY 2026–27 (FY 2025–26); it does not calculate another year by substituting a year label. Recheck legislation, notifications and filing instructions before production use.

| Rule | Implementation |
|---|---|
| New slabs | 0–4 lakh nil; next 4 lakh 5%; next 4 lakh 10%; next 4 lakh 15%; next 4 lakh 20%; next 4 lakh 25%; above 24 lakh 30% |
| Old slabs | Adult basic exemption 2.5 lakh; resident senior 3 lakh; super senior 5 lakh; remaining relevant bands 5%, 20%, 30% |
| Standard deduction | Salary capped at 50,000 old / 75,000 new |
| Rebate | Old: eligible resident total income up to 5 lakh, maximum 12,500. New: up to 12 lakh, maximum 60,000 |
| New marginal relief | Above 12 lakh, reduce slab tax to income exceeding 12 lakh when the former is greater; before cess |
| Cess | 4% after rebate/marginal relief; surcharge excluded by gross-income scope cap |
| HRA | Old only: minimum of actual allowance, rent less 10% qualifying salary, or 50%/40% qualifying salary; zero floor |
| 80C group / NPS additional | Old only: aggregate 1.5 lakh / separate eligible 50,000; no double counting |
| 80D | Old only: eligible self/family 25,000 or 50,000; parents separately 25,000 or 50,000; eligibility prechecked |
| Interest deductions | Old only: eligible savings up to 10,000 under 80TTA; resident senior eligible savings/deposits up to 50,000 under 80TTB; mutually exclusive |
| Self-occupied interest | Old only: eligible 2 lakh or 30,000 cap, available-income restriction; carry-forward cases blocked |
| Rounding | 288A total income: ignore paise then nearest 10. 288B payable/refund: ignore paise then nearest 10 of absolute amount, restore sign. Last digit 5 rounds upward |

The report displays rounded gross tax for comparison. Indicative credit balance is computed from unrounded tax including cess less verified credits, then rounded; it is not calculated by subtracting credits from an already rounded display figure. Separate omitted interest/fees can change the actual payable amount.

## Official source register

- AY-specific slabs, deductions, return applicability and nonbusiness old-regime opt-out: https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1
- Salary standard deduction and professional tax: https://www.incometaxindia.gov.in/w/income-from-salary
- New-regime marginal-relief mechanism and cess: https://www.incometaxindia.gov.in/w/computation-of-tax-for-individual-1
- HRA formula: https://www.incometaxindia.gov.in/w/what-is-the-taxability-of-house-rent-allowance-hra-
- Deductions: https://www.incometaxindia.gov.in/w/various-deductions-under-the-income-tax-act
- Total-income rounding: https://www.incometaxindia.gov.in/w/section-288a-55
- Payable/refund rounding: https://www.incometaxindia.gov.in/w/section-288b-9
- AY-specific ITR-1 validations: https://www.incometax.gov.in/iec/foportal/sites/default/files/2026-05/CBDT_e-Filing_ITR%201_Validation%20Rules_AY%202026-27.pdf

The general computation article contains an apparent stale 7-lakh reference in its AY 2026–27 rebate paragraph. This implementation follows the AY-specific official salaried page's 12-lakh / 60,000 thresholds, cross-checked against the marginal-relief mechanism. General website guidance is secondary to the applicable Act and Rules. Source links may change.

## Deliberate boundaries

Eligibility gates are taxpayer/reviewer declarations, not a residency/day-count or deduction-adjudication engine. Unsupported income is never automatically inferred from a blank amount. There is no automatic portal fetch, Form 16 OCR, government authentication, return upload or e-verification. This keeps computed recommendations reproducible within the stated scope. Wider coverage requires separately versioned rules and additional tests.
