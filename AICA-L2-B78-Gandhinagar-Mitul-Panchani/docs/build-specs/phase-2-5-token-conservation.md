PHASE 2.5 — Token conservation. Free API quota must be protected for the live demo.

Read AGENTS.md, ARCHITECTURE.md and MILESTONE.md in the working directory first.

## STEP 0 — COMPREHENSION CHECK (do this before writing any code)

Output a numbered restatement, in your own words, of:
(a) every file you will create or modify,
(b) every one of the 6 acceptance criteria at the bottom of this document,
(c) the single most important constraint in this task, and why it exists.

Keep it under 400 words. Then proceed to implement. If anything in this spec is ambiguous or
conflicts with AGENTS.md, say so explicitly in that restatement rather than guessing silently.

## WHY THIS TASK EXISTS

The project uses free-tier API quota:
- **Voyage**: 200M tokens, one-time grant. Effectively unlimited at demo scale (~500 tokens/run).
- **Gemini**: ~1,500 requests/DAY, 60/min. One full demo run is ~40 calls. This is the scarce one.

The risk is NOT the demo. It is development: a test suite that hits live APIs, run 50 times while
iterating, burns 2,000 calls and destroys the daily quota. **This already happened** — see
MILESTONE.md: the suite was making real Voyage calls, which caused a hang and flaky results.

The user's decisions:
- **Development (Phases 3-6): fully offline.** Zero live API calls. Governance logic is
  provider-independent, so stub/local proves it just as well.
- **Demo: live calls, with a pre-warmed cache as fallback**, so a wifi drop or 429 mid-demo serves
  a real cached response instead of stalling.

## PART A — Fix the two known test failures

**A1.** `tests/test_phase2.py::test_6b_genuine_qualification_is_approved_and_tagged` fails:
`assert 'ca_qualification' == 'professional_qualification'`. The stub's `subject_key` for a CA
qualification disagrees with the test. Align them — prefer `professional_qualification` (it is what
docs/demo-persona.md specifies) and make the stub normalize CA/CPA/degree/certification mentions to
that key.

**A2.** `tests/test_phase2.py::test_registry_falls_back_offline_and_reports_actual_backends` fails
`assert 1024 == 256` because the real Voyage provider served the call. Part B fixes the root cause.

## PART B — Hard offline enforcement (the core of this task)

### B1. `AMG_OFFLINE` kill switch — `src/amg/config.py`
Add `offline: bool` to `Settings`, from `AMG_OFFLINE` (accept `1/true/yes`, case-insensitive).
**Default `True`.** Live providers may only be constructed when it is explicitly `False`.
When offline, `resolved_llm_provider()` / `resolved_embed_provider()` return `stub` / `local`
regardless of whether keys are present. Log once at startup which mode is active.

### B2. Socket guard — `tests/conftest.py`
This is the real guarantee; configuration alone already leaked once.

An `autouse=True`, session-or-function-scoped fixture that patches `socket.socket.connect` and
`socket.create_connection` to raise `AssertionError("Test attempted network access to <addr>")`
for any non-loopback address. Allow `127.0.0.1` / `::1` / `localhost` so FastAPI's TestClient still
works in Phase 7. Also set, for every test: `AMG_OFFLINE=1`, `AMG_LLM_PROVIDER=stub`,
`AMG_EMBED_PROVIDER=local`, and delete `GEMINI_API_KEY` / `VOYAGE_API_KEY` from the environment.
Clear the `get_settings()` cache before and after each test so nothing leaks between tests.

Add a test that deliberately attempts an outbound connection and asserts the guard fires — the
guard itself must be proven, not assumed.

### B3. Response cache — `src/amg/providers/cache.py`
Disk cache so repeated identical calls cost nothing.
- Location `.amg_cache/` at repo root (add to `.gitignore`).
- Key: `sha256(provider|model|method|canonical_json_of_inputs)`. One JSON file per key, or a single
  SQLite file — your choice, but it must be inspectable and safe under repeated runs.
- Modes via `AMG_CACHE_MODE`: `read_write` (default), `read_only`, `off`, `refresh`
  (ignore existing entries, call live, overwrite — used to pre-warm before the demo).
