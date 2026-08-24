PHASE 8 FIX — the bundle secret-check false-positives on the Python module `amg.db`.

## OBJECTIVE
Make `build_exe.py` complete successfully WITHOUT weakening any secret-exclusion rule.

## STEP 0 — COMPREHENSION CHECK (before writing code)
Restate under 250 words: (a) the root cause, (b) why the fix must NOT be "remove the .db rule",
(c) what you will change and what test you will add. Flag ambiguity rather than guessing.

## TOKEN CONSERVATION
Make ZERO live API calls. Do not disable `AMG_OFFLINE` or the socket guard.

## THE FAILURE
The build produced `dist/AIMemoryGovernance.exe` (54 MB) but then correctly failed closed:

```
BUNDLE CONTENT CHECK FAILED: prohibited Python module 'amg.db'.
```

## ROOT CAUSE
`_is_prohibited_archive_name()` in `build_exe.py` is applied to TWO different namespaces:

1. **CArchive TOC entries** — real file paths. Here `foo.db` genuinely means a SQLite database and
   must stay prohibited.
2. **PYZ archive entries** — dotted Python MODULE names. Here `amg.db` is simply the module
   `src/amg/db.py`, which is legitimate source code that MUST be bundled for the app to run.

The rule `basename.endswith(".db")` cannot tell those apart, so it rejects our own database module.

## THE FIX — split the predicate, do not relax it
Replace the single predicate with two, and apply each only to its own namespace:

**`_is_prohibited_data_name(name)`** — for CArchive TOC entries. Keeps every existing rule
unchanged: `.env` (and `.env.*` except `.env.example`), `.amg_usage.json`, `*.db`, `*.sqlite*`,
anything under `.git/` or `.amg_cache/`, and any `tests` path component.

**`_is_prohibited_module_name(name)`** — for PYZ module names. Module-appropriate rules ONLY:
reject a module whose dotted path has a top-level or any component equal to `tests`, `_pytest`, or
`pytest` (e.g. `tests.test_phase1`, `amg.tests.helpers`). It must NOT apply any file-extension rule,
because a dotted module name is not a filename. `amg.db`, `amg.audit`, `amg.web.app` must all pass.

Be careful with the existing `"tests" in module_parts` check: `amg.db` splits to `['amg','db']`, so
that part is fine — it is only the `.db` suffix rule that misfires. Keep the tests exclusion in BOTH
predicates.

**The secret byte-scan (`_scan_bytes`) must continue to run over every entry in both namespaces,
unchanged.** That is the control that actually catches leaked keys; this fix only corrects which
NAMES are considered prohibited.

## TESTS — add to `tests/test_phase8_packaging.py`
- `_is_prohibited_module_name("amg.db")` is False; so are `amg.audit`, `amg.web.app`, `amg.config`.
- `_is_prohibited_module_name("tests.test_phase1")` is True; so are `_pytest.fixtures`,
  `pytest`, and `amg.tests.helpers`.
- `_is_prohibited_data_name("memory.db")` is True; `"amg_memory.sqlite3"` is True; `".env"` is True;
  `".env.keys-backup"` is True; `".amg_usage.json"` is True; `".env.example"` is False.
- `_is_prohibited_data_name("amg/web/static/app.js")` is False (a legitimately bundled asset).
- A regression test asserting the two predicates are actually distinct functions and that the data
  predicate still rejects `*.db` — so nobody "fixes" this later by deleting the rule.

## ACCEPTANCE CRITERIA
1. `.venv/Scripts/python.exe -m pytest -q` passes with 0 failures.
2. No secret-exclusion rule is removed or weakened; `*.db` data files are still rejected.
3. `_scan_bytes` still runs over every CArchive entry and every PYZ module.

## OUTPUT CONTRACT
You CANNOT run Python or PyInstaller (see AGENTS.md). State what you changed, what remains
unverified, and confirm zero live API calls. Do not claim tests pass or that a build succeeded.
Claude Code runs the build and the suite and will report failures back to you.
