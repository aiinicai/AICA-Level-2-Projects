# Architecture

## The shape of it

```
                       ┌──────────────┐
   Tkinter GUI ──┐     │              │
   CLI ──────────┼────▶│   engine     │──▶ Review ──▶ docx / xlsx / html
   MCP server ───┤     │  run_review  │              evidence JSON
   n8n workflow ─┘     └──────┬───────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
    scanner.py          rules_engine.py        ai_analyzer.py
   (web evidence)     (deterministic, and    (optional, advisory,
                       authoritative)          cannot change the score)
        │                     ▲                     │
        │              questionnaire.py             │
        │             (internal practice)           │
        ▼                     ▼                     ▼
                      dpdp_catalogue.py
              (25 obligations, provisions, weights)
```

Four front ends, one engine. The desktop app, the command line, the MCP
server and the n8n workflow all call `engine.run_review`, so a result cannot
depend on which door it came through. That is what makes the scheduled
re-scan comparable with the scan a reviewer ran by hand.

## The load-bearing decision

**The deterministic rules engine is authoritative and the AI layer is not.**

The v1 tool had the opposite arrangement in intent and neither in fact: it
printed "AI Policy Analysis: placeholder (connect API key for real analysis)"
and presented it in a report as though it were analysis. That is worse than
having no AI at all, because a reader cannot tell.

In v2:

* every rating that contributes to the score comes from `rules_engine.py`,
  which applies published matchers to evidence the scanner actually captured;
* the same scan always produces the same score, so a report can be re-performed
  and defended;
* the AI layer runs afterwards, is handed the rules findings, and is used for
  quoted evidence, drafting help and naming what the reviewer still has to
  obtain;
* an AI finding that claims an obligation is met must quote a passage that
  occurs verbatim in the policy text. If it does not, the finding is rejected
  and the rejection is printed in the report;
* where the AI layer and the rules engine disagree, both are shown and the
  reviewer settles it. The tool does not resolve it silently.

## Scoring

`score = Σ(weight × credit) / Σ(weight of assessed obligations) × 100`
with credit 1.0 for met, 0.5 for partly met, 0.0 for a gap.

An obligation that could not be assessed is removed from the denominator, not
counted as met. The proportion of the catalogue that was assessable is
reported next to the score for exactly that reason: 80 over a third of the
catalogue is a thin scan, not a good school.

## Evidence and re-performance

Every run writes `~/.surakshascan/evidence/<institution>_<timestamp>.json`
containing the raw page evidence, the findings, the score and the working
paper, with anything that looks like a secret redacted. Every report prints
the name of the evidence file it was produced from. Months later a finding can
be reopened and checked against what the site actually said on the day.

## What it deliberately does not do

* It does not log in, submit forms, or touch anything behind authentication.
* It does not send email, post to an API or notify anyone.
* It does not store an API key.
* It does not say whether an institution is compliant. It reports findings
  against provisions and leaves the conclusion to a qualified person.
