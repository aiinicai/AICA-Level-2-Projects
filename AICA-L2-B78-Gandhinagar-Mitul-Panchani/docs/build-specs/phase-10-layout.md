PHASE 10 — Reclaim screen real estate. Setup chrome is crowding out the demo.

## OBJECTIVE
Move one-time setup controls into a compact top status bar and a modal dialog, so the left column
carries the scenario buttons and the three working panels get the space. Nothing about governance,
honesty of reporting, or the audit surface changes.

## STEP 0 — COMPREHENSION CHECK (before writing code)
Restate under 350 words: (a) files you will modify, (b) what moves where, (c) the two things that
must NOT be lost in the move, and why. Flag ambiguity rather than guessing.

## TOKEN CONSERVATION
ZERO live API calls. Do not disable `AMG_OFFLINE` or the socket guard.

## THE MEASUREMENT THAT JUSTIFIES THIS
Measured in the running app at a 720px viewport, the left column totals 2610px:

    Session & providers      576px
    Scripted evidence       1087px   <- the actual demo content
    AI provider settings     829px   <- one-time setup, larger than any demo panel
    Demo controls            118px

1523px of 2610px (58%) is setup chrome. The presenter scrolls past configuration to reach the
scenario buttons on every run.

## THE NEW LAYOUT

### 1. A compact top status bar (new), directly under the page title
One row, wrapping gracefully on narrow screens, containing:

  [● Offline]   [Session s-4745…  ⟳ New]   [Budget 0/100]   [⚙ AI keys]   [Reset database]

- **Provider indicator** — a coloured dot plus a short label. It MUST still distinguish every state
  honestly; this is a governance requirement, not decoration:
      grey   "Offline"        - deterministic engine, offline by design
      green  "Live"           - real API responses
      blue   "Cached"         - a cached REAL response served it
      amber  "Fallback"       - a live call failed, or the daily cap was hit
  Hovering (title attribute) reveals the full detail currently shown in the badges, including the
  provider and model names. Clicking it opens the AI keys modal.
  **A cached real response must never be shown as "Live", and the offline engine must never be shown
  as either.** That rule is unchanged from Phase 2.5 and Phase 9.
- **Session chip** — the id truncated to ~10 chars, with a small "New" button beside it.
- **Budget** — `used/cap`, plain text. Turns amber at 80% of cap.
- **AI keys** — opens the modal (below).
- **Reset database** — the existing action, unchanged.

### 2. The "fresh context" message becomes a moment, not furniture
Today a permanent line reads "Fresh context: this session carries zero conversation history."
It is a talking point in Part 2 of the demo script, so it must NOT be deleted — but it does not need
to occupy space permanently.

Move it to a transient confirmation shown when "New" is clicked: a brief highlighted note near the
session chip reading "New session started - it carries zero conversation history." Keep it visible
for around 8 seconds (long enough for a presenter to point at it), then fade. Also keep the same
text as the `title` tooltip on the session chip so it can be surfaced on demand.

### 3. AI provider settings become a modal dialog
Replace the inline 829px form with a dialog opened from the status bar. Use the native `<dialog>`
element with `showModal()`.

Contents: exactly the fields that exist today - Gemini key, Voyage key, Gemini model, the current
mode line, and the plain-text-storage warning. Do not drop the warning; it is an honesty requirement.

Three buttons, as requested:
    [Save]            apply, keep the dialog open, show inline confirmation and the new resolved mode
    [Save and close]  apply, then close
    [Cancel]          discard edits and close WITHOUT applying
Plus the existing "Clear keys and return to offline" and "Test connection" actions inside the dialog.

Behaviour requirements:
- `Cancel` and `Esc` must both discard unsaved edits. Re-opening shows the stored values, never the
  abandoned ones.
- The dialog must trap focus and return focus to the button that opened it on close.
- Never render a stored key back into the input as plain text - keep the current masked behaviour.
- Clicking the backdrop closes as Cancel (discard).

### 4. Left column becomes scenarios only
After the moves, the left column holds "Scripted evidence" (the nine buttons plus Run all) and
nothing else. Let the three working columns take the reclaimed height.

## WHAT MUST NOT BE LOST — state these back in Step 0
1. **Honest provider reporting.** The compact indicator must still distinguish offline / live /
   cached / fallback. Collapsing them into a single "online/offline" toggle would break the property
   the whole project claims. If a state cannot be shown in the dot, it must be in the tooltip.
2. **The plain-text key warning** and the "fresh context / zero conversation history" wording. Both
   are used verbatim in the demo script and in the defence.

## TESTS — extend the web tests
- `GET /` HTML contains a status bar element with the provider indicator, session chip, budget and
  the keys/reset controls.
- The HTML contains a `<dialog>` for settings, and the settings fields are inside it.
- The four indicator states each have a distinct class or data attribute (assert all four exist in
  the CSS or JS), so they cannot silently collapse into two.
- The phrase "zero conversation history" still appears somewhere in the served HTML or JS.
- The plain-text storage warning still appears.
- Existing endpoint tests all still pass unchanged - this is a presentation change only, no API
  changes.

## ACCEPTANCE CRITERIA
1. `.venv/Scripts/python.exe -m pytest -q` passes with 0 failures.
2. No API endpoint, governance rule, offline enforcement or budget rule changes.
3. The left column contains only the scenario panel.
4. Cancel/Esc discards edits; Save applies without closing; Save and close does both.
5. All four provider states remain distinguishable.

## OUTPUT CONTRACT
You CANNOT run Python or a browser (see AGENTS.md). State what you changed, what remains unverified,
and confirm zero live API calls. Do not claim tests pass. Claude Code runs the suite, rebuilds, and
inspects the rendered layout.
