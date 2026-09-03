# Architecture

## The governing rule

> **The engine computes. The model writes prose. Nothing else.**

Every figure that reaches a workpaper, a ratio card or the face of the
financial statements is produced by a pure Python function with a unit test.
The language model is asked for exactly two things: an explanation in words,
and correspondence. It is never asked to compute, to classify a ledger that
reaches the statements, or to conclude on a CARO clause.

This is not a stylistic preference. A Chartered Accountant signs the report,
and every figure in it must be traceable to a calculation the auditor can
re-perform.

## The pipeline

```
  Trial balance (CY)  ─┐
  Trial balance (PY)  ─┼─▶  ingest.py     validate, normalise headers,
  General ledger      ─┘                  parse Indian number formats
                                                    │
                                                    ▼
                            schedule3.py    map each ledger to a
                                            Schedule III head, by account
                                            code first, ledger name second,
                                            UNMAPPED where neither resolves
                                                    │
                                                    ▼
                            financials.py   build the face of the statements,
                                            derive the figures the ratios need
                                                    │
                    ┌───────────────┬───────────────┼───────────────┐
                    ▼               ▼               ▼               ▼
              ratios.py     materiality.py   je_analytics.py     caro.py
              11 ratios,    SA 320 + SA 530  SA 240 routines,   21 clauses,
              25% flags     sample plan      Benford            applicability
                    └───────────────┴───────────────┴───────────────┘
                                                    │
                                                    ▼
                                            pipeline.py
                                     sequences the engine, carries results
                                                    │
                        ┌───────────────────────────┼──────────────────────┐
                        ▼                           ▼                      ▼
                  report.py                    api.py                 narrate.py
              11-sheet Excel              FastAPI + PWA          Gemini drafting,
                workpaper                                       offline fallback
```

## Why the modules split this way

| Module | Holds | Deliberately does not hold |
| --- | --- | --- |
| `ingest.py` | File reading, header aliasing, Indian number parsing, tally validation | Any judgement about what a ledger is |
| `schedule3.py` | The Schedule III head list and the mapping rules | Any arithmetic |
| `financials.py` | The face of the statements and the derived figures | Any ratio definition |
| `ratios.py` | The eleven ratios and the 25 per cent rule | Where the figures came from |
| `je_analytics.py` | The SA 240 routines and Benford | Any conclusion about an entry |
| `materiality.py` | SA 320 benchmarks and SA 530 sampling | The auditor's choice of benchmark |
| `caro.py` | The 21 clauses and applicability | Any answer to a clause |
| `formatting.py` | Indian digit grouping | Everything else |
| `narrate.py` | Prompts and drafting | Every figure it quotes comes from the engine |
| `pipeline.py` | Sequencing | No audit logic of its own |

The consequence: `report.py`, `api.py` and `cli.py` all call `pipeline.py`,
so the Excel workpaper, the web application and the command line cannot
disagree with each other or with the tests.

## Failure behaviour

| Condition | What happens |
| --- | --- |
| Trial balance does not tally | Reported, with the difference. Never silently corrected. |
| A ledger cannot be mapped | Returned as `UNMAPPED` in a review queue. Never guessed. |
| Balance sheet does not tie | Reported, and reconciled against the unclassified value. |
| A ratio divides by zero | Returned as not computable, with the reason. Never zero. |
| The sample is impractically large | Computed, then flagged as an inefficient response with alternatives. |
| No API key configured | Drafting falls back to deterministic templates. The review still runs. |
| The drafting call fails | Caught. The analytical review is never taken down by a drafting failure. |

## Offline and on-premise

The whole analytical review runs with no network access. Drafting is the only
component that reaches outside, and it degrades to templates when it cannot.
For engagements where confidentiality terms rule out a third-party API, run a
local model in LM Studio and point `AUDITLENS_MODEL` at it — the analytical
result is identical either way, because the model never touches a figure.