- Applies to BOTH LLM and embedding providers.
- Never cache a failed/errored response.
- The cache stores real provider responses only. It must never be populated from stub output —
  a cached stub answer masquerading as a live one would be exactly the dishonesty AGENTS.md forbids.
  Record `served_by` in each entry.

### B4. Budget ledger + hard cap — `src/amg/providers/budget.py`
- Ledger file `.amg_usage.json` at repo root (gitignored): per UTC date, per provider, per model —
  call count and token count where the API reports it (Voyage returns `total_tokens`).
- `AMG_DAILY_LIVE_CALL_CAP`, default **100**. Counts only genuine live calls (cache hits and stub
  calls do not count).
- On reaching the cap: log a clear warning, raise the distinct `BudgetExceeded` control-flow
  signal, and let the registry fall back to stub/local. Never hard-crash — the demo must degrade,
  not die.
- `budget_report() -> dict` for the UI/CLI: calls used today, cap, remaining, per-provider totals.

### B5. Honest provider reporting — `src/amg/providers/__init__.py`
Extend the existing provider report so every call records how it was served:
`live` | `cache` | `cache_after_error` | `stub` | `fallback_after_error` |
`blocked_by_cap` | `blocked_offline`,
plus the actual model used. The Phase 7 UI will display this. It must never show "live" for
anything that was not a real API response.

### B6. CLI visibility — `check_env.py` at repo root
A small script (offline-safe, makes no API calls) that prints: offline mode on/off, resolved LLM and
embedding providers, whether each key is present (never print key values), cache mode, cache entry
count, and today's budget usage vs cap. This is the pre-demo sanity check.

## PART C — Live validation, opt-in only

`tests/test_live_providers.py`, marked `@pytest.mark.live`, skipped unless
`AMG_RUN_LIVE_TESTS=1` AND `AMG_OFFLINE=0`. Register the `live` marker in `pytest.ini` and add
`-m "not live"` to `addopts` so it can never run by accident. It should make at most **3** total API
calls (one Gemini, one Voyage, one cache-hit assertion) and assert the budget ledger incremented.

Also add the Gemini model fallback chain from MILESTONE.md defect 3: ordered
`settings.gemini_model` → `gemini-3.5-flash` → `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite`,
de-duplicated. On 429/404 for a model, log and advance; remember the working model for the process
so it does not re-probe. Exhausting the chain raises `ProviderUnavailable`.
**Do NOT use `gemini-3.7-flash`** — verified to return 429, it is not free-tier eligible.
All `gemini-2.5-*` models return 404 (retired).

## PART D — Also fix defect 1 from MILESTONE.md
`src/amg/config.py::_load_environment` uses `Path(".env")`, which resolves against the current
working directory. Running from anywhere but the repo root silently misses the keys and falls back
to stubs while still reporting the configured provider. Resolve the repo root from
`Path(__file__).resolve().parents[2]` and load `<root>/.env`. Keep `override=False`. Add a test that
chdir's to a temp directory and asserts settings still load.

## ACCEPTANCE CRITERIA — all six must hold

1. `.venv/Scripts/python.exe -m pytest -q` passes **100%** with zero failures.
2. The full suite makes **zero** outbound network connections, proven by the socket guard, even
   though `.env` contains real working keys.
3. A test proves the socket guard itself fires on an attempted outbound connection.
4. `AMG_OFFLINE` defaults to true; live providers cannot be constructed unless explicitly disabled.
5. The budget cap demonstrably blocks the (N+1)th live call and falls back rather than crashing —
   test this with a mocked/faked live provider, NOT by making 100 real calls.
6. `check_env.py` runs offline and reports mode, providers, key presence, cache and budget state.

## CONSTRAINTS
- **Make no real API calls while implementing or testing this task.** Not one. Use fakes/mocks.
- Do not weaken any P0 governance rule for convenience.
- `.gitignore` must cover `.amg_cache/` and `.amg_usage.json`.
- There is NO `python` on PATH — use `.venv/Scripts/python.exe`.

## FINISH BY
Running `.venv/Scripts/python.exe -m pytest -q` and pasting the REAL output showing 0 failures, then
running `.venv/Scripts/python.exe check_env.py` and pasting its real output. Then state, in one
short paragraph, how many live API calls your work consumed (the answer must be zero) and how you
verified that.
