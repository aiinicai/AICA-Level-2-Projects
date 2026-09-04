# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller build spec for the DISCOM Audit Data Compiler desktop app.
# Build with:  pyinstaller DISCOM_Audit_Compiler.spec
# (the accompanying build_exe.bat runs this for you automatically)

import sys
from pathlib import Path

block_cipher = None

# python-calamine and xlsxwriter sometimes need explicit hidden-import hints
# under PyInstaller's static import analysis, since they're loaded via
# dynamic/compiled extension paths that PyInstaller's scanner can miss.
hidden_imports = [
    "python_calamine",
    "xlsxwriter",
    "openpyxl",
    "openpyxl.cell._writer",
    "pandas._libs.tslibs.base",
    "PyQt6.sip",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        # Bundle sample_data so a first-time user has example files to test with
        ("sample_data", "sample_data"),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim unused heavy modules pandas/numpy sometimes pull in, to keep
        # the .exe smaller and build faster. Safe to remove any of these
        # from this list if the build fails complaining a module is missing.
        "matplotlib",
        "scipy",
        "IPython",
        "notebook",
        "pytest",
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtWebEngine",
        "PyQt6.Qt3DCore",
        "PyQt6.Qt3DRender",
        "PyQt6.QtMultimedia",
        "PyQt6.QtBluetooth",
        "PyQt6.QtNfc",
        "PyQt6.QtPositioning",
        "PyQt6.QtSensors",
        "PyQt6.QtSerialPort",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="DISCOM_Audit_Compiler",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # windowed app, no console popup
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,            # place an .ico file path here if you have a firm/app icon
)
