# Sample data

**Every figure and name in this folder is invented.** No real client information appears
anywhere in this repository.

`cases.json` is exported from `app/js/samples.js`, so the two cannot drift apart.
Regenerate after editing the cases:

```bash
node -e "global.window={};require('./app/js/samples.js');const c=global.window.TAS.samples.cases;require('fs').writeFileSync('sample-data/cases.json',JSON.stringify({document:'Synthetic demonstration cases',count:c.length,cases:c},null,2))"
```

---

## The twelve cases — AY 2026-27

Each drives a different path through section 44AB as it stands for FY 2025-26. Every
expected result was worked out by hand from the provisions before the engine was run.

| # | Case | What it shows | Result | Section |
| --- | --- | --- | --- | --- |
| 1 | Small trader within every limit | ₹60 lakh; cash figures not even needed | NOT APPLICABLE | — |
| 2 | Trader above ₹2 crore, cash above 5% | ₹1 crore limit applies; 44AD ceiling stays ₹2 crore | APPLICABLE | 44AB(a) |
| 3 | Firm relying on the ₹10 crore limit | Both cash limbs within 5%; ₹1.8 crore headroom | NOT APPLICABLE | — |
| 4 | **Trader at ₹2.5 crore declaring under 44AD** | Crosses the ₹1 crore limit, but the FA 2023 first proviso takes it outside s. 44AB | NOT APPLICABLE | First proviso |
| 5 | Doctor within 44ADA | ₹42 lakh, profit above 50% | NOT APPLICABLE | — |
| 6 | **Consultant at ₹60 lakh declaring under 44ADA** | Above ₹50 lakh, within the ₹75 lakh ceiling, declared under 44ADA(1) | NOT APPLICABLE | First proviso |
| 7 | Architects above ₹75 lakh | Beyond even the enhanced 44ADA ceiling | APPLICABLE | 44AB(b) |
| 8 | **Professional below 50%, first year** | s. 44AB(d) has no prior-year condition | APPLICABLE | 44AB(d) |
| 9 | Leaving 44AD after an earlier opt-in | ₹90 lakh turnover; 44AD used before, profit now 2.2% | APPLICABLE | 44AB(e) |
| 10 | **Firm within a 44AD(4) bar** | ₹75 lakh; barred; firm has no basic exemption | APPLICABLE | 44AB(e) |
| 11 | Company above ₹10 crore | No presumptive route; Form 3CA | APPLICABLE | 44AB(a) |
| 12 | Derivatives trader within limits | Turnover computed per the ICAI Guidance Note | NOT APPLICABLE | — |

The four in bold are the ones worth demonstrating. Cases 4 and 6 show the Finance Act 2023
change most checklists miss. Case 8 is the error the first version of this tool made, caught
when the statute was checked. Case 10 shows audit applying whatever the turnover.

---

## Using them

**In the application:** Overview panel → Sample cases → click one. It replaces everything
entered and opens the Decision panel.

**As regression fixtures:** each case carries an `expect` field, asserted by
`tests/boundary-suite.js`.
