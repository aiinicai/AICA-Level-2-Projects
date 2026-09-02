# Stage 17 — EXE Packaging, Installation & Distribution

Status: **Application-side packaging work complete and verified where this environment allows; the actual Windows `.exe` build itself was not — and could not be — produced or executed here.** That limitation is stated plainly in this document's first section rather than discovered partway through, per this stage's own Section 35 instruction ("Do not claim an EXE test was completed if the EXE could not actually be executed").

No Accounting/Audit/Tax/Unified Review/Query/Working Paper logic, Stage 15 security logic, or Stage 16 LAN architecture was modified. No database schema change was made.

---

## 0. Environment limitation, stated upfront

This sandbox is **Linux**, not Windows. PyInstaller does not cross-compile — it can only build an executable for the operating system it runs on, so a Windows `FINsight.exe` cannot be produced here regardless of what else is true. Separately, **PyInstaller is not installed in this sandbox and cannot be installed** (no package-registry network access — the same restriction already disclosed for `waitress` in Stage 16 and confirmed again here with a direct `pip install` attempt). `waitress` itself remains not installed here either.

Given that, this stage's real, honest scope was: (1) reconnaissance to find every actual packaging blocker in the codebase, (2) fix the ones that are genuine application-code issues, not packaging-tool issues, (3) write a complete, reproducible PyInstaller spec ready to run on a real Windows build machine, (4) verify everything in this sandbox that does not require Windows or PyInstaller itself, and (5) document precisely what still needs a real Windows machine to build and test. That is what follows.

---

## 1. Packaging architecture

One PyInstaller `--onedir` build, one entry point (`finsight_app.py`), supporting both Local and LAN mode chosen at runtime — not two separate executables (Section 7). `run.py` and `wsgi_lan.py` remain exactly as they were for manual/dev use; `finsight_app.py` does not replace them, it composes the same underlying pieces (`app.create_app`, the new `app.bootstrap`, and the new `app.launch_common`, factored out of `wsgi_lan.py` so both share it without duplicating logic).

## 2. PyInstaller configuration

