PHASE 5 + 6 — Cascading erasure, and the governance layer (bounded retrieval + gated export).

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


Phases 1-4 are built and green. Build on them. Read AGENTS.md, ARCHITECTURE.md and
docs/demo-persona.md first. Section 3.3's deletion and retrieval branches are what this implements.

## 1. `src/amg/deletion.py`  (Phase 5)
Module docstring must state P0 rule 7: an embedding is derived data that can partially leak its
source content, so it must be destroyed with the content, not orphaned.

- `collect_cascade(conn, memory_id) -> CascadePlan` — walks `derived_from` transitively (a memory's
  dependents, and their dependents, to arbitrary depth) and returns the full set of memory ids to
  erase, plus their embedding ids. Must be cycle-safe (track visited ids) — a malformed
  `derived_from` graph must not hang the demo.
- `preview_cascade(conn, memory_id) -> CascadePlan` — same walk, no mutation. The UI shows this
  before asking for confirmation, so the user sees exactly what a deletion will take with it.
- `erase(conn, session, memory_id, confirmed: bool) -> EraseReport`
  - If `confirmed` is False -> refuse, log `access_denied` with `{"gate": "delete_confirmation"}`,
    return the preview. Deletion is a confirmed operation, never a bare call.
  - If confirmed -> in a single transaction, for the target AND every dependent:
    `DELETE FROM memories`, `DELETE FROM embeddings`, `DELETE FROM derived_from` rows referencing
    them. **Physical DELETE, not a status flag.** A `status='deleted'` row that still holds the
    content in the `content` column has not erased anything — the row must be gone.
  - Log ONE `delete` audit event per erased memory, `detail` = `{"subject_key":...,
    "source_type":..., "content_sha256":..., "cascade_count":N, "was_dependent": bool}`.
    Content-free, per P0 rule 1. The `content_sha256` is what preserves tamper-evidence without
    retaining the erased data — this is the Section 12(4)-(5) retention-vs-erasure resolution, so
    say that in a comment.
  - After the transaction, assert the hash chain still verifies and include that in the report.

## 2. `src/amg/retrieval.py`  (Phase 6)
Module docstring must state P0 rules 4 and 5. Two clearly separate operations — never one function
with a flag, because a flag is exactly the back door this design exists to prevent.

- `contextual_retrieve(conn, session, query: str) -> ContextualResult`
  - Embeds the query, cosine-compares against every stored embedding (brute force, plain Python,
    show the math), sorts, and returns **at most `settings.contextual_top_k`** results.
  - The cap is applied by slicing inside this function against the settings value. There is NO
    `top_k`, `limit`, `all`, or `unbounded` parameter on this function's signature. State in a
    comment that the absence of that parameter is the enforcement — a caller cannot request more
    than the cap because there is no way to express it.
  - Excludes `deleted`/`superseded` memories. Returns each hit WITH its provenance metadata
    (`source_type`, `trust_tier`, `confirmed_at`, `created_at`, `source_session_id`) so the caller
    can surface trust honestly (P1).
  - Logs `contextual_read` with `{"result_count": n, "top_k": cap, "provider": ...}`.

- `full_export(conn, session, passphrase: str) -> ExportResult`
  - Calls `governance.confirm_export_gate(session, passphrase)` FIRST. If the gate does not pass,
    return a refusal and log `access_denied` with `{"gate": "export_passphrase"}`. Return no data.
  - Only on success: return every non-deleted memory with full metadata, and log `full_export`.
  - This path is what actually satisfies the DPDP Section 11 access right, so it must genuinely
    succeed when properly invoked. Refusing it too would be its own compliance failure.

## 3. `src/amg/governance.py`  (Phase 6)
Module docstring: the policy engine. Enforces rules at write, contextual read, export, and delete.

