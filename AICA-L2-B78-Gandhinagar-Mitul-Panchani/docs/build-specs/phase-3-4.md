PHASE 3 + 4 — Write path wired to the audit log, and contradiction detection.

## OBJECTIVE
Produce a working `ingest_turn()` that carries a user turn through the full governed write path
(maker -> checker -> provenance -> contradiction -> write -> audit), with every branch logged to the
hash-chained audit log, plus contradiction detection that correctly discriminates Scenario 2 (a real
contradiction, flagged) from Scenario 2b (additive detail, NOT flagged).

## STEP 0 — COMPREHENSION CHECK (before writing any code)
Output a numbered restatement, under 400 words, of:
(a) every file you will create or modify,
(b) the acceptance criteria below,
(c) the single most important constraint, and why it exists.
If anything here is ambiguous, or conflicts with AGENTS.md / ARCHITECTURE.md / MILESTONE.md, say so
explicitly rather than guessing silently. Then implement.

## CONTEXT — read these first, they are authoritative
`AGENTS.md`, `ARCHITECTURE.md` (§3.3 has the flow diagram this phase implements), `MILESTONE.md`,
`docs/demo-persona.md` (the exact scripted turns), and `docs/decisions/001-checker-modes.md`.

## TOKEN CONSERVATION — HARD CONSTRAINT
Phase 2.5 established offline enforcement. **Make ZERO live API calls during this task.**
`AMG_OFFLINE` defaults true and the test socket guard blocks non-loopback connections. Do not
disable, bypass, or weaken either one to make anything pass. Free Gemini quota is reserved for the
live demo. If you believe a live call is genuinely required, STOP and say so instead of making it.

## OUTPUT CONTRACT — what you must return when finished
1. A statement of what you implemented and which acceptance criteria you could NOT verify. You
   CANNOT run Python here (see AGENTS.md) - Claude Code runs the suite and will send you failures.
2. A statement of how many live API calls your work consumed (**must be zero**) and how you verified it.
3. A one-paragraph summary of what you built.
4. Your recommendation for `contradiction_min_confidence`, derived from the confidence values your
   stub entailment logic actually returns for Scenario 2 vs 2b. Show the two values and the
   threshold that separates them - reasoned from your implementation, not a round-number guess.
5. Any spec ambiguity you resolved by judgment, named explicitly.

## FAILURE REPORTING
If you cannot make something pass, say so plainly and explain why. Do NOT report success with
failing tests — that happened on a previous phase and was caught. A truthful partial result is far
more useful than an inaccurate green light.

---

## THE WORK
## 1. `src/amg/session.py`
Module docstring: enforces the P0 session-boundary definition.
- `Session` — `session_id`, `actor`, `started_at`, and an `export_confirmed: bool` flag (default
  False) that only the confirmation gate may set.
- `new_session(actor="demo_user") -> Session` — generates a fresh id (e.g. `s1`, `s2`, or a uuid4).
- The critical property, stated in a comment: a Session carries **no conversation history**. There
  is no `messages` list, no transcript, no carried-over context. A new Session is a genuinely fresh
  LLM context, and the ONLY way information reaches it is through the retrieval layer. That absence
  is the enforcement, and it is what makes Scenario 1 a real persistence proof rather than a
  single-turn trick.

## 2. `src/amg/contradiction.py`  (Phase 4)
Module docstring must state P0 rule 6: similarity NEVER decides a contradiction.
- `find_candidates_for_check(conn, subject_key, exclude_id=None) -> list[Memory]` — retrieves
  `active` and `flagged_conflict` memories with a MATCHING `subject_key`. This is a plain SQL
  lookup, not a vector search. Embedding similarity may optionally *rank* them, but must never
  filter anything in or out on its own.
- `check_for_contradiction(conn, new_content, subject_key) -> ContradictionResult` — for each
  candidate, calls `llm.check_entailment(new_fact, existing_fact)`. A contradiction is declared only
  when `contradicts is True` AND `confidence >= settings.contradiction_min_confidence`. Returns a
  model carrying `conflicts: list[tuple[Memory, EntailmentVerdict]]` and `checked_count`.
- Add a comment explaining why the two-step design exists: subject_key narrows the field cheaply and
  precisely, the LLM makes the actual judgment. Similarity alone both misses subtle contradictions
  and false-positives on merely-related content.

