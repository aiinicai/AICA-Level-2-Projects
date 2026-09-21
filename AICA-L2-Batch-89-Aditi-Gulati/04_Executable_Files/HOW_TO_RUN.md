# Running SurakshaScan

**What is in this folder**

| File | Purpose |
|---|---|
| `SurakshaScan.exe` | The standalone Windows application — see note below |
| `SurakshaScan_Source.zip` | The complete source code, tests and build files |
| `HOW_TO_RUN.md` | This file |

> **About the executable.** `SurakshaScan.exe` is around 150 MB — too large
> for GitHub, which accepts files of up to 25 MB through the browser. It is
> included in the AICA portal submission. Anyone can rebuild it from the
> source in under five minutes (see *Rebuilding the executable* below).

## Option 1 — the executable (no Python needed)

Double-click **`SurakshaScan.exe`**.

- First launch takes 10–15 seconds while it unpacks.
- Windows **SmartScreen** may warn that the app is unrecognised, because it is
  not code-signed. Choose **More info** → **Run anyway**.
- Windows **Smart App Control**, where enabled, blocks unsigned apps outright
  with no override. On such a machine use Option 2.
- Reports are saved to **Documents\SurakshaScan Reports**.

## Option 2 — from source

Requires Python 3.11 or later. First, right-click **`SurakshaScan_Source.zip`**
→ **Extract All…**. Then:

```
cd SurakshaScan_Source
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m surakshascan.tools.demo
python run.py
```

Or double-click **`Start SurakshaScan.bat`** inside `SurakshaScan_Source` —
it sets up the environment on first run.

## Rebuilding the executable

From `SurakshaScan_Source`, with the environment active:

```
pyinstaller SurakshaScan.spec --noconfirm
```

The result is `dist\SurakshaScan.exe`.

## Running the tests

```
pytest tests -q
```

Expect **87 passed**. If pytest is unavailable, `python tests\run_tests.py`
runs the same suite with a bundled substitute.
