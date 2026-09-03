# AuditLens — project summary

**AICA Level 2 · Module C Capstone Project · Batch 104**
Submitted by CA. Rajendra Bagade, Senior Partner

---

## The problem

Every statutory audit of an Indian company begins with the same work. A trial
balance is mapped to Schedule III. Eleven ratios that the Ministry of
Corporate Affairs made mandatory in 2021 are computed, and any that moved
more than 25 per cent must be explained in the notes. Journal entries are
tested for management override under SA 240. Materiality is determined, a
sample selected, and twenty-one CARO clauses worked through.

It is identical across clients, it consumes the opening week of every
engagement, and in most firms it is done by hand in a spreadsheet that is
rebuilt each year.

## What was built

A working web application and Python engine that performs the analytical
review and produces an eleven-sheet Excel workpaper an engagement team can
put straight on the audit file.

- **Ingest** — reads trial balances and general ledgers in whatever shape the
  client's system exported them: aliased headers, Indian number formats,
  bracketed negatives, duplicate account codes.
- **Schedule III mapping** — every ledger mapped to a Division I presentation
  head, on the account code first and the ledger name second. What it cannot
  resolve it returns as `UNMAPPED` for the auditor, rather than guessing.
- **Financial statements** — the face of the Balance Sheet and the Statement
  of Profit and Loss, with an honest reconciliation when they do not tie.
- **The eleven ratios** — computed with the basis recorded, and every
  movement beyond 25 per cent flagged for the notes.
- **SA 240 testing** — six routines plus the Benford first-digit test.
- **SA 320 and SA 530** — materiality from the auditor's benchmark, and a
  monetary unit sample with the seed recorded for re-performance.
- **CARO 2020** — applicability under paragraph 1(2), and all twenty-one
  clauses pre-populated from what the books evidence.
- **Drafting** — the analytical memorandum, the ratio variance notes and the
  enquiry letter to management.

## The design decision that matters

**The engine computes; the model writes prose.** Every figure is produced by
a pure Python function with a unit test. The language model is asked only to
explain in words and to draft correspondence. It never computes, never
classifies a ledger that reaches the statements, and never concludes on a
CARO clause.

This follows from who signs the report. A Chartered Accountant does, and
every figure has to be traceable to a calculation that can be re-performed.

Three consequences visible in the application:

1. The balance sheet is reported as **not tying**, by exactly the amount
   sitting in a suspense account the engine refused to classify. A tool that
   forced the difference to a rounding line would produce statements that tie
   and are wrong.
2. The sample is computed, and then **flagged as an inefficient response**
   because it covers 51 per cent of the population — pointing the auditor to
   controls reliance or SA 520 analytical procedures instead.
3. Ratio movements are shown in **neutral colour**. Whether a fall in the
   debt-equity ratio is favourable is the auditor's judgement, not a colour
   the tool assigns.

## Where each day of Level 2 appears

| Day | Learning | In the project |
| --- | --- | --- |
| 1 | Agents, advanced prompting | Four versioned system instructions with changelogs, in `prompts/` |
| 2 | Gemini API, system instructions, model parameters, local models | The drafting layer, with an LM Studio path for confidential engagements |
| 3 | Python and core libraries | The whole engine — 13 modules, 116 tests |
| 4 | Full-stack build, PWA, deployment | An installable progressive web application |
| 5 | n8n workflow automation | Two exported workflows: a quarterly review and a journal entry alert |

## Verification

116 tests. Every one of the eleven ratios is checked against a hand-computed
figure, so a change that would alter a disclosed ratio fails in the test suite
rather than in a client's financial statements.

The suite also asserts things the arithmetic alone would not reveal — that no
SA 240 routine flags more than 10 per cent of the population, that no CARO
clause is ever concluded, and that an unmapped ledger is never guessed.

## Confidentiality

No client data is used anywhere: not in the repository, not in the sample
files, not in the demonstration video. The synthetic client, Bharat Precision
Components Private Limited, is fictitious, and defects are deliberately seeded
in it so that every routine has something real to find.

## Limitations

Schedule III Division I only; no Ind AS. It forms no opinion, concludes on no
CARO clause, determines no materiality, asserts no commercial reason for any
movement, and verifies no balance. It analyses what the books say; the audit
evidence remains the auditor's to obtain.

## Disclaimer

Machine-generated analytical output. Every figure, selection and draft
requires the review and professional judgement of a Chartered Accountant
before it is relied upon or issued.
