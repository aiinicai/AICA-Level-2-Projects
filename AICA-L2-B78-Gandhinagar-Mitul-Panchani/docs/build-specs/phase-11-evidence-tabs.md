PHASE 11 — Make the right-hand evidence column a two-tab panel.

## OBJECTIVE
Show one evidence panel at a time at full height instead of two stacked panels that both scroll,
without hiding either behind a click-to-reveal drawer.

## STEP 0 — COMPREHENSION CHECK (before writing code)
Restate under 300 words: (a) files you will modify, (b) what the count badges are for, (c) the one
demo property that must survive this change and why a drawer was rejected. Flag ambiguity rather
than guessing.

## TOKEN CONSERVATION
ZERO live API calls. Do not disable `AMG_OFFLINE` or the socket guard.

## WHY
Measured in the running app at a 720px viewport, the right column holds:

    Memory store            912px
    Tamper-evident audit    789px
                          -------
                           1701px  in a 720px viewport

Both panels scroll, so neither is fully readable during a live demo.

A slide-out drawer was considered and REJECTED: the right column is the evidence surface. When a
turn is sent, the audience must see the fact land in the memory store and the audit row appear
without the presenter opening anything. Scenario 4 is the sharpest case - one deletion must visibly
remove TWO memory rows while TWO content-free `delete` rows appear in the audit. Hiding either
behind a click breaks that.

Tabs solve the height problem while keeping both surfaces one click - and zero clicks for whichever
is already showing - from view.

## THE CHANGE

### Tabbed evidence column
Replace the two stacked `<section class="panel">` blocks in the right column with a single panel
containing a tab strip and two tab panes:

    [ Memory store  7 ] [ Tamper-evident audit  19 ]

- Use real tab semantics: `role="tablist"` / `role="tab"` / `role="tabpanel"`, `aria-selected`,
  `aria-controls`, and arrow-key navigation between tabs. The inactive pane uses `hidden`.
- Default tab on load: **Memory store**.
- The pane takes the full available column height with its own internal scroll, so the tab strip
  stays fixed while content scrolls.

### Live count badges — the important part
Each tab label carries a live count that updates on every refresh, whichever tab is showing:
  * Memory store — number of memories currently in the store
  * Tamper-evident audit — number of audit rows

This is what preserves the demo property. Even while looking at the memory store, the presenter and
audience can see the audit count tick from 17 to 19 after a deletion. Point at that during
Scenario 4 rather than switching tabs.

**When a count changes, briefly highlight the badge** (a short background flash, ~1.2s) so the
change is noticeable without switching tabs. Do not animate on first load, only on change.

### Chain status stays visible in both tabs
The `#chain-summary` element (currently in the page header) must remain visible regardless of which
tab is active - it is the Scenario 7 payload. Do not move it inside the audit tab pane.

### Controls
- The Memory store "Refresh" button stays with the memory tab.
- "Verify chain", "Tamper test" and "Repair (reset)" stay with the audit tab, in that order, with
  Repair still directly beside Tamper test.
- Clicking "Tamper test" or "Verify chain" must automatically switch to the audit tab if it is not
  already active, so the presenter is never left looking at the wrong pane after acting.

## WHAT MUST NOT CHANGE
- No API endpoints, governance rules, offline enforcement, or budget behaviour.
- The Phase 9 plain-English labels and the raw values beneath them.
- The memory table's colour coding: unconfirmed inference amber, conflict red, superseded struck
  through, plus the Confirm / Keep this / Delete row actions.
- The audit rows' hash-chain display (`prev → row` truncated hashes) and the content-free `detail`.
- The operator note "Operator display via direct SQLite; not an assistant retrieval endpoint."

## TESTS
- Served HTML contains a `role="tablist"` with exactly two `role="tab"` elements.
- Both tab panes exist; exactly one is visible on load and it is the memory store.
- Both count badge elements exist and are separate from the tab label text.
- `#chain-summary` is NOT inside either tab pane.
- The audit tab contains verify / tamper / repair; the memory tab contains refresh.
- Existing endpoint and scenario tests pass unchanged.

## ACCEPTANCE CRITERIA
1. `.venv/Scripts/python.exe -m pytest -q` passes with 0 failures.
2. One evidence panel shows at a time, at full column height, with its own scroll.
3. Both counts update live regardless of the active tab, and flash on change.
4. Acting on verify/tamper switches to the audit tab automatically.
5. Keyboard: tabs reachable and switchable with arrow keys.

## OUTPUT CONTRACT
You CANNOT run Python or a browser (see AGENTS.md). State what you changed, what remains unverified,
and confirm zero live API calls. Do not claim tests pass. Claude Code runs the suite, rebuilds, and
inspects the rendered layout.