`build_exe.spec` (replacing the Stage 2 placeholder comment that lived there before). `--onedir`, entry point `finsight_app.py`, bundles `frontend/templates/`, `frontend/static/`, `alembic.ini`, `database/migrations/`, and `database/seed/` as data files at their original relative paths (so `app/__init__.py`'s existing, unmodified template/static resolution keeps working inside the frozen build), explicit `hiddenimports` for the four seed modules and Alembic's runtime pieces (imported dynamically, not via a plain top-level `import`, so PyInstaller's static analysis would otherwise miss them), and an explicit exclude list plus a build-time warning check for anything that must never ship (a development database, logs, a local secret file, `.env`).

## 3. Build requirements

- Windows (x64)
- Python matching this project's development version (3.11)
- PyInstaller ≥ 6.5, < 7.0 (commented in `requirements.txt` — install separately in the build environment only, never as part of the shipped application's own dependencies)
- Every package in `requirements.txt` actually installed in the build virtualenv

Build command, from the project root, in the build virtualenv:

```
pip install -r requirements.txt
pip install PyInstaller>=6.5,<7.0
pyinstaller build_exe.spec --clean
```

Output: `dist/FINsight/` — `FINsight.exe` plus an `_internal/` folder. After building, **manually copy** `Start_FINsight_Local.bat` and `Start_FINsight_LAN_Host.bat` (both new, at the project root) into `dist/FINsight/`, next to `FINsight.exe` — PyInstaller's own `_internal/` default placement isn't where a double-click-friendly launcher belongs, so this one small manual step is documented rather than fought.

## 4. Application directory structure (after build)

```
FINsight/
    FINsight.exe
    Start_FINsight_Local.bat
    Start_FINsight_LAN_Host.bat
    _internal/              (bundled Python runtime, dependencies, templates, static assets)
```

## 5. Data directory structure (created automatically on first run, next to FINsight.exe — never inside _internal/)

```
FINsight/
    config/
        secret_key
    database/
        finsight.db
    data/
        input/
        processed/
        output/
    logs/
        finsight.log
```

This separation is the real fix Stage 17's own reconnaissance found necessary (see Section 8 of the reconnaissance, and `config.py`'s Stage 17 comment): `config.py`'s `BASE_DIR` — which drives exactly these four paths and nothing else (confirmed by grep before making the change) — now resolves relative to `sys.executable` (the `.exe` itself) when frozen, instead of `__file__` (which would resolve *inside* `_internal/` in a frozen build). Template/static resolution (`app/__init__.py`) is untouched and correctly stays bundle-relative — those are application files, not user data.

## 6. Local mode

`finsight_app.py`, mode `[1]`: binds `127.0.0.1` only (never `0.0.0.0` — Section 13), opens the default browser automatically to `http://127.0.0.1:5000` after a short delay, uses Flask's own built-in server (the same one `run.py` already uses in dev mode — bundled by PyInstaller like any other Python code, so the end user never installs anything separately; this is what "the EXE contains what is required to run FINsight" means, not that Flask disappears from the process).

## 7. LAN mode

`finsight_app.py`, mode `[2]`: activates `LAN_MODE_ENABLED`, refuses the development `SECRET_KEY` fallback (should never actually trigger in the packaged app — see Section 9 below), binds `0.0.0.0` via Waitress, prints the same Local/LAN URL banner Stage 16's `wsgi_lan.py` already prints (now shared via `app/launch_common.py`, not duplicated). Everything Stage 16 built — the shared access password, CSRF, session security, engagement isolation — is unmodified and unweakened; Stage 17 did not touch `app/security/lan_auth.py`, `app/api/access_bp.py`, or `app/services/lan_access_service.py`.

## 8. First-run process

```
FinSight
Offline Financial Review & Compliance Assistant

Initializing FinSight...
Creating local data directories...
Preparing database...
Loading reference data...
FinSight is ready.

How would you like to start?
  [1] Local Computer   - only this computer can access FINsight.
  [2] Private LAN Host - other computers on this trusted network can access FINsight through their browser.
```

No stack trace is ever shown on this console — a top-level exception handler in `finsight_app.py` catches anything unexpected, logs the real detail to `logs/finsight.log`, and prints only a plain-English line naming the exception class, per Section 12.

## 9. Database initialization

New module: `app/bootstrap.py`. On a brand-new install (no `database/finsight.db` yet — checked **before** the database engine is ever touched, not after; see that module's `initialize_database()` docstring for why the ordering matters): creates the schema directly from the current models (`Base.metadata.create_all`), then attempts to record an Alembic "head" stamp so a future update's incremental migrations apply cleanly, then loads reference data via the four existing, unmodified `database/seed/seed_*.py` modules' own idempotent `seed(session)` functions (each already checks-before-insert — nothing here was rewritten). On an existing install, the schema is **never** recreated (verified directly by a test that asserts `Base.metadata.create_all` is not called), Alembic's own `upgrade head` is invoked to apply anything new, and reference data is seeded again (safe — the same idempotent functions, so this only ever adds what's missing, never touches existing engagements/findings/queries/evidence/notes).

Every step that could fail (Alembic missing or erroring, seeding failing) is caught and made non-fatal — logged in full to `logs/finsight.log`, shown to the console only as a plain, honest one-line note — because a reference-data hiccup should never prevent someone from opening their own engagement data.

## 10. Migration handling

Alembic (already an approved Stage 1 dependency) is invoked **programmatically** (`alembic.command.stamp`/`alembic.command.upgrade`, not a shelled-out CLI command), pointed at absolute, bundle-relative paths for `script_location` and the database URL — never relying on the process's current working directory (Section 8's explicit warning; a desktop shortcut can be launched from any "Start in" folder). No destructive operation is ever issued — no downgrade, no drop, no overwrite — matching Section 11's explicit prohibition.

**Real Alembic could not be installed in this sandbox** to exercise this end-to-end. What was verified instead: the full branching logic (new vs. existing database, Alembic present vs. absent, success vs. failure) using a lightweight fake `alembic.command`/`alembic.config` injected into `sys.modules` for the test — proving this stage's own orchestration code is correct, independent of Alembic's own (separately, extensively tested elsewhere) internal behavior. The genuine ImportError fallback path (Alembic actually absent) was exercised for real, since that's this sandbox's actual condition.

## 11. Backup

Unchanged in substance from Stage 15/16: back up `database/`, `data/`, and `logs/` together. Documented in the new `README_DEPLOYMENT.md` in plain, non-developer language. No automatic backup tool was built this stage (Section 25 explicitly allows documenting the manual procedure instead, to avoid scope creep) — a `[Backup FINsight Data]` button was judged unnecessary complexity for V1 given the manual folder-copy procedure is already simple.

## 12. Upgrade

By design (Section 9 above): installing a newer build's `dist/FINsight/` folder over an older one, while preserving the existing `database/`, `data/`, `logs/`, and `config/` folders (which live outside `_internal/` and are therefore never touched by replacing the application files), means existing engagements, findings, queries, evidence references, reviewer notes, settings, and the LAN password all survive untouched — verified at the unit level (Section 10's "existing database is never recreated" test) and by the same live end-to-end run described in Section 17 below. **A literal "install version 1, then install version 2 over it" walkthrough with two real builds was not performed** — there is only ever one build possible in this sandbox (none, in fact — see Section 0), so this specific upgrade scenario needs to be exercised manually once a real Windows build exists; the Manual UAT Checklist (Section 16 below / Section 36 of the governing instruction) includes it explicitly.

## 13. Uninstall

No installer was built this stage (Section 22's own sequencing: "first produce a working portable folder build... optional installer" — the portable build is what this stage delivers; an installer is future scope, not started here, since building and testing an Inno Setup installer requires the same unavailable Windows/PyInstaller execution environment as the EXE itself). "Uninstalling" a portable build is simply deleting the `FINsight/` folder — which **would** delete user data too, since it all lives in that same folder tree by design (the alternative — a system-wide install location — was not chosen, to keep the whole application self-contained and easy to move between computers, per the Blueprint's original portability intent). This is documented as an explicit, disclosed limitation in `README_DEPLOYMENT.md`'s "How to Update FinSight" section: **back up `database/`, `data/`, and `logs/` before deleting or replacing the folder.**

## 14. Browser requirements

Any current Chrome, Edge, or Firefox. No browser extension, no client-side install of any kind — LAN clients need nothing but the URL (Section 16: "Do NOT package a separate client application... No client EXE. No client database.").

## 15. Windows requirements

Documented, not over-claimed (Section 30): this build targets Windows 10/11, x64, matching the Python 3.11 / PyInstaller 6.x combination named in Section 3 above. No specific Windows version was actually tested (see Section 0) — "targets" is stated deliberately, not "is compatible with" or "was verified on."

## 16. Package size

**Not measurable** — no build was produced in this environment (Section 0). A typical Flask + SQLAlchemy + pandas + openpyxl + reportlab PyInstaller `--onedir` bundle is commonly in the 150-300 MB range, given pandas/openpyxl are the largest contributors; this is stated as a rough, honest expectation from the dependency list, not a measured figure, and should not be repeated as one.

## 17. Test results

See the automated results in Section "Automated Test Results" of the completion report below (**699 passed, 3 skipped**), plus this section's own live walkthrough: a real (non-test-config) Flask process was started via `finsight_app.py` in Local mode, against a genuinely fresh temporary copy of the whole project (no pre-existing database), under the sandbox's SQLAlchemy verification shim (the same shim every prior stage's sandbox testing has used) — confirmed: the secret-key file was created with `0600` permissions and reused on a second run; the database schema was created automatically on first run (no manual `alembic`/seed commands run by hand); an engagement was created and successfully appeared on the Dashboard through real HTTP requests (CSRF token scraped and submitted, exactly as a real browser would); reference-data seeding failed in this specific run for a disclosed, sandbox-only reason (see Known Limitations) and was confirmed **non-fatal** — the rest of the application kept working normally. This is real evidence, not a simulation, of everything **except** the actual Windows-native `.exe` file itself running.

## 18. Known limitations

- **No real `.exe` was built or executed** — Linux sandbox, no PyInstaller, no network to install it (Section 0). The spec is complete and ready for a real Windows build machine.
- **`waitress` is not installed in this sandbox** (same gap disclosed in Stage 16) — LAN mode's `serve()` call could not be exercised live here, only its surrounding logic (banner, config, guard).
- **Real Alembic is not installed in this sandbox** (same gap disclosed since Stage 15) — the ImportError fallback path was exercised for real; the "Alembic present" path was exercised against a faithful fake, not the real library.
- **The four `database/seed/seed_*.py` modules use SQLAlchemy's legacy `.query()` API internally** (pre-existing, Stage 3-10 code, unmodified by this stage) — correct and fully supported against real SQLAlchemy 2.x, but not implemented by this sandbox's ORM verification shim (a newly-surfaced, shim-only gap: nothing in the 699-test suite had ever actually called these functions before this stage, since they were previously only invoked by hand or by the also-excluded `tests/unit/test_models.py`). This stage's own test suite works around it by substituting tracking stubs for the real `seed()` functions, so this stage's *own* orchestration logic (which module gets called, in what order, whether the result is committed, whether a failure is contained) is genuinely verified — the seed modules' own SQL correctness was not modified, and was already exercised via the pre-existing suite's rule-content tests wherever those rules matter.
- **No package-size measurement, no antivirus-scan result, no measured startup-time** — none of these can exist without a real build (Sections 16, 34, 37).
- **No installer, no icon file, no automated shortcut creation** — a professional `.ico` file was not created (Section 20 only calls for one "if an existing asset exists" — none did, and a placeholder was deliberately not fabricated to avoid a "cartoonish" result); two plain `.bat` launcher files were provided instead of programmatic shortcut creation (avoids a new dependency like `pywin32`/`winshell`, and is a one-click-to-shortcut experience via Windows' own "Send to > Desktop" already).

## 19. Deployment instructions

See `README_DEPLOYMENT.md` for the plain-language version. Technically: build per Section 3 above, copy `dist/FINsight/` plus the two `.bat` files to the target computer (or a USB drive / network share for transfer, per Section 30's "transfer to another compatible Windows computer" requirement — this "onedir" folder is exactly what makes that simple: copy the whole folder, nothing to install), double-click `Start_FINsight_Local.bat` or `Start_FINsight_LAN_Host.bat`.
