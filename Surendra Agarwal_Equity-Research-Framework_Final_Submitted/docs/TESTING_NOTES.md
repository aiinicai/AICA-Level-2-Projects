# Testing Notes & Final Self-Review

This document does two things: states plainly what has and hasn't been
verified against live external services, and walks through the original
project spec's closing self-review checklist item by item, honestly.

Per this project's own "no fabricated data" principle, nothing below claims
verification that didn't actually happen.

---

## Real Findings From the Project Owner's Own Testing

Worth recording explicitly, per this project's "no fabricated success"
principle applied to its own history: on 2026-08-12, the project owner
ran the full suite on their real Windows/Python 3.13 machine and hit 3
failures that had never appeared in this development environment.

### First finding: Streamlit version drift

Root
cause: this environment had picked up an unpinned, newer Streamlit
version (1.61.1) instead of the actually-pinned `streamlit==1.41.1` in
`requirements.txt` — a real process gap (my own test verification had
been running against the wrong version). Once reproduced against the
exact pinned version, two distinct problems were confirmed:

1. **A genuine application bug**, not just a test artifact: the sidebar's
   Save Session control called `dict(st.session_state)` to build its
   snapshot. Since the sidebar renders before the current page's body,
   this could execute before that page's dynamic widgets (e.g. the
   AI-IDS Score sliders) had been re-declared for the current run —
   `dict(st.session_state)` touches every key present, including those
   not-yet-re-registered widget keys, which Streamlit correctly raises a
   `KeyError` for. This would have crashed the app for real users
   interacting with sliders while a company was loaded. Fixed by
   building the snapshot from an explicit whitelist of tracked session
   keys (`session_io.TRACKED_SESSION_KEYS`) via `.get()` on each, rather
   than ever converting the entire `session_state`.
2. **A test-only API compatibility issue**: `at.sidebar.download_button`
   doesn't exist as a typed accessor in Streamlit 1.41.1's `AppTest`
   (added in a later version); the generic `at.get("download_button")`
   lookup is the correct call for this pinned version.

Both are fixed and verified against `streamlit==1.41.1` specifically,
not just "some recent version." This episode is itself the clearest
demonstration in this whole project of why the "confirmed on the
project owner's real machine" verification tier matters more than
anything achievable in the development sandbox alone.

### Second real finding: yfinance version incompatibility

On the same date, the project owner ran `scripts/verify_yfinance_live.py`
(a one-time live-verification script — see below) against the originally-
pinned `yfinance==0.2.51`. All three tests failed with
`Expecting value: line 1 column 1 (char 0)` — the signature of Yahoo
Finance returning an empty response body, caused by a crumb/cookie
anti-bot requirement that older yfinance versions can't satisfy. This
was a genuine external-service compatibility problem, not a bug in this
project's own `YFinanceProvider` code — its error handling caught the
failure correctly and raised a clear `MarketDataError` rather than
crashing or returning fabricated data, exactly as designed.

Upgrading to `yfinance==1.5.2` (now the pinned version in
`requirements.txt`) resolved it completely. Re-running the script
produced a real, successful current-price fetch and two successful
historical-data fetches (22 rows for 30 days, 1,237 rows for 5 years),
and — most convincingly — **the live-fetched close price for
2026-08-10 matched the bundled CSV's value for that same date exactly**,
confirming this is genuinely correct market data, not a coincidental
non-error.

### Third finding: OpenAI live verification — a clean success

Also on 2026-08-12, the project owner ran `scripts/verify_openai_live.py`
against a real `OPENAI_API_KEY`. Unlike the two findings above, this one
required no fix — every test passed on the first real run, closing out
the last unverified external integration in this project:

- Basic connectivity/auth: successful, model resolved to `gpt-4o-2024-08-06`.
- Document analysis: correctly extracted a real, page-sourced governance
  claim ("67% of the directors at Sona Comstar are independent directors")
  from the actual bundled annual report.
