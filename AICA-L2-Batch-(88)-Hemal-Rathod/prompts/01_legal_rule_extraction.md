# 01 — Legal rule extraction

> **Revision, 18 September 2026.** This prompt was written for the first version of the
> engine, which had a third outcome, REVIEW REQUIRED. After the legal verification the
> engine has no such outcome: a missing fact produces INFORMATION REQUIRED with a list of
> the exact inputs needed, and every complete input set produces APPLICABLE or NOT
> APPLICABLE. The prompt is kept as used; see `../legal/sources.md` for what changed.

## Objective

Convert a statutory provision **that the Chartered Accountant has already read from a
primary source** into a structured, machine-evaluable test specification.

This prompt structures law that a human supplies. It never recalls law.

## Inputs

1. The verbatim text of the provision, pasted by the user from the bare Act.
2. The Assessment Year and the Finance Act amendment it reflects.
3. The citation of the source consulted.
4. The names of facts already captured by the application.

## Instructions

```
You are assisting a Chartered Accountant to convert a provision of the Income-tax Act
into a structured test specification for a deterministic rule engine.

CONSTRAINTS — these override every other instruction:

1. Work ONLY from the provision text supplied below. Do not add, complete or correct it
   from your own knowledge. If the text appears truncated, say so and stop.
2. Do not state any threshold, rate, percentage, period or date that is not present in
   the supplied text. If a figure is needed but absent, emit null and list it under
   "requires human input".
3. Do not cite any other section, rule, circular, notification or case unless it is named
   in the supplied text.
4. Where the provision is capable of more than one reading, produce BOTH readings and
   mark the entry "interpretive choice required". Do not pick one.

TASK

Produce a JSON test specification with:
  id, label, provision, appliesWhen, measures, threshold, comparison,
  boundaryTreatment, triggersAudit, dependsOn, cannotConcludeWhen,
  requiresHumanInput[], interpretiveChoices[]

Rules:
- "comparison" must be one of: exceeds, atOrBelow, equals, withinPercentage.
- "boundaryTreatment" must state explicitly what happens at exact equality.
- "cannotConcludeWhen" must list every fact pattern where the test cannot be evaluated.
  Prefer listing too many: the engine reports REVIEW REQUIRED for each, which is safe.
- "dependsOn" names other tests whose outcome changes this one's threshold.

PROVISION TEXT (supplied by the user, read from the bare Act):
<<<
{paste}
>>>
ASSESSMENT YEAR: {ay}
SOURCE CITATION: {citation}
```

## Expected output

A JSON object matching the test-record shape consumed by `app/js/engine.js`, plus two
lists: figures the human must supply, and points where the provision admits more than one
reading.

## Validation requirements

Before any output is used:

- [ ] **Every figure** in the output traced back to the supplied text. Any figure not in
      the text is a fabrication — reject the whole output, do not patch it.
- [ ] `boundaryTreatment` checked against the wording. "Exceeds" and "is more than" mean
      equality does not trigger; the engine's `calc.exceeds()` implements that.
- [ ] Each `interpretiveChoices` entry resolved by the CA, and the resolution recorded in
      `legal/sources.md`.
- [ ] `cannotConcludeWhen` reviewed for completeness. A missing entry means the engine
      will produce a confident answer where it should have asked for review.
- [ ] Citation recorded in `legal/sources.md` with the date accessed.

## Limitations

- The model cannot tell you whether the provision you pasted is the one currently in force.
  Currency of the text is entirely the human's responsibility.
- It cannot resolve an interpretive choice. It is instructed to surface both readings, and
  L-01 in `documentation/limitations.md` is an example of one left open on purpose.
- Output structure is reliable; legal judgement in it is not. Treat it as a first draft of
  a specification, not as advice.
