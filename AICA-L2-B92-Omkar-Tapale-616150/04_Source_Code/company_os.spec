# PyInstaller spec for Company OS.
# Build with:  pyinstaller company_os.spec
import sys
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("dateparser")
    + [
        "sqlalchemy.sql.default_comparator",
    ]
)

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("app/templates", "app/templates"),
        ("app/static", "app/static"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CompanyOS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
