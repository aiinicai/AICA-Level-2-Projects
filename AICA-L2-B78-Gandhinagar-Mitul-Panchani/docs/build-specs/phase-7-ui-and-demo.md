PHASE 7 — Demo harness + interactive web UI.

## STEP 0 — COMPREHENSION CHECK (before writing any code)
Output a numbered restatement, under 400 words, of: (a) every file you will create or modify,
(b) the acceptance criteria, (c) the single most important constraint and why it exists.
If anything is ambiguous or conflicts with AGENTS.md / ARCHITECTURE.md / MILESTONE.md, say so
explicitly rather than guessing silently. Then implement.

## TOKEN CONSERVATION — HARD CONSTRAINT
Make ZERO live API calls. `AMG_OFFLINE` defaults true and the test socket guard blocks non-loopback
connections — do not disable, bypass, or weaken either to make anything pass. Free Gemini quota is
reserved for the live demo. If you believe a live call is genuinely required, STOP and say so.

## OUTPUT CONTRACT — what you must return when finished
1. A statement of what you implemented and which acceptance criteria you could NOT verify. You
   CANNOT run Python here (see AGENTS.md) - Claude Code runs the suite and will send you failures.
2. How many live API calls your work consumed (must be zero) and how you verified it.
3. A one-paragraph summary of what you built.
4. Any spec ambiguity you resolved by judgment, named explicitly.

## FAILURE REPORTING
If you cannot make something pass, say so plainly and explain why. Do NOT report success with
failing tests. A truthful partial result is far more useful than an inaccurate green light.

---


Phases 1-6 are built and green. Build on them; do not rewrite them. Read AGENTS.md,
ARCHITECTURE.md and docs/demo-persona.md first. docs/demo-persona.md contains the EXACT scripted
turns and expected outcomes for all 9 scenarios — use those verbatim, do not invent your own.

This phase is what gets demonstrated live in a capstone defense. It must be visually clear, honest
about what it is doing, and it must not crash.

## 1. `src/amg/demo/persona.py`
The scripted dataset from docs/demo-persona.md as data, not prose: session 1 turns, session 2
turns, the attack strings, the poisoning attempts, and the genuine follow-up. One module-level
structure per scenario with an id, title, the input(s), and a plain-English statement of what the
scenario is supposed to prove.

## 2. `src/amg/demo/scenarios.py`
One function per scenario: `scenario_1_continuity(conn) -> ScenarioResult`, `scenario_2_...`,
`scenario_2b_...`, `3`, `4`, `5a`, `5b`, `6a`, `6b`. Plus `run_all(conn) -> list[ScenarioResult]`.

`ScenarioResult` must carry: `id`, `title`, `what_it_proves`, `steps` (an ordered list of
before/after observations), `passed: bool`, `evidence` (the concrete assertions checked, each with
its actual observed value), and `audit_rows_written`.

Each scenario ASSERTS its expected outcome and records pass/fail — this is evaluation, not just a
narration. Scenario 4 must additionally record that the hash chain still verifies after the erasure.

Critically: scenarios 1 and 2 must run against a **genuinely new `Session`** created after session
1's writes, to prove the persistence claim rather than pretending to.

## 3. `run_demo.py` (repo root) — the CLI harness
Resets the DB, runs session 1, then all 9 scenarios in order, printing clear before/after output
with section headers. Ends with a summary table (scenario | proves | PASS/FAIL) and a final
`verify_chain()` result. Exit code 0 only if every scenario passed. Support `--keep-db` to leave the
SQLite file for inspection and `--json` to emit machine-readable results.

## 4. `src/amg/web/app.py` — FastAPI app
Server-rendered Jinja2 shell plus small JSON endpoints called by vanilla JS. No build step, no npm,
no CDN — everything local so it works offline.

Endpoints:
- `GET  /`                     the single-page UI
- `POST /api/session/new`      start a fresh session (returns new session id)
- `POST /api/turn`             body `{text}` -> runs `ingest_turn`, returns the full IngestReport
- `POST /api/query`            body `{text}` -> guarded contextual retrieval, returns hits + provenance,
                               or the refusal + `access_denied` if the guard trips
- `POST /api/export`           body `{passphrase}` -> gated full export
- `GET  /api/memories`         current store (for the table panel)
- `GET  /api/audit`            audit rows + `verify_chain()` result
- `POST /api/memory/{id}/confirm`  confirm an inference (Scenario 3)
- `GET  /api/memory/{id}/cascade`  preview what a deletion would take (Scenario 4)
- `DELETE /api/memory/{id}`    body `{confirmed}` -> cascading erase
- `POST /api/conflict/resolve` body `{keep_id, supersede_id}`
- `POST /api/scenario/{id}`    run one scripted scenario and return its ScenarioResult
- `POST /api/reset`            reset the DB to a clean state
- `GET  /api/status`           which LLM/embedding provider is ACTUALLY serving calls, and whether
                               it is a fallback

## 5. UI layout — `templates/index.html` + `static/app.js` + `static/style.css`
Three columns on desktop, stacked on narrow screens.

**Left — Session & Controls**
- Current session id, prominent "New Session (fresh context)" button. When clicked, show a short
  note that this session carries zero conversation history — that is the persistence proof.
- Provider status badge. Must be honest: green "Gemini (live)" / amber "Stub (offline fallback)",
  and the same for Voyage vs local embeddings. Never show "live" when the stub answered.
- A "Run scenario" list with all 9 buttons, and a "Run all" button.
- Reset button.

