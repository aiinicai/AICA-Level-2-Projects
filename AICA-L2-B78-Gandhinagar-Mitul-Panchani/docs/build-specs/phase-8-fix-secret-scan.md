PHASE 8 FIX 3 — the secret scan is heuristic-only, so it false-positives and is weaker than it looks.

## OBJECTIVE
Make the secret scan authoritative rather than heuristic: check for the OWNER'S ACTUAL KEY VALUES
first, and keep the pattern scan only as a secondary net that ignores obvious placeholders.

## STEP 0 — COMPREHENSION CHECK (before writing code)
Restate under 300 words: (a) why the current failure is a false positive, (b) why an exact-value
scan is strictly stronger than a pattern scan, (c) why the pattern scan should be KEPT anyway.
Flag ambiguity rather than guessing.

## TOKEN CONSERVATION
ZERO live API calls. Do not disable `AMG_OFFLINE` or the socket guard.

## THE FAILURE
```
BUNDLE CONTENT CHECK FAILED: found 1 violation(s):
- [PYZ secret] 'voyageai.util': a non-empty provider key assignment was found.
```

The match is this line of the vendored library's own source:

```
voyageai/util.py:92:  "or set the environment variable VOYAGE_API_KEY=<API-KEY>). If your API key is stored "
```

That is help text containing the PLACEHOLDER `<API-KEY>`. No secret leaked. The regex
`(?:GEMINI_API_KEY|VOYAGE_API_KEY)[ \t]*=[ \t]*[^\x00\r\n \t][^\x00\r\n]*` matches it because `<` is
a non-space character.

## WHY THIS MATTERS BEYOND THE FALSE POSITIVE
A pattern scan answers "does something LOOK like a key assignment?" The question we actually need
answered is "is the OWNER'S REAL KEY in this artifact?" Those are different, and only the second is
authoritative. Any vendored library that documents its own env var will trip the first forever.

## THE FIX — two-tier scan

### Tier 1 (authoritative): exact-value scan
- At build time, load the real key values from the environment and from `.env` if present
  (`GEMINI_API_KEY`, `VOYAGE_API_KEY`, and any var whose name ends in `_API_KEY` or `_TOKEN`
  with a non-empty value).
- Search every CArchive entry AND every DECOMPRESSED PYZ module for each exact value, and for a
  distinctive middle fragment of each (e.g. `value[8:24]`) to catch partial or re-encoded copies.
- Any hit is a HARD FAILURE.
- **Never print, log, or include a key value in any message.** Report only the variable NAME and the
  entry where it was found.
- If no keys are available at build time (no `.env`, nothing in env), print a clear WARNING that
  tier 1 could not run and that only the heuristic tier applied. Do not silently pass — an absent
  check must announce itself.

### Tier 2 (heuristic net): pattern scan, placeholder-aware
Keep the existing regex, but do NOT flag a match whose value is an obvious placeholder or a
non-literal. Treat a match as a placeholder when the value (after `=`) starts with any of
`<`, `${`, `%`, `{`, or is quoted-and-empty, or matches case-insensitively any of:
`your`, `example`, `placeholder`, `changeme`, `xxx`, `api-key`, `api_key`, `<api-key>`, `none`,
`null`, `sk-...`-style dummy markers. Also ignore a match where the whole line is clearly prose
(e.g. contains "environment variable" or "set the").

Keep tier 2 because it catches a key hard-coded under a DIFFERENT variable name than the ones we
know about — which tier 1 cannot see.

### Reporting
On success, print exactly what was verified, e.g.:
`secret scan OK: N CArchive entries, M PYZ modules; exact-value scan covered K key(s)`.
A silent pass is a weak signal.

## TESTS — extend `tests/test_phase8_packaging.py`
- The placeholder line `"set the environment variable VOYAGE_API_KEY=<API-KEY>"` is NOT flagged.
- `VOYAGE_API_KEY=${VOYAGE_KEY}` and `GEMINI_API_KEY=your-key-here` are NOT flagged.
- A genuine-looking assignment `GEMINI_API_KEY=AQ.AbCdEf123456` IS flagged.
- Tier 1: given a fake secret value injected into a byte payload, the scan flags it; and the raised
  message does NOT contain the secret value itself (assert the value is absent from the message).
- Tier 1 unavailable (no keys loadable) produces a warning, and that warning is asserted.

## ACCEPTANCE CRITERIA
1. `.venv/Scripts/python.exe -m pytest -q` passes with 0 failures.
2. `build_exe.py` completes successfully and prints its positive verification summary.
3. No real key value could pass either tier undetected.
4. No secret value is ever printed in any message or exception.

## OUTPUT CONTRACT
You CANNOT run Python or PyInstaller (see AGENTS.md). State what you changed, what remains
unverified, and confirm zero live API calls. Do not claim tests pass or that a build succeeded.
