# 04 — Applicability reasoning

## Objective

Produce the conclusion where tax audit **is** applicable: which limb triggered it, by how
much, what must now be done, and by when.

Implemented in `generateConclusion()` in `app/js/reasoning.js`.

## Inputs

1. The triggering test records (there may be more than one).
2. The applicable threshold, the actual figure, and the variance.
3. The determined report form and the reason for it.
4. The due dates configured for the Assessment Year.
5. Any special conditions flagged.

## Instructions

```
Write the conclusion for a determination where tax audit under section 44AB IS applicable.

STRUCTURE
  lead           one sentence: applicable, to whom, for which year
  grounds[]      one entry per triggering limb: { provision, reason }
  consequences[] audit required, report form, report due date, return due date
  caveat         what this conclusion is subject to

RULES
1. List EVERY triggering limb, not just the first. Two independent triggers are a
   materially different position from one, and the reviewer needs to see both.
2. For each ground, state the provision, the measured figure, the threshold, and the
   variance in rupees. "Exceeds the limit" without the amount is not enough.
3. Where the trigger is the low-profit limb, state that it operates WITHOUT any turnover
   threshold, and state the lock-in consequence for the following assessment years.
4. Where the exemption limit applied is nil because of the constitution, say so and say
   that any positive total income therefore clears it.
5. Name the report form and say WHY that form follows.
6. Quote the due dates exactly as configured. Never compute or infer a date.
7. Where a special condition is also flagged, do not fold it into the grounds. It goes to
   review points, because it may change the computation rather than the conclusion.

TONE: direct. This creates an obligation with a deadline. Say so plainly.
```

## Expected output

A conclusion object with `lead`, `grounds[]`, `consequences[]` and `caveat`.

## Validation requirements

- [ ] `grounds[]` length equals the number of test records with `triggersAudit === true`.
- [ ] Each ground carries provision, figure, threshold and variance.
- [ ] Due dates match `ruleset.dueDates` character for character — and see the warning in
      `legal/sources.md` that those dates are unverified and frequently extended.
- [ ] The form reason is present and correct for the other-law position.
- [ ] Lock-in consequence stated wherever the low-profit limb triggered.

## Limitations

- The engine treats a breach as decisive even where another limb is unresolved. That is
  deliberate — an unresolved limb can only add a further trigger, never remove an existing
  one — but it means an APPLICABLE result can still carry open review points.
- Due dates are configuration, not computation. If a notification extends a date, the
  ruleset must be edited; the model has no way to know.