## 3. `src/amg/memory_service.py`  (Phase 3 — the spine)
This is the module that wires the whole write path from ARCHITECTURE.md 3.3. Every branch writes an
audit row. Module docstring should map each step to the flow diagram.

`ingest_turn(conn, session: Session, user_text: str) -> IngestReport`

Flow, in this exact order:
1. **Maker** — `extraction.propose_candidates(user_text)`. Nothing else is in scope.
2. For each candidate, in order (direct facts before their inferred children):
   a. **Checker** — `verifier.verify_candidate(candidate)`.
      - Rejected -> `audit.append_event(event_type="write_rejected", detail={"assertion_type":...,
        "reason_code":..., "content_sha256": fingerprint})`. **No `memories` row.** Continue to the
        next candidate. Never silently drop — the audit row IS the record.
   b. **Provenance tagger** — `provenance.tag(candidate)`.
   c. **Contradiction check** — `contradiction.check_for_contradiction(...)`.
      - No conflict -> write the memory with `status="active"`.
      - Conflict found -> **both versions persist**. Write the new memory, and set the *existing*
        conflicting memory's `status="flagged_conflict"` (and the new one too, so the pair is
        visible as a pair). Nothing is overwritten, nothing is discarded. Log the flag.
   d. **Embed and store** — embed the content, insert the `embeddings` row, link `memories.embedding_id`.
   e. **derived_from** — if the candidate has `inferred_from_content`, resolve it to the memory id
      written earlier in THIS same turn and insert the `derived_from` row. (Per AGENTS.md, an
      inferred fact's parent is always a sibling from the same turn.)
   f. **Audit** — `write` event with structural detail only: `subject_key`, `category`,
      `source_type`, `trust_tier`, `status`, `content_sha256`, `provider`. Never the content.
3. Return an `IngestReport` listing, per candidate: what happened, why, which audit rows were
   written, and whether a fallback provider served the call. The web UI renders this directly, so
   make it rich and honest.

Also provide:
- `confirm_inference(conn, session, memory_id)` — sets `confirmed_at`, raising the trust tier;
  logs an `update` event. (Scenario 3.)
- `resolve_conflict(conn, session, keep_id, supersede_id)` — sets the superseded memory's
  `status="superseded"` and the keeper's `supersedes_id`; logs `update`. (P1 resolve-by-replacement.)
- `get_flagged_conflicts(conn, subject_key=None) -> list[...]` so the UI can proactively surface an
  unresolved conflict next time that `subject_key` comes up. (P1.)

## 4. `tests/test_phase3.py`
- Ingesting persona turn 1.1 produces: 1 direct + 1 inferred memory, a `derived_from` row linking
  them, 2 `write` audit rows, and a valid hash chain.
- A rejected candidate produces a `write_rejected` row and **zero** `memories` rows.
- **The P0 content-leak test — this one matters most.** After running the full persona script,
  assert that no `audit_log.detail` value contains any meaningful substring of any
  `memories.content`. Implement it as a sliding-window n-gram check: for every memory content,
  generate all normalized windows of >= 12 characters (case-folded, whitespace-collapsed) and
  assert none appears in any audit `detail` blob. A naive full-string check would pass trivially and
  prove nothing; a naive per-word check would false-positive on "the". Document that reasoning in a
  comment. Also assert the same for deleted memories' content captured before deletion.
- Every event type that the phase can emit produces a chain that still verifies.

## 5. `tests/test_phase4.py`
- **Scenario 2**: employer fact, then a different employer, same `subject_key` -> both rows persist,
  both `flagged_conflict`, neither deleted, flag present in the audit log.
- **Scenario 2b**: employer fact, then the office-location detail -> written `active`, **NOT**
  flagged. Assert explicitly that no `flagged_conflict` status appears.
- `check_for_contradiction` performs zero vector searches when deciding — assert the entailment
  call count equals the candidate count (i.e. the LLM, not similarity, made every call).
- `resolve_conflict` sets `superseded` + `supersedes_id` correctly and logs `update`.

## Constraints
- All tests must pass offline with no API keys (stub + local providers).
- Do not weaken Phase 1's `assert_detail_safe` allowlist to make a test pass. If you need a new
  detail key, add it deliberately and justify it in a comment — it must be structural, never content.
- Keep SQL plain and readable.
