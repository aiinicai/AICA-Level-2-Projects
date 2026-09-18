# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for CA DocuFlow AI.

Build a portable single-folder EXE (recommended -- faster startup than
--onefile, and avoids the temp-extraction step that can be flagged by some
antivirus software on shared office PCs):

    pyinstaller pdf_office_utility.spec

Output goes to dist/CADocuFlowAI/CADocuFlowAI.exe.

To build a single-file EXE instead, change `EXE(...)` below to bundle
`a.binaries`/`a.datas` directly into the EXE (see the commented block near
the bottom) -- slower to start (self-extracts to a temp folder each run)
but a single file to distribute.

See README.md "Creating the Windows EXE" for the full walkthrough,
including how to additionally wrap this in an Inno Setup / NSIS installer.

NOTE on webapi/: the Phase 3 "Team Deployment" multi-user web/API platform
(webapi/) is a separate FastAPI service, run with `uvicorn webapi.app:app`,
NOT bundled into this desktop EXE -- app.py never imports it, and this spec
does not reference it. See README.md "Team Deployment" for how to run/deploy
that service on its own.
"""
from pathlib import Path

block_cipher = None

project_root = Path(SPECPATH)

datas = [
    (str(project_root / "assets"), "assets"),
    (str(project_root / "config"), "config"),
]

# pikepdf and pyHanko both ship data files (e.g. certificate bundles /
# templates) that PyInstaller's default hooks usually pick up automatically,
# but we collect them explicitly so a first-time build doesn't silently miss
# them.
hiddenimports = [
    "pikepdf",
    "pyhanko",
    "pyhanko_certvalidator",
    "PIL",
    "fitz",
    "pytesseract",
    "pydantic",
    "keyring",
    "keyring.backends.Windows",
    "qrcode",
    "requests",
    # pywin32 -- Word COM automation (core/word_converter.py). Only imported
    # inside functions (not at module top-level, so it stays optional on
    # non-Windows dev machines), which means PyInstaller's static import
    # scan can miss it; declared explicitly so the built EXE doesn't lose
    # Word automation even though it works fine from source.
    "win32com",
    "win32com.client",
    "pythoncom",
    "pywintypes",
]

try:
    from PyInstaller.utils.hooks import collect_data_files, collect_submodules

    datas += collect_data_files("pyhanko")
    datas += collect_data_files("pyhanko_certvalidator")
    hiddenimports += collect_submodules("pyhanko")
except Exception:
    # Best-effort: if hook collection fails on an older PyInstaller version,
    # the app still runs -- pyHanko/certificate signing is an optional module.
    pass

a = Analysis(
    ["app.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="CADocuFlowAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # windowed app, no console popup
    icon=str(project_root / "assets" / "icons" / "app_icon.ico")
    if (project_root / "assets" / "icons" / "app_icon.ico").exists()
    else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CADocuFlowAI",
)

# ---------------------------------------------------------------------------
# Single-file build (slower startup, one .exe to distribute): comment out the
# EXE(...)/COLLECT(...) block above and uncomment this instead.
# ---------------------------------------------------------------------------
# exe = EXE(
#     pyz,
#     a.scripts,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     [],
#     name="CADocuFlowAI",
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     runtime_tmpdir=None,
#     console=False,
#     icon=str(project_root / "assets" / "icons" / "app_icon.ico"),
# )
