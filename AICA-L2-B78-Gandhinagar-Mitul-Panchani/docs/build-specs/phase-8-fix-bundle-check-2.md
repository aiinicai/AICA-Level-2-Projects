PHASE 8 FIX 2 — the module check still false-positives, and it fails one-at-a-time.

## OBJECTIVE
Two changes: (1) stop rejecting legitimate third-party modules named `tests`, and (2) make the
checker report ALL violations at once instead of failing on the first, so this stops costing a
rebuild per discovery.

## STEP 0 — COMPREHENSION CHECK (before writing code)
Restate under 250 words: (a) why `jinja2.tests` is legitimate and must be allowed, (b) the precise
new rule, (c) why collect-all-then-report matters here. Flag ambiguity rather than guessing.

## TOKEN CONSERVATION
ZERO live API calls. Do not disable `AMG_OFFLINE` or the socket guard.

## THE FAILURE
After the previous fix, the rebuild got further and then failed:

```
BUNDLE CONTENT CHECK FAILED: prohibited Python module 'jinja2.tests'.
```

`jinja2/tests.py` is part of Jinja2 itself — it defines the template test functions (`is_defined`,
`is_odd`, and so on). Jinja2 does not work without it, and the web UI does not work without Jinja2.
It has nothing to do with our test suite.

## DEFECT A — the module rule is too broad
`_is_prohibited_module_name()` currently rejects a module if ANY dotted component is `tests`,
`_pytest`, or `pytest`. Third-party packages legitimately ship a `tests` submodule.

**New rule: judge only the TOP-LEVEL package.** Reject if and only if the FIRST dotted component is
`tests`, `pytest`, or `_pytest`. So:
- `tests`, `tests.test_phase1`, `pytest`, `_pytest.fixtures` -> REJECT (these are ours / the runner)
- `jinja2.tests`, `voyageai.tests`, `anyio.tests`, `amg.db`, `amg.web.app` -> ALLOW

The purpose of this check is to prove OUR test package (which carries fixtures and scripted persona
data) is not bundled. A vendored library's internal `tests` submodule is a size consideration
handled by the spec `excludes` list, NOT a secret-leak concern. Do not conflate the two.

`_is_prohibited_data_name()` is UNCHANGED — every file rule (`.env`, `*.db`, `*.sqlite*`,
`.amg_usage.json`, `.git/`, `.amg_cache/`, and a `tests` PATH component) stays exactly as-is.
A `tests/` directory in the DATA namespace is still rejected.

## DEFECT B — fail-fast makes this cost one rebuild per discovery
`_inspect_archive()` raises on the first prohibited entry. Each 60-second rebuild therefore reveals
exactly one problem. That is why this has now taken three builds.

Change it to **collect every violation, then raise once** with a complete report:
- Walk all CArchive entries and all PYZ modules, accumulating a list of
  `(namespace, name, reason)` for every violation found.
- Keep running `_scan_bytes` on every entry regardless, and accumulate any secret hits into the
  SAME list, tagged distinctly.
- At the end, if the list is non-empty, raise a single RuntimeError listing all of them, capped at
  say 50 lines with an "and N more" tail so the message stays readable.
- If the list is empty, print a positive confirmation of what was verified, e.g. the number of
  CArchive entries and PYZ modules scanned. A silent pass is a weak signal; say what was checked.

**Any secret hit must remain a hard failure** — collecting them does not soften them.

## TESTS — extend `tests/test_phase8_packaging.py`
- `_is_prohibited_module_name` is False for `jinja2.tests`, `voyageai.tests`, `anyio.tests`,
  `amg.db`, `amg.web.app`.
- It is True for `tests`, `tests.test_phase1`, `pytest`, `_pytest.fixtures`.
- `_is_prohibited_data_name` is still True for `memory.db`, `x.sqlite3`, `.env`,
  `.env.keys-backup`, `.amg_usage.json`, and for a path with a `tests/` component.
- It is still False for `.env.example` and `amg/web/static/app.js`.
- A test proving the collect-all behaviour: feed the violation collector two bad names and assert
  the raised message mentions BOTH, not just the first.

## ACCEPTANCE CRITERIA
1. `.venv/Scripts/python.exe -m pytest -q` passes with 0 failures.
2. No file-level secret rule is weakened; `*.db`, `.env*`, and data-namespace `tests/` still rejected.
3. A secret hit still fails the build hard.
4. The checker reports every violation in one pass.

## OUTPUT CONTRACT
You CANNOT run Python or PyInstaller (see AGENTS.md). State what you changed, what remains
unverified, and confirm zero live API calls. Do not claim tests pass or that a build succeeded.
