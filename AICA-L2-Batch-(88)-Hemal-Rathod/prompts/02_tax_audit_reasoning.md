# 02 — Tax audit reasoning chain

> **Revision, 18 September 2026.** This prompt was written for the first version of the
> engine, which had a third outcome, REVIEW REQUIRED. After the legal verification the
> engine has no such outcome: a missing fact produces INFORMATION REQUIRED with a list of
> the exact inputs needed, and every complete input set produces APPLICABLE or NOT
> APPLICABLE. The prompt is kept as used; see `../legal/sources.md` for what changed.

## Objective

Turn a set of evaluated test records into an ordered reasoning chain that a reviewer can
follow from facts to conclusion, and that an article assistant can learn from.

Implemented by `generateReasoning()` in `app/js/reasoning.js`. This prompt produced the
wording conventions that function encodes.

## Inputs

1. The array of test records produced by the engine.
2. The computed ratios and the applicable threshold.
3. The overall status: APPLICABLE, NOT APPLICABLE or REVIEW REQUIRED.

## Instructions

```
Write an ordered reasoning chain for a tax audit applicability determination.

ORDER — follow the sequence a reviewer actually thinks in:
  1 Nature of activity      5 Applicable statutory threshold
  2 Turnover / receipts     6 Presumptive taxation
  3 Cash receipt ratio      7 Low-profit / lock-in condition
  4 Cash payment ratio      8 Audit under another law and report form

For each step emit: heading, measured value, provision, status, explanation.
status is one of: ok, trigger, warn, review, info.

RULES:
- State the finding, then why it matters. One or two sentences. No preamble.
- Every number quoted must come from the inputs. Never compute a new one.
- Where a step was not evaluated, say so and say why. Never omit a step silently.
- Where a step could not be concluded, use status "review" and state what fact is missing.
  Do not guess the missing fact, and do not soften the language to imply a conclusion.
- Do not use "clearly", "obviously", "simply", or any phrase asserting that a legal
  position is beyond argument.
- Do not cite a provision that is not already in the test records.

TONE: a senior speaking to a reviewer. Plain, specific, no padding.
```

## Expected output

An array of eight step objects, rendered on screen as the reasoning chain and in the
working paper as section 5.

## Validation requirements

- [ ] Eight steps present. A missing step means a limb went unexplained.
- [ ] Every figure matches the engine's computed values exactly.
- [ ] No provision cited that is absent from the test records.
- [ ] Every "review" step names the specific missing fact.
- [ ] Read the chain against the matrix: they must agree. They are rendered from the same
      records, so disagreement means a rendering bug.

## Limitations

- The chain explains the engine's reasoning. If a limb is mis-modelled, the chain will
  explain the wrong thing fluently. It is not an independent check.
- It does not cover provisions outside the engine. Those surface as review points instead.
