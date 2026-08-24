PHASE 9b — The full export shows only a row count, not the exported records.

## OBJECTIVE
Render the actual exported records in the UI. This is the payoff of the most important moment in
the demo and it is currently invisible.

## STEP 0 — COMPREHENSION CHECK (under 200 words)
Restate: (a) the defect, (b) what you will change, (c) why showing the records matters more than
showing a count. Flag ambiguity rather than guessing.

## TOKEN CONSERVATION
ZERO live API calls. Do not disable AMG_OFFLINE or the socket guard.

## THE DEFECT
`src/amg/web/static/app.js`, the `#run-export` handler (~line 320):

    node.textContent = result.succeeded
      ? `Gate confirmed: complete export returned ${result.memories.length} row(s).`
      : `REFUSED: ${result.reason} Zero rows returned.`;

`result.memories` is fetched and then discarded except for `.length`. The API returns every memory
with full metadata; the presenter and audience never see it.

Why it matters: Scenario 5a refuses a broad request, 5b grants the same breadth through the
confirmation gate. The contrast IS the argument. If 5b only prints a number, the audience sees a
refusal followed by another non-answer, and the point is lost.

## THE FIX
On success, keep the confirmation line AND render the exported records beneath it:
- A compact table or definition list: content, subject_key (readable form + raw), source_type,
  trust tier, status, created_at, source_session_id.
- Reuse the existing label lookup from Phase 9 so this shows plain-English labels with raw values
  beneath, exactly like the pipeline and memory table. Do not invent a second vocabulary.
- Style it consistently with the Memory store table; put it inside a scrollable container so a large
  export cannot blow out the page layout.
- Include a short heading such as "Complete record returned under the Section 11 access right"
  so a reviewer sees what the export represents.

On refusal, keep the current behaviour exactly: the reason, and an explicit statement that zero rows
were returned. **The refusal path must never render any memory content** - that is the P0 guarantee
Scenario 5a demonstrates, and it must not be weakened by this change.

## TESTS — extend the phase 7/9 web tests
- `POST /api/export` with the correct passphrase returns rows AND the handler renders them: assert
  `app.js` references a field of the memory objects (e.g. `content`) inside the success branch, not
  only `memories.length`.
- Assert the failure branch in `app.js` does not reference `memories` content fields at all.
- An existing-behaviour regression: wrong passphrase still yields zero rows and a refusal.

## ACCEPTANCE CRITERIA
1. `.venv/Scripts/python.exe -m pytest -q` passes with 0 failures.
2. A successful export displays the actual records, using the Phase 9 labels.
3. A refused export still shows no memory content whatsoever.
4. No governance, offline, socket-guard or budget rule is weakened.

## OUTPUT CONTRACT
You CANNOT run Python or a browser (see AGENTS.md). State what you changed, what remains unverified,
and confirm zero live API calls. Do not claim tests pass.
