# 03 — Non-applicability reasoning

## Objective

Produce a **positively reasoned** conclusion where tax audit is not applicable.

This is the prompt the brief cares most about. A working paper that says only "not
applicable" evidences nothing. The reviewer needs to see which limbs were examined and why
each was satisfied — the same weight of reasoning as an applicable conclusion.

Implemented in `generateConclusion()` in `app/js/reasoning.js`.

## Inputs

1. Every evaluated test record, including the ones that did not trigger.
2. The applicable threshold and the headroom to it.
3. The constitution and nature of activity.
4. The presumptive position and the prior-year answer.

## Instructions

```
Write the conclusion for a determination where tax audit under section 44AB is NOT
applicable.

STRUCTURE
  lead          one sentence: not applicable, to whom, for which year
  body          one line introducing the findings
  reasons[]     numbered findings, each stating what was tested and why it is satisfied
  consequences[] what follows, including what has NOT been determined
  caveat        what this conclusion is subject to

RULES
1. Reason from what was TESTED, not from the absence of a trigger. Write
   "Turnover of X is within the applicable limit of Y" — never "no trigger was found".
2. One numbered reason per limb examined. Include limbs that did not arise, stating why
   they did not arise.
3. Where a cash condition FAILED but audit is still not applicable, say so explicitly and
   state that the lower threshold was applied in reaching the conclusion. Do not present a
   failed condition as a satisfied one.
4. In consequences, always include:
   - that no audit report is required on the limbs examined;
   - that section 44AA is a SEPARATE obligation and has not been evaluated;
   - that the working paper and supporting registers should be retained.
5. In the caveat, always include that claiming a presumptive scheme in a later year starts
   the lock-in condition and requires the position to be re-examined.
6. Never write that the assessee "is not required to be audited" without qualifying it to
   the limbs examined and the figures entered.

TONE: measured. This conclusion may be relied on. Do not oversell it.
```

## Expected output

A conclusion object with `lead`, `body`, `reasons[]`, `consequences[]` and `caveat`,
rendered identically on screen, in both PDFs and in the Word document.

## Validation requirements

- [ ] Every limb the engine evaluated appears in `reasons[]`. Count them against the matrix.
- [ ] A failed-but-not-decisive cash condition is stated as failed.
- [ ] The section 44AA carve-out is present.
- [ ] The lock-in warning is present.
- [ ] No sentence claims a broader clearance than the limbs examined.

## Limitations

- The conclusion covers only the modelled limbs. Anything flagged as a special condition
  appears as a review point and is **not** absorbed into this reasoning.
- It cannot confirm the completeness of the figures entered. Garbage in produces a
  well-reasoned wrong conclusion, which is why the caveat is mandatory and not optional.
