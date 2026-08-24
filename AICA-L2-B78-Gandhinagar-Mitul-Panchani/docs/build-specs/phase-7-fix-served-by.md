PHASE 7 FIX — two `served_by` reporting defects. Both are honesty-of-reporting bugs.

## OBJECTIVE
Make the full suite green again by correcting how `served_by` is reported, without weakening any
governance or quota rule. Two tests currently fail.

## STEP 0 — COMPREHENSION CHECK (before writing code)
Restate, under 250 words: (a) the two defects and their root causes, (b) what each `served_by` value
must mean, (c) why mislabelling a budget-cap block as an error is a correctness problem and not a
cosmetic one. Flag any ambiguity rather than guessing.

## TOKEN CONSERVATION — HARD CONSTRAINT
Make ZERO live API calls. Do not disable `AMG_OFFLINE` or bypass the socket guard.

## DEFECT 1 — `cache_after_error` is not a valid literal
```
pydantic ValidationError: served_by
  Input should be 'live','cache','stub','fallback_after_error','blocked_by_cap','blocked_offline'
  input_value='cache_after_error'
```
`src/amg/providers/__init__.py` emits `served_by="cache_after_error"` on the demo-day path where a
live call fails and a PRE-WARMED REAL response is served from cache. That is a legitimate and
genuinely useful distinct state — keep the behaviour, add the value.

Add `cache_after_error` to the `ProviderCallResult.served_by` literal in `src/amg/models.py`
(or wherever it is defined) and to any other place enumerating these states.

## DEFECT 2 — a budget-cap block is being reported as an error
`tests/test_token_conservation.py::test_budget_cap_blocks_n_plus_one_and_registry_falls_back`
expects `served_by == "blocked_by_cap"` but receives `"fallback_after_error"`.

Root cause: the budget cap raises through the same path as a provider error, so the registry
reports it as a generic failure. **The cap block is not an error.** It is a deliberate,
successful refusal to spend quota. Reporting it as `fallback_after_error` tells the operator
something broke when nothing did — and the UI badge will then show a false failure state during
the demo. Honest provider reporting is a stated project requirement.

Fix: distinguish the cap-block from a genuine provider failure so the registry reports
`blocked_by_cap`. Use a distinct exception type (e.g. `BudgetCapReached`, separate from
`ProviderUnavailable`) or an explicit pre-flight cap check before attempting the call — your choice,
but the reported state must be correct. `blocked_offline` must likewise remain distinct from both.

The five states must mean exactly:
- `live` — a real API call was made and succeeded now
- `cache` — served from cache, no call attempted (cache hit on the normal path)
- `cache_after_error` — a live call was attempted and failed; a previously-cached REAL response was served
- `fallback_after_error` — a live call was attempted and failed; the deterministic STUB answered
- `blocked_by_cap` — no call attempted because the daily cap was reached; the stub answered
- `blocked_offline` — no call attempted because offline mode is on; the stub answered

## ALSO
Verify the Phase 7 UI provider badge renders all of these distinctly and never conflates
`cache`/`cache_after_error` (real data) with `stub`/`fallback_after_error`/`blocked_*` (synthetic).
A cached real response and a stub response are different claims and must look different.

## ACCEPTANCE
1. `.venv/Scripts/python.exe -m pytest -q` passes with 0 failures.
2. No governance, offline, socket-guard, or budget rule is weakened to achieve it.
3. Each of the six states is reachable and correctly reported; add a test for any not yet covered.

## OUTPUT CONTRACT
You CANNOT run Python (see AGENTS.md). State what you changed, which criteria you could not verify,
and confirm zero live API calls. Do not claim tests pass.
