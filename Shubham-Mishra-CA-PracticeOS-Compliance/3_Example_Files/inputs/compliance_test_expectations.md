# Agent 3 test fixtures — expected results

These notes live here (not inside the document files themselves) so the drafted
documents stay realistic plain text, with no meta-commentary that could leak into
the compliance agent's keyword self-check.

| File | Document type | Deliberately missing | Expected overall |
|---|---|---|---|
| `sample_engagement_letter_complete.txt` | Engagement Letter | Nothing — all 5 clauses present | PASS |
| `sample_engagement_letter_missing_fees.txt` | Engagement Letter | Fees clause, Limitations clause | FAIL |
| `sample_engagement_letter_missing_scope_and_responsibilities.txt` | Engagement Letter | Objective/Scope, Client & Firm Responsibilities, Limitations (no deliverable stated either) | FAIL |
| `sample_net_worth_certificate_missing_udin.txt` | Net Worth Certificate | UDIN field, Membership Number field | FAIL |

Run against all four with:

```bash
python src/run_agent3_on_samples.py
```
