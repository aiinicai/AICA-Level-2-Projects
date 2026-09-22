# SurakshaScan v1 — reconstructed baseline

These four files are the original v1 implementation, recovered from the
compiled `SurakshaScan.exe` (PyInstaller / CPython 3.13) by extracting the
CArchive and PYZ and disassembling the embedded bytecode. They are kept
verbatim-in-behaviour as the "before" state for the capstone, so the v2
upgrade can be assessed against a fixed baseline.

Known limitations of v1, all addressed in v2:

1. `ai_analyzer.py` returns hardcoded placeholder text. The headline feature
   of the tool did not exist.
2. The scanner looked for keywords but never read the privacy policy itself.
3. No score, no rating, no prioritisation — the report was a findings dump.
4. No mapping to any specific provision of the DPDP Act or DPDP Rules.
5. No coverage of internal practice, which is where most school risk sits.
6. No evidence retained, so a finding could not be re-verified later.
7. No tests, no error handling beyond a bare `except Exception`.