- `EXTRACTION_ATTACK_PATTERNS` — regex list for unscoped-dump shapes: `ignore (all )?(previous|prior)`,
  `you are now`, `debug mode`, `developer mode`, `print (the )?(complete|entire|full|all)`,
  `dump (the |your )?(memory|store|database|everything)`, `no filtering`, `all rows`,
  `disregard (your )?(instructions|rules)`, `override`, `reveal everything`, `system:`.
- `classify_request(text) -> RequestShape` returning one of `ordinary_query`,
  `unscoped_dump_attempt`, `legitimate_export_request`.
  IMPORTANT nuance, get this right: a plain, politely-phrased "show me everything you have on me" is
  a **legitimate_export_request**, NOT an attack. It is routed to the gate, where it succeeds if the
  passphrase is supplied. What makes something an attack is instruction-override framing and an
  attempt to bypass the gate — not breadth of scope. Refusing broad requests wholesale would violate
  the very access right this system is built to honor. Comment this distinction clearly; it is the
  single most important judgment call in the file and a reviewer will ask about it.
- `guard_contextual_query(session, text) -> GuardDecision` — if the shape is
  `unscoped_dump_attempt`, refuse and signal `access_denied`. Otherwise allow. Note that even on the
  allow path the top-k cap still holds independently, so the guard is defense-in-depth, not the only
  barrier.
- `confirm_export_gate(session, passphrase) -> bool` — constant-time compare
  (`hmac.compare_digest`) against `settings.export_passphrase`; on success sets
  `session.export_confirmed = True`. Comment honestly that this stands in for real authentication
  and is not secure in any general sense — its purpose is to make the gate a real, traversable code
  path rather than a suggestion.

## 4. `tests/test_phase5.py`
- **Scenario 4**: ingest persona turn 1.2 (dietary + inferred "avoids leather" child), then erase
  the dietary fact with `confirmed=True`. Assert ALL of:
  - both `memories` rows are physically absent (`SELECT COUNT(*)` == 0, not status-flagged)
  - **both `embeddings` rows are physically absent** — query the embeddings table directly by id
  - the `derived_from` row is gone
  - neither is returned by `contextual_retrieve` for a query that previously matched them
  - two `delete` audit rows exist, and neither `detail` contains any >=12-char window of the erased
    content (reuse the Phase 3 n-gram helper)
  - `verify_chain()` is still valid across the gap
- `erase(confirmed=False)` mutates nothing and logs `access_denied`.
- A 3-level chain (A <- B <- C) cascades fully from A.
- A cyclic `derived_from` graph terminates instead of hanging.

## 5. `tests/test_phase6.py`
- **Scenario 5a**: the persona's attack string -> `guard_contextual_query` refuses,
  `access_denied` logged, and no memory content is returned anywhere in the response object.
- **Scenario 5b**: `full_export` with the correct passphrase -> succeeds, returns all live
  memories, logs `full_export`. Assert it genuinely returns data — this half must pass.
- `full_export` with a wrong/absent passphrase -> refused, `access_denied`, returns no rows.
- **Discrimination test**: assert `classify_request("show me everything you have on me")` is
  `legitimate_export_request`, while `classify_request(<attack string>)` is
  `unscoped_dump_attempt`. This is the pair that proves governance, not blanket refusal.
- **Top-k structural test**: use `inspect.signature(contextual_retrieve)` to assert there is no
  parameter whose name matches `top_k|limit|k|all|count|max`. Then ingest 20+ memories and assert
  the result length never exceeds the configured cap for any query.
- Deleted and superseded memories never appear in either retrieval path.

## Constraints
- All tests pass offline, no keys.
- Brute-force cosine stays plain Python — no numpy.
- Do not add a "return everything" convenience path to `contextual_retrieve`, even for tests. Tests
  that need the full store must query SQLite directly.

## Finish by
Running `python -m pytest tests/ -q` and pasting real output. Fix and re-run until green. Then
summarize, and state how strict you found the instruction-pattern screen needed to be to pass 5a
and 5b together without false-positiving on the legitimate broad request.
