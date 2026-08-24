PHASE 8 — Package the tool as a single portable Windows .exe for distribution.

## OBJECTIVE
Produce a PyInstaller one-file build: a recipient double-clicks `AIMemoryGovernance.exe`, the web UI
opens in their browser, and all 9 scenarios run — with **no Python, no install, no API key, and no
network access required**. Plus a settings panel where a recipient may optionally supply their OWN
Gemini/Voyage keys to enable live mode.

## STEP 0 — COMPREHENSION CHECK (before writing code)
Restate under 400 words: (a) every file you will create or modify, (b) the acceptance criteria,
(c) the single most important constraint and why. Flag ambiguities rather than guessing.

## ABSOLUTE CONSTRAINT — DO NOT SHIP THE OWNER'S SECRETS
The repo `.env` contains the owner's REAL, working Gemini and Voyage API keys. A PyInstaller archive
is trivially extractable — anyone with the exe could read a bundled `.env` in seconds and spend the
owner's free-tier quota.

**The build MUST exclude, and must be PROVEN to exclude:**
`.env`, `.env.keys-backup`, any `.env.*` except `.env.example`, `.amg_cache/`, `.amg_usage.json`,
`*.db`, `*.sqlite*`, `.git/`, and `tests/`.

Write an automated test that inspects the generated bundle/spec and FAILS if any of those are
present, and that scans the built artifact for `GEMINI_API_KEY=` or `VOYAGE_API_KEY=` followed by a
non-empty value. This is the highest-priority acceptance criterion. Nothing else matters if secrets
leak.

## TOKEN CONSERVATION
Make ZERO live API calls. `AMG_OFFLINE` defaults true. Do not disable it or the socket guard.

## 1. `amg_app.py` (repo root) — the frozen entry point
- Detect frozen mode via `getattr(sys, "frozen", False)`; resolve bundled resources from
  `sys._MEIPASS`, falling back to repo paths when running from source. BOTH must work.
- Pick a free localhost port (try 8000, then increment) so an occupied port or a second copy does
  not crash it.
- Start uvicorn programmatically:
  `uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")`.
- Open the default browser at the URL via `webbrowser.open` shortly after startup.
- Print a clear console banner: product name, the URL, "offline mode — no API keys needed", and
  "close this window or press Ctrl+C to stop". Keep the console visible — recipients need to see
  the URL and how to quit.
- Catch startup exceptions and print a readable message plus a "press Enter to close" pause, rather
  than flashing a traceback and vanishing.

## 2. Writable-path handling — CRITICAL, this fails silently if wrong
In a one-file build the app unpacks to a TEMP directory that is deleted on exit. The SQLite DB and
the recipient's saved settings must NOT live there, or every launch starts empty and settings
vanish.

