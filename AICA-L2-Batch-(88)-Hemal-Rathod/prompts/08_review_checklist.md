# 08 — Review checklist and QA matrix

## Objective

Produce (a) the checklist a senior works through before signing the working paper, and
(b) the boundary test matrix that must pass before a release.

The matrix drives the suite reported in
[`../documentation/qa-test-report.md`](../documentation/qa-test-report.md).

## Inputs

1. The limbs the engine evaluates and their thresholds.
2. The validation rules.
3. The list of special conditions.
4. The output channels: screen, executive PDF, detailed PDF, Word, JSON.

## Instructions

```
PART A — REVIEWER CHECKLIST

Produce a checklist for a senior reviewing a completed working paper. Group by:
  1 Inputs      figures agreed to the books and to each other
  2 Facts       constitution, nature, presumptive eligibility, prior-year history
  3 Law         parameters verified for the year; statutory text read, not assumed
  4 Reasoning   every limb explained; nothing left unresolved without a review point
  5 Output      result consistent across every channel; sign-off complete

Each item must be checkable by looking at something specific. "Ensure correctness" is not
a checklist item.

PART B — BOUNDARY MATRIX

For every numeric threshold, generate cases at:
  exactly the threshold        one unit above        one unit below
For every percentage ceiling:
  exactly the ceiling          just above            zero

Also cover:
  - each tri-state answer (yes / no / not known) on both presumptive questions
  - every constitution
  - both natures of activity
  - each validation error: negative amount, cash exceeding total, missing mandatory field
  - each special condition
  - form determination in all three variants
  - all three themes
  - the executive sheet fitting one page FOR EVERY sample case

For each case state the input, the expected status and WHY. The "why" is what makes a
failing test diagnosable instead of merely red.
```

## Expected output

A grouped reviewer checklist, and a machine-runnable boundary matrix.

## Validation requirements

- [ ] Every threshold in `ruleset.js` has all three boundary cases. Count them against the
      parameter list.
- [ ] Expected statuses derived from the provision, not from running the engine and
      recording what it did. A test written from the code cannot detect a bug in the code.
- [ ] Page-count assertions are real measurements of generated PDFs, not estimates.
- [ ] Checklist items each name a specific artefact to look at.

## Limitations

- The suite tests that the engine implements the ruleset. It cannot test that the ruleset
  is the law — that is what `legal/sources.md` is for, and it is a human task.
- Passing tests say nothing about limbs that are not modelled at all.
- The theme checks confirm tokens resolve and contrast is present; they are not a
  substitute for looking at the three modes.
