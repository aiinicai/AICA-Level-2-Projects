PHASE 12 — Live view mode, so a browser window mirrors server-side changes for screen recording.

## OBJECTIVE
Let the page reflect state changes that were driven through the API rather than through the UI, so a
screen recorder captures the demo unfolding in a browser window nobody is clicking.

## STEP 0 — COMPREHENSION CHECK (before writing code)
Restate under 250 words: (a) files you will modify, (b) why polling must be opt-in rather than
always on, (c) the one behaviour that must not change. Flag ambiguity rather than guessing.

## TOKEN CONSERVATION
ZERO live API calls. `AMG_OFFLINE` defaults true. Do not disable it or the socket guard.

## WHY
The demo is being recorded for a capstone video. The presenter's visible browser needs to show
memories appearing, conflicts flagging, deletions cascading and the chain breaking, while those
actions are triggered through the HTTP API from outside the browser. Today the page only updates in
response to its own button clicks, so an API-driven run looks like nothing is happening.

## THE CHANGE

### Opt-in live view
Enable with the query string `?live=1` (optionally `?live=2000` to set the interval in ms).
**Default OFF.** Never poll unless explicitly requested — an always-polling page would add constant
background requests during a normal demo and could mask a genuine refresh bug.

When enabled:
- Poll every 1500ms by default (clamp 500-10000ms).
- On each tick refresh exactly what the existing refresh path already refreshes: the memory table,
  the audit list, both tab count badges, the chain summary, the provider indicator and the budget.
  **Reuse the existing refresh functions — do not write a second rendering path.**
- Keep the active tab as-is. Polling must never switch tabs or steal focus.
- If a request fails, skip that tick silently and continue; never surface an error toast on a poll.

### A visible indicator that live view is on
Show a small, clearly-labelled marker in the status bar, e.g. a pill reading `LIVE VIEW` with a
subdued pulsing dot. This matters for honesty: someone watching the recording should be able to tell
this window is auto-refreshing rather than being clicked. Do not make it flashy - it should read as
a status, not a feature.

### Highlight what changed
So the recording reads as events rather than a slideshow, briefly highlight newly appeared rows:
- A memory row that was not present on the previous tick gets a short background flash (~1.5s).
- Likewise a new audit row.
- Reuse the existing count-badge flash styling for consistency.
Do not animate on the first tick after load, or everything flashes at once.

## WHAT MUST NOT CHANGE
- No API endpoints, governance rules, offline enforcement or budget behaviour.
- Without `?live=1` the page behaves exactly as it does today, with no extra requests.
- The Phase 9 labels, Phase 11 tabs, counts and auto-switch behaviour.

## TESTS
- Served HTML/JS contains the live-view opt-in and it is disabled by default (assert the default
  path does not start a timer).
- A test asserting the poll interval is clamped to the documented range.
- Existing endpoint, scenario and layout tests pass unchanged.

## ACCEPTANCE CRITERIA
1. `.venv/Scripts/python.exe -m pytest -q` passes with 0 failures.
2. `?live=1` polls and refreshes; no query string means no polling at all.
3. Polling never changes the active tab or focus.
4. New rows flash briefly; nothing flashes on first load.

## OUTPUT CONTRACT
You CANNOT run Python or a browser (see AGENTS.md). State what you changed, what remains unverified,
and confirm zero live API calls. Do not claim tests pass.
