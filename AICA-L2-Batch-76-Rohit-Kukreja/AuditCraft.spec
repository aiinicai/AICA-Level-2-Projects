# PyInstaller build for the Windows .exe.
#
#     .venv\Scripts\python.exe -m PyInstaller AuditCraft.spec --noconfirm
#
# One file, so a colleague receives a single thing and there is no folder to
# keep together. The cost is a few seconds of unpacking on each start; the
# alternative is a directory where deleting one file breaks the application
# silently.
#
# Everything the application reads at runtime has to be listed in `datas`.
# Python imports are found by analysis; YAML, HTML, CSS and the migration
# scripts are not, and their absence shows up only when the feature that needs
# them is used.

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

HERE = Path(SPECPATH)

datas = [
    # The clause repository. Without it the application refuses to start, which
    # is the correct behaviour and a confusing first impression.
    (str(HERE / "content"), "content"),
    # Every page.
    (str(HERE / "app" / "templates"), "app/templates"),
    # Stylesheet, workspace script and the vendored HTMX/Alpine.
    (str(HERE / "app" / "static"), "app/static"),
    # The migration chain. A new installation runs it from empty, so the
    # versions directory is not optional.
    (str(HERE / "alembic"), "alembic"),
]

hiddenimports = [
    # uvicorn resolves its loop, protocol and lifespan implementations by
    # string at runtime, so static analysis finds none of them.
    *collect_submodules("uvicorn"),
    # SQLAlchemy loads a dialect by URL scheme, likewise by string.
    "sqlalchemy.dialects.sqlite",
    # alembic imports each migration script by path at runtime.
    *collect_submodules("alembic"),
    "app.main",
]

a = Analysis(
    ["launcher.py"],
    pathex=[str(HERE)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # Not used by the application and large. Excluded to keep the download
    # something a firm can email.
    excludes=["tkinter", "matplotlib", "numpy", "pytest", "PIL"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AuditCraft",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX compression is a common antivirus false-positive trigger.
    runtime_tmpdir=None,
    # A console window, deliberately. It carries the address to open, where the
    # data is kept, and any startup error. Hiding it would leave a colleague
    # with an .exe that appears to do nothing.
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
