# Evaluation

This folder contains the repeatable evaluation workflow for the 20 fictional findings.

## Run

From the AuditSense project directory:

```text
python evaluation/evaluate.py
```

The script requires a locally configured `OPENAI_API_KEY`. It writes:

- `results.json` — per-finding model output and comparison fields
- `summary.md` — aggregate diagnostic metrics

Use `python evaluation/evaluate.py --limit 3` for a small smoke test before running the full set.

## Metrics

- Exact overall-status match
- Exact weakness-set match for the five finding elements
- Unsupported-claim detection count
- API or processing errors

These are evaluation aids, not audit conclusions. The auditor must verify every result.
