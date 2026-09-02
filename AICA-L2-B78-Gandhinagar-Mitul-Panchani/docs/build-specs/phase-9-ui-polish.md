PHASE 9 — Presentation polish. The UI shows raw database vocabulary to a non-technical audience.

## OBJECTIVE
Make the pipeline display readable to someone who has never seen the codebase, without hiding the
technical detail a reviewer may want. Fix two visual defects found while presenting.

## STEP 0 — COMPREHENSION CHECK (before writing code)
Restate under 300 words: (a) files you will modify, (b) the three defects, (c) why the raw values
must remain visible somewhere rather than simply being replaced. Flag ambiguity rather than guessing.

## TOKEN CONSERVATION
ZERO live API calls. `AMG_OFFLINE` defaults true. Do not disable it or the socket guard.

## DEFECT 1 — raw enum values shown as the primary label
`src/amg/web/static/app.js` → `renderPipeline()` prints enum values straight through, e.g.
`direct_self_statement`, `user_stated`, `employer`, `blocked_offline`, `stub-rule-v1`.

**Fix:** show a plain-English label as the PRIMARY text, with the raw value beneath it in small
muted type. Do NOT delete the raw values — a technical reviewer should still be able to tie what
they see to ARCHITECTURE.md, and the raw enum is the honest identifier. Label first, code second.

Add a single lookup table in `app.js` (one place, easy to audit):

    assertion_type:
      direct_self_statement -> "Direct statement about themselves"
      hypothetical          -> "Hypothetical - not a fact"
      third_party           -> "About someone else"
      quoted                -> "Quoted speech"
    source_type:
      user_stated  -> "Stated by the user"
      ai_inferred  -> "Inferred by the AI"
    trust_tier:
      stated                -> "Highest - the user's own words"
      confirmed_inference   -> "Confirmed inference"
      unconfirmed_inference -> "Unconfirmed inference"
    reason_code:
      ok                    -> "Passed all checks"
      instruction_shaped    -> "Looks like an injected instruction"
      hypothetical_framing  -> "Framed as hypothetical, not a fact"
      not_first_person      -> "Not a first-person statement"
      third_party_subject   -> "About a third party"
      quoted_speech         -> "Quoted speech"
      empty_or_trivial      -> "Empty or trivial"
      not_inference_shaped  -> "Inference phrased as a user statement"
      overclaims_certainty  -> "Inference stated as certain fact"
    status:
      active           -> "Stored and active"
      flagged_conflict -> "Flagged - conflicts with an existing fact"
      superseded       -> "Superseded by a newer fact"
    served_by:
      live                 -> "live API"
      cache                -> "cached real response"
      cache_after_error    -> "cached real response (live call failed)"
      stub                 -> "offline engine"
      fallback_after_error -> "offline engine (live call failed)"
      blocked_by_cap       -> "offline engine (daily limit reached)"
      blocked_offline      -> "offline mode"

Unknown values must fall back to the raw string rather than rendering blank.

Also make the stage bodies read as short sentences rather than bare tokens. For example the
Contradiction stage currently shows `Checked 0` / `No conflict`; prefer
`Compared against 0 existing facts` / `No contradiction found`. Keep them SHORT - these boxes are
narrow and are read at a glance from across a room.

`subject_key` should be shown as a readable phrase: replace underscores with spaces
(`professional_expertise` -> "professional expertise") and keep the raw key in the small line.

## DEFECT 2 — words break mid-syllable
`style.css` line ~128: `.stage { ... overflow-wrap: anywhere; }` causes headings to render as
"Provenanc / e" and "Contradicti / on" (confirmed in a screenshot from a live run).

**Fix:** use `overflow-wrap: break-word` on `.stage` so breaks happen at word boundaries, and add
`overflow-wrap: normal; hyphens: none;` to `.stage strong` so a stage HEADING never breaks
mid-word. If a heading still cannot fit, reduce its font-size slightly rather than allowing a break.
Verify all five headings (Maker, Checker, Provenance, Contradiction, Write) render on one line at a
1280px viewport.

## DEFECT 3 — a deliberate offline run is reported as a "fallback"
`app.js` line ~99 renders, whenever `candidate.fallback_used` is true:

    "A provider fallback served part of this candidate; governance continued normally."

In offline mode nothing failed - offline is the intended configuration. Showing an amber warning
makes an audience think something broke. This is the opposite of the honest-reporting requirement:
it overstates a problem rather than hiding one, but it is still inaccurate.

**Fix:** branch the message on WHY the offline engine served the call, using the `served_by` value
already available on the provider records:
  * `blocked_offline`   -> neutral grey note: "Running in offline mode - the deterministic engine
                           served this. No API key is configured."
  * `blocked_by_cap`    -> amber: "Daily live-call limit reached; the offline engine served this."
  * `fallback_after_error` / `cache_after_error` -> amber: "A live call failed; served by the
                           offline engine (or a cached real response). Governance continued
                           normally."
  * otherwise -> show nothing.
Style the neutral offline note in grey/muted, NOT amber - amber must mean "something needed
attention", or it stops meaning anything.

## DEFECT 4 — placeholder text duplicates the scripted examples
`index.html`: the turn textarea placeholder is the exact sentence the demo script tells the
presenter to type ("I work as a financial controller at Northwind Textiles in Coimbatore."), and the
query input placeholder is exactly "Where do I work?". On a projector an empty box is
indistinguishable from a filled one, and the presenter cannot tell whether it cleared.

**Fix:**
  * Reword: turn box -> `e.g. I work as a financial controller at Northwind Textiles.`
    query box -> `e.g. Where do I work?`   passphrase box -> keep as is.
  * Add an explicit `::placeholder` rule in `style.css`: muted grey (around #8a94a0) and italic, so
    hint text is unmistakably not content. There is currently NO ::placeholder rule at all.

## TESTS — extend `tests/test_phase7.py` (or a new `tests/test_phase9_labels.py`)
- Assert `index.html` placeholders no longer equal the scripted sentences verbatim.
- Assert `style.css` contains a `::placeholder` rule.
- Assert `style.css` no longer sets `overflow-wrap: anywhere` on `.stage`.
- Assert `app.js` contains a label lookup covering every enum value in `models.py` - iterate the
  Python enums and check each value string appears in the JS lookup. This is the important one: it
  fails if someone adds an enum value later and forgets the label.
- Assert the raw enum values still appear in `app.js` (labels supplement, never replace them).

## ACCEPTANCE CRITERIA
1. `.venv/Scripts/python.exe -m pytest -q` passes with 0 failures.
2. No governance, offline, socket-guard or budget rule is weakened.
3. Every enum value has a plain-English label, and the raw value remains visible.
4. Stage headings never break mid-word.
5. Offline-by-design is not reported as a failure or fallback.

## OUTPUT CONTRACT
You CANNOT run Python or a browser (see AGENTS.md). State what you changed, what remains unverified,
and confirm zero live API calls. Do not claim tests pass. Claude Code runs the suite, rebuilds the
exe, and inspects the rendered UI.
