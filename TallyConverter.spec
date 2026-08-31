# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Tally Converter.

Run via build_windows.bat (which builds the frontend first, then calls
`pyinstaller TallyConverter.spec`). Produces dist/TallyConverter/ containing
TallyConverter.exe plus all bundled dependencies - no Python/Node install
needed on the target machine.
"""
import sys
from pathlib import Path

block_cipher = None

PROJECT_ROOT = Path(SPECPATH)
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

# --------------------------------------------------------------------
# Data files bundled into the executable's working directory
# --------------------------------------------------------------------
datas = []

if FRONTEND_DIST.exists():
    datas.append((str(FRONTEND_DIST), "frontend/dist"))
else:
    print("WARNING: frontend/dist not found - run 'npm run build' in frontend/ first.")

# Bundle a local Tesseract-OCR install if the build machine has one at
# C:\Program Files\Tesseract-OCR - copies the whole folder (binary +
# tessdata) so the packaged app works fully offline without requiring
# the customer to install Tesseract separately. If you'd rather require
# a customer-side Tesseract install instead, delete this block; the app
# still auto-detects a system install per app/config.py.
_tesseract_candidates = [
    Path(r"C:\Program Files\Tesseract-OCR"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR"),
]
for _tpath in _tesseract_candidates:
    if _tpath.exists():
        datas.append((str(_tpath), "tesseract"))
        break

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "app.api.upload",
    "app.api.transactions",
    "app.api.mappings",
    "app.api.validation",
    "app.api.tally",
    "app.api.dashboard",
    "app.api.audit",
]

a = Analysis(
    [str(BACKEND_DIR / "run.py")],
    pathex=[str(BACKEND_DIR)],
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
    name="TallyConverter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,  # place an .ico at installer/app_icon.ico and reference it here if desired
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TallyConverter",
)