- Pledge disclosure extraction — the most demanding test in this project:
  the real filing discloses a pledge on an *upstream* holding entity's
  shares (Singapore VII Topco III Pte. Ltd.), not on Sona BLW's own
  shares — a distinction the extraction prompt (see
  `app/ai/prompts.py::build_pledge_disclosure_prompt`) was specifically
  written to enforce. The live model made that distinction correctly on
  every one of the 5 relevant pages it found, phrasing it independently
  each time ("pledge on upstream entity shares", "not target company
  shares", "Singapore Topco shares, not the target company shares"),
  and the summarized result landed on the correct `latest_pledge_pct = 0`.
  This had only ever been verified against `FakeLLMClient` test doubles
  before this run — seeing the real model reach the same correct
  conclusion independently is meaningfully stronger evidence than any
  amount of mocked testing could provide.

### Fourth finding: `streamlit run` sys.path bug (a real usage bug, not a testing artifact)

Also on 2026-08-12, immediately after the OpenAI live verification
succeeded, the project owner tried to actually launch the dashboard for
the first time via `streamlit run app\main.py` and hit
`ModuleNotFoundError: No module named 'app'`. Root cause: Streamlit's
script runner adds only the *script's own directory* (`app/`) to
`sys.path` when it executes a file directly — not the project root
above it. Since every import in this codebase is absolute
(`from app.ui.dashboard import run`, etc.), Python couldn't find a
top-level package called `app` from a `sys.path` that only contained
`app/` itself.

This is a structurally important finding: it is a class of bug that
`AppTest` **cannot** catch by construction, no matter how thoroughly
it's used. `AppTest` runs the target script in-process, inheriting
whatever `sys.path` the pytest process itself was already invoked
with — which already includes the project root, because that's how
pytest was launched. Every one of this project's ~30 `AppTest`-based
tests had `sys.path` set up correctly for reasons that have nothing to
do with the fix being tested, and would have kept passing regardless of
whether this bug was present or fixed.

Fixed by inserting the project root into `sys.path` at the very top of
`app/main.py`, before any `app.*` import is attempted — verified
against a genuinely separate subprocess (not `AppTest`) with `sys.path`
constrained to exactly what Streamlit provides, both from the project
root and from a completely different working directory. A permanent
regression test (`tests/unit/test_dashboard.py::TestRealStreamlitRunSysPath`)
now reproduces this exact scenario via `subprocess.run()` rather than
`AppTest`, specifically so this class of bug is caught automatically
going forward — confirmed to actually catch the original bug by
temporarily reverting the fix and re-running the test, which failed
with the identical `ModuleNotFoundError` the project owner saw.

### Fifth finding: `UnboundLocalError` from a redundant local import shadowing a module-level one

Immediately after the sys.path fix above let the app launch successfully
for the first time, the project owner tried the Promoter Holding/Pledge
manual-entry checkbox flow and hit
`UnboundLocalError: cannot access local variable 'compute_all_shareholder_metrics'
where it is not associated with a value`. Root cause: `company_input.py`'s
`render()` function had a **redundant local import** of
`compute_all_shareholder_metrics` inside the shareholding-pattern-CSV-
upload branch, even though the same name was already imported at module
level at the top of the file. Python's scoping rules mean a name
assigned *anywhere* inside a function — including via a local `import`
statement inside a conditional branch that may never execute — is
treated as local for the **entire function**. Since the manual-entry
checkbox flow never touches the CSV-upload branch, that local import
never ran, and the later reference (in the "Apply Promoter Data" button
handler, a different branch further down the same function) found an
unassigned local variable instead of falling back to the perfectly
good module-level import.

A systematic check (`ast`-based, comparing every module-level import
name against every locally-indented import name across all UI page
files) confirmed this was an isolated instance, not a repeated pattern
elsewhere. Fixed by removing the redundant local import. Verified two
ways: (1) reproduced the exact real UI flow via `AppTest` — load a
company, check "no promoter pledge," click "Apply Promoter Data,"
*without* ever touching the shareholding CSV uploader in the same
run — confirming it no longer crashes; (2) added a permanent regression
test doing exactly that, then proved the test actually catches the bug
by temporarily re-introducing the redundant import and confirming the
test failed with the identical `UnboundLocalError` and traceback shape
the project owner saw, before restoring the fix.

### Sixth finding: Windows file-locking `PermissionError` on peer Excel uploads

The project owner then hit `PermissionError: [WinError 32] The process
cannot access the file because it is being used by another process`
when uploading peer companies' Excel files on the Valuation
Dashboard's Peer Comparison feature and clicking "Compute Peer
Comparison." Root cause: `loaders.py::load_screener_excel()` opens the
workbook via `openpyxl.load_workbook(..., read_only=True)` but never
explicitly closed it. openpyxl's read-only mode keeps an underlying zip
file handle open internally, and relying on Python's garbage collector
to release it is unreliable for immediate cleanup — this is a
documented openpyxl caveat, not a Python bug. Streamlit's
`tempfile.TemporaryDirectory()` (used to stage uploaded peer files) then
tried to delete the directory immediately after
`build_peer_multiples_from_workbook()` returned, while the file handle
was potentially still open.

This is another OS-boundary finding, same category as the earlier
Streamlit sys.path issue: **Linux permits deleting a file that's still
open** (the file descriptor stays valid even after the directory entry
is removed) — completely harmless there, which is exactly why this was
never caught in the Linux development environment despite extensive
testing. **Windows locks an open file against deletion outright.**

Fixed by wrapping the entire function body in a `try/finally` and
calling `wb.close()` in the `finally` block, guaranteeing the handle is
released whether the function returns normally or raises partway
through (e.g. a missing "Data Sheet" tab). Verified three ways: (1) a
mock-based spy test confirming `close()` is actually invoked exactly
once on the success path; (2) the same on the exception path
specifically — proving a bare `except` without `finally` would not have
been sufficient, since the raise happens *before* where a trailing
`close()` call would sit; (3) confirmed the tests correctly fail (not
just pass trivially) by temporarily removing the `finally` block and
observing 2 of 3 new tests fail with `AssertionError: Expected 'mock'
to have been called once. Called 0 times.` — with the third
(OS-level file-deletion) test passing even on the broken code,
correctly demonstrating in the test suite itself exactly why this bug
could hide on Linux but not on Windows.

### Seventh finding: environment-key test isolation, twice in a row

Adding the Gemini provider (2026-08-13) reproduced the exact same
category of test-isolation bug found once already for
`OPENAI_API_KEY`: a test asserting "no API key configured -> clear
error" only cleared `OPENAI_API_KEY` from the test environment, not the
newly-added `GOOGLE_API_KEY` — so once the project owner's real `.env`
had both keys configured, that test would have silently made a real API
call instead of testing the intended error path, exactly like before.
This was caught *proactively* this time (by deliberately running the
full suite with both fake keys injected into the environment before the
change was ever shared) rather than by a real failure, and fixed by
extending the existing `no_openai_key` fixture into a `no_llm_key`
fixture that clears both keys. Worth recording as a pattern, not just a
one-off: any test asserting "no provider configured" needs to account
for every provider this project supports, not just the one that existed
when the test was written.

**Update (see Tenth finding below): this fix was later found to be
incomplete** — clearing `os.environ` alone does not account for
`pydantic-settings` reading a real `.env` file on disk directly,
independent of `os.environ`.

### Eighth finding: pydantic version conflict from adding google-genai

Immediately after receiving the Gemini provider addition, the project
owner ran `pip install -r requirements.txt` on their real machine and
hit a hard dependency-resolution failure: `google-genai==2.18.0`
requires `pydantic>=2.12.5,<3.0.0`, but this project had `pydantic`
pinned at `2.10.6` since early milestones — well below that floor.
`pydantic-settings==2.7.1` and `openai==1.59.6` both tolerate a wide
range of `pydantic` versions, so the actual conflict was narrowly
between the old pin and the new dependency, not a three-way clash.

Fixed by testing the resolution directly rather than guessing at a
version number: installed the four directly-conflicting packages in an
isolated virtual environment with an open `pydantic` version range and
let `pip` resolve it, which landed on `2.13.4` — then pinned exactly
that. Verified two ways beyond the isolated four-package test: (1) the
*entire* `requirements.txt` (all ~70 packages) installed cleanly from
scratch in a second isolated environment, confirming no other package
in the file has an incompatible `pydantic` constraint; (2) the full
701-test suite passed using that fresh environment's own Python
interpreter, not just the already-populated development sandbox —
confirming the `pydantic` 2.10 → 2.13 jump introduces no behavioral
break anywhere in this codebase's actual model definitions.

### Ninth finding: Gemini model ID retired for new API keys within weeks

The project owner ran `scripts/verify_gemini_live.py` (2026-08-13) with
a real, freshly-created `GOOGLE_API_KEY` and got a live 404: `"This
model models/gemini-2.5-flash-lite is no longer available to new
users."` — the model this project had defaulted to since the Gemini
provider was added only a day earlier. Researched rather than
guessed: confirmed via multiple independent, recently-published sources
(within the last 2-3 weeks of the check) that the current free-tier
Flash-family lineup has moved to `gemini-3.6-flash`, `gemini-3.5-flash`,
and `gemini-3.5-flash-lite` — with `gemini-2.5-flash-lite` specifically
matching the live error's "no longer available to new users" framing
(likely a soft deprecation: existing users/keys may retain access,
new keys don't). Also confirmed, so as not to over-correct: the
underlying `generateContent` API this project's `GeminiClient` actually
calls remains fully supported by Google — despite a newer "Interactions
API" being promoted for agentic workflows, no architectural change was
needed, only the specific model ID string.

Fixed by updating the default `gemini_model` to `gemini-3.5-flash-lite`
everywhere it appeared (config default, `.env.example`, tests), and —
since this is now the second time a fast-moving AI-provider model name
has needed a same-week correction (see the OPENAI_MODEL comment
warning about the same pattern) — added an explicit comment at the
config default itself, so the next time a model ID goes stale, whoever
hits it knows exactly where to check rather than assuming something
else is broken. This has NOT yet been re-verified with a real live
call — the project owner would need to re-run
`scripts/verify_gemini_live.py` to confirm `gemini-3.5-flash-lite`
itself is actually reachable with their key, which is why
`GeminiClient` remains listed as unverified below rather than moved
to "confirmed." **Update: confirmed the next day (2026-08-13) — see
the "What Has Been Verified" table below, and the Tenth finding for
what came up along the way.**

### Tenth finding: the Seventh finding's fix was itself incomplete — `os.environ` isn't the whole picture

Immediately after receiving the Gemini model-name fix, the project
owner ran `pytest` directly (not the live-verification scripts) and hit
7 failures — all instances of the exact "no key configured" test-
isolation bug from the Seventh finding, which was supposedly already
fixed. Investigated properly rather than re-applying the same fix
harder: `Settings` is configured with
`env_file=str(_PROJECT_ROOT / ".env")` — an **absolute path to the
real `.env` file on disk** — so `pydantic-settings` reads that file
**directly** when `Settings()` is constructed, entirely independent of
`os.environ`. The Seventh finding's fix (`monkeypatch.delenv(...)`)
only ever clears shell-level environment variables; it does nothing to
stop `pydantic-settings` from reading the same keys straight out of a
real `.env` file sitting in the project root — which is exactly what
the project owner's actual machine has, with real working keys. This
had never surfaced in the development sandbox because no real `.env`
file ever existed there; every test always used shell-level env var
injection to *simulate* the target machine, which happened to be
insufficient to catch this specific gap.

Reproduced deliberately before attempting a fix: created a real `.env`
file with fake-but-realistic keys in the sandbox, confirmed the exact
same 6-7 test failures the project owner saw, then fixed it by
additionally redirecting `Settings.model_config["env_file"]` to a
nonexistent path for the duration of the fixture (via
`monkeypatch.setitem`, which reverts automatically), on top of the
existing `os.environ` clearing. Verified the fix properly closes the
gap — not just papered over the one reproduction — by running the full
701-test suite in *three* distinct scenarios: no `.env` file and no
shell env vars, no `.env` file with shell env vars set, and (the
scenario that actually broke) a real `.env` file present on disk with
real-looking keys. All three: 701/701 passing.

### Eleventh finding: `google-genai` SDK's own internal retries silently absorbed minutes per call

The project owner processed a real peer-comparison batch (two real
Excel files, then a Gemini extraction run) and reported it "taking very
long," sharing logs showing 10 successive Gemini calls with strikingly
consistent ~2m51s gaps between each — far beyond this project's own
0.5s pacing delay. Investigated rather than assumed: the `google-genai`
SDK has its **own internal retry-with-backoff hidden inside
`generate_content()`** — up to 4 attempts by default, backoff capped at
60 seconds *each* — confirmed via Google's own retry-strategy
documentation. `GeminiClient` had never configured this, so on an
account being rate-limited by the free tier, each call was silently
absorbing close to its full retry budget (consistent with the observed
~171-second gaps: several retries each landing near the 60s cap)
*before* ever raising an exception back to this project's own code.

This meaningfully undermined `FallbackLLMClient`'s actual purpose: it
can only fall back to OpenAI *after* Gemini's own call raises — but
with the SDK's internal retries silently eating minutes first, a "fast
fallback" took nearly 3 minutes per page instead of seconds. Fixed by
passing `http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1),
timeout=30_000)` when constructing the Gemini client — confirmed these
are the exact field names via `types.HttpRetryOptions.model_fields` and
`types.HttpOptions.model_fields` on the actually-installed SDK version,
not assumed from documentation alone. This disables the SDK's own
retry loop entirely, so a rate-limit or transient error now surfaces to
this project's own code within the 30-second timeout, letting the
already-built, already-tested pacing (`delay_seconds`) and fallback
(`FallbackLLMClient`) logic handle recovery the way they were actually
designed to — not fighting against a second, hidden retry loop with a
much longer timescale. Verified with a dedicated regression test that
inspects the actual constructor arguments passed to `genai.Client(...)`,
confirmed to genuinely catch the regression by temporarily reverting
the fix and observing the test fail with `KeyError: 'http_options'`,
then restoring it.

---

## What Has Been Verified, and How

| Component | Verified how |
|---|---|
| Data ingestion (Excel parsing, unit conversion) | Real 10-year Sona BLW Screener.in export; specific values cross-checked by hand (e.g. FY2026 Sales = Rs 4,123.67 cr) |
| Validators | Real data (found and correctly flagged a genuine IPO share-count discontinuity); synthetic edge cases (zero/negative denominators, duplicates) |
| Fundamentals/cash flow/working capital | Real Sona BLW data; several results cross-checked against independently known facts (e.g. computed EPS of Rs 10.40 matches the company's actual reported EPS) |
| Technical indicators | Independently-coded reference calculations (a separate pure-Python Wilder RSI implementation, not the same pandas code path) plus exact boundary cases (all-gains series -> RSI=100) |
| DCF | Hand-worked 2-year example isolating the discounting/terminal-value math from other line items |
| Investment scoring | Hand-computed renormalization math verified to 2 decimal places |
| Document extraction / quarantine | Real 194-page Sona BLW annual report PDF; adversarial injection-pattern text (synthetic, since real injection attempts aren't sourced from a live document) |
| Report generation (Markdown + DOCX) | Real assembled Sona BLW data through the full pipeline; DOCX specifically verified by rendering to PDF and visually inspecting the images (this caught and fixed a real bug — a stray table-separator row leaking into the rendered table) |
| Streamlit dashboard | Streamlit's own `AppTest` framework, actually launching the app and navigating every page (this caught and fixed a real bug — the app was executing twice due to a `__name__` handling error) |
| **Python 3.13 / Windows 64-bit specifically** | **Confirmed by the project owner's own runs** on a real Windows 10/11 machine with Python 3.13 — `pytest` runs shown passing (198, 230, 439, 606, 607, 608, 617, 620, 642, 660, 679, 699, 701, 702, 727 tests, at successive milestones) directly in their terminal, not just claimed by the development environment (which runs Python 3.12 on Linux). Intermediate counts (454, 470, 490, 503, 520, 541, 556, 570, 589) reflect additions verified in the development environment only, between confirmed real-machine runs. |
| **`OpenAIClient` (live GPT-4o calls)** | **Confirmed via a real live test** on the project owner's machine (2026-08-12, `scripts/verify_openai_live.py`), model resolved to `gpt-4o-2024-08-06`. Three real code paths tested: basic completion, document analysis (extracted a real, correctly-sourced governance claim from the actual annual report), and pledge disclosure extraction. The pledge test is the most demanding real check in this project — the real filing discloses a pledge on an *upstream* holding entity's shares, not Sona BLW's own shares, and the live model correctly made that distinction on every one of the 5 relevant pages, each in its own words, landing on the correct `latest_pledge_pct = 0`. |
| **`YFinanceProvider` (live Yahoo Finance download)** | **Confirmed via a real live test** on the project owner's machine (2026-08-12, `scripts/verify_yfinance_live.py`) — see the version-pin fix described above. Cross-validated: the live current price and the bundled CSV's price for the same date matched exactly. |
| **`GeminiClient` (live Gemini API calls)** | **Confirmed via a real live test** on the project owner's machine (2026-08-13, `scripts/verify_gemini_live.py`), model `gemini-3.5-flash-lite`. All three real code paths succeeded: basic completion; document analysis (extracted a detailed, accurate governance claim — 67% independent directors, 33% women independent directors, 4 of 5 committees independent-chaired — arguably richer than the equivalent OpenAI run); and pledge disclosure extraction, the most demanding check in this project. Gemini correctly handled a nuance neither prior verification run explicitly exercised: page 1 (a cover letter with no specific percentages) was correctly classified `not_applicable` rather than guessed at, while pages 2-6 all independently identified the upstream-vs-target company distinction in their own words, landing on the correct `latest_pledge_pct = 0.0` — matching both the real-world fact and the earlier OpenAI verification exactly. This closes out the last originally-unverified external integration in this project. |

## What Has NOT Been Verified

Stated plainly, not buried — as of 2026-08-13, this list is down to one item:

- **`RediffMoneyProvider`** — the development environment has no network
  route to money.rediff.com, and it hasn't been live-tested on the project
  owner's machine either (no pressing need arose, since `CSVPriceProvider`
  and now-confirmed `YFinanceProvider` both cover price data). The
  row-parsing regex was verified against synthetic HTML built from a
  *real, confirmed* markup sample (from the project owner's own working
  VBA macro), but no live scrape has been performed. This remains the
  one honest gap in this project's external-service verification.
- **Streamlit's actual browser rendering** — `AppTest` verifies the app
  runs without a Python exception and that widgets/text are present in the
  simulated session state, but does not render actual pixels the way a
  real browser would. The DOCX visual verification (converting to PDF and
  viewing images) is a stronger form of this same idea, done specifically
  for the report output.

---

## Final Self-Review Checklist

Walking through the original spec's closing checklist honestly:

- [x] **Python 3.13 compatibility** — confirmed on the project owner's real
      Windows machine (see table above), not just assumed.
- [x] **64-bit Windows compatibility** — same.
- [x] **Modular architecture** — `app/core`, `app/data`, `app/documents`,
      `app/analysis`, `app/valuation`, `app/scoring`, `app/ai`,
      `app/reports`, `app/ui` are cleanly separated; `app/analysis` and
      `app/valuation` have zero imports from `app/ai`.
- [x] **Type hints** — used throughout; Pydantic models enforce types at
      runtime, not just as annotations.
- [x] **Error handling** — a deliberate recoverable/fatal exception
      hierarchy (`app/core/exceptions.py`); nothing silently swallows an
      error without a status code or log entry.
- [x] **Logging** — `logging` used throughout, no `print()` statements in
      application code; centralized config in `app/core/logging_config.py`.
- [x] **Configuration management** — `.env`-driven via `pydantic-settings`;
      startup validation on the score weights.
- [x] **No hard-coded secrets** — confirmed by inspection; `.env.example`
      contains placeholders only.
- [x] **Financial calculation tests** — 727 tests total, the large majority
      of which are financial/technical/valuation/scoring calculations
      against real or hand-verified data.
- [x] **Technical-analysis tests** — independently-coded reference RSI,
      exact boundary cases, real 5-year price history.
- [x] **Valuation tests** — hand-worked DCF example, real-data multiples
      cross-checks.
- [x] **Scoring tests** — hand-computed renormalization math.
- [x] **Missing-data handling** — tested explicitly and repeatedly (e.g.
      the empty-risk-list-is-UNAVAILABLE-not-100 test, the
      never-zero-fill investment score test).
- [x] **Source traceability** — every `MetricResult`/`DocumentEvidence`/
      `AIInterpretation` carries lineage fields (`evidence_ids`,
      `source`, `page_number`) by construction.
- [x] **AI hallucination controls** — deterministic layer never imports
      from `app/ai`; every AI output is confidence-labeled and Level-2
      tagged; the risk-extraction prompt explicitly instructs "never infer
      a risk the excerpt does not actually mention."
- [x] **Prompt-injection controls** — two layers: pattern-based quarantine
      (`app/documents/quarantine.py`, tested against adversarial text) and
      structural prompt framing (`<document_excerpt>` delimiters,
      documented as the primary defense with quarantine as secondary).
- [x] **Human-in-the-loop** — `HumanReview` objects only created by
      explicit action; report checklist defaults every item to
      "not yet reviewed."
- [x] **Report generation** — all 19 spec sections implemented in both
      Markdown and DOCX, verified against real data and (for DOCX)
      visually inspected.
- [x] **README** — this repository's `README.md`.
- [x] **requirements.txt** — pinned versions throughout.
- [x] **pyproject.toml** — present, includes pytest configuration.
- [x] **.env.example** — present, placeholders only, documents every
      variable's purpose and default.
- [x] **Sample dataset** — real Sona BLW financials (Excel), price history
      (CSV), and annual report (PDF) bundled in `data/sample/`.
- [x] **Test suite** — 727 tests as of this writing, covering unit,
      integration-style (real multi-file pipeline runs), and edge cases.

### Items that remain partial or out of scope

- **Comprehensive risk framework (Module 8)** — implemented as a hybrid
  (deterministic financial rules + AI-assisted qualitative extraction), not
  the full seven-category structured framework the spec describes in
  detail. Category coverage depends on what the AI extraction actually
  finds in supplied documents; there's no guarantee every category gets
  populated.
- **Peer relative valuation** — the engine (`app/analysis/peers.py`) is
  built and tested, but no live peer-data source is wired in; peer
  multiples must be supplied manually (by design — the project deliberately
  never fabricates or scrapes peer data without an explicit, sourced input).
- **Live external service verification** — see the "What Has NOT Been
  Verified" section above. This is the most significant honest gap: three
  live integrations (Yahoo Finance, Rediff, OpenAI) are code-complete and
  unit-tested with mocks/fakes, but their first real-world exercise happens
  on the end user's machine, not in this development environment.
- **Notebooks / exploratory analysis** — `notebooks/` exists as a folder
  per the planned structure but is currently empty; no exploratory
  notebooks were part of any milestone's deliverables.
