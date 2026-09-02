# PyInstaller spec — Stage 17 (EXE Packaging, Installation & Distribution).
#
# Populated per the approved Stage 17 instruction, replacing the Stage 2
# placeholder. --onedir (not --onefile) was the explicitly approved
# choice — Section 5: "FINsight uses templates, static assets, SQLite,
# uploaded files, generated reports, evidence, configuration. A
# one-folder deployment is easier to maintain and troubleshoot." This
# spec produces exactly that: a FINsight/ folder containing FINsight.exe
# next to an _internal/ folder holding the bundled Python runtime,
# dependencies, templates, and static assets — with database/, data/,
# and logs/ created alongside FINsight.exe at first run (config.py's
# Stage 17 frozen-aware BASE_DIR — see that file's own comment), never
# inside _internal/, so an application upgrade (which replaces
# _internal/) never touches user data.
#
# BUILD REQUIREMENTS (see documentation/stage17_exe_packaging.md for
# the full, honest account of what could and could not be verified in
# the development sandbox this spec was authored in):
#   - Windows (PyInstaller does not cross-compile — a Windows .exe can
#     only be built by running PyInstaller ON Windows)
#   - Python matching the project's supported version (3.11, per this
#     project's own development environment)
#   - PyInstaller >= 6.5, < 7.0 (see requirements.txt's commented entry)
#   - Every package in requirements.txt actually installed in the build
#     environment's virtualenv (pip install -r requirements.txt)
#
# BUILD COMMAND (run from the project root, in the build virtualenv):
#   pyinstaller build_exe.spec --clean
#
# OUTPUT: dist/FINsight/ — FINsight.exe plus _internal/. Copy the whole
# dist/FINsight/ folder to deploy; do not copy FINsight.exe alone.

import sys
from pathlib import Path

block_cipher = None

PROJECT_ROOT = Path(SPECPATH).resolve()

# --- Non-Python assets that must ship inside _internal/ (application
# files, not user data — see config.py's Stage 17 comment for that
# distinction). Destination paths mirror the source tree exactly, which
# is what lets app/__init__.py's existing template_folder/static_folder
# resolution (Path(__file__).resolve().parent.parent-relative, unchanged
# since Stage 2) keep working unmodified inside the frozen build. ---
datas = [
    (str(PROJECT_ROOT / "frontend" / "templates"), "frontend/templates"),
    (str(PROJECT_ROOT / "frontend" / "static"), "frontend/static"),
    (str(PROJECT_ROOT / "alembic.ini"), "."),
    (str(PROJECT_ROOT / "database" / "migrations"), "database/migrations"),
    (str(PROJECT_ROOT / "database" / "seed"), "database/seed"),
]

# --- Modules PyInstaller's static import analysis can miss. pandas/
# openpyxl ship their own PyInstaller hooks (via hookutils) and do not
# need to be listed; the four seed modules are imported dynamically by
# name inside app/bootstrap.py's _run_seed_modules(), and Alembic's
# migration environment (database/migrations/env.py) is only ever
# reached at runtime through Alembic's own script-location loading, not
# a normal `import`, so both are listed explicitly. ---
hiddenimports = [
    "database.seed.seed_reference_data",
    "database.seed.seed_accounting_rules",
    "database.seed.seed_audit_rules",
    "database.seed.seed_tax_rules",
    "alembic",
    "alembic.command",
    "alembic.config",
    "alembic.runtime.migration",
    "waitress",
]

# --- Files that must NEVER be bundled (Section 32/41) — a defensive,
# explicit exclude list on top of simply not referencing them in
# `datas` above. If a development database, log, or local secret ever
# ends up next to this spec file at build time, this keeps it out of
# the package rather than relying solely on care at build time. ---
excludes_check = [
    PROJECT_ROOT / "database" / "finsight.db",
    PROJECT_ROOT / "logs",
    PROJECT_ROOT / "config" / "secret_key",
    PROJECT_ROOT / ".env",
]
for _p in excludes_check:
    if _p.exists():
        print(f"WARNING: {_p} exists at build time and must be removed or excluded before shipping this build.")

a = Analysis(
    ["finsight_app.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Section 32: keep the build minimal — tests and dev tooling are
    # never imported by finsight_app.py's own import graph, so they are
    # not pulled in by default, but excluded explicitly as well for
    # clarity and defense-in-depth.
    excludes=["pytest", "pytest_cov", "tests"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FINsight",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Section 34: UPX-compressed executables trigger more antivirus false positives, not fewer
    console=True,  # Section 12: the first-run/mode-selection experience is console-based, by design
    icon=str(PROJECT_ROOT / "frontend" / "static" / "icon" / "finsight.ico")
    if (PROJECT_ROOT / "frontend" / "static" / "icon" / "finsight.ico").exists()
    else None,  # Section 20: use a real icon if one exists; do not fail the build if it doesn't yet
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FINsight",
)