Add to `src/amg/config.py` a `user_data_dir()` returning:
- frozen: `%LOCALAPPDATA%\AIMemoryGovernance\` (create if absent)
- source: the repo root, exactly as today — do NOT change existing development behaviour.

Route `AMG_DB_PATH`, `.amg_cache/` and `.amg_usage.json` through it when frozen. Bundled read-only
resources (templates, static) still resolve from `sys._MEIPASS`.

## 3. Recipient settings panel — their keys, never yours
Add a clearly-labelled "AI provider settings" section to the web UI:
- Show current mode honestly, e.g. "Offline (deterministic) — no API key configured".
- Two password-type fields for the recipient's own Gemini and Voyage keys, plus a model field
  defaulting to `gemini-3.5-flash`.
- Save to `<user_data_dir>/settings.json`, NEVER into the bundle. Reload settings and report the
  newly resolved providers.
- A "Test connection" button making exactly ONE cheap call per provider, reporting success or
  failure plainly. Must respect the daily budget cap.
- A "Clear keys and return to offline" button.
- State plainly in the UI that keys are stored in plain text locally and that this is a demo tool,
  not a credential manager. Honesty about limitations is a project requirement.
- Endpoints: `GET/POST /api/settings`, `POST /api/settings/test`, `POST /api/settings/clear`.

## 4. `AIMemoryGovernance.spec` — the PyInstaller spec
- One-file, console enabled, name `AIMemoryGovernance`.
- `datas`: bundle `src/amg/web/templates/` and `src/amg/web/static/` only.
- `hiddenimports`: uvicorn loads loops and protocols dynamically and static analysis WILL miss them.
  Include at least `uvicorn.logging`, `uvicorn.loops.auto`, `uvicorn.loops.asyncio`,
  `uvicorn.protocols.http.auto`, `uvicorn.protocols.http.h11_impl`,
  `uvicorn.protocols.websockets.auto`, `uvicorn.lifespan.on`, `uvicorn.lifespan.off`.
  If `google.genai` or `voyageai` fail to import when frozen, add theirs too.
- `excludes`: `pytest`, `_pytest`, and other test-only packages, to keep size down.
- Explicitly do NOT add `.env` or anything listed in the ABSOLUTE CONSTRAINT.

## 5. `build_exe.py` (repo root)
- Refuse to run if `.env` would be picked up by the spec (defensive re-check of the constraint).
- Clean `build/` and `dist/`, then invoke PyInstaller with the spec.
- After building, scan `dist/AIMemoryGovernance.exe` for secrets and FAIL loudly if any key material
  or excluded file is found.
- Print the output path and final size.
Add `pyinstaller` to a NEW `requirements-build.txt` — not the runtime requirements.

## 6. `DISTRIBUTION.md` (repo root) — written for recipients, not developers
Plain language, assuming no Python knowledge: what the tool is (3–4 sentences), that it needs no
install and no API key, how to run it, the SmartScreen warning they will see on first launch and why
(unsigned binary) with the "More info → Run anyway" steps, how to try the 9 scenarios, how to
optionally add their own API keys, where data is stored (`%LOCALAPPDATA%\AIMemoryGovernance`), and
how to remove it completely. Include the honest disclaimer that this is a capstone demonstration of
architectural alignment with DPDP principles — NOT a compliance product or certified tool.

## 7. `tests/test_phase8_packaging.py`
Must pass offline, and must NOT require a built exe (skip artifact scans with a clear message when
`dist/` is absent, so the suite stays green pre-build):
- **Secret-exclusion test** — parse `AIMemoryGovernance.spec`; assert no excluded path appears in
  `datas`. This one runs ALWAYS, built or not.
- `user_data_dir()` returns the repo root when not frozen, and a `%LOCALAPPDATA%` path when
  `sys.frozen` is monkeypatched true.
- Settings round-trip: save keys to a temp settings file, reload, confirm resolved providers change;
  clear, confirm it returns to offline.
- `POST /api/settings` with an empty key set does NOT flip the app out of offline mode.
- Settings responses NEVER echo a stored key back in full — masked or omitted only.
- When `dist/AIMemoryGovernance.exe` EXISTS: scan its bytes for `GEMINI_API_KEY=` / `VOYAGE_API_KEY=`
  followed by a non-empty value. Fail if found.

## ACCEPTANCE CRITERIA
1. `.venv/Scripts/python.exe -m pytest -q` passes with 0 failures.
2. The spec provably excludes `.env` and every other listed secret or artifact.
3. Settings are stored outside the bundle and survive a restart.
4. Nothing in Phases 1–7 regresses; the 9 scenarios still pass from source.
5. The app still runs from source (`run_web.py`, `run_demo.py`) — freezing must not break the
   development path.

## OUTPUT CONTRACT
You CANNOT run Python or PyInstaller here (see AGENTS.md). State what you implemented, which
criteria remain unverified, and confirm zero live API calls. Do not claim tests pass or that you
built an exe. Claude Code runs the build and the suite and will send you any failures.