**Centre — Conversation & the write pipeline**
- A text box to type a turn, and a Send button.
- After each turn, render the write pipeline as a visible sequence of stages:
  `Maker -> Checker -> Provenance -> Contradiction -> Write`, each stage showing what it decided.
  A rejected candidate shows the checker stage in red with its `reason_code` and stops there,
  visibly, with the `write_rejected` audit row noted. This visualization is the single most
  important thing in the UI — it is what makes the maker-checker architecture legible to a viewer.
- A separate query box for "ask a question" (contextual retrieval) showing the returned memories
  with their cosine scores, and the top-k cap displayed as e.g. "6 of 6 max".
- An export box with a passphrase field, demonstrating the gate.

**Right — Memory store & Audit log**
- Memory table: content, subject_key, source_type, trust tier, status, created_at, session.
  Colour-code: `user_stated` neutral, `ai_inferred`+unconfirmed visibly dimmed/amber with an
  "unconfirmed inference" badge and a Confirm button, `flagged_conflict` red with a Resolve control,
  `superseded` struck through. A Delete button per row that first shows the cascade preview and asks
  for confirmation.
- Audit log: newest first, showing event type, timestamp, actor, and the `detail` JSON. Show
  `prev_row_hash` -> `row_hash` linkage as short truncated hashes so the chain is visible.
  A prominent "Verify chain" button showing valid/invalid with the row count.
- A "Tamper test" button: deliberately mutates one audit row via raw SQL, then re-verifies and shows
  the chain now reports broken, identifying the row. Then a "Repair (reset)" button. This is a
  strong live-demo moment — it proves the tamper-evidence claim instead of asserting it.

Styling: clean, professional, readable at projector distance (generous font sizes, high contrast).
Dark text on light background. No external fonts or CDN assets.

## 6. `run_web.py` (repo root)
Starts uvicorn on `127.0.0.1:8000`, initialising the DB if absent. Print the URL clearly.

## 7. `tests/test_phase7.py`
- `run_all()` returns 9 results and every one passes, offline with no keys.
- Every FastAPI endpoint returns 200 (or the correct 4xx) using `fastapi.testclient.TestClient`.
- `POST /api/query` with the attack string returns a refusal, and the response body contains no
  memory content.
- `POST /api/export` with a wrong passphrase returns a refusal with no rows; with the right one it
  returns rows.
- `GET /api/status` correctly reports the stub/local fallback when no keys are set.

## 8. `README.md` (repo root)
Short and practical: what the project is (2 paragraphs), the DPDP framing in one paragraph with the
explicit disclaimer that this demonstrates architectural alignment and is NOT a compliance claim,
setup (`pip install -r requirements.txt`, copy `.env.example` to `.env`), how to run the CLI demo,
how to run the web UI, how to run tests, and a table of the 9 scenarios with what each proves.
State plainly that it runs fully offline with no API keys via the stub providers, and that adding
`GEMINI_API_KEY` / `VOYAGE_API_KEY` switches it to live calls with no code change.

## Constraints
- Everything must work offline with no keys. That is the demo's safety net and it is tested.
- No CDN, no npm, no build step. Vanilla JS only.
- The UI must never show a raw traceback. Catch errors and show a readable message.
- Do not weaken any Phase 1-6 governance rule to make the UI more convenient. In particular, do not
  add an "unbounded retrieval" endpoint for the memory table — `GET /api/memories` reads SQLite
  directly for display purposes, which is a different thing from the governed retrieval path, and
  you should say so in a comment.

## Finish by
Running `python -m pytest tests/ -q` AND `python run_demo.py`, pasting the real output of both.
Fix and re-run until both are green and all 9 scenarios pass. Then summarize.

## 9. Demo-day mode and cache pre-warming (REQUIRED — do not skip)

The user's decision: **the live demo makes real Gemini/Voyage calls, with a pre-warmed cache as the
fallback** so a wifi drop, 429, or expired key mid-demo serves a real cached response instead of
stalling. Build the mechanism; do NOT execute it (that would spend quota — Claude Code runs it).

### `run_demo.py --prewarm-cache`
- Requires `AMG_OFFLINE=0` and both keys present; if either is missing, print a clear message and
  exit non-zero WITHOUT attempting calls.
- Runs every scripted scenario once with `AMG_CACHE_MODE=refresh`, so each maker/checker/entailment
  prompt and each embedding is fetched live and written to `.amg_cache/`.
- Prints a summary: total live calls made, per-provider/model breakdown, cache entries written, and
  the budget ledger before/after. The operator must be able to see exactly what it cost.
- Refuses to run if it would exceed `AMG_DAILY_LIVE_CALL_CAP`, and says how many calls it needs.

### `run_demo.py --record-confidence`
Per `docs/decisions/002-contradiction-threshold.md`, the contradiction threshold (currently 0.70) is
a defensive default chosen offline and MUST be validated against live Gemini. This flag runs only
the Scenario 2 and 2b entailment pair live and prints the actual `contradicts` and `confidence`
values Gemini returns for each, plus whether the configured threshold separates them correctly.
Budget for this is ~4 calls. Print a recommended threshold based on the observed values.

### UI additions for demo day
- The provider badge must distinguish four states honestly, never conflating them:
  `Gemini (live)` / `Gemini (cached)` / `Stub (offline)` / `Stub (fallback after error)`.
  A cached real response is NOT the same claim as a fresh live call — label it as cached.
- Show today's budget usage (`used/cap`) somewhere visible, so the operator notices approaching
  exhaustion before it degrades mid-demo.
- If a call falls back mid-demo, surface a small non-alarming notice rather than failing silently.
  The audience should be able to see the resilience working — that is a feature worth showing.
