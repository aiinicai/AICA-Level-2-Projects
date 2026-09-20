# 06 — Working paper generation

> **Revision, 18 September 2026.** This prompt was written for the first version of the
> engine, which had a third outcome, REVIEW REQUIRED. After the legal verification the
> engine has no such outcome: a missing fact produces INFORMATION REQUIRED with a list of
> the exact inputs needed, and every complete input set produces APPLICABLE or NOT
> APPLICABLE. The prompt is kept as used; see `../legal/sources.md` for what changed.

## Objective

Assemble the ten-section working paper, and the two document variants generated from it.

Implemented in `app/js/workingpaper.js` (`generateWorkingPaper`, `renderExecutive`,
`renderDetailed`) and `app/js/export.js` (Word).

## Inputs

The complete engine result: facts, tests, conclusion, reasoning chain, reference cards,
matrix, review points, form determination, due dates, verification status.

## Instructions

```
Assemble a professional working paper in exactly ten sections:

   1 Executive conclusion          6 Section-wise legal references
   2 Assessee profile              7 Applicability / non-applicability analysis
   3 Financial data                8 Professional review points
   4 Statutory tests               9 Conclusion with sign-off
   5 Detailed reasoning           10 Disclaimer

ONE MODEL, THREE OUTPUTS
Build a single document model. The screen, both PDFs and the Word file all render from it.
Never write content into one channel that the others cannot produce — that is how a
working paper and the file copy of it come to disagree.

DOCUMENT VARIANTS
- Detailed (multi-page): all ten sections, cover page, full matrix with findings, full
  reasoning chain, all reference cards, all review points, sign-off block.
- Executive (ONE page): compose independently. Do not render the detailed paper and hide
  sections — a one-page budget must be met by deciding what earns its place.
  Carry: result, key figures, key tests, reason, two most severe review points, caveat.
  Where review points are truncated, SAY how many were omitted and where to find them.
  Omit the sign-off: the detailed paper is the document that gets signed.

MANDATORY ON EVERY VARIANT
- Firm name and "Chartered Accountants"
- Assessee, FY and AY
- The UNVERIFIED banner while ruleset verification is incomplete
- The result, stated in the same words as on screen
- A disclaimer

NEVER
- Never generate a working paper where mandatory inputs are missing. Return
  "REVIEW REQUIRED — INCOMPLETE INPUTS" instead.
- Never let the executive sheet imply it is the complete record.
```

## Expected output

A document model plus two rendered HTML documents, styled by `print.css` for A4.

## Validation requirements

- [ ] All ten sections present in the detailed paper.
- [ ] Executive sheet fits one A4 page **for every sample case** — measured, not assumed.
      The harness in `documentation/qa-test-report.md` counts PDF pages for all ten.
- [ ] Screen, both PDFs and Word state the same result and the same figures.
- [ ] UNVERIFIED banner appears on every variant while verification is incomplete.
- [ ] Export is blocked while validation is incomplete.
- [ ] No table row, reasoning step or reference card splits across a page break.

## Limitations

- Page-fit was verified against the ten sample cases. An unusually long assessee name or a
  large number of special conditions could still push the executive sheet over; re-measure
  if the content model changes.
- The Word file is HTML with Word page setup, so Word owns the final pagination. Section
  breaks and running headers are honoured; exact line breaks may differ from the PDF.
