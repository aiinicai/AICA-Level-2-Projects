# 07 — Exception detection

> **Revision, 18 September 2026.** This prompt was written for the first version of the
> engine, which had a third outcome, REVIEW REQUIRED. After the legal verification the
> engine has no such outcome: a missing fact produces INFORMATION REQUIRED with a list of
> the exact inputs needed, and every complete input set produces APPLICABLE or NOT
> APPLICABLE. The prompt is kept as used; see `../legal/sources.md` for what changed.

## Objective

Propose the fact patterns where the engine should **refuse to conclude** — the conditions
that sit outside the modelled decision path.

This prompt generates candidates. The firm decides which to accept. Accepted ones become
entries in `specialConditions` in `app/js/ruleset.js`.

## Inputs

1. The limbs the engine models and the assumptions each makes.
2. The facts captured by the application.
3. The firm's own experience of where a 44AB determination goes wrong.

## Instructions

```
Propose conditions under which a tax audit applicability engine should report
REVIEW REQUIRED rather than a conclusion.

For each candidate emit:
  id, label, why the engine cannot conclude, effect, severity, note to the reviewer

effect is one of:
  review        forces REVIEW REQUIRED
  blocks-44ad   removes access to the presumptive scheme (a determination, not a refusal)
  form-3ca      affects the report form only
  tp-date       affects the return due date only

BIAS: toward listing too many. A false REVIEW REQUIRED costs a reviewer two minutes. A
missed one produces a confident wrong answer on a filed position.

COVER AT LEAST:
- turnover computed on a basis the engine does not implement (derivatives, speculative)
- income streams excluded from the presumptive scheme (commission, brokerage, agency)
- aggregation across more than one business or profession
- part-year operation
- residential status
- presumptive provisions the engine does not model
- audit obligations arising under another law
- transfer pricing
- constitutions outside the modelled categories

FOR EACH, state plainly what the reviewer must now do. A review point that says only
"requires review" is useless.

DO NOT invent a section number, a threshold or a provision to justify a candidate. Describe
the fact pattern and why the engine cannot handle it. The CA supplies the law.
```

## Expected output

An array of candidate condition objects for the firm to accept, reject or reword.

## Validation requirements

- [ ] Each accepted condition reviewed by the CA for whether it genuinely sits outside the
      engine. Conditions the engine *can* handle should be modelled, not deferred.
- [ ] Each `note` states a concrete next action.
- [ ] `effect` correct: `blocks-44ad` is a determination about eligibility;
      `review` is a refusal to conclude. Confusing them either over- or under-blocks.
- [ ] No fabricated legal reference in any note.
- [ ] Test that ticking each condition produces the intended status. The suite covers the
      derivatives and commission cases; extend it when adding conditions.

## Limitations

- The list is not exhaustive and the application says so. It cannot be, because the space
  of unusual fact patterns is open-ended.
- A reviewer who ticks nothing gets no review points. The conditions rely on the user
  recognising the fact pattern — the engine cannot detect, for example, derivatives trading
  from a turnover figure alone.
- Severity ratings are the firm's judgement, not a legal ranking.
